"""
charts.py
Agrupa toda la lógica de ploteo con Matplotlib.
Usa una caché persistente de figuras para permitir refrescos de 10ms sin saturar la CPU.
"""

import math
import io
import base64
import matplotlib as mpl
mpl.use('Agg') # Backend ultra-rápido sin UI

# Optimizaciones extremas para gráficas muy densas (evita cuello de botella SVG)
mpl.rcParams['path.simplify'] = True
mpl.rcParams['path.simplify_threshold'] = 1.0  # Simplifica todo lo que caiga en el mismo pixel
mpl.rcParams['agg.path.chunksize'] = 10000

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
    
    is_fs = getattr(engine_instance, "chart_fullscreen_active", False)
    
    if is_fs:
        avail_h = win_h - 40
        avail_w = win_w - 40
    else:
        # Alto real del contenedor Flet (sin pestañas, header, footer)
        avail_h = win_h - 140
        
        # Ancho real del contenedor (sin panel derecho si está cerrado, estimamos 40px padding)
        is_collapsed = getattr(engine_instance, "is_config_collapsed", False)
        avail_w = win_w - 40 if is_collapsed else win_w - 340
    
    # Determinar qué fracción de pantalla ocupa esta gráfica según sus parámetros base
    # (19.0 y 5.6 eran los valores de pantalla completa originales)
    frac_w = base_width / 19.0
    frac_h = base_height / 5.6
    
    if is_fs:
        frac_w = 1.0
        frac_h = 1.0
    
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


def fig_to_b64(fig: Figure, dpi: int = 96) -> str:
    """Retorna Base64 SVG de alta fidelidad con ejes vectoriales y señales internas rasterizadas.
    Garantiza ejes y textos vectoriales 100% nítidos en Flet y una transmisión ultra-veloz."""
    buf = io.BytesIO()
    try:
        fig.tight_layout(pad=0.25)
    except:
        pass
    fig.savefig(buf, format="svg", facecolor=MPL_BG, edgecolor=MPL_BG)
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
    duration_sec = engine_instance.analysis_window_sec
    t = np.linspace(0.0, duration_sec, n)
    
    # Rango de tiempo absoluto para el título
    c = engine_instance.current_file_time if engine_instance.stream_mode == "file" else (engine_instance.elapsed_samples / engine_instance.sample_rate)
    start_t = max(0.0, c - duration_sec)
    time_str = f"[{start_t:.1f}s - {c:.1f}s]"

    if is_new or "line_i" not in cache.artists["amplitude"]:
        ax.clear()
        style_ax(
            ax, f"Amplitud vs Tiempo (Streaming) {time_str}", "Tiempo (s)", "Amplitud Baseband (V)"
        )
        (line_i,) = ax.plot(t, sig.real, color=ACCENT_CYAN, linewidth=engine_instance.chart_line_width, alpha=0.85, label="I (Real)", rasterized=True)
        (line_q,) = ax.plot(t, sig.imag, color="#E040FB", linewidth=engine_instance.chart_line_width, alpha=0.85, label="Q (Imaginario)", rasterized=True)
        ax.legend(loc="upper right", fontsize=7, facecolor=MPL_AXBG, edgecolor=BORDER_COL)
        cache.artists["amplitude"]["line_i"] = line_i
        cache.artists["amplitude"]["line_q"] = line_q
    else:
        line_i = cache.artists["amplitude"]["line_i"]
        line_q = cache.artists["amplitude"]["line_q"]
        line_i.set_linewidth(engine_instance.chart_line_width)
        line_q.set_linewidth(engine_instance.chart_line_width)
        line_i.set_data(t, sig.real)
        line_q.set_data(t, sig.imag)
        ax.set_title(f"Amplitud vs Tiempo (Streaming) {time_str}", color="#ECEFF1", fontsize=11, fontweight="bold", pad=12)
        
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

    # Rango de tiempo absoluto para el título
    c = engine_instance.current_file_time if engine_instance.stream_mode == "file" else (engine_instance.elapsed_samples / engine_instance.sample_rate)
    w = engine_instance.analysis_window_sec
    start_t = max(0.0, c - w)
    time_str = f"[{start_t:.1f}s - {c:.1f}s]"

    if is_new or "line" not in cache.artists["spectrum"]:
        ax.clear()
        style_ax(
            ax,
            f"Espectro de Frecuencia (Señal Filtrada) {time_str}",
            "Frecuencia (MHz)",
            "Potencia (dBFS)",
        )
        (line,) = ax.plot(full_freq, spec, color=ACCENT_GREEN, linewidth=engine_instance.chart_line_width, rasterized=True)
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
        line.set_linewidth(engine_instance.chart_line_width)
        hline = cache.artists["spectrum"]["hline"]
        
        line.set_data(full_freq, spec)
        
        # Actualizar piso de ruido dinámico sin regenerar leyenda
        nf = engine_instance.db_noise_floor
        hline.set_ydata([nf, nf])
        ax.set_title(f"Espectro de Frecuencia (Señal Filtrada) {time_str}", color="#ECEFF1", fontsize=11, fontweight="bold", pad=12)

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

    # Rango de tiempo absoluto para el título
    c = engine_instance.current_file_time if engine_instance.stream_mode == "file" else (engine_instance.elapsed_samples / engine_instance.sample_rate)
    w = engine_instance.analysis_window_sec
    start_t = max(0.0, c - w)
    time_str = f"[{start_t:.1f}s - {c:.1f}s]"

    if is_new or "line" not in cache.artists["spectrum_raw"]:
        ax.clear()
        style_ax(
            ax,
            f"Espectro (Señal Original — Sin Filtrar) {time_str}",
            "Frecuencia (MHz)",
            "Potencia (dBFS)",
        )
        (line,) = ax.plot(full_freq, spec, color=ACCENT_CYAN, linewidth=engine_instance.chart_line_width, rasterized=True)
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
        line.set_linewidth(engine_instance.chart_line_width)
        hline = cache.artists["spectrum_raw"]["hline"]
        
        line.set_data(full_freq, spec)
        
        nf = engine_instance.db_noise_floor_raw
        hline.set_ydata([nf, nf])
        ax.set_title(f"Espectro (Señal Original — Sin Filtrar) {time_str}", color="#ECEFF1", fontsize=11, fontweight="bold", pad=12)

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
            origin="upper",
            extent=[fc - fs / 2, fc + fs / 2, total_secs, 0],
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
    
    im.set_extent([fc - fs / 2, fc + fs / 2, total_secs, 0])
    ax.set_ylim([total_secs, 0])
    im.set_clim(cfg["ymin"], cfg["ymax"])
    if "cbar" in cache.artists["waterfall"]:
        cache.artists["waterfall"]["cbar"].update_normal(im)

    safe_set_xlim(ax, cfg["xmin"], cfg["xmax"])
    return fig_to_b64(fig)


def chart_histogram() -> str:
    dyn_size = get_dynamic_figsize(19.0, 5.6)
    fig, ax, is_new = get_cached_fig("histogram", figsize=dyn_size)
    samples = engine_instance.histogram_data

    mode = getattr(engine_instance, "histogram_mode", "Magnitud")
    ax.clear()

    # Calcular el rango de tiempo de este análisis para el título de la gráfica
    c = engine_instance.current_file_time if engine_instance.stream_mode == "file" else (engine_instance.elapsed_samples / engine_instance.sample_rate)
    w = engine_instance.analysis_window_sec
    start_t = max(0.0, c - w)
    time_str = f"[{start_t:.1f}s - {c:.1f}s]"

    if mode == "Magnitud":
        style_ax(ax, f"Distribución de Magnitud de Señal {time_str}", "Magnitud de la Señal", "Densidad de Probabilidad (PDF)")
    else:
        style_ax(ax, f"Distribución de Fase de Señal {time_str}", "Fase (Radianes)", "Densidad de Probabilidad (PDF)")

    if len(samples) > 2 and np.std(samples) > 0:
        if mode == "Magnitud":
            # Usar el máximo real de las muestras (+10% margen) para que los 100 bins se distribuyan correctamente
            max_val = float(np.max(samples))
            max_val = max_val * 1.1 if max_val > 0 else 0.1
            bins_range = np.linspace(0.0, max_val, 100)
        else:
            bins_range = np.linspace(-np.pi, np.pi, 100)
            
        # Se genera el histograma como área rellenada (stepfilled)
        counts, bins, _ = ax.hist(samples, bins=bins_range, color=ACCENT_CYAN, alpha=0.4, label="Datos Medidos", histtype='stepfilled', density=True)
        mu, std = np.mean(samples), np.std(samples)
        
        if mode == "Magnitud":
            x = np.linspace(0.0, max_val, 100)
        else:
            x = np.linspace(-np.pi, np.pi, 100)
        
        # Ecuación de la PDF Gaussiana estándar
        gauss = (1 / (std * math.sqrt(2 * math.pi))) * np.exp(
            -0.5 * ((x - mu) / std) ** 2
        )
        # Ya no se requiere escalar la gaussiana porque el histograma ahora es un PDF (density=True)
        ax.plot(x, gauss, color=ACCENT_GREEN, linewidth=1.5, label="Ideal Térmico (Gauss)")

        # NUEVO: Curva empírica real aproximada usando Kernel Density Estimation (KDE)
        try:
            from scipy.stats import gaussian_kde
            kde = gaussian_kde(samples)
            kde_vals = kde(x)
            ax.plot(x, kde_vals, color=ACCENT_AMBER, linewidth=1.5, linestyle="-", label="Real Observado (KDE)")
        except Exception:
            pass
        leg = ax.legend(loc="upper right", fontsize=8, facecolor=MPL_AXBG, edgecolor=BORDER_COL)
        for text in leg.get_texts():
            text.set_color("#ECEFF1")  # Color claro y visible en modo oscuro

    cfg_id = "stat_hist_mag" if mode == "Magnitud" else "stat_hist_fase"
    cfg = engine_instance.charts_config.get(cfg_id)
    if not cfg:
        cfg = {"auto_x": True, "auto_y": True, "xmin": 0.0, "xmax": 0.05, "ymin": 0.0, "ymax": 100.0}
        engine_instance.charts_config[cfg_id] = cfg

    # Si el checkbox de Auto Eje X está seleccionado (True), forzamos los límites que pidió el usuario
    if cfg.get("auto_x", True):
        if mode == "Magnitud":
            cfg["xmin"] = 0.0
            cfg["xmax"] = 0.05
        else:
            cfg["xmin"] = -round(np.pi, 5)
            cfg["xmax"] = round(np.pi, 5)

    safe_set_xlim(ax, cfg["xmin"], cfg["xmax"])

    # Sincronizar ymin/ymax para el eje Y de cuentas absolutas
    if cfg.get("auto_y", True):
        y_lo, y_hi = ax.get_ylim()
        cfg["ymin"] = round(y_lo, 5)
        cfg["ymax"] = round(y_hi, 5)
    else:
        safe_set_ylim(ax, cfg["ymin"], cfg["ymax"])

    # Sincronizar xmin/xmax para el eje X
    if not cfg.get("auto_x", True):
        safe_set_xlim(ax, cfg["xmin"], cfg["xmax"])

    return fig_to_b64(fig)



def chart_signal_time() -> str:
    dyn_size = get_dynamic_figsize(19.0, 5.6)
    fig, ax, is_new = get_cached_fig("signal_time", figsize=dyn_size)
    raw = engine_instance.amplitude_data
    n = len(raw)
    # Tiempo absoluto en segundos
    elapsed_sec = engine_instance.elapsed_samples / engine_instance.sample_rate
    # Ventana de tiempo mostrada (depende del tiempo de análisis)
    duration_sec = engine_instance.analysis_window_sec
    t = np.linspace(elapsed_sec - duration_sec, elapsed_sec, n)

    if is_new or "line_i" not in cache.artists["signal_time"]:
        ax.clear()
        style_ax(ax, "Señal en el Tiempo (I / Q)", "Tiempo (s)", "Amplitud (V)")
        (li,) = ax.plot(t, raw.real, color=ACCENT_CYAN, linewidth=0.8, label="I", rasterized=True)
        (lq,) = ax.plot(t, raw.imag, color="#E040FB", linewidth=0.8, label="Q", rasterized=True)
        ax.legend(loc="upper right", fontsize=7, facecolor=MPL_AXBG, edgecolor=BORDER_COL)
        cache.artists["signal_time"]["line_i"] = li
        cache.artists["signal_time"]["line_q"] = lq
    else:
        cache.artists["signal_time"]["line_i"].set_data(t, raw.real)
        cache.artists["signal_time"]["line_q"].set_data(t, raw.imag)

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


def chart_cwt_map(result: dict = None) -> str:
    """
    Escalograma CWT/Morlet — cascada continua.
    Lee la matriz circular cwt_wf_data del motor (igual que chart_spectrogram con waterfall_data).
    El parámetro 'result' se ignora; se mantiene por compatibilidad de firmas.
    """
    dyn_size = get_dynamic_figsize(19.0, 5.6)
    name = "cwt_map"
    fig, ax, is_new = get_cached_fig(name, figsize=dyn_size)

    # Leer buffer circular
    wf_data  = getattr(engine_instance, "cwt_wf_data", None)
    wf_idx   = getattr(engine_instance, "cwt_wf_idx",  0)
    if wf_data is None or wf_data.size == 0:
        return fig_to_b64(fig)

    data = np.roll(wf_data, -wf_idx, axis=0)   # fila 0 = más reciente

    fc      = engine_instance.center_freq
    fs_mhz  = engine_instance.sample_rate / 1_000_000
    f0, f1  = fc - fs_mhz / 2, fc + fs_mhz / 2
    secs_per_line = engine_instance.analysis_window_sec
    total_secs    = data.shape[0] * secs_per_line

    cfg = engine_instance.charts_config.get("spec_cwt", {})
    if cfg.get("auto_y", True):
        raw_vmin = float(np.percentile(data, 2))
        raw_vmax = float(np.percentile(data, 98))
        if raw_vmax <= raw_vmin:
            raw_vmax = raw_vmin + 20.0

        if "ema_vmin" not in cache.artists[name]:
            cache.artists[name]["ema_vmin"] = raw_vmin
            cache.artists[name]["ema_vmax"] = raw_vmax
        else:
            _a = 0.15
            cache.artists[name]["ema_vmin"] = (1 - _a) * cache.artists[name]["ema_vmin"] + _a * raw_vmin
            cache.artists[name]["ema_vmax"] = (1 - _a) * cache.artists[name]["ema_vmax"] + _a * raw_vmax
        v_min = cache.artists[name]["ema_vmin"]
        v_max = cache.artists[name]["ema_vmax"]
        cfg["ymin"] = round(v_min, 3)
        cfg["ymax"] = round(v_max, 3)
    else:
        v_min = cfg.get("ymin", -100.0)
        v_max = cfg.get("ymax", -20.0)

    if is_new or "im" not in cache.artists[name]:
        ax.clear()
        style_ax(ax, "Escalograma CWT/Morlet 2D", "Frecuencia (MHz)", "Tiempo (s)")
        ax.xaxis.get_major_formatter().set_useOffset(False)
        ax.xaxis.get_major_formatter().set_scientific(False)
        im = ax.imshow(
            data, aspect="auto", origin="upper",
            extent=[f0, f1, total_secs, 0.0],
            cmap="inferno", vmin=v_min, vmax=v_max, interpolation="nearest",
        )
        vline = ax.axvline(x=fc, color=ACCENT_RED, linestyle="--",
                           linewidth=0.9, alpha=0.8, label=f"HI {fc:.2f} MHz")
        ax.legend(loc="upper right", fontsize=7, facecolor=MPL_AXBG, edgecolor=BORDER_COL)
        from mpl_toolkits.axes_grid1 import make_axes_locatable
        cax = make_axes_locatable(ax).append_axes("right", size="2%", pad=0.05)
        cbar = fig.colorbar(im, cax=cax)
        cbar.set_label("PSD (dB)", fontsize=7, color=TEXT_MUTED)
        cbar.ax.tick_params(labelsize=6, colors=TEXT_MUTED)
        cbar.outline.set_edgecolor(BORDER_COL)
        cache.artists[name]["im"]    = im
        cache.artists[name]["vline"] = vline
        cache.artists[name]["cbar"]  = cbar
        try: fig.tight_layout(pad=0.2)
        except: pass
    else:
        im    = cache.artists[name]["im"]
        vline = cache.artists[name]["vline"]
        im.set_data(data)
        vline.set_xdata([fc, fc])

    im.set_extent([f0, f1, total_secs, 0.0])
    ax.set_ylim([total_secs, 0.0])
    im.set_clim(v_min, v_max)
    if "cbar" in cache.artists[name]:
        cache.artists[name]["cbar"].update_normal(im)

    cfg = engine_instance.charts_config.get("spec_cwt", {})
    safe_set_xlim(ax, cfg.get("xmin", f0), cfg.get("xmax", f1))
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

    if is_new or "line_i" not in cache.artists["amplitude_ma"]:
        ax.clear()
        style_ax(
            ax,
            f"Amplitud Filtrada — MA ({int(engine_instance.moving_avg_samples)} muestras)",
            "Tiempo (s)",
            "Amplitud (V)",
        )
        (line_i,) = ax.plot(t, sig.real, color=ACCENT_GREEN, linewidth=0.9, alpha=0.9, label="I Filtrado", rasterized=True)
        (line_q,) = ax.plot(t, sig.imag, color=ACCENT_AMBER, linewidth=0.9, alpha=0.9, label="Q Filtrado", rasterized=True)
        ax.legend(loc="upper right", fontsize=7, facecolor=MPL_AXBG, edgecolor=BORDER_COL)
        cache.artists["amplitude_ma"]["line_i"] = line_i
        cache.artists["amplitude_ma"]["line_q"] = line_q
    else:
        line_i = cache.artists["amplitude_ma"]["line_i"]
        line_q = cache.artists["amplitude_ma"]["line_q"]
        line_i.set_data(t, sig.real)
        line_q.set_data(t, sig.imag)
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


def chart_ar_spectrogram(result: dict = None) -> str:
    """
    Espectrograma AR/Burg 2D — cascada continua.
    Lee la matriz circular ar_wf_data del motor.
    El parámetro 'result' se ignora; se mantiene por compatibilidad.
    """
    dyn_size = get_dynamic_figsize(19.0, 5.6)
    name = "ar_spectrogram"
    fig, ax, is_new = get_cached_fig(name, figsize=dyn_size)

    wf_data = getattr(engine_instance, "ar_wf_data",  None)
    wf_idx  = getattr(engine_instance, "ar_wf_idx",   0)
    if wf_data is None or wf_data.size == 0:
        return fig_to_b64(fig)

    data = np.roll(wf_data, -wf_idx, axis=0)

    fc      = engine_instance.center_freq
    fs_mhz  = engine_instance.sample_rate / 1_000_000
    f0, f1  = fc - fs_mhz / 2, fc + fs_mhz / 2
    secs_per_line = engine_instance.analysis_window_sec
    total_secs    = data.shape[0] * secs_per_line

    cfg = engine_instance.charts_config.get("spec_ar", {})
    if cfg.get("auto_y", True):
        raw_vmin = float(np.percentile(data, 2))
        raw_vmax = float(np.percentile(data, 98))
        if raw_vmax <= raw_vmin:
            raw_vmax = raw_vmin + 20.0

        if "ema_vmin" not in cache.artists[name]:
            cache.artists[name]["ema_vmin"] = raw_vmin
            cache.artists[name]["ema_vmax"] = raw_vmax
        else:
            _a = 0.15
            cache.artists[name]["ema_vmin"] = (1 - _a) * cache.artists[name]["ema_vmin"] + _a * raw_vmin
            cache.artists[name]["ema_vmax"] = (1 - _a) * cache.artists[name]["ema_vmax"] + _a * raw_vmax
        v_min = cache.artists[name]["ema_vmin"]
        v_max = cache.artists[name]["ema_vmax"]
        cfg["ymin"] = round(v_min, 3)
        cfg["ymax"] = round(v_max, 3)
    else:
        v_min = cfg.get("ymin", -100.0)
        v_max = cfg.get("ymax", -20.0)

    if is_new or "im" not in cache.artists[name]:
        ax.clear()
        style_ax(ax, "Espectrograma AR/Burg 2D (Paramétrico)", "Frecuencia (MHz)", "Tiempo (s)")
        ax.xaxis.get_major_formatter().set_useOffset(False)
        ax.xaxis.get_major_formatter().set_scientific(False)
        im = ax.imshow(
            data, aspect="auto", origin="upper",
            extent=[f0, f1, total_secs, 0.0],
            cmap="inferno", vmin=v_min, vmax=v_max, interpolation="nearest",
        )
        vline = ax.axvline(x=fc, color=ACCENT_RED, linestyle="--",
                           linewidth=0.9, alpha=0.8, label=f"HI {fc:.2f} MHz")
        ax.legend(loc="upper right", fontsize=7, facecolor=MPL_AXBG, edgecolor=BORDER_COL)
        from mpl_toolkits.axes_grid1 import make_axes_locatable
        cax = make_axes_locatable(ax).append_axes("right", size="2%", pad=0.05)
        cbar = fig.colorbar(im, cax=cax)
        cbar.set_label("PSD (dB)", fontsize=7, color=TEXT_MUTED)
        cbar.ax.tick_params(labelsize=6, colors=TEXT_MUTED)
        cbar.outline.set_edgecolor(BORDER_COL)
        cache.artists[name]["im"]    = im
        cache.artists[name]["vline"] = vline
        cache.artists[name]["cbar"]  = cbar
        try: fig.tight_layout(pad=0.2)
        except: pass
    else:
        im    = cache.artists[name]["im"]
        vline = cache.artists[name]["vline"]
        im.set_data(data)
        vline.set_xdata([fc, fc])

    im.set_extent([f0, f1, total_secs, 0.0])
    ax.set_ylim([total_secs, 0.0])
    im.set_clim(v_min, v_max)
    if "cbar" in cache.artists[name]:
        cache.artists[name]["cbar"].update_normal(im)

    cfg = engine_instance.charts_config.get("spec_ar", {})
    safe_set_xlim(ax, cfg.get("xmin", f0), cfg.get("xmax", f1))
    return fig_to_b64(fig, dpi=96)

def chart_correlogram_spectrogram(result: dict = None) -> str:
    """
    Correlograma 2D — cascada continua.
    Lee la matriz circular corr_wf_data del motor.
    El parámetro 'result' se ignora; se mantiene por compatibilidad.
    """
    dyn_size = get_dynamic_figsize(19.0, 5.6)
    name = "corr_spectrogram"
    fig, ax, is_new = get_cached_fig(name, figsize=dyn_size)

    wf_data = getattr(engine_instance, "corr_wf_data", None)
    wf_idx  = getattr(engine_instance, "corr_wf_idx",  0)
    if wf_data is None or wf_data.size == 0:
        return fig_to_b64(fig)

    data = np.roll(wf_data, -wf_idx, axis=0)

    fc      = engine_instance.center_freq
    fs_mhz  = engine_instance.sample_rate / 1_000_000
    f0, f1  = fc - fs_mhz / 2, fc + fs_mhz / 2
    secs_per_line = engine_instance.analysis_window_sec
    total_secs    = data.shape[0] * secs_per_line

    cfg = engine_instance.charts_config.get("spec_corr", {})
    if cfg.get("auto_y", True):
        raw_vmin = float(np.percentile(data, 2))
        raw_vmax = float(np.percentile(data, 98))
        if raw_vmax <= raw_vmin:
            raw_vmax = raw_vmin + 20.0

        if "ema_vmin" not in cache.artists[name]:
            cache.artists[name]["ema_vmin"] = raw_vmin
            cache.artists[name]["ema_vmax"] = raw_vmax
        else:
            _a = 0.15
            cache.artists[name]["ema_vmin"] = (1 - _a) * cache.artists[name]["ema_vmin"] + _a * raw_vmin
            cache.artists[name]["ema_vmax"] = (1 - _a) * cache.artists[name]["ema_vmax"] + _a * raw_vmax
        v_min = cache.artists[name]["ema_vmin"]
        v_max = cache.artists[name]["ema_vmax"]
        cfg["ymin"] = round(v_min, 3)
        cfg["ymax"] = round(v_max, 3)
    else:
        v_min = cfg.get("ymin", -100.0)
        v_max = cfg.get("ymax", -20.0)

    if is_new or "im" not in cache.artists[name]:
        ax.clear()
        style_ax(ax, "Correlograma 2D — Blackman-Tukey (Wiener-Khinchin)", "Frecuencia (MHz)", "Tiempo (s)")
        ax.xaxis.get_major_formatter().set_useOffset(False)
        ax.xaxis.get_major_formatter().set_scientific(False)
        im = ax.imshow(
            data, aspect="auto", origin="upper",
            extent=[f0, f1, total_secs, 0.0],
            cmap="inferno", vmin=v_min, vmax=v_max, interpolation="nearest",
        )
        vline = ax.axvline(x=fc, color=ACCENT_RED, linestyle="--",
                           linewidth=0.9, alpha=0.8, label=f"HI {fc:.2f} MHz")
        ax.legend(loc="upper right", fontsize=7, facecolor=MPL_AXBG, edgecolor=BORDER_COL)
        from mpl_toolkits.axes_grid1 import make_axes_locatable
        cax = make_axes_locatable(ax).append_axes("right", size="2%", pad=0.05)
        cbar = fig.colorbar(im, cax=cax)
        cbar.set_label("PSD (dB)", fontsize=7, color=TEXT_MUTED)
        cbar.ax.tick_params(labelsize=6, colors=TEXT_MUTED)
        cbar.outline.set_edgecolor(BORDER_COL)
        cache.artists[name]["im"]    = im
        cache.artists[name]["vline"] = vline
        cache.artists[name]["cbar"]  = cbar
        try: fig.tight_layout(pad=0.2)
        except: pass
    else:
        im    = cache.artists[name]["im"]
        vline = cache.artists[name]["vline"]
        im.set_data(data)
        vline.set_xdata([fc, fc])

    im.set_extent([f0, f1, total_secs, 0.0])
    ax.set_ylim([total_secs, 0.0])
    im.set_clim(v_min, v_max)
    if "cbar" in cache.artists[name]:
        cache.artists[name]["cbar"].update_normal(im)

    cfg = engine_instance.charts_config.get("spec_corr", {})
    safe_set_xlim(ax, cfg.get("xmin", f0), cfg.get("xmax", f1))
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

