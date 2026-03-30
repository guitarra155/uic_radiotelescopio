"""
charts.py
Agrupa toda la lógica de ploteo con Matplotlib.
Usa una caché persistente de figuras para permitir refrescos de 10ms sin saturar la CPU.
"""

import math
import io
import base64
import numpy as np
from matplotlib.figure import Figure
from core.constants import *
from core.dsp_engine import engine_instance

# --- Caché de Objetos Matplotlib (Singleton persistente) ---
class ChartCache:
    def __init__(self):
        self.figs = {}      # {name: Figure}
        self.axes = {}      # {name: Axes}
        self.artists = {}   # {name: [Line2D, ...]}
        self.colorbars = {} # {name: Colorbar}

cache = ChartCache()

def get_cached_fig(name, figsize=(7, 2.8), is_3d=False):
    """Crea o recupera una figura de la caché para evitar sobrecoste de memoria."""
    if name not in cache.figs:
        fig = Figure(figsize=figsize, dpi=85)
        fig.patch.set_facecolor(MPL_BG)
        ax = fig.subplots()
        style_ax(ax)
        cache.figs[name] = fig
        cache.axes[name] = ax
        cache.artists[name] = {}
        return fig, ax, True # True = Recién creado
    return cache.figs[name], cache.axes[name], False

def fig_to_b64(fig: Figure) -> str:
    """Retorna Base64 crudo. savefig es el cuello de botella, pero sin bbox_inches es tolerable."""
    buf = io.BytesIO()
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
    if title: ax.set_title(title, color=ACCENT_CYAN, fontsize=9, pad=6)
    if xlabel: ax.set_xlabel(xlabel, color=TEXT_MUTED, fontsize=8)
    if ylabel: ax.set_ylabel(ylabel, color=TEXT_MUTED, fontsize=8)
    ax.grid(True, color=MPL_GRID, linestyle="--", linewidth=0.5, alpha=0.6)

# --- Funciones de Gráficos Rápidos ---

def chart_amplitude() -> str:
    fig, ax, is_new = get_cached_fig("amplitude")
    sig = engine_instance.amplitude_data
    n = len(sig)
    t = np.linspace(0, n / engine_instance.sample_rate, n)

    if is_new or "line" not in cache.artists["amplitude"]:
        ax.clear()
        style_ax(ax, "Amplitud vs Tiempo (Streaming)", "Tiempo (s)", "Amplitud Baseband (V)")
        line, = ax.plot(t, sig, color=ACCENT_CYAN, linewidth=0.9, alpha=0.85)
        cache.artists["amplitude"]["line"] = line
    else:
        line = cache.artists["amplitude"]["line"]
        line.set_data(t, sig)
    
    ax.set_ylim([engine_instance.amp_min, engine_instance.amp_max])
    return fig_to_b64(fig)

def chart_spectrum() -> str:
    fig, ax, is_new = get_cached_fig("spectrum")
    spec = engine_instance.spectrum_data
    fc = engine_instance.center_freq
    fs = engine_instance.sample_rate / 1_000_000
    
    full_freq = np.linspace(fc - fs/2, fc + fs/2, len(spec))
    fmin, fmax = engine_instance.f_min, engine_instance.f_max
    
    mask = (full_freq >= fmin) & (full_freq <= fmax)
    freq_cr = full_freq[mask]
    spec_cr = spec[mask]
    if len(freq_cr) == 0: freq_cr, spec_cr = full_freq, spec

    if is_new or "line" not in cache.artists["spectrum"]:
        ax.clear()
        style_ax(ax, "Espectro de Frecuencia (Tiempo Real)", "Frecuencia (MHz)", "Potencia (dBFS)")
        line, = ax.plot(freq_cr, spec_cr, color=ACCENT_GREEN, linewidth=1.0)
        cache.artists["spectrum"]["line"] = line
    else:
        line = cache.artists["spectrum"]["line"]
        line.set_data(freq_cr, spec_cr)
    
    ax.set_ylim([engine_instance.db_min, engine_instance.db_max])
    ax.set_xlim([fmin, fmax])
    return fig_to_b64(fig)

def chart_spectrogram() -> str:
    # El waterfall es pesado, aquí imshow es lo más rápido
    fig, ax, is_new = get_cached_fig("waterfall", figsize=(10, 5))
    data = engine_instance.waterfall_data
    fc = engine_instance.center_freq
    fs = engine_instance.sample_rate / 1_000_000
    fmin, fmax = engine_instance.f_min, engine_instance.f_max
    
    full_freq = np.linspace(fc - fs/2, fc + fs/2, data.shape[1])
    mask = (full_freq >= fmin) & (full_freq <= fmax)
    data_cr = data[:, mask]
    if data_cr.shape[1] == 0: data_cr = data
    
    # Safety check for empty buffer
    if data_cr.size == 0:
        return fig_to_b64(fig)

    secs_per_line = (engine_instance.fft_size * 40) / engine_instance.sample_rate
    total_secs = engine_instance.waterfall_steps * secs_per_line

    if is_new or "im" not in cache.artists["waterfall"]:
        ax.clear()
        style_ax(ax, "Cascada Espectral (Waterfall)", "Frecuencia (MHz)", f"Tiempo (s)")
        # Usamos percentiles para el contraste inicial para que se vea SIEMPRE aunque el config sea malo
        v_min, v_max = np.percentile(data_cr, 5), np.percentile(data_cr, 99.9)
        im = ax.imshow(data_cr, aspect="auto", origin="lower",
                       extent=[fmin, fmax, 0, total_secs], 
                       cmap="inferno", interpolation="nearest", 
                       vmin=v_min, vmax=v_max)
        cache.artists["waterfall"]["im"] = im
    else:
        im = cache.artists["waterfall"]["im"]
        im.set_data(data_cr)
        im.set_extent([fmin, fmax, 0, total_secs])
        # Auto-contraste dinámico con seguridad si el buffer está vacío o fuera de rango
        if data_cr.size > 0:
            v_min, v_max = np.percentile(data_cr, 2), np.percentile(data_cr, 99.8)
            if v_min == v_max: v_max += 0.1
            im.set_clim(v_min, v_max)
        else:
            im.set_clim(-110, -20)

    return fig_to_b64(fig)

def chart_histogram() -> str:
    fig, ax, is_new = get_cached_fig("histogram", figsize=(8.0, 4.5))
    samples = engine_instance.histogram_data
    
    # El histograma es difícil de actualizar vía set_data, lo regeneramos pero reusando la figura
    ax.clear()
    style_ax(ax, "Histograma Baseband", "Magnitud (Abs)", "Ocurrencia Relativa")
    
    if len(samples) > 2 and np.std(samples) > 0:
        ax.hist(samples, bins=50, density=True, color=ACCENT_CYAN, alpha=0.5)
        mu, std = np.mean(samples), np.std(samples)
        x = np.linspace(np.min(samples), np.max(samples), 100)
        gauss = (1/(std * math.sqrt(2*math.pi))) * np.exp(-0.5*((x - mu)/std)**2)
        ax.plot(x, gauss, color=ACCENT_GREEN, linewidth=1.5)
        
    return fig_to_b64(fig)

def chart_signal_time() -> str:
    fig, ax, is_new = get_cached_fig("signal_time", figsize=(7, 2.6))
    raw = engine_instance.amplitude_data.astype(np.float32)
    n = len(raw)
    t = np.linspace(0, (n / engine_instance.sample_rate) * 1000, n)

    if is_new or "line_i" not in cache.artists["signal_time"]:
        ax.clear()
        style_ax(ax, "Señal en el Tiempo (I / Q)", "Tiempo (ms)", "Amplitud (V)")
        li, = ax.plot(t, raw, color=ACCENT_CYAN, linewidth=0.8, label="I")
        lq, = ax.plot(t, np.roll(raw, n//4), color=ACCENT_GREEN, linewidth=0.8, label="Q")
        cache.artists["signal_time"]["line_i"] = li
        cache.artists["signal_time"]["line_q"] = lq
    else:
        cache.artists["signal_time"]["line_i"].set_data(t, raw)
        cache.artists["signal_time"]["line_q"].set_data(t, np.roll(raw, n//4))

    ax.set_ylim([engine_instance.amp_min, engine_instance.amp_max])
    return fig_to_b64(fig)

def chart_power_time() -> str:
    fig, ax, is_new = get_cached_fig("power_time", figsize=(10, 5.6))
    written = engine_instance.power_samples_written
    pwr = engine_instance.power_time_data[-written:] if written > 0 else np.array([-100.0])
    n = len(pwr)
    batch_dur = (engine_instance.fft_size * 40) / engine_instance.sample_rate
    t = np.arange(n) * batch_dur

    if is_new or "line" not in cache.artists["power_time"]:
        ax.clear()
        style_ax(ax, "Potencia vs. Tiempo", "Tiempo (s)", "Potencia (dBFS)")
        line, = ax.plot(t, pwr, color=ACCENT_AMBER, linewidth=1.0)
        cache.artists["power_time"]["line"] = line
    else:
        line = cache.artists["power_time"]["line"]
        line.set_data(t, pwr)
        ax.set_xlim([0, max(1, t[-1])])

    ax.set_ylim([engine_instance.power_db_min, engine_instance.power_db_max])
    return fig_to_b64(fig)

def chart_freq_snr() -> str:
    fig, ax, is_new = get_cached_fig("freq_snr", figsize=(10, 5.6))
    snr = engine_instance.snr_data
    fc, fs = engine_instance.center_freq, engine_instance.sample_rate / 1e6
    fmin, fmax = engine_instance.f_min, engine_instance.f_max
    
    full_f = np.linspace(fc - fs/2, fc + fs/2, len(snr))
    mask = (full_f >= fmin) & (full_f <= fmax)
    f_cr, s_cr = full_f[mask], snr[mask]

    if is_new or "line" not in cache.artists["freq_snr"]:
        ax.clear()
        style_ax(ax, "SNR vs. Frecuencia", "Frecuencia (MHz)", "SNR (dB)")
        line, = ax.plot(f_cr, s_cr, color="#1f77b4", linewidth=1.0)
        cache.artists["freq_snr"]["line"] = line
    else:
        line = cache.artists["freq_snr"]["line"]
        line.set_data(f_cr, s_cr)

    ax.set_ylim([engine_instance.snr_db_min, engine_instance.snr_db_max])
    ax.set_xlim([fmin, fmax])
    return fig_to_b64(fig)

def chart_algo_placeholder() -> str:
    # Este no importa mucho que sea rápido
    fig = Figure(figsize=(10, 5.6))
    ax = fig.subplots()
    fig.patch.set_facecolor(MPL_BG)
    ax.set_facecolor(MPL_AXBG)
    ax.text(0.5, 0.5, "Selecciona un método para calcular", color=MPL_TEXT, ha="center")
    style_ax(ax)
    return fig_to_b64(fig)

# Funciones pesadas (AR/Burg, CWT, MUSIC, ESPRIT) ahora con CACHÉ para velocidad 100ms
def chart_ar_spectrum(result: dict) -> str:
    fig, ax, is_new = get_cached_fig("ar_spectrum", figsize=(7, 3.8))
    freqs, psd = result["freqs"], result["psd"]

    if is_new or "line" not in cache.artists["ar_spectrum"]:
        ax.clear()
        style_ax(ax, "Espectro AR/Burg (Alta Resolución)", "Frecuencia (MHz)", "PSD (dB)")
        line, = ax.plot(freqs, psd, color="#B380FF", linewidth=1.1, alpha=0.95)
        cache.artists["ar_spectrum"]["line"] = line
    else:
        line = cache.artists["ar_spectrum"]["line"]
        line.set_data(freqs, psd)
        ax.set_xlim([freqs[0], freqs[-1]])
        ax.set_ylim([np.min(psd)-5, np.max(psd)+5])

    return fig_to_b64(fig)

def chart_cwt_map(result: dict) -> str:
    """Mapa de la CWT: intensidad tiempo-frecuencia (Escalograma)."""
    fig, ax, is_new = get_cached_fig("cwt_map", figsize=(7, 3.8))
    cwt_mat = result["cwt_matrix"]
    t_ms = result["times_s"] * 1000
    f_mhz = result["freqs_hz"] / 1e6

    # El CWT es una matriz 2D, usamos imshow
    if is_new or "im" not in cache.artists["cwt_map"]:
        ax.clear()
        style_ax(ax, "Transformada Wavelet Continua (Morlet)", "Tiempo (ms)", "Escala (MHz)")
        im = ax.imshow(np.flipud(cwt_mat), aspect="auto", cmap="plasma",
                       extent=[t_ms[0], t_ms[-1], f_mhz[0], f_mhz[-1]],
                       interpolation="bilinear")
        cache.artists["cwt_map"]["im"] = im
    else:
        im = cache.artists["cwt_map"]["im"]
        im.set_data(np.flipud(cwt_mat))
        im.set_extent([t_ms[0], t_ms[-1], f_mhz[0], f_mhz[-1]])
        # Auto-ajuste de color para que siempre se vea algo
        im.set_clim(np.percentile(cwt_mat, 5), np.percentile(cwt_mat, 98))

    return fig_to_b64(fig)

def chart_music_spectrum(result: dict) -> str:
    """Pseudo-espectro MUSIC o ESPRIT."""
    method = result.get("method", "MUSIC")
    name = "music_spectrum"
    fig, ax, is_new = get_cached_fig(name, figsize=(7, 3.8))
    freqs = result["freqs"]
    spec = result.get("music_spectrum", result.get("esprit_spectrum"))

    if is_new or "line" not in cache.artists[name]:
        ax.clear()
        style_ax(ax, f"Pseudo-Espectro {method}", "Frecuencia (MHz)", "Pseudo-potencia (dB)")
        col = ACCENT_RED if "MUSIC" in method else "#FF80AB"
        line, = ax.plot(freqs, spec, color=col, linewidth=1.2)
        cache.artists[name]["line"] = line
    else:
        line = cache.artists[name]["line"]
        line.set_data(freqs, spec)
        ax.set_xlim([freqs[0], freqs[-1]])
        ax.set_ylim([np.min(spec)-2, np.max(spec)+2])

    return fig_to_b64(fig)
