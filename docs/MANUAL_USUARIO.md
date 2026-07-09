# Manual de Usuario: Plataforma DSP para Radiotelescopio (UIC)

Este manual proporciona una guía paso a paso para operar la plataforma de procesamiento digital de señales (DSP) para radiotelescopio, diseñada para el hardware SDR **Signal Hound BB60C** y análisis de datos en diferido.

---

## 1. Requisitos y Preparación del Sistema

### Requisitos del Sistema
- **Sistema Operativo:** Windows 10/11 (64-bit).
- **Python:** Versión 3.10 o superior instalada.
- **Controladores del SDR:** Driver oficial de Signal Hound instalado (`bb_api.dll` debe encontrarse en la carpeta `core/bbdevice/`).
- **Dependencias Python:** Instaladas a través de `pip install -r requirements.txt` (incluye `flet`, `numpy`, `scipy` y `matplotlib`).

### Conexión del Hardware (Modo SDR Real)
1. Conecte el dispositivo **Signal Hound BB60C** a un puerto USB 3.0 de alta velocidad en su computadora (evite hubs USB no alimentados).
2. Asegúrese de que el cable coaxial de la antena del radiotelescopio o el generador de señales esté acoplado al puerto `RF IN` del BB60C.
3. Si desea utilizar geolocalización o sincronización temporal de alta precisión, conecte una antena GPS compatible al puerto `GPS` (opcional).

---

## 2. Puesta en Marcha y Modos de Funcionamiento

### Ejecución de la Aplicación
Abra una terminal en la carpeta raíz del proyecto (`c:\uic_radiotelescopio`) y ejecute el siguiente comando:
```bash
python main.py
```
O de forma directa mediante Flet:
```bash
flet run main.py
```

### Modos de Adquisición de Datos
En el panel lateral derecho (**Origen de Datos**), puede alternar entre dos fuentes principales:
1. **Modo SDR (Tiempo Real):** Adquiere muestras directamente desde el hardware físico conectado.
2. **Modo Archivo (Diferido):** Lee y reproduce archivos de señal grabados previamente en formato binario estructurado `.iq` (muestras complejas representadas por pares flotantes `I` y `Q`).
   - Para cargar un archivo, haga clic en el botón de la carpeta 📁 y elija un archivo `.iq` de prueba (ej. dentro de la carpeta `data/`).

---

## 3. Guía de la Interfaz Gráfica de Usuario (GUI)

La interfaz se divide en dos bloques principales: el **Panel de Visualización (Izquierdo)** que contiene múltiples pestañas de análisis y el **Panel de Configuración (Derecho)** que controla la adquisición y sintonía del sistema.

### 3.1 Panel de Configuración (Lateral Derecho)
Este panel permite ajustar el comportamiento del motor DSP y del hardware en tiempo real:
- **Frecuencia Central (MHz):** Controla el oscilador local. Al cambiarlo y presionar *Enter* o hacer clic fuera del campo, el SDR físico se sintoniza instantáneamente sin detener la graficación (Sintonización al Vuelo).
- **Tasa de Muestreo (MSps):** Determina el ancho de banda capturado. Valores altos (ej. 10–40 MSps) muestran bandas anchas pero exigen alta capacidad de procesamiento.
- **Nivel de Referencia (dBm):** Ajusta la ganancia física del SDR. Use niveles bajos (ej. -80 dBm) para señales débiles de radioastronomía y valores altos (ej. 0 dBm) si detecta saturación en el espectro.
- **Ancho de Banda de Filtro (RBW/IQ BW):** Ajusta el filtro físico del SDR. Reducirlo minimiza el ruido térmico capturado en los bordes de la señal.
- **VBW Smoothing:** Filtro de suavizado de video temporal sobre el espectro dibujado (1.0 = tiempo real caótico, 0.1 = promedio muy suave que revela portadoras débiles).
- **Ventana de Adquisición (s):** Duración en segundos del bloque de muestras que se procesa en cada actualización.
- **Historial Cascada (s):** Duración del historial temporal que se acumula en el espectrograma 2D.

---

### 3.2 Pestañas de Visualización y Análisis (Panel Izquierdo)

La plataforma cuenta con 7 secciones independientes especializadas:

#### Pestaña 1: Señal Original vs Filtrada (RAW/MA)
Muestra la amplitud de la señal en el dominio del tiempo y su espectro de frecuencias.
- **Gráfica de Amplitud:** Compara la señal compleja en bruto (RAW) frente a la señal suavizada mediante el filtro *Moving Average* (MA) que reduce el ruido de alta frecuencia en tiempo real.
- **Gráfica de Espectro:** Permite observar interferencias de radiofrecuencia (RFI) y la potencia de banda.

#### Pestaña 2: Espectrograma (Cascada)
Representación tridimensional de la señal (Tiempo vs Frecuencia vs Potencia).
- **Visualización 2D (Waterfall):** El color representa la intensidad de potencia espectral (dBm). Es sumamente útil para detectar tránsitos de meteoros, satélites, RFI pulsante o derivas de frecuencia a lo largo del tiempo.
- **Modos de Espectrograma:** Puede alternar entre el espectrograma clásico (FFT), la Transformada Wavelet Continua (CWT - Morlet), el Espectrograma Autorregresivo (AR) o el Correlograma para identificar patrones ocultos.

#### Pestaña 3: Estadística e Histograma
Muestra la densidad de probabilidad de las amplitudes de las muestras I/Q.
- **Histograma & KDE Gaussiana:** Permite evaluar si el ruido del sistema se comporta como un ruido blanco gaussiano ideal. Si la campana de Gauss está deformada o tiene picos achatados en los extremos, indica la presencia de saturación en el ADC o fuertes interferencias no gaussianas.

#### Pestaña 4: Potencia vs Tiempo
Registra y grafica la potencia integrada instantánea de la señal analítica ($P = I^2 + Q^2$) acumulada en un búfer circular de alta velocidad.
- Ideal para monitorear ráfagas rápidas de radio (FRB) o pulsos transitorios de corta duración.

#### Pestaña 5: SNR vs Frecuencia
Calcula y muestra la Relación Señal a Ruido (SNR) para cada canal de frecuencia respecto al piso de ruido térmico base estimado.
- Posee un umbral dinámico de detección preconfigurado (ej. 6 dB). Las frecuencias que superan este umbral se consideran detecciones válidas y se marcan de forma destacada en la gráfica.

#### Pestaña 6: Algoritmo DSP (Matemáticas Avanzadas)
Aplica métodos de estimación espectral de alta resolución sobre la señal. Esta sección solo se activa cuando se detiene el flujo continuo (Pausa) para analizar un bloque estacionario de muestras con precisión matemática:
- **Welch PSD:** Reduce la varianza del ruido espectral promediando bloques con solapamiento.
- **Correlograma 1D:** Estimación espectral indirecta basada en la autocorrelación de la señal; revela señales periódicas débiles sumergidas en el ruido térmico.
- **AR/Burg:** Modelo autorregresivo que modela la señal mediante polos para entregar un espectro suave sin fugas espectrales (spectral leakage).
- **MUSIC y ESPRIT:** Algoritmos de subespacios que aíslan frecuencias sinusoidales puras con resolución matemática teórica infinita, separando el subespacio de la señal respecto al del ruido.

#### Pestaña 7: Estado
Muestra información sobre el estado del hardware, configuración del motor multihilo de procesamiento y provee una **Enciclopedia Técnica y Glosario** integrada para consultas rápidas. Además, cuenta con controles para cambiar la resolución de la ventana e inmediato redimensionado del grosor de las líneas en las gráficas.

---

## 4. Funciones Especiales y Operaciones Avanzadas

### 4.1 Pausa, Capturas y Navegación de Historial (Snapshot)
Cuando presiona el botón **Pausa (⏸️)** en el encabezado superior:
1. El motor detiene de forma segura la lectura física, pero mantiene el último bloque en memoria.
2. Se habilitan los botones de navegación temporal: **Retroceder (◀️)** y **Avanzar (▶️)**.
3. Puede desplazarse cuadro por cuadro por las capturas almacenadas temporalmente en el buffer histórico para examinar eventos transitorios con calma.
4. Puede ajustar los parámetros de cualquiera de los algoritmos de la **Pestaña 6** para recalcular espectros sobre el bloque de datos exactamente congelado.

### 4.2 Grabación de Datos en Bruto (IQ Recording)
La plataforma permite guardar la señal de radiofrecuencia entrante directamente a disco en formato binario `.iq` sin procesar:
1. Asegúrese de estar en **Modo SDR** en tiempo real.
2. Presione el botón **Grabar (⏺️)** en el panel superior. El botón cambiará de color indicando que la grabación está activa.
3. El sistema volcará el flujo binario I/Q directamente en la carpeta del proyecto bajo un nombre auto-generado con marca de tiempo.
4. Presione **Detener Grabación** para cerrar el archivo atómicamente evitando cualquier corrupción de datos. El archivo resultante puede ser cargado posteriormente en **Modo Archivo** para su reproducción y análisis.

### 4.3 Detección de Eventos con Smart Trigger
El **Smart Trigger** es un algoritmo diseñado para capturar pulsos de radioastronomía cortos y descartar ruido de fondo:
1. **Doble Umbral (Histéresis):** Utiliza un *Umbral Alto* para iniciar la captura de un pulso cuando la energía de la señal se dispara, y un *Umbral Bajo* para finalizar la captura cuando la energía retorna a niveles normales. Esto evita disparos falsos repetitivos debidos al ruido térmico.
2. **Recorte Inteligente (Trim $\pm 1.5s$):** Al detectarse un evento de disparo, el motor localiza el pico de energía exacto en el tiempo y extrae una ventana completa de 3 segundos (1.5 segundos antes y 1.5 segundos después del pico).
3. **Exportación Automática:** El evento recortado se almacena inmediatamente en la carpeta `Resultados_Datos/` como un archivo binario `.iq` limpio para su análisis riguroso posterior.

### 4.4 Captura de Gráficas y Resultados
Cualquier gráfica visualizada en la pantalla de la plataforma puede ser exportada en alta resolución:
- Presione el botón **Capturar Gráfica** o el icono de guardado disponible en el tab correspondiente.
- Las imágenes exportadas se guardan de manera automática en la carpeta `Resultados_Datos/` en formatos estandarizados (PNG/SVG) junto con metadatos descriptivos de los parámetros físicos de sintonía en el momento exacto de la captura.

---

## 5. Solución de Problemas (Troubleshooting)

- **El software indica "Hardware no detectado" o "Error BB60C":**
  * Verifique que el dispositivo SDR esté bien alimentado y conectado a un puerto USB 3.0 (azul).
  * Asegúrese de que no haya otra instancia de la aplicación o software de Signal Hound (como Spike) bloqueando el acceso al puerto del dispositivo.
  * Compruebe que la biblioteca `bb_api.dll` esté presente en la ruta `core/bbdevice/`.

- **Las gráficas se ven lentas o se congelan:**
  * Si está usando una tasa de muestreo muy alta (ej. superior a 20 MSps), reduzca el valor de la *Tasa de Muestreo* en el panel de configuración o incremente el valor del *Filtro RBW* para aliviar la carga del procesador.
  * Verifique que la CPU no esté al 100% de uso por otros procesos del sistema.

- **La campana del histograma muestra líneas verticales planas en los extremos:**
  * Esto es señal de saturación analógica (`ADC Overflow`). Suba el *Nivel de Referencia* en el panel derecho (ej. de -80 dBm a -40 dBm o 0 dBm) para atenuar la señal de entrada y evitar el recorte de amplitud del conversor analógico-digital.
