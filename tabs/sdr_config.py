"""
tabs/sdr_config.py
Lógica y UI para la pestaña de "Configuración SDR"
"""

import flet as ft
from constants import *
from components.shared import panel, txt_field

def build_config(page: ft.Page) -> ft.Control:
    def dd(label, value, options):
        return ft.Dropdown(
            label=label, value=value,
            options=[ft.dropdown.Option(o) for o in options],
            color=TEXT_MAIN, bgcolor=DARK_BG,
            border_color=BORDER_COL, focused_border_color=ACCENT_CYAN,
            border_radius=8, expand=True,
        )

    algo_dd = dd("Algoritmo Espectral", "Periodograma",
                 ["Periodograma", "Burg", "Yule-Walker"])
    fft_dd  = dd("Ventana FFT", "Hanning",
                 ["Hanning", "Hamming", "Blackman", "Kaiser", "Rectangular"])

    freq_f = txt_field("Frecuencia Central (MHz)", "1420.40", "e.g. 1420.40")
    gain_f = txt_field("Ganancia (dB)", "40", "0 – 49.6 dB")
    rate_f = txt_field("Sample Rate (Msps)", "2.4", "e.g. 2.4")
    fft_sz = txt_field("Tamaño FFT (puntos)", "4096", "potencia de 2")
    avg_f  = txt_field("Promediado (frames)", "10", "1 – 100")

    save_btn  = ft.Button(
        content="💾  Aplicar Configuración", bgcolor=ACCENT_CYAN, color=DARK_BG,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)))
    reset_btn = ft.Button(
        content="↺  Restablecer Defaults", color=TEXT_MUTED,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8),
                             side=ft.BorderSide(1, BORDER_COL)))

    def sec(t): return ft.Text(t, color=ACCENT_CYAN, size=13, weight=ft.FontWeight.BOLD)

    form = panel(
        width=560,
        padding_val=24,
        content=ft.Column([
            sec("📡  Parámetros del Receptor SDR"),
            ft.Divider(color=BORDER_COL, height=14),
            ft.Row([algo_dd], expand=True),
            ft.Divider(color=BORDER_COL, height=10),
            sec("🔧  Parámetros de Adquisición"),
            ft.Divider(color=BORDER_COL, height=8),
            ft.Row([freq_f, gain_f], spacing=14, expand=True),
            ft.Row([rate_f], expand=True),
            ft.Divider(color=BORDER_COL, height=16),
            sec("⚙️  Procesamiento de Señal"),
            ft.Divider(color=BORDER_COL, height=8),
            ft.Row([fft_dd], expand=True),
            ft.Row([fft_sz, avg_f], spacing=14, expand=True),
            ft.Divider(color=BORDER_COL, height=20),
            ft.Row([save_btn, reset_btn], spacing=12),
        ], spacing=10),
    )

    dev_rows = [("Modelo SDR",  "RTL-SDR v3 / HackRF", TEXT_MAIN),
                ("Conexión",    "USB 2.0",              TEXT_MAIN),
                ("Estado",      "Desconectado",         ACCENT_RED),
                ("Temperatura", "-- °C",                TEXT_MUTED),
                ("Driver",      "rtlsdr 0.6.0",         TEXT_MAIN),
                ("PPM Offset",  "0 ppm",                TEXT_MUTED),
                ("Buffer",      "16 × 512 KB",          TEXT_MAIN)]

    info_rows = [ft.Row([ft.Text(k, color=TEXT_MUTED, size=11, expand=1),
                          ft.Text(v, color=c, size=11, expand=1,
                                  weight=ft.FontWeight.W_600)])
                 for k, v, c in dev_rows]

    status_p = panel(
        expand=True,
        content=ft.Column([
            ft.Text("📊  Estado del Dispositivo", color=ACCENT_CYAN, size=13,
                    weight=ft.FontWeight.BOLD),
            ft.Divider(color=BORDER_COL, height=12),
            *info_rows,
            ft.Divider(color=BORDER_COL, height=12),
            ft.Text("💡 Instrucciones", color=ACCENT_GREEN, size=11,
                    weight=ft.FontWeight.BOLD),
            ft.Text(
                "1. Conecte el SDR por USB.\n"
                "2. Configure la frecuencia central y el sample rate.\n"
                "3. Seleccione el algoritmo espectral deseado.\n"
                "4. Presione 'Aplicar Configuración'.\n"
                "5. Active el Smart Trigger en la pestaña de Estadística.",
                color=TEXT_MUTED, size=10, selectable=True,
            ),
        ], spacing=8),
    )

    return ft.Container(
        content=ft.Row([form, status_p], spacing=12, expand=True),
        expand=True,
        padding=ft.Padding(left=14, top=14, right=14, bottom=14),
    )
