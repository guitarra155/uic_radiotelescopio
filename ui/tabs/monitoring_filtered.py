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
        fit=ft.BoxFit.FILL,
        gapless_playback=True,
        border_radius=8,
        expand=True,
    )
    img_amp = ft.Image(
        src=chart_amplitude_ma(),
        fit=ft.BoxFit.FILL,
        gapless_playback=True,
        border_radius=8,
        expand=True,
    )

    is_rendering = [False]

    async def on_refresh(msg):
        if msg != "refresh_charts":
            return
        from core.dsp_engine import engine_instance

        if engine_instance.active_tab != 2:  # índice 2 = esta pestaña
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
            if img_spec.page: img_spec.update()
            if img_amp.page: img_amp.update()
        finally:
            is_rendering[0] = False

    page.pubsub.subscribe(on_refresh)

    from core.dsp_engine import engine_instance

    def reset_defaults(e):
        engine_instance.reset_to_defaults()
        engine_instance.save_config()
        # No hace falta refrescar imagen inmediatamente, el loop lo hará.

    def on_zoom_scroll(e: ft.ScrollEvent, chart_id: str):
        ctrl = key_state.get("ctrl", False)
        shift = key_state.get("shift", False)
        if not ctrl and not shift:
            return
        dir_ = 1 if e.scroll_delta_y > 0 else -1
        factor = 0.25 * dir_
        cfg = engine_instance.charts_config[chart_id]
        if ctrl:
            s_y = cfg["ymax"] - cfg["ymin"]
            cfg["ymin"] -= s_y * factor
            cfg["ymax"] += s_y * factor
            cfg["auto_y"] = False
            engine_instance.save_config()
        elif shift:
            s_x = cfg["xmax"] - cfg["xmin"]
            cfg["xmin"] -= s_x * factor
            cfg["xmax"] += s_x * factor
            cfg["auto_x"] = False
            engine_instance.save_config()

    def _chart_box(img, chart_id, accent=BORDER_COL):
        return ft.Container(
            content=ft.GestureDetector(
                mouse_cursor=ft.MouseCursor.ZOOM_IN,
                on_scroll=lambda e: on_zoom_scroll(e, chart_id),
                drag_interval=0,
                content=img,
                expand=True,
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
            ft.Container(content=_chart_box(img_spec, "mon_filt_spec", ACCENT_GREEN), expand=1),
            ft.Container(content=_chart_box(img_amp, "mon_filt_amp", ACCENT_AMBER), expand=1),
        ],
        expand=True,
        spacing=10,
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
