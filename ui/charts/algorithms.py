"""
ui/charts/algorithms.py
Gráficas de algoritmos DSP avanzados (Tab 6 — Algoritmo DSP):
  - chart_ar_spectrum           : AR/Burg — espectro paramétrico 1D
  - chart_welch_spectrum        : Welch — PSD por promediado de periodogramas
  - chart_correlogram_spectrum  : Correlograma — Wiener-Khinchin 1D

Para agregar un nuevo algoritmo:
  1. Implementar run_nuevo en core/advanced_dsp.py
  2. Añadir chart_nuevo aquí
  3. Registrar la entrada en core/algo_registry.py
"""

import numpy as np

import core.constants as C
from core.dsp_engine import engine_instance
from ui.charts.cache import cache
from ui.charts.base import (
    get_dynamic_figsize, get_cached_fig, fig_to_b64,
    safe_set_ylim, safe_set_xlim, style_ax,
)


def chart_ar_spectrum(result: dict) -> str:
    dyn_size = get_dynamic_figsize(19.0, 5.6)
    fig, ax, is_new = get_cached_fig("ar_spectrum", figsize=dyn_size)
    freqs, psd = result["freqs"], result["psd"]

    if is_new or "line" not in cache.artists["ar_spectrum"]:
        ax.clear()
        style_ax(ax, "Espectro AR/Burg (Alta Resolución)", "Frecuencia (MHz)", "PSD (dB)")
        (line,) = ax.plot(freqs, psd, color=C.COLOR_PURPLE, linewidth=1.1, alpha=0.95)
        cache.artists["ar_spectrum"]["line"] = line
    else:
        line = cache.artists["ar_spectrum"]["line"]
        line.set_data(freqs, psd)
        safe_set_xlim(ax, freqs[0], freqs[-1])
        safe_set_ylim(ax, np.min(psd) - 5, np.max(psd) + 5)

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
        style_ax(ax, f"Espectro de Welch ({n_seg} segmentos)", "Frecuencia (MHz)", "PSD (dB)")
        (line,) = ax.plot(freqs, psd, color=C.COLOR_GOLD, linewidth=1.1, alpha=0.95)
        cache.artists[name]["line"] = line
    else:
        line = cache.artists[name]["line"]
        line.set_data(freqs, psd)
        safe_set_xlim(ax, freqs[0], freqs[-1])
        safe_set_ylim(ax, np.min(psd) - 5, np.max(psd) + 5)
        ax.set_title(f"Espectro de Welch ({n_seg} segmentos)", color=C.ACCENT_CYAN, fontsize=9, pad=6)

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
        style_ax(ax, f"Correlograma — lag máx {max_lag} muestras", "Frecuencia (MHz)", "PSD (dB)")
        (line,) = ax.plot(freqs, psd, color="#40E0D0", linewidth=1.1, alpha=0.95)
        cache.artists[name]["line"] = line
    else:
        line = cache.artists[name]["line"]
        line.set_data(freqs, psd)
        safe_set_xlim(ax, freqs[0], freqs[-1])
        safe_set_ylim(ax, np.min(psd) - 5, np.max(psd) + 5)
        ax.set_title(f"Correlograma — lag máx {max_lag} muestras", color=C.ACCENT_CYAN, fontsize=9, pad=6)

    return fig_to_b64(fig)
