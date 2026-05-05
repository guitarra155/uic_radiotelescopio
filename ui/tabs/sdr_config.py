"""
ui/tabs/sdr_config.py
Rediseño total: Tabla de Propiedades (Property Grid).
Se eliminan todos los fallos de layout usando medidas fijas y eliminando la expansión vertical.
"""

import flet as ft
from core.constants import *
from core.dsp_engine import engine_instance

def build_config(page: ft.Page) -> ft.Control:
    
    # --- Estilos Fijos para evitar "Cuadros Grises" ---
    LABEL_WIDTH = 110
    INPUT_WIDTH = 130
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

    def small_field(value, on_submit):
        tf = ft.TextField(
            value=str(value),
            text_size=11,
            height=28,
            content_padding=ft.Padding(8, 0, 8, 0),
            color=TEXT_MAIN,
            bgcolor=DARK_BG,
            border_color=BORDER_COL,
            focused_border_color=ACCENT_CYAN,
            border_radius=4,
            on_submit=on_submit,
            on_blur=on_submit
        )
        return tf

    def small_switch(value, on_change):
        return ft.Switch(value=value, scale=0.8, active_color=ACCENT_GREEN, on_change=on_change)

    # --- Handlers de Configuración ---
    def on_val_change(e, attr, factor=1.0):
        try:
            val = float(e.control.value) * factor
            setattr(engine_instance, attr, val)
            engine_instance.save_config()
            page.pubsub.send_all("refresh_charts")
        except: pass

    def on_toggle(e, attr):
        setattr(engine_instance, attr, e.control.value)
        engine_instance.save_config()
        page.pubsub.send_all("refresh_charts")

    # --- Controles Globales ---
    sw_sync = small_switch(engine_instance.sync_active, None)
    def _sync_t(e):
        engine_instance.apply_sync_mode(e.control.value)
        page.pubsub.send_all("tab_changed")
    sw_sync.on_change = _sync_t

    # --- Diccionario de Pestañas (Diseño de Tabla) ---
    def get_axis_group(title, chart_id):
        cfg = engine_instance.charts_config.get(chart_id, {})
        
        def set_manual(e, axis, key):
            try:
                val = float(e.control.value)
                engine_instance.charts_config[chart_id][key] = val
                engine_instance.charts_config[chart_id][f"auto_{axis}"] = False
                engine_instance.save_config()
                page.pubsub.send_all("tab_changed") # Refrescar UI del panel
            except: pass

        def toggle_auto(e, axis):
            engine_instance.charts_config[chart_id][f"auto_{axis}"] = e.control.value
            engine_instance.save_config()
            page.pubsub.send_all("tab_changed")

        return ft.Column([
            ft.Text(f"📊 {title}", color=ACCENT_CYAN, size=11, weight=ft.FontWeight.BOLD),
            prop_row("Auto Eje X", small_switch(cfg.get("auto_x", True), lambda e: toggle_auto(e, "x"))),
            prop_row("X Mín", small_field(f"{cfg.get('xmin', 0):.2f}", lambda e: set_manual(e, "x", "xmin"))),
            prop_row("X Máx", small_field(f"{cfg.get('xmax', 0):.2f}", lambda e: set_manual(e, "x", "xmax"))),
            prop_row("Auto Eje Y", small_switch(cfg.get("auto_y", True), lambda e: toggle_auto(e, "y"))),
            prop_row("Y Mín", small_field(f"{cfg.get('ymin', 0):.2f}", lambda e: set_manual(e, "y", "ymin"))),
            prop_row("Y Máx", small_field(f"{cfg.get('ymax', 0):.2f}", lambda e: set_manual(e, "y", "ymax"))),
            ft.Divider(height=15, color="#303030")
        ], spacing=2)

    tab_configs = {
        0: ft.Column([ft.Text("🏠 Inicio", color=ACCENT_CYAN, size=12)], spacing=10),
        1: ft.Column([
            prop_row("Modo RAW", small_switch(engine_instance.raw_mode, lambda e: on_toggle(e, "raw_mode"))),
            get_axis_group("Espectro RAW", "mon_raw_spec"),
            get_axis_group("Amplitud RAW", "mon_raw_amp"),
        ]),
        2: ft.Column([
            prop_row("Filtro MA", small_switch(engine_instance.ma_enabled, lambda e: on_toggle(e, "ma_enabled"))),
            prop_row("Ventana (ms)", small_field(engine_instance.moving_avg_window_ms, lambda e: on_val_change(e, "moving_avg_window_ms"))),
            get_axis_group("Espectro Filtrado", "mon_filt_spec"),
            get_axis_group("Amplitud Filtrada", "mon_filt_amp"),
        ]),
        3: ft.Column([
            prop_row("Análisis (s)", small_field(engine_instance.analysis_window_sec, lambda e: on_val_change(e, "analysis_window_sec"))),
            prop_row("Historial (s)", small_field(engine_instance.waterfall_history_sec, lambda e: on_val_change(e, "waterfall_history_sec"))),
            get_axis_group("Cascada", "spec_wf"),
        ]),
        4: ft.Column([get_axis_group("Histograma", "stat_hist")]),
        5: ft.Column([get_axis_group("Potencia", "pow_time")]),
        6: ft.Column([get_axis_group("SNR", "snr_freq")]),
        7: ft.Column([ft.Text("🔬 Algoritmo activo", color=ACCENT_CYAN, size=11)]),
    }

    dynamic_container = ft.Container(content=tab_configs.get(engine_instance.active_tab, tab_configs[0]))

    async def _update_tab(msg):
        if msg == "tab_changed":
            # Re-generar controles para asegurar que reflejen el estado actual (importante para el reset)
            idx = engine_instance.active_tab
            # Nota: para que los valores se actualicen, lo ideal es recrear el objeto o usar refs.
            # Aquí recreamos la vista de la pestaña específica.
            # (En un refactor futuro usaríamos Variables de Estado, pero esto es más seguro para Flet 0.84)
            dynamic_container.content = tab_configs.get(idx, tab_configs[0])
            if dynamic_container.page: dynamic_container.update()

    page.pubsub.subscribe(_update_tab)

    # --- Layout Principal del Panel ---
    return ft.Container(
        width=300,
        bgcolor=PANEL_BG,
        padding=15,
        border=ft.Border(left=ft.BorderSide(1, BORDER_COL)),
        content=ft.Column([
            ft.Text("⚙️ CONFIGURACIÓN", size=14, weight=ft.FontWeight.BOLD, color=ACCENT_CYAN),
            ft.Divider(height=10, color=ACCENT_CYAN),
            prop_row("Sincronización", sw_sync, "Modo Espejo (RAW + FFT)"),
            ft.ElevatedButton("Reset Global", icon=ft.Icons.RESTART_ALT, on_click=lambda e: (engine_instance.reset_to_defaults(), page.pubsub.send_all("tab_changed")),
                             style=ft.ButtonStyle(bgcolor=ft.Colors.RED_900, color=ft.Colors.WHITE, shape=ft.RoundedRectangleBorder(radius=4))),
            ft.Divider(height=20, color=BORDER_COL),
            ft.Container(content=dynamic_container, expand=True)
        ], scroll=ft.ScrollMode.AUTO, spacing=10)
    )
