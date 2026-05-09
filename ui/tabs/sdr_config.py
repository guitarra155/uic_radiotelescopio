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
        return ft.IconButton(
            icon=ft.Icons.CHECK_BOX if value else ft.Icons.CHECK_BOX_OUTLINE_BLANK,
            icon_color=ACCENT_GREEN if value else TEXT_MUTED,
            icon_size=20,
            on_click=on_click,
            visual_density=ft.VisualDensity.COMPACT
        )

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
                cfg[f"auto_{axis}"] = False # Desactivar auto al escribir
                engine_instance.save_config()
                on_ui_event(e)
            except: pass

        return ft.Column([
            ft.Text(f"📊 {title}", color=ACCENT_CYAN, size=12, weight=ft.FontWeight.BOLD),
            row("Auto Eje X", make_toggle(cfg.get("auto_x"), lambda e: toggle_auto(e, "x"))),
            row("X Mín", make_input(f"{cfg.get('xmin', 0):.8f}", lambda e: set_val(e, "x", "xmin"))),
            row("X Máx", make_input(f"{cfg.get('xmax', 0):.8f}", lambda e: set_val(e, "x", "xmax"))),
            ft.Container(height=5),
            row("Auto Eje Y", make_toggle(cfg.get("auto_y"), lambda e: toggle_auto(e, "y"))),
            row("Y Mín", make_input(f"{cfg.get('ymin', 0):.8f}", lambda e: set_val(e, "y", "ymin"))),
            row("Y Máx", make_input(f"{cfg.get('ymax', 0):.8f}", lambda e: set_val(e, "y", "ymax"))),
            ft.Divider(height=20, color="#303030")
        ], spacing=2)

    # Columna principal persistente para mantener el scroll
    main_col = ft.Column(scroll=ft.ScrollMode.AUTO, spacing=10)

    def render_panel():
        """Genera los controles basados en el estado actual del motor."""
        idx = engine_instance.active_tab
        
        # Pestaña actual
        if idx == 1:
            tab_content = ft.Column([
                row("Modo RAW", make_toggle(engine_instance.raw_mode, 
                    lambda e: (setattr(engine_instance, "raw_mode", not engine_instance.raw_mode), engine_instance.save_config(), on_ui_event(e)))),
                build_axis_group("Espectro RAW", "mon_raw_spec"),
                build_axis_group("Amplitud RAW", "mon_raw_amp"),
            ])
        elif idx == 2:
            tab_content = ft.Column([
                row("Filtro MA", make_toggle(engine_instance.ma_enabled, 
                    lambda e: (setattr(engine_instance, "ma_enabled", not engine_instance.ma_enabled), engine_instance.save_config(), on_ui_event(e)))),
                row("Ventana (muestras)", make_input(f"{int(engine_instance.moving_avg_samples)}", 
                    lambda e: (setattr(engine_instance, "moving_avg_samples", max(1, int(float(e.control.value)))), engine_instance.save_config(), on_ui_event(e)))),
                build_axis_group("Espectro Filtrado", "mon_filt_spec"),
                build_axis_group("Amplitud Filtrada", "mon_filt_amp"),
            ])
        elif idx == 3:
            tab_content = ft.Column([
                row("Análisis (s)", make_input(f"{engine_instance.analysis_window_sec:.8f}", 
                    lambda e: (setattr(engine_instance, "analysis_window_sec", float(e.control.value)), engine_instance.save_config(), on_ui_event(e)))),
                row("Historial (s)", make_input(f"{engine_instance.waterfall_history_sec:.8f}", 
                    lambda e: (setattr(engine_instance, "waterfall_history_sec", float(e.control.value)), engine_instance.save_config(), on_ui_event(e)))),
                build_axis_group("Cascada", "spec_wf"),
            ])
        elif idx == 4: tab_content = build_axis_group("Histograma", "stat_hist")
        elif idx == 5: tab_content = build_axis_group("Potencia", "pow_time")
        elif idx == 6: tab_content = build_axis_group("SNR", "snr_freq")
        else: tab_content = ft.Text("Configuración general activa", color=TEXT_MUTED, size=10)

        # Actualizar la lista de controles de la columna persistente
        main_col.controls = [
            ft.Text("⚙️ CONFIGURACIÓN", size=14, weight=ft.FontWeight.BOLD, color=ACCENT_CYAN),
            ft.Divider(height=10, color=ACCENT_CYAN),
            
            row("Sincronización", make_toggle(engine_instance.sync_active, 
                lambda e: (engine_instance.apply_sync_mode(not engine_instance.sync_active), on_ui_event(e)))),
            
            ft.ElevatedButton("Reset Global", icon=ft.Icons.RESTART_ALT, 
                on_click=lambda e: (engine_instance.reset_to_defaults(), on_ui_event(e)),
                style=ft.ButtonStyle(bgcolor=ft.Colors.RED_900, color=ft.Colors.WHITE, shape=ft.RoundedRectangleBorder(radius=4))),
            
            ft.Divider(height=20, color=BORDER_COL),
            tab_content
        ]

    # --- Suscripción a eventos ---
    async def _update_tab(msg):
        if msg == "tab_changed":
            render_panel()
            main_col.update()

    page.pubsub.subscribe(_update_tab)
    
    # Carga inicial
    render_panel()
    root_container.content = main_col
    
    return ft.Container(
        content=root_container,
        width=300,
        bgcolor=PANEL_BG,
        padding=15,
        border=ft.Border(left=ft.BorderSide(1, BORDER_COL))
    )
