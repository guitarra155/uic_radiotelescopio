# Convenciones del Proyecto

## Estructura de Código

### Nomenclatura

- **Clases**: `PascalCase` (e.g., `DSPEngine`, `ChartCache`)
- **Funciones**: `snake_case` (e.g., `chart_spectrum`, `update_bounds`)
- **Constantes**: `UPPER_SNAKE_CASE` (e.g., `ACCENT_CYAN`, `DEFAULT_FFT_SIZE`)
- **Variables**: `snake_case` (e.g., `spectrum_data`, `power_time_data`)

### Imports

```python
# Standard library
import threading
import time

# Third party
import numpy as np
import flet as ft

# Local
from core.constants import *
from core.dsp_engine import engine_instance
```

## UI Components

### Colores del Tema

| Variable | Valor | Uso |
|----------|-------|-----|
| `DARK_BG` | `#0D1117` | Fondo principal |
| `PANEL_BG` | `#161B22` | Paneles |
| `ACCENT_CYAN` | `#00D2FF` | Acentos principales |
| `ACCENT_GREEN` | `#3FD18D` | Señal filtrada |
| `ACCENT_RED` | `#FF4C4C` | Errores/umbrales |
| `TEXT_MAIN` | `#E6EDF3` | Texto principal |

## DSP Engine

### Buffers

- `spectrum_data`: FFT filtrada (4096 puntos)
- `spectrum_raw_data`: FFT sin filtrar (4096 puntos)
- `waterfall_data`: Cascada temporal (29 x 4096)
- `power_time_data`: Potencia vs tiempo (2000 puntos)
- `snr_data`: SNR por bin (4096 puntos)

### Auto-escala

El motor tiene auto-detección de rangos que se puede desactivar por pestaña:
- `auto_scale_spectrum`: Pestañas 1, 2, 3
- `auto_scale_power`: Pestaña 5
- `auto_scale_snr`: Pestaña 6

## Archivos

### No modificar

- `.agents/skills/` - Skills de IA
- `.git/` - Git repository

### Generados automáticamente

- `core/test_signal.iq` - Señal de prueba
- `core/config.json` - Configuración guardada
