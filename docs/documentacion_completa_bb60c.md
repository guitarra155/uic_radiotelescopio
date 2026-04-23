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
* **Sistemas Operativos:** Windows 7, 8, 10, 11 (64 bits) y Linux (arquitectura x64_86, específicamente Ubuntu 18.04 o superior).
