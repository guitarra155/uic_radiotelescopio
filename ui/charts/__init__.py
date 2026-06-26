"""
ui/charts/__init__.py
Punto de entrada del paquete ui/charts.

Re-exporta TODAS las funciones chart_* públicas para que el código
que hace `from ui.charts import chart_spectrum` siga funcionando
sin ningún cambio.

El wrapper `make_synchronized` aplica el lock de Matplotlib
a todas las funciones chart_* en un solo lugar.

Para agregar un nuevo chart:
  1. Implementar la función en el submódulo correspondiente (o en algorithms.py)
  2. Importarla aquí
  → No se necesita tocar ningún otro archivo.
"""

import threading
import types

# ── Importar todos los submódulos ─────────────────────────────────────────────
from ui.charts.base import (
    export_active_chart,
    get_dynamic_figsize,
    get_cached_fig,
    fig_to_b64,
    safe_set_ylim,
    safe_set_xlim,
    style_ax,
)

from ui.charts.monitoring import (
    chart_amplitude,
    chart_amplitude_ma,
    chart_spectrum,
    chart_spectrum_raw,
)

from ui.charts.spectrogram import (
    chart_spectrogram,
    chart_cwt_map,
    chart_ar_spectrogram,
    chart_correlogram_spectrogram,
)

from ui.charts.statistics import (
    chart_histogram,
    chart_signal_time,
)

from ui.charts.signal_analysis import (
    chart_power_time,
)

from ui.charts.freq_snr import (
    chart_freq_snr,
)

from ui.charts.algorithms import (
    chart_ar_spectrum,
    chart_music_spectrum,
    chart_welch_spectrum,
    chart_correlogram_spectrum,
)

# Re-exportar el objeto caché para compatibilidad con código que lo importe directamente
from ui.charts.cache import cache

# ── Thread-safety: Matplotlib no es thread-safe ───────────────────────────────
mpl_lock = threading.Lock()


def make_synchronized(func):
    def wrapper(*args, **kwargs):
        with mpl_lock:
            return func(*args, **kwargs)
    wrapper.__name__ = func.__name__
    wrapper.__doc__ = func.__doc__
    return wrapper


# Decorar TODAS las funciones chart_* del namespace de este __init__
import sys
_this_module = sys.modules[__name__]
for _name, _value in list(vars(_this_module).items()):
    if isinstance(_value, types.FunctionType) and _name.startswith("chart_"):
        setattr(_this_module, _name, make_synchronized(_value))

# ── API pública ───────────────────────────────────────────────────────────────
__all__ = [
    # Base
    "export_active_chart", "get_dynamic_figsize", "get_cached_fig",
    "fig_to_b64", "safe_set_ylim", "safe_set_xlim", "style_ax", "cache",
    # Monitoring (Tab 1)
    "chart_amplitude", "chart_amplitude_ma",
    "chart_spectrum", "chart_spectrum_raw",
    # Spectrogram (Tab 2)
    "chart_spectrogram", "chart_cwt_map",
    "chart_ar_spectrogram", "chart_correlogram_spectrogram",
    # Statistics (Tab 3)
    "chart_histogram", "chart_signal_time",
    # Signal Analysis (Tab 4)
    "chart_power_time",
    # Freq SNR (Tab 5)
    "chart_freq_snr",
    # Algorithms (Tab 6)
    "chart_ar_spectrum", "chart_music_spectrum",
    "chart_welch_spectrum", "chart_correlogram_spectrum",
]
