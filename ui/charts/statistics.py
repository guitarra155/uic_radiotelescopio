"""
ui/charts/statistics.py
Gráficas del Tab 3 — Histograma y Estadística:
  - chart_histogram  : Distribución de magnitud/fase con PDF Gaussiana y KDE
  - chart_signal_time: Señal en el tiempo I/Q (secundaria)
"""

import math
import numpy as np

from core.constants import *
from core.dsp_engine import engine_instance
from ui.charts.cache import cache
from ui.charts.base import (
    get_dynamic_figsize, get_cached_fig, fig_to_b64,
    safe_set_ylim, safe_set_xlim, style_ax,
)


def chart_histogram() -> str:
    dyn_size = get_dynamic_figsize(19.0, 5.6)
    fig, ax, is_new = get_cached_fig("histogram", figsize=dyn_size)
    samples = engine_instance.histogram_data

    mode = getattr(engine_instance, "histogram_mode", "Magnitud")
    ax.clear()

    c = engine_instance.current_file_time if engine_instance.stream_mode == "file" \
        else (engine_instance.elapsed_samples / engine_instance.sample_rate)
    w = engine_instance.analysis_window_sec
    start_t = max(0.0, c - w)
    time_str = f"[{start_t:.1f}s - {c:.1f}s]"

    if mode == "Magnitud":
        style_ax(ax, f"Distribución de Magnitud de Señal {time_str}",
                 "Magnitud de la Señal", "Densidad de Probabilidad (PDF)")
    else:
        style_ax(ax, f"Distribución de Fase de Señal {time_str}",
                 "Fase (Radianes)", "Densidad de Probabilidad (PDF)")

    if len(samples) > 2 and np.std(samples) > 0:
        if mode == "Magnitud":
            max_val = float(np.max(samples))
            max_val = max_val * 1.1 if max_val > 0 else 0.1
            bins_range = np.linspace(0.0, max_val, 100)
        else:
            bins_range = np.linspace(-np.pi, np.pi, 100)

        counts, bins, _ = ax.hist(
            samples, bins=bins_range, color=ACCENT_CYAN, alpha=0.4,
            label="Datos Medidos", histtype='stepfilled', density=True,
        )
        mu, std = np.mean(samples), np.std(samples)

        x = np.linspace(0.0, max_val, 100) if mode == "Magnitud" else np.linspace(-np.pi, np.pi, 100)

        gauss = (1 / (std * math.sqrt(2 * math.pi))) * np.exp(-0.5 * ((x - mu) / std) ** 2)
        ax.plot(x, gauss, color=ACCENT_GREEN, linewidth=1.5, label="Ideal Térmico (Gauss)")

        try:
            from scipy.stats import gaussian_kde
            kde = gaussian_kde(samples)
            kde_vals = kde(x)
            ax.plot(x, kde_vals, color=ACCENT_AMBER, linewidth=1.5, linestyle="-", label="Real Observado (KDE)")
        except Exception:
            pass

        leg = ax.legend(loc="upper right", fontsize=8, facecolor=MPL_AXBG, edgecolor=BORDER_COL, labelcolor='#ECEFF1')
        for text in leg.get_texts():
            text.set_color("#ECEFF1")

    cfg_id = "stat_hist_mag" if mode == "Magnitud" else "stat_hist_fase"
    cfg = engine_instance.charts_config.get(cfg_id)
    if not cfg:
        cfg = {"auto_x": True, "auto_y": True, "xmin": 0.0, "xmax": 0.05, "ymin": 0.0, "ymax": 100.0}
        engine_instance.charts_config[cfg_id] = cfg

    if cfg.get("auto_x", True):
        if mode == "Magnitud":
            cfg["xmin"] = 0.0
            cfg["xmax"] = 0.05
        else:
            cfg["xmin"] = -round(np.pi, 5)
            cfg["xmax"] = round(np.pi, 5)

    safe_set_xlim(ax, cfg["xmin"], cfg["xmax"])

    if cfg.get("auto_y", True):
        y_lo, y_hi = ax.get_ylim()
        cfg["ymin"] = round(y_lo, 5)
        cfg["ymax"] = round(y_hi, 5)
    else:
        safe_set_ylim(ax, cfg["ymin"], cfg["ymax"])

    if not cfg.get("auto_x", True):
        safe_set_xlim(ax, cfg["xmin"], cfg["xmax"])

    return fig_to_b64(fig)


def chart_signal_time() -> str:
    dyn_size = get_dynamic_figsize(19.0, 5.6)
    fig, ax, is_new = get_cached_fig("signal_time", figsize=dyn_size)
    raw = engine_instance.amplitude_data
    n = len(raw)
    elapsed_sec = engine_instance.elapsed_samples / engine_instance.sample_rate
    duration_sec = engine_instance.analysis_window_sec
    t = np.linspace(elapsed_sec - duration_sec, elapsed_sec, n)

    if is_new or "line_i" not in cache.artists["signal_time"]:
        ax.clear()
        style_ax(ax, "Señal en el Tiempo (I / Q)", "Tiempo (s)", "Amplitud (V)")
        (li,) = ax.plot(t, raw.real, color=ACCENT_CYAN, linewidth=0.8, label="I", rasterized=True)
        (lq,) = ax.plot(t, raw.imag, color="#E040FB", linewidth=0.8, label="Q", rasterized=True)
        ax.legend(loc="upper right", fontsize=7, facecolor=MPL_AXBG, edgecolor=BORDER_COL, labelcolor='#ECEFF1')
        cache.artists["signal_time"]["line_i"] = li
        cache.artists["signal_time"]["line_q"] = lq
    else:
        cache.artists["signal_time"]["line_i"].set_data(t, raw.real)
        cache.artists["signal_time"]["line_q"].set_data(t, raw.imag)

    cfg = engine_instance.charts_config["mon_raw_amp"]
    safe_set_ylim(ax, cfg["ymin"], cfg["ymax"])
    safe_set_xlim(ax, cfg["xmin"], cfg["xmax"])
    return fig_to_b64(fig)
