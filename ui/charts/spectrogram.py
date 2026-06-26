"""
ui/charts/spectrogram.py
Gráficas del Tab 2 — Espectrograma:
  - chart_spectrogram           : Waterfall (cascada espectral clásica)
  - chart_cwt_map               : Escalograma CWT/Morlet 2D
  - chart_ar_spectrogram        : Espectrograma AR/Burg 2D
  - chart_correlogram_spectrogram: Correlograma 2D (Blackman-Tukey)
"""

import numpy as np

from core.constants import *
from core.dsp_engine import engine_instance
from ui.charts.cache import cache
from ui.charts.base import (
    get_dynamic_figsize, get_cached_fig, fig_to_b64,
    safe_set_xlim, style_ax,
)


def _render_2d_waterfall(
    name: str,
    wf_data,
    wf_idx: int,
    cfg_key: str,
    title: str,
    default_cmap: str = "inferno",
) -> str:
    """
    Helper interno para los tres espectrogramas 2D con buffer circular:
    waterfall AR, CWT y Correlograma. Evita duplicación de la lógica
    de imshow, EMA, colorbar y update.
    """
    dyn_size = get_dynamic_figsize(19.0, 5.6)
    fig, ax, is_new = get_cached_fig(name, figsize=dyn_size)

    if wf_data is None or wf_data.size == 0:
        return fig_to_b64(fig)

    data = np.roll(wf_data, -wf_idx, axis=0).astype(np.float32)

    MAX_COLS = 1024
    if data.shape[1] > MAX_COLS:
        step = max(1, data.shape[1] // MAX_COLS)
        data = data[:, ::step]

    fc = engine_instance.center_freq
    fs_mhz = engine_instance.sample_rate / 1_000_000
    f0, f1 = fc - fs_mhz / 2, fc + fs_mhz / 2
    secs_per_line = engine_instance.analysis_window_sec
    total_secs = data.shape[0] * secs_per_line

    cfg = engine_instance.charts_config.get(cfg_key, {})
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
        style_ax(ax, title, "Frecuencia (MHz)", "Tiempo (s)")
        ax.xaxis.get_major_formatter().set_useOffset(False)
        ax.xaxis.get_major_formatter().set_scientific(False)
        im = ax.imshow(
            data, aspect="auto", origin="upper",
            extent=[f0, f1, total_secs, 0.0],
            cmap=default_cmap, vmin=v_min, vmax=v_max, interpolation="nearest",
        )
        vline = ax.axvline(x=fc, color=ACCENT_RED, linestyle="--",
                           linewidth=0.9, alpha=0.8, label=f"HI {fc:.2f} MHz")
        ax.legend(loc="upper right", fontsize=7, facecolor=MPL_AXBG, edgecolor=BORDER_COL, labelcolor='#ECEFF1')
        from mpl_toolkits.axes_grid1 import make_axes_locatable
        cax = make_axes_locatable(ax).append_axes("right", size="2%", pad=0.05)
        cbar = fig.colorbar(im, cax=cax)
        cbar.set_label("PSD (dB)", fontsize=7, color=TEXT_MUTED)
        cbar.ax.tick_params(labelsize=6, colors=TEXT_MUTED)
        cbar.outline.set_edgecolor(BORDER_COL)
        cache.artists[name]["im"] = im
        cache.artists[name]["vline"] = vline
        cache.artists[name]["cbar"] = cbar
        try:
            fig.tight_layout(pad=0.2)
        except Exception:
            pass
    else:
        im = cache.artists[name]["im"]
        vline = cache.artists[name]["vline"]
        im.set_data(data)
        vline.set_xdata([fc, fc])

    im.set_extent([f0, f1, total_secs, 0.0])
    ax.set_ylim([total_secs, 0.0])
    im.set_clim(v_min, v_max)
    if "cbar" in cache.artists[name]:
        cache.artists[name]["cbar"].update_normal(im)

    safe_set_xlim(ax, cfg.get("xmin", f0), cfg.get("xmax", f1))
    return fig_to_b64(fig, dpi=96)


def chart_spectrogram() -> str:
    """Waterfall clásico (cascada espectral)."""
    dyn_size = get_dynamic_figsize(19.0, 5.6)
    fig, ax, is_new = get_cached_fig("waterfall", figsize=dyn_size)
    data = np.roll(engine_instance.waterfall_data, -engine_instance.waterfall_idx, axis=0).astype(np.float32)

    if data.shape[1] > 1024:
        data = data[:, ::max(1, data.shape[1] // 1024)]

    fc = engine_instance.center_freq
    fs = engine_instance.sample_rate / 1_000_000

    if data.size == 0:
        return fig_to_b64(fig)

    secs_per_line = engine_instance.analysis_window_sec
    total_secs = engine_instance.waterfall_steps * secs_per_line

    if is_new or "im" not in cache.artists["waterfall"]:
        ax.clear()
        style_ax(ax, "Cascada Espectral (Waterfall)", "Frecuencia (MHz)", "Tiempo (s)")
        ax.xaxis.get_major_formatter().set_useOffset(False)
        ax.xaxis.get_major_formatter().set_scientific(False)
        im = ax.imshow(
            data, aspect="auto", origin="upper",
            extent=[fc - fs / 2, fc + fs / 2, total_secs, 0],
            cmap="inferno", interpolation="nearest",
            vmin=engine_instance.db_min, vmax=engine_instance.db_max,
        )
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


def chart_cwt_map(result: dict = None) -> str:
    """
    Escalograma CWT/Morlet — cascada continua.
    Lee la matriz circular cwt_wf_data del motor.
    El parámetro 'result' se ignora; se mantiene por compatibilidad de firmas.
    """
    wf_data = getattr(engine_instance, "cwt_wf_data", None)
    wf_idx = getattr(engine_instance, "cwt_wf_idx", 0)
    return _render_2d_waterfall(
        name="cwt_map",
        wf_data=wf_data,
        wf_idx=wf_idx,
        cfg_key="spec_cwt",
        title="Escalograma CWT/Morlet 2D",
    )


def chart_ar_spectrogram(result: dict = None) -> str:
    """
    Espectrograma AR/Burg 2D — cascada continua.
    Lee la matriz circular ar_wf_data del motor.
    El parámetro 'result' se ignora; se mantiene por compatibilidad.
    """
    wf_data = getattr(engine_instance, "ar_wf_data", None)
    wf_idx = getattr(engine_instance, "ar_wf_idx", 0)
    return _render_2d_waterfall(
        name="ar_spectrogram",
        wf_data=wf_data,
        wf_idx=wf_idx,
        cfg_key="spec_ar",
        title="Espectrograma AR/Burg 2D (Paramétrico)",
    )


def chart_correlogram_spectrogram(result: dict = None) -> str:
    """
    Correlograma 2D — cascada continua.
    Lee la matriz circular corr_wf_data del motor.
    El parámetro 'result' se ignora; se mantiene por compatibilidad.
    """
    wf_data = getattr(engine_instance, "corr_wf_data", None)
    wf_idx = getattr(engine_instance, "corr_wf_idx", 0)
    return _render_2d_waterfall(
        name="corr_spectrogram",
        wf_data=wf_data,
        wf_idx=wf_idx,
        cfg_key="spec_corr",
        title="Correlograma 2D — Blackman-Tukey (Wiener-Khinchin)",
    )
