"""
tabs/monitoring.py
Pestaña 1 — Señal ORIGINAL (sin ningún filtro).
Muestra espectro RAW + amplitud RAW para referencia pre-filtrado.
"""

import flet as ft
from core.constants import *
from ui.charts import chart_amplitude, chart_spectrum_raw
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
    
    rfi_last_label = ft.Text("--:--:-- UTC", color=TEXT_MAIN, size=11)
    rfi_count_label = ft.Text("0 interferencias", color=ACCENT_AMBER, size=11,
                              weight=ft.FontWeight.W_600)

    def on_rfi(e):
        on = rfi_switch.value
        from core.dsp_engine import engine_instance
        engine_instance.rfi_mitigation_on = on
        rfi_status.value = "Estado: ACTIVO" if on else "Estado: INACTIVO"
        rfi_status.color = ACCENT_GREEN if on else ACCENT_RED
        page.update()

    rfi_switch.on_change = on_rfi

    img_spec = ft.Image(src=chart_spectrum_raw(), fit=ft.BoxFit.CONTAIN,
                        gapless_playback=True, border_radius=8, expand=True)
    img_amp  = ft.Image(src=chart_amplitude(),   fit=ft.BoxFit.CONTAIN,
                        gapless_playback=True, border_radius=8, expand=True)

    is_rendering = [False]

    async def on_refresh(msg):
        if msg != "refresh_charts":
            return
        from core.dsp_engine import engine_instance
        if engine_instance.active_tab != 0:
            return
        if is_rendering[0]:
            return
        is_rendering[0] = True
        try:
            import asyncio
            spec_b64, amp_b64 = await asyncio.gather(
                asyncio.to_thread(chart_spectrum_raw),
                asyncio.to_thread(chart_amplitude),
            )
            img_spec.src = spec_b64
            img_amp.src  = amp_b64
            
            # Actualizar labels de RFI
            rfi_last_label.value = engine_instance.rfi_last_time
            rfi_count_label.value = f"{engine_instance.rfi_event_count} interferencias"
            
            for w in [img_spec, img_amp, rfi_last_label, rfi_count_label]:
                if w.page: w.update()
        finally:
            is_rendering[0] = False

    page.pubsub.subscribe(on_refresh)

    from core.dsp_engine import engine_instance

    def on_zoom_scroll(e: ft.ScrollEvent):
        ctrl  = key_state.get('ctrl', False)
        shift = key_state.get('shift', False)
        if not ctrl and not shift:
            return
        dir    = 1 if e.scroll_delta_y > 0 else -1
        factor = 0.25 * dir
        if ctrl:
            s_amp = engine_instance.amp_max - engine_instance.amp_min
            engine_instance.amp_min -= s_amp * factor
            engine_instance.amp_max += s_amp * factor
            s_db = engine_instance.db_max - engine_instance.db_min
            engine_instance.db_min -= s_db * factor
            engine_instance.db_max += s_db * factor
            engine_instance.save_config()
        elif shift:
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

    graphs = ft.Column([
        ft.Container(content=_chart_box(img_spec, ACCENT_CYAN), expand=1),
        ft.Container(content=_chart_box(img_amp,  ACCENT_CYAN), expand=1),
    ], expand=True, spacing=10, scroll=ft.ScrollMode.AUTO)

    side = panel(
        width=230,
        content=ft.Column([
            ft.Text("🛡️  Control RFI", color=ACCENT_CYAN, size=14,
                    weight=ft.FontWeight.BOLD),
            ft.Divider(color=BORDER_COL, height=14),
            rfi_switch,
            rfi_status,
            ft.Divider(color=BORDER_COL, height=14),
            ft.Text("🛡️ ¿Qué es el Escudo RFI?", color=ACCENT_CYAN, size=10, weight=ft.FontWeight.BOLD),
            ft.Text("Detecta señales artificiales (Satélites, LTE, Wi-Fi) "
                    "que contaminan la observación astronómica y las registra como eventos.",
                    color=TEXT_MUTED, size=9),
            ft.Divider(color=BORDER_COL, height=8),
            
            ft.Text("Última detección:", color=TEXT_MUTED, size=11),
            rfi_last_label,
            ft.Divider(color=BORDER_COL, height=10),
            ft.Text("Eventos hoy:",      color=TEXT_MUTED, size=11),
            rfi_count_label,
            ft.Divider(color=BORDER_COL, height=10),
            ft.Text("Rango activo:",     color=TEXT_MUTED, size=11),
            ft.Text(f"{engine_instance.center_freq - 1:.1f}–{engine_instance.center_freq + 1:.1f} MHz", color=TEXT_MAIN,  size=10),
            ft.Divider(color=BORDER_COL, height=10),
            ft.Text("⚠ Señal ORIGINAL", color=ACCENT_CYAN,
                    size=10, weight=ft.FontWeight.W_600),
            ft.Text("Sin ningún filtro aplicado.\n"
                    "Usar como referencia pre-MA.",
                    color=TEXT_MUTED, size=9, italic=True),
        ], spacing=8),
    )

    return ft.Container(
        content=ft.Row([graphs, side], spacing=12, expand=True),
        expand=True,
        padding=ft.Padding(left=14, top=14, right=14, bottom=14),
    )
