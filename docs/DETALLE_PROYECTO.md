# Documentación y Detalle del Proyecto: Plataforma DSP Radiotelescopio

## 1. ¿Qué es este proyecto?
Este proyecto es una **Plataforma de Procesamiento Digital de Señales (DSP)** diseñada para funcionar como un radiotelescopio en tiempo real. Su objetivo principal es detectar y analizar señales de radiofrecuencia provenientes del espacio o de barrido local (como la banda L, tradicionalmente usada para la frecuencia del Hidrógeno Neutro HI a 1420.405 MHz, aunque es configurable).
Opera convirtiendo las ondas de radio del espacio en gráficas visuales para que los científicos puedan estudiar la composición del universo o analizar interferencias y frecuencias a voluntad.

## 2. ¿Para qué sirve?
- **Observación Astronómica y Espectral**: Detectar radiación y perfilar el espectro en vivo.
- **Análisis de Señales**: Procesar millones de datos por segundo (hasta 40 millones de muestras) para separar las señales útiles del ruido o interferencias.
- **Visualización en Tiempo Real**: Mostrar espectrogramas (mapas de calor), distribuciones de magnitud y estadísticas instantáneas para entender las transmisiones.

---

## 3. Manual de Usuario (Paso a Paso)

### A. Preparación de los Equipos
- **Conectar el equipo**: Conecta el receptor SDR (BB60C o RTL-SDR) a tu computadora. Si usas el BB60C, asegúrate de conectar ambos extremos del cable USB "en Y" a puertos USB 3.0 de tu PC para que tenga suficiente energía.
- **Archivos de datos**: Si no tienes una antena conectada, puedes usar grabaciones previas en formato `.iq` o `.npy`.

### B. Iniciar la Observación
Abre el programa y ve a la pestaña **Configuración SDR**:
- **Origen de los datos (Source Mode)**: Elige `sdr` para captar señales en vivo o `file` para reproducir un archivo grabado.
- **Frecuencia Central**: Escribe la frecuencia de interés (ej. 1420.00 MHz).
- **Tasa de Muestreo (Sample Rate)**: Controla cuánta información se procesa. Usa 1.0 a 5.0 MSps para observaciones generales.
- **Nivel de Señal (Reference Level)**: Configúralo en -30 o -40 dBm, si aparece el aviso ADC OVERFLOW súbelo a -10 o 0 dBm.

### C. Entendiendo las Gráficas
- **Auto-Escala**: A la derecha de la pantalla verás botones de "Auto X" y "Auto Y". Mantenlos encendidos para que el programa ajuste el zoom dinámicamente y encuadre la señal y el ruido térmico de fondo.
- **Distribución de Magnitud (Histograma)**: Calcula automáticamente la presencia de la señal respecto al ruido. Si solo hay ruido térmico bajo, el gráfico mostrará barras pegadas al cero.
- **Sintonía Automática**: Al cargar archivos, el programa detecta el metadata para alinear la emisión.

### D. Limpiando Interferencias y Captura Automática
- **Filtro Moving Average (Pestaña Monitoreo)**: Actívalo para suavizar interferencias rápidas manteniendo una base compleja de datos I/Q.
- **Smart Trigger (Pestaña Estadística)**: Define un umbral. Si se supera, el sistema guardará la ráfaga de datos en `/data`.

---

## 4. Instalación y Entorno de Desarrollo
Nuestro entorno utiliza diversas librerías ("skills") avanzadas:
- **Ciencia y Matemáticas**: Funciones integradas estadísticas (`statsmodels`) y procesamiento simbólico de señales (`scipy` para estimaciones Kernel Density KDE).
- **Interfaz y Arquitectura**: Renderizado nativo de Flet impulsado por una codificación agresiva en Base64 SVG de Matplotlib, logrando visualizaciones de 30 FPS.
- **Optimización de Rendimiento**: Vectorización profunda con NumPy para procesar y filtrar a 40 MSps en tiempo real sin saturar hilos (Threads asíncronos).

---

## 5. Arquitectura del Sistema
El sistema se divide en dos grandes bloques desacoplados:
- **Backend / Motor DSP (`core/dsp_engine.py`):** Ejecuta la adquisición, gestiona los hilos (`threads`) de forma asíncrona, calcula transformadas rápidas de Fourier (FFT), distribuciones de magnitud y promedios móviles (MA). Aplica los filtros base y rellena los buffers circulares.
- **Frontend / UI (`ui/` y `main.py`):** Construida utilizando **Flet (Python)**. Las gráficas se generan usando **Matplotlib** operando a través de una caché SVG (`ui/charts.py`) de memoria que es incrustada como imagen en base64.

## 6. Flujo de Funcionamiento
1. **Inicialización:** `engine_instance` carga la configuración. Flet construye las distintas pestañas.
2. **Adquisición:** Al iniciar, un hilo lee de forma continua datos IQ, calculando magnitudes y espectros.
3. **Procesamiento Baseband:**
   - Lectura del ADC.
   - Filtro *Moving Average* independiente para la fase (I) y cuadratura (Q).
   - Memorización de la amplitud pura (`amplitude_data`) y amplitud filtrada (`amplitude_ma_data`).
   - Cálculo del Waterfall y Espectro (`spectrum_data`).
4. **Visualización y Actualización UI:** La UI recibe el estado por PubSub y renderiza el SVG extraído desde `charts.py`.

## 7. Descripción Detallada de Funciones y Módulos

### Módulo `core/dsp_engine.py`
Contiene la clase estática y singleton `DSPEngine`. 
- **`start_stream` / `stop_stream`:** Hilos de hardware y archivos.
- **`_process_dsp_core`:** El núcleo matemático, con la filtración MA, FFTs, Histogramas y SNR.
- **`_auto_detect_ranges`:** Un sistema heurístico de percentiles que calibra las pantallas según el nivel de ruido (noise floor).

### Módulo `ui/charts.py`
Módulo de procesamiento gráfico en hilo separado.
- **`get_cached_fig`:** Optimización tipo caché de Matplotlib Figures (`plt.Figure`).
- **`fig_to_b64`:** Transforma los gráficos vectoriales en Base64 SVG.

### Rutas y Cabeceras (`ui/components/layout.py`)
Maneja el "Header" dinámico. Muestra la configuración central exactas de frecuencia provista por el SDR sin omitir los decimales ingresados por el usuario.

## 8. Modularización y Dependencias
* `/core`: Constantes universales (`constants.py`), Motor Principal (`dsp_engine.py`).
* `/ui`: Cabeceras (`layout.py`) y motor vectorial (`charts.py`).
* `/ui/tabs`: Configuración, Monitoreo, Espectrograma, etc.
* `main.py`: Punto de entrada universal.

## 9. Implementación del Histograma (Distribución Matemática)
Procesa la distribución de las muestras complejas I/Q según la selección del usuario en la interfaz (`ui/tabs/statistics.py`):
*   **Modo Magnitud:** Extrae el valor absoluto de la señal (`np.abs(amplitude_ma_data)`). Los bins se mantienen anclados estrictamente desde la magnitud $0.0$. Esto previene la falsa recreación de distribuciones simétricas si solo hay ruido en frecuencias carentes de emisión.
*   **Modo Fase:** Extrae el ángulo de la matriz compleja (`np.angle(amplitude_ma_data)`). El eje X respeta los límites físicos de radianes entre $-\pi$ y $\pi$ ($-3.14$ a $3.14$).
*   **Visualización (Matplotlib):** Se dibuja el área rellenada con densidad de probabilidad real empírica frente al modelo de ruido térmico base (Gauss) con una densidad total de 100 *bins*.
*   *Referencia:* PySDR. (n.d.). IQ Data: Complex Numbers and Magnitude Distribution Analysis. PySDR: A Guide to SDR and DSP using Python. Recuperado de https://pysdr.org/content/iq_files.html

## 10. Mejoras e Implementaciones Actuales
- Corrección del filtro Moving Average (complejos separados I/Q).
- Cabecera y paneles sin sesgos forzados (generalización del uso del SDR en lugar de textos fijos sobre Hidrógeno).
- Decimales variables habilitados en la interfaz visual.
- Histogramas de Distribución dual (Magnitud y Fase) seleccionables en vivo con densidad de curva rellenada y corrección geométrica de auto-escalado.
- **Límites Automáticos y Persistencia en Histograma:**
  - Cuando "Auto Eje X" está activado, la Magnitud fuerza un rango de `[0.0, 0.05]` y la Fase un rango de `[-pi, pi]`.
  - Cuando el usuario desactiva "Auto Eje X" e introduce límites manuales en la interfaz, estos se graban de manera persistente y totalmente independiente en las secciones `stat_hist_mag` y `stat_hist_fase` de la configuración JSON, preservando el estado original la próxima vez que se inicie la aplicación.
- **Sintonía Simulada en Reproducción de Archivos:**
  - Se implementó un algoritmo de **desplazamiento digital de frecuencia (digital down/upconversion)** en la reproducción de archivos `.iq`.
  - Cuando el usuario sintoniza una frecuencia central en la interfaz (`center_freq`), el backend calcula la diferencia espectral $\Delta f = f_{archivo} - f_{sintonizada}$.
  - Si hay diferencia, las muestras se multiplican por un exponente complejo ($e^{j 2 \pi \Delta f t}$) para trasladar la señal espectralmente en tiempo real. Esto permite que el usuario "busque" la señal de hidrógeno variando la frecuencia y que el pico se desplace o desaparezca físicamente tal como ocurriría operando un hardware SDR real.


