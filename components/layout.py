"""
components/layout.py
Define la cabecera (Header) y el pie de página (Footer) de la aplicación.
"""

import flet as ft
from constants import *
from components.shared import border_all

def build_header(page: ft.Page) -> ft.Control:
    sdr_dot = ft.Text("●", color=ACCENT_RED, size=16)
    sdr_lbl = ft.Text("Estado SDR: Desconectado", color=ACCENT_RED,
                      size=12, weight=ft.FontWeight.W_600)

    def on_emergency(e):
        sb = ft.SnackBar(
            content=ft.Text("⛔  EMERGENCIA: Adquisición detenida.",
                            color="#FFFFFF", weight=ft.FontWeight.BOLD),
            bgcolor=ACCENT_RED,
        )
        page.overlay.append(sb)
        sb.open = True
        page.update()

    emg_btn = ft.Button(
        content="⛔  Emergencia / Detener",
        bgcolor=ACCENT_RED, color="#FFFFFF",
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)),
        on_click=on_emergency,
    )

    return ft.Container(
        bgcolor=PANEL_BG,
        border=ft.Border(bottom=ft.BorderSide(1, BORDER_COL)),
        padding=ft.Padding(left=20, top=10, right=20, bottom=10),
        content=ft.Row([
            ft.Icon(ft.Icons.WIFI_TETHERING, color=ACCENT_CYAN, size=26),
            ft.Text(
                "Procesamiento de Señales — Radiotelescopio (1420.40 MHz)",
                color=TEXT_MAIN, size=15, weight=ft.FontWeight.BOLD, expand=True,
            ),
            ft.Row([sdr_dot, sdr_lbl], spacing=5,
                   vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ft.Container(width=24),
            emg_btn,
        ], vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=12),
    )

def build_footer() -> ft.Control:
    return ft.Container(
        bgcolor=PANEL_BG,
        border=ft.Border(top=ft.BorderSide(1, BORDER_COL)),
        padding=ft.Padding(left=20, top=6, right=20, bottom=6),
        content=ft.Row([
            ft.Text("UIC Radiotelescopio  •  v1.0.0",         color=TEXT_MUTED, size=10),
            ft.Text("•",                                        color=BORDER_COL, size=10),
            ft.Text("HI 1420.405751 MHz",                      color=TEXT_MUTED, size=10),
            ft.Text("•",                                        color=BORDER_COL, size=10),
            ft.Text("Backend: RTL-SDR / GNU Radio",            color=TEXT_MUTED, size=10),
            ft.Container(expand=True),
            ft.Text("2026-03-22  13:05 CST",                   color=TEXT_MUTED, size=10),
        ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
    )
