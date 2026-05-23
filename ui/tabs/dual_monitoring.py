"""
tabs/dual_monitoring.py
Pestaña Dual — Comparación de Señal Original vs. Filtrada.
Muestra un grid 2x2:
- [0,0] Espectro RAW       | [0,1] Espectro Filtrado
- [1,0] Amplitud RAW      | [1,1] Amplitud Filtrada
"""

import flet as ft
from core.constants import *
from ui.charts import chart_amplitude, chart_spectrum_raw, chart_amplitude_ma, chart_spectrum
from ui.components.shared import panel

def build_dual_monitoring(page: ft.Page, key_state: dict) -> ft.Control:
    # --- Imágenes del Grid ---
    img_spec_raw  = ft.Image(src=chart_spectrum_raw(), fit=ft.BoxFit.FILL, gapless_playback=True, border_radius=4, expand=True)
    img_spec_filt = ft.Image(src=chart_spectrum(),     fit=ft.BoxFit.FILL, gapless_playback=True, border_radius=4, expand=True)
    img_amp_raw   = ft.Image(src=chart_amplitude(),    fit=ft.BoxFit.FILL, gapless_playback=True, border_radius=4, expand=True)
    img_amp_filt  = ft.Image(src=chart_amplitude_ma(), fit=ft.BoxFit.FILL, gapless_playback=True, border_radius=4, expand=True)

    is_rendering = [False]

    async def on_refresh(msg):
        if msg != "refresh_charts": return
        from core.dsp_engine import engine_instance
        if engine_instance.active_tab != 1: return # Índice 1 = Dual
        if is_rendering[0]: return
        is_rendering[0] = True
        try:
            import asyncio
            results = await asyncio.gather(
                asyncio.to_thread(chart_spectrum_raw),
                asyncio.to_thread(chart_spectrum),
                asyncio.to_thread(chart_amplitude),
                asyncio.to_thread(chart_amplitude_ma),
            )
            img_spec_raw.src, img_spec_filt.src, img_amp_raw.src, img_amp_filt.src = results
            
            for w in [img_spec_raw, img_spec_filt, img_amp_raw, img_amp_filt]:
                if w.page: w.update()
        finally:
            is_rendering[0] = False

    page.pubsub.subscribe(on_refresh)

    def on_zoom_scroll(e: ft.ScrollEvent, chart_id: str):
        ctrl  = key_state.get('ctrl', False)
        shift = key_state.get('shift', False)
        if not ctrl and not shift: return
        from core.dsp_engine import engine_instance
        dir    = 1 if e.scroll_delta_y > 0 else -1
        factor = 0.25 * dir
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

    maximized_chart = [None]
    
    # Pre-declarar las cajas y filas
    box_spec_raw = None
    box_spec_filt = None
    box_amp_raw = None
    box_amp_filt = None
    row_1 = None
    row_2 = None
    
    def on_maximize(e, chart_id):
        if maximized_chart[0] == chart_id:
            maximized_chart[0] = None  # Restaurar
            icon = ft.Icons.FULLSCREEN
        else:
            maximized_chart[0] = chart_id  # Maximizar
            icon = ft.Icons.FULLSCREEN_EXIT
            
        e.control.icon = icon
        
        # Restaurar todo por defecto
        box_spec_raw.visible = box_spec_filt.visible = True
        box_amp_raw.visible = box_amp_filt.visible = True
        row_1.visible = row_2.visible = True
        
        # Ocultar lo que no se necesita
        if maximized_chart[0] == "mon_raw_spec":
            box_spec_filt.visible = row_2.visible = False
        elif maximized_chart[0] == "mon_filt_spec":
            box_spec_raw.visible = row_2.visible = False
        elif maximized_chart[0] == "mon_raw_amp":
            box_amp_filt.visible = row_1.visible = False
        elif maximized_chart[0] == "mon_filt_amp":
            box_amp_raw.visible = row_1.visible = False
            
        # Actualizar los iconos de todos para que el estado sea correcto
        for box in [box_spec_raw, box_spec_filt, box_amp_raw, box_amp_filt]:
            btn = box.content.controls[0].controls[1]
            if maximized_chart[0] is None:
                btn.icon = ft.Icons.FULLSCREEN
            else:
                if box.visible:
                    btn.icon = ft.Icons.FULLSCREEN_EXIT
                    
        # Avisar al backend para ajustar resoluciones SVG
        from core.dsp_engine import engine_instance
        engine_instance.maximized_dual_chart = maximized_chart[0]
        e.control.page.pubsub.send_all("refresh_charts")
        e.control.page.update()

    def _chart_box(img, chart_id, title, accent):
        btn = ft.IconButton(
            icon=ft.Icons.FULLSCREEN,
            icon_color=TEXT_MUTED,
            icon_size=18,
            on_click=lambda e: on_maximize(e, chart_id),
            tooltip="Maximizar/Restaurar",
            padding=0,
            width=24,
            height=24
        )
        return ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text(title, color=accent, size=10, weight=ft.FontWeight.BOLD),
                    btn
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.GestureDetector(
                    mouse_cursor=ft.MouseCursor.ZOOM_IN,
                    on_scroll=lambda e: on_zoom_scroll(e, chart_id),
                    content=img,
                    expand=True,
                )
            ], spacing=2, horizontal_alignment=ft.CrossAxisAlignment.STRETCH),
            expand=True,
            bgcolor=PANEL_BG,
            border_radius=8,
            border=ft.Border(top=ft.BorderSide(2, accent), right=ft.BorderSide(1, BORDER_COL), 
                             bottom=ft.BorderSide(1, BORDER_COL), left=ft.BorderSide(1, BORDER_COL)),
            padding=6,
        )

    box_spec_raw = _chart_box(img_spec_raw, "mon_raw_spec", "ESPECTRO ORIGINAL", ACCENT_CYAN)
    box_spec_filt = _chart_box(img_spec_filt, "mon_filt_spec", "ESPECTRO FILTRADO", ACCENT_GREEN)
    box_amp_raw = _chart_box(img_amp_raw, "mon_raw_amp", "AMPLITUD ORIGINAL", ACCENT_CYAN)
    box_amp_filt = _chart_box(img_amp_filt, "mon_filt_amp", "AMPLITUD FILTRADA (MA)", ACCENT_AMBER)

    row_1 = ft.Row([box_spec_raw, box_spec_filt], expand=True, spacing=10, vertical_alignment=ft.CrossAxisAlignment.STRETCH)
    row_2 = ft.Row([box_amp_raw, box_amp_filt], expand=True, spacing=10, vertical_alignment=ft.CrossAxisAlignment.STRETCH)

    # Grid 2x2
    grid = ft.Column([
        row_1,
        row_2,
    ], expand=True, spacing=10, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)

    return ft.Container(
        content=grid,
        expand=True,
        padding=ft.Padding(left=10, top=10, right=10, bottom=10),
    )
