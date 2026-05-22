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
from ui.tabs.monitoring import build_monitoring
from ui.tabs.dual_monitoring import build_dual_monitoring
from ui.tabs.spectrogram import build_spectrogram
from ui.tabs.statistics import build_statistics
from ui.tabs.sdr_config import build_config
from ui.tabs.signal_analysis import build_signal_analysis
from ui.tabs.freq_snr import build_freq_snr
from ui.tabs.algo_result import build_algo_result
from ui.tabs.estado import build_estado

def main(page: ft.Page):
    from core.dsp_engine import engine_instance
    engine_instance.load_config()

    key_state = {'ctrl': False, 'shift': False}

    def on_keyboard(e: ft.KeyboardEvent):
        key_state['ctrl'] = e.ctrl
        key_state['shift'] = e.shift
        if e.key == "F5":
            page.pubsub.send_all("toggle_stream")
        elif e.key == "F11":
            page.window.full_screen = not page.window.full_screen
            page.update()
    page.on_keyboard_event = on_keyboard

    # Configuración de Ventana
    page.title      = "Plataforma DSP"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor    = DARK_BG
    page.window.width     = 1920    
    page.window.height    = 1080
    page.window.min_width = 900
    page.window.min_height= 620
    page.padding = 0
    page.spacing = 0
    page.theme   = ft.Theme(color_scheme_seed=ACCENT_CYAN, use_material3=True)

    # Capturar y sincronizar las dimensiones de la ventana con el renderizador de gráficas
    def on_page_resize(e):
        engine_instance.window_width = page.window.width
        engine_instance.window_height = page.window.height
    page.on_resize = on_page_resize
    engine_instance.window_width = page.window.width
    engine_instance.window_height = page.window.height

    # Componentes de Layout Base
    header = build_header(page)
    footer = build_footer()

    tab_labels = [
        "🏠  Inicio & Configuración",    # 0
        "🌓  Monitoreo Dual (RAW/MA)",   # 1
        "🌈  Espectrograma",             # 2
        "📊  Estadística & Smart Trigger",# 3
        "⚡  Potencia vs. Tiempo",        # 4
        "📶  SNR vs. Frecuencia",        # 5
        "🔬  Algoritmo DSP",             # 6
    ]

    # Renderizamos los componentes visuales de cada módulo
    tab_contents = [
        build_estado(page),                          # 0
        build_dual_monitoring(page, key_state),      # 1
        build_spectrogram(page, key_state),          # 2
        build_statistics(page),                       # 3
        build_signal_analysis(page, key_state),      # 4
        build_freq_snr(page, key_state),             # 5
        build_algo_result(page),                     # 6
    ]

    selected = [0]  # índice activo

    # Indicadores de subrayado activo
    indicators = [
        ft.Container(height=2, bgcolor=ACCENT_CYAN if i == 0 else "transparent", border_radius=1)
        for i in range(len(tab_labels))
    ]

    tab_btns = []

    def make_tab_btn(i, label):
        lbl_text = ft.Text(label, color=ACCENT_CYAN if i == 0 else TEXT_MUTED)
        btn = ft.Container(
            content=lbl_text,
            padding=ft.Padding(left=16, right=16, top=5, bottom=5),
            ink=True,
            border_radius=4,
            bgcolor="transparent"
        )
        def on_click(e, idx):
            tab_btns[selected[0]].content.color = TEXT_MUTED
            indicators[selected[0]].bgcolor = "transparent"
            
            selected[0] = idx
            from core.dsp_engine import engine_instance
            engine_instance.active_tab = idx
            
            tab_body.content = tab_contents[idx]
            
            tab_btns[idx].content.color = ACCENT_CYAN
            indicators[idx].bgcolor = ACCENT_CYAN
            page.pubsub.send_all("tab_changed")
            page.update()
        btn.on_click = lambda e: on_click(e, i)
        return btn

    tab_btns = [make_tab_btn(i, lbl) for i, lbl in enumerate(tab_labels)]

    tab_row = ft.Row(
        [ft.Column([btn, ind], spacing=0) for btn, ind in zip(tab_btns, indicators)],
        spacing=20,
        scroll=ft.ScrollMode.AUTO,
    )

    custom_tab_bar = ft.Container(
        bgcolor=PANEL_BG,
        border=ft.Border(bottom=ft.BorderSide(1, BORDER_COL)),
        content=tab_row,
        height=40,
    )

    tab_body = ft.AnimatedSwitcher(
        content=tab_contents[0],
        transition=ft.AnimatedSwitcherTransition.FADE,
        duration=200,
        switch_in_curve=ft.AnimationCurve.EASE_OUT,
        expand=True
    )

    import asyncio

    # Panel Izquierdo (Contenido de la pestaña, 72% del ancho)
    left_panel_content = ft.Container(
        content=tab_body,
        expand=100,
        padding=ft.Padding(top=5, left=0, right=0, bottom=0)
    )

    # Panel Derecho: Configuración Fija (28% del ancho)
    right_panel = ft.Container(
        content=build_config(page),
        border=ft.Border(left=ft.BorderSide(1, BORDER_COL)),
        bgcolor=DARK_BG,
        expand= 35
    )

    lower_split = ft.Row([left_panel_content, right_panel], expand=True, spacing=0)

    main_view = ft.Column([custom_tab_bar, lower_split], expand=True, spacing=0)

    # ── Manejo de Reset de Configuración ───────────────────────
    def on_config_reset(msg):
        if msg == "config_reset":
            right_panel.content = build_config(page)
            page.update()
    page.pubsub.subscribe(on_config_reset)

    # ── Tarea de Refresco de Interfaz ──────────────
    async def refresh_loop():
        was_playing = False
        while True:
            is_p = engine_instance.is_playing
            try:
                # El motor detectó metadatos nuevos (ej: sintonía automática)
                if getattr(engine_instance, "metadata_updated", False):
                    # Solo enviamos señal de refresco de gráficas/títulos, NO de configuración
                    engine_instance.metadata_updated = False
                    page.pubsub.send_all("refresh_charts")

                if is_p and getattr(engine_instance, "data_ready", False):
                    page.pubsub.send_all("refresh_charts")
                    engine_instance.data_ready = False
                elif was_playing and not is_p:
                    page.pubsub.send_all("stream_stopped")
            except RuntimeError:
                break
                
            was_playing = is_p
            await asyncio.sleep(0.05) # Chequeo rápido del flag
            
    page.run_task(refresh_loop)

    # ── Renderizado Final en Pantalla ──────────────
    page.add(ft.Column([
        header,
        main_view,
        footer,
    ], expand=True, spacing=0))


if __name__ == "__main__":
    # Inicia la aplicación usando la API recomendada para flet > 0.8.0
    ft.run(main)
