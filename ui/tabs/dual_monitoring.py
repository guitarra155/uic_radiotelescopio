"""
tabs/dual_monitoring.py
Pestaña Dual — Comparación de Señal Original vs. Filtrada.
Sirve como contenedor para la ventana superpuesta OpenGL de PyQtGraph.
"""

import flet as ft
import core.constants as C
import socket

def build_dual_monitoring(page: ft.Page, key_state: dict) -> ft.Control:
    
    # Enviar comando de mostrar al iniciar la pestaña
    def send_show_cmd():
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.sendto(b"cmd:show", ("127.0.0.1", 9999))
        except:
            pass

    # Sintonizar el cambio de pestaña para ocultar el overlay si cambiamos de tab
    def on_tab_changed(msg):
        from core.dsp_engine import engine_instance
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            if engine_instance.active_tab == 1:
                s.sendto(b"cmd:show", ("127.0.0.1", 9999))
            else:
                s.sendto(b"cmd:hide", ("127.0.0.1", 9999))
        except:
            pass

    # Suscribirse al evento de cambio de pestaña
    page.pubsub.subscribe(on_tab_changed)

    # Lanzar el monitor externo que se superpone automáticamente
    from ui.qt_monitor import launch_gpu_monitor
    launch_gpu_monitor()
    send_show_cmd()

    return ft.Container(
        bgcolor=C.DARK_BG,
        expand=True,
        padding=0
    )
