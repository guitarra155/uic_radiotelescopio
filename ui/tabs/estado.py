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
            
            if getattr(engine_instance, "is_playing", False) and engine_instance.stream_mode == "file":
                # Forzar recarga automática del nuevo archivo sin tener que pulsar Stop/Start
                engine_instance.file_position = 0
                engine_instance.stop_stream()
                engine_instance.start_stream("file", {"filename": selected_path, "format": engine_instance.iq_format})
                
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
        if getattr(engine_instance, "is_playing", False) and engine_instance.stream_mode == "file":
            engine_instance.file_position = 0
            engine_instance.stop_stream()
            engine_instance.start_stream("file", {"filename": e.control.value, "format": engine_instance.iq_format})

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
                ft.Radio(value="sdr", label="📡 Hardware", active_color=ACCENT_GREEN),
                ft.Radio(value="file", label="📼 Archivo Local (.iq)", active_color=ACCENT_AMBER),
            ],
            spacing=4,
        ),
    )

    def fmt_float(v, max_dec=8):
        try:
            s = f"{float(v):.{max_dec}f}"
            return s.rstrip('0').rstrip('.') if '.' in s else s
        except:
            return str(v)

    freq_f = txt_field("Frecuencia (MHz)", fmt_float(engine_instance.center_freq), "e.g. 1420.40")
    
    # --- Selector de Sample Rate tipo Chips (Flawless Wrap) ---
    rate_container = ft.Column([
        ft.Text("Sample Rate (MSps)", color=TEXT_MUTED, size=11),
        ft.Container(height=4),
    ], spacing=0)
    
    buttons_list = []
    
    def on_rate_click(e, rate_val):
        val = float(rate_val) * 1e6
        engine_instance.sample_rate = val
        engine_instance._retune_requested = True
        engine_instance.save_config()
        
        # Refrescar visualmente todos los botones en este panel
        for btn in buttons_list:
            if btn.data == rate_val:
                btn.bgcolor = ACCENT_CYAN
                btn.content.color = DARK_BG
            else:
                btn.bgcolor = PANEL_BG
                btn.content.color = TEXT_MAIN
            try: btn.update()
            except: pass
            
        try:
            e.control.page.pubsub.send_all("refresh_charts")
        except: pass

    current_sr = engine_instance.sample_rate / 1e6
    sr_str = f"{current_sr:.1f}" if current_sr.is_integer() else str(current_sr).rstrip('0').rstrip('.')
    if '.' not in sr_str: sr_str += ".0"

    rate_opts = ["40.0", "20.0", "10.0", "5.0", "2.5", "1.25", "0.625", "0.3125"]
    buttons_row = ft.Row(wrap=True, spacing=5, run_spacing=5)
    
    for opt in rate_opts:
        is_selected = (opt == sr_str)
        btn = ft.Container(
            content=ft.Text(opt, size=10, weight=ft.FontWeight.BOLD, color=DARK_BG if is_selected else TEXT_MAIN),
            bgcolor=ACCENT_CYAN if is_selected else PANEL_BG,
            border=ft.border.all(1, BORDER_COL),
            border_radius=6,
            padding=ft.padding.all(0),
            alignment=ft.Alignment(0, 0),
            width=50,
            height=28,
            on_click=lambda e, opt_val=opt: on_rate_click(e, opt_val),
            data=opt
        )
        buttons_list.append(btn)
        buttons_row.controls.append(btn)
        
    rate_container.controls.append(buttons_row)

    span_visual_f = txt_field("Span Visual (Zoom MHz)", fmt_float(engine_instance.visual_span_mhz), "e.g. 1.0")

    ref_level_f = txt_field("Nivel Ref. (dBm)", fmt_float(engine_instance.bb60c_ref_level), "-100 a +20")
    rbw_f = txt_field("RBW / IQ BW (MHz)", fmt_float(engine_instance.bb60c_iq_bw), "0.1 a 20.0")
    vbw_alpha_f = txt_field("VBW Smoothing", fmt_float(engine_instance.vbw_alpha), "0.1-1.0")

    def on_global_change(e, attr, factor=1.0):
        try:
            val = float(e.control.value) * factor
            if attr == "bb60c_iq_bw": val = max(0.1, min(40.0, val))
            if attr == "bb60c_ref_level": val = max(-100.0, min(20.0, val))
            
            setattr(engine_instance, attr, val)
            
            # Avisar al hilo que reconfigure en vivo (para SDR y sintonía digital en archivos)
            if attr in ["center_freq", "sample_rate", "bb60c_ref_level", "bb60c_iq_bw"]:
                engine_instance._retune_requested = True
                
            engine_instance.save_config()
            
            # Refrescar todas las gráficas y componentes visuales en todas las pestañas
            try:
                e.control.page.pubsub.send_all("refresh_charts")
            except: pass
        except ValueError: pass

    freq_f.on_submit = lambda e: on_global_change(e, "center_freq")
    ref_level_f.on_submit = lambda e: on_global_change(e, "bb60c_ref_level")
    rbw_f.on_submit       = lambda e: on_global_change(e, "bb60c_iq_bw")
    vbw_alpha_f.on_submit = lambda e: on_global_change(e, "vbw_alpha")
    
    # También aplicar a on_blur para que guarde si hacen click fuera del campo
    freq_f.on_blur = lambda e: on_global_change(e, "center_freq")
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
    
    # --- Controles del Smart Trigger ---
    def on_trigger_chk_change(e):
        engine_instance.trigger_active = e.control.value
        engine_instance.save_config()
        
    trigger_chk = ft.Checkbox(
        label="Smart Trigger (Captura de Transitorios)",
        value=bool(engine_instance.trigger_active),
        on_change=on_trigger_chk_change,
        active_color=ACCENT_CYAN,
        label_style=ft.TextStyle(color=TEXT_MAIN, size=11, weight=ft.FontWeight.BOLD)
    )
    
    def on_trig_high_change(e):
        try:
            engine_instance.trigger_high = float(e.control.value)
            engine_instance.save_config()
        except ValueError: pass

    def on_trig_low_change(e):
        try:
            engine_instance.trigger_low = float(e.control.value)
            engine_instance.save_config()
        except ValueError: pass

    trig_high_f = txt_field("Umbral Alto (Energía)", fmt_float(engine_instance.trigger_high), "e.g. 15.0")
    trig_low_f = txt_field("Umbral Bajo (Energía)", fmt_float(engine_instance.trigger_low), "e.g. 5.0")
    
    trig_high_f.on_submit = on_trig_high_change
    trig_high_f.on_blur = on_trig_high_change
    trig_low_f.on_submit = on_trig_low_change
    trig_low_f.on_blur = on_trig_low_change
    
    rfi_count_lbl = ft.Text(f"{engine_instance.rfi_event_count}", color=ACCENT_AMBER, size=14, weight=ft.FontWeight.BOLD)
    
    trigger_card = panel(
        content=ft.Column([
            section_title("⚡", "Eventos Transitorios & Trigger", ACCENT_CYAN),
            trigger_chk,
            lbl("Activa el autodisparo por picos de energía.", size=10),
            ft.Container(height=5),
            trig_high_f,
            lbl("Umbral de subida para disparar.", size=10),
            ft.Container(height=5),
            trig_low_f,
            lbl("Umbral de caída para terminar captura.", size=10),
            ft.Container(height=5),
            ft.Row([
                ft.Text("Capturas RFI / Transitorios:", color=TEXT_MUTED, size=12, expand=2),
                rfi_count_lbl
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
        ], spacing=10)
    )

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

    analysis_f = txt_field("Ventana Analisis (s)", fmt_float(engine_instance.analysis_window_sec), "e.g. 1.0")
    waterfall_f = txt_field("Historial Cascada (s)", fmt_float(engine_instance.waterfall_history_sec), "e.g. 10.0")

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

    def on_lock_toggle_change(e):
        engine_instance.auto_spectral_lock = e.control.value
        engine_instance.save_config()
        if not e.control.value:
            engine_instance._needs_spectral_lock = False
            
    lock_chk = ft.Checkbox(
        label="Activar Span",
        value=bool(engine_instance.auto_spectral_lock),
        on_change=on_lock_toggle_change,
        active_color=ACCENT_CYAN,
        label_style=ft.TextStyle(color=TEXT_MUTED, size=11)
    )

    # Tarjeta 2: Configuración
    freq_card = panel(
        content=ft.Column([
            section_title("🌍", "Configuración", ACCENT_GREEN),
            freq_f,
            lock_chk,
            span_visual_f,
            rate_container,
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
        "- **Señal y Filtrada:** Visualización comparativa de la señal bruta vs. filtrada. Permite monitorear RFI y el efecto del filtro FIR de media móvil en tiempo real.\n"
        "- **Espectrograma (Cascada):** Representación bidimensional temporal-frecuencial. Ofrece Waterfall clásico, transformada continua de Wavelet (Morlet), autoregresión lineal (Burg) y Correlograma. Ideal para rastrear transitorios y variaciones espectrales.\n"
        "- **Histograma & Estadística:** Calcula la distribución empírica de magnitud o fase. Realiza ajustes probabilísticos mediante estimación de máxima verosimilitud (MLE) a modelos **Gaussiano, Weibull y Rician** para clasificar la señal térmica frente a interferencias terrestres (RFI) o fuentes coherentes, computando la desviación SSE. En fase, evalúa la aproximación a una distribución Uniforme teórica ($1/2\\pi$).\n"
        "- **Potencia vs. Tiempo:** Registra la evolución de la potencia integrada en el tiempo usando un buffer circular de alta velocidad. Esencial para análisis temporal de pulsos.\n"
        "- **SNR vs. Frecuencia:** Visualización de la relación señal/ruido bin por bin mediante el algoritmo adaptativo CFAR, aislando picos por encima del ruido de fondo térmico dinámico.\n"
        "- **Algoritmo DSP:** Permite procesar de manera estática y avanzada el bloque de datos congelado en el review temporal.",
        selectable=True,
    )

    md_hw = ft.Markdown(
        "**📻 Conceptos de SDR, Hardware y Live Tuning**\n\n"
        "- **Frecuencia Central (MHz):** Punto medio del espectro físico monitoreado. Modificarla aplica un sintonizado dinámico en caliente (Live Tuning) sobre el oscilador local del hardware BB60C sin pausar el flujo de la aplicación.\n"
        "- **Sample Rate / Tasa de Muestreo (MSps):** Velocidad de digitalización del ADC del hardware. Físicamente, el BB60C digitaliza a 80 MSps de forma interna y reduce mediante decimación y filtrado anti-aliasing digital a un flujo digital final I/Q de hasta 40 MSps a través de USB 3.0 para cubrir un ancho de banda instantáneo calibrado de 27 MHz respetando el criterio de Nyquist.\n"
        "- **Nivel de Referencia (dBm):** Ajusta el rango dinámico del preamplificador (LNA). Actúa como límite superior de entrada analógica para evitar saturación y sobreflujo del ADC (ADC Overflow).\n"
        "- **RBW / IQ BW (MHz):** Ancho de banda de canal físico y filtro de hardware para la captura I/Q. Restringe el ruido térmico adyacente previo a la digitalización.\n"
        "- **VBW Smoothing:** Filtro de software tipo media móvil exponencial aplicado sobre las trazas de amplitud espectral de forma instantánea.\n"
        "- **Live Tuning (Reconfiguración en Caliente):** Al cambiar parámetros de hardware y confirmar (Enter o desenfoque del campo), el motor DSP aborta y reinicia de forma segura el stream de C++ del hardware mediante la API nativa sin congelar el renderizado visual de la GUI.",
        selectable=True,
    )

    md_dsp = ft.Markdown(
        "**🔬 Concurrencia y Procesamiento Digital (DSP)**\n\n"
        "- **Arquitectura Multihilo y Paralelismo:** La adquisición y el procesamiento se ejecutan en un hilo de trabajo secundario mediante la clase `threading.Thread` de forma asíncrona a la interfaz visual. Al invocar llamadas matemáticas pesadas (NumPy / transformadas de Fourier) y la API nativa de C++ (DLL) del BB60C, se libera el bloqueo global de intérprete (GIL) de Python, permitiendo al sistema operativo paralelizar las tareas entre los múltiples núcleos físicos del procesador.\n"
        "- **FFT (Fast Fourier Transform):** Algoritmo clásico para obtener frecuencias. Es extremadamente rápido pero sufre de fugas espectrales y enmascaramiento por resolución limitada.\n"
        "- **Welch PSD:** Estima la densidad espectral de potencia dividiendo la señal en bloques solapados que se ventanean y promedian, reduciendo significativamente la varianza del ruido.\n"
        "- **Correlograma:** Estimación espectral indirecta basada en el Teorema de Wiener-Khinchin que aplica la FFT a la función de autocorrelación, excelente para revelar periodicidades ocultas en ruido térmico.\n"
        "- **CWT (Continuous Wavelet Transform):** Correlación tiempo-frecuencia usando ondículas de Morlet para localizar transitorios de corta duración.",
        selectable=True,
    )

    md_trigger = ft.Markdown(
        "**⚡ Eventos Transitorios y Detección de Pulsos**\n\n"
        "- **Smart Trigger (Doble Umbral):** Detección temporal basada en la potencia base instantánea ($I^2 + Q^2$). Utiliza una histéresis regulable (típicamente 15 dB sobre el nivel base para disparar la captura y 5 dB para detenerla), previniendo activaciones espurias consecutivas debido a fluctuaciones del ruido térmico.\n"
        "- **CFAR (Constant False Alarm Rate):** Algoritmo espectral adaptativo en el dominio de la frecuencia. Estima bin por bin el piso de ruido dinámico restando la potencia media. Aquellos bins que superen un umbral establecido (típicamente 6 dB) son catalogados como señales candidatas y agrupados con una separación espectral mínima de 10 kHz.\n"
        "- **Recorte de Eventos (Trim $\\pm 1.5s$):** Localiza de forma retrospectiva el centro de gravedad del transitorio de energía detectado y realiza un recorte exacto de 3.0 segundos en disco para su análisis científico.\n"
        "- **Zero-Crossing Rate (ZCR):** Tasa de cruces por cero. Una métrica en el dominio del tiempo; señales de ruido térmico aleatorias presentan una tasa muy alta, mientras que pulsos coherentes la reducen considerablemente.",
        selectable=True,
    )

    md_user_manual = ft.Markdown(
        "**Guía Rápida de Operación**\n\n"
        "1. **Seleccionar Origen:** Elige capturar en vivo mediante **Hardware** o reproducir un archivo local **IQ** con su formato de datos correspondiente.\n"
        "2. **Iniciar Flujo:** Haz clic en **▶ Iniciar Adquisición** en el encabezado para iniciar el streaming en el hilo secundario.\n"
        "3. **Sintonización:** Ajusta la frecuencia central o el sample rate en el panel y presiona *Enter* para aplicar el sintonizado al vuelo.\n"
        "4. **Revisión Temporal:** Presiona **⏸ Pausar** para congelar el espectro. Usa las teclas **Coma (,)** para retroceder o **Punto (.)** para avanzar cuadro por cuadro en el historial de snapshots.\n"
        "5. **Procesamiento de Señal:** Con el flujo en pausa, utiliza la pestaña de *Algoritmos DSP* para procesar estáticamente el cuadro seleccionado.\n"
        "6. **Fijar Navegación:** Haz clic en el botón de la barra lateral (esquina inferior) para alternar entre el menú vertical colapsable o la barra superior horizontal clásica.",
        selectable=True,
    )

    md_shortcuts = ft.Markdown(
        "**⌨️ Atajos de Teclado y Control de Pantalla**\n\n"
        "- **CTRL + TAB / CTRL + SHIFT + TAB:** Navega secuencialmente entre las pestañas del sistema.\n"
        "- **CTRL + [1-6]:** Salta directamente a una pestaña (1: Inicio, 2: Monitoreo Dual, etc.).\n"
        "- **CTRL + B:** Oculta o muestra el panel lateral de visualización activa.\n"
        "- **CTRL + SHIFT + B:** Oculta o muestra el panel de configuración global del hardware.\n"
        "- **Coma (,) / Punto (.):** Navegación cuadro a cuadro hacia atrás o adelante durante la pausa de la captura.\n"
        "- **F1 - F4 (Pestaña 2):** Dibuja un recuadro amarillo para seleccionar una de las cuatro gráficas activas.\n"
        "- **CTRL + F1 - F4 (Pestaña 2):** Maximiza la gráfica correspondiente a pantalla completa o la restaura al diseño original.\n"
        "- **F1 - F4 (Pestaña 3):** Cambia el método espectral activo (F1: Waterfall, F2: CWT, F3: AR/Burg, F4: Correlograma).\n"
        "- **CTRL + F1 - F4 (Pestaña 3):** Maximiza el espectrograma activo a pantalla completa o lo restaura al tamaño normal.\n"
        "- **F5 / F8 / F11:** Controles de adquisición: iniciar/pausar (F5), detener (F8) y pantalla completa general (F11).",
        selectable=True,
    )

    docs_panel = ft.ExpansionPanelList(
        expand_icon_color=ACCENT_CYAN,
        elevation=0,
        divider_color=BORDER_COL,
        controls=[
            ft.ExpansionPanel(
                header=ft.ListTile(title=ft.Text("Manual de Usuario Rápido", color=ACCENT_CYAN, weight=ft.FontWeight.W_600)),
                content=ft.Container(content=md_user_manual, padding=10, bgcolor=DARK_BG, border_radius=6),
            ),
            ft.ExpansionPanel(
                header=ft.ListTile(title=ft.Text("Atajos de Teclado y Control", color="#FF9100", weight=ft.FontWeight.W_600)),
                content=ft.Container(content=md_shortcuts, padding=10, bgcolor=DARK_BG, border_radius=6),
            ),
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
                header=ft.ListTile(title=ft.Text("Eventos Transitorios y Recorte", color=ACCENT_RED, weight=ft.FontWeight.W_600)),
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

    import asyncio
    import threading
    res_opts = [ft.dropdown.Option(o) for o in ["Auto-Detect (Pantalla Actual)", "1920x1080", "1600x900", "1366x768", "1280x720", "2560x1440"]]
    res_dd = ft.Dropdown(label="Resolución Inicial", value=getattr(engine_instance, "window_res", "Auto-Detect (Pantalla Actual)"), options=res_opts, text_size=12, color=TEXT_MAIN, bgcolor=DARK_BG, border_color=BORDER_COL)
    
    mode_opts = [ft.dropdown.Option(o) for o in ["Normal", "Maximizada", "Pantalla Completa"]]
    mode_dd = ft.Dropdown(label="Modo Ventana", value=getattr(engine_instance, "window_mode", "Normal"), options=mode_opts, text_size=12, color=TEXT_MAIN, bgcolor=DARK_BG, border_color=BORDER_COL)
    
    line_opts = [ft.dropdown.Option(str(v)) for v in [0.1, 0.2, 0.3, 0.5, 0.75, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0]]
    current_lw = str(getattr(engine_instance, "chart_line_width", 1.0))
    if current_lw not in [o.key for o in line_opts]:
        current_lw = "1.0"
    line_dd = ft.Dropdown(label="Grosor de Línea Gráficas", value=current_lw, options=line_opts, text_size=12, color=TEXT_MAIN, bgcolor=DARK_BG, border_color=BORDER_COL)
    
    def apply_window_config(e):
        engine_instance.window_res = res_dd.value
        engine_instance.window_mode = mode_dd.value
        engine_instance.chart_line_width = float(line_dd.value)
        engine_instance.save_config()
        
        page = e.control.page
        if res_dd.value == "Auto-Detect (Pantalla Actual)":
            import tkinter as tk
            root = tk.Tk()
            w, h = root.winfo_screenwidth(), root.winfo_screenheight()
            root.destroy()
        else:
            parts = res_dd.value.split("x")
            w, h = int(parts[0]), int(parts[1])
            
        if mode_dd.value == "Pantalla Completa":
            page.window.full_screen = True
            page.window.maximized = False
        elif mode_dd.value == "Maximizada":
            page.window.full_screen = False
            page.window.maximized = True
            page.window.width = w
            page.window.height = h
        else:
            page.window.full_screen = False
            page.window.maximized = False
            page.window.width = w
            page.window.height = h
        page.update()
        # Aplicar grosor de línea inmediatamente sin reiniciar
        try:
            page.pubsub.send_all("refresh_charts")
        except: pass

        btn = e.control
        btn.text = "¡Guardado!"
        btn.bgcolor = ACCENT_GREEN
        btn.update()
        async def revert():
            await asyncio.sleep(1.5)
            btn.text = "🖥️ Aplicar y Guardar"
            btn.bgcolor = ACCENT_CYAN
            try: btn.update()
            except: pass
        threading.Thread(target=lambda: asyncio.run(revert())).start()

    apply_btn = ft.ElevatedButton("🖥️ Aplicar y Guardar", on_click=apply_window_config, style=ft.ButtonStyle(bgcolor=ACCENT_CYAN, color=DARK_BG, shape=ft.RoundedRectangleBorder(radius=4)))

    window_card = panel(
        content=ft.Column([
            ft.Text("🖥️ PANTALLA Y VENTANA", size=14, weight=ft.FontWeight.BOLD, color="#B380FF"),
            ft.Divider(height=10, color="#B380FF"),
            res_dd, 
            ft.Container(height=5),
            mode_dd, 
            ft.Container(height=5),
            line_dd,
            ft.Container(height=10),
            apply_btn
        ], spacing=5)
    )

    left_col = ft.Column([
        data_source_card,
        trigger_card,
    ], spacing=20, expand=4, scroll=ft.ScrollMode.AUTO)

    mid_col = ft.Column([
        freq_card,
        hw_card,
    ], spacing=20, expand=4, scroll=ft.ScrollMode.AUTO)

    right_col = ft.Column([
        window_card,
        info_card
    ], spacing=20, expand=4, scroll=ft.ScrollMode.AUTO)

    def on_refresh(msg):
        if msg == "refresh_charts":
            current_sr = engine_instance.sample_rate / 1e6
            sr_str = f"{current_sr:.1f}" if current_sr.is_integer() else str(current_sr).rstrip('0').rstrip('.')
            if '.' not in sr_str: sr_str += ".0"
            
            # Actualizar todos los inputs y los chips
            freq_f.value = fmt_float(engine_instance.center_freq)
            span_visual_f.value = fmt_float(engine_instance.visual_span_mhz)
            ref_level_f.value = fmt_float(engine_instance.bb60c_ref_level)
            rbw_f.value = fmt_float(engine_instance.bb60c_iq_bw)
            vbw_alpha_f.value = fmt_float(engine_instance.vbw_alpha)
            lock_chk.value = bool(engine_instance.auto_spectral_lock)
            
            # Sincronizar Smart Trigger
            trigger_chk.value = bool(engine_instance.trigger_active)
            trig_high_f.value = fmt_float(engine_instance.trigger_high)
            trig_low_f.value = fmt_float(engine_instance.trigger_low)
            rfi_count_lbl.value = f"{engine_instance.rfi_event_count}"
            
            for f_input in [freq_f, span_visual_f, ref_level_f, rbw_f, vbw_alpha_f, lock_chk, trigger_chk, trig_high_f, trig_low_f, rfi_count_lbl]:
                try: f_input.update()
                except: pass

            for btn in buttons_list:
                is_sel = (btn.data == sr_str)
                btn.bgcolor = ACCENT_CYAN if is_sel else PANEL_BG
                btn.content.color = DARK_BG if is_sel else TEXT_MAIN
                try: btn.update()
                except: pass
                
    page.pubsub.subscribe(on_refresh)

    return ft.Container(
        content=ft.Row([left_col, mid_col, right_col], alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.START, spacing=30, expand=True),
        expand=True,
        padding=ft.Padding(left=30, top=20, right=30, bottom=40),
    )
