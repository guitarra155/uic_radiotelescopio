"""
ui/charts/monitoring.py
Gráficas del Tab 1 — Monitoreo Dual (Señal RAW vs Filtrada):
  - chart_amplitude      : Amplitud IQ raw (I y Q)
  - chart_amplitude_ma   : Amplitud post-Moving Average
  - chart_spectrum       : Espectro FFT señal filtrada
  - chart_spectrum_raw   : Espectro FFT señal original
"""

import numpy as np
import matplotlib as mpl

import core.constants as C
from core.dsp_engine import engine_instance
from ui.charts.cache import cache
from ui.charts.base import (
    get_dynamic_figsize, get_cached_fig, fig_to_b64,
    safe_set_ylim, safe_set_xlim, style_ax,
)


def chart_amplitude() -> str:
    is_max = getattr(engine_instance, "maximized_dual_chart", None) == "mon_raw_amp"
    bw, bh = (19.0, 5.6) if is_max else (9.5, 2.8)
    dyn_size = get_dynamic_figsize(bw, bh)
    fig, ax, is_new = get_cached_fig("amplitude", figsize=dyn_size)
    sig = engine_instance.amplitude_data
    n_raw = len(sig)
    duration_sec = engine_instance.analysis_window_sec

    cfg = engine_instance.charts_config["mon_raw_amp"]
    xmin = cfg.get("xmin", 0.0)
    xmax = cfg.get("xmax", duration_sec)

    xmin = max(0.0, min(xmin, duration_sec))
    xmax = max(xmin + 1e-6, min(xmax, duration_sec))

    idx_min = int((xmin / duration_sec) * n_raw) if duration_sec > 0 else 0
    idx_max = int((xmax / duration_sec) * n_raw) if duration_sec > 0 else n_raw
    idx_max = max(idx_min + 1, min(idx_max, n_raw))

    sig_slice = sig[idx_min:idx_max]
    n_slice = len(sig_slice)

    MAX_PTS = 1500
    if n_slice > MAX_PTS:
        step = n_slice // MAX_PTS
        sig_slice = sig_slice[::step]

    sig = sig_slice
    t = np.linspace(xmin, xmax, len(sig_slice))

    c = engine_instance.current_file_time if engine_instance.stream_mode == "file" \
        else (engine_instance.elapsed_samples / engine_instance.sample_rate)
    start_t = max(0.0, c - duration_sec)
    time_str = f"[{start_t:.1f}s - {c:.1f}s]"

    if is_new or "line_i" not in cache.artists["amplitude"]:
        ax.clear()
        style_ax(ax, f"Amplitud vs Tiempo (Streaming) {time_str}", "Tiempo (s)", "Amplitud Baseband (V)")
        (line_i,) = ax.plot(t, sig.real, color=C.ACCENT_CYAN, linewidth=engine_instance.chart_line_width,
                            alpha=0.85, label="I (Real)", rasterized=True)
        (line_q,) = ax.plot(t, sig.imag, color=C.COLOR_PINK, linewidth=engine_instance.chart_line_width,
                            alpha=0.85, label="Q (Imaginario)", rasterized=True)
        ax.legend(loc="upper right", fontsize=7, facecolor=C.MPL_AXBG, edgecolor=C.BORDER_COL, labelcolor=C.MPL_TEXT)
        cache.artists["amplitude"]["line_i"] = line_i
        cache.artists["amplitude"]["line_q"] = line_q
    else:
        line_i = cache.artists["amplitude"]["line_i"]
        line_q = cache.artists["amplitude"]["line_q"]
        line_i.set_linewidth(engine_instance.chart_line_width)
        line_q.set_linewidth(engine_instance.chart_line_width)
        line_i.set_data(t, sig.real)
        line_q.set_data(t, sig.imag)
        ax.set_title(f"Amplitud vs Tiempo (Streaming) {time_str}", color=C.ACCENT_CYAN, fontsize=9, pad=6)

    safe_set_ylim(ax, cfg["ymin"], cfg["ymax"])
    safe_set_xlim(ax, cfg["xmin"], cfg["xmax"])

    x_span = abs(cfg["xmax"] - cfg["xmin"])
    if x_span < 0.01:
        ax.xaxis.set_major_formatter(mpl.ticker.ScalarFormatter(useMathText=True))
        ax.ticklabel_format(axis='x', style='sci', scilimits=(-3, 3))
    else:
        ax.xaxis.set_major_formatter(mpl.ticker.ScalarFormatter(useMathText=False))
        ax.ticklabel_format(axis='x', style='plain')

    return fig_to_b64(fig)


def chart_amplitude_ma() -> str:
    """Gráfica de amplitud post-Moving Average para comparación con la señal cruda."""
    is_max = getattr(engine_instance, "maximized_dual_chart", None) == "mon_filt_amp"
    bw, bh = (19.0, 5.6) if is_max else (9.5, 2.8)
    dyn_size = get_dynamic_figsize(bw, bh)
    fig, ax, is_new = get_cached_fig("amplitude_ma", figsize=dyn_size)
    sig = engine_instance.amplitude_ma_data
    n_raw = len(sig)
    duration_sec = engine_instance.analysis_window_sec

    cfg = engine_instance.charts_config["mon_filt_amp"]
    xmin = cfg.get("xmin", 0.0)
    xmax = cfg.get("xmax", duration_sec)

    xmin = max(0.0, min(xmin, duration_sec))
    xmax = max(xmin + 1e-6, min(xmax, duration_sec))

    idx_min = int((xmin / duration_sec) * n_raw) if duration_sec > 0 else 0
    idx_max = int((xmax / duration_sec) * n_raw) if duration_sec > 0 else n_raw
    idx_max = max(idx_min + 1, min(idx_max, n_raw))

    sig_slice = sig[idx_min:idx_max]
    MAX_PTS = 1500
    if len(sig_slice) > MAX_PTS:
        step = len(sig_slice) // MAX_PTS
        sig_slice = sig_slice[::step]

    sig = sig_slice
    t = np.linspace(xmin, xmax, len(sig_slice))

    c = engine_instance.current_file_time if engine_instance.stream_mode == "file" \
        else (engine_instance.elapsed_samples / engine_instance.sample_rate)
    w = engine_instance.analysis_window_sec
    start_t = max(0.0, c - w)
    time_str = f"[{start_t:.1f}s - {c:.1f}s]"

    if is_new or "line_i" not in cache.artists["amplitude_ma"]:
        ax.clear()
        style_ax(
            ax,
            f"Amplitud Filtrada — MA ({int(engine_instance.moving_avg_samples)} muestras) {time_str}",
            "Tiempo (s)", "Amplitud (V)",
        )
        (line_i,) = ax.plot(t, sig.real, color=C.ACCENT_GREEN, linewidth=engine_instance.chart_line_width,
                            alpha=0.9, label="I Filtrado", rasterized=True)
        (line_q,) = ax.plot(t, sig.imag, color=C.ACCENT_AMBER, linewidth=engine_instance.chart_line_width,
                            alpha=0.9, label="Q Filtrado", rasterized=True)
        ax.legend(loc="upper right", fontsize=7, facecolor=C.MPL_AXBG, edgecolor=C.BORDER_COL, labelcolor=C.MPL_TEXT)
        cache.artists["amplitude_ma"]["line_i"] = line_i
        cache.artists["amplitude_ma"]["line_q"] = line_q
    else:
        line_i = cache.artists["amplitude_ma"]["line_i"]
        line_q = cache.artists["amplitude_ma"]["line_q"]
        line_i.set_data(t, sig.real)
        line_q.set_data(t, sig.imag)
        line_i.set_linewidth(engine_instance.chart_line_width)
        line_q.set_linewidth(engine_instance.chart_line_width)
        ax.set_title(
            f"Amplitud Filtrada — MA ({int(engine_instance.moving_avg_samples)} muestras) {time_str}",
            color=C.ACCENT_CYAN, fontsize=9, pad=6,
        )

    safe_set_ylim(ax, cfg["ymin"], cfg["ymax"])
    safe_set_xlim(ax, cfg["xmin"], cfg["xmax"])

    x_span = abs(cfg["xmax"] - cfg["xmin"])
    if x_span < 0.01:
        ax.xaxis.set_major_formatter(mpl.ticker.ScalarFormatter(useMathText=True))
        ax.ticklabel_format(axis='x', style='sci', scilimits=(-3, 3))
    else:
        ax.xaxis.set_major_formatter(mpl.ticker.ScalarFormatter(useMathText=False))
        ax.ticklabel_format(axis='x', style='plain')

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

    c = engine_instance.current_file_time if engine_instance.stream_mode == "file" \
        else (engine_instance.elapsed_samples / engine_instance.sample_rate)
    w = engine_instance.analysis_window_sec
    start_t = max(0.0, c - w)
    time_str = f"[{start_t:.1f}s - {c:.1f}s]"

    if is_new or "line" not in cache.artists["spectrum"]:
        ax.clear()
        style_ax(ax, f"Espectro de Frecuencia (Señal Filtrada) {time_str}", "Frecuencia (MHz)", "Potencia (dBFS)")
        (line,) = ax.plot(full_freq, spec, color=C.ACCENT_GREEN, linewidth=engine_instance.chart_line_width, rasterized=True)
        hline = ax.axhline(y=engine_instance.db_noise_floor, color=C.ACCENT_AMBER, linestyle="--",
                           linewidth=0.8, alpha=0.7, label="Piso de Ruido")
        ax.legend(loc="upper right", fontsize=7, facecolor=C.MPL_AXBG, edgecolor=C.BORDER_COL, labelcolor=C.MPL_TEXT)
        cache.artists["spectrum"]["line"] = line
        cache.artists["spectrum"]["hline"] = hline
    else:
        line = cache.artists["spectrum"]["line"]
        line.set_linewidth(engine_instance.chart_line_width)
        hline = cache.artists["spectrum"]["hline"]
        line.set_data(full_freq, spec)
        nf = engine_instance.db_noise_floor
        hline.set_ydata([nf, nf])
        ax.set_title(f"Espectro de Frecuencia (Señal Filtrada) {time_str}", color=C.ACCENT_CYAN, fontsize=9, pad=6)

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

    c = engine_instance.current_file_time if engine_instance.stream_mode == "file" \
        else (engine_instance.elapsed_samples / engine_instance.sample_rate)
    w = engine_instance.analysis_window_sec
    start_t = max(0.0, c - w)
    time_str = f"[{start_t:.1f}s - {c:.1f}s]"

    if is_new or "line" not in cache.artists["spectrum_raw"]:
        ax.clear()
        style_ax(ax, f"Espectro (Señal Original — Sin Filtrar) {time_str}", "Frecuencia (MHz)", "Potencia (dBFS)")
        (line,) = ax.plot(full_freq, spec, color=C.ACCENT_CYAN, linewidth=engine_instance.chart_line_width, rasterized=True)
        hline = ax.axhline(y=engine_instance.db_noise_floor_raw, color=C.ACCENT_AMBER, linestyle="--",
                           linewidth=0.8, alpha=0.7, label="Piso de Ruido (RAW)")
        ax.legend(loc="upper right", fontsize=7, facecolor=C.MPL_AXBG, edgecolor=C.BORDER_COL, labelcolor=C.MPL_TEXT)
        cache.artists["spectrum_raw"]["line"] = line
        cache.artists["spectrum_raw"]["hline"] = hline
    else:
        line = cache.artists["spectrum_raw"]["line"]
        line.set_linewidth(engine_instance.chart_line_width)
        hline = cache.artists["spectrum_raw"]["hline"]
        line.set_data(full_freq, spec)
        nf = engine_instance.db_noise_floor_raw
        hline.set_ydata([nf, nf])
        ax.set_title(f"Espectro (Señal Original — Sin Filtrar) {time_str}", color=C.ACCENT_CYAN, fontsize=9, pad=6)

    cfg = engine_instance.charts_config["mon_raw_spec"]
    safe_set_ylim(ax, cfg["ymin"], cfg["ymax"])
    safe_set_xlim(ax, cfg["xmin"], cfg["xmax"])
    return fig_to_b64(fig)
