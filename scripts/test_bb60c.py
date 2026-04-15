import sys
import os

# Añadir el path para encontrar core.bbdevice
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

try:
    from core.bbdevice.bb_api import *
    print("OK: API de Signal Hound cargada correctamente.")
    
    # Intentar obtener versión de la API
    ver = bb_get_API_version()["api_version"]
    print(f"Versión de la API: {ver.decode()}")
    
    # Listar dispositivos conectados
    res = bb_get_serial_number_list()
    if res["status"] == 0:
        count = res["device_count"].value
        print(f"Dispositivos detectados: {count}")
        if count > 0:
            for i in range(count):
                print(f" - Serial: {res['serials'][i]}")
    else:
        print(f"Estatus de búsqueda de dispositivos: {res['status']}")

except Exception as e:
    print(f"❌ Error al cargar la API o detectar hardware: {e}")
