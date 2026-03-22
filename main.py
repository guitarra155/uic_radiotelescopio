"""
main.py
Punto de entrada principal. Ensambla y configura el layout global agrupando todos los submódulos.
"""

import flet as ft

from constants import *
from components.layout import build_header, build_footer
from tabs.monitoring import build_monitoring
from tabs.spectrogram import build_spectrogram
from tabs.statistics import build_statistics
from tabs.sdr_config import build_config

def main(page: ft.Page):
    # Configuración de Ventana
    page.title      = "Plataforma DSP — Radiotelescopio 1420.40 MHz"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor    = DARK_BG
    page.window.width     = 1280
    page.window.height    = 820
    page.window.min_width = 900
    page.window.min_height= 620
    page.padding = 0
    page.spacing = 0
    page.theme   = ft.Theme(color_scheme_seed=ACCENT_CYAN, use_material3=True)

    # Componentes de Layout Base
    header = build_header(page)
    footer = build_footer()

    # ── Sistema de Pestañas (TabBar nativo de Flet 0.82) ──────────────
    tab_labels = [
        "📡  Monitoreo y RFI",
        "🌈  Espectrograma",
        "📊  Estadística & Smart Trigger",
        "⚙️  Configuración SDR",
    ]
    
    # Renderizamos los componentes visuales de cada módulo
    tab_contents = [
        build_monitoring(page),
        build_spectrogram(page),
        build_statistics(page),
        build_config(page),
    ]

    tab_bar = ft.TabBar(
        tabs=[ft.Tab(label=lbl) for lbl in tab_labels],
        label_color=ACCENT_CYAN,
        unselected_label_color=TEXT_MUTED,
        indicator_color=ACCENT_CYAN,
        divider_color=BORDER_COL,
    )
    
    tab_view = ft.TabBarView(controls=tab_contents, expand=True)

    # El contenedor maestro de tabs engloba ambos componentes
    tabs = ft.Tabs(
        content=ft.Column([
            tab_bar,
            tab_view
        ], expand=True, spacing=0),
        length=len(tab_labels),
        selected_index=0,
        expand=True,
    )

    # ── Renderizado Final en Pantalla ──────────────
    page.add(ft.Column([
        header,
        tabs,
        footer,
    ], expand=True, spacing=0))


if __name__ == "__main__":
    # Inicia la aplicación usando la API recomendada para escritorio clásico
    ft.app(target=main)
