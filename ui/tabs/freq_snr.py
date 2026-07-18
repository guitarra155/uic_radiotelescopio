"""
tabs/freq_snr.py
Pestaña dedicada exclusivamente a "Frecuencia vs. SNR" — gráfica a pantalla completa
con panel de señales de interés detectadas en tiempo real.
"""

import asyncio
import flet as ft
import core.constants as C
from ui.charts import chart_freq_snr
from ui.components.shared import panel, border_all


def build_freq_snr(page: ft.Page, key_state: dict) -> ft.Control:
    from core.dsp_engine import engine_instance

    img = ft.Image(
        src=chart_freq_snr(),
        fit=ft.BoxFit.FILL,
        gapless_playback=True,
        border_radius=10,
        expand=True,
    )

    # ── Tabla de señales detectadas ──────────────────────────────────────────
    signals_col = ft.Column([], spacing=4, scroll=ft.ScrollMode.AUTO)
    signals_count = ft.Text(
        "0 señales detectadas", color=C.ACCENT_AMBER, size=12, weight=ft.FontWeight.W_600
    )

    def _rebuild_signals_table():
        soi = engine_instance.signals_of_interest
        signals_count.value = (
            f"{len(soi)} señal(es) detectada(s)"
            if soi
            else "Sin señales sobre el umbral"
        )
        signals_count.color = C.ACCENT_AMBER if soi else C.TEXT_MUTED
        signals_col.controls.clear()

        if soi:
            # Encabezado
            signals_col.controls.append(
                ft.Row(
                    [
                        ft.Text(
                            "Frec. (MHz)",
                            color=C.TEXT_MUTED,
                            size=10,
                            weight=ft.FontWeight.W_600,
                            expand=2,
                        ),
                        ft.Text(
                            "SNR (dB)",
                            color=C.TEXT_MUTED,
                            size=10,
                            weight=ft.FontWeight.W_600,
                            expand=1,
                        ),
                        ft.Text(
                            "Estado",
                            color=C.TEXT_MUTED,
                            size=10,
                            weight=ft.FontWeight.W_600,
                            expand=1,
                        ),
                    ]
                )
            )
            signals_col.controls.append(ft.Divider(color=C.BORDER_COL, height=4))

            for freq_mhz, snr_db in sorted(soi, key=lambda x: x[1], reverse=True):
                # Clasificar por SNR
                if snr_db >= 20:
                    badge, badge_col = "FUERTE", C.ACCENT_RED
                elif snr_db >= 12:
                    badge, badge_col = "MODERADA", C.ACCENT_AMBER
                else:
                    badge, badge_col = "DÉBIL", C.ACCENT_GREEN

                # Destacar HI 1420.40 MHz
                is_hi = abs(freq_mhz - 1420.40) < 0.02
                freq_color = C.ACCENT_CYAN if is_hi else C.TEXT_MAIN
                freq_label = f"{freq_mhz:.4f}" + (" ★" if is_hi else "")

                signals_col.controls.append(
                    ft.Container(
                        content=ft.Row(
                            [
                                ft.Text(
                                    freq_label,
                                    color=freq_color,
                                    size=11,
                                    weight=ft.FontWeight.W_600,
                                    expand=2,
                                ),
                                ft.Text(
                                    f"{snr_db:.1f}", color=badge_col, size=11, expand=1
                                ),
                                ft.Container(
                                    content=ft.Text(
                                        badge,
                                        color="#000",
                                        size=9,
                                        weight=ft.FontWeight.BOLD,
                                    ),
                                    bgcolor=badge_col,
                                    border_radius=4,
                                    padding=ft.Padding(
                                        left=6, right=6, top=2, bottom=2
                                    ),
                                ),
                            ]
                        ),
                        bgcolor=C.DARK_BG,
                        border_radius=6,
                        padding=ft.Padding(left=10, right=10, top=6, bottom=6),
                    )
                )
        else:
            signals_col.controls.append(
                ft.Text(
                    "El umbral actual es 6 dB.\nAumenta el SNR o activa el stream.",
                    color=C.TEXT_MUTED,
                    size=10,
                    italic=True,
                )
            )

    _rebuild_signals_table()

    # ── Estadísticas rápidas ─────────────────────────────────────────────────
    val_noise = ft.Text("—", color=C.TEXT_MUTED, size=11)
    val_pico = ft.Text("—", color=C.ACCENT_GREEN, size=11)
    val_rango = ft.Text("—", color=C.TEXT_MUTED, size=11)

    # ── Refresco automático ──────────────────────────────────────────────────
    is_rendering = [False]

    async def on_refresh(msg):
        if isinstance(msg, tuple) and msg[0] == "toggle_tab_panel":
            if msg[1] == 5:
                on_toggle_side(None)
            return
        if msg not in ("refresh_charts", "tab_changed"):
            return
        if engine_instance.active_tab != 5:
            return  # Solo renderizar si es la pestaña activa

        if is_rendering[0]:
            return
        is_rendering[0] = True
        try:
            import numpy as np

            snr_b64 = await asyncio.to_thread(chart_freq_snr)
            img.src = snr_b64

            _rebuild_signals_table()

            noise_floor = float(np.median(engine_instance.spectrum_data))
            val_noise.value = f"{noise_floor:.1f} dBm"

            snr = engine_instance.snr_data
            best_bin = int(np.argmax(snr))
            fc = engine_instance.center_freq
            fs = engine_instance.sample_rate / 1_000_000
            freqs = np.linspace(fc - fs / 2, fc + fs / 2, len(snr))
            val_pico.value = f"{freqs[best_bin]:.4f} MHz ({snr[best_bin]:.1f} dB)"
            val_rango.value = (
                f"{engine_instance.f_min:.3f} – {engine_instance.f_max:.3f} MHz"
            )

            for w in [img, signals_count, signals_col, val_noise, val_pico, val_rango]:
                if w.page: w.update()
        finally:
            is_rendering[0] = False

    page.pubsub.subscribe(on_refresh)

    def reset_defaults(e):
        engine_instance.reset_to_defaults()
        engine_instance.save_config()

    # ── Zoom con scroll ──────────────────────────────────────────────────────
    def on_zoom_scroll(e: ft.ScrollEvent):
        from core.dsp_engine import engine_instance
        
        if e.scroll_delta.y != 0:
            d = 1 if e.scroll_delta.y > 0 else -1
            s_snr = engine_instance.snr_max - engine_instance.snr_min
            engine_instance.snr_min -= s_snr * 0.15 * d
            engine_instance.snr_max += s_snr * 0.15 * d
        elif e.scroll_delta.x != 0:
            d = 1 if e.scroll_delta.x > 0 else -1
            s_f = engine_instance.f_max - engine_instance.f_min
            engine_instance.f_min -= s_f * 0.15 * d
            engine_instance.f_max += s_f * 0.15 * d
        else:
            return

        engine_instance.save_config()
        page.pubsub.send_all("refresh_charts")

    def save_current_detections(e):
        import time
        import os
        import json
        import numpy as np
        import threading

        folder = "Resultados_Datos"
        if not os.path.exists(folder):
            os.makedirs(folder)

        timestamp = int(time.time())
        timestr = time.strftime("%Y%m%d_%H%M%S")

        # 1. Guardar metadatos JSON
        metadata = {
            "timestamp": timestamp,
            "datetime_utc": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(timestamp)),
            "center_frequency_mhz": engine_instance.center_freq,
            "sample_rate_hz": engine_instance.sample_rate,
            "noise_floor_dbfs": float(np.median(engine_instance.spectrum_data)) if len(engine_instance.spectrum_data) > 0 else 0.0,
            "signals_detected": [
                {"frequency_mhz": float(freq), "snr_db": float(snr)}
                for freq, snr in sorted(engine_instance.signals_of_interest, key=lambda x: x[1], reverse=True)
            ]
        }

        json_path = os.path.join(folder, f"cfar_detection_{timestr}.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=4)

        # 2. Guardar curva SNR en CSV (Frecuencia vs SNR)
        fc = engine_instance.center_freq
        fs = engine_instance.sample_rate / 1_000_000
        n_bins = len(engine_instance.snr_data)
        freqs = np.linspace(fc - fs / 2, fc + fs / 2, n_bins)

        csv_path = os.path.join(folder, f"cfar_detection_{timestr}.csv")
        with open(csv_path, "w", encoding="utf-8") as f_csv:
            f_csv.write("Frecuencia_MHz,SNR_dB\n")
            for f_val, snr_val in zip(freqs, engine_instance.snr_data):
                f_csv.write(f"{f_val:.8f},{snr_val:.4f}\n")

        # Efecto visual de guardado exitoso
        btn_save.text = "¡Guardado!"
        btn_save.bgcolor = C.ACCENT_GREEN
        btn_save.color = ft.Colors.WHITE
        try: btn_save.update()
        except: pass

        async def revert():
            await asyncio.sleep(1.5)
            btn_save.text = "💾 Guardar Detección"
            btn_save.bgcolor = C.ACCENT_CYAN
            btn_save.color = C.DARK_BG
            try: btn_save.update()
            except: pass

        threading.Thread(target=lambda: asyncio.run(revert())).start()

    btn_save = ft.ElevatedButton(
        "💾 Guardar Detección",
        on_click=save_current_detections,
        style=ft.ButtonStyle(
            bgcolor=C.ACCENT_CYAN,
            color=C.DARK_BG,
            shape=ft.RoundedRectangleBorder(radius=4)
        ),
        width=250,
    )

    # ── Panel lateral ────────────────────────────────────────────────────────
    side = panel(
        width=280,
        padding_val=14,
        content=ft.Column(
            [
                ft.Text(
                    "📶  Señales Detectadas",
                    color=C.ACCENT_CYAN,
                    size=14,
                    weight=ft.FontWeight.BOLD,
                ),
                ft.Row(
                    [
                        ft.Text("Auto-detección:", color=C.TEXT_MUTED, size=10),
                        ft.TextButton(
                            "Restaurar",
                            on_click=reset_defaults,
                            style=ft.ButtonStyle(color=C.ACCENT_CYAN),
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.Text(
                    "Umbral: 6 dB sobre el piso de ruido",
                    color=C.TEXT_MUTED,
                    size=10,
                    italic=True,
                ),
                ft.Divider(color=C.BORDER_COL, height=8),
                signals_count,
                ft.Container(
                    content=signals_col,
                    expand=True,
                    bgcolor=C.PANEL_BG,
                ),
                ft.Divider(color=C.BORDER_COL, height=8),
                ft.Text(
                    "📊  Estadísticas",
                    color=C.ACCENT_CYAN,
                    size=13,
                    weight=ft.FontWeight.BOLD,
                ),
                ft.Row(
                    [
                        ft.Text("Piso ruido:", color=C.TEXT_MAIN, size=10, expand=1),
                        val_noise,
                    ]
                ),
                ft.Row(
                    [ft.Text("Pico SNR:", color=C.TEXT_MAIN, size=10, expand=1), val_pico]
                ),
                ft.Row(
                    [ft.Text("Rango X:", color=C.TEXT_MAIN, size=10, expand=1), val_rango]
                ),
                ft.Divider(color=C.BORDER_COL, height=8),
                ft.Text(
                    "Ctrl+Scroll → zoom Y\nShift+Scroll → zoom X",
                    color=C.TEXT_MUTED,
                    size=9,
                    italic=True,
                ),
                ft.Container(height=5),
                btn_save,
            ],
            spacing=8,
            expand=True,
        ),
    )

    def on_fullscreen_global(e):
        from core.dsp_engine import engine_instance
        is_fs = getattr(engine_instance, "chart_fullscreen_active", False)
        engine_instance.chart_fullscreen_active = not is_fs
        
        is_fs = engine_instance.chart_fullscreen_active
        side.visible = not is_fs
            
        e.control.icon = ft.Icons.CLOSE_FULLSCREEN if engine_instance.chart_fullscreen_active else ft.Icons.ASPECT_RATIO
        e.control.page.pubsub.send_all("toggle_fullscreen_chart")

    btn_fs = ft.IconButton(
        icon=ft.Icons.ASPECT_RATIO,
        icon_color=C.ACCENT_AMBER,
        icon_size=18,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=4)),
        on_click=on_fullscreen_global,
        tooltip="Pantalla Completa (Global)",
        padding=0,
        width=26,
        height=26
    )

    def on_toggle_side(e):
        side.visible = not side.visible
        btn_toggle_side.icon = ft.Icons.VIEW_SIDEBAR_OUTLINED if side.visible else ft.Icons.VIEW_SIDEBAR
        btn_toggle_side.icon_color = C.ACCENT_CYAN if side.visible else C.ACCENT_AMBER
        btn_toggle_side.tooltip = "Ocultar panel de señales detectadas" if side.visible else "Mostrar panel de señales detectadas"
        page.update()

    btn_toggle_side = ft.IconButton(
        icon=ft.Icons.VIEW_SIDEBAR_OUTLINED,
        icon_color=C.ACCENT_CYAN,
        icon_size=18,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=4)),
        on_click=on_toggle_side,
        tooltip="Ocultar panel de señales detectadas",
        padding=0,
        width=26,
        height=26
    )

    chart_container = ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Text("FRECUENCIA VS. SNR", color=C.ACCENT_CYAN, size=10, weight=ft.FontWeight.BOLD),
                ft.Row([btn_toggle_side, btn_fs], spacing=5)
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.GestureDetector(
                mouse_cursor=ft.MouseCursor.ZOOM_IN,
                on_scroll=on_zoom_scroll,
                drag_interval=0,
                content=img,
                expand=True,
            )
        ], spacing=2, horizontal_alignment=ft.CrossAxisAlignment.STRETCH),
        expand=True,
        bgcolor=C.PANEL_BG,
        border_radius=10,
        border=border_all(),
        padding=6,
    )

    return ft.Container(
        content=ft.Row([chart_container, side], spacing=10, expand=True, vertical_alignment=ft.CrossAxisAlignment.STRETCH),
        expand=True,
        padding=ft.Padding(left=14, top=14, right=14, bottom=14),
    )
