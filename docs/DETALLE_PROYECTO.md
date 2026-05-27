# Documentación Detallada del Proyecto (DETALLE_PROYECTO.md)

## 1. Arquitectura del Sistema
El proyecto "Plataforma DSP" consiste en un sistema avanzado de procesamiento digital de señales (DSP) en tiempo real, diseñado para operar un radiotelescopio. Su núcleo lógico está programado en Python, utilizando **Flet** para proveer una interfaz gráfica de usuario (GUI) reactiva y **Matplotlib** para el renderizado asíncrono y ultra-rápido de gráficos científicos de alto nivel.

El sistema está construido bajo una arquitectura modular y concurrente, garantizando el aislamiento entre la adquisición de hardware, los cálculos matemáticos pesados y el refresco visual de la interfaz. Esto previene cuellos de botella y permite operar a tasas de hasta 40 MSps reales.

### 1.1 Diagrama de Modularización
- **`core/`**: Cerebro matemático y de control. Contiene el motor DSP (`dsp_engine.py`), métodos avanzados como Wavelet y Burg (`advanced_dsp.py`), y parámetros físicos (`constants.py`).
- **`ui/`**: Capa de presentación visual. Maneja el diseño reactivo con Flet, organizado en componentes aislados (`ui/components/`) y visualizadores de pestañas específicos (`ui/tabs/`). Aquí también se sitúa el puente de renderizado gráfico (`ui/charts.py`).
- **`data/`**: Repositorio de almacenamiento de volcados IQ, firmas de eventos transitorios (Smart Trigger) y configuraciones previas guardadas.
- **`scripts/`**: Utilidades auxiliares (por ejemplo, para generar señales sintéticas de prueba).

## 2. Flujo de Funcionamiento Detallado

El ciclo de vida del procesamiento de señales transcurre por varias etapas críticas, sincronizadas mediante un sistema "PubSub" (Publicación/Suscripción) interno de Flet y hilos de exclusión (Locks):

1. **Adquisición de Hardware / Lectura (Data Ingestion)**: El `DSPEngine` recolecta muestras I/Q de forma ininterrumpida desde un receptor SDR (Signal Hound BB60C) o desde archivos binarios (`.iq` / `.npy`). Se alimenta un buffer global para su procesamiento por lotes.
2. **Acondicionamiento y Filtrado**: Las señales brutas atraviesan un filtro de media móvil (Moving Average) hiper-optimizado mediante sumas acumuladas (`cumsum`), cuyo propósito es amortiguar transitorios espurios (RFI) sin degradar las firmas de banda estrecha, como el Hidrógeno Neutro a 1420.4 MHz.
3. **Procesamiento de Señal (DSP Core)**: 
    - Se calculan las Transformadas Rápidas de Fourier (FFT) para obtener la Densidad Espectral de Potencia (Welch PSD).
    - Se invocan matrices de cálculo bidimensional mediante el motor `advanced_dsp.py` para calcular el Escalograma de Wavelet Continua (CWT), el Autoregresivo de Burg (AR) y el Correlograma 2D por el método de Blackman-Tukey.
    - El módulo computa automáticamente métricas de energía y ajusta los umbrales del piso de ruido (`db_noise_floor`).
    - Se evalúan las métricas frente al módulo "Smart Trigger", el cual registra ráfagas de interés si la relación Señal/Ruido supera un umbral parametrizable.
4. **Renderizado Asíncrono de Interfaz**: Un bucle `async` captura los tensores procesados y solicita su visualización a `charts.py`. Matplotlib dibuja los mapas de calor y genera un volcado vectorial SVG integrado con metadatos Base64. Esta cadena es protegida por candados multihilo (`threading.Lock`) para evitar corrupción visual (pantallas blancas o colapsos de coordenadas) en transiciones en caliente.
5. **Persistencia (Persistence Layer)**: Las modificaciones aplicadas por el usuario en tiempo de ejecución (ganancia, frecuencias, escalas de color) son inyectadas instantáneamente a disco vía `config.json`, asegurando que la parametrización sobreviva a cortes de flujo.

## 3. Descripción Detallada de Funciones Clave

### `core/dsp_engine.py` (El Corazón del Sistema)
- `_process_dsp_core(self, iq)`: Función crítica ejecutada por el hilo de adquisición. Ingesta el vector de muestras complejas, computa la energía en el dominio del tiempo, resuelve la FFT aplicando una ventana Blackman, extrae el piso de ruido y actualiza los buffers circulares que dan vida a los gráficos históricos de la UI.
- `_auto_detect_ranges(self)`: Algoritmo heurístico que escanea la distribución estadística de la señal instantánea para ajustar dinámicamente los ejes cartesianos de la Interfaz (Auto-Escala), garantizando que los picos de interés nunca queden ocultos.
- `save_config(self)`: Serializador síncrono ultra-rápido. Convierte el estado interno de la plataforma en JSON, impidiendo bloqueos I/O prolongados y garantizando la persistencia al vuelo.

### `core/advanced_dsp.py` (Matemáticas Avanzadas)
- `run_cwt_2d`: Implementa una Transformada Wavelet Continua mediante la convolución de un banco vectorizado de filtros Morlet. Posee una cuadrícula espectral bilateral y promediado de sub-ventanas, entregando una suavidad temporal extrema (sin pixelado) para el análisis de espectros transitorios.
- `run_ar_burg_2d`: Computa el modelo paramétrico Autoregresivo usando el algoritmo de minimización de error hacia adelante/atrás de Burg. Vectorizado a bajo nivel, proporciona una resolución frecuencial masivamente superior a la FFT clásica, replicando con exactitud la función `pburg` de MATLAB.
- `run_correlogram_2d`: Genera un Espectrograma de Correlograma vánculo de Wiener-Khinchin. Calcula la autocorrelación de las tramas y su posterior Transformada Inversa. El sistema calibra rigurosamente la escala espectral para coincidir en dBm reales.

### `ui/charts.py` (Motor de Renderizado Gráfico)
- `get_cached_fig(name)`: Implementa un patrón de diseño tipo *Flyweight*. Recicla las estructuras pesadas de Matplotlib (ejes, canvas), evitando la creación masiva de objetos que degradaría drásticamente los FPS.
- `chart_cwt_map`, `chart_ar_spectrogram`, `chart_correlogram_spectrogram`: Cadenas de renderizado atómicas (Thread-Safe). Reconstruyen los visuales instantáneamente basándose en metadatos y caché paramétrica cuando el usuario altera los límites del zoom o la barra de colores sin necesidad de volver a computar las matemáticas pesadas. Utilizan rasterizado híbrido sobre contenedores SVG para mantener etiquetas infinitamente nítidas.

### `main.py` (Orquestación General)
- Coordina la inicialización de Flet, la configuración de la ventana (Full Screen auto-detectado, renderizado adaptativo `STRETCH` de los contenedores), invoca los sub-componentes (Layouts, pestañas) e inyecta la tarea asíncrona permanente (`refresh_loop`) que refresca la pantalla iterativamente a medida que el `DSPEngine` informa de nuevos datos (`metadata_updated` / `data_ready`).

## 4. Dependencias y Optimizaciones
- **Python 3.10+**: Motor de ejecución base.
- **NumPy & SciPy**: Base monolítica de tensores multidimensionales y transformadas (`solve_toeplitz`, `ifft`, algebra lineal).
- **Matplotlib**: Subsistema gráfico, vectorizando en SVG para Flet sin bloquear el hilo primario.
- **Flet**: Framework de Flutter transpilado que proporciona botones, controles, sliders reactivos asíncronos y sistema de *routing* de menús (`tabs`).
- **Hardware DLL**: API estática (`bb_api.dll`) que abstrae la complejidad de la tarjeta de adquisición del Signal Hound.

El software fue intensamente optimizado (ver `OPTIMIZATIONS_LOG.md`) para abatir la latencia visual de <400ms a <10ms, erradicar fugas de memoria por variables complejas "zombies", y eliminar interrupciones térmicas mediante el uso dinámico del diezmado (decimation) en la GPU/CPU de la PC anfitriona.

## 5. Fuentes y Referencias Académicas (Normas APA)
- Blackman, R. B., & Tukey, J. W. (1958). *The measurement of power spectra, from the point of view of communications engineering*. Dover Publications.
- Burg, J. P. (1975). *Maximum entropy spectral analysis* (Doctoral dissertation, Stanford University).
- Welch, P. (1967). The use of fast Fourier transform for the estimation of power spectra: A method based on time averaging over short, modified periodograms. *IEEE Transactions on Audio and Electroacoustics*, 15(2), 70-73. https://doi.org/10.1109/TAU.1967.1161895
- Wiener, N. (1930). Generalized harmonic analysis. *Acta Mathematica*, 55(1), 117-258. https://doi.org/10.1007/BF02546511
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
# Documentación Técnica Detallada: Signal Hound BB60C

El **Signal Hound BB60C** es un analizador de espectro en tiempo real y grabador de RF de alto rendimiento. Basado en una arquitectura de Radio Definida por Software (SDR), ofrece un rendimiento de grado de laboratorio en un dispositivo alimentado exclusivamente por USB 3.0. 

A continuación, se detalla la información técnica profunda extraída de sus manuales de usuario, referencias de la API y hojas de datos de producto.

---

## 1. Arquitectura de Hardware y Panel de Conexiones

El BB60C utiliza un oscilador y filtros pasa-banda para realizar una conversión descendente (down-convert) de una porción del espectro de entrada a una Frecuencia Intermedia (IF). Esta IF se envía al PC host mediante USB 3.0, donde el software se encarga de aplicar el análisis de espectro mediante la Transformada Rápida de Fourier (FFT).

### Panel Frontal
* **Entrada de RF (SMA):** Conector de 50Ω nominales. **Precaución:** No se debe exceder una potencia de entrada de +20 dBm para evitar daños irreversibles en el equipo.
* **LED de Estado (READY/BUSY):** Parpadea en color naranja cada vez que procesa un comando desde el ordenador anfitrión.

### Panel Trasero
* **Referencia de 10 MHz (In/Out):** Permite sincronizar la base de tiempo. Se recomienda una onda sinusoidal limpia o cuadrada con un nivel >0 dBm (idealmente una onda senoidal de +13 dBm o un reloj CMOS de 3.3V).
* **Puerto USB 3.0 Micro-B Hembra:** Conector principal de datos y alimentación. Requiere el cable tipo "Y" suministrado para garantizar el amperaje adecuado (datos USB 3.0 + alimentación auxiliar USB 2.0).
* **Conector BNC Multipropósito:** Funciona principalmente para la entrada de un pulso por segundo (1 PPS) de GPS que permite marcas de tiempo con una precisión de ±50 ns, o para triggers. También es capaz de emitir niveles lógicos alto y bajo controlados mediante la API.

---

## 2. Rendimiento y Especificaciones de Radiofrecuencia

El BB60C mejora significativamente respecto a modelos anteriores (como el BB60A), mejorando el Rango Dinámico Libre de Espurias (SFDR) en 20 dB y aplanando el piso de ruido en más de 8 dB.

* **Rango de Frecuencia:** 9 kHz a 6.0 GHz.
* **Ancho de Banda Instantáneo (IBW):** Hasta 27 MHz calibrados para streaming I/Q.
* **Velocidad de Barrido:** Hasta 24 GHz/segundo (con RBW ≥ 10 kHz).
* **Tasa de Muestreo:** Recolecta 80 millones de muestras IF por segundo, generando un flujo continuo de datos de 140 MB/s hacia la PC.
* **Tasas de Muestreo I/Q Variables:** Permite tasas seleccionables desde 312.5 kS/s hasta 40 MS/s I/Q, ofreciendo un control fino sobre el espectro que se desea grabar.
* **Rango Dinámico:** Amplio rango de -158 dBm hasta +10 dBm (90 dB de rango dinámico general).
* **Nivel de Ruido Promedio Mostrado (DANL):**
    * De 9 kHz a 500 kHz: -140 dBm/Hz.
    * De 500 kHz a 10 MHz: -154 dBm/Hz.
    * De 10 MHz a 6 GHz: -158 dBm + 1.1 dB/GHz.
* **Figura de Ruido del Sistema:** 12 dB típico (de 20 MHz a 1.8 GHz).
* **Precisión de Amplitud:** ± 2.0 dB absolutos.
* **Precisión de Base de Tiempo:** ± 1 ppm por año.
* **Temperaturas de Operación:** * Estándar: 0°C a +65°C.
    * Opción 1: -40°C a +65°C (Probado rigurosamente con ráfagas de frío de 3 horas a -40ºC y 24 horas de calor continuo a +65ºC).
* **Dimensiones y Peso:** 21.9 x 8.1 x 3 cm (8.63" x 3.19" x 1.19") y 0.50 kg de peso.

---

## 3. Funciones de Software (Spike) y Aplicaciones

El procesamiento se realiza a través del software **Spike** (o aplicaciones de terceros mediante la API), el cual incluye:

* **Pantalla de Persistencia de Color 2D y Cascada (Waterfall):** Revela eventos transitorios de hasta 1 µsec con un 100% de probabilidad de intercepción (POI) que los analizadores de espectro normales no detectarían.
* **Aplicaciones Principales:**
    * Grabador de RF (RF Recorder).
    * Test y medición de RF de propósito general.
    * Pruebas de pre-cumplimiento EMC.
    * Caracterización de Ruido de Fase.
    * Mediciones EVM (Error Vector Magnitude).
    * Caracterización de canales.

---

## 4. Desarrollo de Software y API

El BB60C incluye una potente Interfaz de Programación de Aplicaciones (API) escrita en C (compatible con la interfaz binaria de aplicaciones ABI), la cual permite una personalización total del dispositivo.

* **Compatibilidad y Entornos:** Al ser compatible con ABI de C, la API puede ser invocada desde múltiples lenguajes de programación, incluyendo Java, C#, Python, C++, MATLAB y LabVIEW.
* **Mediciones Principales Vía API:**
    * Análisis de Espectro por Barrido (Swept Spectrum Analysis).
    * Análisis de Espectro en Tiempo Real.
    * Streaming de datos I/Q.
    * Demodulación de Audio.
    * Análisis de Redes Escalar (Scalar Network Analysis).
* **Gestión de Energía Avanzada:** Mediante la API, el equipo puede ponerse en estado de bajo consumo. Estando activo, el BB60C consume unos 6 Watts, pero usando la función `bbSetPowerState` se puede reducir a un modo de espera (standby) de aproximadamente 1.25 Watts.
* **Procesamiento de Datos I/Q Vía Código:** Para medir la potencia de una muestra en los flujos I/Q de la API, los desarrolladores deben convertir las muestras complejas de 16-bits a punto flotante (float), escalar los valores flotantes utilizando el valor de corrección devuelto por `bbGetIQCorrection`, y aplicar un cálculo logarítmico (10.0 * log10) para obtener la potencia en dBm.
* **Salida UART en Barrido:** Durante el streaming o barrido, se pueden emitir bytes UART en posiciones específicas, permitiendo aplicaciones como radiogoniometría (dirección pseudo-Doppler) o conmutación de múltiples antenas.

---

## 5. Requisitos del Sistema y Hardware

Dado el enorme flujo sostenido de información, el PC utilizado debe cumplir especificaciones estrictas:

* **Procesador:** Intel Core i7 de cuatro núcleos de 3.ª generación para equipos de escritorio (los procesadores Intel están recomendados debido a optimizaciones específicas de instrucciones).
* **Conectividad:** Controlador USB 3.0 nativo.
* **Grabación de RF Continua:** Si se desea operar como un grabador de banda base I/Q a la máxima velocidad, se necesita un disco duro de estado sólido (SSD) o arreglo RAID capaz de sostener de forma ininterrumpida una velocidad de escritura de al menos 250 MB/s.
## 6. Optimización y Estabilidad en UIC Radiotelescopio

Para garantizar una operación ininterrumpida en entornos de investigación, se han implementado las siguientes mejoras de software sobre la API base:

* **Gestión de Bloqueos (Mutex):** Implementación de `threading.Lock` para sincronizar el acceso al `sdr_handle`. Esto evita errores de `Device not open` cuando la interfaz de usuario intenta reconfigurar el hardware mientras el motor DSP está leyendo muestras.
* **Manejo Inteligente de Warnings:** El sistema diferencia entre errores fatales (Status < 0) y avisos informativos (Status > 0). El **Warning 4 (Value Clamped)** se captura y se ignora silenciosamente, permitiendo que la adquisición continúe sin desconexiones accidentales.
* **Auto-Cuantización de Sample Rate:** El software traduce automáticamente cualquier petición de velocidad de muestreo a las potencias de 2 soportadas por el BB60C (40, 20, 10, 5, 2.5, 1.25 MSps), garantizando que `bb_configure_IQ` siempre reciba parámetros válidos.
* **Límites de Seguridad de Ancho de Banda:** Para operar de forma estable a la tasa máxima (40 MSps), se aplica un límite de ancho de banda IQ de **27 MHz**, cumpliendo con los límites físicos del dispositivo y garantizando una señal libre de aliasing.
* **Recuperación Automática:** En caso de un fallo de configuración crítico, el motor intenta devolver el hardware a un estado seguro (20 MHz BW / Decimación 1) antes de reportar el error, maximizando la resiliencia del sistema.

