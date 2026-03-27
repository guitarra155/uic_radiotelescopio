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
    def on_filepath_change(e):
        engine_instance.iq_filename = e.control.value
        engine_instance.save_config()
    filepath_input.on_change = on_filepath_change

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
    def on_fmt_change(e):
        engine_instance.iq_format = e.control.value
        engine_instance.save_config()
    fmt_dd.on_change = on_fmt_change

    # --- Selector de Modo de Adquisición ---
    def on_mode_change(e):
        engine_instance.stream_mode = e.control.value
        engine_instance.save_config()
    mode_rg = ft.RadioGroup(
        value=engine_instance.stream_mode,
        on_change=on_mode_change,
        content=ft.Row([
            ft.Radio(value="sdr", label="🛠️ SDR Físico (RTL/HackRF)", active_color=ACCENT_GREEN),
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
    
    # --- Ajuste de Rango Amplitud (Y) ---
    amp_min_f = txt_field("Min Amplitud (V)", str(engine_instance.amp_min), "Ej: 0.0")
    amp_max_f = txt_field("Max Amplitud (V)", str(engine_instance.amp_max), "Ej: 1.0")
    
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
        try: engine_instance.amp_min = float(amp_min_f.value)
        except ValueError: pass
        try: engine_instance.amp_max = float(amp_max_f.value)
        except ValueError: pass
        try: engine_instance.waterfall_history_sec = float(waterfall_sec_f.value)
        except ValueError: pass
        # Guardar configuración automáticamente al cambiar cualquier valor
        engine_instance.save_config()

    for field in [db_min_f, db_max_f, f_min_f, f_max_f, amp_min_f, amp_max_f, waterfall_sec_f]:
        field.on_change = update_bounds
        field.on_submit = update_bounds

    form = panel(
        expand=True,
        padding_val=16,
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
            ft.Row([ft.Text("Rango de Amplitud (Min/Max Voltaje en Onda):", color=TEXT_MUTED, size=11)]),
            ft.Container(content=ft.Row([amp_min_f, amp_max_f], spacing=14), height=50),
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
        padding_val=16,
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
        ], spacing=8, scroll=ft.ScrollMode.ADAPTIVE),
    )

    # animate_size offloads tweening to Flutter's GPU natively so python doesn't need to brute-force FPS
    status_container = ft.Container(content=status_p, height=280, animate_size=50)

    import time
    drag_state = {"last_update": 0.0}

    def handle_drag(e):
        dy = 0.0
        # Flet deprecó on_pan_update silenciosamente en favor de on_vertical_drag_update con 'primary_delta'
        try: dy = float(getattr(e, 'primary_delta', getattr(e, 'delta_y', 0.0)))
        except: pass
        
        if dy == 0.0 and getattr(e, 'data', None):
            try:
                import json
                d = json.loads(e.data)
                dy = float(d.get("primary_delta", d.get("delta_y", d.get("dy", 0.0))))
            except: pass
            
        if dy != 0.0:
            new_h = max(80, min(800, status_container.height + dy))
            status_container.height = new_h
            
            # THROTTLE (Anti-Lag Extremo): Limitar a 20 FPS max (0.05s).
            # Flutter GPU interpola el espacio intermedio gracias a animate_size
            now = time.time()
            if now - drag_state.get("last_update", 0.0) > 0.05:
                if status_container.page:
                    status_container.update()
                drag_state["last_update"] = now

    def handle_drag_end(e):
        # Asegura la última actualización perfecta cuando suelta el click
        if status_container.page:
            status_container.update()

    splitter = ft.GestureDetector(
        mouse_cursor=ft.MouseCursor.RESIZE_UP_DOWN,
        on_pan_update=handle_drag,
        on_vertical_drag_update=handle_drag,
        on_pan_end=handle_drag_end,
        on_vertical_drag_end=handle_drag_end,
        content=ft.Container(
            height=12,
            bgcolor="transparent",
            content=ft.Divider(color=BORDER_COL, height=2)
        )
    )

    return ft.Container(
        content=ft.Column([status_container, splitter, form], spacing=2, expand=True),
        expand=True,
        padding=ft.Padding(left=10, top=14, right=14, bottom=14),
    )
