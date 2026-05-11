import flet as ft
from core.constants import *
import tkinter as tk
from tkinter import filedialog
import asyncio
from ui.components.shared import txt_field

def build_estado(page: ft.Page) -> ft.Control:
    from core.dsp_engine import engine_instance

    def dd(label, value, options):
        return ft.Dropdown(
            label=label,
            value=value,
            options=[ft.dropdown.Option(o) for o in options],
            color=TEXT_MAIN,
            bgcolor=DARK_BG,
            border_color=BORDER_COL,
            focused_border_color=ACCENT_CYAN,
            border_radius=8,
            expand=True,
        )

    filepath_input = txt_field(
        "Ruta del Archivo .iq", engine_instance.iq_filename, "Ej: C:\\Datos\\señal.iq"
    )

    async def on_pick_file(e):
        def _pick():
            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            path = filedialog.askopenfilename(
                title="Seleccionar archivo .iq",
                filetypes=[("Archivos IQ", "*.iq"), ("Todos", "*.*")]
            )
            root.destroy()
            return path

        selected_path = await asyncio.to_thread(_pick)
        if selected_path:
            filepath_input.value = selected_path
            engine_instance.iq_filename = selected_path
            engine_instance.save_config()
            page.update()

    pick_btn = ft.ElevatedButton(
        content=ft.Text("📁 Abrir", size=11),
        on_click=on_pick_file,
        tooltip="Seleccionar archivo .iq",
        style=ft.ButtonStyle(
            color=TEXT_MAIN,
            bgcolor=PANEL_BG,
            shape=ft.RoundedRectangleBorder(radius=8),
        ),
    )

    def on_filepath_change(e):
        engine_instance.iq_filename = e.control.value
        engine_instance.save_config()

    filepath_input.on_change = on_filepath_change

    fmt_dd = dd(
        "Formato Datos .iq", engine_instance.iq_format, ["uint8", "int8", "int16", "complex64"]
    )

    def on_fmt_change(e):
        engine_instance.iq_format = e.control.value
        engine_instance.save_config()

    fmt_dd.on_change = on_fmt_change

    def on_mode_change(e):
        engine_instance.stream_mode = e.control.value
        engine_instance.save_config()

    mode_rg = ft.RadioGroup(
        value=engine_instance.stream_mode,
        on_change=on_mode_change,
        content=ft.Column(
            [
                ft.Radio(value="sdr", label="🛠️ SDR Físico (RTL/HackRF)", active_color=ACCENT_GREEN),
                ft.Radio(value="file", label="📼 Archivo Local (.iq)", active_color=ACCENT_AMBER),
            ],
            spacing=4,
        ),
    )

    freq_f = txt_field("Frecuencia (MHz)", f"{engine_instance.center_freq:.8f}", "e.g. 1420.40")
    rate_f = txt_field("Sample Rate (MSps)", f"{engine_instance.sample_rate / 1e6:.8f}", "")
    span_visual_f = txt_field("Span Visual (Zoom MHz)", f"{engine_instance.visual_span_mhz:.8f}", "e.g. 1.0")

    ref_level_f = txt_field("Nivel Ref. (dBm)", f"{engine_instance.bb60c_ref_level:.8f}", "-100 a +20")
    rbw_f = txt_field("RBW / IQ BW (MHz)", f"{engine_instance.bb60c_iq_bw:.8f}", "0.1 a 20.0")
    vbw_alpha_f = txt_field("VBW Smoothing", f"{engine_instance.vbw_alpha:.8f}", "0.1-1.0")

    def on_global_change(e, attr, factor=1.0):
        try:
            val = float(e.control.value) * factor
            if attr == "bb60c_iq_bw": val = max(0.1, min(40.0, val))
            if attr == "bb60c_ref_level": val = max(-100.0, min(20.0, val))
            
            setattr(engine_instance, attr, val)
            
            # Avisar al hilo de hardware que reconfigure en vivo si es un parámetro físico
            if attr in ["sample_rate", "bb60c_ref_level", "bb60c_iq_bw"]:
                engine_instance._retune_requested = True
                
            engine_instance.save_config()
        except ValueError: pass

    freq_f.on_submit = lambda e: on_global_change(e, "center_freq")
    rate_f.on_submit = lambda e: on_global_change(e, "sample_rate", factor=1e6)
    ref_level_f.on_submit = lambda e: on_global_change(e, "bb60c_ref_level")
    rbw_f.on_submit       = lambda e: on_global_change(e, "bb60c_iq_bw")
    vbw_alpha_f.on_submit = lambda e: on_global_change(e, "vbw_alpha")
    
    # También aplicar a on_blur para que guarde si hacen click fuera del campo
    freq_f.on_blur = lambda e: on_global_change(e, "center_freq")
    rate_f.on_blur = lambda e: on_global_change(e, "sample_rate", factor=1e6)
    ref_level_f.on_blur = lambda e: on_global_change(e, "bb60c_ref_level")
    rbw_f.on_blur       = lambda e: on_global_change(e, "bb60c_iq_bw")
    vbw_alpha_f.on_blur = lambda e: on_global_change(e, "vbw_alpha")

    def on_span_change(e):
        try:
            val = float(e.control.value)
            engine_instance.update_visual_span(val)
            engine_instance.save_config()
        except: pass
    
    span_visual_f.on_submit = on_span_change
    span_visual_f.on_blur = on_span_change

    def lbl(t, color=TEXT_MUTED, size=12):
        return ft.Text(t, color=color, size=size)

    def section_title(icon, title, color=ACCENT_CYAN):
        return ft.Container(
            content=ft.Text(f"{icon}  {title}", color=color, size=18, weight=ft.FontWeight.BOLD),
            bgcolor="#0D1117",
            border_radius=4,
            padding=ft.Padding(left=12, top=8, right=12, bottom=8),
            margin=ft.Margin(top=15, bottom=5, left=0, right=0)
        )

    from ui.components.shared import panel

    # Layout de la pestaña en tarjetas (Panels)
    
    # Tarjeta 1: Origen de Datos
    data_source_card = panel(
        content=ft.Column([
            section_title("📁", "Origen de Datos", TEXT_MAIN),
            ft.Row([filepath_input, pick_btn], spacing=10),
            ft.Container(height=5),
            fmt_dd,
            ft.Container(height=5),
            mode_rg,
        ], spacing=10)
    )

    analysis_f = txt_field("Ventana Analisis (s)", f"{engine_instance.analysis_window_sec:.8f}", "e.g. 1.0")
    waterfall_f = txt_field("Historial Cascada (s)", f"{engine_instance.waterfall_history_sec:.8f}", "e.g. 10.0")

    def on_analysis_change(e):
        try:
            val = float(e.control.value)
            engine_instance.analysis_window_sec = val
            engine_instance.save_config()
        except ValueError: pass

    def on_waterfall_change(e):
        try:
            val = float(e.control.value)
            engine_instance.waterfall_history_sec = val
            engine_instance.save_config()
        except ValueError: pass

    analysis_f.on_submit = on_analysis_change
    analysis_f.on_blur = on_analysis_change
    waterfall_f.on_submit = on_waterfall_change
    waterfall_f.on_blur = on_waterfall_change

    # Tarjeta 2: SDR & Frecuencia
    freq_card = panel(
        content=ft.Column([
            section_title("🌍", "SDR & Frecuencia", ACCENT_GREEN),
            freq_f,
            span_visual_f,
            rate_f,
            ft.Divider(color=BORDER_COL, height=10),
            ft.Text("Ventana de Adquisicion", color=ACCENT_AMBER, size=12, weight=ft.FontWeight.W_600),
            analysis_f,
            waterfall_f,
        ], spacing=15)
    )

    # Tarjeta 3: Hardware (BB60C)
    hw_card = panel(
        content=ft.Column([
            section_title("🔧", "Hardware (BB60C)", ACCENT_CYAN),
            ref_level_f,
            lbl("Ajusta el techo de entrada para no saturar.", size=10),
            ft.Container(height=5),
            rbw_f,
            lbl("Filtro físico del SDR. Valores bajos = menos ruido.", size=10),
            ft.Container(height=5),
            vbw_alpha_f,
            lbl("0.1 = Muy filtrado, 1.0 = Tiempo Real/Puro.", size=10),
        ], spacing=5)
    )

    config_col = ft.Column([
        data_source_card,
        freq_card,
        hw_card,
    ], spacing=20, expand=5, scroll=ft.ScrollMode.AUTO)

    # Añadir sección de estado informativo
    dev_rows = [
        ("Modelo SDR", "BB60C", TEXT_MAIN),
        ("Estado DSP", "Multihilo", ACCENT_GREEN),
    ]
    info_rows = [
        ft.Row([
            ft.Text(k, color=TEXT_MUTED, size=14, expand=2),
            ft.Text(v, color=c, size=14, expand=3, weight=ft.FontWeight.W_600),
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
        for k, v, c in dev_rows
    ]

    md_tabs = ft.Markdown(
        "**📚 Pestañas y Componentes**\n\n"
        "- **Monitoreo Dual (RAW/MA):** Visualización comparativa de la señal bruta vs. filtrada. Permite monitorear RFI y el efecto del Moving Average en tiempo real.\n"
        "- **Espectrograma (Cascada):** Representación 2D. El eje vertical es el tiempo, el horizontal la frecuencia, y el color es la potencia espectral. Ideal para rastrear meteoros y satélites.\n"
        "- **Estadística:** Muestra el histograma gaussiano de las muestras. Si hay desvíos fuertes de la campana, indica saturación o interferencia no lineal.\n"
        "- **SNR vs. Frecuencia:** *Signal-to-Noise Ratio* (Relación Señal a Ruido). Mide qué tan por encima del ruido de fondo térmico están los picos. SNR > 0 dB significa detección probable.\n"
        "- **Algoritmo DSP:** Aplicación de matemáticas complejas sobre señales bloqueadas o congeladas.",
        selectable=True,
    )

    md_hw = ft.Markdown(
        "**📻 Conceptos de SDR, Hardware y Live Tuning**\n\n"
        "- **Frecuencia Central (MHz):** Determina el punto medio del espectro físico monitoreado.\n  *Rango:* 0.009 MHz a 6000 MHz (depende del BB60C).\n  *Efecto:* Su cambio aplica **Sintonización en Vivo (Live Tuning)**, moviendo los osciladores físicos de la antena sin detener el software.\n"
        "- **Sample Rate / Tasa de Muestreo (MSps):** Velocidad de captura del ADC. Dicta tu \"ancho de banda visual\" total.\n  *Rango:* 1.0 a 40.0 MSps.\n  *Efecto:* Valores altos permiten ver bandas gigantes (como WiFi completo) pero exigen mucha CPU. Se aplica en tiempo real ajustando la decimación del hardware.\n"
        "- **Nivel de Referencia (dBm):** Controla el pre-amplificador (LNA). Actúa como techo de potencia para evitar la saturación (`ADC Overflow`).\n  *Rango:* -100 dBm (Máxima ganancia) a +20 dBm (Mínima ganancia).\n  *Efecto:* Si buscas señales astronómicas, usa -80. Si monitoreas radares o TV, usa 0 o +10 para evitar saturación cruzada.\n"
        "- **RBW / IQ BW (MHz):** Filtro Pasa-Banda de hardware para la captura I/Q.\n  *Rango:* 0.1 MHz a 40.0 MHz.\n  *Efecto:* Cerrar este valor aisla la señal deseada y mata el ruido térmico adyacente. Se re-sintetiza al presionar Enter.\n"
        "- **VBW Smoothing (Video Bandwidth):** Promedio matemático temporal (EMA) sobre el espectro dibujado.\n  *Rango:* 0.1 (Muy suavizado, revela pulsos débiles y estables) a 1.0 (Sin suavizado, 100% caótico y físico).\n  *Efecto:* Aplicado solo en software, es instantáneo y no interrumpe al hardware.\n"
        "- **Live Tuning (Reconfiguración al Vuelo):** Todos estos controles se aplican *al presionar Enter o quitar el cursor (Blur)*. El motor inyecta comandos C++ (`bb_abort` y `bb_initiate`) reiniciando el dispositivo en un lapso de milisegundos sin congelar la ventana gráfica.",
        selectable=True,
    )

    md_dsp = ft.Markdown(
        "**🔬 Matemáticas y Algoritmos (DSP)**\n\n"
        "- **FFT (Fast Fourier Transform):** Algoritmo clásico para obtener frecuencias. Es extremadamente rápido pero sufre de *fugas espectrales* (spectral leakage) y enmascaramiento por resolución limitada.\n"
        "- **Welch PSD:** Calcula la Densidad Espectral de Potencia mediante la división del bloque en ventanas que se solapan (overlap) y se promedian. Resulta en gráficas libres de picos de ruido esporádicos.\n"
        "- **Correlograma:** Estimación espectral indirecta basada en el *Teorema de Wiener-Khinchin*. Calcula la autocorrelación de la señal, le aplica una ventana temporal y luego su FFT. Excelente para revelar señales periódicas ocultas en ruido térmico.\n"
        "- **CWT (Continuous Wavelet Transform):** Utiliza la ondícula de *Morlet* (una sinusoide envuelta en una gaussiana). Escanea la señal para entregar un mapa ultra-preciso de correlación de Tiempo y Frecuencia.\n"
        "- **MUSIC & ESPRIT:** Algoritmos de subespacios ortogonales. Descomponen la matriz de covarianza de la señal separando matemáticamente el \"Subespacio de Señal\" del \"Subespacio de Ruido\". Permiten calcular frecuencias de sinusoides puras con resolución infinita teórica.\n"
        "- **Filtro MA (Moving Average):** Filtro FIR (*Finite Impulse Response*) pasa-bajos simple temporal que limpia ruido térmico de alta frecuencia instantáneo.",
        selectable=True,
    )

    md_trigger = ft.Markdown(
        "**⚡ Smart Trigger y Eventos Transitorios**\n\n"
        "- **Magnitud de Energía ($I^2 + Q^2$):** La potencia base instantánea de la señal analítica compleja. Se utiliza como métrica principal para disparar la captura de eventos.\n"
        "- **Umbrales e Histéresis:** Dos límites (Alto y Bajo). El algoritmo captura cuando se supera el *Umbral Alto* y finaliza cuando cae bajo el *Umbral Bajo*, previniendo \"falsos positivos\" repetitivos por el ruido estadístico.\n"
        "- **Recorte Automático (Trim $\\pm 1.5s$):** El algoritmo iterativo localiza el centro exacto del pulso detectado y recorta 3 segundos íntegros (1.5 segundos a cada lado). Preservar el silencio antes y después del evento es crucial para validar detecciones en radioastronomía.\n"
        "- **Zero-Crossing Rate (ZCR):** Tasa de cruces por cero. Una métrica rápida en el dominio del tiempo. El ruido puramente térmico tiene un ZCR altísimo y desordenado; pulsos coherentes reducen significativamente esta tasa.",
        selectable=True,
    )

    docs_panel = ft.ExpansionPanelList(
        expand_icon_color=ACCENT_CYAN,
        elevation=0,
        divider_color=BORDER_COL,
        controls=[
            ft.ExpansionPanel(
                header=ft.ListTile(title=ft.Text("Módulos y Pestañas UI", color=ACCENT_AMBER, weight=ft.FontWeight.W_600)),
                content=ft.Container(content=md_tabs, padding=10, bgcolor=DARK_BG, border_radius=6),
            ),
            ft.ExpansionPanel(
                header=ft.ListTile(title=ft.Text("Parámetros SDR y Hardware", color=ACCENT_GREEN, weight=ft.FontWeight.W_600)),
                content=ft.Container(content=md_hw, padding=10, bgcolor=DARK_BG, border_radius=6),
            ),
            ft.ExpansionPanel(
                header=ft.ListTile(title=ft.Text("Procesamiento Digital (DSP)", color="#B380FF", weight=ft.FontWeight.W_600)),
                content=ft.Container(content=md_dsp, padding=10, bgcolor=DARK_BG, border_radius=6),
            ),
            ft.ExpansionPanel(
                header=ft.ListTile(title=ft.Text("Smart Trigger & Recorte", color=ACCENT_RED, weight=ft.FontWeight.W_600)),
                content=ft.Container(content=md_trigger, padding=10, bgcolor=DARK_BG, border_radius=6),
            ),
        ],
    )

    info_card = panel(
        content=ft.Column([
            section_title("📊", "Información del Sistema", ACCENT_AMBER),
            *info_rows,
            ft.Divider(color=BORDER_COL, height=15),
            ft.Text("📖 Enciclopedia Técnica y Glosario", color=TEXT_MAIN, size=16, weight=ft.FontWeight.BOLD),
            docs_panel
        ], spacing=15)
    )

    info_col = ft.Column([
        info_card
    ], spacing=20, expand=4, scroll=ft.ScrollMode.AUTO)

    return ft.Container(
        content=ft.Row([config_col, info_col], alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.START, spacing=30, expand=True),
        expand=True,
        padding=ft.Padding(left=30, top=20, right=30, bottom=40),
    )
