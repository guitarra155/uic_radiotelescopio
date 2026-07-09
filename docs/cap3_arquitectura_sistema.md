# Capítulo III: Arquitectura y Diseño del Sistema

Para garantizar la fiabilidad en la detección y el procesamiento de señales electromagnéticas de muy baja amplitud —como la línea de hidrógeno neutro a 1420.4 MHz—, el desarrollo de la plataforma UIC prioriza la verificación formal de sus algoritmos y una división estricta de responsabilidades entre los componentes de software. La captura de datos astronómicos requiere un entorno libre de cuellos de botella y fluctuaciones temporales artificiales. Por ello, la arquitectura del sistema se ha diseñado para aislar las tareas críticas de procesamiento matemático de la interfaz de usuario, minimizando la probabilidad de pérdida de muestras I/Q y reduciendo la tasa de errores lógicos en el motor digital de procesamiento de señales (DSP).

Esta modularidad se materializa mediante el desacoplamiento de la plataforma en tres capas independientes: Adquisición, Procesamiento y Presentación. Cada capa opera de manera autónoma, comunicándose mediante interfaces bien definidas y flujos asíncronos. La capa de adquisición extrae los datos crudos en tiempo real, el motor DSP ejecuta los filtros de promedio móvil y estimaciones espectrales en hilos secundarios dedicados, y la interfaz gráfica gestiona la visualización interactiva sin interferir en la ingesta de datos. Este enfoque arquitectónico garantiza que la plataforma mantenga una respuesta fluida y precisa, incluso bajo tasas de muestreo elevadas de hasta 40 MSps.

Para comprender en detalle las transformaciones numéricas y los procesos de estimación espectral que se describen en este capítulo, es indispensable establecer un marco teórico común. A continuación, la Tabla 1 expone la nomenclatura matemática empleada en el diseño e implementación del pipeline DSP, sirviendo como guía conceptual para las secciones posteriores.

> **Tabla 1.** *Nomenclatura Matemática del Sistema DSP.*

| Símbolo | Descripción Técnica | Unidad |
|:---:|:---|:---:|
| $f_s$ | Tasa de muestreo (Sample Rate) efectiva | MSps / Hz |
| $N$ | Tamaño del kernel para el filtro de media móvil | Muestras |
| $N_{FFT}$ | Tamaño de segmento para la transformada rápida de Fourier | Muestras |
| $B$ | Número de bloques espectrales promediados | Adimensional |
| $P_{dBFS}$ | Potencia espectral relativa al fondo de escala | dBFS |
| $\alpha$ | Factor de memoria (constante temporal) para filtros IIR | Adimensional |
| $k$ | Índice discreto del bin de frecuencia | Adimensional |

---

## 3.1. Descripción General del Sistema y Flujo de Datos

La plataforma UIC se concibe como un sistema de software integrado cuyo propósito es la adquisición, procesamiento y visualización en tiempo real de señales de radiofrecuencia (RF) provenientes de un receptor SDR de grado científico. El flujo de datos atraviesa tres capas funcionales claramente diferenciadas: la capa de adquisición y hardware, la capa de procesamiento digital, y la capa de presentación e interfaz gráfica de usuario.

En la capa inferior, el analizador de espectro BB60C de Signal Hound —o en su defecto, un archivo de muestras I/Q pregrabadas— suministra un flujo continuo de datos complejos en banda base. Estas muestras ingresan al motor DSP (`DSPEngine`), el cual ejecuta de forma secuencial las etapas de filtrado digital, decimación, estimación espectral, detección estadística de señales y cálculo de métricas derivadas tales como la relación señal-ruido (SNR) por bin de frecuencia y la potencia media instantánea. Finalmente, los resultados procesados se transfieren a la capa de presentación, donde se renderizan de forma simultánea en múltiples dominios de análisis (tiempo, frecuencia, tiempo-frecuencia y distribución probabilística) a través de una interfaz gráfica construida con el framework Flet.

> **Figura 11.** *Arquitectura del Sistema.*
> **[INSERTE LA IMAGEN DE LA FIGURA 11 AQUÍ - `fig11_arquitectura_sistema.puml`]**
> Diagrama de bloques que detalla la arquitectura de software estructurada en el patrón de diseño por capas, estableciendo una separación estricta de responsabilidades. Como se ilustra en el esquema, la **Capa de Presentación (GUI)** gestiona la interacción directa con el usuario; en ella, el panel `sdr_config.py` captura las variaciones de parámetros en vivo y sincroniza la interfaz enviando las directivas al controlador Flet (`main.py`), el cual a su vez instancia y actualiza dinámicamente las diferentes pestañas de análisis gráfico (`Vistas`).
> 
> En el nivel intermedio, la **Capa de Procesamiento (DSP Core)** implementa el motor de cómputo en segundo plano mediante `dsp_engine.py`. Esta entidad interactúa bidireccionalmente con el módulo `advanced_dsp.py`, al cual delega los bloques de muestras temporales I/Q y del cual recibe de regreso los espectros calculados y los parámetros estimados. Esta separación asegura que los cálculos matemáticos intensivos no bloqueen el hilo de renderizado gráfico de la aplicación.
> 
> En la base, la **Capa de Adquisición** provee el flujo continuo de muestras en banda base. Para ello, implementa una interfaz dual: el módulo `bb_api.py` para interactuar directamente con el hardware a través de llamadas ctypes de bajo nivel, y el `Simulador Sintético` que reproduce de forma controlada señales previamente registradas. El flujo resultante de muestras I/Q se transfiere de forma ascendente al motor DSP, cerrando el ciclo de procesamiento y visualización.

---

## 3.2. Arquitectura de Software Modularizada en Python

Una vez definida la estructura funcional del sistema, se procedió a la implementación de una arquitectura modular basada en el lenguaje de programación Python (versión 3.12). Esta arquitectura se organiza en paquetes independientes que encapsulan las responsabilidades de cada capa, facilitando el mantenimiento, la extensibilidad algorítmica y la depuración del sistema.

> **Figura 12.** *Flujo de datos y Control general.*
> **[INSERTE LA IMAGEN DE LA FIGURA 12 AQUÍ]**
> Diagrama que ilustra la secuencia continua del flujo de datos en el sistema. Inicia con la ingesta de muestras I/Q desde el analizador BB60C o fuentes sintéticas, atravesando el pipeline de procesamiento digital del DSPEngine que incluye etapas de filtrado digital, diezmado y estimación espectral. Finalmente, se activa el algoritmo de umbralización CFAR para la detección de eventos. En paralelo, el sistema se apoya en un archivo de configuración persistente (`config.json`) para sincronizar parámetros operativos entre la lógica de negocio y la interfaz de usuario en tiempo real.

La Tabla 3 resume la responsabilidad de cada módulo principal del software.

> **Tabla 3.** *Módulos principales del sistema y sus responsabilidades.*

| Módulo | Archivo(s) | Responsabilidad |
|:---|:---|:---|
| Motor DSP (Singleton) | `core/dsp_engine.py` | Gestión del ciclo de vida del procesamiento: lectura de muestras, filtrado, FFT, estimación espectral, detección, auto-escalado y persistencia de configuración. |
| Algoritmos DSP Avanzados | `core/advanced_dsp.py` | Implementación de los algoritmos de estimación espectral de alta resolución: AR/Burg, CWT/Morlet, Welch y Correlograma. |
| Registro de Algoritmos | `core/algo_registry.py` | Diccionario centralizado que mapea los nombres de los métodos a sus funciones ejecutoras, permitiendo la selección dinámica de algoritmos desde la interfaz gráfica. |
| Wrapper del BB60C | `core/bbdevice/bb_api.py` | Interfaz Python (ctypes) que abstrae las funciones del SDK nativo de Signal Hound (`bb_api.dll`), encapsulando las llamadas al hardware. |
| Punto de Entrada | `main.py` | Inicialización del framework Flet, construcción de pestañas, gestión global de atajos de teclado y orquestación del ciclo principal de la interfaz gráfica. |
| Pestañas de Análisis | `ui/tabs/*.py` | Módulos independientes que construyen cada vista de análisis (monitoreo, espectrograma, histograma, potencia vs. tiempo, SNR vs. frecuencia). |
| Renderizadores Gráficos | `ui/charts/*.py` | Funciones de renderizado Matplotlib que generan las gráficas a partir de los buffers numéricos del motor DSP. |
| Panel de Configuración | `ui/tabs/sdr_config.py` | Panel lateral interactivo que expone los parámetros de hardware, filtrado, estimación espectral y ejecución de algoritmos avanzados. |

### 3.2.1. Estructura orientada a componentes independientes

La organización física del código fuente refleja la separación de responsabilidades definida por la arquitectura de capas. A continuación, se presenta la estructura jerárquica del proyecto con la descripción funcional de sus componentes principales:

```text
uic_radiotelescopio/
├── main.py                          # Punto de entrada y controlador principal de la GUI (Flet).
├── core/                            # Capa de control, procesamiento digital y drivers
│   ├── dsp_engine.py                # Motor de procesamiento (Singleton) y gestión de hilos.
│   ├── advanced_dsp.py              # Algoritmos de estimación espectral clásicos y paramétricos.
│   ├── algo_registry.py             # Registro y mapeo dinámico de funciones matemáticas.
│   ├── constants.py                 # Constantes físicas, del sistema y estilos visuales globales.
│   └── bbdevice/                    # Abstracción de bajo nivel del hardware SDR
│       ├── bb_api.py                # Wrapper ctypes para llamadas C++ en Python.
│       └── bb_api.dll               # Biblioteca dinámica provista por el fabricante (Signal Hound).
├── ui/                              # Capa de presentación (Entorno gráfico de usuario)
│   ├── tabs/                        # Módulos que orquestan las vistas e inputs de cada pestaña
│   │   ├── estado.py                # Pestaña 1: Configuración de hardware y manuales.
│   │   ├── dual_monitoring.py       # Pestaña 2: Monitoreo en tiempo/frecuencia (RAW vs. Filtrada).
│   │   ├── spectrogram.py           # Pestaña 3: Espectrogramas bidimensionales.
│   │   ├── statistics.py            # Pestaña 4: Histogramas y estimación MLE.
│   │   ├── signal_analysis.py       # Pestaña 5: Series temporales de potencia media.
│   │   ├── freq_snr.py              # Pestaña 6: Gráficas de relación señal-ruido.
│   │   └── sdr_config.py            # Panel lateral de control dinámico y auto-escala.
│   ├── charts/                      # Renderizadores gráficos autónomos basados en Matplotlib
│   │   ├── monitoring.py            # Gráficas de monitoreo temporal/frecuencial (2x2).
│   │   ├── spectrogram.py           # Renderizado de cascadas de potencia espectral en 2D.
│   │   ├── statistics.py            # Renderizado de histogramas con curvas teóricas MLE.
│   │   ├── signal_analysis.py       # Renderizado de series temporales de potencia.
│   │   └── freq_snr.py              # Renderizado de picos de relación señal-ruido.
│   └── components/                  # Elementos comunes e instrumentación del layout
│       ├── layout.py                # Barra de cabecera superior y pie de página de la aplicación.
│       └── shared.py                # Widgets genéricos, campos de texto y estilos comunes.
├── data/                            # Directorio local para almacenamiento de archivos binarios (.iq).
└── docs/                            # Documentación de diseño del sistema y esquemas UML (.puml).
```

Esta separación física garantiza que modificaciones en los algoritmos matemáticos dentro de `core/advanced_dsp.py` no tengan impacto sobre el flujo gráfico de las pestañas en `ui/tabs/`, asegurando un mantenimiento sumamente ordenado.

### 3.2.2. Modelo de ejecución asíncrono y gestión de concurrencia

La adquisición de datos y el procesamiento digital de señales se ejecutan en un hilo secundario (`threading.Thread`) independiente del hilo principal de la interfaz gráfica (Flet). Esta separación es necesaria dado que el analizador BB60C opera a tasas de muestreo de hasta 40 MSps (mega muestras por segundo), lo cual genera un volumen de datos que bloquearía la interfaz gráfica si ambos procesos compartiesen un único hilo de ejecución.

El flujo de concurrencia opera de la siguiente manera:

1. El **hilo de la GUI** (Flet) atiende los eventos del usuario (clics, cambios de configuración, atajos de teclado) y renderiza las gráficas.
2. El **hilo DSP** (`_process_sdr_loop()` o `_process_file_loop()`) captura las muestras I/Q desde el hardware o desde un archivo, las procesa matemáticamente y actualiza los buffers compartidos (`spectrum_data`, `waterfall_data`, `snr_data`, `histogram_data`, `power_time_data`).
3. Una señal de sincronización (`data_ready = True`) notifica a la GUI que un nuevo bloque de datos ha sido procesado, activando el refresco de las gráficas mediante el patrón publicador-suscriptor (`page.pubsub.send_all("refresh_charts")`).

> **Figura 13.** *Modelo de Concurrencia del Sistema.*
> **[INSERTE LA IMAGEN DE LA FIGURA 13 AQUÍ - `fig13_concurrencia.puml`]**
> Diagrama de secuencia que describe el comportamiento asíncrono entre la interfaz gráfica (hilo GUI) y el motor de procesamiento (hilo DSP). Se ilustra cómo las acciones del usuario, como iniciar o detener la adquisición, se comunican mediante un bus de eventos (PubSub). A su vez, el hilo DSP opera de manera continua sobre el hardware (o archivo) procesando la señal y utilizando una bandera de estado (`data_ready = True`) para notificar a la GUI que los buffers compartidos contienen información actualizada, desencadenando la renderización de las gráficas sin bloquear la recepción de nuevas muestras I/Q.

### 3.2.3. Mecanismo de persistencia de configuración y comunicación inter-módulos

Los parámetros del sistema (frecuencia central, tasa de muestreo, límites de visualización, orden de los algoritmos, modos de operación, resolución de ventana) se persisten automáticamente en un archivo JSON ubicado en `core/config.json`. Cada modificación realizada por el usuario a través del panel de configuración invoca la función `engine_instance.save_config()`, la cual serializa el estado completo del motor DSP al disco.

La comunicación entre los módulos de la interfaz gráfica se realiza mediante un bus de eventos distribuido provisto por Flet (`page.pubsub`). Cuando el usuario modifica un parámetro en el panel de configuración lateral, se emite un mensaje de tipo `"refresh_charts"` que todas las pestañas suscritas reciben de forma simultánea, garantizando la coherencia visual de las gráficas en todos los dominios de análisis.

> **Tabla 4.** *Mensajes del bus de eventos (PubSub) y su efecto en el sistema.*

| Mensaje PubSub | Emisor | Efecto |
|:---|:---|:---|
| `"refresh_charts"` | `sdr_config.py`, `dsp_engine.py` | Refresca todas las gráficas activas en la pestaña visible. |
| `"toggle_stream"` | `main.py` (tecla F5) | Inicia o detiene la adquisición y el procesamiento de datos. |
| `"emergency_stop"` | `main.py` (tecla F8) | Detención de emergencia del sistema completo. |
| `"toggle_config_collapse"` | `main.py` (Ctrl+Shift+B) | Colapsa o expande el panel lateral de configuración. |

---

## 3.3. Subsistema de Adquisición de Datos y Control de Hardware

### 3.3.1. Interfaz de abstracción y control para el analizador de espectro BB60C

La plataforma UIC interactúa con el analizador de espectro Signal Hound BB60C mediante una capa de abstracción implementada en el módulo `core/bbdevice/bb_api.py`. Este módulo utiliza la librería estándar de Python `ctypes` para invocar las funciones de la biblioteca dinámica nativa del SDK de Signal Hound (`bb_api.dll`, compilada en C++). Esta aproximación permite controlar el hardware directamente desde Python sin necesidad de compiladores externos.

La secuencia de inicialización del hardware sigue el protocolo definido por el fabricante (Signal Hound, 2024):

1. **Apertura del dispositivo** (`bb_open_device()`): Establece la conexión USB 3.0 con el BB60C.
2. **Configuración de ganancia y nivel de referencia** (`bb_configure_ref_level()`, `bb_configure_gain_atten()`): Ajusta la cadena de amplificación interna del receptor para evitar saturación del ADC.
3. **Configuración de la frecuencia central** (`bb_configure_IQ_center()`): Sintoniza el oscilador local del receptor a la frecuencia de interés (expresada en Hz).
4. **Configuración de decimación y ancho de banda** (`bb_configure_IQ()`): Define la tasa de muestreo efectiva y el filtro anti-aliasing digital.
5. **Inicio del modo streaming** (`bb_initiate(BB_STREAMING, BB_STREAM_IQ)`): Activa el flujo continuo de muestras I/Q en banda base.
6. **Lectura de bloques I/Q** (`bb_get_IQ_unpacked()`): Obtiene un arreglo NumPy complejo (`complex64`) con las muestras capturadas.

> **Figura 14.** *Secuencia de Inicialización del BB60C.*
> **[INSERTE LA IMAGEN DE LA FIGURA 14 AQUÍ - `fig14_secuencia_bb60c.puml`]**
> Diagrama de secuencia que modela las interacciones entre la abstracción en Python (`bb_api.py`), la biblioteca nativa en C++ (`bb_api.dll`) y el hardware SDR físico. Detalla el protocolo estricto requerido por el fabricante, el cual inicia con la apertura del dispositivo, continúa con la calibración del nivel de referencia para evitar la saturación del ADC, establece la frecuencia central y la decimación del filtro anti-aliasing digital, para finalmente iniciar el flujo continuo de muestras complejas I/Q hacia los buffers de la aplicación.

> **IMAGEN DEL PROGRAMA:** Capturar la **Pestaña 1 (Inicio & Configuración)** mostrando el panel de control del BB60C con los campos de Frecuencia Central, Sample Rate, Nivel de Referencia y el botón de inicio (F5).

### 3.3.2. Configuración dinámica del hardware

La plataforma permite la reconfiguración en tiempo real de los parámetros del hardware sin necesidad de detener la adquisición. Cuando el usuario modifica la frecuencia central o la tasa de muestreo durante una sesión de streaming activa, el motor DSP activa una señal interna (`_retune_requested = True`) que el hilo de adquisición evalúa en cada ciclo de lectura. Al detectar esta señal, el hilo ejecuta la secuencia de reconfiguración completa (`bb_abort()` → re-configuración → `bb_initiate()`) de forma atómica dentro del mismo hilo, sin crear nuevos hilos ni interrumpir el flujo de datos.

La tasa de muestreo efectiva se calcula mediante la fórmula de decimación del BB60C:

$$f_s = \frac{40\ \text{MSps}}{2^n}, \quad n \in \{0, 1, 2, \ldots, 7\}$$

Donde $f_s$ es la tasa de muestreo resultante y $n$ es el exponente de decimación. El sistema calcula automáticamente el valor de $n$ más cercano al valor solicitado por el usuario.

> **Tabla 5.** *Tasas de muestreo disponibles del BB60C según el factor de decimación.*

| Factor de Decimación (2^n) | Tasa de Muestreo (fs) | Ancho de Banda Útil |
|:---:|:---:|:---:|
| 1 | 40.00 MSps | 24.0 MHz |
| 2 | 20.00 MSps | 12.0 MHz |
| 4 | 10.00 MSps | 6.0 MHz |
| 8 | 5.00 MSps | 3.0 MHz |
| 16 | 2.50 MSps | 1.5 MHz |
| 32 | 1.25 MSps | 0.75 MHz |
| 64 | 625.0 kSps | 375.0 kHz |
| 128 | 312.5 kSps | 187.5 kHz |

*Nota: El ancho de banda útil se limita al 60% de la tasa de muestreo para cumplir con los requisitos del filtro anti-aliasing del SDK de Signal Hound (Signal Hound, 2024).*

---

## 3.4. Pipeline de Procesamiento Digital de Señales (DSP)

El pipeline de procesamiento digital de señales constituye el núcleo computacional de la plataforma. Opera de forma secuencial sobre cada bloque de muestras I/Q recibido, produciendo los arreglos numéricos que alimentan las gráficas de la interfaz gráfica de usuario.

> **Figura 15.** *Pipeline de Procesamiento Digital de Señales.*
> **[INSERTE LA IMAGEN DE LA FIGURA 15 AQUÍ - `fig15_pipeline_dsp.puml`]**
> Diagrama de flujo horizontal que detalla exhaustivamente el procesamiento de las señales desde su ingreso como muestras I/Q complejas hasta la detección de eventos. El proceso se bifurca inmediatamente para mantener una ruta de señal original (RAW) y una filtrada (vía media móvil). Ambas rutas son transformadas al dominio de la frecuencia mediante algoritmos configurables como FFT o Welch. Los resultados alimentan simultáneamente a los módulos de instrumentación, actualizando los buffers de los espectrogramas (Waterfall, CWT, AR/Burg), las distribuciones estadísticas (Histogramas), y las series temporales (Potencia y SNR), culminando en el bloque de decisión estadística (CFAR).

### 3.4.1. Bloque de filtrado digital, diezmado y conversión espectral

La primera etapa del pipeline recibe las muestras I/Q complejas en banda base y aplica un filtro de media móvil (Moving Average) configurable. Este filtro suaviza las fluctuaciones del ruido térmico al promediar N muestras consecutivas, donde N es un parámetro ajustable por el usuario desde el panel de configuración (valor por defecto: 240 muestras).

La implementación utiliza la función `uniform_filter1d()` de SciPy, la cual opera de forma separada sobre las componentes real (I) e imaginaria (Q) de la señal compleja:

$$y_I[n] = \frac{1}{N} \sum_{k=0}^{N-1} x_I[n-k], \quad y_Q[n] = \frac{1}{N} \sum_{k=0}^{N-1} x_Q[n-k]$$

La señal resultante y[n] = y_I[n] + j·y_Q[n] constituye la versión filtrada que se utiliza en todas las etapas posteriores del pipeline, con excepción del espectro RAW (sin filtrar), el cual se preserva para comparación directa en la pestaña de monitoreo dual (Pestaña 2).

Posteriormente, se aplica la Transformada Rápida de Fourier (FFT) sobre segmentos de N_FFT muestras (por defecto, 4096) ponderados con una ventana de Hanning para reducir la fuga espectral. El espectro de potencia en escala logarítmica se calcula como:

$$P_{dBFS}[k] = 10 \cdot \log_{10}\left(\frac{|X[k]|^2}{B \cdot W_{pwr}} + \epsilon\right)$$

Donde B es el número de bloques promediados, W_pwr es la potencia de la ventana de Hanning y epsilon = 10^-12 evita el logaritmo de cero.

Adicionalmente, se aplica un filtro IIR de primer orden (suavizado VBW - Video Bandwidth) para estabilizar visualmente el espectro entre frames consecutivos:

$$S_{out}[k] = (1 - \alpha) \cdot S_{prev}[k] + \alpha \cdot P[k]$$

Donde alpha es el factor de suavizado VBW configurable (valor por defecto: 0.3).

### 3.4.2. Implementación de estimación espectral clásica y paramétrica

La plataforma implementa los siguientes métodos de estimación espectral, seleccionables de forma dinámica desde el panel de configuración:

> **Tabla 6.** *Algoritmos de estimación espectral implementados.*

| Algoritmo | Tipo | Resolución | Parámetros Configurables |
|:---|:---|:---|:---|
| FFT + Ventana Hanning | No paramétrico | Limitada por N_FFT | Tamaño de FFT |
| Welch (Periodograma promediado) | No paramétrico | Mejorada por promediado | Tamaño de segmento, solapamiento (%) |
| AR/Burg | Paramétrico (Autorregresivo) | Muy alta (independiente de N_FFT) | Orden del modelo AR |
| CWT/Morlet | Tiempo-Frecuencia | Variable por escala | Número de escalas |
| Correlograma | No paramétrico (indirecto) | Controlada por lag máximo | Lag máximo de autocorrelación |

**Método de Welch.** Divide la señal en segmentos solapados, aplica una ventana a cada segmento, calcula su periodograma individual y promedia los resultados. Esta técnica reduce la varianza de la estimación espectral a cambio de una resolución de frecuencia ligeramente menor (Welch, 1967, p. 72).

**Método AR/Burg.** Estima los coeficientes de un modelo autorregresivo (AR) de orden p mediante la minimización simultánea de los errores de predicción hacia adelante y hacia atrás (Burg, 1975, p. 34). La densidad espectral de potencia se obtiene evaluando el polinomio AR en el círculo unitario:

$$P_{AR}(f) = \frac{\sigma^2}{\left|1 + \sum_{k=1}^{p} a_k \cdot e^{-j2\pi f k}\right|^2}$$

Donde a_k son los coeficientes AR estimados y sigma^2 es la varianza del error de predicción.

> **IMAGEN DEL PROGRAMA:** Capturar la **Pestaña 1 (Inicio & Configuración)** mostrando el panel lateral en la sección "Algoritmos DSP" con la selección del método AR/Burg, el campo de Orden AR, y los resultados de ejecución.

### 3.4.3. Algoritmo de detección espectral y cálculo de umbrales dinámicos (CFAR)

Para la detección automática de señales de interés, el sistema implementa un esquema de umbralización dinámica basado en el principio de Tasa de Falsa Alarma Constante (CFAR). El proceso opera de la siguiente manera:

1. **Estimación del piso de ruido local:** Se aplica un filtro de mediana deslizante (`scipy.signal.medfilt`) con un kernel de tamaño proporcional al 4% del número total de bins espectrales. Este filtro estima el nivel de ruido de fondo localmente sin verse afectado por los picos espectrales de señales coherentes.

2. **Cálculo del SNR por bin:** La relación señal-ruido se calcula como la diferencia entre la potencia espectral observada y el piso de ruido estimado:

$$SNR[k] = P_{señal}[k]_{dBFS} - P_{ruido}[k]_{dBFS}$$

3. **Umbral de detección fijo:** Un bin se clasifica como señal de interés si SNR[k] > 6 dB. Este umbral de 6 dB corresponde a una probabilidad de falsa alarma suficientemente baja para evitar clasificar fluctuaciones térmicas como señales reales en el contexto de detección radioastronómica.

4. **Agrupamiento de detecciones (clustering):** Los bins adyacentes que superan el umbral se agrupan en clusters con una separación mínima de 10 kHz, seleccionando el pico de mayor SNR dentro de cada grupo.

> **Figura 16.** *Algoritmo de Detección CFAR.*
> **[INSERTE LA IMAGEN DE LA FIGURA 16 AQUÍ - `fig16_cfar.puml`]**
> Diagrama de flujo que ilustra la lógica del algoritmo de Tasa de Falsa Alarma Constante (CFAR) implementado en el sistema. A partir de los datos espectrales crudos, se emplea un filtro de mediana espacial sobre una ventana deslizante proporcional al ancho de banda, logrando estimar el piso de ruido dinámico de manera robusta e inmune a valores atípicos. Posteriormente, se evalúa la relación señal-ruido bin por bin respecto a un umbral predefinido (6 dB). Los eventos detectados son agrupados (clustering) por proximidad espectral (10 kHz de tolerancia), garantizando la mitigación de detecciones espurias y extrayendo el pico dominante de cada grupo como una señal de interés legítima.

---

## 3.5. Entorno Gráfico de Usuario (GUI) para el Uso Multidominio

La interfaz gráfica de usuario fue desarrollada utilizando el framework Flet (versión 0.84), el cual permite la construcción de interfaces nativas multiplataforma utilizando exclusivamente Python. La GUI se organiza en un sistema de pestañas, donde cada pestaña presenta la información en un dominio de análisis diferente.

> **Tabla 7.** *Pestañas de la GUI y su dominio de análisis.*

| N.° | Nombre de la Pestaña | Dominio de Análisis |
|:---:|:---|:---|
| 1 | Inicio & Configuración | Estado del sistema, control de hardware, ejecución de algoritmos avanzados |
| 2 | Señal y Señal Filtrada | Dominio del Tiempo (amplitud) + Dominio de la Frecuencia (espectro). Comparación RAW vs. Filtrada |
| 3 | Espectrograma | Dominio Tiempo-Frecuencia (Waterfall FFT, CWT, AR/Burg, Correlograma) |
| 4 | Histograma | Distribución probabilística (PDF empírica + ajuste Gaussiana, Weibull, Rician) |
| 5 | Potencia vs. Tiempo | Serie temporal de potencia media instantánea (dBFS) |
| 6 | SNR vs. Frecuencia | Relación señal-ruido por bin de frecuencia |

> **IMAGEN DEL PROGRAMA:** Capturar una vista general de la **interfaz completa** mostrando la barra de pestañas, el header y el panel lateral de configuración visible.

### 3.5.1. Subsistema de instrumentación estadística y representación en el dominio del tiempo

La Pestaña 2 (*Señal y Señal Filtrada*) presenta cuatro gráficas simultáneas organizadas en una disposición de 2×2:

- **Espectro RAW (cuadrante superior izquierdo):** Densidad espectral de potencia de la señal original sin filtrar, expresada en dBFS vs. MHz.
- **Amplitud RAW (cuadrante inferior izquierdo):** Forma de onda temporal de la componente en fase (I) de la señal original.
- **Espectro Filtrado (cuadrante superior derecho):** Densidad espectral de potencia de la señal tras aplicar el filtro de media móvil.
- **Amplitud Filtrada (cuadrante inferior derecho):** Forma de onda temporal de la señal filtrada.

Esta disposición permite al investigador evaluar visualmente el efecto del filtrado de media móvil sobre la señal antes y después de su aplicación.

> **IMAGEN DEL PROGRAMA:** Capturar la **Pestaña 2 (Señal y Señal Filtrada)** completa mostrando las 4 gráficas simultáneas con una señal activa.

### 3.5.2. Subsistema de densidad espectral de potencia y soporte multibanda

La Pestaña 5 (*Potencia vs. Tiempo*) presenta la evolución temporal de la potencia media espectral instantánea, calculada como el promedio aritmético en escala logarítmica de todos los bins del espectro RAW en cada ventana de análisis.

Adicionalmente, la Pestaña 6 (*SNR vs. Frecuencia*) presenta un gráfico de la relación señal-ruido por bin de frecuencia, permitiendo identificar las frecuencias donde la señal supera significativamente al piso de ruido.

> **IMAGEN DEL PROGRAMA:** Capturar la **Pestaña 5 (Potencia vs. Tiempo)** mostrando la serie temporal de potencia.

> **IMAGEN DEL PROGRAMA:** Capturar la **Pestaña 6 (SNR vs. Frecuencia)** mostrando los picos de SNR sobre la banda de interés.

### 3.5.3. Subsistema de visualización tiempo-frecuencia (Espectrogramas concurrentes)

La Pestaña 3 (*Espectrograma*) constituye el subsistema más completo de análisis, ofreciendo cuatro métodos de representación tiempo-frecuencia seleccionables de forma dinámica:

1. **Waterfall FFT (por defecto):** Espectrograma clásico basado en la Transformada Rápida de Fourier, donde cada línea horizontal representa un espectro instantáneo y el eje vertical codifica el tiempo transcurrido. La escala de color mapea la potencia espectral en dBFS.

2. **CWT/Morlet 2D:** Espectrograma basado en la Transformada Wavelet Continua con wavelet de Morlet bilateral. Este método proporciona una resolución adaptativa: mayor resolución temporal para componentes de alta frecuencia y mayor resolución frecuencial para componentes de baja frecuencia.

3. **AR/Burg (Cascada):** Espectrograma paramétrico donde cada línea se calcula mediante un modelo autorregresivo de Burg. Ofrece una resolución espectral superior a la FFT para señales con componentes estrechamente espaciadas.

4. **Correlograma (Cascada):** Espectrograma indirecto calculado como la FFT de la función de autocorrelación estimada con ventana de Bartlett. El lag máximo de la autocorrelación controla la resolución espectral.

> **IMAGEN DEL PROGRAMA:** Capturar la **Pestaña 3 (Espectrograma)** mostrando el Waterfall FFT con la banda de 1420.4 MHz visible.

> **IMAGEN DEL PROGRAMA (alternativa):** Capturar la misma pestaña con el método **AR/Burg** seleccionado para comparación visual.

### 3.5.4. Subsistema de análisis y ajuste interactivo de funciones de densidad de probabilidad (PDF)

La Pestaña 4 (*Histograma*) presenta la distribución empírica de la magnitud o fase de la señal I/Q cruda, representada como un histograma normalizado. Sobre este histograma empírico, el sistema superpone el ajuste por estimación de máxima verosimilitud (MLE) de tres funciones de densidad de probabilidad teóricas, las cuales se detallan en la Tabla 8.

> **Tabla 8.** *Funciones de Densidad de Probabilidad (PDF) implementadas para el análisis estadístico.*

| Distribución | Parámetros Estimados | Aplicación en el Contexto del Radiotelescopio |
|:---|:---|:---|
| **Gaussiana (Normal)** | $\mu$ (Media), $\sigma$ (Desviación Estándar) | Representación ideal del ruido térmico puramente gaussiano sin presencia de señales deterministas. |
| **Weibull** | $k$ (Forma), $\lambda$ (Escala) | Modelado de ruido impulsivo severo (RFI corto) y colas pesadas en la distribución de amplitud. |
| **Rician** | $\nu$ (No-centralidad), $\sigma$ (Escala) | Detección de una componente de señal determinista (ej. portadora o señal de hidrógeno neutro) sumada al ruido térmico. |


El ajuste se realiza mediante la función `scipy.stats.{norm,weibull_min,rice}.fit()`, la cual emplea internamente el método de máxima verosimilitud para estimar los parámetros óptimos de cada distribución a partir de los datos observados.

> **IMAGEN DEL PROGRAMA:** Capturar la **Pestaña 4 (Histograma)** mostrando el histograma empírico con las tres curvas de ajuste superpuestas (Gaussiana en azul, Weibull en verde, Rician en rojo).

---

## 3.6. Entorno de Simulación y Calibración del Sistema

### 3.6.1. Protocolo de calibración de amplitud espectral

El sistema incluye un mecanismo de estabilización automática del piso de ruido que opera a nivel del motor DSP. Este mecanismo compensa las fluctuaciones térmicas que provocan variaciones en el nivel de ruido de fondo entre frames consecutivos. El procedimiento es el siguiente:

1. Se calcula la mediana del espectro de potencia del frame actual (m_actual).
2. Se compara con una línea base almacenada (m_base), la cual se actualiza adaptativamente con una constante temporal lenta (alpha_base = 0.10).
3. Si la diferencia excede 10 dB, el frame se clasifica como afectado por RFI impulsivo y se sustituye por el frame anterior.
4. En caso contrario, el frame se alinea a la línea base para eliminar el parpadeo visual:

$$P_{calibrado}[k] = P_{observado}[k] - m_{actual} + m_{base}$$

### 3.6.2. Módulo simulador de señales astronómicas y fuentes de prueba sintéticas

La plataforma soporta la reproducción de archivos de muestras I/Q pregrabadas (formato `.iq`) como fuente de datos alternativa al hardware BB60C. Este modo permite:

- Validar el funcionamiento del pipeline DSP sin necesidad del hardware físico.
- Reproducir grabaciones realizadas en el Observatorio Astronómico de Quito para análisis offline.
- Simular diferentes condiciones de observación variando la tasa de muestreo y el formato de cuantización.

El reproductor de archivos soporta control de velocidad de reproducción (`playback_speed`), pausa con navegación temporal entre frames (`seek_frames()`), y la grabación de nuevas sesiones I/Q a disco (`start_iq_recording()`). La Tabla 9 resume los formatos de datos binarios soportados por el motor de reproducción y escritura.

> **Tabla 9.** *Formatos de cuantización binaria soportados para archivos I/Q.*

| Formato | Bits por Muestra | Bytes por Muestra (I+Q) | Rango Dinámico Teórico | Uso Principal |
|:---|:---:|:---:|:---:|:---|
| `complex64` | 32 (Float) | 8 bytes | ~150 dB | Formato nativo de alta precisión para investigación |
| `int16` | 16 (Entero) | 4 bytes | ~96 dB | Grabaciones de larga duración (equilibrio tamaño/calidad) |
| `int8` | 8 (Entero) | 2 bytes | ~48 dB | Pruebas sintéticas de baja fidelidad |
| `uint8` | 8 (Sin signo) | 2 bytes | ~48 dB | Compatibilidad con SDR genéricos (RTL-SDR) |

> **IMAGEN DEL PROGRAMA:** Capturar la **Pestaña 1 (Inicio & Configuración)** mostrando la sección de "Fuente de Datos" con un archivo .iq seleccionado y los controles de reproducción activos.

---

## Referencias del Capítulo III

- Burg, J. P. (1975). *Maximum Entropy Spectral Analysis* [Tesis doctoral, Stanford University]. (p. 34, Section 3 "The Burg Algorithm").
- Signal Hound. (2024). *BB60C API Programming Guide* (Rev. 4.5). Signal Hound Inc. https://signalhound.com/sigdownloads/BB60C/BB-Series-API-Manual.pdf
- Welch, P. D. (1967). The use of fast Fourier transform for the estimation of power spectra: A method based on time averaging over short, modified periodograms. *IEEE Transactions on Audio and Electroacoustics*, AU-15(2), 70-73. https://doi.org/10.1109/TAU.1967.1161901
