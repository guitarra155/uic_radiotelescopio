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
    
    ma_win_f = txt_field("Filtro MA (ms)", str(engine_instance.moving_avg_window_ms), "0.1-10.0")
    wf_sec_f = txt_field("Historial (s)", str(engine_instance.waterfall_history_sec), "10-300")

    def on_global_change(e, attr, factor=1.0):
        try:
            val = float(e.control.value) * factor
            setattr(engine_instance, attr, val)
            engine_instance.save_config()
        except ValueError: pass

    freq_f.on_change = lambda e: on_global_change(e, "center_freq")
    rate_f.on_change = lambda e: on_global_change(e, "sample_rate", factor=1e6)
    ma_win_f.on_change = lambda e: on_global_change(e, "moving_avg_window_ms")
    wf_sec_f.on_change = lambda e: on_global_change(e, "waterfall_history_sec")

    # NUEVO: Los controles de rango ahora son dinámicos vía _axis_control

    # Lógica de actualización ahora centralizada en _axis_control.on_manual_change

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
        if not cfg:
            return ft.Text(f"Config error for {chart_id}", color="red")

        # Texto de ayuda
        help_txt = ft.Text(title_text, color=ACCENT_CYAN, size=11, weight=ft.FontWeight.BOLD)
        
        # Filtros para inputs manuales (para desactivar auto-scale)
        def on_manual_change(e, axis, attr):
            try:
                val = float(e.control.value)
                engine_instance.charts_config[chart_id][attr] = val
                # Desactivar auto-escala al cambiar manualmente
                engine_instance.charts_config[chart_id][f"auto_{axis}"] = False
                # Sincronizar switch
                if axis == "x": sw_x.value = False
                else: sw_y.value = False
                engine_instance.save_config()
                page.pubsub.send_all("refresh_charts") # Notificar para redibujado inmediato
                page.update()
            except ValueError:
                pass

        # Inputs X
        xi_min = txt_field("X Min", str(cfg["xmin"]))
        xi_max = txt_field("X Max", str(cfg["xmax"]))
        xi_min.on_change = lambda e: on_manual_change(e, "x", "xmin")
        xi_max.on_change = lambda e: on_manual_change(e, "x", "xmax")

        # Inputs Y
        yi_min = txt_field("Y Min", str(cfg["ymin"]))
        yi_max = txt_field("Y Max", str(cfg["ymax"]))
        yi_min.on_change = lambda e: on_manual_change(e, "y", "ymin")
        yi_max.on_change = lambda e: on_manual_change(e, "y", "ymax")

        # Switches Auto
        def on_auto_toggle(e, axis):
            engine_instance.charts_config[chart_id][f"auto_{axis}"] = e.control.value
            engine_instance.save_config()
            page.pubsub.send_all("refresh_charts") # Notificar para redibujado inmediato

        sw_x = ft.Switch(label="Auto X", value=cfg["auto_x"], active_color=ACCENT_GREEN, 
                         label_text_style=ft.TextStyle(size=9), on_change=lambda e: on_auto_toggle(e, "x"))
        sw_y = ft.Switch(label="Auto Y", value=cfg["auto_y"], active_color=ACCENT_GREEN, 
                         label_text_style=ft.TextStyle(size=9), on_change=lambda e: on_auto_toggle(e, "y"))

        return ft.Container(
            content=ft.Column([
                help_txt,
                ft.Row([sw_x, sw_y], spacing=10),
                ft.Row([xi_min, xi_max], spacing=5),
                ft.Row([yi_min, yi_max], spacing=5),
            ], spacing=5),
            padding=ft.Padding(5, 8, 5, 8),
            border=ft.Border(bottom=ft.BorderSide(0.5, BORDER_COL))
        )

    sdr_content = ft.Column(
        [
            section_title("🎯", "Modo de Escala Inteligente", ACCENT_AMBER),
            ft.Text("Las gráficas se centran automáticamente al nivel de referencia y señal "
                    "a menos que cambies un valor manualmente.", color=TEXT_MUTED, size=9, italic=True),
            reset_btn,
            divider(),

            section_title("📡", "Pestaña 1: Monitoreo RAW", ACCENT_CYAN),
            _axis_control("Gráfica 1: Espectro RAW", "mon_raw_spec"),
            _axis_control("Gráfica 2: Amplitud RAW", "mon_raw_amp"),
            
            section_title("🔍", "Pestaña 2: Monitoreo Filtrado", ACCENT_GREEN),
            lbl("Filtro Moving Average (ms)"),
            ma_win_f,
            _axis_control("Gráfica 1: Espectro Filtrado", "mon_filt_spec"),
            _axis_control("Gráfica 2: Amplitud Filtrada", "mon_filt_amp"),

            section_title("🌈", "Pestaña 3: Espectrograma", "#FF6B9D"),
            lbl("Historial Cascada (segundos)"),
            wf_sec_f,
            _axis_control("Cascada (Waterfall)", "spec_wf"),

            section_title("📊", "Pestaña 4: Estadística", ACCENT_AMBER),
            _axis_control("Histograma de Amplitud", "stat_hist"),

            section_title("⚡", "Pestaña 5: Potencia vs Tiempo", "#FFB347"),
            _axis_control("Potencia Instantánea", "pow_time"),

            section_title("📶", "Pestaña 6: SNR vs Frecuencia", "#00CED1"),
            _axis_control("SNR por Bin de Freq", "snr_freq"),

            section_title("🌍", "SDR & Frecuencia", TEXT_MAIN),
            lbl("Freq Central (MHz)"), freq_f,
            lbl("Sample Rate (MSps)"), rate_f,
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
