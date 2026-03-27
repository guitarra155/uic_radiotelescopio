"""
components/layout.py
Define la cabecera (Header) y el pie de página (Footer) de la aplicación.
"""

import flet as ft
import os
from core.constants import *
from ui.components.shared import border_all
from core.dsp_engine import engine_instance

def build_header(page: ft.Page) -> ft.Control:
    sdr_dot = ft.Text("●", color=ACCENT_RED, size=16)
    sdr_lbl = ft.Text("Estado SDR: Detenido", color=ACCENT_RED, size=12, weight=ft.FontWeight.W_600)
    timer_lbl = ft.Text("", color=ACCENT_AMBER, size=14, weight=ft.FontWeight.W_700)

    async def on_header_msg(msg):
        if msg == "stream_stopped":
            play_btn.content = "▶ Iniciar Adquisición"
            play_btn.bgcolor = ACCENT_GREEN
            sdr_dot.color = ACCENT_RED
            sdr_lbl.value = "Estado SDR: Finalizado"
            sdr_lbl.color = ACCENT_RED
            page.update()
        elif msg == "refresh_charts":
            if engine_instance.stream_mode == "file":
                # Renderiza tiempo transcurrido en el header
                c = engine_instance.current_file_time
                t = engine_instance.total_file_time
                timer_lbl.value = f"⏱ {c:.1f}s / {t:.1f}s"
                timer_lbl.update()
                
    page.pubsub.subscribe(on_header_msg)

    # --- Botón de Play Global ---
    def toggle_stream(e):
        if not engine_instance.is_playing:
            if engine_instance.stream_mode == 'file':
                path = engine_instance.iq_filename
                if not os.path.exists(path):
                    page.snack_bar = ft.SnackBar(ft.Text(f"⚠ Archivo no encontrado en: {path}", color="#fff"), bgcolor=ACCENT_RED)
                    page.snack_bar.open = True
                    page.update()
                    return
                engine_instance.start_stream('file', {'filename': path, 'format': engine_instance.iq_format})
            else:
                engine_instance.start_stream('sdr', {})
                
            play_btn.content = "⏸ Detener Adquisición"
            play_btn.bgcolor = ACCENT_AMBER
            sdr_dot.color = ACCENT_AMBER
            sdr_lbl.value = "Streaming Activo..."
            sdr_lbl.color = ACCENT_AMBER
        else:
            engine_instance.stop_stream()
            play_btn.content = "▶ Iniciar Adquisición"
            play_btn.bgcolor = ACCENT_GREEN
            sdr_dot.color = ACCENT_RED
            sdr_lbl.value = "Estado SDR: Detenido"
            sdr_lbl.color = ACCENT_RED
        page.update()

    play_btn = ft.Button(
        content="▶ Iniciar Adquisición", bgcolor=ACCENT_GREEN, color=DARK_BG,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)),
        on_click=toggle_stream
    )

    # --- Botón de Emergencia ---
    def on_emergency(e):
        engine_instance.stop_stream()
        if hasattr(play_btn, 'content') and "Detener" in play_btn.content:
            play_btn.content = "▶ Iniciar Adquisición"
            play_btn.bgcolor = ACCENT_GREEN
            sdr_dot.color = ACCENT_RED
            sdr_lbl.value = "EMERGENCIA DETENIDA"
            sdr_lbl.color = ACCENT_RED
            timer_lbl.value = ""
            
        sb = ft.SnackBar(
            content=ft.Text("⛔  EMERGENCIA: Todos los hilos DSP han sido abortados.",
                            color="#FFFFFF", weight=ft.FontWeight.BOLD),
            bgcolor=ACCENT_RED,
        )
        page.overlay.append(sb)
        sb.open = True
        page.update()

    emg_btn = ft.Button(
        content="⛔  Stop",
        bgcolor=ACCENT_RED, color="#FFFFFF",
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)),
        on_click=on_emergency,
    )

    return ft.Container(
        bgcolor=PANEL_BG,
        border=ft.Border(bottom=ft.BorderSide(1, BORDER_COL)),
        padding=ft.Padding(left=20, top=10, right=20, bottom=10),
        content=ft.Row([
            ft.Icon(ft.Icons.WIFI_TETHERING, color=ACCENT_CYAN, size=26),
            ft.Text(
                "Procesamiento DSP —",
                color=TEXT_MAIN, size=15, weight=ft.FontWeight.BOLD,
            ),
            ft.Text(
                "Radiotelescopio (1420.40 MHz)",
                color=ACCENT_CYAN, size=14, weight=ft.FontWeight.BOLD, expand=True,
            ),
            ft.Row([sdr_dot, sdr_lbl], spacing=5,
                   vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ft.Container(width=16),
            timer_lbl,
            ft.Container(width=10),
            play_btn,
            emg_btn,
        ], vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=12),
    )

def build_footer() -> ft.Control:
    return ft.Container(
        bgcolor=PANEL_BG,
        border=ft.Border(top=ft.BorderSide(1, BORDER_COL)),
        padding=ft.Padding(left=20, top=6, right=20, bottom=6),
        content=ft.Row([
            ft.Text("UIC Radiotelescopio  •  v1.0.0",         color=TEXT_MUTED, size=10),
            ft.Text("•",                                        color=BORDER_COL, size=10),
            ft.Text("HI 1420.405751 MHz",                      color=TEXT_MUTED, size=10),
            ft.Text("•",                                        color=BORDER_COL, size=10),
            ft.Text("Backend: RTL-SDR / GNU Radio",            color=TEXT_MUTED, size=10),
            ft.Container(expand=True),
            ft.Text("2026-03-22  13:05 CST",                   color=TEXT_MUTED, size=10),
        ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
    )
