"""
tabs/monitoring_filtered.py
Pestaña 2 — Señal FILTRADA (post Moving Average).
Mismo layout que Tab 1 pero usando spectrum_data + amplitude_ma_data.
Desde esta pestaña en adelante TODO opera sobre señal filtrada.
"""

import flet as ft
from core.constants import *
from ui.charts import chart_amplitude_ma, chart_spectrum
from ui.components.shared import panel, border_all


def build_monitoring_filtered(page: ft.Page, key_state: dict) -> ft.Control:

    img_spec = ft.Image(
        src=chart_spectrum(),
        fit=ft.BoxFit.CONTAIN,
        gapless_playback=True,
        border_radius=8,
        expand=True,
    )
    img_amp = ft.Image(
        src=chart_amplitude_ma(),
        fit=ft.BoxFit.CONTAIN,
        gapless_playback=True,
        border_radius=8,
        expand=True,
    )

    is_rendering = [False]

    async def on_refresh(msg):
        if msg != "refresh_charts":
            return
        from core.dsp_engine import engine_instance

        if engine_instance.active_tab != 1:  # índice 1 = esta pestaña
            return
        if is_rendering[0]:
            return
        is_rendering[0] = True
        try:
            import asyncio

            spec_b64, amp_b64 = await asyncio.gather(
                asyncio.to_thread(chart_spectrum),
                asyncio.to_thread(chart_amplitude_ma),
            )
            img_spec.src = spec_b64
            img_amp.src = amp_b64
            img_spec.update()
            img_amp.update()
        finally:
            is_rendering[0] = False

    from core.dsp_engine import engine_instance

    def reset_defaults(e):
        engine_instance.reset_to_defaults()
        engine_instance.save_config()
        # No hace falta refrescar imagen inmediatamente, el loop lo hará.

    def on_zoom_scroll(e: ft.ScrollEvent):
        ctrl = key_state.get("ctrl", False)
        shift = key_state.get("shift", False)
        if not ctrl and not shift:
            return
        dir_ = 1 if e.scroll_delta_y > 0 else -1
        factor = 0.25 * dir_
        if ctrl:
            # Zoom en Eje Y (Amplitud y Espectro)
            s_amp = engine_instance.amp_max - engine_instance.amp_min
            engine_instance.amp_min -= s_amp * factor
            engine_instance.amp_max += s_amp * factor
            s_db = engine_instance.db_max - engine_instance.db_min
            engine_instance.db_min -= s_db * factor
            engine_instance.db_max += s_db * factor
            engine_instance.save_config()
        elif shift:
            # Zoom en Eje X (Frecuencia)
            s_f = engine_instance.f_max - engine_instance.f_min
            engine_instance.f_min -= s_f * factor
            engine_instance.f_max += s_f * factor
            engine_instance.save_config()

    def _chart_box(img, accent=BORDER_COL):
        return ft.Container(
            content=ft.GestureDetector(
                mouse_cursor=ft.MouseCursor.ZOOM_IN,
                on_scroll=on_zoom_scroll,
                drag_interval=0,
                content=img,
            ),
            expand=True,
            bgcolor=PANEL_BG,
            border_radius=8,
            border=ft.Border(
                top=ft.BorderSide(2, accent),
                right=ft.BorderSide(1, BORDER_COL),
                bottom=ft.BorderSide(1, BORDER_COL),
                left=ft.BorderSide(1, BORDER_COL),
            ),
            padding=4,
        )

    graphs = ft.Column(
        [
            ft.Container(content=_chart_box(img_spec, ACCENT_GREEN), expand=1),
            ft.Container(content=_chart_box(img_amp, ACCENT_AMBER), expand=1),
        ],
        expand=True,
        spacing=10,
        scroll=ft.ScrollMode.AUTO,
    )

    side = panel(
        width=230,
        content=ft.Column(
            [
                ft.Text(
                    "🔍  Señal Filtrada",
                    color=ACCENT_GREEN,
                    size=14,
                    weight=ft.FontWeight.BOLD,
                ),
                ft.Divider(color=BORDER_COL, height=10),
                ft.Row(
                    [
                        ft.Text("Auto-detección:", color=TEXT_MUTED, size=10),
                        ft.TextButton(
                            "Restaurar",
                            on_click=reset_defaults,
                            style=ft.ButtonStyle(color=ACCENT_CYAN),
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.Divider(color=BORDER_COL, height=8),
                ft.Text(
                    "Moving Average activo",
                    color=ACCENT_AMBER,
                    size=11,
                    weight=ft.FontWeight.W_600,
                ),
                ft.Divider(color=BORDER_COL, height=8),
                ft.Text("Espectro:", color=TEXT_MUTED, size=10),
                ft.Row(
                    [
                        ft.Container(
                            width=8, height=8, bgcolor=ACCENT_GREEN, border_radius=4
                        ),
                        ft.Text("FFT señal filtrada", color=TEXT_MUTED, size=9),
                    ],
                    spacing=6,
                ),
                ft.Divider(color=BORDER_COL, height=8),
                ft.Text("Amplitud:", color=TEXT_MUTED, size=10),
                ft.Row(
                    [
                        ft.Container(
                            width=8, height=8, bgcolor=ACCENT_AMBER, border_radius=4
                        ),
                        ft.Text("Post-MA (suavizada)", color=TEXT_MUTED, size=9),
                    ],
                    spacing=6,
                ),
                ft.Divider(color=BORDER_COL, height=10),
                ft.Text(
                    "ℹ️ Desde esta pestaña\nen adelante TODAS las\n"
                    "vistas usan la señal\nfiltrada por MA.",
                    color=TEXT_MUTED,
                    size=9,
                    italic=True,
                ),
                ft.Divider(color=BORDER_COL, height=8),
                ft.Text(
                    "Ctrl+Scroll → zoom Y\nShift+Scroll → zoom X",
                    color=TEXT_MUTED,
                    size=9,
                    italic=True,
                ),
            ],
            spacing=8,
        ),
    )

    return ft.Container(
        content=ft.Row([graphs, side], spacing=12, expand=True),
        expand=True,
        padding=ft.Padding(left=14, top=14, right=14, bottom=14),
    )
