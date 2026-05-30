# DETALLE DEL PROYECTO: Plataforma DSP - Radiotelescopio UIC

## 1. Arquitectura del Sistema
El proyecto es una plataforma avanzada de Procesamiento Digital de Señales (DSP) para un radiotelescopio. 
La arquitectura se divide en dos hilos principales:
- **Backend (DSP Engine):** Procesamiento en segundo plano (`core/dsp_engine.py`) utilizando NumPy y SciPy para realizar operaciones de cálculo intensivo (FFT, filtros MA, estimación PSD de Welch, MUSIC, AR/Burg). Puede obtener datos en tiempo real mediante un SDR (Signal Hound BB60C) o desde archivos de muestras (IQ).
- **Frontend (UI Flet + Matplotlib):** La interfaz de usuario (`main.py`, `ui/tabs/`) está construida con Flet (Flutter para Python). Las gráficas son renderizadas mediante Matplotlib usando el backend `Agg` de alta velocidad sin UI. Se exportan como base64 SVG para una inserción vectorial rápida y nítida en Flet (`ui/charts.py`).

## 2. Flujo de Funcionamiento
1. **Adquisición de Datos:** La clase `DSPEngine` adquiere bloques IQ y los almacena en buffers circulares, aplicando recortes de "Smart Trigger" si detecta eventos de alta energía.
2. **Procesamiento de Señal (DSP):** 
   - La señal en crudo (RAW) se almacena para su visualización.
   - Se aplica un filtro de promedio móvil (Moving Average) ajustable para suavizar ruido.
   - Se procesan estimaciones de espectro (FFT normal o Welch) tanto de la señal cruda como la filtrada.
   - Se calculan métricas derivadas: SNR, potencia vs. tiempo e histogramas estadísticos.
3. **Representación Visual (Auto-escala):** Cada gráfica tiene un diccionario de configuración de límites (`xmin`, `xmax`, `ymin`, `ymax`) que se recalcula automáticamente basado en la desviación y máximos absolutos de la señal (`_auto_detect_ranges`), permitiendo que el radiotelescopio se mantenga siempre dentro de una escala visible.
4. **Renderizado Reactivo:** Flet notifica a través de su sistema de publicación/suscripción (`pubsub`) cuando se debe actualizar una gráfica.

## 3. Modularización y Dependencias
- `main.py`: Punto de entrada, layout principal, barras de navegación y gestión global del ciclo de eventos Flet.
- `core/dsp_engine.py`: Núcleo de las matemáticas de señal. Configura el SDR, procesa buffers, detecta SNR e identifica picos o señales de interés.
- `ui/charts.py`: Singleton con caché gráfica para mantener `Figure` y `Axes` instanciados y evitar sobrecarga de memoria al redibujar a altas tasas de refresco.
- `ui/tabs/`: Archivos para cada pestaña del sistema (Monitoring, Espectrograma, Análisis de Señal SNR, Algoritmos avanzados).
- **Dependencias principales:** `flet`, `numpy`, `scipy`, `matplotlib`, `bb_api` (API local para Signal Hound).

## Últimos Cambios (Actualización Reciente)
- Corrección de la autoescala de las gráficas de Amplitud (RAW y Filtrada) dentro de `dsp_engine.py`. Se ajustaron los límites `ymin` y `ymax` para que sean simétricos alrededor del 0 (`[-a_max * 1.2, a_max * 1.2]`), dado que la envolvente de la señal real/imaginaria es bipolar (valores negativos y positivos) y la magnitud (`np.abs`) era forzada a límites que truncaban la parte negativa de la gráfica, mostrándola desde 0 hacia arriba, como un rectificador de onda.
