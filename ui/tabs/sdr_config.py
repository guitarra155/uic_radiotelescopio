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

    def on_ui_event(e):
        """Cualquier cambio en la UI dispara un refresco total del panel."""
        page.pubsub.send_all("tab_changed")

    LABEL_WIDTH = 100
    INPUT_WIDTH = 145
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

    def make_input(value, on_submit):
        return ft.TextField(
            value=str(value),
            width=INPUT_WIDTH,
            height=28,
            text_size=11,
            content_padding=ft.Padding(8, 0, 8, 0),
            color=TEXT_MAIN,
            bgcolor=DARK_BG,
            border_color=BORDER_COL,
            focused_border_color=ACCENT_CYAN,
            on_submit=on_submit,
            on_blur=on_submit
        )

    def row(label, control):
        return ft.Row([
            ft.Text(label, color=TEXT_MUTED, size=11, width=120),
            control
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

    # --- Funciones de construcción dinámica ---
    _live_fields = {}

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

        tf_xmin = make_input(f"{cfg.get('xmin', 0):.8f}", lambda e: set_val(e, "x", "xmin"))
        tf_xmax = make_input(f"{cfg.get('xmax', 0):.8f}", lambda e: set_val(e, "x", "xmax"))
        tf_ymin = make_input(f"{cfg.get('ymin', 0):.8f}", lambda e: set_val(e, "y", "ymin"))
        tf_ymax = make_input(f"{cfg.get('ymax', 0):.8f}", lambda e: set_val(e, "y", "ymax"))
        
        _live_fields[chart_id] = {"xmin": tf_xmin, "xmax": tf_xmax, "ymin": tf_ymin, "ymax": tf_ymax, "cfg_key": chart_id}

        return ft.Column([
            ft.Text(f"📊 {title}", color=ACCENT_CYAN, size=12, weight=ft.FontWeight.BOLD),
            row("Auto Eje X", make_toggle(cfg.get("auto_x"), lambda e: toggle_auto(e, "x"))),
            row("X Mín", tf_xmin),
            row("X Máx", tf_xmax),
            ft.Container(height=5),
            row("Auto Eje Y", make_toggle(cfg.get("auto_y"), lambda e: toggle_auto(e, "y"))),
            row("Y Mín", tf_ymin),
            row("Y Máx", tf_ymax),
            ft.Divider(height=20, color="#303030")
        ], spacing=2)

    # --- Controles persistentes que se actualizan frecuentemente ---
    rfi_last_val = ft.Text(engine_instance.rfi_last_time, color=TEXT_MAIN, size=10)
    rfi_count_val = ft.Text(f"{engine_instance.rfi_event_count}", color=ACCENT_AMBER, size=10, weight=ft.FontWeight.BOLD)

    # Columna principal persistente para mantener el scroll y el foco de los inputs
    main_col = ft.Column(scroll=ft.ScrollMode.AUTO, spacing=10, expand=True)

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
                build_axis_group("Espectro RAW", "mon_raw_spec"),
                build_axis_group("Amplitud RAW", "mon_raw_amp"),
                ft.Divider(height=20, color=ACCENT_AMBER),
                row("Filtro MA", make_toggle(engine_instance.ma_enabled, 
                    lambda e: (setattr(engine_instance, "ma_enabled", not engine_instance.ma_enabled), engine_instance.save_config(), on_ui_event(e)))),
                row("Ventana (muestras)", make_input(f"{int(engine_instance.moving_avg_samples)}", 
                    lambda e: (setattr(engine_instance, "moving_avg_samples", max(1, int(float(e.control.value)))), engine_instance.save_config(), on_ui_event(e)))),
                build_axis_group("Espectro Filtrado", "mon_filt_spec"),
                build_axis_group("Amplitud Filtrada", "mon_filt_amp"),
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
            
            _live_fields[cfg_key] = {"xmin": tf_xmin, "xmax": tf_xmax, "ymin": tf_ymin, "ymax": tf_ymax, "cfg_key": cfg_key}

            method_name = {"waterfall": "Waterfall FFT", "cwt": "CWT / Morlet", "ar_burg_2d": "AR / Burg 2D", "correlogram_2d": "Correlograma 2D"}.get(active_method, "Espectrograma 2D")

            tab_content = ft.Column([
                ft.Text(f"📊 {method_name}", color=ACCENT_CYAN, size=12, weight=ft.FontWeight.BOLD),
                row("Auto Eje X", make_toggle(cfg_spec.get("auto_x", True), lambda e: toggle_auto(e, "x"))),
                row("X Mín (MHz)", tf_xmin),
                row("X Máx (MHz)", tf_xmax),
                ft.Divider(height=5, color=BORDER_COL),
                row("Auto Color", make_toggle(cfg_spec.get("auto_y", True), lambda e: toggle_auto(e, "y"))),
                row("Color Mín", tf_ymin),
                row("Color Máx", tf_ymax),
            ])
        elif idx == 3: tab_content = build_axis_group("Histograma", "stat_hist")
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
            pairs = [
                ("xmin", cfg.get("auto_x", False), f"{cfg.get('xmin', 0):.5f}"),
                ("xmax", cfg.get("auto_x", False), f"{cfg.get('xmax', 0):.5f}"),
                ("ymin", cfg.get("auto_y", False), f"{cfg.get('ymin', 0):.5f}"),
                ("ymax", cfg.get("auto_y", False), f"{cfg.get('ymax', 0):.5f}"),
            ]
            for key, is_auto, new_val in pairs:
                tf = fields.get(key)
                if tf and is_auto and tf.page:
                    try:
                        if tf.value != new_val:
                            tf.value = new_val
                            updated.append(tf)
                    except: pass
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
                wrapper.padding = 15 if idx != 0 else 5
                wrapper.update()
            except: pass

        elif msg == "refresh_charts":
            if engine_instance.active_tab == 1:
                update_stats()
            _sync_auto_fields()

    page.pubsub.subscribe(_update_ui)
    
    render_panel()
    root_container.content = main_col
    
    wrapper = ft.Container(
        content=root_container,
        width=300,
        bgcolor=PANEL_BG if engine_instance.active_tab != 0 else ft.Colors.TRANSPARENT,
        padding=15 if engine_instance.active_tab != 0 else 5,
    )
    
    is_collapsed = [False]
    
    def toggle_collapse(e):
        is_collapsed[0] = not is_collapsed[0]
        wrapper.visible = not is_collapsed[0]
        collapse_btn.icon = ft.Icons.KEYBOARD_ARROW_RIGHT if is_collapsed[0] else ft.Icons.KEYBOARD_ARROW_LEFT
        e.control.page.update()

    collapse_btn = ft.IconButton(
        icon=ft.Icons.KEYBOARD_ARROW_LEFT,
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
