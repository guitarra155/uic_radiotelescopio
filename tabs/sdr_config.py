"""
tabs/sdr_config.py
Lógica y UI para la pestaña de "Configuración SDR" y Lector .iq
"""

import flet as ft
import os
from constants import *
from components.shared import panel, txt_field
from dsp_engine import engine_instance

def build_config(page: ft.Page) -> ft.Control:
    # --- Ruta de Archivo Directa ---
    # Reemplazamos FilePicker porque flet > 0.80 extrajo muchos controles binarios a paquetes separados.
    # Usar un TextField es un proxy 100% confiable.
    filepath_input = txt_field("Ruta del Archivo .iq", engine_instance.iq_filename, "Ej: C:\\Datos\\señal.iq")
    filepath_input.on_change = lambda e: setattr(engine_instance, 'iq_filename', e.control.value)

    def dd(label, value, options):
        return ft.Dropdown(
            label=label, value=value,
            options=[ft.dropdown.Option(o) for o in options],
            color=TEXT_MAIN, bgcolor=DARK_BG,
            border_color=BORDER_COL, focused_border_color=ACCENT_CYAN,
            border_radius=8, expand=True,
        )

    algo_dd = dd("Algoritmo", "Periodograma (FFT)", ["Periodograma (FFT)", "Burg", "Yule"])
    fmt_dd  = dd("Formato Datos .iq", engine_instance.iq_format, ["uint8", "int8", "complex64"])
    fmt_dd.on_change = lambda e: setattr(engine_instance, 'iq_format', e.control.value)

    # --- Selector de Modo de Adquisición ---
    mode_rg = ft.RadioGroup(
        value=engine_instance.stream_mode,
        on_change=lambda e: setattr(engine_instance, 'stream_mode', e.control.value),
        content=ft.Row([
            ft.Radio(value="sdr", label="🛰️ SDR Físico (RTL/HackRF)", active_color=ACCENT_GREEN),
            ft.Radio(value="file", label="📼 Archivo Local (.iq)", active_color=ACCENT_AMBER),
        ])
    )

    freq_f = txt_field("Frecuencia (MHz)", "1420.40", "e.g. 1420.40")
    rate_f = txt_field("Sample Rate (MSps)", "2.4", "")
    
    def sec(t): return ft.Text(t, color=ACCENT_CYAN, size=13, weight=ft.FontWeight.BOLD)

    # --- Ajuste de Rangos Dinámicos dBFS ---
    db_min_f = txt_field("Min Rango Y (dBFS)", str(engine_instance.db_min), "Ej: -100")
    db_max_f = txt_field("Max Rango Y (dBFS)", str(engine_instance.db_max), "Ej: -40")
    
    # --- Ajuste de Zoom Frecuencial (Crop X) ---
    f_min_f = txt_field("Min Rango X (MHz)", str(engine_instance.f_min), "Ej: 1419.0")
    f_max_f = txt_field("Max Rango X (MHz)", str(engine_instance.f_max), "Ej: 1421.0")
    
    # --- Ajuste de Historial Waterfall ---
    waterfall_sec_f = txt_field("Historial Cascada (Segundos)", str(engine_instance.waterfall_history_sec), "Ej: 60")
    
    def update_bounds(e):
        try: engine_instance.db_min = float(db_min_f.value)
        except ValueError: pass
        try: engine_instance.db_max = float(db_max_f.value)
        except ValueError: pass
        try: engine_instance.f_min = float(f_min_f.value)
        except ValueError: pass
        try: engine_instance.f_max = float(f_max_f.value)
        except ValueError: pass
        try: engine_instance.waterfall_history_sec = float(waterfall_sec_f.value)
        except ValueError: pass

    for field in [db_min_f, db_max_f, f_min_f, f_max_f, waterfall_sec_f]:
        field.on_change = update_bounds
        field.on_submit = update_bounds

    form = panel(
        width=560,
        padding_val=24,
        content=ft.Column([
            sec("⚙️ Fuente de Adquisición de Datos"),
            ft.Divider(color=BORDER_COL, height=14),
            mode_rg,
            ft.Divider(color=BORDER_COL, height=14),
            sec("📂 Lector de Archivos .iq (Streaming Offline)"),
            ft.Divider(color=BORDER_COL, height=14),
            ft.Container(content=filepath_input, height=50),
            ft.Container(height=5),
            ft.Container(content=ft.Row([fmt_dd, algo_dd], spacing=14), height=55),
            ft.Divider(color=BORDER_COL, height=16),
            sec("📡 Parámetros de Adquisición SDR"),
            ft.Divider(color=BORDER_COL, height=8),
            ft.Container(content=ft.Row([freq_f, rate_f], spacing=14), height=50),
            ft.Divider(color=BORDER_COL, height=4),
            ft.Row([ft.Text("Escala de Gráficos (Rango Y de Potencia):", color=TEXT_MUTED, size=11)]),
            ft.Container(content=ft.Row([db_min_f, db_max_f], spacing=14), height=50),
            ft.Container(height=2),
            ft.Row([ft.Text("Zoom Frecuencial (Rango X Central en MHz):", color=TEXT_MUTED, size=11)]),
            ft.Container(content=ft.Row([f_min_f, f_max_f], spacing=14), height=50),
            ft.Container(height=2),
            ft.Row([ft.Text("Memoria del Espectrograma (Eje Y de Cascada):", color=TEXT_MUTED, size=11)]),
            ft.Container(content=ft.Row([waterfall_sec_f], spacing=14), height=50),
            ft.Container(height=20) # Espaciado inferior para que el scroll termine limpio
        ], spacing=10, scroll=ft.ScrollMode.AUTO),
    )

    dev_rows = [("Modelo SDR",  "RTL-SDR v3 / HackRF", TEXT_MAIN),
                ("Conexión",    "Archivo Local (.iq)",  ACCENT_CYAN),
                ("Estado",      "Listo para leer",      ACCENT_GREEN),
                ("Temperatura", "-- °C",                TEXT_MUTED),
                ("DSP Worker",  "Multihilo Async",      TEXT_MAIN)]

    info_rows = [ft.Row([ft.Text(k, color=TEXT_MUTED, size=11, expand=1),
                          ft.Text(v, color=c, size=11, expand=1,
                                  weight=ft.FontWeight.W_600)])
                 for k, v, c in dev_rows]

    status_p = panel(
        expand=True,
        content=ft.Column([
            ft.Text("📊 Estado de Adquisición", color=ACCENT_CYAN, size=13,
                    weight=ft.FontWeight.BOLD),
            ft.Divider(color=BORDER_COL, height=12),
            *info_rows,
            ft.Divider(color=BORDER_COL, height=12),
            ft.Text("💡 Instrucciones Streaming", color=ACCENT_GREEN, size=11,
                    weight=ft.FontWeight.BOLD),
            ft.Text(
                "1. En 'Examinar', ubique el archivo .iq guardado en su PC.\n"
                "2. Elija el formato correcto (RTL-SDR usa uint8, GNURadio usa complex64).\n"
                "3. Presione 'Reproducir'. Las pestañas Espectro y Waterfall\n"
                "   se animarán procesando bloques sin saturar el disco duro.",
                color=TEXT_MUTED, size=10, selectable=True,
            ),
        ], spacing=8),
    )

    return ft.Container(
        content=ft.Row([form, status_p], spacing=12, expand=True),
        expand=True,
        padding=ft.Padding(left=14, top=14, right=14, bottom=14),
    )
