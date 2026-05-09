"""
tabs/comparison.py
Pestaña de Comparación Directa — Vista 2x2 Full Width.
[Amplitud RAW] [Espectro RAW]
[Amplitud MA]  [Espectro Filtrado]
"""

import flet as ft
from core.constants import *
from ui.charts import chart_amplitude, chart_spectrum_raw, chart_amplitude_ma, chart_spectrum

def build_comparison(page: ft.Page, key_state: dict) -> ft.Control:
    from core.dsp_engine import engine_instance
    import asyncio

    # --- Imágenes de las 4 gráficas ---
    img_raw_amp  = ft.Image(src=chart_amplitude(),    fit=ft.BoxFit.FILL, gapless_playback=True, border_radius=8, expand=True)
    img_raw_spec = ft.Image(src=chart_spectrum_raw(), fit=ft.BoxFit.FILL, gapless_playback=True, border_radius=8, expand=True)
    img_filt_amp = ft.Image(src=chart_amplitude_ma(), fit=ft.BoxFit.FILL, gapless_playback=True, border_radius=8, expand=True)
    img_filt_spec= ft.Image(src=chart_spectrum(),    fit=ft.BoxFit.FILL, gapless_playback=True, border_radius=8, expand=True)

    is_rendering = [False]

    async def on_refresh(msg):
        if msg != "refresh_charts": return
        if engine_instance.active_tab != 1: return
        if is_rendering[0]: return
        is_rendering[0] = True
        try:
            res = await asyncio.gather(
                asyncio.to_thread(chart_amplitude),
                asyncio.to_thread(chart_spectrum_raw),
                asyncio.to_thread(chart_amplitude_ma),
                asyncio.to_thread(chart_spectrum),
            )
            img_raw_amp.src  = res[0]
            img_raw_spec.src = res[1]
            img_filt_amp.src = res[2]
            img_filt_spec.src = res[3]
            page.update()
        finally:
            is_rendering[0] = False

    page.pubsub.subscribe(on_refresh)

    def on_zoom_scroll(e: ft.ScrollEvent, chart_id: str):
        ctrl = key_state.get('ctrl', False)
        shift = key_state.get('shift', False)
        if not ctrl and not shift: return
        dir_ = 1 if e.scroll_delta_y > 0 else -1
        factor = 0.25 * dir_
        cfg = engine_instance.charts_config[chart_id]
        if ctrl:
            s_y = cfg["ymax"] - cfg["ymin"]
            cfg["ymin"] -= s_y * factor
            cfg["ymax"] += s_y * factor
            cfg["auto_y"] = False
        elif shift:
            s_x = cfg["xmax"] - cfg["xmin"]
            cfg["xmin"] -= s_x * factor
            cfg["xmax"] += s_x * factor
            cfg["auto_x"] = False
        engine_instance.save_config()

    def _chart_container(img, title, chart_id, accent=ACCENT_CYAN):
        return ft.Container(
            content=ft.Column([
                ft.Text(title, size=10, weight=ft.FontWeight.BOLD, color=accent),
                ft.GestureDetector(
                    on_scroll=lambda e: on_zoom_scroll(e, chart_id),
                    content=img,
                    expand=True
                )
            ], spacing=2),
            expand=True,
            bgcolor=PANEL_BG,
            border_radius=8,
            padding=5,
            border=ft.Border(top=ft.BorderSide(2, accent), left=ft.BorderSide(1, BORDER_COL), right=ft.BorderSide(1, BORDER_COL), bottom=ft.BorderSide(1, BORDER_COL))
        )

    # --- Grid 2x2 ocupando todo el ancho ---
    return ft.Container(
        content=ft.Column([
            ft.Row([
                _chart_container(img_raw_amp,  "AMPLITUD RAW (TIEMPO)", "mon_raw_amp", ACCENT_CYAN),
                _chart_container(img_raw_spec, "ESPECTRO RAW (FRECUENCIA)", "mon_raw_spec", ACCENT_CYAN),
            ], expand=True, spacing=10),
            ft.Row([
                _chart_container(img_filt_amp, "AMPLITUD FILTRADA (MA)", "mon_filt_amp", ACCENT_AMBER),
                _chart_container(img_filt_spec, "ESPECTRO FILTRADO (MA)", "mon_filt_spec", ACCENT_GREEN),
            ], expand=True, spacing=10),
        ], expand=True, spacing=10),
        expand=True,
        padding=10
    )
