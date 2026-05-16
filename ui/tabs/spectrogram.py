"""
tabs/spectrogram.py
Pestaña "Espectrograma" con selector de método 2D (Tiempo × Frecuencia).
Métodos: Waterfall FFT, CWT/Morlet, AR/Burg 2D, Correlograma 2D.
"""

import numpy as np
import flet as ft
from core.constants import *
from ui.charts import chart_spectrogram
from ui.components.shared import panel, border_all

_METHODS = [
    ("waterfall", "Waterfall FFT"),
    ("cwt", "CWT / Morlet"),
    ("ar_burg_2d", "AR / Burg 2D"),
    ("correlogram_2d", "Correlograma 2D"),
]

_METHOD_COLORS = {
    "waterfall": ACCENT_CYAN,
    "cwt": "#00C8FF",
    "ar_burg_2d": "#B380FF",
    "correlogram_2d": "#40E0D0",
}

_METHOD_DESCRIPTIONS = {
    "waterfall": "STFT clasico: cada fila es una FFT del bloque temporal. Colormap Inferno.",
    "cwt": "Transformada Wavelet Continua (Morlet): resolucion adaptativa tiempo-frecuencia.",
    "ar_burg_2d": "Modelo parametrico AR/Burg en ventanas deslizantes: alta resolucion espectral.",
    "correlogram_2d": "PSD via autocorrelacion (Wiener-Khinchin) en ventanas deslizantes.",
}


def build_spectrogram(page: ft.Page, key_state: dict) -> ft.Control:
    from core.dsp_engine import engine_instance
    from ui.components.shared import txt_field
    import asyncio

    # Estado local
    current_method = [engine_instance.algo_params.get("spec2d_method", "waterfall")]
    is_rendering = [False]
    algo_counter = [0]
    algo_gen = [0]
    ALGO_EVERY_N = 25

    img = ft.Image(
        src=chart_spectrogram(),
        fit=ft.BoxFit.FILL,
        border_radius=10,
        expand=True,
        gapless_playback=True,
    )

    # Selector usando RadioGroup (100% fiable, usado exitosamente en otras partes)
    method_radio = ft.RadioGroup(
        value=current_method[0],
        content=ft.Row([
            ft.Radio(value=k, label=lbl, active_color=ACCENT_CYAN) for k, lbl in _METHODS
        ], wrap=True, spacing=10)
    )

    # Descripcion + status del metodo activo
    _init_method = current_method[0]
    desc_text = ft.Text(
        _METHOD_DESCRIPTIONS.get(_init_method, ""),
        color=TEXT_MUTED, size=10, italic=True,
    )
    status_badge = ft.Text(
        "Listo" if _init_method == "waterfall" else "Esperando primer frame...",
        color=ACCENT_GREEN if _init_method == "waterfall" else ACCENT_AMBER,
        size=10, weight=ft.FontWeight.W_600,
    )

    # Parametros contextuales
    ar_order_f = txt_field(
        "Orden AR", str(engine_instance.algo_params.get("ar_order", 64)), "16-256"
    )
    corr_lag_f = txt_field(
        "Max Lag", str(engine_instance.algo_params.get("corr_max_lag", 37)), "10-256"
    )

    ar_order_row = ft.Container(content=ar_order_f, visible=(current_method[0] == "ar_burg_2d"), width=160)
    corr_lag_row = ft.Container(content=corr_lag_f, visible=(current_method[0] == "correlogram_2d"), width=160)

    def _update_param_visibility():
        m = current_method[0]
        ar_order_row.visible = (m == "ar_burg_2d")
        corr_lag_row.visible = (m == "correlogram_2d")
        try:
            if ar_order_row.page: ar_order_row.update()
            if corr_lag_row.page: corr_lag_row.update()
        except Exception:
            pass

    def on_method_change(e):
        try:
            val = e.control.value
            if not val:
                return
                
            current_method[0] = val
            engine_instance.algo_params["spec2d_method"] = val
            
            try:
                engine_instance.save_config()
            except Exception:
                pass
                
            algo_gen[0] += 1
            algo_counter[0] = 0

            # Actualizar componentes de UI individuales
            desc_text.value = _METHOD_DESCRIPTIONS.get(val, "")
            status_badge.value = "Calculando..." if val != "waterfall" else "Listo"
            status_badge.color = ACCENT_AMBER if val != "waterfall" else ACCENT_GREEN
            
            ar_order_row.visible = (val == "ar_burg_2d")
            corr_lag_row.visible = (val == "correlogram_2d")

            # Actualizar solo los controles afectados
            controls_to_update = [desc_text, status_badge, ar_order_row, corr_lag_row]
            for c in controls_to_update:
                if c.page:
                    c.update()
            
            # Lanzar tarea pesada
            if val != "waterfall":
                if e.page:
                    async def _run_it(*args):
                        await _render_advanced_method()
                    e.page.run_task(_run_it)
        except Exception as ex:
            print(f"Error UI fatal: {ex}")

    method_radio.on_change = on_method_change

    def _save_params(e=None):
        try:
            engine_instance.algo_params["ar_order"] = int(ar_order_f.value or 64)
        except Exception:
            pass
        try:
            engine_instance.algo_params["corr_max_lag"] = int(corr_lag_f.value or 512)
        except Exception:
            pass
        engine_instance.save_config()

    ar_order_f.on_submit = _save_params
    ar_order_f.on_blur = _save_params
    corr_lag_f.on_submit = _save_params
    corr_lag_f.on_blur = _save_params

    async def _render_advanced_method():
        """Ejecuta CWT/AR/Correlogram 2D en hilo secundario."""
        my_gen = algo_gen[0]
        method = current_method[0]
        sr = engine_instance.sample_rate
        fc = engine_instance.center_freq

        # ── Fuente de IQ según el método ─────────────────────────────────────
        if method == "correlogram_2d":
            # Usar el buffer circular de alta resolución (50k muestras sin decimar)
            if engine_instance._corr_buf_full:
                idx = engine_instance._corr_buf_idx
                iq = np.roll(engine_instance.corr_iq_buffer, -idx).copy()
            elif engine_instance._corr_buf_idx > 0:
                iq = engine_instance.corr_iq_buffer[:engine_instance._corr_buf_idx].copy()
            else:
                status_badge.value = "Acumulando muestras... espera unos segundos"
                status_badge.color = ACCENT_AMBER
                try:
                    if status_badge.page: status_badge.update()
                except Exception:
                    pass
                return
        else:
            # CWT / AR: fuente original (amplitude_ma_data diezmado)
            iq = engine_instance.amplitude_ma_data.copy()
            if not np.any(iq != 0):
                iq = engine_instance.amplitude_data.copy()
            if not np.any(iq != 0):
                wf = engine_instance.waterfall_data
                if wf is not None and wf.size > 0:
                    row = wf[engine_instance.waterfall_idx, :]
                    if np.any(row != -100.0):
                        iq = 10 ** (row / 20.0)
                    else:
                        status_badge.value = "Sin datos — inicia el stream (Play)"
                        status_badge.color = ACCENT_RED
                        try:
                            if status_badge.page: status_badge.update()
                        except Exception:
                            pass
                        return
                else:
                    status_badge.value = "Sin datos — inicia el stream (Play)"
                    status_badge.color = ACCENT_RED
                    try:
                        if status_badge.page: status_badge.update()
                    except Exception:
                        pass
                    return

        from core.advanced_dsp import run_cwt, run_ar_burg_2d, run_correlogram_2d
        from ui.charts import chart_cwt_map, chart_ar_spectrogram, chart_correlogram_spectrogram

        def _compute():
            if method == "cwt":
                iq_cwt = iq[:512] if len(iq) > 512 else iq
                return chart_cwt_map(run_cwt(iq_cwt, sample_rate=sr, n_scales=32))
            elif method == "ar_burg_2d":
                order = engine_instance.algo_params.get("ar_order", 64)
                return chart_ar_spectrogram(
                    run_ar_burg_2d(iq, order=order, sample_rate=sr, center_freq=fc)
                )
            elif method == "correlogram_2d":
                max_lag    = engine_instance.algo_params.get("corr_max_lag", 37)
                span_mhz   = getattr(engine_instance, "visual_span_mhz", 2.0)
                f_min_vis  = fc - span_mhz / 2
                f_max_vis  = fc + span_mhz / 2
                return chart_correlogram_spectrogram(
                    run_correlogram_2d(
                        iq,
                        max_lag=max_lag,
                        n_freqs=1024,
                        window_len=128,
                        overlap=0.5,
                        block_size=5000,
                        block_overlap=0.5,
                        offset_calibracion=engine_instance.db_noise_floor - 20.0,
                        f_min_visual=f_min_vis,
                        f_max_visual=f_max_vis,
                        sample_rate=sr,
                        center_freq=fc,
                    )
                )
            return None

        try:
            b64 = await asyncio.to_thread(_compute)
            if algo_gen[0] != my_gen:
                return  # El usuario cambio de metodo durante el calculo
            if b64:
                img.src = b64
                status_badge.value = f"OK — {dict(_METHODS).get(method, method)}"
                status_badge.color = _METHOD_COLORS.get(method, ACCENT_CYAN)
                try:
                    if img.page: img.update()
                    if status_badge.page: status_badge.update()
                except Exception:
                    pass
        except Exception as ex:
            status_badge.value = f"Error: {str(ex)[:60]}"
            status_badge.color = ACCENT_RED
            try:
                if status_badge.page: status_badge.update()
            except Exception:
                pass
            print(f"[Spec2D] ERROR ({method}): {ex}")
            import traceback; traceback.print_exc()

    async def on_refresh(msg):
        if msg not in ("refresh_charts", "tab_changed"):
            return
        if engine_instance.active_tab != 2:
            return
        method = current_method[0]

        if msg == "tab_changed":
            if method != "waterfall":
                await _render_advanced_method()
            return

        if is_rendering[0]:
            return
        is_rendering[0] = True
        try:
            if method == "waterfall":
                img.src = await asyncio.to_thread(chart_spectrogram)
                if img.page: img.update()
            else:
                algo_counter[0] += 1
                if algo_counter[0] % ALGO_EVERY_N == 0:
                    await _render_advanced_method()
        finally:
            is_rendering[0] = False

    page.pubsub.subscribe(on_refresh)

    def reset_defaults(e):
        engine_instance.reset_to_defaults()
        engine_instance.save_config()

    # Zoom (funciona para waterfall; los otros metodos no dependen de db_min/db_max)
    def on_zoom_scroll(e: ft.ScrollEvent):
        ctrl = key_state.get("ctrl", False)
        shift = key_state.get("shift", False)

        if not ctrl and not shift:
            return

        dir = 1 if e.scroll_delta_y > 0 else -1
        factor = 0.15 * dir

        if ctrl:
            s_db = engine_instance.db_max - engine_instance.db_min
            engine_instance.db_min -= s_db * factor
            engine_instance.db_max += s_db * factor
            engine_instance.save_config()
        elif shift:
            s_f = engine_instance.f_max - engine_instance.f_min
            engine_instance.f_min -= s_f * factor
            engine_instance.f_max += s_f * factor
            engine_instance.save_config()

    def sw(color):
        return ft.Container(width=14, height=14, bgcolor=color, border_radius=4)

    legend = ft.Row(
        [
            sw(ACCENT_RED),
            ft.Text("RFI Intenso", color=TEXT_MAIN, size=10),
            sw(ACCENT_AMBER),
            ft.Text("Senal moderada", color=TEXT_MAIN, size=10),
            sw("#3F51B5"),
            ft.Text("Ruido base", color=TEXT_MAIN, size=10),
            sw(ACCENT_CYAN),
            ft.Text("HI 1420.40 MHz", color=TEXT_MAIN, size=10),
        ],
        spacing=8,
        alignment=ft.MainAxisAlignment.CENTER,
    )

    main_container = ft.Container(
        expand=True,
        padding=ft.Padding(left=14, top=14, right=14, bottom=14),
    )

    main_container.content = ft.Column(
        [
            ft.Row(
                [
                    ft.Text(
                        "Espectrograma 2D",
                        color=ACCENT_CYAN,
                        weight=ft.FontWeight.BOLD,
                        size=14,
                    ),
                    method_radio,
                    ar_order_row,
                    corr_lag_row,
                    ft.TextButton(
                        "Restaurar",
                        on_click=reset_defaults,
                        style=ft.ButtonStyle(color=ACCENT_CYAN),
                    ),
                ],
                alignment=ft.MainAxisAlignment.START,
                spacing=12,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            ft.Row([desc_text, ft.Container(expand=True), status_badge], spacing=8),
            ft.Container(
                content=ft.GestureDetector(
                    mouse_cursor=ft.MouseCursor.ZOOM_IN,
                    on_scroll=on_zoom_scroll,
                    drag_interval=0,
                    content=img,
                    expand=True,
                ),
                expand=True,
                bgcolor=PANEL_BG,
                border_radius=10,
                border=border_all(),
                padding=6,
            ),
            legend,
        ],
        expand=True,
        spacing=8,
    )
    return main_container
