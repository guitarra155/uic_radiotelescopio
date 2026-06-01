"""
tabs/statistics.py
Lógica y UI para la pestaña "Estadística y Smart Trigger"
"""

import flet as ft
from core.constants import *
from ui.charts import chart_histogram
from ui.components.shared import panel, border_all

def build_statistics(page: ft.Page, key_state: dict) -> ft.Control:
    img = ft.Image(src=chart_histogram(), fit=ft.BoxFit.FILL,
                   gapless_playback=True, border_radius=8, expand=True)

    main_container = ft.Container(
        expand=True,
        padding=ft.Padding(left=14, top=14, right=14, bottom=14),
    )

    val_media = ft.Text("0.0000", color=ACCENT_GREEN, size=10, weight=ft.FontWeight.W_600, expand=1)
    val_std   = ft.Text("0.0000", color=ACCENT_GREEN, size=10, weight=ft.FontWeight.W_600, expand=1)
    val_kur   = ft.Text("0.00",  color=ACCENT_AMBER, size=10, weight=ft.FontWeight.W_600, expand=1)
    val_sesgo = ft.Text("0.00",  color=ACCENT_AMBER, size=10, weight=ft.FontWeight.W_600, expand=1)
    val_rango_t = ft.Text("0.0s - 0.0s", color=ACCENT_CYAN, size=10, weight=ft.FontWeight.W_600, expand=1)

    is_rendering = [False]
    async def on_refresh(msg):
        if msg not in ("refresh_charts", "tab_changed"):
            return
        from core.dsp_engine import engine_instance
        if engine_instance.active_tab != 3: return # Solo renderizar si es la pestaña activa
        
        if is_rendering[0]: return
        is_rendering[0] = True
        try:
            from core.dsp_engine import engine_instance # redundante pero seguro
            import numpy as np
            
            # Calcular rango temporal de análisis
            c = engine_instance.current_file_time if engine_instance.stream_mode == "file" else (engine_instance.elapsed_samples / engine_instance.sample_rate)
            w = engine_instance.analysis_window_sec
            start_t = max(0.0, c - w)
            val_rango_t.value = f"{start_t:.1f}s - {c:.1f}s"
            if val_rango_t.page: val_rango_t.update()

            samples = engine_instance.histogram_data
            if len(samples) > 0:
                mu, std = np.mean(samples), np.std(samples)
                val_media.value = f"{mu:.4f}"
                val_std.value = f"{std:.4f}"
                
                dif = samples - mu
                if std > 1e-6:
                    sesgo = float(np.mean(dif**3) / (std**3))
                    kurt = float(np.mean(dif**4) / (std**4))
                    val_sesgo.value = f"{sesgo:.2f}"
                    val_kur.value = f"{kurt:.2f}"
                else:
                    val_sesgo.value = "0.00"
                    val_kur.value = "0.00"
                
                # Actualizar los textos individualmente con validación
                for w_lbl in [val_media, val_std, val_sesgo, val_kur]:
                    if w_lbl.page: w_lbl.update()

            import asyncio
            img.src = await asyncio.to_thread(chart_histogram)
            if img.page: img.update()
        finally:
            is_rendering[0] = False
            
    page.pubsub.subscribe(on_refresh)

    stat_rows = [
        ft.Row([ft.Text("Media (μ)", color=TEXT_MAIN, size=10, expand=1), val_media]),
        ft.Row([ft.Text("Std Dev (σ)", color=TEXT_MAIN, size=10, expand=1), val_std]),
        ft.Row([ft.Text("Kurtosis", color=TEXT_MAIN, size=10, expand=1), val_kur]),
        ft.Row([ft.Text("Sesgo", color=TEXT_MAIN, size=10, expand=1), val_sesgo]),
        ft.Row([ft.Text("Rango Temporal", color=TEXT_MAIN, size=10, expand=1), val_rango_t])
    ]
    
    info_lbl = ft.Text("Distribución detectada:\nCampana de Gauss (Aprox)", color=ACCENT_CYAN, size=11, italic=True)

    side = panel(
        width=240,
        content=ft.Column([
            ft.Text("📊  Estadística", color=ACCENT_CYAN, size=14,
                    weight=ft.FontWeight.BOLD),
            ft.Divider(color=BORDER_COL, height=12),
            info_lbl,
            ft.Container(height=4),
            ft.Text("Estadísticas en vivo:", color=TEXT_MUTED, size=11),
            *stat_rows,
        ], spacing=8),
    )

    def on_fullscreen_global(e):
        from core.dsp_engine import engine_instance
        is_fs = getattr(engine_instance, "chart_fullscreen_active", False)
        engine_instance.chart_fullscreen_active = not is_fs
        
        is_fs = engine_instance.chart_fullscreen_active
        side.visible = not is_fs
            
        e.control.icon = ft.Icons.CLOSE_FULLSCREEN if engine_instance.chart_fullscreen_active else ft.Icons.ASPECT_RATIO
        e.control.page.pubsub.send_all("toggle_fullscreen_chart")

    btn_fs = ft.IconButton(
        icon=ft.Icons.ASPECT_RATIO,
        icon_color=ACCENT_AMBER,
        icon_size=18,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=4)),
        on_click=on_fullscreen_global,
        tooltip="Pantalla Completa (Global)",
        padding=0,
        width=26,
        height=26
    )

    def on_zoom_scroll(e: ft.ScrollEvent):
        from core.dsp_engine import engine_instance
        ctrl = key_state.get("ctrl", False)
        shift = key_state.get("shift", False)
        if not ctrl and not shift:
            return
            
        d = 1 if e.scroll_delta_y > 0 else -1
        factor = 0.2 * d
        
        cfg = engine_instance.charts_config.get("stat_hist", {})
        
        if ctrl:
            s_y = cfg.get("ymax", 100) - cfg.get("ymin", 0)
            cfg["ymin"] = max(0.0, cfg.get("ymin", 0) - s_y * factor)
            cfg["ymax"] = cfg.get("ymax", 100) + s_y * factor
            cfg["auto_y"] = False
        elif shift:
            s_x = cfg.get("xmax", 1.5) - cfg.get("xmin", 0.0)
            cfg["xmin"] = max(0.0, cfg.get("xmin", 0.0) - s_x * factor)
            cfg["xmax"] = cfg.get("xmax", 1.5) + s_x * factor
            cfg["auto_x"] = False
            
        engine_instance.save_config()

    def on_hist_mode_change(e):
        from core.dsp_engine import engine_instance
        engine_instance.histogram_mode = e.control.value
        
        # Usar perfiles de configuración separados para no destruir los ajustes manuales del usuario
        cfg_id = "stat_hist_mag" if engine_instance.histogram_mode == "Magnitud" else "stat_hist_fase"
        if cfg_id not in engine_instance.charts_config:
            engine_instance.charts_config[cfg_id] = {"auto_x": True, "auto_y": True, "xmin": 0.0, "xmax": 1.0, "ymin": 0.0, "ymax": 100.0}
            
        engine_instance._frames_since_autoscale = 10
        engine_instance.save_config()
        
        if e.control.page:
            engine_instance.metadata_updated = True
            e.control.page.pubsub.send_all("tab_changed")  # Reconstruye el panel derecho con la nueva llave JSON
            e.control.page.pubsub.send_all("refresh_charts")

    hist_mode_dd = ft.RadioGroup(
        content=ft.Row([
            ft.Radio(value="Magnitud", label="Magnitud", fill_color=ACCENT_CYAN),
            ft.Radio(value="Fase", label="Fase", fill_color=ACCENT_CYAN)
        ], spacing=10),
        value="Magnitud",
        on_change=on_hist_mode_change,
    )

    chart_area = ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Text("HISTOGRAMA / DISTRIBUCIÓN", color=ACCENT_CYAN, size=10, weight=ft.FontWeight.BOLD),
                ft.Row([hist_mode_dd, btn_fs], spacing=5, vertical_alignment=ft.CrossAxisAlignment.CENTER)
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Container(
                content=ft.GestureDetector(
                    mouse_cursor=ft.MouseCursor.ZOOM_IN,
                    on_scroll=on_zoom_scroll,
                    drag_interval=0,
                    content=img,
                    expand=True,
                ),
                expand=True
            )
        ], spacing=2, horizontal_alignment=ft.CrossAxisAlignment.STRETCH),
        expand=True, bgcolor=PANEL_BG,
        border_radius=10, border=border_all(), padding=6
    )

    main_container.content = ft.Row([
        chart_area,
        side,
    ], spacing=12, expand=True, vertical_alignment=ft.CrossAxisAlignment.STRETCH)

    return main_container
