import re

with open(r"c:\uic_radiotelescopio\ui\tabs\sdr_config.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Add _live_fields = {} before build_axis_group
if "_live_fields =" not in content:
    content = content.replace("    def build_axis_group(title, chart_id):", "    _live_fields = {}\n\n    def build_axis_group(title, chart_id):")

# 2. Modify build_axis_group to use tf_ variables and add to _live_fields
build_axis_new = """    def build_axis_group(title, chart_id):
        cfg = engine_instance.charts_config.get(chart_id, {})
        
        def toggle_auto(e, axis):
            cfg[f"auto_{axis}"] = not cfg.get(f"auto_{axis}", True)
            engine_instance.save_config()
            on_ui_event(e)

        def set_val(e, axis, key):
            try:
                val = float(e.control.value)
                cfg[key] = val
                cfg[f"auto_{axis}"] = False
                engine_instance.save_config()
                on_ui_event(e)
            except: pass

        tf_xmin = make_input(f"{cfg.get('xmin', 0):.8f}", lambda e: set_val(e, "x", "xmin"))
        tf_xmax = make_input(f"{cfg.get('xmax', 0):.8f}", lambda e: set_val(e, "x", "xmax"))
        tf_ymin = make_input(f"{cfg.get('ymin', 0):.8f}", lambda e: set_val(e, "y", "ymin"))
        tf_ymax = make_input(f"{cfg.get('ymax', 0):.8f}", lambda e: set_val(e, "y", "ymax"))
        
        _live_fields[chart_id] = {"xmin": tf_xmin, "xmax": tf_xmax, "ymin": tf_ymin, "ymax": tf_ymax, "cfg_key": chart_id}

        return ft.Column([
            ft.Text(f"📊 {title}", color=ACCENT_CYAN, size=12, weight=ft.FontWeight.BOLD),
            row("Auto Eje X", make_toggle(cfg.get("auto_x"), lambda e: toggle_auto(e, "x"))),
            row("X Mín", tf_xmin),
            row("X Máx", tf_xmax),
            ft.Container(height=5),
            row("Auto Eje Y", make_toggle(cfg.get("auto_y"), lambda e: toggle_auto(e, "y"))),
            row("Y Mín", tf_ymin),
            row("Y Máx", tf_ymax),
            ft.Divider(height=20, color="#303030")
        ], spacing=2)"""

content = re.sub(r'    def build_axis_group\(title, chart_id\):.*?\], spacing=2\)', build_axis_new, content, flags=re.DOTALL)

# 3. Add _live_fields.clear() to render_panel()
if "_live_fields.clear()" not in content:
    content = content.replace('    def render_panel():\n        """Genera la estructura de controles. Solo se llama al cambiar de pestaña."""\n        idx = engine_instance.active_tab', '    def render_panel():\n        """Genera la estructura de controles. Solo se llama al cambiar de pestaña."""\n        _live_fields.clear()\n        idx = engine_instance.active_tab')

# 4. Modify idx == 2 block
idx_2_old = """        elif idx == 2:
            cfg_spec = engine_instance.charts_config.get("spec_wf", {})
            tab_content = ft.Column([
                ft.Text("📊 Espectrograma 2D", color=ACCENT_CYAN, size=12, weight=ft.FontWeight.BOLD),
                row("Auto Eje X", make_toggle(cfg_spec.get("auto_x", True),
                    lambda e: (cfg_spec.update({"auto_x": not cfg_spec.get("auto_x", True)}), engine_instance.save_config(), on_ui_event(e)))),
                row("X Mín (MHz)", make_input(f"{cfg_spec.get('xmin', 1419.0):.5f}",
                    lambda e: (cfg_spec.update({"xmin": float(e.control.value), "auto_x": False}), engine_instance.save_config(), on_ui_event(e)))),
                row("X Máx (MHz)", make_input(f"{cfg_spec.get('xmax', 1421.0):.5f}",
                    lambda e: (cfg_spec.update({"xmax": float(e.control.value), "auto_x": False}), engine_instance.save_config(), on_ui_event(e)))),
                ft.Divider(height=5, color=BORDER_COL),
                row("Auto Color", make_toggle(cfg_spec.get("auto_y", True),
                    lambda e: (cfg_spec.update({"auto_y": not cfg_spec.get("auto_y", True)}), engine_instance.save_config(), on_ui_event(e)))),
                row("Color Mín", make_input(f"{cfg_spec.get('ymin', -100.0):.3f}",
                    lambda e: (cfg_spec.update({"ymin": float(e.control.value), "auto_y": False}), engine_instance.save_config(), on_ui_event(e)))),
                row("Color Máx", make_input(f"{cfg_spec.get('ymax', -20.0):.3f}",
                    lambda e: (cfg_spec.update({"ymax": float(e.control.value), "auto_y": False}), engine_instance.save_config(), on_ui_event(e)))),
            ])"""

idx_2_new = """        elif idx == 2:
            method_map = {
                "waterfall": "spec_wf",
                "cwt": "spec_cwt",
                "ar_burg_2d": "spec_ar",
                "correlogram_2d": "spec_corr"
            }
            active_method = getattr(engine_instance, "active_spec_method", "waterfall")
            cfg_key = method_map.get(active_method, "spec_wf")
            
            cfg_spec = engine_instance.charts_config.get(cfg_key)
            if not cfg_spec:
                cfg_spec = {"xmin": 1419.0, "xmax": 1421.0, "ymin": -100.0, "ymax": -20.0, "auto_x": False, "auto_y": True}
                engine_instance.charts_config[cfg_key] = cfg_spec

            def toggle_auto(e, axis):
                cfg_spec[f"auto_{axis}"] = not cfg_spec.get(f"auto_{axis}", True)
                engine_instance.save_config()
                on_ui_event(e)

            def set_val(e, axis, key):
                try:
                    val = float(e.control.value)
                    cfg_spec[key] = val
                    cfg_spec[f"auto_{axis}"] = False
                    engine_instance.save_config()
                    on_ui_event(e)
                except: pass

            tf_xmin = make_input(f"{cfg_spec.get('xmin', 1419.0):.5f}", lambda e: set_val(e, "x", "xmin"))
            tf_xmax = make_input(f"{cfg_spec.get('xmax', 1421.0):.5f}", lambda e: set_val(e, "x", "xmax"))
            tf_ymin = make_input(f"{cfg_spec.get('ymin', -100.0):.3f}", lambda e: set_val(e, "y", "ymin"))
            tf_ymax = make_input(f"{cfg_spec.get('ymax', -20.0):.3f}", lambda e: set_val(e, "y", "ymax"))
            
            _live_fields[cfg_key] = {"xmin": tf_xmin, "xmax": tf_xmax, "ymin": tf_ymin, "ymax": tf_ymax, "cfg_key": cfg_key}

            method_name = {"waterfall": "Waterfall FFT", "cwt": "CWT / Morlet", "ar_burg_2d": "AR / Burg 2D", "correlogram_2d": "Correlograma 2D"}.get(active_method, "Espectrograma 2D")

            tab_content = ft.Column([
                ft.Text(f"📊 {method_name}", color=ACCENT_CYAN, size=12, weight=ft.FontWeight.BOLD),
                row("Auto Eje X", make_toggle(cfg_spec.get("auto_x", True), lambda e: toggle_auto(e, "x"))),
                row("X Mín (MHz)", tf_xmin),
                row("X Máx (MHz)", tf_xmax),
                ft.Divider(height=5, color=BORDER_COL),
                row("Auto Color", make_toggle(cfg_spec.get("auto_y", True), lambda e: toggle_auto(e, "y"))),
                row("Color Mín", tf_ymin),
                row("Color Máx", tf_ymax),
            ])"""

content = content.replace(idx_2_old, idx_2_new)

# 5. Add _sync_auto_fields and modify _update_ui
sync_code = """    def _sync_auto_fields():
        updated = []
        for chart_id, fields in _live_fields.items():
            actual_key = fields.get("cfg_key", chart_id)
            cfg = engine_instance.charts_config.get(actual_key)
            if not cfg: continue
            pairs = [
                ("xmin", cfg.get("auto_x", False), f"{cfg.get('xmin', 0):.5f}"),
                ("xmax", cfg.get("auto_x", False), f"{cfg.get('xmax', 0):.5f}"),
                ("ymin", cfg.get("auto_y", False), f"{cfg.get('ymin', 0):.5f}"),
                ("ymax", cfg.get("auto_y", False), f"{cfg.get('ymax', 0):.5f}"),
            ]
            for key, is_auto, new_val in pairs:
                tf = fields.get(key)
                if tf and is_auto and tf.page:
                    try:
                        if tf.value != new_val:
                            tf.value = new_val
                            updated.append(tf)
                    except: pass
        for tf in updated:
            try: tf.update()
            except: pass

    # --- Suscripción a eventos ---
    async def _update_ui(msg):
        if msg == "tab_changed":
            render_panel()
            try: main_col.update()
            except: pass
        elif msg == "refresh_charts":
            if engine_instance.active_tab == 1:
                update_stats()
            _sync_auto_fields()"""

old_update_ui = """    # --- Suscripción a eventos ---
    async def _update_ui(msg):
        if msg == "tab_changed":
            render_panel()
            try: main_col.update()
            except: pass
        elif msg == "refresh_charts":
            # Si estamos en la pestaña dual, actualizar SOLO los textos dinámicos
            if engine_instance.active_tab == 1:
                update_stats()"""

content = content.replace(old_update_ui, sync_code)

with open(r"c:\uic_radiotelescopio\ui\tabs\sdr_config.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Done patching sdr_config.py!")
