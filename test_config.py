import flet as ft
from ui.tabs.sdr_config import build_config

class DummyEngine:
    active_tab = 1
    raw_mode = False
    ma_enabled = False
    moving_avg_samples = 5
    rfi_last_time = "N/A"
    rfi_event_count = 0
    sync_active = False
    charts_config = {
        "mon_raw_spec": {},
        "mon_raw_amp": {},
        "mon_filt_spec": {},
        "mon_filt_amp": {},
    }
    def save_config(self): pass

import core.dsp_engine
core.dsp_engine.engine_instance = DummyEngine()

def main(page: ft.Page):
    try:
        build_config(page)
        # trigger tab change
        page.pubsub.send_all_on_connections = lambda *args: None
        
        # We must call render_panel directly to see the exception
        # Actually, let's just inspect the module
        from ui.tabs.sdr_config import _live_fields
        import asyncio
    except Exception as e:
        import traceback
        traceback.print_exc()

ft.app(target=main)
