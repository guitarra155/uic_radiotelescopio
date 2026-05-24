# Convenciones del Proyecto: UIC Radiotelescopio

## Estructura de Código y Nomenclatura

### Estándares de Naming
- **Clases**: `PascalCase` (e.g., `DSPEngine`, `SpectralAnalyzer`).
- **Funciones/Métodos**: `snake_case` (e.g., `sync_all_charts`, `calculate_noise_floor`).
- **Constantes**: `UPPER_SNAKE_CASE` (e.g., `ACCENT_CYAN`, `DEFAULT_FFT_SIZE`).

### Organización de Imports
1. Librerías Estándar (`threading`, `json`, `os`, `time`).
2. Librerías de Terceros (`numpy` como `np`, `flet` como `ft`, `matplotlib`).
3. Módulos Locales (`core.constants`, `core.dsp_engine`).

## Arquitectura de Visualización (charts_config)

El sistema ha migrado de "flags" globales a un diccionario unificado `charts_config` que centraliza el estado de cada gráfica.

### Estructura del Config
Cada gráfica (Spectrum, Power, SNR, Waterfall) tiene su propia entrada en `engine_instance.charts_config` con:
- `xmin`, `xmax`: Límites del eje de frecuencias o tiempo.
- `ymin`, `ymax`: Límites de amplitud o potencia en dBFS.
- `auto_x`, `auto_y`: Booleanos que habilitan el motor de auto-escalado dinámico.

**Regla de Oro**: Siempre redondear los valores a 2 decimales antes de enviarlos a la UI para evitar errores de renderizado.

## Gestión de Hardware (Signal Hound BB60C)

- **Acceso Exclusivo**: Utilizar siempre `with self._hw_lock:` antes de cualquier llamada a la API `bb_api`.
- **Manejo de Estados**: 
    - Ignorar estados `> 0` (Warnings).
    - Capturar estados `< 0` (Errores) y aplicar fallback a configuración segura (20 MHz BW).
- **Decimación**: Utilizar potencias de 2 para el `sample_rate`. La API escalará la decimación automáticamente.

## Sistema de Persistencia

Toda la configuración se centraliza en `core/config.json`.
- **Escritura**: El motor llama a `save_config()` automáticamente al modificar parámetros clave.
- **Lectura**: `load_config()` se ejecuta una única vez en el arranque de `main.py`.

## Archivos y Directorios Protegidos

- `data/`: Reservado para capturas del Smart Trigger.
- `docs/`: Documentación técnica y manuales de usuario.
- `.venv/`: Entorno virtual de Python.
- `config.json`: NO editar manualmente mientras la aplicación está abierta.
