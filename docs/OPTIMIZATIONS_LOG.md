# Referencia Técnica: Arquitectura y Optimizaciones

Este documento profundiza en la ingeniería detrás de la plataforma UIC Radiotelescopio, detallando las soluciones aplicadas a retos de alta tasa de datos.

## 1. Gestión de Datos de Alta Velocidad (40 MSps)
A 40 Millones de muestras por segundo (MSps), el BB60C genera aproximadamente **160 MB/s** de datos I/Q. 
- **Estrategia de Ráfagas**: El motor DSP no procesa muestra por muestra. Captura "chunks" de 1 segundo (40M de puntos), los procesa vectorialmente con NumPy y luego actualiza los buffers de visualización.
- **Diezmado Visual**: Para mantener la UI a 30 FPS sin colapsar, los buffers de amplitud se diezman de 40,000,000 a 2,000 puntos usando un paso dinámico (`step = len(iq) // 2000`). Esto permite ver la forma de onda global sin pérdida de información de envolvente.

## 2. Estabilización de la API de Signal Hound
La integración con `bb_api.dll` presentó retos de concurrencia y límites físicos:
- **Manejo de Warnings (Status 4 - Clamping)**: El BB60C aplica un recorte digital si el ancho de banda solicitado es muy cercano a la tasa de muestreo. Implementamos un filtro de estados donde los valores `> 0` se registran pero no interrumpen el flujo. Esto permite operar a los **27 MHz** máximos con total estabilidad.
- **Auto-Configuración en Cascada**: El comando `bb_configure_IQ` es precedido siempre por un `bb_abort` y seguido por un `bb_initiate`. Esta secuencia está protegida por un **Mutex (Lock)** global para evitar que ráfagas de comandos desde la UI saturen el buffer de comandos del hardware USB.

## 3. Inteligencia Espectral y Auto-Rango
- **Algoritmo de Centrado**: El sistema utiliza `np.argmax()` sobre el espectro suavizado para localizar la portadora más fuerte. Si el pico está dentro de un margen del 10% del centro, se considera una "señal de interés" y se activa el protocolo de centrado.
- **Sanitización de Visualización**: El error de los "cuadros blancos" fue identificado como una excepción de renderizado de la UI (Flet) ante números de punto flotante con precisión excesiva. La solución implementada aplica `round(val, 2)` en la capa de carga de datos (`load_config`), garantizando que la UI solo reciba strings compatibles.

## 4. Algoritmos de Análisis Avanzado
Además de la FFT estándar, la plataforma integra:
- **Welch PSD**: Reduce la varianza del ruido promediando periodogramas solapados. Esencial para ver la línea de hidrógeno oculta bajo el piso de ruido.
- **SNR en Tiempo Real**: Se calcula estimando el piso de ruido mediante el percentil 25 del espectro y restándolo de la potencia pico. Un SNR > 3dB activa automáticamente los indicadores de detección en el Header.
