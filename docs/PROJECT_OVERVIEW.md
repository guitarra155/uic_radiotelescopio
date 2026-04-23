# UIC Radiotelescopio

Plataforma DSP para radioastronomía enfocada en la línea de **Hidrógeno Neutro (HI) a 21cm / 1420.405 MHz**.

## Arquitectura

```
SDR/Archivo .iq → DSPEngine (Singleton) → Buffers Circulares → charts.py → UI (Flet)
                                      ↘ advanced_dsp.py (AR/MUSIC/ESPRIT/CWT)
```

## Estructura

| Directorio | Propósito |
|------------|-----------|
| `core/` | Motor DSP (`dsp_engine.py`), algoritmos avanzados (`advanced_dsp.py`), constantes |
| `ui/` | Visualización con Flet + Matplotlib |
| `ui/tabs/` | 5+ pestañas: monitoring, spectrogram, statistics, sdr_config, algo_tab |
| `ui/components/` | Layout reutilizable, widgets compartidos |
| `scripts/` | Generador de IQ sintético |

## Tech Stack

- **Backend**: Python, NumPy (vectorizado), SciPy
- **UI**: Flet (Flutter)
- **Visualización**: Matplotlib con cache de artists para ~30 FPS
- **Comunicación**: PubSub (latido cada 10ms)
