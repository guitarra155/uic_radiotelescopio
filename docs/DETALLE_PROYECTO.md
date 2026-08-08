# Detalles Técnicos del Proyecto: UIC Radiotelescopio

> Última actualización: 2026-08-07  
> Autor del sistema: UIC — Plataforma DSP para Radiotelescopio

---

## 1. Arquitectura del Sistema

El proyecto sigue una arquitectura de tres capas estrictamente desacopladas:

```
┌─────────────────────────────────────────────────────────┐
│  CAPA UI  (ui/)                                         │
│  Flet + Matplotlib → pestañas, componentes, gráficas   │
├─────────────────────────────────────────────────────────┤
│  CAPA CORE  (core/)                                     │
│  Motor DSP, constantes, registro de algoritmos, BB60C  │
├─────────────────────────────────────────────────────────┤
│  CAPA DATOS  (Resultados_Datos/, archivos .iq)          │
│  Persistencia binaria y capturas de pantalla           │
└─────────────────────────────────────────────────────────┘
```

### Árbol completo de módulos

```
c:\uic_radiotelescopio\
├── main.py                         ← Punto de entrada, orquestador UI + pubsub
├── requirements.txt
│
├── core\
│   ├── __init__.py
│   ├── constants.py                ← Paletas de color (dark/light/white), constantes globales
│   ├── dsp_engine.py               ← Motor DSP multihilo, buffers circulares, hardware BB60C
│   ├── advanced_dsp.py             ← Algoritmos AR/Burg, CWT, Welch, Correlograma
│   ├── algo_registry.py            ← Registro centralizado de algoritmos DSP avanzados
│   ├── config.json                 ← Configuración persistente (frecuencia, tema, ventana, etc.)
│   └── bbdevice\
│       ├── bb_api.py               ← Wrapper ctypes para la DLL de Signal Hound
│       ├── bb_api.dll              ← Biblioteca nativa Windows del BB60C
│       └── ftd2xx.dll              ← Driver USB FTDI requerido por bb_api.dll
│
├── ui\
│   ├── __init__.py
│   ├── charts\
│   │   ├── __init__.py             ← Re-exporta todas las chart_*, aplica lock MPL
│   │   ├── base.py                 ← fig_to_b64, get_cached_fig, style_ax, export_active_chart
│   │   ├── cache.py                ← Objeto cache compartido (dict de figuras)
│   │   ├── monitoring.py           ← chart_amplitude, chart_amplitude_ma, chart_spectrum, chart_spectrum_raw
│   │   ├── spectrogram.py          ← chart_spectrogram, chart_cwt_map, chart_ar_spectrogram, chart_correlogram_spectrogram
│   │   ├── statistics.py           ← chart_histogram, chart_signal_time
│   │   ├── signal_analysis.py      ← chart_power_time
│   │   ├── freq_snr.py             ← chart_freq_snr
│   │   └── algorithms.py           ← chart_ar_spectrum, chart_welch_spectrum, chart_correlogram_spectrum
│   ├── components\
│   │   ├── __init__.py
│   │   ├── layout.py               ← build_header(), build_footer()
│   │   └── shared.py               ← txt_field(), panel(), border_all()
│   └── tabs\
│       ├── __init__.py
│       ├── estado.py               ← Tab 0: Estado del sistema, glosario, configuración de ventana
│       ├── dual_monitoring.py      ← Tab 1: Señal RAW vs. Filtrada MA
│       ├── spectrogram.py          ← Tab 2: Espectrograma (FFT / CWT / AR / Correlograma)
│       ├── statistics.py           ← Tab 3: Histograma y estadística IQ
│       ├── signal_analysis.py      ← Tab 4: Potencia vs. Tiempo
│       ├── freq_snr.py             ← Tab 5: SNR vs. Frecuencia
│       ├── algo_tab.py             ← Contenedor del tab de algoritmos avanzados
│       └── algo_result.py          ← Panel de resultado de cada algoritmo DSP
│
├── scripts\
│   ├── create_dummy_iq.py          ← Generador de archivo .iq sintético para pruebas
│   └── test_bb60c.py               ← Script de diagnóstico de conexión del hardware BB60C
│
├── Resultados_Datos\               ← Capturas PNG, archivos .iq exportados por Smart Trigger
│
└── docs\
    ├── DETALLE_PROYECTO.md         ← Este documento
    ├── MANUAL_USUARIO.md           ← Manual de operación
    ├── BB60-API-Manual.pdf         ← Manual oficial API Signal Hound BB60C
    └── BB60C-User-Manual.pdf       ← Manual de usuario físico del hardware BB60C
```

---

## 2. Flujo de Funcionamiento

```
Inicio (main.py)
  │
  ├─ engine_instance.load_config()       → Lee core/config.json
  ├─ build_estado(), build_dual_monitoring(), ...  → Construye 6 pestañas
  ├─ page.run_task(refresh_loop)         → Tarea asíncrona a 20 Hz
  │
  └─ Usuario interactúa
       │
       ├─ Inicia stream (F5 / botón Play)
       │     DSPEngine._stream_thread (threading.Thread)
       │       ├─ Modo SDR    → bb_api.py → BB60C → muestras IQ
       │       └─ Modo Archivo → lee .iq binario por bloques
       │
       ├─ engine.data_ready = True
       │     refresh_loop detecta el flag → pubsub "refresh_charts"
       │     Cada tab activo llama chart_*() → Matplotlib → SVG b64 → ft.Image
       │
       ├─ Smart Trigger activo
       │     Umbral alto superado → inicia buffer de captura
       │     Energía cae bajo umbral bajo → recorta ±1.5 s → guarda .iq en Resultados_Datos/
       │
       └─ Pausa (⏸️)
             Seek frame a frame con ◀/▶
             Recálculo de algoritmos avanzados sobre bloque congelado
```

---

## 3. Descripción Detallada de Módulos y Funciones

### 3.1 `main.py`

| Función / Bloque | Responsabilidad |
|---|---|
| `main(page)` | Carga config, construye la UI completa, registra handlers de teclado y pubsub |
| `on_keyboard(e)` | F5=Play/Stop, F8=Emergency Stop, F11=Fullscreen, ←/→=Seek, Ctrl+Tab=nav, Ctrl+Shift+B=sidebar |
| `switch_to_tab(idx)` | Cambia la pestaña activa, actualiza sidebar y topbar, notifica via pubsub |
| `refresh_loop()` | Coroutine asíncrona (asyncio) que sondea `engine.data_ready` a 50 ms y envía `refresh_charts` |
| `on_main_pubsub(msg)` | Gestiona `config_reset`, `apply_theme`, `toggle_fullscreen_chart` |

### 3.2 `core/constants.py`

Define tres paletas (`dark`, `light`, `white`) con las siguientes claves por paleta:
`DARK_BG`, `PANEL_BG`, `ACCENT_CYAN`, `ACCENT_GREEN`, `ACCENT_RED`, `ACCENT_AMBER`,
`TEXT_MAIN`, `TEXT_MUTED`, `BORDER_COL`, `MPL_BG`, `MPL_AXBG`, `MPL_GRID`, `MPL_TEXT`,
`SIDEBAR_ACTIVE_BG`, `COLOR_PURPLE`, `COLOR_ORANGE`, `COLOR_PINK`.

La función `set_theme(name)` inyecta la paleta seleccionada como variables globales del módulo.

### 3.3 `core/dsp_engine.py` — `DSPEngine`

Clase singleton (`engine_instance`) con las siguientes responsabilidades:

| Atributo / Método | Descripción |
|---|---|
| `load_config()` / `save_config()` | Serialización JSON de todos los parámetros a `core/config.json` |
| `start_stream()` / `stop_stream()` | Lanza / detiene `_stream_thread` de forma segura con `threading.Event` |
| `_stream_loop_iq()` | Lee bloques del archivo .iq y llena los buffers circulares |
| `_stream_loop_sdr()` | Adquiere muestras del BB60C vía `bb_api`, aplica VBW smoothing |
| `_run_fft(iq)` | Ventana Hanning → FFT → conversión a dBm/Hz |
| `smart_trigger_step(iq)` | Implementa el detector de doble umbral (histéresis) |
| `seek_frames(n)` | Desplaza el puntero de lectura del buffer histórico para modo pausa |
| Buffers circulares | `deque` de `N` frames: `iq_buf`, `fft_buf`, `power_buf`, `freq_buf` |

### 3.4 `core/advanced_dsp.py`

| Función | Algoritmo |
|---|---|
| `run_ar_burg(iq, order, n_freqs, ...)` | Modelo AR por método de Burg |
| `run_cwt(iq, fs, center_freq, ...)` | CWT Morlet (análisis tiempo-frecuencia) |
| `run_welch(iq, fs, ...)` | Welch PSD con solapamiento configurable |
| `run_correlogram(iq, fs, ...)` | Correlograma (FFT de autocorrelación) |

### 3.5 `core/algo_registry.py`

Diccionario `ALGO_REGISTRY` con entradas por nombre de algoritmo. Cada entrada especifica:
`color`, `full_name`, `desc`, `params` (lista de parámetros configurables), `runner` (callable de `advanced_dsp`), `chart_func` (callable de `ui/charts/algorithms`).

### 3.6 `core/bbdevice/bb_api.py`

Wrapper ctypes sobre `bb_api.dll` (Signal Hound). Expone las constantes del hardware
(`BB_AUTO_GAIN`, `BB_AUTO_ATTEN`, etc.) y las funciones de bajo nivel:
`bbOpenDevice`, `bbConfigureCenter`, `bbConfigureAcquisition`, `bbInitiate`,
`bbFetchRaw`, `bbCloseDevice`, entre otras.

### 3.7 `ui/charts/base.py`

| Función | Descripción |
|---|---|
| `get_dynamic_figsize(page)` | Calcula tamaño de figura en pulgadas según `engine.window_width/height` |
| `get_cached_fig(key, ...)` | Devuelve figura de caché o la crea nueva |
| `fig_to_b64(fig)` | Renderiza SVG y lo codifica en base64 para `ft.Image` |
| `style_ax(ax)` | Aplica colores de la paleta activa al eje Matplotlib |
| `export_active_chart(key, fmt)` | Guarda PNG/SVG en `Resultados_Datos/` con marca de tiempo |
| `clear_chart_cache()` | Vacía el diccionario `cache` para forzar regeneración al cambiar tema |

### 3.8 `ui/tabs/` — Pestañas de la Aplicación

| Archivo | Tab # | Contenido |
|---|---|---|
| `estado.py` | 0 | Estado HW, enciclopedia/glosario, configuración resolución y línea |
| `dual_monitoring.py` | 1 | Amplitud RAW vs. MA + espectro RAW vs. suavizado |
| `spectrogram.py` | 2 | Waterfall, CWT, AR, Correlograma — selector de método |
| `statistics.py` | 3 | Histograma + KDE Gaussiana + señal en tiempo |
| `signal_analysis.py` | 4 | Potencia integrada acumulada vs. tiempo |
| `freq_snr.py` | 5 | SNR por canal con umbral de detección marcado |
| `algo_tab.py` | — | Contenedor reutilizable para pestañas de algoritmo |
| `algo_result.py` | — | Panel de parámetros + resultado gráfico por algoritmo |

### 3.9 `ui/components/`

| Archivo | Exports |
|---|---|
| `layout.py` | `build_header(page)`, `build_footer()` |
| `shared.py` | `txt_field(label, value, ...)`, `panel(content, ...)`, `border_all(content, ...)` |

---

## 4. Sistema de Navegación y Eventos (PubSub)

La aplicación usa el sistema `page.pubsub` de Flet como bus de mensajes interno:

| Mensaje | Emisor | Receptor |
|---|---|---|
| `"refresh_charts"` | `refresh_loop`, cambio de tema | Cada tab activo (actualiza gráficas) |
| `"refresh_charts_all"` | Seek en pausa | Todos los tabs |
| `"stream_stopped"` | `refresh_loop` | Tab de estado |
| `"tab_changed"` | `switch_to_tab` | `sdr_config` (sincroniza panel derecho) |
| `"toggle_stream"` | F5 | Tab de estado (botón Play/Stop) |
| `"emergency_stop"` | F8 | Tab de estado |
| `"open_iq_file_picker"` | Ctrl+O | Tab de estado |
| `"toggle_config_collapse"` | Ctrl+B | `sdr_config` |
| `("apply_theme", name)` | `sdr_config` | `main.py` |
| `"config_reset"` | `sdr_config` | `main.py` |
| `"toggle_fullscreen_chart"` | botón chart | `main.py` |
| `("maximize_dual_chart", idx)` | Ctrl+F1–F4 | `dual_monitoring` |
| `("maximize_spec", idx)` | Ctrl+F1–F4 | `spectrogram` |
| `("select_dual_chart", idx)` | F1–F4 | `dual_monitoring` |
| `("select_spec_method", idx)` | F1–F4 | `spectrogram` |

---

## 5. Dependencias del Sistema

### Python (runtime)

| Paquete | Versión | Rol |
|---|---|---|
| flet | 0.84.0 | Framework GUI multiplataforma (Flutter/Python) |
| flet-desktop | 0.84.0 | Módulo desktop de Flet |
| numpy | 2.4.4 | Operaciones vectoriales IQ, FFT, buffers |
| scipy | 1.17.1 | `scipy.signal` (filtros, Welch, ventanas) |
| matplotlib | 3.10.9 | Renderizado de todas las gráficas científicas |
| pillow | 12.2.0 | Procesamiento de imágenes (PNG export) |
| PyQt6 | 6.11.0 | Backend Qt para Matplotlib en entorno desktop |
| pyqtgraph | 0.14.0 | Gráficas rápidas auxiliares |
| lxml | 6.1.1 | Procesamiento XML/SVG |
| python-docx | 1.2.0 | Generación de informes Word |
| colorama | 0.4.6 | Salida de consola con color (Windows) |

### Binarios nativos (Windows)

| Archivo | Ruta | Descripción |
|---|---|---|
| `bb_api.dll` | `core/bbdevice/` | API Signal Hound BB60C (x64) |
| `ftd2xx.dll` | `core/bbdevice/` | Driver USB FTDI requerido por bb_api.dll |

### Bibliotecas estándar de Python (sin instalación)

`threading`, `asyncio`, `collections`, `json`, `os`, `sys`, `io`, `datetime`,
`base64`, `math`, `time`, `tkinter`, `ctypes`, `types`

---

## 6. Configuración Persistente (`core/config.json`)

El archivo almacena el estado completo de la sesión. Campos principales:

| Clave | Tipo | Descripción |
|---|---|---|
| `center_freq` | float | Frecuencia central en MHz |
| `sample_rate` | int | Tasa de muestreo en Hz |
| `fft_size` | int | Puntos de la FFT |
| `db_min` / `db_max` | float | Rango dinámico del eje Y en dBm |
| `theme` | str | `"dark"` / `"light"` / `"white"` |
| `window_res` | str | Resolución de ventana (ej. `"1920x1080"`) |
| `window_mode` | str | `"Normal"` / `"Maximizada"` / `"Pantalla Completa"` |
| `bb60c_ref_level` | float | Nivel de referencia BB60C en dBm |
| `bb60c_iq_bw` | float | Ancho de banda IQ en MHz |
| `vbw_alpha` | float | Factor de suavizado VBW (0.1–1.0) |
| `trigger_high` / `trigger_low` | float | Umbrales del Smart Trigger en dB |
| `algo_params` | dict | Parámetros persistidos por algoritmo |
| `stream_mode` | str | `"sdr"` / `"iq_file"` |

---

## 7. Atajos de Teclado

| Tecla | Acción |
|---|---|
| F5 | Iniciar / Detener stream |
| F8 | Parada de emergencia |
| F11 | Pantalla completa |
| ←  /  → (en pausa) | Retroceder / avanzar frame |
| Ctrl+Tab | Siguiente pestaña |
| Ctrl+Shift+Tab | Pestaña anterior |
| Ctrl+1…6 | Ir directamente a la pestaña N |
| Ctrl+Shift+1…6 | Toggle panel de pestaña N |
| Ctrl+O | Abrir selector de archivo .iq |
| Ctrl+B | Colapsar / expandir panel activo |
| Ctrl+Shift+B | Toggle sidebar / topbar |
| Ctrl+Shift+S | Toggle modo de navegación |
| F1–F4 (Tab 1) | Seleccionar gráfica del dual monitoring |
| F1–F4 (Tab 2) | Seleccionar método de espectrograma |
| Ctrl+F1–F4 | Maximizar gráfica en tab activo |

---

## 8. Scripts de Utilidad

| Script | Descripción |
|---|---|
| `scripts/create_dummy_iq.py` | Genera un archivo `.iq` sintético de señal sinusoidal + ruido para pruebas sin hardware |
| `scripts/test_bb60c.py` | Diagnóstico de conexión: intenta abrir el BB60C y reporta estado del dispositivo |
