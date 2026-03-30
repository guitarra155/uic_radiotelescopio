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
def _accordion_section(icon: str, title: str, accent: str,
                       content: ft.Control, expanded: bool = False
                       ) -> tuple:
    """
    Devuelve (header_container, body_container) para usar en el acordeón.
    body_container.visible se maneja externamente.
    """
    arrow = ft.Text("▼" if expanded else "▶", color=accent, size=9)
    dot   = ft.Container(width=6, height=6, bgcolor=accent, border_radius=3)

    header = ft.Container(
        content=ft.Row([
            dot,
            ft.Text(f"{icon}  {title}", color=accent, size=12,
                    weight=ft.FontWeight.W_600, expand=1),
            arrow,
        ], spacing=8),
        bgcolor=PANEL_BG,
        border=ft.Border(
            bottom=ft.BorderSide(1, BORDER_COL),
            left=ft.BorderSide(2, accent if expanded else "transparent"),
        ),
        padding=ft.Padding(left=14, top=10, right=14, bottom=10),
        ink=True,
        border_radius=ft.BorderRadius(top_left=6, top_right=6,
                                      bottom_left=0, bottom_right=0),
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
            label=label, value=value,
            options=[ft.dropdown.Option(o) for o in options],
            color=TEXT_MAIN, bgcolor=DARK_BG,
            border_color=BORDER_COL, focused_border_color=ACCENT_CYAN,
            border_radius=8, expand=True,
        )

    # ─────────────────────────────────────────────────────────────────────────
    # ── Controles de la sección Fuente & SDR ─────────────────────────────────
    # ─────────────────────────────────────────────────────────────────────────
    filepath_input = txt_field("Ruta del Archivo .iq",
                               engine_instance.iq_filename,
                               "Ej: C:\\Datos\\señal.iq")
    def on_filepath_change(e):
        engine_instance.iq_filename = e.control.value
        engine_instance.save_config()
    filepath_input.on_change = on_filepath_change

    fmt_dd = dd("Formato Datos .iq", engine_instance.iq_format,
                 ["uint8", "int8", "complex64"])

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
        content=ft.Column([
            ft.Radio(value="sdr",  label="🛠️ SDR Físico (RTL/HackRF)",
                     active_color=ACCENT_GREEN),
            ft.Radio(value="file", label="📼 Archivo Local (.iq)",
                     active_color=ACCENT_AMBER),
        ], spacing=4)
    )

    freq_f = txt_field("Frecuencia (MHz)", "1420.40", "e.g. 1420.40")
    rate_f = txt_field("Sample Rate (MSps)", "2.4", "")

    db_min_f = txt_field("Min Y (dBFS) Espectro", str(engine_instance.db_min),  "-100")
    db_max_f = txt_field("Max Y (dBFS) Espectro", str(engine_instance.db_max),  "-40")
    
    pwr_db_min_f = txt_field("Min Potencia (dBFS)", str(engine_instance.power_db_min), "-100")
    pwr_db_max_f = txt_field("Max Potencia (dBFS)", str(engine_instance.power_db_max), "0")

    snr_db_min_f = txt_field("Min Magnitud (dB)", str(engine_instance.snr_db_min), "-10")
    snr_db_max_f = txt_field("Max Magnitud (dB)", str(engine_instance.snr_db_max), "40")

    f_min_f  = txt_field("Min X (MHz)",  str(engine_instance.f_min),   "1419.0")
    f_max_f  = txt_field("Max X (MHz)",  str(engine_instance.f_max),   "1421.0")
    amp_min_f = txt_field("Min Amp (V)", str(engine_instance.amp_min), "0.0")
    amp_max_f = txt_field("Max Amp (V)", str(engine_instance.amp_max), "1.0")
    wf_sec_f  = txt_field("Cascada (s)", str(engine_instance.waterfall_history_sec), "60")

    def update_bounds(e):
        for attr, field in [("db_min", db_min_f), ("db_max", db_max_f),
                             ("power_db_min", pwr_db_min_f), ("power_db_max", pwr_db_max_f),
                             ("snr_db_min", snr_db_min_f), ("snr_db_max", snr_db_max_f),
                             ("f_min",  f_min_f),  ("f_max",  f_max_f),
                             ("amp_min", amp_min_f),("amp_max", amp_max_f),
                             ("waterfall_history_sec", wf_sec_f)]:
            try: setattr(engine_instance, attr, float(field.value))
            except ValueError: pass
        engine_instance.save_config()

    for field in [db_min_f, db_max_f, pwr_db_min_f, pwr_db_max_f, snr_db_min_f, snr_db_max_f, f_min_f, f_max_f,
                  amp_min_f, amp_max_f, wf_sec_f]:
        field.on_change = update_bounds
        field.on_submit = update_bounds

    def lbl(t): return ft.Text(t, color=TEXT_MUTED, size=10)

    sdr_content = ft.Column([
        lbl("Piso de Ruido / Rango (Espectrograma / Waterfall)"),
        ft.Row([db_min_f, db_max_f], spacing=8),
        ft.Divider(color=BORDER_COL, height=8),
        lbl("⚡ Rango Y (Potencia vs. Tiempo)"),
        ft.Row([pwr_db_min_f, pwr_db_max_f], spacing=8),
        ft.Divider(color=BORDER_COL, height=8),
        lbl("📶 Rango Y (Magnitud de SNR vs Frecuencia)"),
        ft.Row([snr_db_min_f, snr_db_max_f], spacing=8),
        ft.Divider(color=BORDER_COL, height=8),
        lbl("Modo de Adquisición"),
        mode_rg,
        ft.Divider(color=BORDER_COL, height=10),
        lbl("Archivo .iq y Formato"),
        filepath_input,
        fmt_dd,
        ft.Divider(color=BORDER_COL, height=10),
        lbl("Frecuencia y Tasa de Muestreo"),
        ft.Row([freq_f, rate_f], spacing=8),
        ft.Divider(color=BORDER_COL, height=10),
        lbl("Rango X (Frecuencia visible MHz)"),
        ft.Row([f_min_f, f_max_f], spacing=8),
        lbl("Amplitud (Voltaje)  — IQ plot"),
        ft.Row([amp_min_f, amp_max_f], spacing=8),
        lbl("Historial Cascada (segundos)"),
        wf_sec_f,
    ], spacing=8, scroll=ft.ScrollMode.AUTO)

    # ─────────────────────────────────────────────────────────────────────────
    # ── Controles de la sección Estado ───────────────────────────────────────
    # ─────────────────────────────────────────────────────────────────────────
    dev_rows = [("Modelo SDR",  "RTL-SDR v3 / HackRF", TEXT_MAIN),
                ("Conexión",    "Archivo Local (.iq)",  ACCENT_CYAN),
                ("Estado",      "Listo para leer",      ACCENT_GREEN),
                ("Temperatura", "-- °C",                TEXT_MUTED),
                ("DSP Worker",  "Multihilo Async",      TEXT_MAIN)]

    info_rows = [ft.Row([ft.Text(k, color=TEXT_MUTED, size=11, expand=1),
                          ft.Text(v, color=c, size=11, expand=1,
                                  weight=ft.FontWeight.W_600)])
                 for k, v, c in dev_rows]

    estado_content = ft.Column([
        *info_rows,
        ft.Divider(color=BORDER_COL, height=8),
        ft.Text("💡 Instrucciones", color=ACCENT_GREEN, size=11,
                weight=ft.FontWeight.BOLD),
        ft.Text(
            "1. Ubique el archivo .iq guardado en su PC.\n"
            "2. Elija el formato correcto.\n"
            "3. Presione 'Reproducir' en el stream.",
            color=TEXT_MUTED, size=10,
        ),
    ], spacing=6)

    # ─────────────────────────────────────────────────────────────────────────
    # ── Controles de la sección Algoritmo DSP ────────────────────────────────
    # ─────────────────────────────────────────────────────────────────────────
    METHODS = ["AR/Burg", "CWT/Morlet", "Pseudo-MUSIC", "ESPRIT"]

    # Usamos RadioGroup porque el Dropdown estaba fallando internamente en Flet
    method_rg = ft.RadioGroup(
        value=engine_instance.algo_params.get("method", "AR/Burg"),
        content=ft.Column([
            ft.Radio(value=m, label=m, active_color=ACCENT_CYAN) for m in METHODS
        ], spacing=2)
    )

    ar_order_f = txt_field("Orden AR / Burg",      "64", "16–256")
    music_ns_f = txt_field("# Señales MUSIC/ESPRIT", "3", "1–10")

    algo_status_txt = ft.Text("Esperando stream...", color=TEXT_MUTED,
                               size=9, italic=True)
    algo_running = [False]
    algo_counter = [0]
    algo_gen     = [0]          # epoch: se incrementa al cambiar método
    ALGO_EVERY_N = 30

    ar_order_row = ft.Container(content=ar_order_f, visible=True)
    music_ns_row = ft.Container(content=music_ns_f, visible=False)

    def _update_param_visibility():
        m = engine_instance.algo_params.get("method", "AR/Burg")
        ar_order_row.visible = (m == "AR/Burg")
        music_ns_row.visible = (m in ("Pseudo-MUSIC", "ESPRIT"))
        try:
            if ar_order_row.page: ar_order_row.update()
            if music_ns_row.page: music_ns_row.update()
        except Exception: pass

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
            try: algo_status_txt.update()
            except: pass
            
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
        try: engine_instance.algo_params["ar_order"] = int(ar_order_f.value or 64)
        except: pass
        try: engine_instance.algo_params["n_signals"] = int(music_ns_f.value or 3)
        except: pass
        engine_instance.save_config()
    ar_order_f.on_change = _save_params; ar_order_f.on_submit = _save_params
    music_ns_f.on_change = _save_params; music_ns_f.on_submit = _save_params

    async def _run_selected_algo():
        if algo_running[0]: return
        algo_running[0] = True
        my_gen = algo_gen[0]
        method = engine_instance.algo_params.get("method", "AR/Burg")
        algo_status_txt.value = f"⏳ {method}..."

        try: algo_status_txt.update()
        except: pass
        try:
            iq        = engine_instance.amplitude_data
            sr        = engine_instance.sample_rate
            fc        = engine_instance.center_freq
            order_val = engine_instance.algo_params.get("ar_order", 64)
            ns_val    = engine_instance.algo_params.get("n_signals", 3)

            from core.advanced_dsp import run_ar_burg, run_cwt, run_pseudo_music, run_esprit
            from ui.charts import chart_ar_spectrum, chart_cwt_map, chart_music_spectrum

            def _compute():
                if method == "AR/Burg":
                    return chart_ar_spectrum(
                        run_ar_burg(iq, order=order_val, sample_rate=sr, center_freq=fc))
                elif method == "CWT/Morlet":
                    return chart_cwt_map(run_cwt(iq, sample_rate=sr))
                elif method == "Pseudo-MUSIC":
                    return chart_music_spectrum(
                        run_pseudo_music(iq, n_signals=ns_val, sample_rate=sr, center_freq=fc))
                else:
                    return chart_music_spectrum(
                        run_esprit(iq, n_signals=ns_val, sample_rate=sr, center_freq=fc))

            b64 = await asyncio.to_thread(_compute)

            # ── Descartar obsoletos SIN romper el lock del nuevo ──
            if algo_gen[0] != my_gen:
                return

            engine_instance.algo_results["current"]        = b64
            engine_instance.algo_results["current_method"] = method
            page.pubsub.send_all("algo_results_ready")
            algo_status_txt.value = f"✓ {method}"
        except Exception as ex:
            algo_status_txt.value = f"⚠ ERROR: {str(ex)[:35]}"
            print("CRITICAL ALGO ERROR:", ex)
        finally:
            # Solo liberar el lock si nosotros somos la generación actual
            if algo_gen[0] == my_gen:
                algo_running[0] = False
            try: algo_status_txt.update()
            except: pass

    async def on_algo_refresh(msg):
        if msg != "refresh_charts": return
        if not engine_instance.is_playing: return
        algo_counter[0] += 1
        if algo_counter[0] % ALGO_EVERY_N == 0:
            await _run_selected_algo()
    page.pubsub.subscribe(on_algo_refresh)

    algo_content = ft.Column([
        ft.Row([
            ft.Text("Resultado en pestaña  🔬 Algoritmo DSP",
                    color=TEXT_MUTED, size=9, italic=True, expand=1),
            algo_status_txt,
        ]),
        ft.Text("Método Avanzado:", color=TEXT_MAIN, size=12),
        method_rg,
        ar_order_row,
        music_ns_row,
    ], spacing=8)

    # ─────────────────────────────────────────────────────────────────────────
    # ── ACORDEÓN ─────────────────────────────────────────────────────────────
    # ─────────────────────────────────────────────────────────────────────────
    SECTIONS = [
        ("📊", "Estado",           ACCENT_GREEN, estado_content, False),
        ("⚙️",  "Fuente & SDR",    ACCENT_CYAN,  sdr_content,    True),
        ("🔬", "Algoritmo DSP",   "#B380FF",    algo_content,   False),
    ]

    headers, bodies, arrows, dots = [], [], [], []

    def make_toggle(idx, accent_color):
        def _toggle(e):
            for i in range(len(bodies)):
                is_active = (i == idx)
                bodies[i].visible = is_active
                bodies[i].border = ft.Border(
                    left=ft.BorderSide(2, accent_color if is_active else "transparent"),
                    bottom=ft.BorderSide(1, BORDER_COL),
                )
                arrows[i].value = "▼" if is_active else "▶"
                headers[i].border = ft.Border(
                    bottom=ft.BorderSide(1, BORDER_COL),
                    left=ft.BorderSide(2, (SECTIONS[i][2] if is_active
                                          else "transparent")),
                )
                arrows[i].color  = SECTIONS[i][2]
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
