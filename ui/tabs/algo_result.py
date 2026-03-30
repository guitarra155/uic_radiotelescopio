"""
tabs/algo_result.py
Pestaña única "🔬 Algoritmo DSP" — muestra el resultado del método
seleccionado en el panel derecho. Solo corre UN algoritmo a la vez.
"""

import flet as ft
from core.constants import *
from ui.components.shared import panel, border_all

_ALGO_META = {
    "AR/Burg": {
        "color": "#B380FF",
        "desc": (
            "Modelo Autorregresivo por método de Burg.\n"
            "Alta resolución espectral con pocas muestras.\n"
            "Ideal para señales CW estrechas."
        ),
    },
    "CWT/Morlet": {
        "color": "#00C8FF",
        "desc": (
            "Transformada Wavelet Continua con Morlet.\n"
            "Análisis tiempo-frecuencia simultáneo.\n"
            "Útil para señales transitorias o moduladas."
        ),
    },
    "Pseudo-MUSIC": {
        "color": "#FF4C4C",
        "desc": (
            "MUltiple SIgnal Classification.\n"
            "Resolución super-FFT mediante sub-espacio de ruido.\n"
            "Detecta frecuencias con gran precisión."
        ),
    },
    "ESPRIT": {
        "color": "#FF80AB",
        "desc": (
            "Estimation of Signal Parameters via\nRotational Invariance Techniques.\n"
            "Más eficiente que MUSIC para pocos componentes."
        ),
    },
}


def build_algo_result(page: ft.Page) -> ft.Control:
    from core.dsp_engine import engine_instance
    from ui.charts import chart_algo_placeholder

    # Imagen del resultado — inicia con placeholder válido
    img = ft.Image(
        src=chart_algo_placeholder(),
        fit=ft.BoxFit.CONTAIN,
        gapless_playback=True,
        border_radius=10,
        expand=True,
    )

    # Panel de info dinámico
    method_name   = ft.Text("—", color=ACCENT_CYAN, size=15,
                             weight=ft.FontWeight.BOLD)
    method_color_dot = ft.Container(width=12, height=12, border_radius=6,
                                    bgcolor=ACCENT_CYAN)
    method_desc   = ft.Text("—", color=TEXT_MUTED, size=10)
    status_txt    = ft.Text("Esperando stream...", color=TEXT_MUTED,
                            size=11, italic=True)

    def _update_meta(do_update: bool = True):
        m = engine_instance.algo_params.get("method", "AR/Burg")
        meta = _ALGO_META.get(m, {})
        method_name.value = m
        method_name.color = meta.get("color", ACCENT_CYAN)
        method_color_dot.bgcolor = meta.get("color", ACCENT_CYAN)
        method_desc.value = meta.get("desc", "")
        if do_update:
            try:
                if method_name.page: method_name.update()
                if method_color_dot.page: method_color_dot.update()
                if method_desc.page: method_desc.update()
            except Exception as e:
                print(f"Update Meta Error: {e}")

    _update_meta(do_update=False)  # Sólo asigna valores, no llama update()

    # Recibir resultado cuando el runner termina
    async def on_algo_ready(msg):
        if msg == "algo_method_changed":
            _update_meta()
            # Mostrar placeholder mientras se espera el próximo cálculo
            from ui.charts import chart_algo_placeholder as _ph
            img.src = _ph()
            status_txt.value = "Método cambiado — esperando recálculo..."
            status_txt.color = ACCENT_AMBER
            if img.page: img.update()
            if status_txt.page: status_txt.update()
            return

        if msg != "algo_results_ready":
            return

        b64 = engine_instance.algo_results.get("current")
        if b64 is None:
            return

        img.src = b64
        mth = engine_instance.algo_results.get("current_method", engine_instance.algo_params.get("method", "?"))
        status_txt.value = f"✓ {mth} actualizado"
        status_txt.color = ACCENT_GREEN

        try:
            if img.page: img.update()
            if status_txt.page: status_txt.update()
        except:
            pass

    page.pubsub.subscribe(on_algo_ready)

    # Borde superior del color del método actual (se actualiza vía on_algo_ready)
    chart_border = ft.Border(
        top=ft.BorderSide(2, "#B380FF"),
        right=ft.BorderSide(1, BORDER_COL),
        bottom=ft.BorderSide(1, BORDER_COL),
        left=ft.BorderSide(1, BORDER_COL),
    )

    chart_container = ft.Container(
        content=img,
        expand=True,
        bgcolor=PANEL_BG,
        border_radius=10,
        border=chart_border,
        padding=8,
    )

    side = panel(
        width=260,
        padding_val=14,
        content=ft.Column([
            ft.Row([method_color_dot, method_name], spacing=8),
            ft.Divider(color=BORDER_COL, height=10),
            ft.Text("Descripción:", color=TEXT_MUTED, size=10),
            method_desc,
            ft.Divider(color=BORDER_COL, height=10),
            ft.Text("Estado:", color=TEXT_MUTED, size=10),
            status_txt,
            ft.Divider(color=BORDER_COL, height=10),
            ft.Text(
                "El método se selecciona en el\n"
                "panel derecho → 🔬 Algoritmos DSP.\n\n"
                "Solo corre UN algoritmo a la vez\n"
                "para optimizar el rendimiento.\n\n"
                "Se recalcula cada ~0.5 s con\nel stream activo.",
                color=TEXT_MUTED, size=9, italic=True,
            ),
        ], spacing=8),
    )

    return ft.Container(
        content=ft.Row([chart_container, side], spacing=10, expand=True),
        expand=True,
        padding=ft.Padding(left=14, top=14, right=14, bottom=14),
    )
