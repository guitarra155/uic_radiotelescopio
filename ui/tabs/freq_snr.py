"""
tabs/freq_snr.py
Pestaña dedicada exclusivamente a "Frecuencia vs. SNR" — gráfica a pantalla completa
con panel de señales de interés detectadas en tiempo real.
"""

import asyncio
import flet as ft
from core.constants import *
from ui.charts import chart_freq_snr
from ui.components.shared import panel, border_all


def build_freq_snr(page: ft.Page, key_state: dict) -> ft.Control:
    from core.dsp_engine import engine_instance

    img = ft.Image(src=chart_freq_snr(), fit=ft.BoxFit.CONTAIN,
                   gapless_playback=True, border_radius=10, expand=True)

    # ── Tabla de señales detectadas ──────────────────────────────────────────
    signals_col = ft.Column([], spacing=4, scroll=ft.ScrollMode.AUTO)
    signals_count = ft.Text("0 señales detectadas", color=ACCENT_AMBER,
                            size=12, weight=ft.FontWeight.W_600)

    def _rebuild_signals_table():
        soi = engine_instance.signals_of_interest
        signals_count.value = (f"{len(soi)} señal(es) detectada(s)"
                               if soi else "Sin señales sobre el umbral")
        signals_count.color = ACCENT_AMBER if soi else TEXT_MUTED
        signals_col.controls.clear()

        if soi:
            # Encabezado
            signals_col.controls.append(
                ft.Row([
                    ft.Text("Frec. (MHz)", color=TEXT_MUTED, size=10,
                            weight=ft.FontWeight.W_600, expand=2),
                    ft.Text("SNR (dB)", color=TEXT_MUTED, size=10,
                            weight=ft.FontWeight.W_600, expand=1),
                    ft.Text("Estado", color=TEXT_MUTED, size=10,
                            weight=ft.FontWeight.W_600, expand=1),
                ])
            )
            signals_col.controls.append(ft.Divider(color=BORDER_COL, height=4))

            for freq_mhz, snr_db in sorted(soi, key=lambda x: x[1], reverse=True):
                # Clasificar por SNR
                if snr_db >= 20:
                    badge, badge_col = "FUERTE", ACCENT_RED
                elif snr_db >= 12:
                    badge, badge_col = "MODERADA", ACCENT_AMBER
                else:
                    badge, badge_col = "DÉBIL", ACCENT_GREEN

                # Destacar HI 1420.40 MHz
                is_hi = abs(freq_mhz - 1420.40) < 0.02
                freq_color = ACCENT_CYAN if is_hi else TEXT_MAIN
                freq_label = f"{freq_mhz:.4f}" + (" ★" if is_hi else "")

                signals_col.controls.append(
                    ft.Container(
                        content=ft.Row([
                            ft.Text(freq_label, color=freq_color, size=11,
                                    weight=ft.FontWeight.W_600, expand=2),
                            ft.Text(f"{snr_db:.1f}", color=badge_col,
                                    size=11, expand=1),
                            ft.Container(
                                content=ft.Text(badge, color="#000", size=9,
                                                weight=ft.FontWeight.BOLD),
                                bgcolor=badge_col,
                                border_radius=4,
                                padding=ft.Padding(left=6, right=6, top=2, bottom=2),
                            ),
                        ]),
                        bgcolor="#0A0F16",
                        border_radius=6,
                        padding=ft.Padding(left=10, right=10, top=6, bottom=6),
                    )
                )
        else:
            signals_col.controls.append(
                ft.Text("El umbral actual es 6 dB.\nAumenta el SNR o activa el stream.",
                        color=TEXT_MUTED, size=10, italic=True)
            )

    _rebuild_signals_table()

    # ── Estadísticas rápidas ─────────────────────────────────────────────────
    val_noise = ft.Text("—", color=TEXT_MUTED, size=11)
    val_pico  = ft.Text("—", color=ACCENT_GREEN, size=11)
    val_rango = ft.Text("—", color=TEXT_MUTED, size=11)

    # ── Refresco automático ──────────────────────────────────────────────────
    is_rendering = [False]

    async def on_refresh(msg):
        if msg != "refresh_charts":
            return
        if engine_instance.active_tab != 4: return # Solo renderizar si es la pestaña activa
            
        if is_rendering[0]:
            return
        is_rendering[0] = True
        try:
            import numpy as np
            snr_b64 = await asyncio.to_thread(chart_freq_snr)
            img.src = snr_b64
            img.update()

            _rebuild_signals_table()

            noise_floor = float(np.median(engine_instance.spectrum_data))
            val_noise.value = f"{noise_floor:.1f} dBFS"

            snr = engine_instance.snr_data
            best_bin = int(np.argmax(snr))
            fc  = engine_instance.center_freq
            fs  = engine_instance.sample_rate / 1_000_000
            import numpy as np2
            freqs = np2.linspace(fc - fs/2, fc + fs/2, len(snr))
            val_pico.value  = f"{freqs[best_bin]:.4f} MHz ({snr[best_bin]:.1f} dB)"
            val_rango.value = f"{engine_instance.f_min:.3f} – {engine_instance.f_max:.3f} MHz"

            signals_count.update()
            signals_col.update()
            val_noise.update()
            val_pico.update()
            val_rango.update()
        finally:
            is_rendering[0] = False

    page.pubsub.subscribe(on_refresh)

    # ── Zoom con scroll ──────────────────────────────────────────────────────
    def on_zoom_scroll(e: ft.ScrollEvent):
        ctrl  = key_state.get("ctrl",  False)
        shift = key_state.get("shift", False)
        if not ctrl and not shift:
            return
        d = 1 if e.scroll_delta_y > 0 else -1
        factor = 0.2 * d
        if ctrl:
            s_db = engine_instance.db_max - engine_instance.db_min
            engine_instance.db_min -= s_db * factor
            engine_instance.db_max += s_db * factor
            engine_instance.save_config()
        elif shift:
            s_f = engine_instance.f_max - engine_instance.f_min
            engine_instance.f_min -= s_f * factor
            engine_instance.f_max += s_f * factor
            engine_instance.save_config()

    # ── Panel lateral ────────────────────────────────────────────────────────
    side = panel(
        width=280,
        padding_val=14,
        content=ft.Column([
            ft.Text("📶  Señales Detectadas", color=ACCENT_CYAN, size=14,
                    weight=ft.FontWeight.BOLD),
            ft.Text("Umbral: 6 dB sobre el piso de ruido",
                    color=TEXT_MUTED, size=10, italic=True),
            ft.Divider(color=BORDER_COL, height=8),
            signals_count,
            ft.Container(
                content=signals_col,
                expand=True,
                bgcolor=PANEL_BG,
            ),
            ft.Divider(color=BORDER_COL, height=8),
            ft.Text("📊  Estadísticas", color=ACCENT_CYAN, size=13,
                    weight=ft.FontWeight.BOLD),
            ft.Row([ft.Text("Piso ruido:", color=TEXT_MAIN, size=10, expand=1),
                    val_noise]),
            ft.Row([ft.Text("Pico SNR:",   color=TEXT_MAIN, size=10, expand=1),
                    val_pico]),
            ft.Row([ft.Text("Rango X:",    color=TEXT_MAIN, size=10, expand=1),
                    val_rango]),
            ft.Divider(color=BORDER_COL, height=8),
            ft.Text("Ctrl+Scroll → zoom Y\nShift+Scroll → zoom X",
                    color=TEXT_MUTED, size=9, italic=True),
        ], spacing=8, expand=True),
    )

    chart_container = ft.Container(
        content=ft.GestureDetector(
            mouse_cursor=ft.MouseCursor.ZOOM_IN,
            on_scroll=on_zoom_scroll,
            drag_interval=0,
            content=img,
        ),
        expand=True,
        bgcolor=PANEL_BG,
        border_radius=10,
        border=border_all(),
        padding=6,
    )

    return ft.Container(
        content=ft.Row([chart_container, side], spacing=10, expand=True),
        expand=True,
        padding=ft.Padding(left=14, top=14, right=14, bottom=14),
    )
