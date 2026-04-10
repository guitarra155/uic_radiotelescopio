"""
main.py
Punto de entrada principal. Ensambla y configura el layout global agrupando todos los submódulos.
"""

import flet as ft

from core.constants import *
from ui.components.layout import build_header, build_footer
from ui.tabs.monitoring import build_monitoring
from ui.tabs.spectrogram import build_spectrogram
from ui.tabs.statistics import build_statistics
from ui.tabs.sdr_config import build_config
from ui.tabs.signal_analysis import build_signal_analysis
from ui.tabs.freq_snr import build_freq_snr
from ui.tabs.algo_result import build_algo_result

def main(page: ft.Page):
    from core.dsp_engine import engine_instance
    engine_instance.load_config()

    # Diccionario simple para rastrear modificadores de teclado (Ctrl/Shift)
    key_state = {'ctrl': False, 'shift': False}

    def on_keyboard(e: ft.KeyboardEvent):
        key_state['ctrl'] = e.ctrl
        key_state['shift'] = e.shift
    page.on_keyboard_event = on_keyboard

    # Configuración de Ventana
    page.title      = "Plataforma DSP"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor    = DARK_BG
    page.window.width     = 1280
    page.window.height    = 720
    page.window.min_width = 900
    page.window.min_height= 620
    page.padding = 0
    page.spacing = 0
    page.theme   = ft.Theme(color_scheme_seed=ACCENT_CYAN, use_material3=True)

    # Componentes de Layout Base
    header = build_header(page)
    footer = build_footer()

    tab_labels = [
        "📡  Monitoreo y RFI",
        "🌈  Espectrograma",
        "📊  Estadística & Smart Trigger",
        "⚡  Potencia vs. Tiempo",
        "📶  SNR vs. Frecuencia",
        "🔬  Algoritmo DSP",
    ]

    # Renderizamos los componentes visuales de cada módulo
    tab_contents = [
        build_monitoring(page, key_state),
        build_spectrogram(page, key_state),
        build_statistics(page),
        build_signal_analysis(page, key_state),
        build_freq_snr(page, key_state),
        build_algo_result(page),
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

    # Panel Izquierdo: Sistema de Pestañas (72% del ancho)
    left_panel = ft.Container(
        content=ft.Column([custom_tab_bar, tab_body], expand=True, spacing=0),
        expand=100
    )

    # Panel Derecho: Configuración Fija (28% del ancho)
    right_panel = ft.Container(
        content=build_config(page),
        border=ft.Border(left=ft.BorderSide(1, BORDER_COL)),
        bgcolor=DARK_BG,
        expand=25
    )

    main_view = ft.Row([left_panel, right_panel], expand=True, spacing=0)

    # ── Tarea Asíncrona de Refresco de Interfaz ──────────────
    async def refresh_loop():
        was_playing = False
        while True:
            is_p = engine_instance.is_playing
            try:
                if is_p:
                    page.pubsub.send_all("refresh_charts")
                elif was_playing and not is_p:
                    page.pubsub.send_all("stream_stopped")
            except RuntimeError:
                break
                
            was_playing = is_p
            await asyncio.sleep(0.010)
            
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
