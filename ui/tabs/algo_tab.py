"""
tabs/algo_tab.py
Builder genérico para pestañas de resultados de algoritmos DSP avanzados.
Cada pestaña muestra la gráfica del algoritmo correspondiente + info de picos.

Uso en main.py:
    from ui.tabs.algo_tab import build_algo_tab
    build_algo_tab(page, "ar",     "AR / Burg",     "#B380FF")
    build_algo_tab(page, "cwt",    "CWT / Morlet",  "#00C8FF")
    build_algo_tab(page, "music",  "Pseudo-MUSIC",  "#FF4C4C")
    build_algo_tab(page, "esprit", "ESPRIT",        "#FF80AB")
"""

import flet as ft
from core.constants import *
from ui.components.shared import panel, border_all

# Descripciones cortas de cada algoritmo para el panel lateral
_ALGO_INFO = {
    "ar": {
        "full_name": "Modelo Autorregresivo (AR / Burg)",
        "desc": (
            "Ajusta un modelo paramétrico AR de orden p "
            "a la señal IQ usando el algoritmo de Burg.\n\n"
            "Alta resolución espectral incluso con pocas muestras. "
            "Ideal para señales CW estrechas."
        ),
        "params": "Orden: configurable en el panel derecho (Orden AR).",
        "color": "#B380FF",
    },
    "cwt": {
        "full_name": "Transformada Wavelet Continua (CWT / Morlet)",
        "desc": (
            "Analiza la señal en el dominio tiempo-frecuencia "
            "mediante convolución con wavelet Morlet compleja.\n\n"
            "Muestra cómo varía la energía espectral a lo largo "
            "del tiempo — útil para señales transitorias."
        ),
        "params": "Escala automática: 64 bandas logarítmicas.",
        "color": "#00C8FF",
    },
    "music": {
        "full_name": "Pseudo-MUSIC (MUltiple SIgnal Classification)",
        "desc": (
            "Descompone la matriz de covarianza en sub-espacios "
            "de señal y ruido. El pseudo-espectro muestra picos "
            "ultra-estrechos en las frecuencias de las señales.\n\n"
            "Resolución muy superior a la FFT."
        ),
        "params": "# Señales: configurable en el panel derecho.",
        "color": "#FF4C4C",
    },
    "esprit": {
        "full_name": "ESPRIT (Estimation of Signal Parameters via Rotational Invariance)",
        "desc": (
            "Estima frecuencias directamente desde el sub-espacio "
            "de señal sin barrer frecuencias, usando la estructura "
            "rotacional del array.\n\n"
            "Más eficiente que MUSIC para pocos componentes."
        ),
        "params": "# Señales: configurable en el panel derecho.",
        "color": "#FF80AB",
    },
}


def build_algo_tab(page: ft.Page, algo_key: str,
                   title: str, color: str) -> ft.Control:
    from core.dsp_engine import engine_instance

    info = _ALGO_INFO.get(algo_key, {})

    # Imagen principal del resultado
    img = ft.Image(
        src=None,
        fit=ft.BoxFit.CONTAIN,
        gapless_playback=True,
        border_radius=10,
        expand=True,
    )

    # Estado y métricas
    status_txt   = ft.Text("Esperando resultados...", color=TEXT_MUTED,
                           size=11, italic=True)
    peaks_col    = ft.Column([], spacing=4, scroll=ft.ScrollMode.AUTO)
    peaks_count  = ft.Text("—", color=color, size=12,
                           weight=ft.FontWeight.W_600)

    def _update_peaks_display(b64: str):
        img.src = b64
        if img.page:
            img.update()

        # Para CWT no hay picos, mostramos solo el mapa
        if algo_key == "cwt":
            peaks_count.value = "Mapa 2D tiempo-frecuencia"
            peaks_col.controls.clear()
            peaks_col.controls.append(
                ft.Text("La intensidad del color indica\n"
                        "la potencia wavelet en cada instante.",
                        color=TEXT_MUTED, size=10, italic=True)
            )
        else:
            # Calcular info de picos desde algo_results no tenemos peaks
            # Solo mostramos que hay un resultado nuevo
            peaks_count.value = "Resultado actualizado ✓"
            peaks_col.controls.clear()
            peaks_col.controls.append(
                ft.Text("Los picos se marcan directamente\nen la gráfica con líneas verticales.",
                        color=TEXT_MUTED, size=10, italic=True)
            )

        status_txt.value = "✓ Actualizado"
        status_txt.color = ACCENT_GREEN
        if status_txt.page:
            status_txt.update()
        if peaks_count.page:
            peaks_count.update()
        if peaks_col.page:
            peaks_col.update()

    # Suscribirse a "algo_results_ready" para actualizar la imagen
    async def on_algo_ready(msg):
        if msg != "algo_results_ready":
            return
        b64 = engine_instance.algo_results.get(algo_key)
        if b64 is None:
            return
        _update_peaks_display(b64)

    page.pubsub.subscribe(on_algo_ready)

    # ── Panel lateral ────────────────────────────────────────────────────────
    side = panel(
        width=270,
        padding_val=14,
        content=ft.Column([
            # Indicador de color del algoritmo
            ft.Row([
                ft.Container(width=12, height=12, bgcolor=color,
                             border_radius=6),
                ft.Text(title, color=color, size=14,
                        weight=ft.FontWeight.BOLD, expand=1),
            ], spacing=8),

            ft.Divider(color=BORDER_COL, height=10),

            ft.Text(info.get("full_name", title),
                    color=TEXT_MAIN, size=11, weight=ft.FontWeight.W_600),
            ft.Container(height=4),
            ft.Text(info.get("desc", ""), color=TEXT_MUTED, size=10),

            ft.Divider(color=BORDER_COL, height=10),
            ft.Text("⚙️  Parámetros", color=ACCENT_CYAN, size=12,
                    weight=ft.FontWeight.BOLD),
            ft.Text(info.get("params", ""), color=TEXT_MUTED, size=10),

            ft.Divider(color=BORDER_COL, height=10),
            ft.Text("📊  Estado", color=ACCENT_CYAN, size=12,
                    weight=ft.FontWeight.BOLD),
            status_txt,
            ft.Container(height=4),
            peaks_count,
            ft.Container(
                content=peaks_col,
                expand=True,
            ),

            ft.Divider(color=BORDER_COL, height=8),
            ft.Text(
                "Los algoritmos se recalculan cada\n~0.5 s con el stream activo.\n"
                "Configura parámetros en el panel\nderecho → 🔬 Algoritmos DSP.",
                color=TEXT_MUTED, size=9, italic=True,
            ),
        ], spacing=6, expand=True),
    )

    # Borde superior de color según algoritmo
    chart_container = ft.Container(
        content=img,
        expand=True,
        bgcolor=PANEL_BG,
        border_radius=10,
        border=ft.Border(
            top=ft.BorderSide(2, color),
            right=ft.BorderSide(1, BORDER_COL),
            bottom=ft.BorderSide(1, BORDER_COL),
            left=ft.BorderSide(1, BORDER_COL),
        ),
        padding=8,
    )

    return ft.Container(
        content=ft.Row([chart_container, side], spacing=10, expand=True),
        expand=True,
        padding=ft.Padding(left=14, top=14, right=14, bottom=14),
    )
