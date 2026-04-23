"""
tabs/signal_analysis.py
Pestaña "Potencia vs. Tiempo" — rolling buffer dBFS con marcador de piso de ruido.
"""

import asyncio
import flet as ft
from core.constants import *
from ui.charts import chart_power_time
from ui.components.shared import panel, border_all


def build_signal_analysis(page: ft.Page, key_state: dict) -> ft.Control:
    from core.dsp_engine import engine_instance
    import numpy as np

    img = ft.Image(src=chart_power_time(), fit=ft.BoxFit.CONTAIN,
                   gapless_playback=True, border_radius=10, expand=True)

    # ── Métricas ─────────────────────────────────────────────────────────────
    val_pwr_now   = ft.Text("—", color=ACCENT_AMBER, size=13,
                             weight=ft.FontWeight.W_600)
    val_pwr_max   = ft.Text("—", color=ACCENT_RED, size=12)
    val_pwr_min   = ft.Text("—", color=ACCENT_GREEN, size=12)
    val_pwr_avg   = ft.Text("—", color=TEXT_MAIN, size=12)
    val_noise_fl  = ft.Text("—", color=TEXT_MUTED, size=12)
    val_pwr_range = ft.Text("—", color=TEXT_MUTED, size=11)

    is_rendering = [False]

    async def on_refresh(msg):
        if msg != "refresh_charts":
            return
        if engine_instance.active_tab != 4: return # Solo renderizar si es la pestaña activa
        
        if is_rendering[0]:
            return
        is_rendering[0] = True
        try:
            pwr_b64 = await asyncio.to_thread(chart_power_time)
            img.src = pwr_b64
            
            # Actualizar todo junto con validación de seguridad
            for w in [img, val_pwr_now, val_pwr_max, val_pwr_min,
                      val_pwr_avg, val_noise_fl, val_pwr_range]:
                if w.page: w.update()

            written = engine_instance.power_samples_written
            data_pwr = engine_instance.power_time_data
            d_len = len(data_pwr)

            if written == 0:
                p_active = np.array([-100.0])
                current_pwr = -100.0
            elif written < d_len:
                p_active = data_pwr[:written]
                current_pwr = float(p_active[-1])
            else:
                p_active = data_pwr
                current_pwr = float(data_pwr[(written - 1) % d_len])

            noise_fl = float(np.median(p_active))
            val_pwr_now.value   = f"{current_pwr:.2f} dBFS"
            val_pwr_max.value   = f"{float(np.max(p_active)):.2f} dBFS"
            val_pwr_min.value   = f"{float(np.min(p_active)):.2f} dBFS"
            val_pwr_avg.value   = f"{float(np.mean(p_active)):.2f} dBFS"
            val_noise_fl.value  = f"{noise_fl:.2f} dBFS"

            cfg = engine_instance.charts_config.get("pow_time", {})
            val_pwr_range.value = (f"{cfg.get('ymin', 0):.0f} → "
                                   f"{cfg.get('ymax', 0):.0f} dBFS")

            # (Combinado en el bloque anterior)
        finally:
            is_rendering[0] = False

    page.pubsub.subscribe(on_refresh)

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

    def stat_row(label, val_widget):
        return ft.Row([
            ft.Text(label, color=TEXT_MUTED, size=11, expand=1),
            val_widget,
        ])

    side = panel(
        width=250,
        padding_val=14,
        content=ft.Column([
            ft.Text("⚡  Potencia en Tiempo Real", color=ACCENT_CYAN, size=14,
                    weight=ft.FontWeight.BOLD),
            ft.Divider(color=BORDER_COL, height=10),
            ft.Text("Potencia actual:", color=TEXT_MUTED, size=10),
            ft.Container(content=val_pwr_now, padding=ft.Padding(left=2, top=0, right=0, bottom=8)),
            ft.Divider(color=BORDER_COL, height=8),
            ft.Text("📊  Estadísticas del buffer", color=ACCENT_CYAN, size=12,
                    weight=ft.FontWeight.BOLD),
            stat_row("Máximo:", val_pwr_max),
            stat_row("Mínimo:", val_pwr_min),
            stat_row("Promedio:", val_pwr_avg),
            stat_row("Piso ruido (med.):", val_noise_fl),
            stat_row("Rango Y activo:", val_pwr_range),
            ft.Divider(color=BORDER_COL, height=10),
            ft.Text(
                "El buffer muestra las últimas 2000\n"
                "mediciones de potencia promedio.\n\n"
                "Ctrl+Scroll → zoom Y\n"
                "Shift+Scroll → zoom X",
                color=TEXT_MUTED, size=9, italic=True,
            ),
        ], spacing=8),
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
