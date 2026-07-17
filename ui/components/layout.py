"""
components/layout.py
Define la cabecera (Header) y el pie de página (Footer) de la aplicación.
Usa import de módulo para compatibilidad con temas dinámicos.
"""

import flet as ft
import os
import core.constants as C
from ui.components.shared import border_all
from core.dsp_engine import engine_instance

def build_header(page: ft.Page) -> ft.Control:
    sdr_dot = ft.Text("●", color=C.ACCENT_RED, size=16)
    sdr_lbl = ft.Text("Estado Actual: Detenido", color=C.ACCENT_RED, size=12, weight=ft.FontWeight.W_600)
    timer_lbl = ft.Text("", color=C.ACCENT_AMBER, size=14, weight=ft.FontWeight.W_700)

    header_title = ft.Text(
        f"Frecuencia Central SDR: {engine_instance.center_freq} MHz",
        color=C.ACCENT_CYAN, size=14, weight=ft.FontWeight.BOLD, expand=True,
    )

    # ── Estado interno de reproducción ─────────────────────────────────────
    # "stopped" | "playing" | "paused"
    _state = ["stopped"]
    _rec_state = [False]  # False = sin grabar, True = grabando

    # ── Etiqueta de frame actual durante el review ──────────────────────────
    frame_lbl = ft.Text(
        "Frame 0 / 0",
        color=C.ACCENT_AMBER,
        size=11,
        weight=ft.FontWeight.W_600,
        visible=False,
    )

    def _update_frame_label():
        n = len(engine_instance._frame_snapshots)
        off = engine_instance._review_offset
        if n > 0:
            frame_lbl.value = f"Frame -{off} / {n - 1}"
        else:
            frame_lbl.value = "Sin historial"
        if frame_lbl.page:
            frame_lbl.update()

    # ── Botón principal Play / Pausa / Reanudar ─────────────────────────────
    play_btn = ft.ElevatedButton(
        content=ft.Text("▶ Iniciar Adquisición", color=C.DARK_BG, weight=ft.FontWeight.BOLD),
        bgcolor=C.ACCENT_GREEN,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)),
        on_click=lambda e: on_play_pause(e),
    )

    # ── Panel de navegación de frames (visible solo en pausa) ───────────────
    def on_seek(delta: int):
        offset = engine_instance.seek_frames(delta)
        _update_frame_label()
        # Forzar refresh en TODAS las pestañas ignorando el filtro de active_tab
        engine_instance.data_ready = True
        engine_instance._seek_refresh = True   # flag especial para bypass de tab filter
        page.pubsub.send_all("refresh_charts_all")

    btn_prev10 = ft.IconButton(
        icon=ft.Icons.FAST_REWIND,
        icon_color=C.ACCENT_AMBER,
        icon_size=20,
        tooltip="Retroceder 10 frames",
        on_click=lambda e: on_seek(10),
        padding=2,
    )
    btn_prev1 = ft.IconButton(
        icon=ft.Icons.SKIP_PREVIOUS,
        icon_color=C.ACCENT_AMBER,
        icon_size=20,
        tooltip="Retroceder 1 frame",
        on_click=lambda e: on_seek(1),
        padding=2,
    )
    btn_next1 = ft.IconButton(
        icon=ft.Icons.SKIP_NEXT,
        icon_color=C.ACCENT_CYAN,
        icon_size=20,
        tooltip="Avanzar 1 frame",
        on_click=lambda e: on_seek(-1),
        padding=2,
    )
    btn_next10 = ft.IconButton(
        icon=ft.Icons.FAST_FORWARD,
        icon_color=C.ACCENT_CYAN,
        icon_size=20,
        tooltip="Avanzar 10 frames",
        on_click=lambda e: on_seek(-10),
        padding=2,
    )
    btn_latest = ft.IconButton(
        icon=ft.Icons.LAST_PAGE,
        icon_color=C.ACCENT_GREEN,
        icon_size=20,
        tooltip="Ir al frame más reciente",
        on_click=lambda e: on_seek(-9999),
        padding=2,
    )
    
    def do_export(e, fmt):
        from ui.charts import export_active_chart
        path, err = export_active_chart(fmt)
        if err:
            sb = ft.SnackBar(ft.Text(err, color="#FFFFFF"), bgcolor=C.ACCENT_RED)
        else:
            def open_file(ev):
                try:
                    os.startfile(path)
                except Exception as ex:
                    print(f"Error abriendo archivo: {ex}")
            sb = ft.SnackBar(
                content=ft.Text(f"Exportado: {path}", color="#FFFFFF"),
                bgcolor=C.ACCENT_GREEN,
                action="ABRIR ARCHIVO",
                on_action=open_file
            )
        page = e.control.page
        page.overlay.append(sb)
        sb.open = True
        page.update()

        # Desaparecer naturalmente tras 4 segundos de forma compatible
        import threading
        import time
        def auto_close():
            time.sleep(4.0)
            try:
                sb.open = False
                page.update()
            except:
                pass
        threading.Thread(target=auto_close, daemon=True).start()

    btn_export_png = ft.IconButton(
        icon=ft.Icons.IMAGE,
        icon_color=C.TEXT_MAIN,
        icon_size=20,
        tooltip="Exportar Vista Actual (PNG)",
        on_click=lambda e: do_export(e, "png"),
        padding=2,
    )
    btn_export_pdf = ft.IconButton(
        icon=ft.Icons.PICTURE_AS_PDF,
        icon_color=ft.Colors.RED_300,
        icon_size=20,
        tooltip="Exportar Vista Actual (PDF Vectorial)",
        on_click=lambda e: do_export(e, "pdf"),
        padding=2,
    )

    seek_panel = ft.Container(
        content=ft.Row(
            [
                ft.Text("◀ REVIEW:", color=C.TEXT_MUTED, size=10, italic=True),
                btn_prev10,
                btn_prev1,
                frame_lbl,
                btn_next1,
                btn_next10,
                btn_latest,
                ft.Container(width=10), # Separador
                btn_export_png,
                btn_export_pdf,
            ],
            spacing=2,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        bgcolor=C.PANEL_BG,
        border=ft.Border(
            left=ft.BorderSide(2, C.ACCENT_AMBER),
            right=ft.BorderSide(1, C.BORDER_COL),
            top=ft.BorderSide(1, C.BORDER_COL),
            bottom=ft.BorderSide(1, C.BORDER_COL),
        ),
        border_radius=6,
        padding=ft.Padding(left=8, top=4, right=8, bottom=4),
        visible=False,
    )

    # ── Botón de grabación IQ ───────────────────────────────────────────────
    rec_lbl = ft.Text("", color=C.ACCENT_RED, size=11, weight=ft.FontWeight.W_700, visible=False)
    rec_btn = ft.ElevatedButton(
        content=ft.Row(
            [ft.Text("⏺", size=13), ft.Text("REC", color="#FFFFFF", weight=ft.FontWeight.BOLD, size=12)],
            spacing=4,
            tight=True,
        ),
        bgcolor="#8B0000",
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)),
        tooltip="Grabar IQ del hardware a disco (solo modo SDR)",
        visible=False,  # Se muestra solo en SDR
    )

    def on_rec_click(e):
        if engine_instance.stream_mode != "sdr":
            return
        if not _rec_state[0]:
            path = engine_instance.start_iq_recording()
            if path:
                _rec_state[0] = True
                rec_btn.bgcolor = C.ACCENT_RED
                rec_btn.content.controls[0].value = "⏹"
                rec_btn.content.controls[1].value = "STOP REC"
                rec_lbl.value = "● REC"
                rec_lbl.visible = True
                sb = ft.SnackBar(ft.Text(f"🔴 Grabando en: {path}", color="#fff"), bgcolor="#8B0000")
                e.control.page.overlay.append(sb)
                sb.open = True
        else:
            path = engine_instance.stop_iq_recording()
            _rec_state[0] = False
            rec_btn.bgcolor = "#8B0000"
            rec_btn.content.controls[0].value = "⏺"
            rec_btn.content.controls[1].value = "REC"
            rec_lbl.visible = False
            if path:
                sb = ft.SnackBar(ft.Text(f"✅ Archivo guardado: {path}", color="#fff"), bgcolor=C.ACCENT_GREEN)
                e.control.page.overlay.append(sb)
                sb.open = True
        e.control.page.update()

    rec_btn.on_click = on_rec_click

    # ── Helpers de estado de UI ─────────────────────────────────────────────
    def _set_playing_ui():
        _state[0] = "playing"
        play_btn.content.value = "⏸ Pausar"
        play_btn.bgcolor = C.ACCENT_AMBER
        sdr_dot.color = C.ACCENT_AMBER
        sdr_lbl.value = "Streaming Activo..."
        sdr_lbl.color = C.ACCENT_AMBER
        seek_panel.visible = False
        frame_lbl.visible = False
        # Mostrar botón REC solo en modo SDR
        rec_btn.visible = (engine_instance.stream_mode == "sdr")

    def _set_paused_ui():
        _state[0] = "paused"
        play_btn.content.value = "▶ Reanudar"
        play_btn.bgcolor = C.ACCENT_GREEN
        sdr_dot.color = C.ACCENT_AMBER
        sdr_lbl.value = "⏸"
        sdr_lbl.color = C.ACCENT_AMBER
        # Mostrar controles de review solo si hay historial
        has_frames = len(engine_instance._frame_snapshots) > 0
        seek_panel.visible = has_frames
        frame_lbl.visible = has_frames
        if has_frames:
            _update_frame_label()

    def _set_stopped_ui():
        _state[0] = "stopped"
        engine_instance.is_paused = False
        play_btn.content.value = "▶ Iniciar Adquisición"
        play_btn.bgcolor = C.ACCENT_GREEN
        sdr_dot.color = C.ACCENT_RED
        sdr_lbl.value = "Estado Actual: Detenido"
        sdr_lbl.color = C.ACCENT_RED
        timer_lbl.value = ""
        seek_panel.visible = False
        frame_lbl.visible = False
        # Ocultar REC al detenerse
        rec_btn.visible = False
        rec_lbl.visible = False
        # Si quedó grabando, resetear estado visual
        if _rec_state[0]:
            _rec_state[0] = False
            rec_btn.bgcolor = "#8B0000"
            rec_btn.content.controls[0].value = "⏺"
            rec_btn.content.controls[1].value = "REC"

    # ── Lógica del botón principal ──────────────────────────────────────────
    def on_play_pause(e):
        if _state[0] == "stopped":
            # ▶ Iniciar desde cero
            if engine_instance.stream_mode == 'file':
                path = engine_instance.iq_filename
                if not os.path.exists(path):
                    page.snack_bar = ft.SnackBar(
                        ft.Text(f"⚠ Archivo no encontrado en: {path}", color="#fff"),
                        bgcolor=C.ACCENT_RED,
                    )
                    page.snack_bar.open = True
                    page.update()
                    return
                engine_instance.start_stream('file', {'filename': path, 'format': engine_instance.iq_format})
            else:
                engine_instance.start_stream('sdr', {})
            _set_playing_ui()

        elif _state[0] == "playing":
            # ⏸ Pausar
            engine_instance.is_paused = True
            engine_instance.is_playing = False
            _set_paused_ui()

        elif _state[0] == "paused":
            # ▶ Reanudar desde el punto actual (incluyendo seek)
            engine_instance.is_paused = False
            engine_instance.exit_review_mode()
            if engine_instance.stream_mode == 'file':
                path = engine_instance.iq_filename
                engine_instance.start_stream('file', {'filename': path, 'format': engine_instance.iq_format})
            else:
                # SDR: volver al tiempo real, descartar historial de review
                engine_instance._frame_snapshots.clear()
                engine_instance.start_stream('sdr', {})
            _set_playing_ui()

        page.update()

    # ── PubSub para mensajes del motor DSP ──────────────────────────────────
    async def on_header_msg(msg):
        if msg == "stream_stopped":
            _set_stopped_ui()
            page.update()
        elif msg == "toggle_stream":
            on_play_pause(None)
        elif msg == "emergency_stop":
            on_emergency(None)
        elif msg == "update_frame_label":
            _update_frame_label()
        elif msg == "refresh_charts":
            header_title.value = f"Frecuencia : {engine_instance.center_freq} MHz"
            header_title.update()

            if engine_instance.stream_mode == "file":
                if getattr(engine_instance, "metadata_updated", False):
                    engine_instance.metadata_updated = False
                    page.pubsub.send_all("refresh_charts")
                c = engine_instance.current_file_time
                t = engine_instance.total_file_time
                timer_lbl.value = f"⏱ {c:.1f}s / {t:.1f}s"
                timer_lbl.update()

    page.pubsub.subscribe(on_header_msg)

    # ── Botón de Emergencia (Stop total) ────────────────────────────────────
    def on_emergency(e):
        engine_instance.stop_stream()
        _set_stopped_ui()
        sb = ft.SnackBar(
            content=ft.Text(
                "⛔  EMERGENCIA: Todos los hilos DSP han sido abortados.",
                color="#FFFFFF",
                weight=ft.FontWeight.BOLD,
            ),
            bgcolor=C.ACCENT_RED,
        )
        page.overlay.append(sb)
        sb.open = True
        page.update()

    emg_btn = ft.ElevatedButton(
        content=ft.Text("⛔  Stop", color="#FFFFFF", weight=ft.FontWeight.BOLD),
        bgcolor=C.ACCENT_RED,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)),
        on_click=on_emergency,
    )

    return ft.Container(
        bgcolor=C.PANEL_BG,
        border=ft.Border(bottom=ft.BorderSide(1, C.BORDER_COL)),
        padding=ft.Padding(left=20, top=10, right=20, bottom=10),
        content=ft.Row(
            [
                ft.Icon(ft.Icons.WIFI_TETHERING, color=C.ACCENT_CYAN, size=26),
                ft.Text(
                    "Procesamiento DSP —",
                    color=C.TEXT_MAIN,
                    size=15,
                    weight=ft.FontWeight.BOLD,
                ),
                header_title,
                ft.Row([sdr_dot, sdr_lbl], spacing=5, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ft.Container(width=16),
                timer_lbl,
                ft.Container(width=6),
                seek_panel,
                ft.Container(width=6),
                rec_btn,
                rec_lbl,
                play_btn,
                emg_btn,
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=12,
        ),
    )


def build_footer() -> ft.Control:
    from datetime import datetime
    now_str = datetime.now().strftime("%Y-%m-%d  %H:%M %Z").strip()
    return ft.Container(
        bgcolor=C.PANEL_BG,
        border=ft.Border(top=ft.BorderSide(1, C.BORDER_COL)),
        padding=ft.Padding(left=20, top=6, right=20, bottom=6),
        content=ft.Row(
            [
                ft.Text("UIC Radiotelescopio  •  v2.1.1",         color=C.TEXT_MUTED, size=10),
                ft.Text("•",                                        color=C.BORDER_COL, size=10),
                ft.Text("Signal Hound BB60C",   color=C.TEXT_MUTED, size=10),
                ft.Container(expand=True),
                ft.Text(now_str,                                    color=C.TEXT_MUTED, size=10),
            ],
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )
