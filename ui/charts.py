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


# ─────────────────────────────────────────────────────────────────────────────
# Gráficas de la pestaña "Análisis de Señal"
# ─────────────────────────────────────────────────────────────────────────────

def chart_signal_time() -> str:
    """Forma de onda IQ en tiempo real — componentes I y Q separadas."""
    fig = Figure(figsize=(7, 2.6))
    ax = fig.subplots()
    fig.patch.set_facecolor(MPL_BG)

    raw = engine_instance.amplitude_data.astype(np.float32)
    n = len(raw)
    t_total = n / engine_instance.sample_rate
    t = np.linspace(0, t_total * 1000, n)          # milisegundos

    # Usar la amplitud real como proxy (I real, Q imaginario)
    i_comp =  raw
    q_comp = np.roll(raw, n // 4)                   # proxy desfasado 90°

    ax.plot(t, i_comp, color=ACCENT_CYAN, linewidth=0.8, alpha=0.9, label="I (real)")
    ax.plot(t, q_comp, color=ACCENT_GREEN, linewidth=0.8, alpha=0.75, label="Q (imag)")
    ax.fill_between(t, i_comp, alpha=0.08, color=ACCENT_CYAN)

    ax.set_ylim([engine_instance.amp_min, engine_instance.amp_max])
    ax.legend(fontsize=7, facecolor=MPL_AXBG, edgecolor=BORDER_COL, labelcolor=MPL_TEXT,
              loc="upper right")
    style_ax(ax, "Señal en el Tiempo (I / Q)", "Tiempo (ms)", "Amplitud (V)")
    fig.tight_layout(pad=0.5)
    return fig_to_b64(fig)


def chart_power_time() -> str:
    """Potencia instantánea en dBFS vs tiempo (ventana deslizante)."""
    fig = Figure(figsize=(10, 5.6))
    ax = fig.subplots()
    fig.patch.set_facecolor(MPL_BG)

    written = engine_instance.power_samples_written
    if written > 0:
        pwr = engine_instance.power_time_data[-written:]
    else:
        pwr = np.array([-100.0])

    n = len(pwr)

    # Tiempo en segundos relativos (ventana ≈ batch_size * N / Fs)
    batch_dur = (engine_instance.fft_size * 10) / engine_instance.sample_rate
    t = np.arange(n) * batch_dur

    ax.plot(t, pwr, color=ACCENT_AMBER, linewidth=1.0, alpha=0.9, label="Potencia")
    ax.fill_between(t, pwr, np.min(pwr), alpha=0.15, color=ACCENT_AMBER)

    # Línea de piso de ruido (mediana)
    if len(pwr) > 1:
        noise_floor = float(np.median(pwr))
        ax.axhline(noise_floor, color=TEXT_MUTED, linestyle=":", linewidth=0.9,
                   alpha=0.8, label=f"Piso ruido: {noise_floor:.1f} dB")

        # Resaltar máximo
        max_idx = int(np.argmax(pwr))
        ax.axvline(t[max_idx], color=ACCENT_RED, linestyle="--", linewidth=0.9,
                   alpha=0.85, label=f"Pico: {pwr[max_idx]:.1f} dB")

    ax.legend(fontsize=7, facecolor=MPL_AXBG, edgecolor=BORDER_COL, labelcolor=MPL_TEXT)

    # Aplicar rango Y configurado por el usuario ESPECÍFICO para esta pestaña
    ymin = engine_instance.power_db_min
    ymax = engine_instance.power_db_max
    ax.set_ylim([ymin, ymax])

    # Segundas líneas de referencia visuales a cuartos del rango
    quarter = (ymax - ymin) / 4
    for q_val in [ymin + quarter, ymin + quarter * 2, ymin + quarter * 3]:
        ax.axhline(q_val, color=BORDER_COL, linestyle="-", linewidth=0.4, alpha=0.35)

    style_ax(ax, "Potencia vs. Tiempo  [dBFS \u2014 relativo al fondo de escala digital]",
             "Tiempo desde inicio (s)", f"Potencia (dBFS)  [{ymin:.0f} \u2026 {ymax:.0f}]")
    fig.tight_layout(pad=0.5)
    return fig_to_b64(fig)


def chart_freq_snr() -> str:
    """SNR por bin de frecuencia, resaltando señales de interés detectadas."""
    fig = Figure(figsize=(10, 5.6))
    ax = fig.subplots()
    fig.patch.set_facecolor(MPL_BG)

    snr = engine_instance.snr_data
    fc  = engine_instance.center_freq
    fs  = engine_instance.sample_rate / 1_000_000

    full_freq = np.linspace(fc - fs/2, fc + fs/2, len(snr))
    fmin, fmax = engine_instance.f_min, engine_instance.f_max
    mask = (full_freq >= fmin) & (full_freq <= fmax)
    freq_cr = full_freq[mask]
    snr_cr  = snr[mask]
    if len(freq_cr) == 0:
        freq_cr, snr_cr = full_freq, snr

    ax.plot(freq_cr, snr_cr, color="#1f77b4", linewidth=1.0, alpha=0.95)
    
    # Marcador de picos: similar a la imagen (círculo rojo hueco)
    if len(engine_instance.signals_of_interest) > 0:
        pk_f = []
        pk_s = []
        for freq_si, snr_si in engine_instance.signals_of_interest:
            if fmin <= freq_si <= fmax:
                pk_f.append(freq_si)
                pk_s.append(snr_si)
        if pk_f:
            ax.scatter(pk_f, pk_s, s=40, facecolors='none', edgecolors='red', linewidth=1.2, zorder=5)

    # Marcador HI
    if fmin <= 1420.40 <= fmax:
        ax.axvline(1420.40, color=ACCENT_CYAN, linestyle="--",
                   linewidth=1.0, alpha=0.9, label="HI 1420.40 MHz")

    ax.set_ylim([engine_instance.snr_db_min, engine_instance.snr_db_max])
    ax.set_xlim([fmin, fmax])
    style_ax(ax,
             "SNR vs. Frecuencia",
             "Frecuencia (MHz)",
             "Magnitud (dB sobre piso de ruido)")
    fig.tight_layout(pad=0.5)
    return fig_to_b64(fig)


# ─────────────────────────────────────────────────────────────────────────────
# Gráficas de resultados de algoritmos avanzados
# ─────────────────────────────────────────────────────────────────────────────

def chart_algo_placeholder() -> str:
    """Placeholder rápido mientras corre un algoritmo pesado."""
    fig = Figure(figsize=(7, 3.8))
    ax = fig.subplots()
    fig.patch.set_facecolor(MPL_BG)
    ax.text(0.5, 0.5, "Calculando Nuevo Método...", color=ACCENT_AMBER, 
            fontsize=12, ha="center", va="center")
    style_ax(ax, "Transición de Algoritmo", "", "")
    ax.set_xticks([]); ax.set_yticks([])
    fig.tight_layout(pad=0.5)
    return fig_to_b64(fig)


def chart_ar_spectrum(result: dict) -> str:
    """Espectro AR/Burg: alta resolución."""
    fig = Figure(figsize=(7, 3.8))
    ax = fig.subplots()
    fig.patch.set_facecolor(MPL_BG)

    freqs = result["freqs"]
    psd   = result["psd"]
    order = result["order"]

    ax.plot(freqs, psd, color="#B380FF", linewidth=1.1, alpha=0.95,
            label=f"AR/Burg (orden {order})")
    ax.fill_between(freqs, psd, np.min(psd), alpha=0.15, color="#B380FF")

    for f_pk, p_pk in result.get("peaks", []):
        ax.axvline(f_pk, color=ACCENT_AMBER, linewidth=1.0,
                   linestyle="--", alpha=0.85)
        ax.text(f_pk, p_pk + 0.5, f"{f_pk:.3f}", color=ACCENT_AMBER,
                fontsize=6, ha="center")

    ax.legend(fontsize=7, facecolor=MPL_AXBG, edgecolor=BORDER_COL, labelcolor=MPL_TEXT)
    style_ax(ax, "Espectro AR/Burg (Alta Resolución)", "Frecuencia (MHz)", "PSD (dB)")
    fig.tight_layout(pad=0.6)
    return fig_to_b64(fig)


def chart_cwt_map(result: dict) -> str:
    """Mapa de la CWT: intensidad tiempo-frecuencia."""
    fig = Figure(figsize=(7, 3.8))
    ax = fig.subplots()
    fig.patch.set_facecolor(MPL_BG)

    cwt_mat   = result["cwt_matrix"]     # (n_scales, n_samples)
    times_s   = result["times_s"]
    freqs_hz  = result["freqs_hz"]

    im = ax.imshow(
        np.flipud(cwt_mat),
        aspect="auto",
        extent=[times_s[0] * 1000, times_s[-1] * 1000,
                freqs_hz[0] / 1e6, freqs_hz[-1] / 1e6],
        cmap="plasma", interpolation="bilinear", origin="lower"
    )
    cb = fig.colorbar(im, ax=ax, shrink=0.9, pad=0.02)
    cb.set_label("Potencia Wavelet", color=MPL_TEXT, fontsize=8)
    cb.ax.yaxis.set_tick_params(color=MPL_TEXT, labelcolor=MPL_TEXT, labelsize=7)

    style_ax(ax, "Transformada Wavelet Continua (Morlet)",
             "Tiempo (ms)", "Escala Frecuencial (Δf MHz)")
    fig.tight_layout(pad=0.6)
    return fig_to_b64(fig)


def chart_music_spectrum(result: dict) -> str:
    """Pseudo-espectro MUSIC o ESPRIT: picos ultra-estrechos."""
    fig = Figure(figsize=(7, 3.8))
    ax = fig.subplots()
    fig.patch.set_facecolor(MPL_BG)

    method = result.get("method", "MUSIC")
    freqs  = result["freqs"]
    key    = "music_spectrum" if "music_spectrum" in result else "esprit_spectrum"
    spec   = result[key]

    col = ACCENT_RED if "MUSIC" in method else "#FF80AB"
    ax.plot(freqs, spec, color=col, linewidth=1.2, alpha=0.95, label=method)
    ax.fill_between(freqs, spec, np.min(spec), alpha=0.14, color=col)

    for f_pk, p_pk in result.get("peaks", []):
        ax.axvline(f_pk, color=ACCENT_AMBER, linewidth=1.1,
                   linestyle=":", alpha=0.9)
        ax.text(f_pk, p_pk + 0.5, f"{f_pk:.4f}", color=ACCENT_AMBER,
                fontsize=6, ha="center")

    ax.legend(fontsize=7, facecolor=MPL_AXBG, edgecolor=BORDER_COL, labelcolor=MPL_TEXT)
    style_ax(ax, f"Pseudo-Espectro {method}",
             "Frecuencia (MHz)", "Pseudo-potencia (dB norm.)")
    fig.tight_layout(pad=0.6)
    return fig_to_b64(fig)


def chart_algo_placeholder() -> str:
    """Imagen oscura 16:9 — placeholder antes de iniciar el stream."""
    fig = Figure(figsize=(10, 5.6))
    ax = fig.subplots()
    fig.patch.set_facecolor(MPL_BG)
    ax.set_facecolor(MPL_AXBG)
    ax.set_xlim([0, 1])
    ax.set_ylim([0, 1])
    ax.text(0.5, 0.55,
            "Selecciona un metodo en el panel derecho\ny activa el stream para calcular.",
            transform=ax.transAxes, ha="center", va="center",
            color=MPL_TEXT, fontsize=13, alpha=0.50, multialignment="center")
    ax.text(0.5, 0.30, "Algoritmo DSP",
            transform=ax.transAxes, ha="center", va="center",
            color=ACCENT_CYAN, fontsize=22, alpha=0.22)
    for sp in ax.spines.values():
        sp.set_edgecolor(BORDER_COL)
    ax.tick_params(left=False, bottom=False, labelleft=False, labelbottom=False)
    ax.grid(False)
    fig.tight_layout(pad=0.6)
    return fig_to_b64(fig)
