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

    # ─────────────────────────────────────────────────────────────────────────
    # ── Selector de Archivos (Implementación Robusta) ──────────────────────────
    # ─────────────────────────────────────────────────────────────────────────
    def on_file_result(e):
        if e.files:
            selected_path = e.files[0].path
            filepath_input.value = selected_path
            engine_instance.iq_filename = selected_path
            engine_instance.save_config()
            page.update()

    # Usamos un botón simple si FilePicker falla en esta versión de Flet
    # file_picker = ft.FilePicker()
    # file_picker.on_result = on_file_result
    # page.overlay.append(file_picker)
    file_picker = None

    def on_pick_file(e):
        if file_picker:
            file_picker.pick_files(
                allow_multiple=False,
                allowed_extensions=["iq"],
            )
        else:
            print("FilePicker no disponible en esta versión de Flet")

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

    freq_f = txt_field("Frecuencia (MHz)", "1420.40", "e.g. 1420.40")
    rate_f = txt_field("Sample Rate (MSps)", "2.4", "")

    db_min_f = txt_field("Min Y (dBFS) Espectro", str(engine_instance.db_min), "-100")
    db_max_f = txt_field("Max Y (dBFS) Espectro", str(engine_instance.db_max), "-40")

    pwr_db_min_f = txt_field(
        "Min Potencia (dBFS)", str(engine_instance.power_db_min), "-100"
    )
    pwr_db_max_f = txt_field(
        "Max Potencia (dBFS)", str(engine_instance.power_db_max), "0"
    )

    snr_db_min_f = txt_field(
        "Min Magnitud (dB)", str(engine_instance.snr_db_min), "-10"
    )
    snr_db_max_f = txt_field("Max Magnitud (dB)", str(engine_instance.snr_db_max), "40")

    f_min_f = txt_field("Min X (MHz)", str(engine_instance.f_min), "1419.0")
    f_max_f = txt_field("Max X (MHz)", str(engine_instance.f_max), "1421.0")
    amp_min_f = txt_field("Min Amp (V)", str(engine_instance.amp_min), "0.0")
    amp_max_f = txt_field("Max Amp (V)", str(engine_instance.amp_max), "1.0")
    wf_sec_f = txt_field(
        "Cascada (s)", str(engine_instance.waterfall_history_sec), "60"
    )
    analysis_win_f = txt_field(
        "Ventana Análisis (s)", str(engine_instance.analysis_window_sec), "0.1–5.0"
    )
    ma_win_f = txt_field(
        "Moving Average (ms)", str(engine_instance.moving_avg_window_ms), "0.1–10.0"
    )

    def update_bounds(e, auto_off_attrs=None):
        # Desactivar auto-escala cuando se modifican valores manualmente
        if auto_off_attrs:
            for attr in auto_off_attrs:
                if hasattr(engine_instance, attr):
                    setattr(engine_instance, attr, False)

        for attr, field in [
            ("db_min", db_min_f),
            ("db_max", db_max_f),
            ("power_db_min", pwr_db_min_f),
            ("power_db_max", pwr_db_max_f),
            ("snr_db_min", snr_db_min_f),
            ("snr_db_max", snr_db_max_f),
            ("f_min", f_min_f),
            ("f_max", f_max_f),
            ("amp_min", amp_min_f),
            ("amp_max", amp_max_f),
            ("waterfall_history_sec", wf_sec_f),
            ("analysis_window_sec", analysis_win_f),
            ("moving_avg_window_ms", ma_win_f),
        ]:
            try:
                setattr(engine_instance, attr, float(field.value))
            except ValueError:
                pass
        engine_instance.save_config()

    def update_current_labels():
        # Actualizar los labels que muestran los valores actuales
        pass  # Se actualizan dinámicamente desde las gráficas

    # Conectar campos con auto-desactivación de escala
    db_min_f.on_change = lambda e: update_bounds(
        e, ["auto_scale_spectrum", "auto_scale_waterfall"]
    )
    db_max_f.on_change = lambda e: update_bounds(
        e, ["auto_scale_spectrum", "auto_scale_waterfall"]
    )
    db_min_f.on_submit = lambda e: update_bounds(
        e, ["auto_scale_spectrum", "auto_scale_waterfall"]
    )
    db_max_f.on_submit = lambda e: update_bounds(
        e, ["auto_scale_spectrum", "auto_scale_waterfall"]
    )

    pwr_db_min_f.on_change = lambda e: update_bounds(e, ["auto_scale_power"])
    pwr_db_max_f.on_change = lambda e: update_bounds(e, ["auto_scale_power"])
    pwr_db_min_f.on_submit = lambda e: update_bounds(e, ["auto_scale_power"])
    pwr_db_max_f.on_submit = lambda e: update_bounds(e, ["auto_scale_power"])

    snr_db_min_f.on_change = lambda e: update_bounds(e, ["auto_scale_snr"])
    snr_db_max_f.on_change = lambda e: update_bounds(e, ["auto_scale_snr"])
    snr_db_min_f.on_submit = lambda e: update_bounds(e, ["auto_scale_snr"])
    snr_db_max_f.on_submit = lambda e: update_bounds(e, ["auto_scale_snr"])

    # Los demás campos sin auto-off
    for field in [
        f_min_f,
        f_max_f,
        amp_min_f,
        amp_max_f,
        wf_sec_f,
        analysis_win_f,
        ma_win_f,
    ]:
        field.on_change = update_bounds
        field.on_submit = update_bounds

    def on_welch_toggle(e):
        engine_instance.use_welch = e.control.value == "welch"
        engine_instance.save_config()

    def on_reset_defaults(e):
        engine_instance.reset_to_defaults()
        engine_instance.save_config()
        # Sincronizar los campos de texto de la UI con los nuevos valores del engine
        db_min_f.value = str(engine_instance.db_min)
        db_max_f.value = str(engine_instance.db_max)
        pwr_db_min_f.value = str(engine_instance.power_db_min)
        pwr_db_max_f.value = str(engine_instance.power_db_max)
        snr_db_min_f.value = str(engine_instance.snr_db_min)
        snr_db_max_f.value = str(engine_instance.snr_db_max)
        f_min_f.value = str(engine_instance.f_min)
        f_max_f.value = str(engine_instance.f_max)
        amp_min_f.value = str(engine_instance.amp_min)
        amp_max_f.value = str(engine_instance.amp_max)
        wf_sec_f.value = str(engine_instance.waterfall_history_sec)

        # Sincronizar switches de auto-escala
        auto_scale_spectrum.value = True
        auto_scale_power.value = True
        auto_scale_snr.value = True
        auto_scale_waterfall.value = True

        page.update()

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

    # ── Toggle de Auto-Escala por pestaña ──────────────────────────────
    auto_scale_spectrum = ft.Switch(
        label="Auto-escala Espectro",
        value=True,
        active_color=ACCENT_GREEN,
        label_text_style=ft.TextStyle(color=TEXT_MUTED, size=10),
    )
    auto_scale_power = ft.Switch(
        label="Auto-escala Potencia",
        value=True,
        active_color=ACCENT_GREEN,
        label_text_style=ft.TextStyle(color=TEXT_MUTED, size=10),
    )
    auto_scale_snr = ft.Switch(
        label="Auto-escala SNR",
        value=True,
        active_color=ACCENT_GREEN,
        label_text_style=ft.TextStyle(color=TEXT_MUTED, size=10),
    )
    auto_scale_waterfall = ft.Switch(
        label="Auto-escala Waterfall",
        value=True,
        active_color=ACCENT_GREEN,
        label_text_style=ft.TextStyle(color=TEXT_MUTED, size=10),
    )

    def on_auto_scale_toggle(e, attr):
        setattr(engine_instance, attr, e.control.value)
        engine_instance.save_config()

    auto_scale_spectrum.on_change = lambda e: on_auto_scale_toggle(
        e, "auto_scale_spectrum"
    )
    auto_scale_power.on_change = lambda e: on_auto_scale_toggle(e, "auto_scale_power")
    auto_scale_snr.on_change = lambda e: on_auto_scale_toggle(e, "auto_scale_snr")
    auto_scale_waterfall.on_change = lambda e: on_auto_scale_toggle(
        e, "auto_scale_waterfall"
    )

    # Sincronizar con estado actual del engine
    auto_scale_spectrum.value = getattr(engine_instance, "auto_scale_spectrum", True)
    auto_scale_power.value = getattr(engine_instance, "auto_scale_power", True)
    auto_scale_snr.value = getattr(engine_instance, "auto_scale_snr", True)
    auto_scale_waterfall.value = getattr(engine_instance, "auto_scale_waterfall", True)

    sdr_content = ft.Column(
        [
            section_title("📡", "Pestaña 1: Monitoreo y RFI", ACCENT_CYAN),
            ft.Row(
                [lbl("Rango Y del Espectro (dBFS)"), auto_scale_spectrum], spacing=8
            ),
            ft.Row([db_min_f, db_max_f], spacing=8),
            lbl(
                f"Actual: {engine_instance.db_min:.1f} a {engine_instance.db_max:.1f} dBFS",
                ACCENT_CYAN,
                9,
            ),
            divider(),
            section_title("🔍", "Pestaña 2: Monitoreo Filtrado", ACCENT_GREEN),
            lbl("Moving Average (ms)"),
            ma_win_f,
            lbl("Rango Y Amplitud (V)"),
            ft.Row([amp_min_f, amp_max_f], spacing=8),
            lbl("Rango X (MHz)"),
            ft.Row([f_min_f, f_max_f], spacing=8),
            lbl(
                f"Actual: {engine_instance.amp_min:.3f} a {engine_instance.amp_max:.3f} V",
                ACCENT_CYAN,
                9,
            ),
            divider(),
            section_title("🌈", "Pestaña 3: Espectrograma", "#FF6B9D"),
            lbl("Historial Cascada (segundos)"),
            wf_sec_f,
            ft.Row([lbl("Rango Y (dBFS)"), auto_scale_waterfall], spacing=8),
            ft.Row([db_min_f, db_max_f], spacing=8),
            lbl("Rango X (MHz)"),
            ft.Row([f_min_f, f_max_f], spacing=8),
            lbl(
                f"Actual: {engine_instance.db_min:.1f} a {engine_instance.db_max:.1f} dBFS",
                ACCENT_CYAN,
                9,
            ),
            divider(),
            section_title("📊", "Pestaña 4: Estadística", ACCENT_AMBER),
            lbl("Sin parámetros específicos de rango"),
            divider(),
            section_title("⚡", "Pestaña 5: Potencia vs Tiempo", "#FFB347"),
            ft.Row([lbl("Rango Y (dBFS)"), auto_scale_power], spacing=8),
            ft.Row([pwr_db_min_f, pwr_db_max_f], spacing=8),
            lbl(
                f"Actual: {engine_instance.power_db_min:.1f} a {engine_instance.power_db_max:.1f} dBFS",
                ACCENT_CYAN,
                9,
            ),
            divider(),
            section_title("📶", "Pestaña 6: SNR vs Frecuencia", "#00CED1"),
            ft.Row([lbl("Rango Y (SNR dB)"), auto_scale_snr], spacing=8),
            ft.Row([snr_db_min_f, snr_db_max_f], spacing=8),
            lbl("Rango X (MHz)"),
            ft.Row([f_min_f, f_max_f], spacing=8),
            lbl(
                f"Actual: {engine_instance.snr_db_min:.1f} a {engine_instance.snr_db_max:.1f} dB",
                ACCENT_CYAN,
                9,
            ),
            divider(),
            section_title("🔬", "Algoritmo DSP", "#B380FF"),
            lbl("Método espectral base:"),
            welch_rg,
            lbl("Ventana Análisis (s)"),
            analysis_win_f,
            divider(),
            section_title("🌍", "Parámetros Globales", TEXT_MAIN),
            lbl("Frecuencia Central (MHz)"),
            freq_f,
            lbl("Sample Rate (MSps)"),
            rate_f,
            lbl("Rango X (Frecuencia MHz)"),
            ft.Row([f_min_f, f_max_f], spacing=8),
            lbl(
                f"Actual: {engine_instance.f_min:.3f} a {engine_instance.f_max:.3f} MHz",
                ACCENT_CYAN,
                9,
            ),
            divider(),
            section_title("📁", "Archivo y Formato", TEXT_MAIN),
            ft.Row([filepath_input, pick_btn], spacing=5),
            fmt_dd,
            lbl("Modo de Adquisición"),
            mode_rg,
        ],
        spacing=6,
        scroll=ft.ScrollMode.AUTO,
    )

    def divider():
        return ft.Divider(color=BORDER_COL, height=12)

    sdr_content = ft.Column(
        [
            section_title("📡", "Pestaña 1: Monitoreo y RFI", ACCENT_CYAN),
            lbl("Rango Y del Espectro (dBFS)"),
            ft.Row([db_min_f, db_max_f], spacing=8),
            lbl("Rango X (MHz)"),
            ft.Row([f_min_f, f_max_f], spacing=8),
            divider(),
            section_title("🔍", "Pestaña 2: Monitoreo Filtrado", ACCENT_GREEN),
            lbl("Moving Average (ms)"),
            ma_win_f,
            lbl("Rango Y Amplitud (V)"),
            ft.Row([amp_min_f, amp_max_f], spacing=8),
            lbl("Rango X (MHz)"),
            ft.Row([f_min_f, f_max_f], spacing=8),
            divider(),
            section_title("🌈", "Pestaña 3: Espectrograma", "#FF6B9D"),
            lbl("Historial Cascada (segundos)"),
            wf_sec_f,
            lbl("Rango Y (dBFS)"),
            ft.Row([db_min_f, db_max_f], spacing=8),
            lbl("Rango X (MHz)"),
            ft.Row([f_min_f, f_max_f], spacing=8),
            divider(),
            section_title("📊", "Pestaña 4: Estadística", ACCENT_AMBER),
            lbl("Sin parámetros específicos de rango"),
            divider(),
            section_title("⚡", "Pestaña 5: Potencia vs Tiempo", "#FFB347"),
            lbl("Rango Y (dBFS)"),
            ft.Row([pwr_db_min_f, pwr_db_max_f], spacing=8),
            divider(),
            section_title("📶", "Pestaña 6: SNR vs Frecuencia", "#00CED1"),
            lbl("Rango Y (SNR dB)"),
            ft.Row([snr_db_min_f, snr_db_max_f], spacing=8),
            lbl("Rango X (MHz)"),
            ft.Row([f_min_f, f_max_f], spacing=8),
            divider(),
            section_title("🔬", "Algoritmo DSP", "#B380FF"),
            lbl("Método espectral base:"),
            welch_rg,
            lbl("Ventana Análisis (s)"),
            analysis_win_f,
            divider(),
            section_title("🌍", "Parámetros Globales", TEXT_MAIN),
            lbl("Frecuencia Central (MHz)"),
            freq_f,
            lbl("Sample Rate (MSps)"),
            rate_f,
            lbl("Rango X (Frecuencia MHz)"),
            ft.Row([f_min_f, f_max_f], spacing=8),
            divider(),
            section_title("📁", "Archivo y Formato", TEXT_MAIN),
            ft.Row([filepath_input, pick_btn], spacing=5),
            fmt_dd,
            lbl("Modo de Adquisición"),
            mode_rg,
        ],
        spacing=6,
        scroll=ft.ScrollMode.AUTO,
    )

    # ─────────────────────────────────────────────────────────────────────────
    # ── Controles de la sección Estado ───────────────────────────────────────
    # ─────────────────────────────────────────────────────────────────────────
    dev_rows = [
        ("Modelo SDR", "RTL-SDR v3 / HackRF", TEXT_MAIN),
        ("Conexión", "Archivo Local (.iq)", ACCENT_CYAN),
        ("Estado", "Listo para leer", ACCENT_GREEN),
        ("Temperatura", "-- °C", TEXT_MUTED),
        ("DSP Worker", "Multihilo Async", TEXT_MAIN),
    ]

    info_rows = [
        ft.Row(
            [
                ft.Text(k, color=TEXT_MUTED, size=11, expand=1),
                ft.Text(v, color=c, size=11, expand=1, weight=ft.FontWeight.W_600),
            ]
        )
        for k, v, c in dev_rows
    ]

    estado_content = ft.Column(
        [
            *info_rows,
            ft.Divider(color=BORDER_COL, height=8),
            ft.Text(
                "💡 Instrucciones",
                color=ACCENT_GREEN,
                size=11,
                weight=ft.FontWeight.BOLD,
            ),
            ft.Text(
                "1. Ubique el archivo .iq guardado en su PC.\n"
                "2. Elija el formato correcto.\n"
                "3. Presione 'Reproducir' en el stream.",
                color=TEXT_MUTED,
                size=10,
            ),
        ],
        spacing=6,
    )

    # ─────────────────────────────────────────────────────────────────────────
    # ── Controles de la sección Algoritmo DSP ────────────────────────────────
    # ─────────────────────────────────────────────────────────────────────────
    METHODS = [
        "AR/Burg",
        "CWT/Morlet",
        "Pseudo-MUSIC",
        "ESPRIT",
        "Welch",
        "Correlograma",
        "ASLT",
    ]

    # Usamos RadioGroup porque el Dropdown estaba fallando internamente en Flet
    method_rg = ft.RadioGroup(
        value=engine_instance.algo_params.get("method", "AR/Burg"),
        content=ft.Column(
            [
                ft.Radio(value="AR/Burg", label="AR/Burg", active_color=ACCENT_CYAN),
                ft.Radio(
                    value="CWT/Morlet", label="CWT/Morlet", active_color=ACCENT_CYAN
                ),
                ft.Radio(
                    value="Pseudo-MUSIC", label="Pseudo-MUSIC", active_color=ACCENT_CYAN
                ),
                ft.Radio(value="ESPRIT", label="ESPRIT", active_color=ACCENT_CYAN),
                ft.Divider(color=BORDER_COL, height=4),
                ft.Radio(value="Welch", label="Welch PSD", active_color="#FFD700"),
                ft.Radio(
                    value="Correlograma", label="Correlograma", active_color="#40E0D0"
                ),
                ft.Divider(color=BORDER_COL, height=4),
                ft.Radio(
                    value="ASLT", label="ASLT ⚠ (pendiente)", active_color=TEXT_MUTED
                ),
            ],
            spacing=2,
        ),
    )

    ar_order_f = txt_field("Orden AR / Burg", "64", "16–256")
    music_ns_f = txt_field("# Señales MUSIC/ESPRIT", "3", "1–10")

    algo_status_txt = ft.Text(
        "Esperando stream...", color=TEXT_MUTED, size=9, italic=True
    )
    algo_running = [False]
    algo_counter = [0]
    algo_gen = [0]  # epoch: se incrementa al cambiar método
    ALGO_EVERY_N = 30

    ar_order_row = ft.Container(content=ar_order_f, visible=True)
    music_ns_row = ft.Container(content=music_ns_f, visible=False)

    def _update_param_visibility():
        m = engine_instance.algo_params.get("method", "AR/Burg")
        ar_order_row.visible = m == "AR/Burg"
        music_ns_row.visible = m in ("Pseudo-MUSIC", "ESPRIT")
        try:
            if ar_order_row.page:
                ar_order_row.update()
            if music_ns_row.page:
                music_ns_row.update()
        except Exception:
            pass

    def on_method_change(e):
        try:
            val = e.control.value
            if val is None or val == "":
                return

            engine_instance.algo_params["method"] = val
            engine_instance.save_config()  # Persistencia!
            algo_gen[0] += 1
            algo_running[0] = False

            # Depuración Visual CRÍTICA
            algo_status_txt.value = f"⚠ Clicked: {val}"
            try:
                algo_status_txt.update()
            except:
                pass

            # Avisamos AL INSTANTE a los otros paneles
            page.pubsub.send_all("algo_method_changed")

            # Y recién entonces actualizamos las cajas locales propensas a error de Flet
            _update_param_visibility()

            if engine_instance.is_playing:
                page.run_task(_run_selected_algo)
        except Exception as ex:
            print(f"Error on on_method_change: {ex}")

    method_rg.on_change = on_method_change

    def _save_params(e=None):
        try:
            engine_instance.algo_params["ar_order"] = int(ar_order_f.value or 64)
        except:
            pass
        try:
            engine_instance.algo_params["n_signals"] = int(music_ns_f.value or 3)
        except:
            pass
        engine_instance.save_config()

    ar_order_f.on_change = _save_params
    ar_order_f.on_submit = _save_params
    music_ns_f.on_change = _save_params
    music_ns_f.on_submit = _save_params

    async def _run_selected_algo():
        if algo_running[0]:
            return
        algo_running[0] = True
        my_gen = algo_gen[0]
        method = engine_instance.algo_params.get("method", "AR/Burg")
        algo_status_txt.value = f"⏳ {method}..."

        try:
            algo_status_txt.update()
        except:
            pass
        try:
            iq = engine_instance.amplitude_ma_data  # Siempre señal filtrada
            sr = engine_instance.sample_rate
            fc = engine_instance.center_freq
            order_val = engine_instance.algo_params.get("ar_order", 64)
            ns_val = engine_instance.algo_params.get("n_signals", 3)
            wfft_val = engine_instance.algo_params.get("welch_fft", 1024)
            wovl_val = engine_instance.algo_params.get("welch_overlap", 0.5)
            corr_lag = engine_instance.algo_params.get("corr_max_lag", 512)

            from core.advanced_dsp import (
                run_ar_burg,
                run_cwt,
                run_pseudo_music,
                run_esprit,
                run_welch,
                run_correlogram,
                run_aslt,
            )
            from ui.charts import (
                chart_ar_spectrum,
                chart_cwt_map,
                chart_music_spectrum,
                chart_welch_spectrum,
                chart_correlogram_spectrum,
            )

            def _compute():
                if method == "AR/Burg":
                    return "ar", chart_ar_spectrum(
                        run_ar_burg(iq, order=order_val, sample_rate=sr, center_freq=fc)
                    )
                elif method == "CWT/Morlet":
                    return "cwt", chart_cwt_map(run_cwt(iq, sample_rate=sr))
                elif method == "Pseudo-MUSIC":
                    return "music", chart_music_spectrum(
                        run_pseudo_music(
                            iq, n_signals=ns_val, sample_rate=sr, center_freq=fc
                        )
                    )
                elif method == "ESPRIT":
                    return "esprit", chart_music_spectrum(
                        run_esprit(iq, n_signals=ns_val, sample_rate=sr, center_freq=fc)
                    )
                elif method == "Welch":
                    return "welch", chart_welch_spectrum(
                        run_welch(
                            iq,
                            fft_size=wfft_val,
                            overlap=wovl_val,
                            sample_rate=sr,
                            center_freq=fc,
                        )
                    )
                elif method == "Correlograma":
                    return "correlogram", chart_correlogram_spectrum(
                        run_correlogram(
                            iq, max_lag=corr_lag, sample_rate=sr, center_freq=fc
                        )
                    )
                else:  # ASLT
                    return "aslt", chart_ar_spectrum(
                        run_aslt(iq, sample_rate=sr, center_freq=fc)
                    )

            algo_key, b64 = await asyncio.to_thread(_compute)

            # ── Descartar obsoletos SIN romper el lock del nuevo ──
            if algo_gen[0] != my_gen:
                return

            engine_instance.algo_results[algo_key] = b64
            engine_instance.algo_results["current"] = b64
            engine_instance.algo_results["current_method"] = method
            page.pubsub.send_all("algo_results_ready")
            algo_status_txt.value = f"✓ {method}"
        except NotImplementedError as ni:
            try:
                algo_status_txt.value = "⚠ ASLT: archivos pendientes"
                algo_status_txt.update()
            except:
                pass
        except RuntimeError:
            pass  # Ignorar si la ventana se cerró
        except Exception as ex:
            try:
                algo_status_txt.value = f"⚠ ERROR: {str(ex)[:35]}"
                algo_status_txt.update()
            except:
                pass
            print("CRITICAL ALGO ERROR:", ex)
        finally:
            # Solo liberar el lock si nosotros somos la generación actual
            if algo_gen[0] == my_gen:
                algo_running[0] = False
            try:
                algo_status_txt.update()
            except:
                pass

    async def on_algo_refresh(msg):
        if msg != "refresh_charts":
            return
        if not engine_instance.is_playing:
            return
        algo_counter[0] += 1
        if algo_counter[0] % ALGO_EVERY_N == 0:
            await _run_selected_algo()

    page.pubsub.subscribe(on_algo_refresh)

    algo_content = ft.Column(
        [
            ft.Row(
                [
                    ft.Text(
                        "Resultado en pestaña  🔬 Algoritmo DSP",
                        color=TEXT_MUTED,
                        size=9,
                        italic=True,
                        expand=1,
                    ),
                    algo_status_txt,
                ]
            ),
            ft.Text("Método Avanzado:", color=TEXT_MAIN, size=12),
            method_rg,
            ar_order_row,
            music_ns_row,
            ft.Divider(color=BORDER_COL, height=6),
            ft.Text(
                "⚠ ASLT requiere archivos externos.\n"
                "Al agregarlos, reemplaza run_aslt() en\n"
                "core/advanced_dsp.py sin cambiar la firma.",
                color=TEXT_MUTED,
                size=9,
                italic=True,
            ),
        ],
        spacing=8,
    )

    # ── ACORDEÓN ─────────────────────────────────────────────────────────────
    # ── ACORDEÓN ─────────────────────────────────────────────────────────────
    SECTIONS = [
        (
            "📊",
            "Estado",
            ACCENT_GREEN,
            ft.Column([estado_content, divider(), reset_btn], spacing=8),
            False,
        ),
        ("⚙️", "Fuente & SDR", ACCENT_CYAN, sdr_content, True),
        ("🔬", "Algoritmo DSP", "#B380FF", algo_content, False),
    ]

    headers, bodies, arrows, dots = [], [], [], []

    def make_toggle(idx, accent_color):
        def _toggle(e):
            for i in range(len(bodies)):
                is_active = i == idx
                bodies[i].visible = is_active
                bodies[i].border = ft.Border(
                    left=ft.BorderSide(2, accent_color if is_active else "transparent"),
                    bottom=ft.BorderSide(1, BORDER_COL),
                )
                arrows[i].value = "▼" if is_active else "▶"
                headers[i].border = ft.Border(
                    bottom=ft.BorderSide(1, BORDER_COL),
                    left=ft.BorderSide(
                        2, (SECTIONS[i][2] if is_active else "transparent")
                    ),
                )
                arrows[i].color = SECTIONS[i][2]
                headers[i].update()
                bodies[i].update()

        return _toggle

    for idx, (icon, title, accent, content, expanded) in enumerate(SECTIONS):
        h, b, arr, dot = _accordion_section(icon, title, accent, content, expanded)
        headers.append(h)
        bodies.append(b)
        arrows.append(arr)
        dots.append(dot)

    for i, (_, _, accent, _, _) in enumerate(SECTIONS):
        headers[i].on_click = make_toggle(i, accent)

    accordion = ft.Column(
        [item for pair in zip(headers, bodies) for item in pair],
        spacing=0,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )

    return ft.Container(
        content=accordion,
        expand=True,
        padding=ft.Padding(left=8, top=10, right=10, bottom=10),
    )
