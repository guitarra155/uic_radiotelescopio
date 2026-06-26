"""
ui/charts/freq_snr.py
Gráficas del Tab 5 — SNR vs. Frecuencia:
  - chart_freq_snr : Curva SNR con umbral de 6 dB
"""

import numpy as np

from core.constants import *
from core.dsp_engine import engine_instance
from ui.charts.cache import cache
from ui.charts.base import (
    get_dynamic_figsize, get_cached_fig, fig_to_b64,
    safe_set_ylim, safe_set_xlim, style_ax,
)


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
        ax.axhline(y=6, color=ACCENT_RED, linestyle="--", linewidth=0.8, alpha=0.7, label="Umbral 6 dB")
        ax.legend(loc="upper right", fontsize=7, facecolor=MPL_AXBG, edgecolor=BORDER_COL, labelcolor='#ECEFF1')
        cache.artists["freq_snr"]["line"] = line
    else:
        line = cache.artists["freq_snr"]["line"]
        line.set_data(full_freq, snr)

    cfg = engine_instance.charts_config["snr_freq"]
    safe_set_ylim(ax, cfg["ymin"], cfg["ymax"])
    safe_set_xlim(ax, cfg["xmin"], cfg["xmax"])
    return fig_to_b64(fig)
