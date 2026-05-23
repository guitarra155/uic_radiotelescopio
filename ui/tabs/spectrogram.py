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
    ALGO_EVERY_N = 10  # Reducido para mayor fluidez
    _last_dsp_results = {}
    _last_dsp_params = {}

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
    cwt_scales_f = txt_field(
        "Escalas CWT", str(engine_instance.algo_params.get("cwt_n_scales", 64)), "12-256"
    )

    ar_order_row = ft.Container(content=ar_order_f, visible=(current_method[0] == "ar_burg_2d"), width=160)
    corr_lag_row = ft.Container(content=corr_lag_f, visible=(current_method[0] == "correlogram_2d"), width=160)
    cwt_scales_row = ft.Container(content=cwt_scales_f, visible=(current_method[0] == "cwt"), width=160)

    def _update_param_visibility():
        m = current_method[0]
        ar_order_row.visible = (m == "ar_burg_2d")
        corr_lag_row.visible = (m == "correlogram_2d")
        cwt_scales_row.visible = (m == "cwt")
        try:
            if ar_order_row.page: ar_order_row.update()
            if corr_lag_row.page: corr_lag_row.update()
            if cwt_scales_row.page: cwt_scales_row.update()
        except Exception:
            pass

    def on_method_change(e):
        try:
            val = e.control.value
            if not val:
                return
                
            current_method[0] = val
            engine_instance.active_spec_method = val
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
            cwt_scales_row.visible = (val == "cwt")

            # Actualizar controles afectados y refrescar panel de config lateral
            controls_to_update = [desc_text, status_badge, ar_order_row, corr_lag_row, cwt_scales_row]
            for c in controls_to_update:
                if c.page:
                    c.update()
            page.pubsub.send_all("tab_changed")  # refresca el panel de config
            
            # Lanzar tarea pesada usando la caché si ya existe una anterior
            if val != "waterfall":
                if e.page:
                    async def _run_it(*args):
                        await _render_advanced_method(force_recompute=False)
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
        try:
            engine_instance.algo_params["cwt_n_scales"] = int(cwt_scales_f.value or 64)
        except Exception:
            pass
        engine_instance.save_config()

    ar_order_f.on_submit = _save_params
    ar_order_f.on_blur = _save_params
    corr_lag_f.on_submit = _save_params
    corr_lag_f.on_blur = _save_params
    cwt_scales_f.on_submit = _save_params
    cwt_scales_f.on_blur = _save_params

    async def _render_advanced_method(force_recompute=False):
        """Ejecuta CWT/AR/Correlogram 2D en hilo secundario."""
        my_gen = algo_gen[0]
        method = current_method[0]
        sr = engine_instance.sample_rate
        fc = engine_instance.center_freq

        # ── Todos los métodos 2D usan el buffer IQ circular de alta resolución ──
        if engine_instance._corr_buf_full:
            buf_idx = engine_instance._corr_buf_idx
            iq = np.roll(engine_instance.corr_iq_buffer, -buf_idx).copy()
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

        from core.advanced_dsp import run_cwt_2d, run_ar_burg_2d, run_correlogram_2d
        from ui.charts import chart_cwt_map, chart_ar_spectrogram, chart_correlogram_spectrogram

        cfg_spec = engine_instance.charts_config.get("spec_wf", {})
        f_min_vis = cfg_spec.get("xmin", fc - 1.0)
        f_max_vis = cfg_spec.get("xmax", fc + 1.0)
        span_mhz  = f_max_vis - f_min_vis
        offset    = engine_instance.db_noise_floor - 20.0

        current_params = {
            "ar_order": engine_instance.algo_params.get("ar_order", 64),
            "corr_max_lag": engine_instance.algo_params.get("corr_max_lag", 37),
            "cwt_n_scales": engine_instance.algo_params.get("cwt_n_scales", 64),
            "sample_rate": sr,
            "center_freq": fc,
            "iq_len": len(iq),
            "span_mhz": span_mhz
        }

        # Intentar renderizado instantáneo usando la caché
        if not force_recompute and method in _last_dsp_results:
            cached_params = _last_dsp_params.get(method, {})
            if cached_params == current_params:
                result = _last_dsp_results[method]
                def _replot():
                    if method == "cwt":
                        return chart_cwt_map(result)
                    elif method == "ar_burg_2d":
                        return chart_ar_spectrogram(result)
                    elif method == "correlogram_2d":
                        return chart_correlogram_spectrogram(result)
                    return None
                
                try:
                    b64 = await asyncio.to_thread(_replot)
                    if algo_gen[0] != my_gen:
                        return
                    if b64:
                        img.src = b64
                        status_badge.value = f"OK — {dict(_METHODS).get(method, method)} (Renderizado Rápido)"
                        status_badge.color = _METHOD_COLORS.get(method, ACCENT_CYAN)
                        if img.page: img.update()
                        if status_badge.page: status_badge.update()
                except Exception as ex:
                    print(f"Error replotting cached {method}: {ex}")
                return

        def _compute():
            import time as _time
            t0 = _time.perf_counter()

            if method == "cwt":
                n_scales = engine_instance.algo_params.get("cwt_n_scales", 64)
                result = run_cwt_2d(
                    iq,
                    sample_rate=sr,
                    n_scales=n_scales,
                    center_freq=fc,
                    block_size=5000,
                    block_overlap=0.5,
                    f_min_visual=f_min_vis,
                    f_max_visual=f_max_vis,
                    offset_calibracion=offset,
                )
                b64 = chart_cwt_map(result)
                t_total = _time.perf_counter() - t0
                n_blocks = result["matrix"].shape[0]
                print(
                    f"[CWT 2D] IQ={len(iq)} muestras | "
                    f"Bloques={n_blocks} | "
                    f"Total={t_total*1000:.1f}ms"
                )
                return result, b64

            elif method == "ar_burg_2d":
                order = engine_instance.algo_params.get("ar_order", 20)
                n_freqs = engine_instance.algo_params.get("ar_n_freqs", 1024)
                result = run_ar_burg_2d(
                    iq,
                    order=order,
                    n_freqs=n_freqs,
                    window_len=128,
                    overlap=0.5,
                    block_size=5000,
                    block_overlap=0.5,
                    sample_rate=sr,
                    center_freq=fc,
                    offset_calibracion=offset,
                    f_min_visual=f_min_vis,
                    f_max_visual=f_max_vis,
                )
                b64 = chart_ar_spectrogram(result)
                t_total = _time.perf_counter() - t0
                n_segs = result["matrix"].shape[0]
                print(
                    f"[AR/Burg 2D] IQ={len(iq)} muestras | "
                    f"Segs={n_segs} | "
                    f"Total={t_total*1000:.1f}ms"
                )
                return result, b64

            elif method == "correlogram_2d":
                max_lag = engine_instance.algo_params.get("corr_max_lag", 37)
                t0_c = _time.perf_counter()
                result = run_correlogram_2d(
                    iq,
                    max_lag=max_lag,
                    n_freqs=1024,
                    window_len=128,
                    overlap=0.5,
                    block_size=5000,
                    block_overlap=0.5,
                    offset_calibracion=offset,
                    f_min_visual=f_min_vis,
                    f_max_visual=f_max_vis,
                    sample_rate=sr,
                    center_freq=fc,
                )
                t_dsp = _time.perf_counter() - t0_c
                t1 = _time.perf_counter()
                b64 = chart_correlogram_spectrogram(result)
                t_chart = _time.perf_counter() - t1
                n_segs = result["matrix"].shape[0]
                print(
                    f"[Correlograma] IQ={len(iq)} muestras | "
                    f"Segs={n_segs} | "
                    f"DSP={t_dsp*1000:.1f}ms | "
                    f"Chart={t_chart*1000:.1f}ms | "
                    f"Total={(t_dsp+t_chart)*1000:.1f}ms"
                )
                return result, b64
            return None, None


        try:
            res_tuple = await asyncio.to_thread(_compute)
            if algo_gen[0] != my_gen:
                return  # El usuario cambio de metodo durante el calculo
            result, b64 = res_tuple
            if result is not None and b64:
                # Guardar en la caché
                _last_dsp_results[method] = result
                _last_dsp_params[method]  = current_params

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

        if is_rendering[0]:
            return
        is_rendering[0] = True
        try:
            if msg == "tab_changed":
                # Refresco forzado al cambiar configuración, para cualquier método
                if method == "waterfall":
                    img.src = await asyncio.to_thread(chart_spectrogram)
                    if img.page: img.update()
                else:
                    await _render_advanced_method(force_recompute=False)
                return

            if method == "waterfall":
                img.src = await asyncio.to_thread(chart_spectrogram)
                if img.page: img.update()
            elif method == "correlogram_2d":
                await _render_advanced_method(force_recompute=True)
            else:
                algo_counter[0] += 1
                if algo_counter[0] % ALGO_EVERY_N == 0:
                    await _render_advanced_method(force_recompute=True)
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
                    cwt_scales_row,
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
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
    )
    return ft.Container(content=main_container, expand=True)
