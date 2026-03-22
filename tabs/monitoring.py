"""
tabs/monitoring.py
Lógica y UI para la pestaña de "Monitoreo y RFI"
"""

import flet as ft
from constants import *
from charts import chart_amplitude, chart_spectrum
from components.shared import panel, border_all

def build_monitoring(page: ft.Page) -> ft.Control:
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
                        border_radius=8, expand=True)
    img_spec = ft.Image(src=chart_spectrum(),   fit=ft.BoxFit.CONTAIN,
                        border_radius=8, expand=True)

    graphs = ft.Column([
        ft.Container(content=img_amp,  expand=1, bgcolor=PANEL_BG,
                     border_radius=8, border=border_all(), padding=4),
        ft.Container(content=img_spec, expand=1, bgcolor=PANEL_BG,
                     border_radius=8, border=border_all(), padding=4),
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

    return ft.Container(
        content=ft.Row([graphs, side], spacing=12, expand=True),
        expand=True,
        padding=ft.Padding(left=14, top=14, right=14, bottom=14),
    )
