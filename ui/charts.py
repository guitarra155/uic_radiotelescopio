"""
charts.py
Agrupa toda la lógica de ploteo con Matplotlib.
Usa una caché persistente de figuras para permitir refrescos de 10ms sin saturar la CPU.
"""

import math
import io
import base64
import numpy as np
import matplotlib
from matplotlib.figure import Figure
from core.constants import *
from core.dsp_engine import engine_instance

# Configuración global para que SVG no convierta el texto en trazados (paths).
# Esto delega la renderización del texto a Flet, haciéndolo 100% nítido.
matplotlib.rcParams['svg.fonttype'] = 'none'


# --- Caché de Objetos Matplotlib (Singleton persistente) ---
class ChartCache:
    def __init__(self):
        self.figs = {}  # {name: Figure}
        self.axes = {}  # {name: Axes}
        self.artists = {}  # {name: [Line2D, ...]}
        self.colorbars = {}  # {name: Colorbar}


cache = ChartCache()


def get_dynamic_figsize(base_width=9.5, base_height=2.8):
    """Calcula un tamaño dinámico con aspect ratio PERFECTO según la ventana."""
    win_w = getattr(engine_instance, "window_width", 1280)
    win_h = getattr(engine_instance, "window_height", 720)
    
    # Alto real del contenedor Flet (sin pestañas, header, footer)
    avail_h = win_h - 140
    
    # Ancho real del contenedor (sin panel derecho si está cerrado, estimamos 40px padding)
    is_collapsed = getattr(engine_instance, "is_config_collapsed", False)
    avail_w = win_w - 40 if is_collapsed else win_w - 340
    
    # Determinar qué fracción de pantalla ocupa esta gráfica según sus parámetros base
    # (19.0 y 5.6 eran los valores de pantalla completa originales)
    frac_w = base_width / 19.0
    frac_h = base_height / 5.6
    
    fig_w = (avail_w * frac_w) / 100.0
    fig_h = (avail_h * frac_h) / 100.0
    
    return (max(2.0, fig_w), max(1.5, fig_h))

def get_cached_fig(name, figsize=(9.5, 3.0), is_3d=False):
    """Crea o recupera una figura de la caché para evitar sobrecoste de memoria."""
    if name not in cache.figs:
        fig = Figure(figsize=figsize, dpi=96)  # 96dpi estándar de pantalla
        fig.patch.set_facecolor(MPL_BG)
        ax = fig.subplots()
        style_ax(ax)
        # tight_layout UNA SOLA VEZ al crear la figura, no en cada frame
        try:
            fig.tight_layout(pad=0.2)
        except:
            pass
        cache.figs[name] = fig
        cache.axes[name] = ax
        cache.artists[name] = {}
        return fig, ax, True  # True = Recién creado
    
    fig = cache.figs[name]
    ax = cache.axes[name]
    
    # Actualizar tamaño si cambió (sin tight_layout para no bloquear el hilo)
    current_size = fig.get_size_inches()
    if abs(current_size[0] - figsize[0]) > 0.1 or abs(current_size[1] - figsize[1]) > 0.1:
        fig.set_size_inches(figsize)
    return fig, ax, False


def fig_to_b64(fig: Figure, dpi: int = 72) -> str:
    """Retorna Base64 SVG para que los ejes tengan resolución vectorial perfecta, 
    mientras los rasterizados (gráficas 2D) quedan incrustados."""
    buf = io.BytesIO()
    # SVG garantiza resolución infinita en las etiquetas y ejes de Flet sin pixelarse.
    fig.savefig(buf, format="svg", bbox_inches='tight', facecolor=MPL_BG, edgecolor=MPL_BG)
    buf.seek(0)
    enc = base64.b64encode(buf.read()).decode()
    buf.close()
    return f"data:image/svg+xml;base64,{enc}"


def safe_set_ylim(ax, ymin, ymax, fallback_span=10.0):
    """Evita que Matplotlib se queje si ymin == ymax."""
    ymin, ymax = float(ymin), float(ymax)
    if abs(ymax - ymin) < 1e-6:
        ymin -= 5.0
        ymax += 5.0
    
    current_ymin, current_ymax = ax.get_ylim()
    if abs(current_ymin - ymin) > 1e-3 or abs(current_ymax - ymax) > 1e-3:
        ax.set_ylim([ymin, ymax])

def safe_set_xlim(ax, xmin, xmax, fallback_span=1.0):
    """Evita que Matplotlib se queje si xmin == xmax."""
    xmin, xmax = float(xmin), float(xmax)
    if abs(xmax - xmin) < 1e-6:
        xmin -= 0.5
        xmax += 0.5
        
    current_xmin, current_xmax = ax.get_xlim()
    if abs(current_xmin - xmin) > 1e-3 or abs(current_xmax - xmax) > 1e-3:
        ax.set_xlim([xmin, xmax])

def style_ax(ax, title="", xlabel="", ylabel=""):
    """Aplica formato Dark Theme nativo a un eje de Matplotlib."""
    ax.set_facecolor(MPL_AXBG)
    ax.tick_params(colors=MPL_TEXT, labelsize=8)
    for sp in ax.spines.values():
        sp.set_edgecolor(BORDER_COL)
    if title:
        ax.set_title(title, color=ACCENT_CYAN, fontsize=9, pad=6)
    if xlabel:
        ax.set_xlabel(xlabel, color=TEXT_MUTED, fontsize=8)
    if ylabel:
        ax.set_ylabel(ylabel, color=TEXT_MUTED, fontsize=8)
    ax.grid(True, color=MPL_GRID, linestyle="--", linewidth=0.5, alpha=0.6)


# --- Funciones de Gráficos Rápidos ---


def chart_amplitude() -> str:
    is_max = getattr(engine_instance, "maximized_dual_chart", None) == "mon_raw_amp"
    bw, bh = (19.0, 5.6) if is_max else (9.5, 2.8)
    dyn_size = get_dynamic_figsize(bw, bh)
    fig, ax, is_new = get_cached_fig("amplitude", figsize=dyn_size)
    sig = engine_instance.amplitude_data
    n = len(sig)
    # Tiempo RELATIVO: siempre de 0 a la duración de la ventana
    # La señal siempre será visible; solo cambia la escala X si cambia analysis_window_sec
    duration_sec = engine_instance.analysis_window_sec
    t = np.linspace(0.0, duration_sec, n)

    if is_new or "line" not in cache.artists["amplitude"]:
        ax.clear()
        style_ax(
            ax, "Amplitud vs Tiempo (Streaming)", "Tiempo (s)", "Amplitud Baseband (V)"
        )
        (line,) = ax.plot(t, sig, color=ACCENT_CYAN, linewidth=0.9, alpha=0.85)
        cache.artists["amplitude"]["line"] = line
    else:
        line = cache.artists["amplitude"]["line"]
        line.set_data(t, sig)
        
    # El eje X siempre cubre exactamente la ventana de análisis actual
    cfg = engine_instance.charts_config["mon_raw_amp"]
    safe_set_ylim(ax, cfg["ymin"], cfg["ymax"])
    safe_set_xlim(ax, cfg["xmin"], cfg["xmax"])

    return fig_to_b64(fig)


def chart_spectrum() -> str:
    is_max = getattr(engine_instance, "maximized_dual_chart", None) == "mon_filt_spec"
    bw, bh = (19.0, 5.6) if is_max else (9.5, 2.8)
    dyn_size = get_dynamic_figsize(bw, bh)
    fig, ax, is_new = get_cached_fig("spectrum", figsize=dyn_size)
    spec = engine_instance.spectrum_data
    fc = engine_instance.center_freq
    fs = engine_instance.sample_rate / 1_000_000

    full_freq = np.linspace(fc - fs / 2, fc + fs / 2, len(spec))

    if is_new or "line" not in cache.artists["spectrum"]:
        ax.clear()
        style_ax(
            ax,
            "Espectro de Frecuencia (Señal Filtrada)",
            "Frecuencia (MHz)",
            "Potencia (dBFS)",
        )
        (line,) = ax.plot(full_freq, spec, color=ACCENT_GREEN, linewidth=1.0)
        hline = ax.axhline(
            y=engine_instance.db_noise_floor,
            color=ACCENT_AMBER,
            linestyle="--",
            linewidth=0.8,
            alpha=0.7,
            label="Piso de Ruido",
        )
        leg = ax.legend(
            loc="upper right", fontsize=7, facecolor=MPL_AXBG, edgecolor=BORDER_COL
        )
        cache.artists["spectrum"]["line"] = line
        cache.artists["spectrum"]["hline"] = hline
    else:
        line = cache.artists["spectrum"]["line"]
        hline = cache.artists["spectrum"]["hline"]
        
        line.set_data(full_freq, spec)
        
        # Actualizar piso de ruido dinámico sin regenerar leyenda
        nf = engine_instance.db_noise_floor
        hline.set_ydata([nf, nf])

    cfg = engine_instance.charts_config["mon_filt_spec"]
    safe_set_ylim(ax, cfg["ymin"], cfg["ymax"])
    safe_set_xlim(ax, cfg["xmin"], cfg["xmax"])
    return fig_to_b64(fig)


def chart_spectrum_raw() -> str:
    """Espectro FFT desde señal RAW (sin filtro MA) — exclusivo Tab 1."""
    is_max = getattr(engine_instance, "maximized_dual_chart", None) == "mon_raw_spec"
    bw, bh = (19.0, 5.6) if is_max else (9.5, 2.8)
    dyn_size = get_dynamic_figsize(bw, bh)
    fig, ax, is_new = get_cached_fig("spectrum_raw", figsize=dyn_size)
    spec = engine_instance.spectrum_raw_data
    fc = engine_instance.center_freq
    fs = engine_instance.sample_rate / 1_000_000

    full_freq = np.linspace(fc - fs / 2, fc + fs / 2, len(spec))

    if is_new or "line" not in cache.artists["spectrum_raw"]:
        ax.clear()
        style_ax(
            ax,
            "Espectro (Señal Original — Sin Filtrar)",
            "Frecuencia (MHz)",
            "Potencia (dBFS)",
        )
        (line,) = ax.plot(full_freq, spec, color=ACCENT_CYAN, linewidth=1.0)
        hline = ax.axhline(
            y=engine_instance.db_noise_floor_raw,
            color=ACCENT_AMBER,
            linestyle="--",
            linewidth=0.8,
            alpha=0.7,
            label="Piso de Ruido (RAW)",
        )
        leg = ax.legend(
            loc="upper right", fontsize=7, facecolor=MPL_AXBG, edgecolor=BORDER_COL
        )
        cache.artists["spectrum_raw"]["line"] = line
        cache.artists["spectrum_raw"]["hline"] = hline
    else:
        line = cache.artists["spectrum_raw"]["line"]
        hline = cache.artists["spectrum_raw"]["hline"]
        
        line.set_data(full_freq, spec)
        
        nf = engine_instance.db_noise_floor_raw
        hline.set_ydata([nf, nf])

    cfg = engine_instance.charts_config["mon_raw_spec"]
    safe_set_ylim(ax, cfg["ymin"], cfg["ymax"])
    safe_set_xlim(ax, cfg["xmin"], cfg["xmax"])
    return fig_to_b64(fig)


def chart_spectrogram() -> str:
    # El waterfall es pesado, aquí imshow es lo más rápido
    dyn_size = get_dynamic_figsize(19.0, 5.6)
    fig, ax, is_new = get_cached_fig("waterfall", figsize=dyn_size)
    data = np.roll(engine_instance.waterfall_data, -engine_instance.waterfall_idx, axis=0)
    fc = engine_instance.center_freq
    fs = engine_instance.sample_rate / 1_000_000
    # Safety check for empty buffer
    if data.size == 0:
        return fig_to_b64(fig)

    secs_per_line = engine_instance.analysis_window_sec # Ahora cada fila es el tiempo de análisis
    total_secs = engine_instance.waterfall_steps * secs_per_line

    if is_new or "im" not in cache.artists["waterfall"]:
        ax.clear()
        style_ax(ax, "Cascada Espectral (Waterfall)", "Frecuencia (MHz)", f"Tiempo (s)")
        ax.xaxis.get_major_formatter().set_useOffset(False)
        ax.xaxis.get_major_formatter().set_scientific(False)
        im = ax.imshow(
            data,
            aspect="auto",
            origin="lower",
            extent=[fc - fs / 2, fc + fs / 2, 0, total_secs],
            cmap="inferno",
            interpolation="nearest",
            vmin=engine_instance.db_min,
            vmax=engine_instance.db_max,
        )
        # Barra de color
        from mpl_toolkits.axes_grid1 import make_axes_locatable

        divider = make_axes_locatable(ax)
        cax = divider.append_axes("right", size="2%", pad=0.05)
        cbar = fig.colorbar(im, cax=cax)
        cbar.set_label("Potencia (dBFS)", fontsize=7, color=TEXT_MUTED)
        cbar.ax.tick_params(labelsize=6, colors=TEXT_MUTED)
        cbar.outline.set_edgecolor(BORDER_COL)
        cache.artists["waterfall"]["im"] = im
        cache.artists["waterfall"]["cbar"] = cbar
    else:
        im = cache.artists["waterfall"]["im"]
        im.set_data(data)
        
    cfg = engine_instance.charts_config["spec_wf"]
    xmin, xmax = cfg["xmin"], cfg["xmax"]
    if abs(xmax - xmin) < 1e-6:
        xmin, xmax = xmin - 0.5, xmax + 0.5
    
    im.set_extent([fc - fs / 2, fc + fs / 2, 0, total_secs])
    im.set_clim(cfg["ymin"], cfg["ymax"])
    if "cbar" in cache.artists["waterfall"]:
        cache.artists["waterfall"]["cbar"].update_normal(im)

    safe_set_xlim(ax, cfg["xmin"], cfg["xmax"])
    return fig_to_b64(fig)


def chart_histogram() -> str:
    dyn_size = get_dynamic_figsize(19.0, 5.6)
    fig, ax, is_new = get_cached_fig("histogram", figsize=dyn_size)
    samples = engine_instance.histogram_data

    # El histograma es difícil de actualizar vía set_data, lo regeneramos pero reusando la figura
    ax.clear()
    style_ax(ax, "Histograma Baseband", "Magnitud (Abs)", "Ocurrencia Relativa")

    if len(samples) > 2 and np.std(samples) > 0:
        ax.hist(samples, bins=50, density=True, color=ACCENT_CYAN, alpha=0.5)
        mu, std = np.mean(samples), np.std(samples)
        x = np.linspace(np.min(samples), np.max(samples), 100)
        gauss = (1 / (std * math.sqrt(2 * math.pi))) * np.exp(
            -0.5 * ((x - mu) / std) ** 2
        )
        ax.plot(x, gauss, color=ACCENT_GREEN, linewidth=1.5)

    cfg = engine_instance.charts_config["stat_hist"]
    safe_set_xlim(ax, cfg["xmin"], cfg["xmax"])

    # Sincronizar ymin/ymax: auto detecta el rango real de la curva gaussiana
    if cfg.get("auto_y", True):
        y_lo, y_hi = ax.get_ylim()
        cfg["ymin"] = round(y_lo, 5)
        cfg["ymax"] = round(y_hi, 5)
    else:
        safe_set_ylim(ax, cfg["ymin"], cfg["ymax"])

    # Sincronizar xmin/xmax cuando auto_x está activo
    if cfg.get("auto_x", True):
        x_lo, x_hi = ax.get_xlim()
        cfg["xmin"] = round(x_lo, 5)
        cfg["xmax"] = round(x_hi, 5)

    return fig_to_b64(fig)


def chart_signal_time() -> str:
    dyn_size = get_dynamic_figsize(19.0, 5.6)
    fig, ax, is_new = get_cached_fig("signal_time", figsize=dyn_size)
    raw = engine_instance.amplitude_data.astype(np.float32)
    n = len(raw)
    # Tiempo absoluto en segundos
    elapsed_sec = engine_instance.elapsed_samples / engine_instance.sample_rate
    # Ventana de tiempo mostrada (depende del tiempo de análisis)
    duration_sec = engine_instance.analysis_window_sec
    t = np.linspace(elapsed_sec - duration_sec, elapsed_sec, n)

    if is_new or "line_i" not in cache.artists["signal_time"]:
        ax.clear()
        style_ax(ax, "Señal en el Tiempo (I / Q)", "Tiempo (s)", "Amplitud (V)")
        (li,) = ax.plot(t, raw, color=ACCENT_CYAN, linewidth=0.8, label="I")
        (lq,) = ax.plot(
            t, np.roll(raw, n // 4), color=ACCENT_GREEN, linewidth=0.8, label="Q"
        )
        cache.artists["signal_time"]["line_i"] = li
        cache.artists["signal_time"]["line_q"] = lq
    else:
        cache.artists["signal_time"]["line_i"].set_data(t, raw)
        cache.artists["signal_time"]["line_q"].set_data(t, np.roll(raw, n // 4))

    # Sincronizar con charts_config igual que los demás
    cfg = engine_instance.charts_config["mon_raw_amp"]
    safe_set_ylim(ax, cfg["ymin"], cfg["ymax"])
    safe_set_xlim(ax, cfg["xmin"], cfg["xmax"])
    return fig_to_b64(fig)


def chart_power_time() -> str:
    dyn_size = get_dynamic_figsize(19.0, 5.6)
    fig, ax, is_new = get_cached_fig("power_time", figsize=dyn_size)
    written = engine_instance.power_samples_written
    data_len = len(engine_instance.power_time_data)
    
    if written == 0:
        pwr = np.array([-100.0])
    elif written < data_len:
        # Aún no se ha llenado el buffer una vez: los datos van de 0 a written
        pwr = engine_instance.power_time_data[:written]
    else:
        # Buffer circular lleno: rotar para que el dato más antiguo esté en t=0
        idx = written % data_len
        pwr = np.roll(engine_instance.power_time_data, -idx)
    
    n = len(pwr)
    # Cada muestra en power_time_data ahora representa 1 ventana de análisis
    batch_dur = engine_instance.analysis_window_sec
    t = np.arange(n) * batch_dur

    if is_new or "line" not in cache.artists["power_time"]:
        ax.clear()
        style_ax(ax, "Potencia vs. Tiempo", "Tiempo (s)", "Potencia (dBFS)")
        (line,) = ax.plot(t, pwr, color=ACCENT_AMBER, linewidth=1.0)
        hline = ax.axhline(
            y=engine_instance.db_noise_floor,
            color=ACCENT_RED,
            linestyle="--",
            linewidth=0.8,
            alpha=0.7,
            label="Piso de Ruido",
        )
        leg = ax.legend(
            loc="upper right", fontsize=7, facecolor=MPL_AXBG, edgecolor=BORDER_COL
        )
        cache.artists["power_time"]["line"] = line
        cache.artists["power_time"]["hline"] = hline
    else:
        line = cache.artists["power_time"]["line"]
        hline = cache.artists["power_time"]["hline"]
        
        line.set_data(t, pwr)
        
        nf = engine_instance.db_noise_floor
        hline.set_ydata([nf, nf])
        
    cfg = engine_instance.charts_config["pow_time"]
    # Eje X: Mostrar el historial acumulado (crece hasta el máximo del buffer)
    x_max = max(1.0, float(t[-1]))
    safe_set_xlim(ax, 0.0, x_max)
    
    # Eje Y: Auto-ajuste dinámico o manual
    safe_set_ylim(ax, cfg["ymin"], cfg["ymax"])

    return fig_to_b64(fig)


def chart_freq_snr() -> str:
    dyn_size = get_dynamic_figsize(19.0, 5.6)
    fig, ax, is_new = get_cached_fig("freq_snr", figsize=dyn_size)
    snr = engine_instance.snr_data
    fc, fs = engine_instance.center_freq, engine_instance.sample_rate / 1e6
    full_freq = np.linspace(fc - fs / 2, fc + fs / 2, len(snr))

    if is_new or "line" not in cache.artists["freq_snr"]:
        ax.clear()
        style_ax(ax, "SNR vs. Frecuencia", "Frecuencia (MHz)", "SNR (dB)")
        (line,) = ax.plot(full_freq, snr, color="#1f77b4", linewidth=1.0)
        ax.axhline(
            y=6,
            color=ACCENT_RED,
            linestyle="--",
            linewidth=0.8,
            alpha=0.7,
            label="Umbral 6 dB",
        )
        ax.legend(
            loc="upper right", fontsize=7, facecolor=MPL_AXBG, edgecolor=BORDER_COL
        )
        cache.artists["freq_snr"]["line"] = line
    else:
        line = cache.artists["freq_snr"]["line"]
        line.set_data(full_freq, snr)
        
    cfg = engine_instance.charts_config["snr_freq"]
    safe_set_ylim(ax, cfg["ymin"], cfg["ymax"])
    safe_set_xlim(ax, cfg["xmin"], cfg["xmax"])
    return fig_to_b64(fig)


def chart_algo_placeholder() -> str:
    # Este no importa mucho que sea rápido
    fig = Figure(figsize=(9.5, 4.5))
    ax = fig.subplots()
    fig.patch.set_facecolor(MPL_BG)
    ax.set_facecolor(MPL_AXBG)
    ax.text(0.5, 0.5, "Selecciona un método para calcular", color=MPL_TEXT, ha="center")
    style_ax(ax)
    return fig_to_b64(fig)


# Funciones pesadas (AR/Burg, CWT, MUSIC, ESPRIT) ahora con CACHÉ para velocidad 100ms
def chart_ar_spectrum(result: dict) -> str:
    dyn_size = get_dynamic_figsize(19.0, 5.6)
    fig, ax, is_new = get_cached_fig("ar_spectrum", figsize=dyn_size)
    freqs, psd = result["freqs"], result["psd"]

    if is_new or "line" not in cache.artists["ar_spectrum"]:
        ax.clear()
        style_ax(
            ax, "Espectro AR/Burg (Alta Resolución)", "Frecuencia (MHz)", "PSD (dB)"
        )
        (line,) = ax.plot(freqs, psd, color="#B380FF", linewidth=1.1, alpha=0.95)
        cache.artists["ar_spectrum"]["line"] = line
    else:
        line = cache.artists["ar_spectrum"]["line"]
        line.set_data(freqs, psd)
        safe_set_xlim(ax, freqs[0], freqs[-1])
        safe_set_ylim(ax, np.min(psd) - 5, np.max(psd) + 5)

    return fig_to_b64(fig)


def chart_cwt_map(result: dict) -> str:
    """
    Escalograma CWT 2D: Frecuencia (MHz) vs Tiempo (s).
    Usa el mismo patrón visual y de ejes que el waterfall FFT.
    """
    dyn_size = get_dynamic_figsize(19.0, 5.6)
    name = "cwt_map"
    fig, ax, is_new = get_cached_fig(name, figsize=dyn_size)

    matrix    = result["matrix"]          # (n_blocks × n_scales_vis)
    times_s   = result["times_s"]         # (n_blocks,)
    freqs_mhz = result["freqs_mhz"]       # (n_scales_vis,)
    v_min     = result.get("v_min",  float(np.percentile(matrix, 2)))
    v_max     = result.get("v_max",  float(np.percentile(matrix, 98)))
    if v_max <= v_min: v_max = v_min + 20.0
    fc_hi = engine_instance.center_freq
    history_sec = engine_instance.waterfall_history_sec

    f0 = freqs_mhz[0] if len(freqs_mhz) > 0 else fc_hi - 1.0
    f1 = freqs_mhz[-1] if len(freqs_mhz) > 0 else fc_hi + 1.0

    if is_new or "im" not in cache.artists[name]:
        ax.clear()
        style_ax(ax, "Escalograma CWT/Morlet 2D", "Frecuencia (MHz)", "Tiempo (s)")
        ax.xaxis.get_major_formatter().set_useOffset(False)
        ax.xaxis.get_major_formatter().set_scientific(False)
        im = ax.imshow(
            matrix,
            aspect="auto", origin="lower",
            extent=[f0, f1, 0.0, history_sec],
            cmap="inferno",
            vmin=v_min, vmax=v_max,
            interpolation="nearest",
        )
        vline = ax.axvline(x=fc_hi, color=ACCENT_RED, linestyle="--",
                   linewidth=0.9, alpha=0.8, label=f"HI {fc_hi:.2f} MHz")
        legend = ax.legend(loc="upper right", fontsize=7,
                  facecolor=MPL_AXBG, edgecolor=BORDER_COL)

        from mpl_toolkits.axes_grid1 import make_axes_locatable
        divider = make_axes_locatable(ax)
        cax = divider.append_axes("right", size="2%", pad=0.05)
        cbar = fig.colorbar(im, cax=cax)
        cbar.set_label("PSD (dBm)", fontsize=7, color=TEXT_MUTED)
        cbar.ax.tick_params(labelsize=6, colors=TEXT_MUTED)
        cbar.outline.set_edgecolor(BORDER_COL)
        
        cache.artists[name]["im"] = im
        cache.artists[name]["vline"] = vline
        cache.artists[name]["legend"] = legend
        cache.artists[name]["cbar"] = cbar
        
        try:
            fig.tight_layout(pad=0.2)
        except:
            pass
    else:
        im = cache.artists[name]["im"]
        im.set_data(matrix)
        vline = cache.artists[name]["vline"]
        vline.set_xdata([fc_hi, fc_hi])
        vline.set_label(f"HI {fc_hi:.2f} MHz")
        legend = cache.artists[name]["legend"]
        legend.get_texts()[0].set_text(f"HI {fc_hi:.2f} MHz")

    ax.set_ylim([0.0, history_sec])
    im = cache.artists[name]["im"]
    im.set_extent([f0, f1, 0.0, history_sec])

    cfg = engine_instance.charts_config.get("spec_cwt", {})
    safe_set_xlim(ax, cfg["xmin"], cfg["xmax"])
    
    if cfg.get('auto_y', True):
        cfg["ymin"] = v_min
        cfg["ymax"] = v_max
        im.set_clim(v_min, v_max)
    else:
        im.set_clim(cfg["ymin"], cfg["ymax"])

    if "cbar" in cache.artists[name]:
        cache.artists[name]["cbar"].update_normal(im)

    return fig_to_b64(fig, dpi=96)


def chart_music_spectrum(result: dict) -> str:
    """Pseudo-espectro MUSIC o ESPRIT."""
    method = result.get("method", "MUSIC")
    name = "music_spectrum"
    dyn_size = get_dynamic_figsize(19.0, 5.6)
    fig, ax, is_new = get_cached_fig(name, figsize=dyn_size)
    freqs = result["freqs"]
    spec = result.get("music_spectrum", result.get("esprit_spectrum"))

    if is_new or "line" not in cache.artists[name]:
        ax.clear()
        style_ax(
            ax, f"Pseudo-Espectro {method}", "Frecuencia (MHz)", "Pseudo-potencia (dB)"
        )
        col = ACCENT_RED if "MUSIC" in method else "#FF80AB"
        (line,) = ax.plot(freqs, spec, color=col, linewidth=1.2)
        cache.artists[name]["line"] = line
    else:
        line = cache.artists[name]["line"]
        line.set_data(freqs, spec)
        safe_set_xlim(ax, freqs[0], freqs[-1])
        safe_set_ylim(ax, np.min(spec) - 2, np.max(spec) + 2)

    return fig_to_b64(fig)


def chart_amplitude_ma() -> str:
    """Gráfica de amplitud post-Moving Average para comparación con la señal cruda."""
    is_max = getattr(engine_instance, "maximized_dual_chart", None) == "mon_filt_amp"
    bw, bh = (19.0, 5.6) if is_max else (9.5, 2.8)
    dyn_size = get_dynamic_figsize(bw, bh)
    fig, ax, is_new = get_cached_fig("amplitude_ma", figsize=dyn_size)
    sig = engine_instance.amplitude_ma_data
    n = len(sig)

    duration_sec = engine_instance.analysis_window_sec
    t = np.linspace(0.0, duration_sec, n)

    if is_new or "line" not in cache.artists["amplitude_ma"]:
        ax.clear()
        style_ax(
            ax,
            f"Amplitud Filtrada — MA ({int(engine_instance.moving_avg_samples)} muestras)",
            "Tiempo (s)",
            "Amplitud (V)",
        )
        (line,) = ax.plot(t, sig, color=ACCENT_AMBER, linewidth=0.9, alpha=0.9)
        cache.artists["amplitude_ma"]["line"] = line
    else:
        line = cache.artists["amplitude_ma"]["line"]
        line.set_data(t, sig)
        ax.set_title(
            f"Amplitud Filtrada — MA ({int(engine_instance.moving_avg_samples)} muestras)",
            color=ACCENT_CYAN,
            fontsize=9,
            pad=6,
        )
    # El eje X siempre cubre exactamente la ventana de análisis actual
    cfg = engine_instance.charts_config["mon_filt_amp"]
    safe_set_ylim(ax, cfg["ymin"], cfg["ymax"])
    safe_set_xlim(ax, cfg["xmin"], cfg["xmax"])

    return fig_to_b64(fig)



def chart_welch_spectrum(result: dict) -> str:
    """Espectro Welch: reutiliza el mismo estilo que AR/Burg con clave de caché propia."""
    name = "welch_spectrum"
    dyn_size = get_dynamic_figsize(19.0, 5.6)
    fig, ax, is_new = get_cached_fig(name, figsize=dyn_size)
    freqs, psd = result["freqs"], result["psd"]
    n_seg = result.get("n_segments", "?")

    if is_new or "line" not in cache.artists[name]:
        ax.clear()
        style_ax(
            ax, f"Espectro de Welch ({n_seg} segmentos)", "Frecuencia (MHz)", "PSD (dB)"
        )
        (line,) = ax.plot(freqs, psd, color="#FFD700", linewidth=1.1, alpha=0.95)
        cache.artists[name]["line"] = line
    else:
        line = cache.artists[name]["line"]
        line.set_data(freqs, psd)
        safe_set_xlim(ax, freqs[0], freqs[-1])
        safe_set_ylim(ax, np.min(psd) - 5, np.max(psd) + 5)
        ax.set_title(
            f"Espectro de Welch ({n_seg} segmentos)",
            color=ACCENT_CYAN,
            fontsize=9,
            pad=6,
        )

    return fig_to_b64(fig)


def chart_correlogram_spectrum(result: dict) -> str:
    """Espectro Correlograma (Wiener-Khinchin): clave de caché propia."""
    name = "correlogram_spectrum"
    dyn_size = get_dynamic_figsize(19.0, 5.6)
    fig, ax, is_new = get_cached_fig(name, figsize=dyn_size)
    freqs, psd = result["freqs"], result["psd"]
    max_lag = result.get("max_lag", "?")

    if is_new or "line" not in cache.artists[name]:
        ax.clear()
        style_ax(
            ax,
            f"Correlograma — lag máx {max_lag} muestras",
            "Frecuencia (MHz)",
            "PSD (dB)",
        )
        (line,) = ax.plot(freqs, psd, color="#40E0D0", linewidth=1.1, alpha=0.95)
        cache.artists[name]["line"] = line
    else:
        line = cache.artists[name]["line"]
        line.set_data(freqs, psd)
        safe_set_xlim(ax, freqs[0], freqs[-1])
        safe_set_ylim(ax, np.min(psd) - 5, np.max(psd) + 5)
        ax.set_title(
            f"Correlograma — lag máx {max_lag} muestras",
            color=ACCENT_CYAN,
            fontsize=9,
            pad=6,
        )

    return fig_to_b64(fig)


def chart_ar_spectrogram(result: dict) -> str:
    """
    Espectrograma 2D AR/Burg paramétrico.
    Usa el mismo patrón visual y de ejes que el waterfall FFT.
    """
    dyn_size = get_dynamic_figsize(19.0, 5.6)
    name = "ar_spectrogram"
    fig, ax, is_new = get_cached_fig(name, figsize=dyn_size)

    matrix    = result["matrix"]          # (n_segs × n_freqs_vis)
    times_s   = result["times_s"]         # (n_segs,)
    freqs_mhz = result["freqs_mhz"]       # (n_freqs_vis,)
    v_min     = result.get("v_min",  float(np.percentile(matrix, 1)))
    v_max     = result.get("v_max",  float(np.percentile(matrix, 99)))
    if v_max <= v_min: v_max = v_min + 20.0
    fc_hi = engine_instance.center_freq
    history_sec = engine_instance.waterfall_history_sec

    f0 = freqs_mhz[0] if len(freqs_mhz) > 0 else fc_hi - 1.0
    f1 = freqs_mhz[-1] if len(freqs_mhz) > 0 else fc_hi + 1.0

    if is_new or "im" not in cache.artists[name]:
        ax.clear()
        style_ax(ax, "Espectrograma AR/Burg 2D (Paramétrico)", "Frecuencia (MHz)", "Tiempo (s)")
        ax.xaxis.get_major_formatter().set_useOffset(False)
        ax.xaxis.get_major_formatter().set_scientific(False)
        im = ax.imshow(
            matrix,
            aspect="auto", origin="lower",
            extent=[f0, f1, 0.0, history_sec],
            cmap="inferno",
            vmin=v_min, vmax=v_max,
            interpolation="nearest",
        )
        vline = ax.axvline(x=fc_hi, color=ACCENT_RED, linestyle="--",
                   linewidth=0.9, alpha=0.8, label=f"HI {fc_hi:.2f} MHz")
        legend = ax.legend(loc="upper right", fontsize=7,
                  facecolor=MPL_AXBG, edgecolor=BORDER_COL)

        from mpl_toolkits.axes_grid1 import make_axes_locatable
        divider = make_axes_locatable(ax)
        cax = divider.append_axes("right", size="2%", pad=0.05)
        cbar = fig.colorbar(im, cax=cax)
        cbar.set_label("PSD (dBm)", fontsize=7, color=TEXT_MUTED)
        cbar.ax.tick_params(labelsize=6, colors=TEXT_MUTED)
        cbar.outline.set_edgecolor(BORDER_COL)
        
        cache.artists[name]["im"] = im
        cache.artists[name]["vline"] = vline
        cache.artists[name]["legend"] = legend
        cache.artists[name]["cbar"] = cbar
        
        try:
            fig.tight_layout(pad=0.2)
        except:
            pass
    else:
        im = cache.artists[name]["im"]
        im.set_data(matrix)
        vline = cache.artists[name]["vline"]
        vline.set_xdata([fc_hi, fc_hi])
        vline.set_label(f"HI {fc_hi:.2f} MHz")
        legend = cache.artists[name]["legend"]
        legend.get_texts()[0].set_text(f"HI {fc_hi:.2f} MHz")

    ax.set_ylim([0.0, history_sec])
    im = cache.artists[name]["im"]
    im.set_extent([f0, f1, 0.0, history_sec])

    cfg = engine_instance.charts_config.get("spec_ar", {})
    safe_set_xlim(ax, cfg["xmin"], cfg["xmax"])
    
    if cfg.get("auto_y", True):
        cfg["ymin"] = v_min
        cfg["ymax"] = v_max
        im.set_clim(v_min, v_max)
    else:
        im.set_clim(cfg["ymin"], cfg["ymax"])

    if "cbar" in cache.artists[name]:
        cache.artists[name]["cbar"].update_normal(im)

    return fig_to_b64(fig, dpi=96)


def chart_correlogram_spectrogram(result: dict) -> str:
    """
    Correlograma 2D — Blackman-Tukey (Wiener-Khinchin).
    """
    dyn_size = get_dynamic_figsize(19.0, 5.6)
    name = "corr_spectrogram"
    fig, ax, is_new = get_cached_fig(name, figsize=dyn_size)

    matrix    = result["matrix"]        # (n_segs × n_freqs)
    times_s   = result["times_s"]       # (n_segs,)
    freqs_mhz = result["freqs_mhz"]    # (n_freqs,)
    v_min     = result.get("v_min", float(np.percentile(matrix, 1)))
    v_max     = result.get("v_max", float(np.percentile(matrix, 99)))
    if v_max <= v_min: v_max = v_min + 20.0
    fc_hi     = engine_instance.center_freq
    history_sec = engine_instance.waterfall_history_sec

    f0 = freqs_mhz[0] if len(freqs_mhz) > 0 else fc_hi - 1.0
    f1 = freqs_mhz[-1] if len(freqs_mhz) > 0 else fc_hi + 1.0

    if is_new or "im" not in cache.artists[name]:
        ax.clear()
        style_ax(ax, "Correlograma 2D — Blackman-Tukey (Wiener-Khinchin)", "Frecuencia (MHz)", "Tiempo (s)")
        ax.xaxis.get_major_formatter().set_useOffset(False)
        ax.xaxis.get_major_formatter().set_scientific(False)
        im = ax.imshow(
            matrix,
            aspect="auto", origin="lower",
            extent=[f0, f1, 0.0, history_sec],
            cmap="inferno",
            vmin=v_min, vmax=v_max,
            interpolation="nearest",
        )
        vline = ax.axvline(x=fc_hi, color=ACCENT_RED, linestyle="--",
                   linewidth=0.9, alpha=0.8, label=f"HI {fc_hi:.2f} MHz")
        legend = ax.legend(loc="upper right", fontsize=7,
                  facecolor=MPL_AXBG, edgecolor=BORDER_COL)

        from mpl_toolkits.axes_grid1 import make_axes_locatable
        divider = make_axes_locatable(ax)
        cax = divider.append_axes("right", size="2%", pad=0.05)
        cbar = fig.colorbar(im, cax=cax)
        cbar.set_label("PSD (dBm)", fontsize=7, color=TEXT_MUTED)
        cbar.ax.tick_params(labelsize=6, colors=TEXT_MUTED)
        cbar.outline.set_edgecolor(BORDER_COL)
        
        cache.artists[name]["im"] = im
        cache.artists[name]["vline"] = vline
        cache.artists[name]["legend"] = legend
        cache.artists[name]["cbar"] = cbar
        
        try:
            fig.tight_layout(pad=0.2)
        except:
            pass
    else:
        im = cache.artists[name]["im"]
        im.set_data(matrix)
        vline = cache.artists[name]["vline"]
        vline.set_xdata([fc_hi, fc_hi])
        vline.set_label(f"HI {fc_hi:.2f} MHz")
        legend = cache.artists[name]["legend"]
        legend.get_texts()[0].set_text(f"HI {fc_hi:.2f} MHz")

    ax.set_ylim([0.0, history_sec])
    im = cache.artists[name]["im"]
    im.set_extent([f0, f1, 0.0, history_sec])

    cfg = engine_instance.charts_config.get("spec_corr", {})
    safe_set_xlim(ax, cfg["xmin"], cfg["xmax"])
    
    if cfg.get('auto_y', True):
        cfg["ymin"] = v_min
        cfg["ymax"] = v_max
        im.set_clim(v_min, v_max)
    else:
        im.set_clim(cfg["ymin"], cfg["ymax"])

    if "cbar" in cache.artists[name]:
        cache.artists[name]["cbar"].update_normal(im)

    return fig_to_b64(fig, dpi=96)


# ── Sincronización Automática e Hilo-Segura (Thread-Safe) de Matplotlib ───────
import threading
import types

mpl_lock = threading.Lock()

def make_synchronized(func):
    def wrapper(*args, **kwargs):
        with mpl_lock:
            return func(*args, **kwargs)
    wrapper.__name__ = func.__name__
    wrapper.__doc__ = func.__doc__
    return wrapper

# Decorar todas las funciones expuestas que comienzan con "chart_"
for name, value in list(globals().items()):
    if isinstance(value, types.FunctionType) and name.startswith("chart_"):
        globals()[name] = make_synchronized(value)

