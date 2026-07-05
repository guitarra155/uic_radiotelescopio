# Detalle Técnico del Proyecto: Plataforma DSP para Radiotelescopio (UIC)

> **Última actualización:** 2026-06-26 | **Versión de refactor:** 2.0 (modularización Fases 1–3)

---

## 1. Arquitectura del Sistema

Aplicación de escritorio Python para DSP de radiotelescopio. Usa **Flet** (Flutter) para UI y un motor DSP interno.

### Capas del sistema
```
main.py
├── core/               ← Backend y motor DSP
│   ├── dsp_engine.py   ← Singleton DSPEngine (estado, I/O, procesamiento)
│   ├── advanced_dsp.py ← Algoritmos matemáticos aislados
│   ├── algo_registry.py← ★ NUEVO: fuente única de verdad de algoritmos
│   ├── constants.py    ← Colores y constantes de tema
│   ├── config.json     ← Persistencia de configuración
│   └── bbdevice/       ← Wrapper ctypes para hardware BB60C
└── ui/                 ← Frontend Flet + Matplotlib
    ├── components/     ← Header, Footer, widgets reutilizables
    ├── tabs/           ← Un módulo por pestaña (build_*)
    └── charts/         ← ★ NUEVO: paquete modular de gráficas
        ├── __init__.py ← Re-exporta todo + thread-safety automático
        ├── cache.py    ← ChartCache singleton + config Matplotlib
        ├── base.py     ← Utilidades compartidas (figsize, caché, SVG)
        ├── monitoring.py      ← Charts del Tab 1 (RAW vs Filtrada)
        ├── spectrogram.py     ← Charts del Tab 2 (Waterfall, CWT, AR 2D, Corr 2D)
        ├── statistics.py      ← Charts del Tab 3 (Histograma, KDE)
        ├── signal_analysis.py ← Charts del Tab 4 (Potencia vs Tiempo)
        ├── freq_snr.py        ← Charts del Tab 5 (SNR vs Frecuencia)
        └── algorithms.py      ← Charts del Tab 6 (AR, MUSIC, Welch, Correlograma)
```

---

## 2. Flujo de Funcionamiento

1. **Arranque:** `main.py` inicia Flet, carga `DSPEngine.load_config()` y construye todos los tabs.
2. **Adquisición:** `DSPEngine` corre en hilos separados — `_worker_read_file()` o `_worker_read_sdr()`.
3. **Procesamiento:** El motor calcula FFT, moving average y waterfall. Para algoritmos avanzados, delega en `core/advanced_dsp.py`.
4. **Notificación:** El flag `data_ready = True` activa el `refresh_loop` en `main.py` → `page.pubsub.send_all("refresh_charts")`.
5. **Renderizado:** Cada tab escucha el pubsub. Llama a la función `chart_*` del paquete `ui/charts/`. Estas funciones actualizan artistas en caché y serializan la figura a SVG Base64.
6. **Visualización:** El componente `ft.Image` recibe el Base64 y Flet lo muestra en pantalla.

---

## 3. Estructura de Directorios (Post-Refactor)

```
c:\uic_radiotelescopio\
├── main.py
├── requirements.txt
├── core/
│   ├── __init__.py
│   ├── constants.py
│   ├── config.json
│   ├── dsp_engine.py      (1670 líneas — Fase 4 pendiente)
│   ├── advanced_dsp.py    (817 líneas)
│   ├── algo_registry.py   ← NUEVO (Fase 2)
│   └── bbdevice/
│       ├── bb_api.py
│       ├── bb_api.dll
│       └── ftd2xx.dll
├── ui/
│   ├── __init__.py
│   ├── charts/            ← NUEVO paquete (Fase 3, reemplaza charts.py monolítico)
│   │   ├── __init__.py
│   │   ├── cache.py
│   │   ├── base.py
│   │   ├── monitoring.py
│   │   ├── spectrogram.py
│   │   ├── statistics.py
│   │   ├── signal_analysis.py
│   │   ├── freq_snr.py
│   │   └── algorithms.py
│   ├── components/
│   │   ├── layout.py
│   │   └── shared.py
│   └── tabs/
│       ├── algo_result.py  (usa ALGO_REGISTRY)
│       ├── algo_tab.py     (usa ALGO_REGISTRY)
│       ├── dual_monitoring.py
│       ├── estado.py
│       ├── freq_snr.py
│       ├── monitoring.py
│       ├── signal_analysis.py
│       ├── spectrogram.py
│       ├── sdr_config.py
│       └── statistics.py
├── data/              ← Archivos .iq de prueba
├── docs/
│   ├── DETALLE_PROYECTO.md
│   ├── MANUAL_USUARIO.md  ← NUEVO (Manual de usuario en español)
│   └── esquema_proyecto.puml ← NUEVO (Esquema de arquitectura en PlantUML)
├── research/
│   └── ...
├── scripts/
└── Resultados_Datos/
```

---

## 4. Sistema de Registro de Algoritmos (`core/algo_registry.py`)

### Propósito
Fuente única de verdad para todos los algoritmos DSP. Antes, la metadata estaba duplicada en `algo_tab.py` (`_ALGO_INFO`) y `algo_result.py` (`_ALGO_META`). Ahora ambos leen de `ALGO_REGISTRY`.

### Estructura de una entrada
```python
"AR/Burg": {
    "color":      "#B380FF",          # Color de acento en la UI
    "full_name":  "Modelo AR...",     # Nombre completo para mostrar
    "desc":       "...",              # Descripción para el panel lateral
    "params_hint":"...",              # Texto de ayuda de parámetros
    "param_keys": ["ar_order", ...],  # Claves en engine.algo_params
    "runner":     "run_ar_burg",      # Función en advanced_dsp.py
    "chart_fn":   "chart_ar_spectrum",# Función en ui/charts/algorithms.py
    "result_key": "ar",               # Clave en engine.algo_results
}
```

### Cómo agregar un nuevo algoritmo
1. Implementar `run_nuevo_algo(iq, ...) -> dict` en `core/advanced_dsp.py`
2. Implementar `chart_nuevo_algo(result) -> str` en `ui/charts/algorithms.py`
3. Añadir una entrada en `core/algo_registry.py`
4. Importar `chart_nuevo_algo` en `ui/charts/__init__.py`
→ **Cero cambios** en `main.py`, `sdr_config.py`, `algo_result.py`

---

## 5. Paquete `ui/charts/` — Descripción de Módulos

| Módulo | Función exportada | Tab |
|--------|-------------------|-----|
| `monitoring.py` | `chart_amplitude`, `chart_amplitude_ma`, `chart_spectrum`, `chart_spectrum_raw` | 1 |
| `spectrogram.py` | `chart_spectrogram`, `chart_cwt_map`, `chart_ar_spectrogram`, `chart_correlogram_spectrogram` | 2 |
| `statistics.py` | `chart_histogram`, `chart_signal_time` | 3 |
| `signal_analysis.py` | `chart_power_time` | 4 |
| `freq_snr.py` | `chart_freq_snr` | 5 |
| `algorithms.py` | `chart_ar_spectrum`, `chart_music_spectrum`, `chart_welch_spectrum`, `chart_correlogram_spectrum` | 6 |
| `base.py` | `get_cached_fig`, `fig_to_b64`, `style_ax`, `safe_set_*lim`, etc. | — |
| `cache.py` | `cache` (singleton `ChartCache`) | — |

El `__init__.py` aplica `make_synchronized` a todas las funciones `chart_*` con un único `threading.Lock()` compartido.

---

## 6. Dependencias Clave

| Librería | Versión | Uso |
|----------|---------|-----|
| `flet` | 0.84.0 | Framework UI reactivo |
| `numpy` | 2.4.4 | Arrays IQ, FFT |
| `scipy` | 1.17.1 | KDE, filtros |
| `matplotlib` | 3.10.9 | Renderizado gráficas (backend Agg → SVG Base64) |
| `ctypes` | stdlib | Interfaz con `bb_api.dll` (hardware BB60C) |

---

## 7. Cambios Recientes (Fase 1–3 Refactor)

### Eliminados
- `ui/charts.py` (1145 líneas) → reemplazado por paquete `ui/charts/`
- `ui/charts_corr_patch.py` → absorbido en `ui/charts/spectrogram.py`
- `ui/tabs/monitoring_filtered.py` → código muerto, no era importado

### Creados
- `core/algo_registry.py` → registro centralizado de algoritmos
- `ui/charts/` → paquete modular de 8 archivos (~1200 líneas totales, pero organizadas)
- `docs/MANUAL_USUARIO.md` → manual de usuario detallado paso a paso para el radiotelescopio
- `docs/esquema_proyecto.puml` → diagrama completo de arquitectura y flujo de datos en código PlantUML

### Optimizaciones e Información adicional
- **Ajustes Estadísticos Avanzados (Weibull y Rician):** Se incorporó soporte en tiempo real para estimar y ajustar curvas de distribución probabilística **Weibull** y **Rician** sobre el histograma de magnitudes de señal ([statistics.py](file:///c:/uic_radiotelescopio/ui/charts/statistics.py)).
- **Criterio de Ajuste Dinámico:** Se calcula la suma de errores cuadráticos acumulados (SSE) sobre las PDFs teóricas para clasificar dinámicamente si la señal actual se comporta como ruido Gaussiano (térmico), Rician (señal determinista) o Weibull (interferencias/colas pesadas), mostrando los parámetros resultantes y el tipo de señal detectada en la UI en vivo ([statistics.py](file:///c:/uic_radiotelescopio/ui/tabs/statistics.py)).
- **Corrección Matemática en Modo Fase:** Se sustituyó la campana de Gauss por una línea recta teórica constante que modela la distribución **Uniforme** ($1 / 2\pi \approx 0.159$) cuando la gráfica del histograma está configurada en modo Fase, previniendo visualizaciones matemáticamente incorrectas.
- **Switches Interactivos de Curvas:** Se integró una sección de "Ajustes de Curva" dentro del panel de configuración lateral derecho (`ui/tabs/sdr_config.py`). Esta sección solo se visualiza cuando el usuario está posicionado en la pestaña de estadística (idx=3), permitiendo alternar de forma independiente la visualización de las curvas teóricas Gauss, Weibull, Rician o KDE utilizando los controles visuales estandarizados `make_toggle` y liberando espacio de la gráfica en el panel central.
- **Paneles Laterales Colapsables:** Se generalizó el comportamiento de ocultación de paneles laterales mediante la inserción de un control interactivo `btn_toggle_side` (`ft.IconButton`) con icono `ft.Icons.VIEW_SIDEBAR` en los headers de las gráficas de las pestañas **Histograma & Estadística** ([statistics.py](file:///c:/uic_radiotelescopio/ui/tabs/statistics.py)), **Potencia vs. Tiempo** ([signal_analysis.py](file:///c:/uic_radiotelescopio/ui/tabs/signal_analysis.py)) y **SNR vs. Frecuencia** ([freq_snr.py](file:///c:/uic_radiotelescopio/ui/tabs/freq_snr.py)). Al pulsarlo, el respectivo panel derecho de información y estadísticas del buffer se minimiza a voluntad, permitiendo que la gráfica se expanda automáticamente a pantalla completa para una visualización en detalle.
- **Optimización de Rendimiento por Submuestreo (Downsampling):** Se limitó el cálculo de ajustes pesados (`weibull_min.fit`, `rice.fit` y `gaussian_kde`) mediante el submuestreo del buffer de magnitudes a un tamaño máximo de 500 muestras, además de omitir los cómputos de las curvas desactivadas. Esto reduce la carga computacional en más de un 90% garantizando una tasa de refresco fluida y en tiempo real.
- **Remoción de Terminología Redundante:** Se eliminaron las referencias al término "Smart Trigger" en los comentarios y etiquetas de la pestaña de estadística para mejorar la coherencia científica de la interfaz.
- `_render_2d_waterfall()` en `spectrogram.py` unifica la lógica de los tres espectrogramas 2D (evita ~200 líneas duplicadas)
- Thread-safety centralizado en `__init__.py` (antes en el final de `charts.py`)
- Corregida la Enciclopedia Técnica y Glosario en `ui/tabs/estado.py` para incluir la pestaña de *Potencia vs Tiempo* que faltaba, y se integró un panel interactivo del **Manual de Usuario Rápido** directo en la UI.
- **Actualización Integral del Glosario y Manual de Usuario:** Se modificó la Enciclopedia Técnica en [estado.py](file:///c:/uic_radiotelescopio/ui/tabs/estado.py#L325-L425) para documentar el ajuste estadístico multiprobabilístico (**Weibull y Rician**), se eliminó la denominación obsoleta de "Smart Trigger" sustituyéndola por **Detección de Transitorios y Recorte**, y se creó la sección interactiva **Atajos de Teclado y Control** para guiar al usuario en el uso de atajos (`CTRL + [1-6]`, `CTRL + TAB`, `CTRL + B` y `CTRL + SHIFT + B`).
- **Corrección de Carga en Espectrograma 2D:** Se resolvió el retardo/desvanecimiento inicial al ingresar a la pestaña de Espectrograma ([spectrogram.py](file:///c:/uic_radiotelescopio/ui/tabs/spectrogram.py#L40-L60)). Ahora el método seleccionado en la configuración (`spec2d_method`) se sincroniza inmediatamente con el motor DSP (`active_spec_method`) al inicializar el módulo, y la fuente de la imagen (`img.src`) se carga con el gráfico correspondiente del método activo por defecto desde el primer instante.
- **Formateo inteligente de flotantes:** Se implementó `fmt_float()` en `estado.py` y `sdr_config.py` para limpiar ceros a la derecha redundantes en las entradas numéricas (ej. `2.4` en lugar de `2.40000000`), manteniendo la capacidad de sintonizar y operar con máxima precisión (hasta 8 decimales).
- **Atajos de Teclado para Navegación y Colapso:** 
  - Se incorporaron atajos de teclado al handler `on_keyboard` en [main.py](file:///c:/uic_radiotelescopio/main.py#L38-L46) para cambiar de pestaña al presionar `CTRL + Número` (1 a 6).
  - **Navegación Secuencial (CTRL + TAB / CTRL + SHIFT + TAB):** Permite rotar cíclicamente hacia adelante (`CTRL + TAB`) o hacia atrás (`CTRL + SHIFT + TAB`) a través de las 6 pestañas de la interfaz, facilitando el cambio rápido y fluido.
  - **Atajo General CTRL + B:** Colapsa o expande el panel lateral de estadísticas/datos en la pestaña activa actual, evitando tener que memorizar números específicos.
  - **Atajo General CTRL + SHIFT + B:** Colapsa o expande el panel lateral derecho global de configuración (`right_panel`) desde cualquier pestaña.
  - Se mantiene el soporte auxiliar de `CTRL + SHIFT + Número` (1 a 6) para conmutar la visibilidad de los paneles a pantalla completa vía PubSub de forma dirigida.

---

## 8. Fases Pendientes

### Fase 4 — Partir `core/dsp_engine.py` (1670 líneas)
Propuesta:
```
core/engine/
├── base.py       ← Clase DSPEngine, estado, config
├── io_file.py    ← _worker_read_file()
├── io_sdr.py     ← _worker_read_sdr()
├── processing.py ← FFT, VBW, moving average
└── snapshots.py  ← Sistema de review de frames
```
> Riesgo: alto. Requiere mantener compatibilidad del Singleton `engine_instance`.

### Limpieza opcional
- `core/bbdevice/bb_api.py`: ~80% de funciones son código latente (no usado actualmente).
  Candidatos a limpiar: `bb_self_cal`, `bb_get_serial_number_list`, `bb_configure_IO`, `bb_sync_CPU_to_GPS`.
