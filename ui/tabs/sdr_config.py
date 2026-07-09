"""
ui/tabs/sdr_config.py
Versión ULTRA-ESTABLE: Icon-Toggles y Property Grid Dinámico.
Soluciona los cuadros grises usando IconButtons en lugar de Checkboxes/Switches.
"""

import flet as ft
from core.constants import *
from core.dsp_engine import engine_instance

def build_config(page: ft.Page) -> ft.Control:
    
    # Contenedor raíz que se refrescará por completo
    root_container = ft.Container(expand=True)
    focused_fields = set()

    def on_ui_event(e):
        """Cualquier cambio en la UI dispara un refresco total del panel."""
        page.pubsub.send_all("tab_changed")

    LABEL_WIDTH = 95
    INPUT_WIDTH = 120
    ROW_HEIGHT = 35

    def prop_row(label: str, control: ft.Control, tooltip: str = "") -> ft.Row:
        """Crea una fila alineada [Etiqueta | Control] con medidas estrictas."""
        return ft.Row([
            ft.Container(
                content=ft.Text(label, color=TEXT_MUTED, size=10, no_wrap=True),
                width=LABEL_WIDTH,
                alignment=ft.Alignment(-1, 0),
                tooltip=tooltip
            ),
            ft.Container(
                content=control,
                width=INPUT_WIDTH,
                alignment=ft.Alignment(1, 0)
            )
        ], spacing=10, height=ROW_HEIGHT, vertical_alignment=ft.CrossAxisAlignment.CENTER)

    def make_toggle(value, on_click):
        """Usa Iconos en lugar de Checkbox para evitar errores de renderizado."""
        btn = ft.IconButton(
            icon=ft.Icons.CHECK_BOX if value else ft.Icons.CHECK_BOX_OUTLINE_BLANK,
            icon_color=ACCENT_GREEN if value else TEXT_MUTED,
            icon_size=20,
            on_click=on_click,
            visual_density=ft.VisualDensity.COMPACT
        )
        try:
            btn.tab_index = -1
        except:
            pass
        return btn

    def make_input(value, on_submit, input_width=INPUT_WIDTH):
        tf = ft.TextField(
            value=str(value),
            width=input_width,
            height=28,
            text_size=11,
            content_padding=ft.Padding(8, 0, 8, 0),
            color=TEXT_MAIN,
            bgcolor=DARK_BG,
            border_color=BORDER_COL,
            focused_border_color=ACCENT_CYAN,
        )

        def handle_focus(e):
            focused_fields.add(tf)
            engine_instance.any_field_focused = True
            if tf.page:
                tf.update()

        def handle_blur(e):
            focused_fields.discard(tf)
            engine_instance.any_field_focused = len(focused_fields) > 0
            on_submit(e)

        tf.on_focus = handle_focus
        tf.on_blur = handle_blur
        tf.on_submit = on_submit
        return tf

    def row(label, control):
        return ft.Row([
            ft.Text(label, color=TEXT_MUTED, size=11, width=120),
            control
        ], alignment=ft.MainAxisAlignment.START, spacing=10)

    # --- Funciones de construcción dinámica ---
    _live_fields = {}

    def fmt_float(v, max_dec=8):
        try:
            s = f"{float(v):.{max_dec}f}"
            return s.rstrip('0').rstrip('.') if '.' in s else s
        except:
            return str(v)

    def build_axis_group(title, chart_id):
        cfg = engine_instance.charts_config.get(chart_id, {})
        
        def toggle_auto(e, axis):
            cfg[f"auto_{axis}"] = not cfg.get(f"auto_{axis}", True)
            engine_instance.save_config()
            on_ui_event(e)

        def set_val(e, axis, key):
            try:
                val = float(e.control.value)
                cfg[key] = val
                cfg[f"auto_{axis}"] = False
                engine_instance.save_config()
                on_ui_event(e)
            except: pass

        tf_xmin = make_input(fmt_float(cfg.get('xmin', 0)), lambda e: set_val(e, "x", "xmin"))
        tf_xmax = make_input(fmt_float(cfg.get('xmax', 0)), lambda e: set_val(e, "x", "xmax"))
        tf_ymin = make_input(fmt_float(cfg.get('ymin', 0)), lambda e: set_val(e, "y", "ymin"))
        tf_ymax = make_input(fmt_float(cfg.get('ymax', 0)), lambda e: set_val(e, "y", "ymax"))
        
        btn_auto_x = make_toggle(cfg.get("auto_x", True), lambda e: toggle_auto(e, "x"))
        btn_auto_y = make_toggle(cfg.get("auto_y", True), lambda e: toggle_auto(e, "y"))
        
        _live_fields[chart_id] = {
            "xmin": tf_xmin, "xmax": tf_xmax, "ymin": tf_ymin, "ymax": tf_ymax,
            "btn_auto_x": btn_auto_x, "btn_auto_y": btn_auto_y, "cfg_key": chart_id
        }

        return ft.Column([
            ft.Text(f"📊 {title}", color=ACCENT_CYAN, size=12, weight=ft.FontWeight.BOLD),
            row("Auto Eje X", btn_auto_x),
            row("X Mín", tf_xmin),
            row("X Máx", tf_xmax),
            ft.Container(height=5),
            row("Auto Eje Y", btn_auto_y),
            row("Y Mín", tf_ymin),
            row("Y Máx", tf_ymax),
            ft.Divider(height=20, color="#303030")
        ], spacing=2)

    # --- Controles persistentes que se actualizan frecuentemente ---
    rfi_last_val = ft.Text(engine_instance.rfi_last_time, color=TEXT_MAIN, size=10)
    rfi_count_val = ft.Text(f"{engine_instance.rfi_event_count}", color=ACCENT_AMBER, size=10, weight=ft.FontWeight.BOLD)
    main_col = ft.Column(scroll=ft.ScrollMode.AUTO, spacing=10, expand=True)

    def build_dual_axis_group(title, raw_id, filt_id):
        cfg_r = engine_instance.charts_config.get(raw_id, {})
        cfg_f = engine_instance.charts_config.get(filt_id, {})

        def toggle_r(e, axis):
            cfg_r[f"auto_{axis}"] = not cfg_r.get(f"auto_{axis}", True)
            engine_instance.save_config()
            on_ui_event(e)

        def toggle_f(e, axis):
            cfg_f[f"auto_{axis}"] = not cfg_f.get(f"auto_{axis}", True)
            engine_instance.save_config()
            on_ui_event(e)

        def set_r(e, axis, key):
            try:
                cfg_r[key] = float(e.control.value)
                cfg_r[f"auto_{axis}"] = False
                engine_instance.save_config()
                on_ui_event(e)
            except: pass

        def set_f(e, axis, key):
            try:
                cfg_f[key] = float(e.control.value)
                cfg_f[f"auto_{axis}"] = False
                engine_instance.save_config()
                on_ui_event(e)
            except: pass

        w = 80
        tfx_min_r = make_input(fmt_float(cfg_r.get('xmin', 0)), lambda e: set_r(e, "x", "xmin"), w)
        tfx_max_r = make_input(fmt_float(cfg_r.get('xmax', 0)), lambda e: set_r(e, "x", "xmax"), w)
        tfy_min_r = make_input(fmt_float(cfg_r.get('ymin', 0)), lambda e: set_r(e, "y", "ymin"), w)
        tfy_max_r = make_input(fmt_float(cfg_r.get('ymax', 0)), lambda e: set_r(e, "y", "ymax"), w)
        bx_r = make_toggle(cfg_r.get("auto_x", True), lambda e: toggle_r(e, "x"))
        by_r = make_toggle(cfg_r.get("auto_y", True), lambda e: toggle_r(e, "y"))

        tfx_min_f = make_input(fmt_float(cfg_f.get('xmin', 0)), lambda e: set_f(e, "x", "xmin"), w)
        tfx_max_f = make_input(fmt_float(cfg_f.get('xmax', 0)), lambda e: set_f(e, "x", "xmax"), w)
        tfy_min_f = make_input(fmt_float(cfg_f.get('ymin', 0)), lambda e: set_f(e, "y", "ymin"), w)
        tfy_max_f = make_input(fmt_float(cfg_f.get('ymax', 0)), lambda e: set_f(e, "y", "ymax"), w)
        bx_f = make_toggle(cfg_f.get("auto_x", True), lambda e: toggle_f(e, "x"))
        by_f = make_toggle(cfg_f.get("auto_y", True), lambda e: toggle_f(e, "y"))

        _live_fields[raw_id] = {"xmin": tfx_min_r, "xmax": tfx_max_r, "ymin": tfy_min_r, "ymax": tfy_max_r, "btn_auto_x": bx_r, "btn_auto_y": by_r, "cfg_key": raw_id}
        _live_fields[filt_id] = {"xmin": tfx_min_f, "xmax": tfx_max_f, "ymin": tfy_min_f, "ymax": tfy_max_f, "btn_auto_x": bx_f, "btn_auto_y": by_f, "cfg_key": filt_id}

        def triple(label, c1, c2):
            if isinstance(c1, ft.IconButton):
                c1 = ft.Container(c1, width=w, alignment=ft.Alignment(0, 0))
                c2 = ft.Container(c2, width=w, alignment=ft.Alignment(0, 0))
            return ft.Row([ft.Container(ft.Text(label, color=TEXT_MUTED, size=11), width=65), c1, c2], spacing=5, alignment=ft.MainAxisAlignment.START)

        return ft.Column([
            ft.Text(f"📊 {title}", color=ACCENT_CYAN, size=12, weight=ft.FontWeight.BOLD),
            ft.Row([ft.Container(width=65), ft.Container(ft.Text("RAW", color=TEXT_MUTED, size=10, weight="bold"), width=w, alignment=ft.Alignment(0, 0)), ft.Container(ft.Text("FILTRADA", color=TEXT_MUTED, size=10, weight="bold"), width=w, alignment=ft.Alignment(0, 0))], spacing=5),
            triple("Auto Eje X", bx_r, bx_f),
            triple("X Mín", tfx_min_r, tfx_min_f),
            triple("X Máx", tfx_max_r, tfx_max_f),
            ft.Container(height=3),
            triple("Auto Eje Y", by_r, by_f),
            triple("Y Mín", tfy_min_r, tfy_min_f),
            triple("Y Máx", tfy_max_r, tfy_max_f),
            ft.Divider(height=15, color="#303030")
        ], spacing=2)

    def render_panel():
        """Genera la estructura de controles. Solo se llama al cambiar de pestaña."""
        _live_fields.clear()
        idx = engine_instance.active_tab
        
        if idx == 1:
            tab_content = ft.Column([
                ft.Text("🛡️ MONITOREO DUAL", color=ACCENT_CYAN, size=12, weight=ft.FontWeight.BOLD),
                row("Modo RAW", make_toggle(engine_instance.raw_mode, 
                    lambda e: (setattr(engine_instance, "raw_mode", not engine_instance.raw_mode), engine_instance.save_config(), on_ui_event(e)))),
                ft.Divider(height=10, color=BORDER_COL),
                
                build_dual_axis_group("Amplitud", "mon_raw_amp", "mon_filt_amp"),
                
                ft.Text("⚙️ FILTRO MEDIA MÓVIL", color=ACCENT_AMBER, size=11, weight="bold"),
                row("Activado", make_toggle(engine_instance.ma_enabled, 
                    lambda e: (setattr(engine_instance, "ma_enabled", not engine_instance.ma_enabled), engine_instance.save_config(), on_ui_event(e)))),
                row("Ventana (N)", make_input(f"{int(engine_instance.moving_avg_samples)}", 
                    lambda e: (setattr(engine_instance, "moving_avg_samples", max(1, int(float(e.control.value)))), engine_instance.save_config(), on_ui_event(e)), 80)),
                ft.Divider(height=10, color="#303030"),

                build_dual_axis_group("Espectro", "mon_raw_spec", "mon_filt_spec"),
            ])
        elif idx == 2:
            method_map = {
                "waterfall": "spec_wf",
                "cwt": "spec_cwt",
                "ar_burg_2d": "spec_ar",
                "correlogram_2d": "spec_corr"
            }
            active_method = getattr(engine_instance, "active_spec_method", "waterfall")
            cfg_key = method_map.get(active_method, "spec_wf")
            
            cfg_spec = engine_instance.charts_config.get(cfg_key)
            if not cfg_spec:
                cfg_spec = {"xmin": 1419.0, "xmax": 1421.0, "ymin": -100.0, "ymax": -20.0, "auto_x": False, "auto_y": True}
                engine_instance.charts_config[cfg_key] = cfg_spec

            def toggle_auto(e, axis):
                cfg_spec[f"auto_{axis}"] = not cfg_spec.get(f"auto_{axis}", True)
                engine_instance.save_config()
                on_ui_event(e)

            def set_val(e, axis, key):
                try:
                    val = float(e.control.value)
                    cfg_spec[key] = val
                    cfg_spec[f"auto_{axis}"] = False
                    engine_instance.save_config()
                    on_ui_event(e)
                except: pass

            tf_xmin = make_input(f"{cfg_spec.get('xmin', 1419.0):.5f}", lambda e: set_val(e, "x", "xmin"))
            tf_xmax = make_input(f"{cfg_spec.get('xmax', 1421.0):.5f}", lambda e: set_val(e, "x", "xmax"))
            tf_ymin = make_input(f"{cfg_spec.get('ymin', -100.0):.3f}", lambda e: set_val(e, "y", "ymin"))
            tf_ymax = make_input(f"{cfg_spec.get('ymax', -20.0):.3f}", lambda e: set_val(e, "y", "ymax"))
            
            btn_auto_x = make_toggle(cfg_spec.get("auto_x", True), lambda e: toggle_auto(e, "x"))
            btn_auto_y = make_toggle(cfg_spec.get("auto_y", True), lambda e: toggle_auto(e, "y"))
            
            _live_fields[cfg_key] = {
                "xmin": tf_xmin, "xmax": tf_xmax, "ymin": tf_ymin, "ymax": tf_ymax,
                "btn_auto_x": btn_auto_x, "btn_auto_y": btn_auto_y, "cfg_key": cfg_key
            }

            method_name = {"waterfall": "Waterfall FFT", "cwt": "CWT / Morlet", "ar_burg_2d": "AR / Burg", "correlogram_2d": "Correlograma"}.get(active_method, "Espectrograma 2D")

            tab_content = ft.Column([
                ft.Text(f"📊 {method_name}", color=ACCENT_CYAN, size=12, weight=ft.FontWeight.BOLD),
                row("Auto Eje X", btn_auto_x),
                row("X Mín (MHz)", tf_xmin),
                row("X Máx (MHz)", tf_xmax),
                ft.Divider(height=5, color=BORDER_COL),
                row("Auto Color", btn_auto_y),
                row("Color Mín", tf_ymin),
                row("Color Máx", tf_ymax),
            ])
        elif idx == 3: 
            mode = getattr(engine_instance, "histogram_mode", "Magnitud")
            cfg_id = "stat_hist_mag" if mode == "Magnitud" else "stat_hist_fase"
            axis_group = build_axis_group(f"Histograma ({mode})", cfg_id)
            
            # Inicializar variables de configuración si no existen
            if not hasattr(engine_instance, "show_gauss_fit"): engine_instance.show_gauss_fit = True
            if not hasattr(engine_instance, "show_weibull_fit"): engine_instance.show_weibull_fit = True
            if not hasattr(engine_instance, "show_rician_fit"): engine_instance.show_rician_fit = True
            if not hasattr(engine_instance, "show_kde_fit"): engine_instance.show_kde_fit = True

            # Crear toggles para cada curva
            sw_gauss = make_toggle(engine_instance.show_gauss_fit, 
                lambda e: (setattr(engine_instance, "show_gauss_fit", not engine_instance.show_gauss_fit), engine_instance.save_config(), on_ui_event(e)))
            sw_weibull = make_toggle(engine_instance.show_weibull_fit, 
                lambda e: (setattr(engine_instance, "show_weibull_fit", not engine_instance.show_weibull_fit), engine_instance.save_config(), on_ui_event(e)))
            sw_rician = make_toggle(engine_instance.show_rician_fit, 
                lambda e: (setattr(engine_instance, "show_rician_fit", not engine_instance.show_rician_fit), engine_instance.save_config(), on_ui_event(e)))
            sw_kde = make_toggle(engine_instance.show_kde_fit, 
                lambda e: (setattr(engine_instance, "show_kde_fit", not engine_instance.show_kde_fit), engine_instance.save_config(), on_ui_event(e)))

            tab_content = ft.Column([
                ft.Text("📈 AJUSTES DE CURVA", color=ACCENT_CYAN, size=12, weight=ft.FontWeight.BOLD),
                row("Curva Gauss (Térmico)", sw_gauss),
                row("Curva Weibull (RFI)", sw_weibull),
                row("Curva Rician (Señal)", sw_rician),
                row("Curva KDE (Real)", sw_kde),
                ft.Divider(height=10, color=BORDER_COL),
                axis_group
            ])
        elif idx == 4: tab_content = build_axis_group("Potencia", "pow_time")
        elif idx == 5: tab_content = build_axis_group("SNR", "snr_freq")
        elif idx == 6: tab_content = build_axis_group("Algoritmo", "mon_filt_spec")
        else: tab_content = ft.Text("Configuración general activa", color=TEXT_MUTED, size=10)

        if idx == 0:
            main_col.controls = []
        else:
            sync_btn = make_toggle(engine_instance.sync_active, 
                lambda e: (engine_instance.apply_sync_mode(not engine_instance.sync_active), on_ui_event(e)))
            
            reset_btn = ft.ElevatedButton("Reset Global", icon=ft.Icons.RESTART_ALT, 
                on_click=lambda e: (engine_instance.reset_to_defaults(), on_ui_event(e)),
                style=ft.ButtonStyle(bgcolor=ft.Colors.RED_900, color=ft.Colors.WHITE, shape=ft.RoundedRectangleBorder(radius=4)))
            
            try:
                reset_btn.tab_index = -1
            except:
                pass

            main_col.controls = [
                ft.Text("⚙️ CONFIGURACIÓN", size=14, weight=ft.FontWeight.BOLD, color=ACCENT_CYAN),
                ft.Divider(height=10, color=ACCENT_CYAN),
                row("Sincronización", sync_btn),
                reset_btn,
                ft.Divider(height=20, color=BORDER_COL),
                tab_content
            ]

    def update_stats():
        """Solo actualiza los valores de los textos, sin recrear controles."""
        rfi_last_val.value = engine_instance.rfi_last_time
        rfi_count_val.value = f"{engine_instance.rfi_event_count}"
        try:
            if rfi_last_val.page: rfi_last_val.update()
            if rfi_count_val.page: rfi_count_val.update()
        except: pass

    def _sync_auto_fields():
        updated = []
        for chart_id, fields in _live_fields.items():
            actual_key = fields.get("cfg_key", chart_id)
            cfg = engine_instance.charts_config.get(actual_key)
            if not cfg: continue
            
            # Sincronizar toggles visuales (checkboxes)
            btn_x = fields.get("btn_auto_x")
            is_x = cfg.get("auto_x", False)
            if btn_x and btn_x.page:
                new_icon_x = ft.Icons.CHECK_BOX if is_x else ft.Icons.CHECK_BOX_OUTLINE_BLANK
                new_color_x = ACCENT_GREEN if is_x else TEXT_MUTED
                if btn_x.icon != new_icon_x:
                    btn_x.icon = new_icon_x
                    btn_x.icon_color = new_color_x
                    updated.append(btn_x)

            btn_y = fields.get("btn_auto_y")
            is_y = cfg.get("auto_y", False)
            if btn_y and btn_y.page:
                new_icon_y = ft.Icons.CHECK_BOX if is_y else ft.Icons.CHECK_BOX_OUTLINE_BLANK
                new_color_y = ACCENT_GREEN if is_y else TEXT_MUTED
                if btn_y.icon != new_icon_y:
                    btn_y.icon = new_icon_y
                    btn_y.icon_color = new_color_y
                    updated.append(btn_y)

            # Sincronizar textfields SOLO SI auto está activado para ese eje y no tienen foco
            if is_x:
                for key in ["xmin", "xmax"]:
                    tf = fields.get(key)
                    if tf and tf.page and tf not in focused_fields:
                        new_val = fmt_float(cfg.get(key, 0))
                        if tf.value != new_val:
                            tf.value = new_val
                            updated.append(tf)
                            
            if is_y:
                for key in ["ymin", "ymax"]:
                    tf = fields.get(key)
                    if tf and tf.page and tf not in focused_fields:
                        new_val = fmt_float(cfg.get(key, 0))
                        if tf.value != new_val:
                            tf.value = new_val
                            updated.append(tf)
                            
        for tf in updated:
            try: tf.update()
            except: pass


    # --- Suscripción a eventos ---
    async def _update_ui(msg):
        if msg == "tab_changed":
            render_panel()
            try: main_col.update()
            except: pass
            
            # Actualizar estilos del wrapper dinámicamente
            try:
                idx = engine_instance.active_tab
                wrapper.bgcolor = PANEL_BG if idx != 0 else ft.Colors.TRANSPARENT
                wrapper.padding = ft.Padding(left=10, top=15, right=25, bottom=15) if idx != 0 else 5
                wrapper.update()
            except: pass

        elif msg == "refresh_charts":
            if engine_instance.active_tab == 1:
                update_stats()
            _sync_auto_fields()
            
        elif msg == "toggle_config_collapse":
            is_collapsed[0] = not is_collapsed[0]
            wrapper.visible = not is_collapsed[0]
            collapse_btn.icon = ft.Icons.KEYBOARD_ARROW_LEFT if is_collapsed[0] else ft.Icons.KEYBOARD_ARROW_RIGHT
            engine_instance.is_config_collapsed = is_collapsed[0]
            try: wrapper.update()
            except: pass
            try: collapse_btn.update()
            except: pass
            page.pubsub.send_all("refresh_charts")

        elif msg == "force_collapse":
            if not is_collapsed[0]:
                is_collapsed[0] = True
                wrapper.visible = False
                collapse_btn.icon = ft.Icons.KEYBOARD_ARROW_LEFT
                engine_instance.is_config_collapsed = True
                try: wrapper.update()
                except: pass
                try: collapse_btn.update()
                except: pass

    page.pubsub.subscribe(_update_ui)
    
    render_panel()
    root_container.content = main_col
    
    wrapper = ft.Container(
        content=root_container,
        width=300,
        bgcolor=PANEL_BG,
        border=ft.Border(left=ft.BorderSide(1, BORDER_COL)),
        padding=ft.Padding(left=10, top=15, right=20, bottom=15),
        alignment=ft.Alignment(-1.0, -1.0),
    )
    
    is_collapsed = [False]
    
    def toggle_collapse(e):
        is_collapsed[0] = not is_collapsed[0]
        wrapper.visible = not is_collapsed[0]
        collapse_btn.icon = ft.Icons.KEYBOARD_ARROW_LEFT if is_collapsed[0] else ft.Icons.KEYBOARD_ARROW_RIGHT
        engine_instance.is_config_collapsed = is_collapsed[0]
        e.control.page.pubsub.send_all("refresh_charts")
        e.control.page.update()

    collapse_btn = ft.IconButton(
        icon=ft.Icons.KEYBOARD_ARROW_RIGHT,
        icon_color=ACCENT_CYAN,
        icon_size=20,
        on_click=toggle_collapse,
        tooltip="Minimizar/Expandir Panel",
        padding=0,
        width=24,
    )
    
    collapsed_col = ft.Column([
        ft.Container(
            content=collapse_btn,
            alignment=ft.alignment.Alignment(-1.0, -1.0)
        )
    ], width=24, alignment=ft.MainAxisAlignment.START)
    
    final_row = ft.Row([
        collapsed_col,
        wrapper
    ], spacing=0, vertical_alignment=ft.CrossAxisAlignment.START)
    
    # Re-asignar para poder actualizarlo desde _update_ui
    page.pubsub.subscribe(lambda msg: wrapper.update() if msg == "tab_changed" else None)
    
    return final_row
