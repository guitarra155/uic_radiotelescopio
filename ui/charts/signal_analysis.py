"""
ui/charts/signal_analysis.py
Gráficas del Tab 4 — Potencia vs. Tiempo:
  - chart_power_time : Potencia acumulada con piso de ruido dinámico
"""

import numpy as np

import core.constants as C
from core.dsp_engine import engine_instance
from ui.charts.cache import cache
from ui.charts.base import (
    get_dynamic_figsize, get_cached_fig, fig_to_b64,
    safe_set_ylim, safe_set_xlim, style_ax,
)


def chart_power_time() -> str:
    dyn_size = get_dynamic_figsize(19.0, 5.6)
    fig, ax, is_new = get_cached_fig("power_time", figsize=dyn_size)
    written = engine_instance.power_samples_written
    data_len = len(engine_instance.power_time_data)

    if written == 0:
        pwr = np.array([-100.0])
    elif written < data_len:
        pwr = engine_instance.power_time_data[:written]
    else:
        idx = written % data_len
        pwr = np.roll(engine_instance.power_time_data, -idx)

    n = len(pwr)
    batch_dur = engine_instance.analysis_window_sec
    t = np.arange(n) * batch_dur

    if is_new or "line" not in cache.artists["power_time"]:
        ax.clear()
        style_ax(ax, "Potencia vs. Tiempo", "Tiempo (s)", "Potencia (dBm)")
        (line,) = ax.plot(t, pwr, color=C.ACCENT_AMBER, linewidth=1.0)
        hline = ax.axhline(
            y=engine_instance.db_noise_floor, color=C.ACCENT_RED,
            linestyle="--", linewidth=0.8, alpha=0.7, label="Piso de Ruido",
        )
        ax.legend(loc="upper right", fontsize=7, facecolor=C.MPL_AXBG, edgecolor=C.BORDER_COL, labelcolor=C.MPL_TEXT)
        cache.artists["power_time"]["line"] = line
        cache.artists["power_time"]["hline"] = hline
    else:
        line = cache.artists["power_time"]["line"]
        hline = cache.artists["power_time"]["hline"]
        line.set_data(t, pwr)
        nf = engine_instance.db_noise_floor
        hline.set_ydata([nf, nf])

    cfg = engine_instance.charts_config["pow_time"]

    if cfg.get("auto_x", True):
        x_max = max(1.0, float(t[-1]) if len(t) > 0 else 1.0)
        cfg["xmin"] = 0.0
        cfg["xmax"] = x_max
        safe_set_xlim(ax, 0.0, x_max)
    else:
        safe_set_xlim(ax, cfg["xmin"], cfg["xmax"])

    safe_set_ylim(ax, cfg["ymin"], cfg["ymax"])
    return fig_to_b64(fig)
