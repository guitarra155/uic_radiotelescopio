# Detalle Técnico del Proyecto: Plataforma DSP para Radiotelescopio (UIC)

## 1. Arquitectura del Sistema
El proyecto es una aplicación de escritorio desarrollada en Python enfocada en el Procesamiento Digital de Señales (DSP) para un radiotelescopio. Utiliza **Flet** (basado en Flutter) para la Interfaz de Usuario (UI) y un motor interno de DSP altamente optimizado en el backend. 

La arquitectura se divide en dos capas principales:
- **Core (Backend & DSP):** Encargado de la comunicación con el hardware SDR (Signal Hound BB60C u otros) y de la ejecución asíncrona de algoritmos matemáticos complejos.
- **UI (Frontend):** Responsable de la visualización en tiempo real de los datos mediante gráficas renderizadas de `matplotlib` a base64, controlando el flujo y estado global.

## 2. Flujo de Funcionamiento
1. **Inicialización:** `main.py` levanta la ventana de Flet e inicializa el motor `DSPEngine` (Singleton).
2. **Adquisición de Datos:** El módulo `bbdevice/bb_api.py` interactúa con el dispositivo físico en C/C++ vía ctypes. Obtiene datos IQ en bruto (raw).
3. **Procesamiento:** `DSPEngine` aloja un bucle asíncrono que extrae muestras, las normaliza y aplica filtros. Para el procesamiento avanzado, delega en `advanced_dsp.py` (Burg, CWT, MUSIC, Welch, Correlogram, etc.).
4. **Renderizado:** La interfaz se suscribe a los eventos del motor. Cuando hay nuevos datos, las pestañas activas solicitan a `charts.py` la generación de la gráfica correspondiente.
5. **Visualización:** El componente renderizado en Base64 se muestra en los contenedores Flet en tiempo real.

## 3. Modularización y Estructura de Directorios

- `main.py`: Punto de entrada, configuración de ventana, manejo de teclado y orquestador de pestañas de Flet.
- `core/`:
  - `dsp_engine.py`: Clase `DSPEngine`, maneja el buffer circular, hilos de lectura/escritura (SDR/Fichero), y estado de reproducción.
  - `advanced_dsp.py`: Implementación matemática de algoritmos avanzados (AR Burg, Transformada Wavelet Continua 1D/2D, Pseudo-MUSIC, ESPRIT, Welch, Correlograma, ASLT).
  - `bbdevice/`: Librerías y wrappers (`bb_api.py`) para comunicarse con el hardware de Signal Hound.
  - `constants.py` / `config.json`: Valores constantes y persistencia de la configuración.
- `ui/`:
  - `components/`: Elementos reutilizables de UI (`layout.py` para header/footer, `shared.py`).
  - `tabs/`: Controladores de cada vista (`monitoring.py`, `spectrogram.py`, `statistics.py`, `signal_analysis.py`, `freq_snr.py`, `sdr_config.py`, `algo_tab.py`, `algo_result.py`).
  - `charts.py`: Generador de gráficos con Matplotlib. Cachea figuras para optimizar el rendimiento.
- `data/`, `docs/`, `research/`, `scripts/`: Carpetas auxiliares.

## 4. Descripción Detallada de Funciones y Dependencias
### 4.1 Dependencias Clave
- **Flet:** Framework UI reactivo.
- **NumPy / SciPy:** Manejo vectorial de datos IQ y funciones de señal.
- **Matplotlib:** Generación de espectrogramas e histogramas.
- **ctypes:** Llamadas a la API compilada del dispositivo BB60C.

### 4.2 Motor DSP (`dsp_engine.py`)
- Mantiene hilos separados para no bloquear la UI.
- `DSPEngine.load_config() / save_config()`: Persistencia de estado.
- `DSPEngine._worker_read_sdr()`: Lectura del buffer de entrada desde el dispositivo físico usando las APIs BB.

### 4.3 UI (`charts.py` y `tabs`)
- Sistema de Caché (`ChartCache`): Evita instanciar múltiples figuras `matplotlib` en memoria por cada frame.
- Se utilizan funciones decoradas con `make_synchronized` para evitar colisiones de hilos de Flet sobre el renderizador de Matplotlib (que no es thread-safe).

## 5. Identificación de Acciones/Funciones Obsoletas o No Utilizadas

Tras un análisis del código fuente, se identifican las siguientes áreas con código muerto, obsoleto o en desarrollo (Placeholders):

1. **Funciones del API BB60C (`core/bbdevice/bb_api.py`) no utilizadas**:
   - De las decenas de funciones mapeadas de la API en C (ej. `bb_self_cal`, `bb_get_serial_number_list`, `bb_get_device_diagnostics`, `bb_configure_IO`, `bb_sync_CPU_to_GPS`, sweeps de UART), solo un pequeño subconjunto vital (`bb_open_device`, `bb_configure_IQ`, `bb_initiate`, `bb_get_IQ_unpacked`, `bb_abort`, `bb_close_device`) es llamado realmente desde `dsp_engine.py`. El resto del envoltorio (wrapper) es código muerto (o "latente" preparado para futuras versiones, pero actualmente sin uso en la aplicación).

## 6. Actualizaciones Recientes
- Se ajustó la ventana de auto-escalado (auto_y) para la gráfica de "Potencia vs. Tiempo" (`pow_time`), pasando de un margen de ±5.0 dB a ±15.0 dB.
- Se modificó el escalado automático del Eje X (`auto_x`) en todas las gráficas espectrales para mostrar el **100% del ancho de banda (Sample Rate)** en lugar del 75%. El usuario ahora visualiza todo el espectro capturado o los rangos manuales que seleccione sin recortes predeterminados.

## 7. Siguientes Pasos
- Limpiar el código de la API del BB60C si no se prevén usos de hardware avanzados como sincronización GPS o Sweeps en UART.
- Optimizar la transferencia de memoria si se integran algoritmos 2D pesados.
