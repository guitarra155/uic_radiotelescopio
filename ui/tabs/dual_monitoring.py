"""
tabs/dual_monitoring.py
Pestaña Dual — Comparación de Señal Original vs. Filtrada.
Muestra un grid 2x2:
- [0,0] Espectro RAW       | [0,1] Espectro Filtrado
- [1,0] Amplitud RAW      | [1,1] Amplitud Filtrada
"""

import flet as ft
import core.constants as C
from ui.charts import chart_amplitude, chart_spectrum_raw, chart_amplitude_ma, chart_spectrum
from ui.components.shared import panel

def build_dual_monitoring(page: ft.Page, key_state: dict) -> ft.Control:
    # --- Gráficos del Grid Acelerados por Canvas (GPU) ---
    from ui.components.canvas_chart import CanvasChart
    import numpy as np

    chart_spec_raw  = CanvasChart("Espectro RAW", C.ACCENT_CYAN, -150, -40)
    chart_spec_filt = CanvasChart("Espectro Filtrado", C.ACCENT_GREEN, -150, -40)
    chart_amp_raw   = CanvasChart("Amplitud RAW", C.ACCENT_CYAN, -0.5, 0.5)
    chart_amp_filt  = CanvasChart("Amplitud Filtrada", C.ACCENT_AMBER, -0.5, 0.5)

    # Alias para mantener compatibilidad con el resto de la interfaz (on_maximize, etc)
    img_spec_raw  = chart_spec_raw
    img_spec_filt = chart_spec_filt
    img_amp_raw   = chart_amp_raw
    img_amp_filt  = chart_amp_filt

    is_rendering = [False]

    async def on_refresh(msg):
        if msg != "refresh_charts": return
        from core.dsp_engine import engine_instance
        if engine_instance.active_tab != 1: return # Índice 1 = Dual
        if is_rendering[0]: return
        is_rendering[0] = True
        try:
            # Obtener datos crudos del motor DSP
            spec_raw = getattr(engine_instance, "spectrum_raw_data", None)
            spec_filt = getattr(engine_instance, "spectrum_data", None)
            iq_raw = getattr(engine_instance, "current_iq", None)
            iq_filt = getattr(engine_instance, "amplitude_ma_data", None)

            # Obtener configuraciones de escala de los charts
            cfg_spec_raw = engine_instance.charts_config["mon_raw_spec"]
            cfg_spec_filt = engine_instance.charts_config["mon_filt_spec"]
            cfg_amp_raw = engine_instance.charts_config["mon_raw_amp"]
            cfg_amp_filt = engine_instance.charts_config["mon_filt_amp"]

            # Frecuencias en MHz
            fc = engine_instance.center_freq
            fs_mhz = engine_instance.sample_rate / 1_000_000.0
            fft_size = engine_instance.fft_size
            freqs = np.linspace(fc - fs_mhz / 2, fc + fs_mhz / 2, fft_size)

            if spec_raw is not None and len(spec_raw) == len(freqs):
                chart_spec_raw.update_plot(
                    freqs, spec_raw, 
                    x_min=cfg_spec_raw["xmin"], x_max=cfg_spec_raw["xmax"],
                    y_min=cfg_spec_raw["ymin"], y_max=cfg_spec_raw["ymax"]
                )
            if spec_filt is not None and len(spec_filt) == len(freqs):
                chart_spec_filt.update_plot(
                    freqs, spec_filt,
                    x_min=cfg_spec_filt["xmin"], x_max=cfg_spec_filt["xmax"],
                    y_min=cfg_spec_filt["ymin"], y_max=cfg_spec_filt["ymax"]
                )
            if iq_raw is not None:
                # Decimar y graficar parte Real
                y_raw = np.real(iq_raw)
                x_raw = np.linspace(cfg_amp_raw["xmin"], cfg_amp_raw["xmax"], len(y_raw))
                chart_amp_raw.update_plot(
                    x_raw, y_raw,
                    x_min=cfg_amp_raw["xmin"], x_max=cfg_amp_raw["xmax"],
                    y_min=cfg_amp_raw["ymin"], y_max=cfg_amp_raw["ymax"]
                )
            if iq_filt is not None:
                y_filt = np.real(iq_filt)
                x_filt = np.linspace(cfg_amp_filt["xmin"], cfg_amp_filt["xmax"], len(y_filt))
                chart_amp_filt.update_plot(
                    x_filt, y_filt,
                    x_min=cfg_amp_filt["xmin"], x_max=cfg_amp_filt["xmax"],
                    y_min=cfg_amp_filt["ymin"], y_max=cfg_amp_filt["ymax"]
                )
        except Exception as e:
            # print(f"DEBUG: Canvas update failed: {e}")
            pass
        finally:
            is_rendering[0] = False

    page.pubsub.subscribe(on_refresh)

    def on_zoom_scroll(e: ft.ScrollEvent, chart_id: str):
        from core.dsp_engine import engine_instance
        cfg = engine_instance.charts_config[chart_id]
        
        if e.scroll_delta.y != 0:
            d = 1 if e.scroll_delta.y > 0 else -1
            s_y = cfg["ymax"] - cfg["ymin"]
            cfg["ymin"] -= s_y * 0.15 * d
            cfg["ymax"] += s_y * 0.15 * d
            cfg["auto_y"] = False
        elif e.scroll_delta.x != 0:
            d = 1 if e.scroll_delta.x > 0 else -1
            s_x = cfg["xmax"] - cfg["xmin"]
            cfg["xmin"] -= s_x * 0.15 * d
            cfg["xmax"] += s_x * 0.15 * d
            cfg["auto_x"] = False
        else:
            return

        engine_instance.save_config()
        page.pubsub.send_all("refresh_charts")


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
            btn = getattr(box, "btn_maximize", None)
            if btn:
                if maximized_chart[0] is None:
                    btn.icon = ft.Icons.FULLSCREEN
                else:
                    if box.visible:
                        btn.icon = ft.Icons.FULLSCREEN_EXIT
                    
        # Avisar al backend para ajustar resoluciones SVG
        from core.dsp_engine import engine_instance
        engine_instance.maximized_dual_chart = maximized_chart[0]
        e.control.page.pubsub.send_all("refresh_charts")
        if e and e.control and e.control.page:
            e.control.page.update()

    def on_fullscreen_global(e, chart_id):
        from core.dsp_engine import engine_instance
        is_fs = getattr(engine_instance, "chart_fullscreen_active", False)
        engine_instance.chart_fullscreen_active = not is_fs
        
        # Ocultar lo que no se necesita (las otras gráficas del tab) si entramos en FS
        if engine_instance.chart_fullscreen_active:
            # Forzar maximize de este chart
            if maximized_chart[0] != chart_id:
                on_maximize(e, chart_id)
        else:
            # Restaurar
            if maximized_chart[0] == chart_id:
                on_maximize(e, chart_id)

        e.control.icon = ft.Icons.CLOSE_FULLSCREEN if engine_instance.chart_fullscreen_active else ft.Icons.ASPECT_RATIO
        e.control.page.pubsub.send_all("toggle_fullscreen_chart")

    def _chart_box(img, chart_id, title, accent):
        btn = ft.IconButton(
            icon=ft.Icons.FULLSCREEN,
            icon_color=C.TEXT_MUTED,
            icon_size=18,
            on_click=lambda e: on_maximize(e, chart_id),
            tooltip="Maximizar/Restaurar",
            padding=0,
            width=24,
            height=24
        )
        btn_fs = ft.IconButton(
            icon=ft.Icons.ASPECT_RATIO,
            icon_color=C.ACCENT_AMBER,
            icon_size=18,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=4)
            ),
            on_click=lambda e: on_fullscreen_global(e, chart_id),
            tooltip="Pantalla Completa (Global)",
            padding=0,
            width=26,
            height=26
        )
        box = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text(title, color=accent, size=9, weight=ft.FontWeight.BOLD),
                    ft.Row([btn, btn_fs], spacing=0),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                   vertical_alignment=ft.CrossAxisAlignment.CENTER,
                   height=20),
                ft.GestureDetector(
                    mouse_cursor=ft.MouseCursor.ZOOM_IN,
                    on_scroll=lambda e: on_zoom_scroll(e, chart_id),
                    content=img,
                    expand=True,
                )
            ], spacing=1, horizontal_alignment=ft.CrossAxisAlignment.STRETCH),
            expand=True,
            bgcolor=C.PANEL_BG,
            border_radius=8,
            border=ft.Border(top=ft.BorderSide(2, accent), right=ft.BorderSide(1, C.BORDER_COL),
                             bottom=ft.BorderSide(1, C.BORDER_COL), left=ft.BorderSide(1, C.BORDER_COL)),
            padding=ft.Padding(left=6, top=2, right=2, bottom=4),
        )
        box.btn_maximize = btn
        box.btn_fs = btn_fs
        return box

    box_spec_raw = _chart_box(img_spec_raw, "mon_raw_spec", "ESPECTRO ORIGINAL", C.ACCENT_CYAN)
    box_spec_filt = _chart_box(img_spec_filt, "mon_filt_spec", "ESPECTRO FILTRADO", C.ACCENT_GREEN)
    box_amp_raw = _chart_box(img_amp_raw, "mon_raw_amp", "AMPLITUD ORIGINAL", C.ACCENT_CYAN)
    box_amp_filt = _chart_box(img_amp_filt, "mon_filt_amp", "AMPLITUD FILTRADA (MA)", C.ACCENT_AMBER)

    row_1 = ft.Row([box_spec_raw, box_spec_filt], expand=True, spacing=10, vertical_alignment=ft.CrossAxisAlignment.STRETCH)
    row_2 = ft.Row([box_amp_raw, box_amp_filt], expand=True, spacing=10, vertical_alignment=ft.CrossAxisAlignment.STRETCH)

    boxes = [box_spec_raw, box_spec_filt, box_amp_raw, box_amp_filt]
    accents = [C.ACCENT_CYAN, C.ACCENT_GREEN, C.ACCENT_CYAN, C.ACCENT_AMBER]
    chart_ids = ["mon_raw_spec", "mon_filt_spec", "mon_raw_amp", "mon_filt_amp"]
    selected_idx = [None]

    async def on_dual_keyboard_msg(msg):
        from core.dsp_engine import engine_instance
        if engine_instance.active_tab != 1: return  # Pestaña 2 (índice 1)
        
        if isinstance(msg, tuple) and len(msg) == 2:
            cmd, idx = msg
            if cmd == "select_dual_chart":
                selected_idx[0] = idx
                for i, (box, accent) in enumerate(zip(boxes, accents)):
                    if i == idx:
                        # Borde grueso del color secundario/alerta activo
                        box.border = ft.Border(
                            top=ft.BorderSide(3, C.ACCENT_AMBER),
                            right=ft.BorderSide(3, C.ACCENT_AMBER),
                            bottom=ft.BorderSide(3, C.ACCENT_AMBER),
                            left=ft.BorderSide(3, C.ACCENT_AMBER)
                        )
                    else:
                        # Borde normal
                        box.border = ft.Border(
                            top=ft.BorderSide(2, accent),
                            right=ft.BorderSide(1, C.BORDER_COL),
                            bottom=ft.BorderSide(1, C.BORDER_COL),
                            left=ft.BorderSide(1, C.BORDER_COL)
                        )
                    if box.page:
                        try: box.update()
                        except: pass
            elif cmd == "maximize_dual_chart":
                box = boxes[idx]
                chart_id = chart_ids[idx]
                class FakeEvent:
                    def __init__(self):
                        self.control = getattr(box, "btn_maximize", None)
                e_fake = FakeEvent()
                if e_fake.control:
                    on_maximize(e_fake, chart_id)

    page.pubsub.subscribe(on_dual_keyboard_msg)

    # Grid 2x2
    grid = ft.Column([
        row_1,
        row_2,
    ], expand=True, spacing=10, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)

    help_banner = ft.Container(
        content=ft.Row([
            ft.Icon(ft.Icons.KEYBOARD_ROUNDED, color=C.ACCENT_CYAN, size=15),
            ft.Text(
                "Navegación por teclado: [F1 - F4] Seleccionar gráfica (borde amarillo)  •  [CTRL + F1 - F4] Maximizar / Restaurar vista",
                color=C.TEXT_MUTED,
                size=10,
                weight=ft.FontWeight.W_500
            )
        ], spacing=8, alignment=ft.MainAxisAlignment.CENTER),
        padding=ft.Padding(top=5, bottom=5, left=10, right=10),
        bgcolor=C.PANEL_BG,
        border_radius=6,
        border=ft.Border(
            top=ft.BorderSide(1, C.BORDER_COL), right=ft.BorderSide(1, C.BORDER_COL),
            bottom=ft.BorderSide(1, C.BORDER_COL), left=ft.BorderSide(1, C.BORDER_COL)
        )
    )

    main_layout = ft.Column([
        grid,
        help_banner
    ], expand=True, spacing=8, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)

    return ft.Container(
        content=main_layout,
        expand=True,
        padding=ft.Padding(left=10, top=10, right=10, bottom=10),
    )
