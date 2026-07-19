"""
tabs/dual_monitoring.py
Pestaña Dual — Comparación de Señal Original vs. Filtrada.
Ahora delega el renderizado a una ventana PyQtGraph acelerada por GPU usando C++.
"""

import flet as ft
import core.constants as C
from ui.components.shared import panel

def build_dual_monitoring(page: ft.Page, key_state: dict) -> ft.Control:
    
    def on_launch_click(e):
        from ui.qt_monitor import launch_gpu_monitor
        launch_gpu_monitor()

    btn_launch_gpu = ft.ElevatedButton(
        content=ft.Text("🚀 Abrir Monitor en Tiempo Real Acelerado por GPU (60 FPS)", color=C.DARK_BG, weight=ft.FontWeight.BOLD),
        on_click=on_launch_click,
        style=ft.ButtonStyle(
            bgcolor=C.ACCENT_CYAN,
            shape=ft.RoundedRectangleBorder(radius=8),
            padding=20
        )
    )

    content_col = ft.Column(
        controls=[
            ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Text("Monitoreo Dual Acelerado", size=24, weight=ft.FontWeight.BOLD, color=C.TEXT_MAIN),
                        ft.Text("Esta pestaña utiliza un backend en C++ y renderizado OpenGL (PyQtGraph) para alcanzar 60 FPS reales sin retraso (como SDR++ o Spike).", color=C.TEXT_MUTED, text_align=ft.TextAlign.CENTER),
                        ft.Divider(color=C.BORDER_COL, height=30),
                        btn_launch_gpu
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
                alignment=ft.alignment.Alignment(0, 0),
                expand=True
            )
        ],
        expand=True
    )

    return ft.Container(
        content=panel(content=content_col, expand=True),
        expand=True,
        padding=10
    )
