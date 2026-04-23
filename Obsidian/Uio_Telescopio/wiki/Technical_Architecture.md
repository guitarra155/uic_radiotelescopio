---
type: summary
tags: [uic, radiotelescopio, architecture, technical]
created: 2026-04-21
sources: [main.py, core/dsp_engine.py, ui/charts.py]
---

# Arquitectura Técnica de la Plataforma

La plataforma está construida íntegramente en **Python**, utilizando una arquitectura modular de tres capas (Adquisición, Procesamiento, Visualización) sobre el framework **Flet**.

## 1. Capa de Adquisición (Hardware/Virtual)
Gestionada por `DSPEngine` en `core/dsp_engine.py`:
- **Modo Real**: Comunicación con el SDR **Signal Hound BB60C** mediante el módulo `core/bbdevice/`. Permite configurar frecuencia central, nivel de referencia, ganancia y diezmado (hasta 40 MS/s).
- **Modo Offline**: Reproducción de archivos `.iq` (formatos uint8, int8 y complex64) simulando una captura en tiempo real con control de velocidad (`playback_speed`).

## 2. Capa de Procesamiento (DSP Core)
El motor principal (`DSPEngine`) orquesta el flujo de datos:
- **Filtrado RFI**: Implementa un filtro de **Media Móvil (Moving Average)** ultra-rápido basado en sumas acumuladas para suavizar interferencias temporales.
- **Estimación Espectral**: 
    - **Modo Real-time**: Basado en FFT estándar con ventana de Hanning.
    - **Modo Post-procesado/Smooth**: Utiliza el método de **Welch** para periodogramas promediados.
- **Buffers de Estado**: Mantiene buffers circulares de potencia (dBFS), espectrograma (waterfall), histograma y SNR por bin de frecuencia.

## 3. Capa de Visualización (GUI)
Interfaz de usuario dinámica construida con **Flet**:
- **Dashboards**: Organizados en pestañas (Monitero RAW, Monitoreo Filtrado, Espectrograma, Estadística, etc.).
- **Gráficas**: Implementadas en `ui/charts.py`, que renderizan en tiempo real los buffers del `engine_instance`.
- **Auto-escala**: Algoritmos de detección inteligente de rangos (Y-axis) que se ajustan cada 30 frames para mantener la señal siempre visible.

## 4. Patrones de Diseño Modulares
El proyecto utiliza varios patrones para mantener la escalabilidad y el rendimiento:
- **Singleton (Engine Instance)**: `engine_instance` centraliza el estado del DSP para que sea accesible desde cualquier pestaña de la UI sin redundancia de datos.
- **Caché de Gráficas**: Evita la recreación costosa de objetos Matplotlib, actualizando solo los datos de los "Artist" existentes.
- **PubSub (Publicador/Suscriptor)**: Las pestañas en `ui/tabs/` se suscriben al canal `refresh_charts`, permitiendo una arquitectura desacoplada donde el motor no necesita conocer los detalles de la interfaz.

## Interfaz de Hardware (SDR)
La comunicación con el **Signal Hound BB60C** se realiza mediante un envoltorio de la API BB en C++ (`core/bbdevice/bb_api.py`).
- **Control de Ganancia**: Implementa `bb_configure_gain_atten` para prevenir la saturación del ADC ante señales terrestres fuertes.
- **Streaming IQ**: Utiliza `bb_get_IQ_unpacked` para extraer ráfagas de datos en crudo (In-phase & Quadrature) a una tasa de 40 MS/s.

## Mapeo Funcional
Para un detalle de cada función y su fórmula matemática, consulta la **[[Function_Reference]]**.
