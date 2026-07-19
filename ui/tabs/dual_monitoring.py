"""
tabs/dual_monitoring.py
Pestaña Dual — Lanzador del Monitor Acelerado por GPU Externo.
"""

import flet as ft
import core.constants as C
from ui.qt_monitor import launch_gpu_monitor

def build_dual_monitoring(page: ft.Page, key_state: dict) -> ft.Control:
    
    def on_launch_click(e):
        launch_gpu_monitor()

    # Lanzar la ventana del monitor automáticamente al hacer clic en la pestaña
    launch_gpu_monitor()

    return ft.Container(
        content=ft.Column(
            [
                ft.Container(height=40),
                ft.Text("🌓", size=64),
                ft.Container(height=10),
                ft.Text(
                    "Monitoreo Dual Acelerado por GPU",
                    size=22,
                    weight=ft.FontWeight.BOLD,
                    color=C.TEXT_MAIN,
                ),
                ft.Container(height=10),
                ft.Text(
                    "Este módulo se ejecuta en una ventana externa independiente para aprovechar la aceleración\n"
                    "por hardware 3D (GPU) y renderizar a 60 FPS fluidos sin bloquear la interfaz de Flet.",
                    size=14,
                    color=C.TEXT_MUTED,
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.Container(height=30),
                ft.ElevatedButton(
                    content=ft.Text("Abrir Monitor Gráfico Externo", size=13),
                    bgcolor=C.ACCENT_CYAN,
                    color=C.DARK_BG,
                    on_click=on_launch_click,
                    style=ft.ButtonStyle(
                        shape=ft.RoundedRectangleBorder(radius=6),
                        padding=15
                    )
                ),
                ft.Container(height=15),
                ft.Text(
                    "Nota: La ventana contiene el panel lateral de configuraciones (límites de ejes,\n"
                    "filtro de media móvil, etc.) y se comunica bidireccionalmente con el software.",
                    size=12,
                    color=C.TEXT_MUTED,
                    italic=True,
                    text_align=ft.TextAlign.CENTER,
                ),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
        ),
        bgcolor=C.DARK_BG,
        expand=True,
        alignment=ft.alignment.Alignment(0.0, 0.0)
    )
