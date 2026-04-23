---
type: concept
tags: [uic, radiotelescopio, workflow, conventions]
created: 2026-04-21
sources: [docs/CONVENTIONS.md]
---

# Convenciones y Estética del Proyecto

Este documento describe las normas de codificación y el sistema de diseño utilizado en la plataforma, asegurando la coherencia entre el backend de procesamiento y la interfaz de usuario.

## Sistema de Diseño (UI)
La interfaz utiliza una estética **Dark Mode / Glassmorphism** basada en el esquema de colores definido por el usuario.

| Variable | Valor Hex | Uso en la Interfaz |
| :--- | :--- | :--- |
| `DARK_BG` | `#0D1117` | Fondo profundo de la aplicación. |
| `PANEL_BG` | `#161B22` | Fondos de contenedores y controles laterales. |
| `ACCENT_CYAN` | `#00D2FF` | Acento para señal RAW y elementos activos. |
| `ACCENT_GREEN`| `#3FD18D` | Acento para señal filtrada y resultados DSP. |
| `BORDER_COL` | `#30363D` | Bordes sutiles para separación de paneles. |

## Normas de Nomenclatura (Notation)
El código sigue estándares estrictos para facilitar la legibilidad del "camino de la señal" (signal path):
- **Clases**: `PascalCase` (ej. `DSPEngine`, `SpectrumChart`).
- **Funciones de UI**: `build_<componente>` (ej. `build_header`, `build_monitoring`).
- **Buffers de Señal**: `<tipo>_data` (ej. `spectrum_data`, `snr_data`).

## Configuración y Persistencia
Los parámetros operativos se sincronizan en **`config.json`**, lo que permite:
1. Persistencia de rangos de visualización entre sesiones.
2. Configuración granular de auto-escala por cada tipo de gráfica.
3. Almacenamiento de parámetros de algoritmos (ej. `ar_order`, `n_signals`).
