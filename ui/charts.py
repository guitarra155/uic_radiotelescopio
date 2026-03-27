"""
charts.py
Agrupa toda la lógica de ploteo con Matplotlib.
Ahora lee directamente de los buffers del DSPEngine para visualización en tiempo real.
"""

import math
import io
import base64
import numpy as np
from matplotlib.figure import Figure
from core.constants import *
from core.dsp_engine import engine_instance

def fig_to_b64(fig: Figure) -> str:
    """Retorna Base64 crudo listo para usar en ft.Image(src=...)."""
    buf = io.BytesIO()
    # Interpolacion nativa a 85 DPI + Eliminando bbox_inches='tight' baja de 500ms a 30ms el tiempo de render
    fig.savefig(buf, format="png", dpi=85)
    buf.seek(0)
    enc = base64.b64encode(buf.read()).decode()
    buf.close()
    return f"data:image/png;base64,{enc}"

def style_ax(ax, title="", xlabel="", ylabel=""):
    """Aplica formato Dark Theme nativo a un eje de Matplotlib."""
    ax.set_facecolor(MPL_AXBG)
    ax.tick_params(colors=MPL_TEXT, labelsize=8)
    for sp in ax.spines.values():
        sp.set_edgecolor(BORDER_COL)
    ax.set_title(title, color=ACCENT_CYAN, fontsize=9, pad=6)
    ax.set_xlabel(xlabel, color=TEXT_MUTED, fontsize=8)
    ax.set_ylabel(ylabel, color=TEXT_MUTED, fontsize=8)
    ax.grid(True, color=MPL_GRID, linestyle="--", linewidth=0.5, alpha=0.6)

def chart_amplitude() -> str:
    fig = Figure(figsize=(7, 2.8))
    ax = fig.subplots()
    fig.patch.set_facecolor(MPL_BG)
    
    # Leemos del DSP puro en tiempo real
    sig = engine_instance.amplitude_data
    # Convertimos muestras a tiempo real (segundos)
    n = len(sig)
    t_total = n / engine_instance.sample_rate  # segundos
    t = np.linspace(0, t_total, n)
    
    ax.plot(t, sig, color=ACCENT_CYAN, linewidth=0.9, alpha=0.85)
    ax.fill_between(t, sig, alpha=0.15, color=ACCENT_CYAN)
    
    # Marcador decorativo de pico más alto actual
    if n > 0:
        max_idx = np.argmax(sig)
        ax.axvline(t[max_idx], color=ACCENT_RED, linestyle="--", linewidth=0.9,
                   alpha=0.85, label=f"Pico: t={t[max_idx]:.4f} s")
        
    ax.legend(fontsize=7, facecolor=MPL_AXBG, edgecolor=BORDER_COL, labelcolor=MPL_TEXT)
    ax.set_ylim([engine_instance.amp_min, engine_instance.amp_max])
    style_ax(ax, "Amplitud vs Tiempo (Streaming)", "Tiempo (s)", "Amplitud Baseband (V)")
    fig.tight_layout(pad=0.6)
    return fig_to_b64(fig)

def chart_spectrum() -> str:
    fig = Figure(figsize=(7, 2.8))
    ax = fig.subplots()
    fig.patch.set_facecolor(MPL_BG)
    
    spec = engine_instance.spectrum_data
    # Convertimos los bins de la FFT a frecuencias absolutas (MHz)
    fc = engine_instance.center_freq
    fs = engine_instance.sample_rate / 1_000_000 # En MHz
    
    full_freq = np.linspace(fc - fs/2, fc + fs/2, len(spec))
    fmin, fmax = engine_instance.f_min, engine_instance.f_max
    
    # Recorte Horizontal (Zoom)
    mask = (full_freq >= fmin) & (full_freq <= fmax)
    freq_cr = full_freq[mask]
    spec_cr = spec[mask]
    if len(freq_cr) == 0: freq_cr, spec_cr = full_freq, spec
    
    ax.plot(freq_cr, spec_cr, color=ACCENT_GREEN, linewidth=1.0)
    ax.fill_between(freq_cr, spec_cr, engine_instance.db_min, alpha=0.2, color=ACCENT_GREEN)
    ax.axvline(1420.40, color=ACCENT_AMBER, linestyle="--", linewidth=1.0,
               alpha=0.9, label="HI 1420.40 MHz")
    ax.set_ylim([engine_instance.db_min, engine_instance.db_max])
    ax.set_xlim([fmin, fmax])
    ax.legend(fontsize=7, facecolor=MPL_AXBG, edgecolor=BORDER_COL, labelcolor=MPL_TEXT)
    style_ax(ax, "Espectro de Frecuencia (Tiempo Real)", "Frecuencia (MHz)", "Potencia (dBFS)")
    fig.tight_layout(pad=0.6)
    return fig_to_b64(fig)

def chart_spectrogram() -> str:
    fig = Figure(figsize=(10, 5))
    ax = fig.subplots()
    fig.patch.set_facecolor(MPL_BG)
    
    data = engine_instance.waterfall_data
    fc = engine_instance.center_freq
    fs = engine_instance.sample_rate / 1_000_000 # En MHz
    
    fmin, fmax = engine_instance.f_min, engine_instance.f_max
    full_freq = np.linspace(fc - fs/2, fc + fs/2, data.shape[1])
    
    # Recorte (Zoom Horizontal)
    mask = (full_freq >= fmin) & (full_freq <= fmax)
    data_cr = data[:, mask]
    if data_cr.shape[1] == 0: data_cr = data
    
    # Calcular el tiempo real por línea (cada línea = fft_size * batches / sample_rate segundos)
    secs_per_line = (engine_instance.fft_size * 10) / engine_instance.sample_rate
    total_secs = engine_instance.waterfall_steps * secs_per_line

    # El waterfall dibuja la historia recortada
    im = ax.imshow(data_cr, aspect="auto", origin="lower",
                   extent=[fmin, fmax, 0, total_secs], 
                   cmap="inferno", interpolation="nearest", 
                   vmin=engine_instance.db_min, vmax=engine_instance.db_max)
                   
    cb = fig.colorbar(im, ax=ax, shrink=0.9, pad=0.02)
    cb.set_label("Potencia (dBFS)", color=MPL_TEXT, fontsize=9)
    cb.ax.yaxis.set_tick_params(color=MPL_TEXT, labelcolor=MPL_TEXT, labelsize=8)
    
    ax.axvline(1420.40, color=ACCENT_CYAN, linestyle="--", linewidth=1.2,
               alpha=0.85, label="HI 1420.40 MHz")
    ax.legend(fontsize=8, facecolor=MPL_AXBG, edgecolor=BORDER_COL,
              labelcolor=MPL_TEXT, loc="upper right")
    style_ax(ax, "Cascada Espectral (Waterfall)", "Frecuencia (MHz)", f"Tiempo (s)  [reso. {secs_per_line:.3f} s/línea]")
    fig.tight_layout(pad=0.6)
    return fig_to_b64(fig)

def chart_histogram() -> str:
    fig = Figure(figsize=(8.0, 4.5))  # Aspecto 16:9
    ax = fig.subplots()
    fig.patch.set_facecolor(MPL_BG)
    
    samples = engine_instance.histogram_data
    if len(samples) > 0 and np.std(samples) > 0:
        ax.hist(samples, bins=70, density=True, color=ACCENT_CYAN,
                alpha=0.55, edgecolor=MPL_BG, linewidth=0.3, label="Muestras en vivo")
        
        # Superponer gaussiana teórica basada en media y desviación estándar real
        mu, std = np.mean(samples), np.std(samples)
        x = np.linspace(np.min(samples), np.max(samples), 300)
        gauss = (1/(std * math.sqrt(2*math.pi))) * np.exp(-0.5*((x - mu)/std)**2)
        ax.plot(x, gauss, color=ACCENT_GREEN, linewidth=1.5, label=f"Fit (μ={mu:.2f}, σ={std:.2f})")
        
        # Umbral anomalía basado en el 99th percentil real
        p99 = np.percentile(samples, 99.5) if len(samples) > 0 else 0
        ax.axvline(p99, color=ACCENT_RED, linewidth=1.2, linestyle=":", label="Umbral Smart Trigger")
        
    ax.legend(fontsize=7, facecolor=MPL_AXBG, edgecolor=BORDER_COL, labelcolor=MPL_TEXT)
    style_ax(ax, "Histograma Baseband", "Magnitud (Abs)", "Ocurrencia Relativa")
    fig.tight_layout(pad=0.6)
    return fig_to_b64(fig)
