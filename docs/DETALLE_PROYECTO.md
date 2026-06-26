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
│   └── DETALLE_PROYECTO.md
├── research/
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

### Optimizaciones incluidas
- `_render_2d_waterfall()` en `spectrogram.py` unifica la lógica de los tres espectrogramas 2D (evita ~200 líneas duplicadas)
- Thread-safety centralizado en `__init__.py` (antes en el final de `charts.py`)

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
