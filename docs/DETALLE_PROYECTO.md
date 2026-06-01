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
*   **Visualización (Matplotlib):** Se dibuja el área rellenada transformando el histograma en una **Función de Densidad de Probabilidad (PDF)** (`density=True`), calculando la probabilidad real en lugar del conteo bruto. Se superponen los modelos empíricos (KDE) y térmicos (Gauss) escalados a densidad total.
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
  - Si hay diferencia y esta es menor que el límite físico de Nyquist ($\pm f_s / 2$), las muestras se multiplican por un exponente complejo ($e^{j 2 \pi \Delta f t}$) para trasladar la señal espectralmente en tiempo real.
  - Si la diferencia de frecuencia supera el límite de Nyquist, significa que la frecuencia sintonizada está completamente fuera del ancho de banda capturado en el archivo. En este caso, el motor **reemplaza las muestras grabadas por ruido térmico de bajísima amplitud** ($0.005$ V), logrando que los picos espectrales y de histograma desaparezcan por completo de la pantalla tal como ocurre en un receptor SDR real de hardware.
- **Propagación en Caliente de Parámetros Globales:**
  - Se habilitó la reactividad total cuando se altera la **Frecuencia Central** (`center_freq`) u otros atributos desde la pestaña de Estado.
  - El setter de `center_freq` ahora activa el flag de sintonía en caliente (`_retune_requested`) incondicionalmente para modo SDR y Archivos.
  - La UI en `estado.py` emite un evento PubSub de difusión (`refresh_charts`) al presionar Enter o quitar el cursor, refrescando en caliente todas las gráficas y cabeceras dinámicas de todas las pestañas de manera instantánea y coherente.
- **Corrección de Lógica de Auto-Calibración en Archivos:**
  - Se corrigió la condición de calibración espectral ciega (`_perform_spectral_lock`). Anteriormente, si el usuario sintonizaba una frecuencia lejana como $1410.0\text{ MHz}$, la condición invertida forzaba el retorno a $1420.4\text{ MHz}$ automáticamente.
  - La nueva lógica solo realiza el ajuste fino de auto-calibración si la frecuencia ingresada ya se encuentra cerca de la banda de interés ($\le 1.0\text{ MHz}$ de diferencia), permitiendo al usuario explorar libremente sintonías manuales lejanas (como $1410.0\text{ MHz}$) y ver la banda completamente desierta sin que el software anule su decisión.
- **Rango Temporal del Bloque de Análisis en Todas las Gráficas Principales:**
  - Se incorporó la visualización dinámica del instante de tiempo analizado en el título de todas las gráficas principales de la interfaz (Amplitud, Espectro e Histograma en `ui/charts.py`), así como en la tabla estadística lateral (`ui/tabs/statistics.py`). Se calcula y muestra el rango exacto `[t_inicio - t_fin]` relativo al archivo o streaming en vivo. Esto permite realizar comparaciones temporales cruzadas y congelar visualizaciones exactas al pulsar "Pausa", correlacionándolas fácilmente con la escala de tiempo del Espectrograma.
- **Mejora de Contraste en Leyendas para Modo Oscuro:**
  - Se corrigió el problema de legibilidad en la leyenda del histograma. El texto por defecto heredaba un tono oscuro casi invisible contra el fondo gris del panel. Se forzó explícitamente un color de fuente claro (`#ECEFF1`) y un tamaño de letra ligeramente mayor (`fontsize=8`) para asegurar una lectura óptima y descansada bajo cualquier iluminación de la pantalla.
- **Protección de Sintonía al Pausar / Reanudar:**
  - Se implementó un control en `_try_load_metadata()` que detecta si el archivo se está reanudando desde una pausa (`file_position > 0`). Si es el caso, se omite por completo la inicialización de la búsqueda de metadatos y el flag de calibración espectral ciega (`_needs_spectral_lock = False`). Esto evita que el sistema sobreescriba o fuerce calibraciones repetidas de la frecuencia central si el usuario no ha realizado ningún cambio en los controles.
- **Optimización de Latencia y Prevención de Solapamiento de Hilos:**
  - **Sincronización por Fraccionamiento (Micro-Sleeping) y Escape Rápido:** Se sustituyó el retardo largo `time.sleep(sleep_time)` por un bucle de micro-intervalos de 30ms. Asimismo, se añadieron múltiples puntos de control e interrupción rápida (`if not self.is_playing: break`) a lo largo del flujo de lectura, conversión de formato y procesamiento DSP en `_process_file_loop()`. Esto causa que el hilo cese operaciones y libere recursos inmediatamente (en menos de 3ms) tras pulsar "Pausa".
  - **Exclusión Mutua de Hilos (Safe Thread Re-use) y No-Bloqueo de UI:**
  - En `start_stream()`, se realiza una espera segura mediante `.join(timeout=0.02)` (reducido de 300ms a tan solo 20ms). Al ser combinada con el escape rápido, garantiza que el hilo anterior muere de inmediato y evita congelar o bloquear el hilo principal de la interfaz visual (UI de Flet), logrando transiciones fluidas de play/pausa sin saltos ni congelamientos.
- **Selector de Sample Rate de Tipo Chip (Flawless Row Wrap):**
  - Se eliminó el antiguo desplegable (`ft.Dropdown`) para el Sample Rate en la pestaña de Estado (`ui/tabs/estado.py`). Este componente generaba fallos visuales de posicionamiento 3D (solapamientos y cortes verticales).
  - Se sustituyó por una matriz de botones tipo "Chip" en disposición flotante auto-ajustable (`ft.Row` con parámetro `wrap=True`), estilizados con un borde e iluminación interactiva cian (`ACCENT_CYAN`) al ser seleccionados. 
  - Cuenta con un suscriptor dinámico a `refresh_charts` que actualiza y resalta en caliente la tasa de muestreo actual de forma reactiva si el motor DSP ajusta el Sample Rate por auto-calibración en archivos o cambios globales.
- **Límite de Seguridad del Buffer (Anti-Congelamiento de RAM):**
  - Se implementó un límite máximo de seguridad (`MAX_SAFE_SAMPLES = 10_000_000`) en `_resize_corr_buffer()`. Esto restringe el consumo máximo del buffer del correlograma a unos 80 MB de memoria RAM.
  - Evita que al operar a tasas de muestreo extremas de $40.0\text{ MSps}$ con cascadas muy anchas ($30.0$ segundos) se intente reservar buffers absurdos de más de 1.2 mil millones de muestras complejas (~9.6 GB de RAM), lo cual generaba el congelamiento severo de Windows por paginación de memoria y cuellos de botella de disco.
- **Checkbox de Control de Auto-Calibración Espectral Fina:**
  - Se incorporó un Checkbox en la pestaña de Estado (`ui/tabs/estado.py`) que permite al usuario habilitar o deshabilitar dinámicamente la auto-calibración espectral ciega (`auto_spectral_lock`).
  - Cuando está **desmarcado**, el motor DSP ignora cualquier pico detectado en archivos I/Q y respeta estrictamente la frecuencia central manual que el usuario introduzca en el cuadro de texto.
  - Su estado se almacena y recupera de manera persistente en `core/config.json` bajo la clave `auto_spectral_lock`.
- **Sincronización Dinámica de Gráficos Rodantes (Waterfall & Potencia vs Tiempo):**
  - Se rediseñó el buffer `power_time_data` para que deje de tener un tamaño fijo e ineficiente (de 2000 muestras) y se redimensione dinámicamente según la ecuación $\frac{\text{Historial Cascada}}{\text{Ventana Análisis}}$ (ej: $30.0\text{ s} / 0.1\text{ s} = 300\text{ pasos}$).
  - Esto garantiza que tanto el Espectrograma de Cascada como la gráfica de Potencia vs Tiempo se desplacen de forma coordinada a la velocidad de tu ventana de análisis (0.1s) y mantengan exactamente la misma ventana de memoria visual configurada (30 segundos), desplazando los datos antiguos hacia la izquierda/arriba en tiempo real y eliminando discrepancias de escala temporal.
