# 📡 UIC Radiotelescopio

Implementación de una plataforma en Python para el procesamiento digital de señales (DSP) de radiotelescopios, enfocada en la detección y análisis de la **línea de emisión del Hidrógeno Neutro (HI) a 21 cm / 1420.405 MHz**.

## Arquitectura

```
SDR / Archivo .iq  →  DSPEngine (Singleton)  →  Buffers Circulares  →  charts.py  →  UI (Flet)
                                             ↘  advanced_dsp.py (AR / MUSIC / ESPRIT / CWT / Welch / Correlograma)
```

## Características

- **Adquisición dual**: archivos `.iq` pregrabados o hardware SDR en tiempo real (Signal Hound BB60C).
- **Motor DSP multihilo**: filtrado Moving Average, FFT, detección de SNR y RFI, auto-escalado de rangos.
- **7 pestañas de visualización** en tiempo real con Matplotlib + caché de artists (~30 FPS):
  1. 📡 Monitoreo y RFI (señal original)
  2. 🔍 Monitoreo Filtrado (post Moving Average)
  3. 🌈 Espectrograma (Waterfall / Cascada)
  4. 📊 Estadística y Smart Trigger
  5. ⚡ Potencia vs. Tiempo
  6. 📶 SNR vs. Frecuencia
  7. 🔬 Algoritmo DSP Avanzado
- **6 algoritmos de estimación espectral avanzada**: AR/Burg, CWT/Morlet, Pseudo-MUSIC, ESPRIT, Welch PSD, Correlograma.
- **Panel de configuración** con controles granulares por gráfica, modo espejo, y persistencia en JSON.

## Estructura del Proyecto

| Directorio        | Propósito                                                                 |
|-------------------|---------------------------------------------------------------------------|
| `core/`           | Motor DSP (`dsp_engine.py`), algoritmos avanzados (`advanced_dsp.py`), constantes |
| `core/bbdevice/`  | API y DLLs para el hardware Signal Hound BB60C                           |
| `ui/`             | Visualización con Flet + Matplotlib                                      |
| `ui/tabs/`        | 7 pestañas: monitoreo, espectrograma, estadística, señal, SNR, algoritmo |
| `ui/components/`  | Layout reutilizable (header, footer), widgets compartidos                |
| `scripts/`        | Generador de señales IQ sintéticas, test de hardware                     |
| `data/`           | Archivos `.iq` de prueba (excluidos de Git)                              |
| `docs/`           | Documentación del proyecto (excluidos de Git)                            |

## Requisitos

- Python 3.12+
- Windows (requerido para la DLL del Signal Hound BB60C)

## Instalación

```bash
# Clonar el repositorio
git clone https://github.com/tu-usuario/uic_radiotelescopio.git
cd uic_radiotelescopio

# Crear entorno virtual (recomendado)
python -m venv venv
venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt
```

## Uso

```bash
# Ejecutar la plataforma
python main.py
```

Al iniciar, la aplicación abrirá una ventana con el panel de pestañas a la izquierda y el panel de configuración a la derecha. Para comenzar:

1. En el panel derecho, seleccione la fuente de datos (archivo `.iq` o SDR físico).
2. Configure la frecuencia central (por defecto 1420.40 MHz).
3. Presione **▶ Iniciar Adquisición** en el header.

## Parámetros Técnicos

| Parámetro         | Valor por defecto        |
|-------------------|--------------------------|
| Frecuencia central| 1420.405 MHz (línea HI)  |
| Sample Rate       | 2.4 MSps                 |
| FFT Size          | 4096                     |
| Formato IQ        | uint8 (interleaved)      |

## Stack Tecnológico

- **Backend**: Python, NumPy (vectorizado), SciPy
- **UI**: Flet 0.84+ (Flutter para Python)
- **Visualización**: Matplotlib con caché de artists
- **Comunicación interna**: PubSub asíncrono (latido cada 10 ms)
- **Hardware**: Signal Hound BB60C via `bb_api.dll`

## Licencia

Proyecto académico — Universidad UIC.
