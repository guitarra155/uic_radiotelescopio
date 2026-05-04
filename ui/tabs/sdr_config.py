"""
tabs/sdr_config.py
Panel derecho con secciones en acordeón:
  • 📊  Estado de Adquisición
  • ⚙️   Fuente & Parámetros SDR
  • 🔬  Algoritmo DSP Avanzado
Clic en el título expande esa sección y colapsa las demás.
"""

import flet as ft
import asyncio
import time
from core.constants import *
from ui.components.shared import panel, txt_field
from core.dsp_engine import engine_instance
import tkinter as tk
from tkinter import filedialog


# ─────────────────────────────────────────────────────────────────────────────
# Helper: crea una sección de acordeón
# ─────────────────────────────────────────────────────────────────────────────
def _accordion_section(
    icon: str, title: str, accent: str, content: ft.Control, expanded: bool = False
) -> tuple:
    """
    Devuelve (header_container, body_container) para usar en el acordeón.
    body_container.visible se maneja externamente.
    """
    arrow = ft.Text("▼" if expanded else "▶", color=accent, size=9)
    dot = ft.Container(width=6, height=6, bgcolor=accent, border_radius=3)

    header = ft.Container(
        content=ft.Row(
            [
                dot,
                ft.Text(
                    f"{icon}  {title}",
                    color=accent,
                    size=12,
                    weight=ft.FontWeight.W_600,
                    expand=1,
                ),
                arrow,
            ],
            spacing=8,
        ),
        bgcolor=PANEL_BG,
        border=ft.Border(
            bottom=ft.BorderSide(1, BORDER_COL),
            left=ft.BorderSide(2, accent if expanded else "transparent"),
        ),
        padding=ft.Padding(left=14, top=10, right=14, bottom=10),
        ink=True,
        border_radius=ft.BorderRadius(
            top_left=6, top_right=6, bottom_left=0, bottom_right=0
        ),
    )

    body = ft.Container(
        content=content,
        visible=expanded,
        animate_opacity=180,
        bgcolor=PANEL_BG,
        border=ft.Border(
            left=ft.BorderSide(2, accent if expanded else "transparent"),
            bottom=ft.BorderSide(1, BORDER_COL),
        ),
        padding=ft.Padding(left=12, right=12, top=10, bottom=12),
    )

    return header, body, arrow, dot


def build_config(page: ft.Page) -> ft.Control:

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

    # ─────────────────────────────────────────────────────────────────────────
    # ── Controles de la sección Fuente & SDR ─────────────────────────────────
    # ─────────────────────────────────────────────────────────────────────────
    filepath_input = txt_field(
        "Ruta del Archivo .iq", engine_instance.iq_filename, "Ej: C:\\Datos\\señal.iq"
    )

    # USAMOS FORMA ALTERNATIVA: Cuadro de diálogo nativo de Windows (Tkinter)
    # Esto evita el error "Unknown control: FilePicker" de Flet en Windows local.
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
        "Formato Datos .iq", engine_instance.iq_format, ["uint8", "int8", "complex64"]
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
                ft.Radio(
                    value="sdr",
                    label="🛠️ SDR Físico (RTL/HackRF)",
                    active_color=ACCENT_GREEN,
                ),
                ft.Radio(
                    value="file",
                    label="📼 Archivo Local (.iq)",
                    active_color=ACCENT_AMBER,
                ),
            ],
            spacing=4,
        ),
    )

    freq_f = txt_field("Frecuencia (MHz)", str(engine_instance.center_freq), "e.g. 1420.40")
    rate_f = txt_field("Sample Rate (MSps)", str(engine_instance.sample_rate / 1e6), "")
    span_visual_f = txt_field("Span Visual (Zoom MHz)", str(engine_instance.visual_span_mhz), "e.g. 1.0")
    analysis_win_f = txt_field("Tiempo Análisis (s)", str(engine_instance.analysis_window_sec), "e.g. 1.0")
    
    ma_win_f = txt_field("Filtro MA (ms)", str(engine_instance.moving_avg_window_ms), "0.1-10.0")
    ma_switch = ft.Switch(label="Activar Filtro Moving Average", value=engine_instance.ma_enabled, active_color=ACCENT_GREEN)
    wf_sec_f = txt_field("Historial (s)", str(engine_instance.waterfall_history_sec), "10-300")
    
    # NUEVOS: Controles sugeridos por el profesor
    ref_level_f = txt_field("Nivel Ref. (dBm)", str(engine_instance.bb60c_ref_level), "-100 a +20")
    rbw_f = txt_field("RBW / IQ BW (MHz)", str(engine_instance.bb60c_iq_bw), "0.1 a 20.0")
    vbw_alpha_f = txt_field("VBW Smoothing", str(engine_instance.vbw_alpha), "0.1-1.0")
    raw_switch = ft.Switch(label="Modo 100% RAW (Física)", value=engine_instance.raw_mode, active_color=ACCENT_CYAN)
    
    def on_global_change(e, attr, factor=1.0):
        try:
            val = float(e.control.value) * factor
            # Validaciones de seguridad
            if attr == "bb60c_iq_bw": val = max(0.1, min(40.0, val))
            if attr == "bb60c_ref_level": val = max(-100.0, min(20.0, val))
            
            setattr(engine_instance, attr, val)
            engine_instance.save_config()
        except ValueError: pass

    def on_raw_toggle(e):
        engine_instance.raw_mode = e.control.value
        engine_instance.save_config()
        page.pubsub.send_all("refresh_charts")

    freq_f.on_change = lambda e: on_global_change(e, "center_freq")
    rate_f.on_change = lambda e: on_global_change(e, "sample_rate", factor=1e6)
    analysis_win_f.on_change = lambda e: on_global_change(e, "analysis_window_sec")
    def on_ma_toggle(e):
        engine_instance.ma_enabled = e.control.value
        engine_instance.save_config()
        page.pubsub.send_all("refresh_charts")

    ma_switch.on_change = on_ma_toggle
    ma_win_f.on_change = lambda e: on_global_change(e, "moving_avg_window_ms")

    raw_switch.on_change = on_raw_toggle
    wf_sec_f.on_change = lambda e: on_global_change(e, "waterfall_history_sec")

    def on_span_change(e):
        try:
            val = float(e.control.value)
            engine_instance.update_visual_span(val)
        except: pass
    
    span_visual_f.on_change = on_span_change

    def on_sync_toggle(e):
        val = e.control.value
        engine_instance.apply_sync_mode(val)
        
        # Sincronizar visualmente y deshabilitar controles individuales
        ma_switch.disabled = val
        welch_rg.disabled = val
        raw_switch.disabled = val
        ma_win_f.disabled = val
        
        if val:
            # Modo Espejo: Todo a RAW y FFT básica
            ma_switch.value = False
            welch_rg.value = "fft"
            raw_switch.value = True
        else:
            # Restaurar: Regresar a los valores guardados
            ma_switch.value = engine_instance.ma_enabled
            welch_rg.value = "welch" if engine_instance.use_welch else "fft"
            raw_switch.value = engine_instance.raw_mode
        
        page.pubsub.send_all("refresh_charts")
        if page: page.update()

    sync_switch = ft.Switch(
        label="Sincronización Total (Modo Espejo)",
        value=engine_instance.sync_active,
        active_color=ft.Colors.ORANGE_800,
        on_change=on_sync_toggle
    )
    
    ref_level_f.on_change = lambda e: on_global_change(e, "bb60c_ref_level")
    rbw_f.on_change       = lambda e: on_global_change(e, "bb60c_iq_bw")
    vbw_alpha_f.on_change = lambda e: on_global_change(e, "vbw_alpha")

    # NUEVO: Los controles de rango ahora son dinámicos vía _axis_control

    # Lógica de actualización ahora centralizada en _axis_control.on_manual_change

    # Indicador de Overflow
    overflow_txt = ft.Text("⚠️ ADC OVERFLOW", color=ft.Colors.AMBER_ACCENT, 
                          size=12, weight=ft.FontWeight.BOLD, visible=False)

    async def on_ui_refresh(msg):
        if msg == "refresh_charts":
            overflow_txt.visible = engine_instance.sdr_overflow
            if overflow_txt.page: overflow_txt.update()
            
    page.pubsub.subscribe(on_ui_refresh)

    def on_welch_toggle(e):
        engine_instance.use_welch = e.control.value == "welch"
        engine_instance.save_config()

    def on_reset_defaults(e):
        """Restablece los valores y fuerza un refresco de la configuración."""
        engine_instance.reset_to_defaults()
        # En lugar de actualizar controles individuales (que pueden no existir),
        # notificamos para un refresco total de la UI de configuración.
        page.pubsub.send_all("config_reset")

    reset_btn = ft.ElevatedButton(
        content=ft.Text(
            "Restaurar Valores por Defecto", size=12, weight=ft.FontWeight.W_600
        ),
        on_click=on_reset_defaults,
        style=ft.ButtonStyle(
            color=TEXT_MAIN,
            bgcolor=ACCENT_CYAN,
            shape=ft.RoundedRectangleBorder(radius=8),
        ),
    )

    welch_rg = ft.RadioGroup(
        value="welch" if engine_instance.use_welch else "fft",
        on_change=on_welch_toggle,
        content=ft.Column(
            [
                ft.Radio(
                    value="fft", label="FFT Promedioado", active_color=ACCENT_GREEN
                ),
                ft.Text(
                    "FFT clásico: rápido, bueno para señales\nestables. Promedia múltiples bloques.",
                    color=TEXT_MUTED,
                    size=9,
                ),
                ft.Radio(value="welch", label="Welch PSD", active_color="#FFD700"),
                ft.Text(
                    "Welch: más suave, mejor resolución\nen frecuencia, usa solapamiento.",
                    color=TEXT_MUTED,
                    size=9,
                ),
            ],
            spacing=2,
        ),
    )

    def lbl(t, color=TEXT_MUTED, size=10):
        return ft.Text(t, color=color, size=size)

    def section_title(icon, title, color=ACCENT_CYAN):
        return ft.Container(
            content=ft.Text(
                f"{icon}  {title}", color=color, size=12, weight=ft.FontWeight.BOLD
            ),
            bgcolor="#0D1117",
            border_radius=4,
            padding=ft.Padding(left=8, top=4, right=8, bottom=4),
        )

    def divider():
        return ft.Divider(color=BORDER_COL, height=12)

    # Flags de auto-escala antiguos (deprecados en favor de charts_config)

    def _axis_control(title_text, chart_id):
        """Helper para crear controles de rango X/Y para una gráfica específica."""
        cfg = engine_instance.charts_config.get(chart_id)
        if not cfg or not isinstance(cfg, dict):
            return ft.Text(f"Configuración no disponible para: {chart_id}", color=ACCENT_AMBER, size=10)

        # Restaurar on_manual_change
        def on_manual_change(e, axis, attr):
            try:
                val = float(e.control.value)
                engine_instance.charts_config[chart_id][attr] = val
                engine_instance.charts_config[chart_id][f"auto_{axis}"] = False
                if axis == "x": sw_x.value = False
                else: sw_y.value = False
                engine_instance.save_config()
                page.pubsub.send_all("refresh_charts") 
                page.update()
            except ValueError:
                pass

        xi_min = txt_field("X Min", str(cfg["xmin"]))
        xi_max = txt_field("X Max", str(cfg["xmax"]))
        
        xi_min.on_change = lambda e: on_manual_change(e, "x", "xmin")
        xi_max.on_change = lambda e: on_manual_change(e, "x", "xmax")

        yi_min = txt_field("Y Min", str(cfg["ymin"]))
        yi_max = txt_field("Y Max", str(cfg["ymax"]))
        
        yi_min.on_change = lambda e: on_manual_change(e, "y", "ymin")
        yi_max.on_change = lambda e: on_manual_change(e, "y", "ymax")

        def on_auto_toggle(e, axis):
            engine_instance.charts_config[chart_id][f"auto_{axis}"] = e.control.value
            engine_instance.save_config()
            page.pubsub.send_all("refresh_charts") 

        # Usar Switch, que es nativo y muy testeado
        sw_x = ft.Switch(label="Auto X", value=cfg["auto_x"], active_color=ACCENT_GREEN, on_change=lambda e: on_auto_toggle(e, "x"))
        sw_y = ft.Switch(label="Auto Y", value=cfg["auto_y"], active_color=ACCENT_GREEN, on_change=lambda e: on_auto_toggle(e, "y"))

        return ft.Container(
            content=ft.Column([
                ft.Text(title_text, color=ACCENT_CYAN, size=11, weight=ft.FontWeight.BOLD),
                sw_x,
                ft.Row([xi_min, xi_max], spacing=10),
                sw_y,
                ft.Row([yi_min, yi_max], spacing=10),
                ft.Divider(color="#303030", height=10)
            ], spacing=10),
            padding=5
        )

    tab_configs = {
        0: ft.Column([
            section_title("🎯", "Pestaña 1: Monitoreo y RFI", ACCENT_CYAN),
            lbl("Fuerza bruta:"),
            raw_switch,
            _axis_control("Gráfica 1: Espectro RAW", "mon_raw_spec"),
            _axis_control("Gráfica 2: Amplitud RAW", "mon_raw_amp"),
        ], spacing=5),
        1: ft.Column([
            section_title("🔍", "Pestaña 2: Monitoreo Filtrado", ACCENT_GREEN),
            lbl("Interruptor de Filtro"),
            ma_switch,
            lbl("Filtro Moving Average (ms)"),
            ma_win_f,
            _axis_control("Gráfica 1: Espectro Filtrado", "mon_filt_spec"),
            _axis_control("Gráfica 2: Amplitud Filtrada", "mon_filt_amp"),
        ], spacing=5),
        2: ft.Column([
            section_title("🌈", "Pestaña 3: Espectrograma", "#FF6B9D"),
            lbl("Tiempo de Análisis por bloque (s) - Afecta velocidad general"),
            analysis_win_f,
            lbl("Historial Total Cascada (s)"),
            wf_sec_f,
            _axis_control("Cascada (Waterfall)", "spec_wf"),
        ], spacing=5),
        3: ft.Column([
            section_title("📊", "Pestaña 4: Estadística", ACCENT_AMBER),
            _axis_control("Histograma de Amplitud", "stat_hist"),
        ], spacing=5),
        4: ft.Column([
            section_title("⚡", "Pestaña 5: Potencia vs Tiempo", "#FFB347"),
            _axis_control("Potencia Instantánea", "pow_time"),
        ], spacing=5),
        5: ft.Column([
            section_title("📶", "Pestaña 6: SNR vs Frecuencia", "#00CED1"),
            _axis_control("SNR por Bin de Freq", "snr_freq"),
        ], spacing=5),
        6: ft.Column([
            section_title("🔬", "Pestaña 7: Algoritmo DSP", "#B380FF"),
            ft.Text("Ver la sección 'Algoritmo DSP' abajo.", color=TEXT_MUTED, size=9)
        ], spacing=5),
        7: ft.Column([
            section_title("ℹ️", "Pestaña 8: Estado", ACCENT_GREEN),
            ft.Text("Información de estado visible en la pestaña principal.", color=TEXT_MUTED, size=9)
        ], spacing=5),
    }

    dynamic_tab_container = ft.Container(content=tab_configs.get(engine_instance.active_tab, tab_configs[0]))

    async def _update_dynamic_tab(msg):
        if msg == "refresh_charts" or msg == "tab_changed":
            idx = engine_instance.active_tab
            target_content = tab_configs.get(idx, tab_configs[0])
            if dynamic_tab_container.content != target_content:
                dynamic_tab_container.content = target_content
                if dynamic_tab_container.page:
                    dynamic_tab_container.update()

    page.pubsub.subscribe(_update_dynamic_tab)

    sdr_content = ft.Column(
        [
            section_title("🎯", "Modo de Escala Inteligente", ACCENT_AMBER),
            ft.Text("Las gráficas se centran automáticamente al nivel de referencia y señal "
                    "a menos que cambies un valor manualmente.", color=TEXT_MUTED, size=9, italic=True),
            lbl("Control de Sincronización:"),
            sync_switch,
            overflow_txt,
            reset_btn,
            divider(),

            dynamic_tab_container,

            divider(),
            section_title("🌍", "SDR & Frecuencia", TEXT_MAIN),
            lbl("Freq Central (MHz)"), freq_f,
            lbl("Span Visual (Zoom MHz)"), span_visual_f,
            lbl("Sample Rate (MSps)"), rate_f,
            divider(),

            section_title("🔧", "Hardware (BB60C)", ACCENT_CYAN),
            lbl("Nivel de Referencia (dBm)"),
            ref_level_f,
            lbl("Ajusta el techo de entrada para no saturar.", size=8),
            
            lbl("RBW / Ancho Banda IQ (MHz)"),
            rbw_f,
            lbl("Filtro físico del SDR. Valores bajos = menos ruido.", size=8),
            
            lbl("Suavizado VBW (Digital)"),
            vbw_alpha_f,
            lbl("0.1 = Muy filtrado, 1.0 = Tiempo Real/Puro.", size=8),
            divider(),
            
            section_title("📁", "Origen de Datos", TEXT_MAIN),
            ft.Row([filepath_input, pick_btn], spacing=5),
            fmt_dd,
            mode_rg,
        ],
        spacing=8,
        scroll=ft.ScrollMode.AUTO,
    )

    # Fin de sdr_content avanzado

    # ─────────────────────────────────────────────────────────────────────────
    # ── Controles de la sección Estado ───────────────────────────────────────
    # ─────────────────────────────────────────────────────────────────────────
    # (La sección de Estado ha sido movida a ui/tabs/estado.py)

    # ─────────────────────────────────────────────────────────────────────────
    # ── Controles de la sección Algoritmo DSP movidos a su propia pestaña ────
    # ─────────────────────────────────────────────────────────────────────────

    # ── FINALIZACIÓN ─────────────────────────────────────────────────────────
    tab_configs[6] = ft.Column([
        section_title("🔬", "Pestaña 7: Algoritmo DSP", "#B380FF"),
        ft.Text("La configuración del método está en la pestaña central.", color=TEXT_MUTED, size=9, italic=True)
    ], spacing=5)

    if engine_instance.active_tab == 6:
        dynamic_tab_container.content = tab_configs[6]

    return ft.Container(
        content=ft.Column([sdr_content], scroll=ft.ScrollMode.AUTO, expand=True),
        expand=True,
        width=300,
        padding=ft.Padding(left=10, top=10, right=15, bottom=10),
    )
