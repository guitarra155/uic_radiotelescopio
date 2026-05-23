import glob

for f in glob.glob('c:/uic_radiotelescopio/ui/tabs/*.py'):
    with open(f, 'r', encoding='utf-8') as file:
        content = file.read()
        
    old_str = 'e.control.page.pubsub.send_all("toggle_fullscreen_chart")'
    new_str = 'e.control.icon = ft.Icons.CLOSE_FULLSCREEN if engine_instance.chart_fullscreen_active else ft.Icons.ASPECT_RATIO\n        e.control.page.pubsub.send_all("toggle_fullscreen_chart")'
    
    if old_str in content and 'e.control.icon = ft.Icons.CLOSE_FULLSCREEN' not in content:
        content = content.replace(old_str, new_str)
        with open(f, 'w', encoding='utf-8') as file:
            file.write(content)
            print(f"Updated {f}")
