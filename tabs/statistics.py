"""
tabs/statistics.py
Lógica y UI para la pestaña "Estadística y Smart Trigger"
"""

import flet as ft
from constants import *
from charts import chart_histogram
from components.shared import panel, border_all

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
                   border_radius=8, expand=True)

    stat_data = [("Media (σ)", "0.023", ACCENT_GREEN),
                 ("Std Dev",   "1.041", ACCENT_GREEN),
                 ("Kurtosis",  "3.87",  ACCENT_AMBER),
                 ("Sesgo",     "1.14",  ACCENT_AMBER)]

    stat_rows = [ft.Row([ft.Text(k, color=TEXT_MAIN, size=10, expand=1),
                          ft.Text(v, color=c, size=10, expand=1,
                                  weight=ft.FontWeight.W_600)])
                 for k, v, c in stat_data]

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
            ft.Text("Estadísticas de sesión:", color=TEXT_MUTED, size=11),
            *stat_rows,
        ], spacing=8),
    )

    return ft.Container(
        content=ft.Row([
            ft.Container(content=img, expand=True, bgcolor=PANEL_BG,
                         border_radius=10, border=border_all(), padding=6),
            side,
        ], spacing=12, expand=True),
        expand=True,
        padding=ft.Padding(left=14, top=14, right=14, bottom=14),
    )
