"""
tabs/monitoring.py
Lógica y UI para la pestaña de "Monitoreo y RFI"
"""

import flet as ft
from core.constants import *
from ui.charts import chart_amplitude, chart_spectrum
from ui.components.shared import panel, border_all

def build_monitoring(page: ft.Page, key_state: dict) -> ft.Control:
    rfi_switch = ft.Switch(
        label="Mitigación Automática de RFI",
        value=False,
        active_color=ACCENT_GREEN,
        label_text_style=ft.TextStyle(color=TEXT_MAIN, size=13),
    )
    rfi_status = ft.Text("Estado: INACTIVO", color=ACCENT_RED, size=11,
                         weight=ft.FontWeight.W_600)

    def on_rfi(e):
        on = rfi_switch.value
        rfi_status.value = "Estado: ACTIVO" if on else "Estado: INACTIVO"
        rfi_status.color = ACCENT_GREEN if on else ACCENT_RED
        page.update()

    rfi_switch.on_change = on_rfi

    img_amp  = ft.Image(src=chart_amplitude(),  fit=ft.BoxFit.CONTAIN,
                        gapless_playback=True, border_radius=8, expand=True)
    img_spec = ft.Image(src=chart_spectrum(),   fit=ft.BoxFit.CONTAIN,
                        gapless_playback=True, border_radius=8, expand=True)

    main_container = ft.Container(
        expand=True,
        padding=ft.Padding(left=14, top=14, right=14, bottom=14),
    )

    is_rendering = [False]
    async def on_refresh(msg):
        if msg == "refresh_charts":
            from core.dsp_engine import engine_instance
            if engine_instance.active_tab != 0: return # Solo renderizar si es la pestaña activa
            
            if is_rendering[0]: return
            is_rendering[0] = True
            try:
                import asyncio
                # Ejecutar dibujo de las dos gráficas de forma paralela en hilos de C separados (Multinúcleo)
                amp_b64, spec_b64 = await asyncio.gather(
                    asyncio.to_thread(chart_amplitude),
                    asyncio.to_thread(chart_spectrum)
                )
                img_amp.src  = amp_b64
                img_spec.src = spec_b64
                img_amp.update()
                img_spec.update()
            finally:
                is_rendering[0] = False
            
    page.pubsub.subscribe(on_refresh)

    from core.dsp_engine import engine_instance

    def on_zoom_scroll(e: ft.ScrollEvent):
        ctrl = key_state.get('ctrl', False)
        shift = key_state.get('shift', False)
        
        # Si no pulsa ni ctrl ni shift, no hacemos zoom
        if not ctrl and not shift: return
            
        # e.scroll_delta_y > 0 -> Hacia abajo (Alejar / Zoom Out)
        # e.scroll_delta_y < 0 -> Hacia arriba (Acercar / Zoom In)
        dir = 1 if e.scroll_delta_y > 0 else -1
        factor = 0.25 * dir
        
        if ctrl:
            # Zoom Vertical: Eje Y (Potencia y Amplitud)
            s_amp = engine_instance.amp_max - engine_instance.amp_min
            engine_instance.amp_min -= s_amp * factor
            engine_instance.amp_max += s_amp * factor
            s_db = engine_instance.db_max - engine_instance.db_min
            engine_instance.db_min -= s_db * factor
            engine_instance.db_max += s_db * factor
            engine_instance.save_config()
        elif shift:
            # Zoom Horizontal: Eje X (Frecuencia)
            s_f = engine_instance.f_max - engine_instance.f_min
            engine_instance.f_min -= s_f * factor
            engine_instance.f_max += s_f * factor
            engine_instance.save_config()

    graphs = ft.Column([
        ft.Container(content=ft.GestureDetector(
            mouse_cursor=ft.MouseCursor.ZOOM_IN,
            on_scroll=on_zoom_scroll,
            drag_interval=0,
            content=img_amp),
            expand=1, bgcolor=PANEL_BG, border_radius=8, border=border_all(), padding=4),
        ft.Container(content=ft.GestureDetector(
            mouse_cursor=ft.MouseCursor.ZOOM_IN,
            on_scroll=on_zoom_scroll,
            drag_interval=0,
            content=img_spec),
            expand=1, bgcolor=PANEL_BG, border_radius=8, border=border_all(), padding=4),
    ], expand=True, spacing=10)

    side = panel(
        width=230,
        content=ft.Column([
            ft.Text("🛡️  Control RFI", color=ACCENT_CYAN, size=14,
                    weight=ft.FontWeight.BOLD),
            ft.Divider(color=BORDER_COL, height=14),
            rfi_switch,
            rfi_status,
            ft.Divider(color=BORDER_COL, height=14),
            ft.Text("Última detección:", color=TEXT_MUTED, size=11),
            ft.Text("12:43:07 UTC",      color=TEXT_MAIN,  size=11),
            ft.Divider(color=BORDER_COL, height=10),
            ft.Text("Eventos hoy:",      color=TEXT_MUTED, size=11),
            ft.Text("7 interferencias",  color=ACCENT_AMBER, size=11,
                    weight=ft.FontWeight.W_600),
            ft.Divider(color=BORDER_COL, height=10),
            ft.Text("Rango activo:",      color=TEXT_MUTED, size=11),
            ft.Text("1419.8–1421.0 MHz", color=TEXT_MAIN,  size=10),
        ], spacing=8),
    )

    main_container.content = ft.Row([graphs, side], spacing=12, expand=True)
    return main_container
