---
type: concept
tags: [uic, radiotelescopio, reference, development]
created: 2026-04-21
sources: [core/dsp_engine.py, core/advanced_dsp.py, ui/charts.py]
---

# Referencia de Funciones y Módulos

Este documento mapea la estructura modular del proyecto, vinculando cada función principal con su rol técnico y la formulación matemática que implementa.

## 1. Núcleo de Procesamiento (`core/`)

| Función | Ubicación | Descripción Técnica | Fórmula Relacionada |
| :--- | :--- | :--- | :--- |
| `_process_dsp_core` | `dsp_engine.py` | Orquestador del flujo de señal. Realiza el MA filtering y FFT. | Flujo de Señal (Mermaid) |
| `fast_ma` | `dsp_engine.py` | Implementación $O(N)$ del filtro de media móvil. | Suma Acumulada |
| `run_welch` | `advanced_dsp.py` | Estimación de PSD mediante segmentos solapados. | [[DSP_Implementation#3-método-de-welch-periodograma-promediado\|Welch PSD]] |
| `run_ar_burg` | `advanced_dsp.py` | Modelo AR de alta resolución. | [[DSP_Implementation#1-modelo-autorregresivo-burg\|Burg Error Minimization]] |
| `run_pseudo_music`| `advanced_dsp.py` | Localización de fuentes en sub-espacio de ruido. | [[DSP_Implementation#2-pseudo-music\|MUSIC Pseudospectrum]] |

## 2. Visualización y Gráficas (`ui/`)

| Función | Ubicación | Descripción Técnica | Vínculo de Datos || `chart_power_time`| `charts.py` | Renderiza el historial de potencia dBFS. | `pow_time` buffer |
| `bb_open_device` | `bb_api.py` | Inicializa la conexión con el hardware BB60C. | `handle` del dispositivo |
| `build_statistics`| `statistics.py` | Panel de análisis de Kurtosis/Sesgo + Smart Trigger. | `histogram_data` |
| `on_zoom_scroll` | `monitoring.py` | Lógica de zoom dinámico (Ctrl/Shift + Mouse). | `charts_config` state |
| :--- | :--- | :--- | :--- |
| `chart_power_time` | `charts.py` | Renderiza el historial de potencia dBFS. | `pow_time` buffer |
| `bb_open_device` | `bb_api.py` | Inicializa la conexión con el hardware BB60C. | `handle` del dispositivo |
| `build_statistics` | `statistics.py` | Panel de análisis de Kurtosis/Sesgo + Smart Trigger. | `histogram_data` |
| `on_zoom_scroll` | `monitoring.py` | Lógica de zoom dinámico (Ctrl/Shift + Mouse). | `charts_config` state |
| `get_cached_fig` | `charts.py` | Gestiona el `ChartCache` para evitar fugas de memoria. | Figura Matplotlib |
| `chart_spectrum` | `charts.py` | Renderiza la FFT filtrada en tiempo real. | `engine.spectrum_data` |
| `chart_spectrogram`| `charts.py` | Renderiza el waterfall 2D (imshow). | `engine.waterfall_data` |
| `chart_histogram` | `charts.py` | Calcula el histograma y ajusta curva Gaussiana. | `engine.histogram_data` |

## 3. Componentes de Interfaz (Tabs)

El proyecto sigue un patrón **Modular de Pestañas**, donde cada archivo en `ui/tabs/` es independiente:
- `monitoring.py`: Pestaña 1 (RAW). Se suscribe a `pubsub` para refrescos asíncronos.
- `monitoring_filtered.py`: Pestaña 2 (MA Filtered).
- `spectrogram.py`: Pestaña 3 (Cascada 2D).
- `statistics.py`: Pestaña 4 (Análisis Probabilístico).

## Resumen de la Forma Modular
1. **Separación de Concernimientos**: El `DSPEngine` no sabe nada de Flet; solo llena buffers de NumPy.
2. **Puente Base64**: `charts.py` actúa como puente, convirtiendo matrices de NumPy en strings Base64 que Flet puede mostrar.
3. **Sincronización Asíncrona**: El loop principal en `main.py` usa `asyncio` para notificar a todas las pestañas activas que deben refrescar sus imágenes.
