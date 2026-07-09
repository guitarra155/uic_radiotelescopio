import sys
if sys.platform.startswith("win"):
    try:
        import io
        if hasattr(sys.stdout, "buffer"):
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
        if hasattr(sys.stderr, "buffer"):
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")
    except Exception:
        pass

import flet as ft

from core.constants import *
from ui.components.layout import build_header, build_footer
from ui.tabs.dual_monitoring import build_dual_monitoring
from ui.tabs.spectrogram import build_spectrogram
from ui.tabs.statistics import build_statistics
from ui.tabs.sdr_config import build_config
from ui.tabs.signal_analysis import build_signal_analysis
from ui.tabs.freq_snr import build_freq_snr
from ui.tabs.estado import build_estado

def main(page: ft.Page):
    from core.dsp_engine import engine_instance
    engine_instance.load_config()

    # key_state: diccionario compartido con todos los tabs para detectar Ctrl/Shift en scroll.
    # page.on_keyboard_event entrega KeyboardEvent con .ctrl/.shift actualizados en cada keydown.
    # Para detectar el RELEASE de Ctrl/Shift: e.ctrl/e.shift ya vienen en False cuando
    # se pulsa cualquier otra tecla sin el modificador. Adicionalmente, detectamos las
    # teclas "Control"/"Shift" directamente para forzar el reset inmediato.
    key_state = {'ctrl': False, 'shift': False}

    def on_keyboard(e: ft.KeyboardEvent):
        if e.key in {"Control", "ControlLeft", "ControlRight"} or e.ctrl:
            key_state['ctrl'] = True
        else:
            key_state['ctrl'] = False
            
        if e.key in {"Shift", "ShiftLeft", "ShiftRight"} or e.shift:
            key_state['shift'] = True
        else:
            key_state['shift'] = False

        if e.key == "F5":
            page.pubsub.send_all("toggle_stream")
        elif e.key == "F8":
            page.pubsub.send_all("emergency_stop")
        elif e.key == "F11":
            page.window.full_screen = not page.window.full_screen
            page.update()
        elif e.key in {"ArrowLeft", "Left", ","} and engine_instance.is_paused and not getattr(engine_instance, "any_field_focused", False):
            engine_instance.seek_frames(1)
            engine_instance.data_ready = True
            engine_instance._seek_refresh = True
            page.pubsub.send_all("refresh_charts_all")
            page.pubsub.send_all("update_frame_label")
        elif e.key in {"ArrowRight", "Right", "."} and engine_instance.is_paused and not getattr(engine_instance, "any_field_focused", False):
            engine_instance.seek_frames(-1)
            engine_instance.data_ready = True
            engine_instance._seek_refresh = True
            page.pubsub.send_all("refresh_charts_all")
            page.pubsub.send_all("update_frame_label")
        elif e.ctrl and e.key in {"F1", "F2", "F3", "F4"}:
            idx = int(e.key[1]) - 1
            page.pubsub.send_all(("maximize_dual_chart", idx))
        elif e.key in {"F1", "F2", "F3", "F4"} and not e.ctrl and not e.shift:
            idx = int(e.key[1]) - 1
            page.pubsub.send_all(("select_dual_chart", idx))
        if e.ctrl and e.shift:
            if e.key == "Tab":
                prev_idx = (engine_instance.active_tab - 1) % len(tab_labels)
                switch_to_tab(prev_idx)
            elif e.key.upper() == "B":
                page.pubsub.send_all("toggle_config_collapse")
            elif e.key.upper() == "S":
                _toggle_sidebar()
            else:
                k = e.key
                if k.startswith("Numpad "):
                    k = k.replace("Numpad ", "")
                if k in ["1", "2", "3", "4", "5", "6"]:
                    idx = int(k) - 1
                    page.pubsub.send_all(("toggle_tab_panel", idx))
        elif e.ctrl:
            if e.key == "Tab":
                next_idx = (engine_instance.active_tab + 1) % len(tab_labels)
                switch_to_tab(next_idx)
            elif e.key.upper() == "B":
                page.pubsub.send_all(("toggle_tab_panel", engine_instance.active_tab))
            else:
                k = e.key
                if k.startswith("Numpad "):
                    k = k.replace("Numpad ", "")
                if k in ["1", "2", "3", "4", "5", "6"]:
                    idx = int(k) - 1
                    switch_to_tab(idx)
    page.on_keyboard_event = on_keyboard

    # Configuración de Ventana


    page.title      = "Plataforma DSP"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor    = DARK_BG
    # Leer configuración guardada de ventana
    saved_res = getattr(engine_instance, "window_res", "Auto-Detect (Pantalla Actual)")
    saved_mode = getattr(engine_instance, "window_mode", "Normal")

    if saved_res and saved_res != "Auto-Detect (Pantalla Actual)":
        try:
            parts = saved_res.split("x")
            page.window.width = int(parts[0])
            page.window.height = int(parts[1])
        except:
            page.window.width = 1920
            page.window.height = 1080
    elif saved_res == "Auto-Detect (Pantalla Actual)":
        try:
            import tkinter as tk
            root = tk.Tk()
            page.window.width = root.winfo_screenwidth()
            page.window.height = root.winfo_screenheight()
            root.destroy()
        except:
            page.window.width = 1920
            page.window.height = 1080
    else:
        page.window.width = 1920    
        page.window.height = 1080
        
    if saved_mode == "Pantalla Completa":
        page.window.full_screen = True
    elif saved_mode == "Maximizada":
        page.window.maximized = True
    page.window.min_width = 900
    page.window.min_height= 620
    page.padding = 0
    page.spacing = 0
    page.theme   = ft.Theme(color_scheme_seed=ACCENT_CYAN, use_material3=True)

    # Capturar y sincronizar las dimensions de la ventana con el renderizador de gráficas
    def on_page_resize(e):
        engine_instance.window_width = page.width
        engine_instance.window_height = page.height
        # Avisar a todos que los charts deben recalcular su escala base
        page.pubsub.send_all("refresh_charts")
    page.on_resized = on_page_resize  # Flet event is on_resized, not on_resize!
    engine_instance.window_width = page.width or 1280
    engine_instance.window_height = page.height or 720

    # Components de Layout Base
    header = build_header(page)
    footer = build_footer()

    tab_labels = [
        ("🏠", "Inicio & Configuración"),     # 0
        ("🌓", "Señal y Señal Filtrada"),      # 1
        ("🌈", "Espectrograma"),               # 2
        ("📊", "Histograma"),                  # 3
        ("⚡", "Potencia vs. Tiempo"),          # 4
        ("📶", "SNR vs. Frecuencia"),           # 5
    ]

    # Renderizamos los components visuals de cada módulo
    tab_contents = [
        build_estado(page),                          # 0
        build_dual_monitoring(page, key_state),      # 1
        build_spectrogram(page, key_state),          # 2
        build_statistics(page, key_state),           # 3
        build_signal_analysis(page, key_state),      # 4
        build_freq_snr(page, key_state),             # 5
    ]

    selected = [0]   # índice activo
    sidebar_expanded = [False]  # Empieza colapsada
    sidebar_pinned = [False]    # True = usuario la fijó manualmente abierta
    SIDEBAR_W_EXPANDED = 190
    SIDEBAR_W_COLLAPSED = 52

    def switch_to_tab(idx):
        if idx < 0 or idx >= len(tab_labels):
            return
        if not sidebar_items or len(sidebar_items) <= selected[0]:
            return
        # Deseleccionar anterior
        _set_item_state(selected[0], active=False)
        selected[0] = idx
        from core.dsp_engine import engine_instance
        engine_instance.active_tab = idx
        tab_body.content = tab_contents[idx]
        right_panel.visible = (idx != 0)
        _set_item_state(idx, active=True)
        # Sincronizar topbar si está visible
        _tb_set_active(idx)
        page.pubsub.send_all("tab_changed")
        page.update()

    def _set_item_state(idx, active):
        """Actualiza colores e indicador visual del ítem de sidebar."""
        item = sidebar_items[idx]
        icon_ctrl = item.content.controls[0]   # Text emoji
        label_ctrl = item.content.controls[1]  # Text label
        if active:
            icon_ctrl.color = ACCENT_CYAN
            label_ctrl.color = TEXT_MAIN
            item.bgcolor = "#0D2137"          # Fondo azul profundo
            item.border = ft.Border(
                left=ft.BorderSide(4, ACCENT_CYAN)
            )
        else:
            icon_ctrl.color = TEXT_MUTED
            label_ctrl.color = TEXT_MUTED
            item.bgcolor = "transparent"
            item.border = ft.Border(
                left=ft.BorderSide(3, "transparent")
            )

    sidebar_items = []

    def make_sidebar_item(i, icon, label):
        is_active = (i == 0)
        icon_ctrl = ft.Text(
            icon, size=20,
            color=ACCENT_CYAN if is_active else TEXT_MUTED,
        )
        label_ctrl = ft.Text(
            label, size=12,
            color=ACCENT_CYAN if is_active else TEXT_MUTED,
            weight=ft.FontWeight.W_500,
            no_wrap=True,
            overflow=ft.TextOverflow.ELLIPSIS,
        )
        row = ft.Row(
            [icon_ctrl, label_ctrl],
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )
        item = ft.Container(
            content=row,
            padding=ft.Padding(left=12, right=8, top=10, bottom=10),
            border_radius=8,
            ink=True,
            bgcolor="#1C2333" if is_active else "transparent",
            tooltip=label,
            border=ft.Border(
                left=ft.BorderSide(3, ACCENT_CYAN if is_active else "transparent")
            ),
        )
        item.on_click = lambda e, idx=i: switch_to_tab(idx)
        return item, icon_ctrl, label_ctrl

    sidebar_items = []
    _icon_ctrls = []
    _label_ctrls = []
    for i, (icon, label) in enumerate(tab_labels):
        item, ic, lc = make_sidebar_item(i, icon, label)
        sidebar_items.append(item)
        _icon_ctrls.append(ic)
        _label_ctrls.append(lc)

    # Inicializar con sidebar colapsada: ocultar labels
    for lc in _label_ctrls:
        lc.visible = False

    # Botón de toggle (colapsar / expandir)
    toggle_icon = ft.Text("◀", size=14, color=TEXT_MUTED)
    toggle_btn = ft.Container(
        content=ft.Row(
            [toggle_icon],
            alignment=ft.MainAxisAlignment.CENTER,
        ),
        on_click=lambda e: _toggle_sidebar(),
        ink=True,
        border_radius=6,
        padding=ft.Padding(left=4, right=4, top=6, bottom=6),
        tooltip="Colapsar barra lateral",
    )

    def _expand_sidebar():
        sidebar_expanded[0] = True
        sidebar_col.width = SIDEBAR_W_EXPANDED
        toggle_icon.value = "◀"
        toggle_btn.tooltip = "Fijar / Colapsar"
        for lc in _label_ctrls:
            lc.visible = True
        if sidebar_col.page:
            sidebar_col.update()

    def _collapse_sidebar():
        sidebar_expanded[0] = False
        sidebar_col.width = SIDEBAR_W_COLLAPSED
        toggle_icon.value = "▶"
        toggle_btn.tooltip = "Expandir barra lateral"
        for lc in _label_ctrls:
            lc.visible = False
        if sidebar_col.page:
            sidebar_col.update()

    def _toggle_sidebar():
        """Toggle manual (teclado o botón pin)."""
        sidebar_pinned[0] = not sidebar_pinned[0]
        if sidebar_pinned[0]:
            _expand_sidebar()
        else:
            _collapse_sidebar()

    def _on_sidebar_hover(e):
        """Auto-expand al entrar, auto-colapsa al salir (si no está fijada)."""
        if sidebar_pinned[0]:
            return
        if e.data == "true":   # mouse entró
            _expand_sidebar()
        else:                  # mouse salió
            _collapse_sidebar()

    # Botón para alternar modo de navegación (parte inferior del sidebar)
    nav_mode_icon = ft.Icon(ft.Icons.GRID_VIEW, color=TEXT_MUTED, size=18)
    nav_mode_label = ft.Text("Modo Superior", size=11, color=TEXT_MUTED, visible=False)
    nav_mode_btn = ft.Container(
        content=ft.Row(
            [nav_mode_icon, nav_mode_label],
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.Padding(left=12, right=8, top=8, bottom=8),
        ink=True, border_radius=8,
        tooltip="Cambiar a barra superior horizontal",
        on_click=lambda e: _toggle_nav_mode(),
    )

    def _toggle_nav_mode():
        if nav_mode[0] == "sidebar":
            nav_mode[0] = "topbar"
            sidebar_col.visible = False
            topbar_row.visible = True
            nav_mode_icon.name = ft.Icons.VIEW_SIDEBAR
            nav_mode_label.value = "Modo Lateral"
            nav_mode_btn.tooltip = "Cambiar a barra lateral vertical"
        else:
            nav_mode[0] = "sidebar"
            sidebar_col.visible = True
            topbar_row.visible = False
            nav_mode_icon.name = ft.Icons.GRID_VIEW
            nav_mode_label.value = "Modo Superior"
            nav_mode_btn.tooltip = "Cambiar a barra superior horizontal"
        page.update()

    sidebar_col = ft.Container(
        width=SIDEBAR_W_COLLAPSED,
        bgcolor=PANEL_BG,
        border=ft.Border(right=ft.BorderSide(1, BORDER_COL)),
        on_hover=_on_sidebar_hover,
        animate=ft.Animation(180, ft.AnimationCurve.EASE_IN_OUT),
        content=ft.Column(
            [
                ft.Container(
                    content=ft.Row(
                        [toggle_btn],
                        alignment=ft.MainAxisAlignment.CENTER,
                    ),
                    padding=ft.Padding(left=4, right=8, top=6, bottom=2),
                ),
                ft.Divider(height=1, color=BORDER_COL),
                ft.Column(
                    sidebar_items,
                    spacing=2,
                    expand=True,
                    scroll=ft.ScrollMode.AUTO,
                ),
                ft.Divider(height=1, color=BORDER_COL),
                nav_mode_btn,
            ],
            spacing=0,
            expand=True,
        ),
    )

    tab_body = ft.AnimatedSwitcher(
        content=tab_contents[0],
        transition=ft.AnimatedSwitcherTransition.FADE,
        duration=200,
        switch_in_curve=ft.AnimationCurve.EASE_OUT,
        expand=True
    )

    import asyncio

    # ── Modo de navegación: "sidebar" | "topbar" ───────────────────────────
    nav_mode = ["sidebar"]

    # ── Barra horizontal clásica (Top-bar) ─────────────────────────────────
    tb_indicators = [
        ft.Container(height=2, bgcolor=ACCENT_CYAN if i == 0 else "transparent", border_radius=1)
        for i in range(len(tab_labels))
    ]
    tb_btns = []

    def _make_tb_btn(i, icon, label):
        lbl = ft.Text(
            f"{icon}  {label}",
            color=ACCENT_CYAN if i == 0 else TEXT_MUTED,
            size=13,
        )
        btn = ft.Container(
            content=lbl,
            padding=ft.Padding(left=14, right=14, top=5, bottom=5),
            ink=True, border_radius=4, bgcolor="transparent",
        )
        btn.on_click = lambda e, idx=i: switch_to_tab(idx)
        return btn, lbl

    tb_btns = []
    _tb_lbls = []
    for i, (icon, label) in enumerate(tab_labels):
        b, l = _make_tb_btn(i, icon, label)
        tb_btns.append(b)
        _tb_lbls.append(l)

    def _tb_set_active(idx):
        for j, (b, ind) in enumerate(zip(tb_btns, tb_indicators)):
            active = (j == idx)
            _tb_lbls[j].color = ACCENT_CYAN if active else TEXT_MUTED
            ind.bgcolor = ACCENT_CYAN if active else "transparent"

    topbar_row = ft.Container(
        bgcolor=PANEL_BG,
        border=ft.Border(bottom=ft.BorderSide(1, BORDER_COL)),
        height=40,
        visible=False,
        padding=ft.Padding(left=10, right=10, top=0, bottom=0),
        content=ft.Row(
            [
                ft.Row(
                    [ft.Column([btn, ind], spacing=0) for btn, ind in zip(tb_btns, tb_indicators)],
                    spacing=4,
                    scroll=ft.ScrollMode.AUTO,
                    expand=True,
                ),
                ft.IconButton(
                    icon=ft.Icons.VIEW_SIDEBAR,
                    icon_color=TEXT_MUTED,
                    icon_size=18,
                    tooltip="Cambiar a barra lateral vertical",
                    on_click=lambda e: _toggle_nav_mode(),
                )
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )

    # Panel Izquierdo (Contenido de la pestaña, toma el espacio sobrante)
    left_panel_content = ft.Container(
        content=tab_body,
        expand=True,
        padding=ft.Padding(top=5, left=0, right=0, bottom=0)
    )

    # Panel Derecho: Configuración Fija (ancho dinámico)
    right_panel = ft.Container(
        content=build_config(page),
        border=ft.Border(left=ft.BorderSide(1, BORDER_COL)),
        bgcolor=DARK_BG,
        expand=False,
        visible=False
    )

    lower_split = ft.Row(
        [sidebar_col, left_panel_content, right_panel],
        expand=True, spacing=0,
        vertical_alignment=ft.CrossAxisAlignment.STRETCH
    )

    main_view = ft.Column(
        [topbar_row, lower_split],
        expand=True, spacing=0,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH
    )

    # ── Manejo de Reset de Configuración y Fullscreen ───────────────────────
    def on_main_pubsub(msg):
        if msg == "config_reset":
            right_panel.content = build_config(page)
            page.update()
        elif msg == "toggle_fullscreen_chart":
            is_fs = getattr(engine_instance, "chart_fullscreen_active", False)
            header.visible = not is_fs
            footer.visible = not is_fs
            if nav_mode[0] == "sidebar":
                sidebar_col.visible = not is_fs
            else:
                topbar_row.visible = not is_fs
            
            if is_fs:
                page.pubsub.send_all("force_collapse")
                
            right_panel.visible = (engine_instance.active_tab != 0)
            
            page.update()
            page.pubsub.send_all("refresh_charts")
            
    page.pubsub.subscribe(on_main_pubsub)

    # ── Tarea de Refresco de Interfaz ──────────────
    async def refresh_loop():
        was_playing = False
        while True:
            is_p = engine_instance.is_playing
            try:
                # El motor detectó metadatos nuevos (ej: sintonía automática)
                if getattr(engine_instance, "metadata_updated", False):
                    engine_instance.metadata_updated = False
                    page.pubsub.send_all("refresh_charts")

                if is_p and getattr(engine_instance, "data_ready", False):
                    # Solo despachar refresh si hay una pestaña activa con gráficas (no tab 0)
                    engine_instance.data_ready = False
                    if engine_instance.active_tab != 0:
                        page.pubsub.send_all("refresh_charts")
                elif getattr(engine_instance, "_seek_refresh", False):
                    # Seek manual en pausa: refrescar la pestaña activa independientemente
                    engine_instance._seek_refresh = False
                    if engine_instance.active_tab != 0:
                        page.pubsub.send_all("refresh_charts")
                elif was_playing and not is_p:
                    if not getattr(engine_instance, "is_paused", False):
                        page.pubsub.send_all("stream_stopped")
            except RuntimeError:
                break

            was_playing = is_p
            await asyncio.sleep(0.05)  # Chequeo rápido del flag
            
    page.run_task(refresh_loop)

    # ── Renderizado Final en Pantalla ──────────────
    page.add(ft.Column([
        header,
        main_view,
        footer,
    ], expand=True, spacing=0, horizontal_alignment=ft.CrossAxisAlignment.STRETCH))




if __name__ == "__main__":
    # Inicia la aplicación usando la API recomendada para flet > 0.8.0
    ft.run(main)
