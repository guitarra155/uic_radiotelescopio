"""
ui/charts/base.py
Funciones base compartidas por todos los módulos de chart:
  - get_dynamic_figsize   : calcula tamaño dinámico según ventana
  - get_cached_fig        : crea o recupera figura de la caché
  - fig_to_b64            : serializa una Figure a SVG Base64
  - safe_set_ylim         : set_ylim sin que Matplotlib se queje
  - safe_set_xlim         : set_xlim sin que Matplotlib se queje
  - style_ax              : aplica tema al eje según paleta activa
  - export_active_chart   : exporta la gráfica activa a PNG/SVG
  - clear_chart_cache     : limpia la caché de figuras al cambiar de tema
"""

import io
import os
import datetime
import base64
import numpy as np

import matplotlib as mpl
from matplotlib.figure import Figure

import core.constants as C
from core.dsp_engine import engine_instance
from ui.charts.cache import cache


# ─────────────────────────────────────────────────────────────────────────────
# Limpieza de caché (para cambio de tema)
# ─────────────────────────────────────────────────────────────────────────────

def clear_chart_cache():
    """Elimina todas las figuras en caché para forzar recreación con la nueva paleta."""
    for fig in cache.figs.values():
        try:
            import matplotlib.pyplot as plt
            plt.close(fig)
        except Exception:
            pass
    cache.figs.clear()
    cache.axes.clear()
    cache.artists.clear()


# ─────────────────────────────────────────────────────────────────────────────
# Exportación
# ─────────────────────────────────────────────────────────────────────────────

def export_active_chart(format_type='png'):
    idx = getattr(engine_instance, "active_tab", 0)
    chart_id = None
    if idx == 1:
        max_id = getattr(engine_instance, "maximized_dual_chart", None)
        if max_id:
            dual_map = {
                "mon_raw_spec":  "spectrum_raw",
                "mon_filt_spec": "spectrum",
                "mon_raw_amp":   "amplitude",
                "mon_filt_amp":  "amplitude_ma",
            }
            chart_id = dual_map.get(max_id)
        else:
            return None, "En Monitoreo Dual, maximiza una gráfica primero con el ícono [ ]."
    elif idx == 2:
        method_map = {
            "waterfall":       "waterfall",
            "cwt":             "cwt_map",
            "ar_burg_2d":      "ar_spectrogram",
            "correlogram_2d":  "corr_spectrogram",
        }
        chart_id = method_map.get(
            getattr(engine_instance, "active_spec_method", "waterfall"), "waterfall"
        )
    elif idx == 3:
        chart_id = "histogram"
    elif idx == 4:
        chart_id = "power_time"
    elif idx == 5:
        chart_id = "freq_snr"

    if not chart_id or chart_id not in cache.figs:
        return None, "No hay gráfica activa para exportar en esta pestaña."

    os.makedirs("Resultados_Datos", exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = os.path.join("Resultados_Datos", f"captura_{chart_id}_{ts}.{format_type}")

    fig = cache.figs[chart_id]
    try:
        fig.savefig(
            filepath, format=format_type, bbox_inches='tight',
            facecolor=fig.get_facecolor(), edgecolor='none', dpi=300,
        )
    except Exception as e:
        return None, f"Error al guardar: {e}"
    return filepath, None


# ─────────────────────────────────────────────────────────────────────────────
# Tamaño dinámico
# ─────────────────────────────────────────────────────────────────────────────

def get_dynamic_figsize(base_width=9.5, base_height=2.8):
    """Calcula un tamaño dinámico con aspect ratio PERFECTO según la ventana."""
    win_w = getattr(engine_instance, "window_width", 1280)
    win_h = getattr(engine_instance, "window_height", 720)

    is_fs = getattr(engine_instance, "chart_fullscreen_active", False)

    if is_fs:
        avail_h = win_h - 40
        avail_w = win_w - 40
    else:
        avail_h = win_h - 140
        is_collapsed = getattr(engine_instance, "is_config_collapsed", False)
        avail_w = win_w - 40 if is_collapsed else win_w - 340

    frac_w = base_width / 19.0
    frac_h = base_height / 5.6

    if is_fs:
        frac_w = 1.0
        frac_h = 1.0

    fig_w = (avail_w * frac_w) / 100.0
    fig_h = (avail_h * frac_h) / 100.0

    return (max(2.0, fig_w), max(1.5, fig_h))


# ─────────────────────────────────────────────────────────────────────────────
# Caché de figuras
# ─────────────────────────────────────────────────────────────────────────────

def get_cached_fig(name, figsize=(9.5, 3.0), is_3d=False):
    """Crea o recupera una figura de la caché para evitar sobrecoste de memoria."""
    if name not in cache.figs:
        fig = Figure(figsize=figsize, dpi=96)
        fig.patch.set_facecolor(C.MPL_BG)
        ax = fig.subplots()
        style_ax(ax)
        try:
            fig.tight_layout(pad=0.2)
        except Exception:
            pass
        cache.figs[name] = fig
        cache.axes[name] = ax
        cache.artists[name] = {}
        return fig, ax, True  # True = Recién creado

    fig = cache.figs[name]
    ax = cache.axes[name]

    current_size = fig.get_size_inches()
    if abs(current_size[0] - figsize[0]) > 0.1 or abs(current_size[1] - figsize[1]) > 0.1:
        fig.set_size_inches(figsize)
    return fig, ax, False


# ─────────────────────────────────────────────────────────────────────────────
# Serialización
# ─────────────────────────────────────────────────────────────────────────────

def fig_to_b64(fig: Figure, dpi: int = 96) -> str:
    """Retorna Base64 SVG de alta fidelidad con ejes vectoriales."""
    buf = io.BytesIO()
    try:
        fig.tight_layout(pad=0.25)
    except Exception:
        pass
    fig.savefig(buf, format="svg", facecolor=C.MPL_BG, edgecolor=C.MPL_BG)
    buf.seek(0)
    enc = base64.b64encode(buf.read()).decode()
    buf.close()
    return f"data:image/svg+xml;base64,{enc}"


# ─────────────────────────────────────────────────────────────────────────────
# Límites de ejes seguros
# ─────────────────────────────────────────────────────────────────────────────

def safe_set_ylim(ax, ymin, ymax, fallback_span=10.0):
    """Evita que Matplotlib se queje si ymin == ymax."""
    ymin, ymax = float(ymin), float(ymax)
    if ymin > ymax:
        ymin, ymax = ymax, ymin
    if abs(ymax - ymin) < 1e-9:
        ymin -= 5.0
        ymax += 5.0
    current_ymin, current_ymax = ax.get_ylim()
    if abs(current_ymin - ymin) > 1e-9 or abs(current_ymax - ymax) > 1e-9:
        ax.set_ylim([ymin, ymax])


def safe_set_xlim(ax, xmin, xmax, fallback_span=1.0):
    """Evita que Matplotlib se queje si xmin == xmax."""
    xmin, xmax = float(xmin), float(xmax)
    if xmin > xmax:
        xmin, xmax = xmax, xmin
    if abs(xmax - xmin) < 1e-15:
        xmin -= 0.5
        xmax += 0.5
    current_xmin, current_xmax = ax.get_xlim()
    if abs(current_xmin - xmin) > 1e-9 or abs(current_xmax - xmax) > 1e-9:
        ax.set_xlim([xmin, xmax])


# ─────────────────────────────────────────────────────────────────────────────
# Estilo dinámico de ejes (lee paleta activa)
# ─────────────────────────────────────────────────────────────────────────────

def style_ax(ax, title="", xlabel="", ylabel=""):
    """Aplica formato de tema activo a un eje de Matplotlib."""
    ax.set_facecolor(C.MPL_AXBG)
    ax.tick_params(colors=C.MPL_TEXT, labelsize=8)
    for sp in ax.spines.values():
        sp.set_edgecolor(C.BORDER_COL)
    if title:
        ax.set_title(title, color=C.ACCENT_CYAN, fontsize=9, pad=6)
    if xlabel:
        ax.set_xlabel(xlabel, color=C.TEXT_MUTED, fontsize=8)
    if ylabel:
        ax.set_ylabel(ylabel, color=C.TEXT_MUTED, fontsize=8)
    ax.grid(True, color=C.MPL_GRID, linestyle="--", linewidth=0.5, alpha=0.6)
