"""
components/shared.py
Componentes UI reutilizables estilo "Widgets" para consistencia de diseño.
Usa import de módulo para que los colores se actualicen con el tema activo.
"""

import flet as ft
import core.constants as C

def border_all(width=1, color=None) -> ft.Border:
    """Retorna un borde completo para Flet 0.82."""
    if color is None:
        color = C.BORDER_COL
    s = ft.BorderSide(width, color)
    return ft.Border(top=s, right=s, bottom=s, left=s)

def panel(padding_val=18, **kwargs) -> ft.Container:
    """Contenedor estándar tipo Panel, con borde y fondo acordes al tema."""
    return ft.Container(
        bgcolor=C.PANEL_BG,
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
        color=C.TEXT_MAIN, bgcolor=C.DARK_BG,
        border_color=C.BORDER_COL, focused_border_color=C.ACCENT_CYAN,
        cursor_color=C.ACCENT_CYAN, border_radius=8,
    )
