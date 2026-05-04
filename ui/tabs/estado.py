import flet as ft
from core.constants import *

def build_estado(page: ft.Page) -> ft.Control:
    dev_rows = [
        ("Modelo SDR", "RTL-SDR v3 / HackRF", TEXT_MAIN),
        ("Conexión", "Archivo Local (.iq) / Físico", ACCENT_CYAN),
        ("Estado", "Listo", ACCENT_GREEN),
        ("Temperatura", "-- °C", TEXT_MUTED),
        ("DSP Worker", "Multihilo Async", TEXT_MAIN),
    ]

    info_rows = [
        ft.Row(
            [
                ft.Text(k, color=TEXT_MUTED, size=14, expand=1),
                ft.Text(v, color=c, size=14, expand=2, weight=ft.FontWeight.W_600),
            ]
        )
        for k, v, c in dev_rows
    ]

    estado_content = ft.Column(
        [
            *info_rows,
            ft.Divider(color=BORDER_COL, height=16),
            ft.Text(
                "💡 Instrucciones de Uso",
                color=ACCENT_GREEN,
                size=16,
                weight=ft.FontWeight.BOLD,
            ),
            ft.Text(
                "1. Ubique el archivo .iq guardado en su PC en la pestaña Fuente & SDR.\n"
                "2. Elija el formato de datos correcto.\n"
                "3. Configure la Frecuencia Central y el Sample Rate.\n"
                "4. Presione 'Reproducir' en la barra superior para iniciar el procesamiento.",
                color=TEXT_MUTED,
                size=14,
            ),
        ],
        spacing=12,
    )

    return ft.Container(
        content=estado_content,
        expand=True,
        padding=ft.Padding(left=40, top=40, right=40, bottom=40),
    )
