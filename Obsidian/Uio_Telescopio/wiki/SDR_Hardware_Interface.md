---
type: concept
tags: [uic, radiotelescopio, hardware, bb60c]
created: 2026-04-21
sources: [core/bbdevice/bb_api.py, core/dsp_engine.py, raw/documentacion_completa_bb60c.md]
---

# Interfaz de Hardware: Signal Hound BB60C

La plataforma integra el receptor SDR **Signal Hound BB60C**, un analizador de espectro de alto rendimiento que ofrece un rango dinámico de 90 dB y un ancho de banda instantáneo de hasta 27 MHz calibrados.

## Especificaciones Técnicas (Deep Dive)
- **Rango de Frecuencia**: 9 kHz a 6.4 GHz (máximo API).
- **Sensibilidad (DANL)**: -158 dBm/Hz (típico a >10 MHz).
- **Rango Dinámico**: -158 dBm a +10 dBm.
- **Tasa de Datos**: Genera un flujo sostenido de hasta 140 MB/s vía USB 3.0 (80 M muestras IF/s).

## Arquitectura de Conexión
La integración se realiza mediante una capa de interoperabilidad entre Python (ctypes) y la librería dinámica nativa `bb_api.dll`.

### Funciones de Control Críticas (`bb_api.py`)
- **`bb_open_device`**: Inicializa el handle del hardware.
- **`bb_get_IQ_correction`**: Crucial para escalar los valores flotantes y obtener lecturas de potencia precisas en dBm.
- **`bb_set_power_state`**: Permite reducir el consumo de 6W a 1.25W en modo standby.

## Requisitos del Sistema
Para garantizar que no haya pérdida de muestras (sample loss) durante la observación astronómica:
- **CPU**: Intel Core i7 (4ta gen o superior recomendado).
- **Bus**: Controlador USB 3.0 nativo (se requiere cable en "Y" para alimentación auxiliar).
- **Almacenamiento**: SSD capaz de sostener >250 MB/s si se activa la grabación continua.

## Protección de Hardware
El sistema implementa mecanismos de seguridad activa:
1. **Detección de Saturación**: El loop `_process_sdr_loop` monitorea el bit de overflow del hardware. **Límite absoluto de entrada: +20 dBm.**
2. **Clamping Digital**: Si la señal excede los límites seguros, el motor alerta visualmente mediante el indicador "⚠️ ADC OVERFLOW" en la pestaña de configuración.

## Modos de Operación
- **BB_STREAMING**: Modo nativo para captura continua de muestras IQ.
- **Modo Offline**: Simulación bit-a-bit utilizando archivos binarios `.iq` con el mismo formato que el hardware real (`complex64`).
