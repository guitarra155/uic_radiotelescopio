"""
tabs/algo_result.py
Pestaña única "🔬 Algoritmo DSP" — muestra el resultado del método
seleccionado en el panel derecho. Solo corre UN algoritmo a la vez.
"""

import flet as ft
from core.constants import *
from ui.components.shared import panel, border_all

_ALGO_META = {
    "AR/Burg": {
        "color": "#B380FF",
        "desc": (
            "Modelo Autorregresivo por método de Burg.\n"
            "Alta resolución espectral con pocas muestras.\n"
            "Ideal para señales CW estrechas."
        ),
    },
    "CWT/Morlet": {
        "color": "#00C8FF",
        "desc": (
            "Transformada Wavelet Continua con Morlet.\n"
            "Análisis tiempo-frecuencia simultáneo.\n"
            "Útil para señales transitorias o moduladas."
        ),
    },
    "Pseudo-MUSIC": {
        "color": "#FF4C4C",
        "desc": (
            "MUltiple SIgnal Classification.\n"
            "Resolución super-FFT mediante sub-espacio de ruido.\n"
            "Detecta frecuencias con gran precisión."
        ),
    },
    "ESPRIT": {
        "color": "#FF80AB",
        "desc": (
            "Estimation of Signal Parameters via\nRotational Invariance Techniques.\n"
            "Más eficiente que MUSIC para pocos componentes."
        ),
    },
    "Welch": {
        "color": "#FFD700",
        "desc": (
            "Densidad Espectral de Potencia (Welch).\n"
            "Reduce el ruido promediando periodogramas solapados."
        ),
    },
    "Correlograma": {
        "color": "#40E0D0",
        "desc": (
            "Estimación espectral indirecta (Wiener-Khinchin).\n"
            "FFT de la autocorrelación truncada (Blackman-Tukey).\n"
            "Útil para señales inmersas en ruido."
        ),
    },
}


def build_algo_result(page: ft.Page) -> ft.Control:
    from core.dsp_engine import engine_instance
    from ui.charts import chart_algo_placeholder
    from ui.components.shared import txt_field
    import asyncio

    # Imagen del resultado — inicia con placeholder válido
    img = ft.Image(
        src=chart_algo_placeholder(),
        fit=ft.BoxFit.FILL,
        gapless_playback=True,
        border_radius=10,
        expand=True,
    )

    # Panel de info dinámico
    method_name   = ft.Text("—", color=ACCENT_CYAN, size=15,
                             weight=ft.FontWeight.BOLD)
    method_color_dot = ft.Container(width=12, height=12, border_radius=6,
                                    bgcolor=ACCENT_CYAN)
    method_desc   = ft.Text("—", color=TEXT_MUTED, size=10)
    status_txt    = ft.Text("Esperando stream...", color=TEXT_MUTED,
                            size=11, italic=True)

    # ─────────────────────────────────────────────────────────────────────────
    # ── Controles de la sección Algoritmo DSP ────────────────────────────────
    # ─────────────────────────────────────────────────────────────────────────

    algo_status_txt = ft.Text("Esperando stream...", color=TEXT_MUTED, size=9, italic=True)
    algo_running = [False]
    algo_counter = [0]
    algo_gen = [0]  # epoch: se incrementa al cambiar método
    ALGO_EVERY_N = 30

    method_rg = ft.RadioGroup(
        value=engine_instance.algo_params.get("method", "AR/Burg"),
        content=ft.Column(
            [
                ft.Radio(value="AR/Burg", label="AR/Burg", active_color=ACCENT_CYAN),
                ft.Radio(value="CWT/Morlet", label="CWT/Morlet", active_color=ACCENT_CYAN),
                ft.Radio(value="Pseudo-MUSIC", label="Pseudo-MUSIC", active_color=ACCENT_CYAN),
                ft.Radio(value="ESPRIT", label="ESPRIT", active_color=ACCENT_CYAN),
                ft.Divider(color=BORDER_COL, height=4),
                ft.Radio(value="Welch", label="Welch PSD", active_color="#FFD700"),
                ft.Radio(value="Correlograma", label="Correlograma", active_color="#40E0D0"),
                ft.Divider(color=BORDER_COL, height=4),
                ft.Radio(value="ASLT", label="ASLT ⚠ (pendiente)", active_color=TEXT_MUTED),
            ],
            spacing=2,
        ),
    )

    ar_order_f = txt_field("Orden AR / Burg", "64", "16–256")
    music_ns_f = txt_field("# Señales MUSIC/ESPRIT", "3", "1–10")
    corr_lag_f = txt_field("Max Lag Correlograma", "512", "128–1024")

    ar_order_row = ft.Container(content=ar_order_f, visible=True)
    music_ns_row = ft.Container(content=music_ns_f, visible=False)
    corr_lag_row = ft.Container(content=corr_lag_f, visible=False)

    def _update_param_visibility():
        m = engine_instance.algo_params.get("method", "AR/Burg")
        ar_order_row.visible = m == "AR/Burg"
        music_ns_row.visible = m in ("Pseudo-MUSIC", "ESPRIT")
        corr_lag_row.visible = m == "Correlograma"
        try:
            if ar_order_row.page: ar_order_row.update()
            if music_ns_row.page: music_ns_row.update()
            if corr_lag_row.page: corr_lag_row.update()
        except Exception:
            pass

    def _update_meta(do_update: bool = True):
        m = engine_instance.algo_params.get("method", "AR/Burg")
        meta = _ALGO_META.get(m, {})
        method_name.value = m
        method_name.color = meta.get("color", ACCENT_CYAN)
        method_color_dot.bgcolor = meta.get("color", ACCENT_CYAN)
        method_desc.value = meta.get("desc", "")
        if do_update:
            try:
                if method_name.page: method_name.update()
                if method_color_dot.page: method_color_dot.update()
                if method_desc.page: method_desc.update()
            except Exception as e:
                pass

    _update_meta(do_update=False)

    def on_method_change(e):
        try:
            val = e.control.value
            if val is None or val == "":
                return

            engine_instance.algo_params["method"] = val
            engine_instance.save_config()  # Persistencia!
            algo_gen[0] += 1
            algo_running[0] = False

            algo_status_txt.value = f"⚠ Clicked: {val}"
            status_txt.value = "Método cambiado — esperando recálculo..."
            status_txt.color = ACCENT_AMBER

            # Mostrar placeholder
            from ui.charts import chart_algo_placeholder as _ph
            img.src = _ph()

            try:
                if img.page: img.update()
                if status_txt.page: status_txt.update()
                if algo_status_txt.page: algo_status_txt.update()
            except: pass

            _update_meta()
            _update_param_visibility()

            if engine_instance.is_playing:
                page.run_task(_run_selected_algo)
        except Exception as ex:
            print(f"Error on on_method_change: {ex}")

    method_rg.on_change = on_method_change

    def _save_params(e=None):
        try:
            engine_instance.algo_params["ar_order"] = int(ar_order_f.value or 64)
        except: pass
        try:
            engine_instance.algo_params["n_signals"] = int(music_ns_f.value or 3)
        except: pass
        try:
            engine_instance.algo_params["corr_max_lag"] = int(corr_lag_f.value or 512)
        except: pass
        engine_instance.save_config()

    ar_order_f.on_change = _save_params
    ar_order_f.on_submit = _save_params
    music_ns_f.on_change = _save_params
    music_ns_f.on_submit = _save_params
    corr_lag_f.on_change = _save_params
    corr_lag_f.on_submit = _save_params

    async def _run_selected_algo():
        if algo_running[0]:
            return
        algo_running[0] = True
        my_gen = algo_gen[0]
        method = engine_instance.algo_params.get("method", "AR/Burg")
        algo_status_txt.value = f"⏳ {method}..."

        try:
            if algo_status_txt.page: algo_status_txt.update()
        except: pass

        try:
            iq = engine_instance.amplitude_ma_data
            sr = engine_instance.sample_rate
            fc = engine_instance.center_freq
            order_val = engine_instance.algo_params.get("ar_order", 64)
            ns_val = engine_instance.algo_params.get("n_signals", 3)
            wfft_val = engine_instance.algo_params.get("welch_fft", 1024)
            wovl_val = engine_instance.algo_params.get("welch_overlap", 0.5)
            corr_lag = engine_instance.algo_params.get("corr_max_lag", 512)

            from core.advanced_dsp import (
                run_ar_burg, run_cwt, run_pseudo_music, run_esprit,
                run_welch, run_correlogram, run_aslt,
            )
            from ui.charts import (
                chart_ar_spectrum, chart_cwt_map, chart_music_spectrum,
                chart_welch_spectrum, chart_correlogram_spectrum,
            )

            def _compute():
                if method == "AR/Burg":
                    return "ar", chart_ar_spectrum(run_ar_burg(iq, order=order_val, sample_rate=sr, center_freq=fc))
                elif method == "CWT/Morlet":
                    return "cwt", chart_cwt_map(run_cwt(iq, sample_rate=sr))
                elif method == "Pseudo-MUSIC":
                    return "music", chart_music_spectrum(run_pseudo_music(iq, n_signals=ns_val, sample_rate=sr, center_freq=fc))
                elif method == "ESPRIT":
                    return "esprit", chart_music_spectrum(run_esprit(iq, n_signals=ns_val, sample_rate=sr, center_freq=fc))
                elif method == "Welch":
                    return "welch", chart_welch_spectrum(run_welch(iq, fft_size=wfft_val, overlap=wovl_val, sample_rate=sr, center_freq=fc))
                elif method == "Correlograma":
                    return "correlogram", chart_correlogram_spectrum(run_correlogram(iq, max_lag=corr_lag, sample_rate=sr, center_freq=fc))
                else:
                    return "aslt", chart_ar_spectrum(run_aslt(iq, sample_rate=sr, center_freq=fc))

            algo_key, b64 = await asyncio.to_thread(_compute)

            if algo_gen[0] != my_gen:
                return

            engine_instance.algo_results[algo_key] = b64
            engine_instance.algo_results["current"] = b64
            engine_instance.algo_results["current_method"] = method
            
            # Update visual components
            img.src = b64
            status_txt.value = f"✓ {method} actualizado"
            status_txt.color = ACCENT_GREEN
            algo_status_txt.value = f"✓ {method}"

            try:
                if img.page: img.update()
                if status_txt.page: status_txt.update()
                if algo_status_txt.page: algo_status_txt.update()
            except: pass
        except NotImplementedError:
            try:
                algo_status_txt.value = "⚠ ASLT: archivos pendientes"
                if algo_status_txt.page: algo_status_txt.update()
            except: pass
        except RuntimeError:
            pass
        except Exception as ex:
            try:
                algo_status_txt.value = f"⚠ ERROR: {str(ex)[:35]}"
                if algo_status_txt.page: algo_status_txt.update()
            except: pass
            print("CRITICAL ALGO ERROR:", ex)
        finally:
            if algo_gen[0] == my_gen:
                algo_running[0] = False
            try:
                if algo_status_txt.page: algo_status_txt.update()
            except: pass

    async def on_algo_refresh(msg):
        if msg != "refresh_charts":
            return
        if not engine_instance.is_playing:
            return
            
        # OPTIMIZACIÓN: Solo ejecutar algoritmos pesados si la pestaña 6 está activa
        if engine_instance.active_tab != 7:
            return

        algo_counter[0] += 1
        if algo_counter[0] % ALGO_EVERY_N == 0:
            await _run_selected_algo()

    page.pubsub.subscribe(on_algo_refresh)

    # Inicializar visibilidad de parámetros
    _update_param_visibility()

    chart_border = ft.Border(
        top=ft.BorderSide(2, "#B380FF"),
        right=ft.BorderSide(1, BORDER_COL),
        bottom=ft.BorderSide(1, BORDER_COL),
        left=ft.BorderSide(1, BORDER_COL),
    )

    chart_container = ft.Container(
        content=img,
        expand=True,
        bgcolor=PANEL_BG,
        border_radius=10,
        border=chart_border,
        padding=8,
    )

    side = panel(
        width=260,
        padding_val=14,
        content=ft.Column([
            ft.Row([method_color_dot, method_name], spacing=8),
            ft.Divider(color=BORDER_COL, height=10),
            ft.Text("Descripción:", color=TEXT_MUTED, size=10),
            method_desc,
            ft.Divider(color=BORDER_COL, height=10),
            ft.Text("Método Avanzado:", color=TEXT_MAIN, size=12),
            method_rg,
            ar_order_row,
            music_ns_row,
            corr_lag_row,
            ft.Divider(color=BORDER_COL, height=10),
            ft.Text("Estado:", color=TEXT_MUTED, size=10),
            status_txt,
            algo_status_txt,
        ], spacing=8, scroll=ft.ScrollMode.AUTO),
    )

    return ft.Container(
        content=ft.Row([chart_container, side], spacing=10, expand=True),
        expand=True,
        padding=ft.Padding(left=14, top=14, right=14, bottom=14),
    )
