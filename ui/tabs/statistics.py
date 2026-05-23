"""
tabs/statistics.py
Lógica y UI para la pestaña "Estadística y Smart Trigger"
"""

import flet as ft
from core.constants import *
from ui.charts import chart_histogram
from ui.components.shared import panel, border_all

def build_statistics(page: ft.Page) -> ft.Control:
    thresh_high = ft.TextField(
        label="Umbral Alto (Energía)", value="15.0",
        color=TEXT_MAIN, bgcolor=DARK_BG,
        border_color=BORDER_COL, focused_border_color=ACCENT_CYAN,
        cursor_color=ACCENT_CYAN, border_radius=8, width=200,
        keyboard_type=ft.KeyboardType.NUMBER,
    )
    thresh_low = ft.TextField(
        label="Umbral Bajo (Energía)", value="5.0",
        color=TEXT_MAIN, bgcolor=DARK_BG,
        border_color=BORDER_COL, focused_border_color=ACCENT_CYAN,
        cursor_color=ACCENT_CYAN, border_radius=8, width=200,
        keyboard_type=ft.KeyboardType.NUMBER,
    )
    stat_txt = ft.Text("Smart Trigger: INACTIVO", color=TEXT_MUTED,
                       size=12, weight=ft.FontWeight.W_600)
    active = [False]

    trigger_btn = ft.Button(
        content="⚡  Activar Smart Trigger",
        bgcolor=ACCENT_GREEN, color="#000000",
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)),
    )

    def on_trigger(e):
        from core.dsp_engine import engine_instance
        active[0] = not active[0]
        
        if active[0]:
            try:
                engine_instance.trigger_high = float(thresh_high.value)
                engine_instance.trigger_low = float(thresh_low.value)
            except ValueError:
                engine_instance.trigger_high = 15.0
                engine_instance.trigger_low = 5.0
                
            engine_instance.trigger_active = True
            stat_txt.value  = f"Smart Trigger: ACTIVO (Alto={engine_instance.trigger_high}, Bajo={engine_instance.trigger_low})"
            stat_txt.color  = ACCENT_GREEN
            trigger_btn.content = "⛔  Desactivar Smart Trigger"
            trigger_btn.bgcolor = ACCENT_RED
        else:
            engine_instance.trigger_active = False
            stat_txt.value  = "Smart Trigger: INACTIVO"
            stat_txt.color  = TEXT_MUTED
            trigger_btn.content = "⚡  Armar Auto-Recorte (±1.5s)"
            trigger_btn.bgcolor = ACCENT_GREEN
        page.update()

    trigger_btn.on_click = on_trigger
    trigger_btn.content = "⚡  Armar Auto-Recorte (±1.5s)"

    img = ft.Image(src=chart_histogram(), fit=ft.BoxFit.FILL,
                   gapless_playback=True, border_radius=8, expand=True)

    main_container = ft.Container(
        expand=True,
        padding=ft.Padding(left=14, top=14, right=14, bottom=14),
    )

    val_media = ft.Text("0.000", color=ACCENT_GREEN, size=10, weight=ft.FontWeight.W_600, expand=1)
    val_std   = ft.Text("0.000", color=ACCENT_GREEN, size=10, weight=ft.FontWeight.W_600, expand=1)
    val_kur   = ft.Text("0.00",  color=ACCENT_AMBER, size=10, weight=ft.FontWeight.W_600, expand=1)
    val_sesgo = ft.Text("0.00",  color=ACCENT_AMBER, size=10, weight=ft.FontWeight.W_600, expand=1)

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
                for w in [val_media, val_std, val_sesgo, val_kur]:
                    if w.page: w.update()

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
        ft.Row([ft.Text("Sesgo", color=TEXT_MAIN, size=10, expand=1), val_sesgo])
    ]
    
    info_lbl = ft.Text("Distribución detectada:\nCampana de Gauss (Aprox)", color=ACCENT_CYAN, size=11, italic=True)

    side = panel(
        width=240,
        content=ft.Column([
            ft.Text("⚡  Smart Trigger", color=ACCENT_CYAN, size=14,
                    weight=ft.FontWeight.BOLD),
            ft.Divider(color=BORDER_COL, height=12),
            thresh_high,
            ft.Container(height=4),
            thresh_low,
            ft.Container(height=8),
            trigger_btn,
            ft.Container(height=6),
            stat_txt,
            ft.Divider(color=BORDER_COL, height=12),
            info_lbl,
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

    chart_area = ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Text("HISTOGRAMA / DISTRIBUCIÓN", color=ACCENT_CYAN, size=10, weight=ft.FontWeight.BOLD),
                btn_fs
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Container(content=img, expand=True)
        ], spacing=2, horizontal_alignment=ft.CrossAxisAlignment.STRETCH),
        expand=True, bgcolor=PANEL_BG,
        border_radius=10, border=border_all(), padding=6
    )

    main_container.content = ft.Row([
        chart_area,
        side,
    ], spacing=12, expand=True, vertical_alignment=ft.CrossAxisAlignment.STRETCH)

    return main_container
