"""
tabs/dual_monitoring.py
Pestaña Dual — Comparación de Señal Original vs. Filtrada.
Sirve como contenedor vacío para la incrustación nativa de PyQtGraph (OpenGL) vía Win32.
"""

import flet as ft
import core.constants as C

def build_dual_monitoring(page: ft.Page, key_state: dict) -> ft.Control:
    # Contenedor completamente vacío. PyQtGraph se incrustará encima de esta área.
    return ft.Container(
        bgcolor=C.DARK_BG,
        expand=True,
        padding=0
    )
