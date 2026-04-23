"""
tabs/spectrogram.py
Lógica y UI para la pestaña "Espectrograma" (Waterfall)
"""

import flet as ft
from core.constants import *
from ui.charts import chart_spectrogram
from ui.components.shared import panel, border_all


def build_spectrogram(page: ft.Page, key_state: dict) -> ft.Control:
    img = ft.Image(
        src=chart_spectrogram(),
        fit=ft.BoxFit.CONTAIN,
        border_radius=10,
        expand=True,
        gapless_playback=True,
    )

    main_container = ft.Container(
        expand=True,
        padding=ft.Padding(left=14, top=14, right=14, bottom=14),
    )

    is_rendering = [False]

    async def on_refresh(msg):
        if msg == "refresh_charts":
            from core.dsp_engine import engine_instance

            if engine_instance.active_tab != 2:
                return  # Solo renderizar si es la pestaña activa

            if is_rendering[0]:
                return
            is_rendering[0] = True
            try:
                import asyncio

                # Ejecutar gráfica intensiva en hilo de CPU secundario
                img.src = await asyncio.to_thread(chart_spectrogram)
                if img.page: img.update()
            finally:
                is_rendering[0] = False

    page.pubsub.subscribe(on_refresh)

    from core.dsp_engine import engine_instance

    def reset_defaults(e):
        engine_instance.reset_to_defaults()
        engine_instance.save_config()

    def on_zoom_scroll(e: ft.ScrollEvent):
        ctrl = key_state.get("ctrl", False)
        shift = key_state.get("shift", False)

        if not ctrl and not shift:
            return

        dir = 1 if e.scroll_delta_y > 0 else -1
        factor = 0.15 * dir

        if ctrl:
            s_db = engine_instance.db_max - engine_instance.db_min
            engine_instance.db_min -= s_db * factor
            engine_instance.db_max += s_db * factor
            engine_instance.save_config()
        elif shift:
            s_f = engine_instance.f_max - engine_instance.f_min
            engine_instance.f_min -= s_f * factor
            engine_instance.f_max += s_f * factor
            engine_instance.save_config()

    def sw(color):
        return ft.Container(width=14, height=14, bgcolor=color, border_radius=4)

    legend = ft.Row(
        [
            sw(ACCENT_RED),
            ft.Text("RFI Intenso", color=TEXT_MAIN, size=10),
            sw(ACCENT_AMBER),
            ft.Text("Señal moderada", color=TEXT_MAIN, size=10),
            sw("#3F51B5"),
            ft.Text("Ruido base", color=TEXT_MAIN, size=10),
            sw(ACCENT_CYAN),
            ft.Text("HI 1420.40 MHz", color=TEXT_MAIN, size=10),
        ],
        spacing=8,
        alignment=ft.MainAxisAlignment.CENTER,
    )

    main_container.content = ft.Column(
        [
            ft.Row(
                [
                    ft.Text(
                        "Waterfall",
                        color=ACCENT_CYAN,
                        weight=ft.FontWeight.BOLD,
                        size=14,
                    ),
                    ft.TextButton(
                        "Restaurar",
                        on_click=reset_defaults,
                        style=ft.ButtonStyle(color=ACCENT_CYAN),
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            ft.Container(
                content=ft.GestureDetector(
                    mouse_cursor=ft.MouseCursor.ZOOM_IN,
                    on_scroll=on_zoom_scroll,
                    drag_interval=0,
                    content=img,
                ),
                expand=True,
                bgcolor=PANEL_BG,
                border_radius=10,
                border=border_all(),
                padding=6,
            ),
            legend,
        ],
        expand=True,
        spacing=8,
    )
    return main_container
