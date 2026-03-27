"""
tabs/statistics.py
Lógica y UI para la pestaña "Estadística y Smart Trigger"
"""

import flet as ft
from core.constants import *
from ui.charts import chart_histogram
from ui.components.shared import panel, border_all

def build_statistics(page: ft.Page) -> ft.Control:
    thresh = ft.TextField(
        label="Umbral de anomalía (%)", value="15",
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
        active[0] = not active[0]
        if active[0]:
            stat_txt.value  = f"Smart Trigger: ACTIVO  (umbral={thresh.value}%)"
            stat_txt.color  = ACCENT_GREEN
            trigger_btn.content = "⛔  Desactivar Smart Trigger"
            trigger_btn.bgcolor = ACCENT_RED
        else:
            stat_txt.value  = "Smart Trigger: INACTIVO"
            stat_txt.color  = TEXT_MUTED
            trigger_btn.content = "⚡  Activar Smart Trigger"
            trigger_btn.bgcolor = ACCENT_GREEN
        page.update()

    trigger_btn.on_click = on_trigger

    img = ft.Image(src=chart_histogram(), fit=ft.BoxFit.CONTAIN,
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
        if msg == "refresh_charts":
            if is_rendering[0]: return
            is_rendering[0] = True
            try:
                from core.dsp_engine import engine_instance
                import numpy as np
                samples = engine_instance.histogram_data
                if len(samples) > 0:
                    mu, std = np.mean(samples), np.std(samples)
                    val_media.value = f"{mu:.4f}"
                    val_std.value = f"{std:.4f}"
                    if std > 0:
                        dif = samples - mu
                        sesgo = np.mean(dif**3) / (std**3)
                        kurt = np.mean(dif**4) / (std**4)
                        val_sesgo.value = f"{sesgo:.2f}"
                        val_kur.value = f"{kurt:.2f}"
                    
                    # Actualizar los textos individualmente
                    val_media.update()
                    val_std.update()
                    val_sesgo.update()
                    val_kur.update()

                import asyncio
                img.src = await asyncio.to_thread(chart_histogram)
                img.update()
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
            thresh,
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

    main_container.content = ft.Row([
        ft.Container(content=img, expand=True, bgcolor=PANEL_BG,
                     border_radius=10, border=border_all(), padding=6),
        side,
    ], spacing=12, expand=True)

    return main_container
