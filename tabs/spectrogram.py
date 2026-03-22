"""
tabs/spectrogram.py
Lógica y UI para la pestaña "Espectrograma" (Waterfall)
"""

import flet as ft
from constants import *
from charts import chart_spectrogram
from components.shared import panel, border_all

def build_spectrogram(page: ft.Page) -> ft.Control:
    img = ft.Image(src=chart_spectrogram(), fit=ft.BoxFit.CONTAIN,
                   border_radius=10, expand=True)

    async def on_refresh(msg):
        if msg == "refresh_charts":
            img.src = chart_spectrogram()
            img.update()
            
    page.pubsub.subscribe(on_refresh)

    def sw(color): return ft.Container(width=14, height=14, bgcolor=color, border_radius=4)

    legend = ft.Row([
        sw(ACCENT_RED),   ft.Text("RFI Intenso",     color=TEXT_MAIN, size=10),
        sw(ACCENT_AMBER), ft.Text("Señal moderada",  color=TEXT_MAIN, size=10),
        sw("#3F51B5"),    ft.Text("Ruido base",      color=TEXT_MAIN, size=10),
        sw(ACCENT_CYAN),  ft.Text("HI 1420.40 MHz", color=TEXT_MAIN, size=10),
    ], spacing=8, alignment=ft.MainAxisAlignment.CENTER)

    return ft.Container(
        content=ft.Column([
            ft.Container(content=img, expand=True, bgcolor=PANEL_BG,
                         border_radius=10, border=border_all(), padding=6),
            legend,
        ], expand=True, spacing=8),
        expand=True,
        padding=ft.Padding(left=14, top=14, right=14, bottom=14),
    )
