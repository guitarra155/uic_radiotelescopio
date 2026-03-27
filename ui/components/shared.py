"""
components/shared.py
Componentes UI reutilizables estilo "Widgets" para consistencia de diseño.
"""

import flet as ft
from core.constants import *

def border_all(width=1, color=BORDER_COL) -> ft.Border:
    """Retorna un borde completo para Flet 0.82."""
    s = ft.BorderSide(width, color)
    return ft.Border(top=s, right=s, bottom=s, left=s)

def panel(padding_val=18, **kwargs) -> ft.Container:
    """Contenedor estándar tipo Panel, con borde y fondo acordes al tema."""
    return ft.Container(
        bgcolor=PANEL_BG,
        border_radius=12,
        border=border_all(),
        padding=ft.Padding(left=padding_val, top=padding_val,
                           right=padding_val, bottom=padding_val),
        **kwargs,
    )

def txt_field(label, value="", hint="") -> ft.TextField:
    """Campo de texto con estilos estándar del proyecto."""
    return ft.TextField(
        label=label, value=value, hint_text=hint,
        color=TEXT_MAIN, bgcolor=DARK_BG,
        border_color=BORDER_COL, focused_border_color=ACCENT_CYAN,
        cursor_color=ACCENT_CYAN, border_radius=8, expand=True,
    )
