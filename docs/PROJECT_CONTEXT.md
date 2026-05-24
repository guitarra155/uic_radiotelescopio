# Contexto del Proyecto: UIC Radiotelescopio

## Objetivo General
Desarrollar una estación terrestre de radioastronomía para la detección y análisis de la línea de emisión del **Hidrógeno Neutro (HI)** a 21cm, integrando hardware de alto rendimiento (BB60C) con algoritmos DSP de vanguardia.

## Parámetros Técnicos de Operación
- **Frecuencia Central Astronómica**: 1420.405 MHz.
- **Tasa de Muestreo (Sample Rate)**: 1.0 MSps a 40.0 MSps (Ajustado dinámicamente a valores nativos del BB60C).
- **Resolución FFT**: 4096 puntos por defecto (Ajustable).
- **Formatos IQ Soportados**: `uint8` (RTL-SDR), `int16`, `complex64`.

## Capacidades de Inteligencia de Señal
- **Spectral Lock (Auto-Sintonía)**: Al cargar un archivo IQ, el sistema escanea el espectro en busca de firmas de hidrógeno y auto-sintoniza la frecuencia central si detecta un pico de interés.
- **Auto-Escala Dinámica**: Las gráficas analizan el buffer circular en tiempo real para ajustar los límites Y al rango dinámico exacto de la señal (Min/Max).
- **Smart Trigger**: Captura ráfagas de 3 segundos ante eventos que superen umbrales de potencia configurables (SNR > X dB).

## Organización de la Interfaz (Pestañas)
1. **Inicio & Configuración**: Control de archivos, hardware y sintonía en vivo.
2. **Monitoreo y RFI**: Señal RAW para identificar interferencias locales.
3. **Monitoreo Filtrado**: Señal limpia tras el filtro Moving Average.
4. **Espectrograma (Waterfall)**: Historial temporal de frecuencias.
5. **Estadística & Smart Trigger**: Histogramas de amplitud y configuración de alertas.
6. **Potencia vs Tiempo**: Evolución de la potencia total integrada.
7. **SNR vs Frecuencia**: Análisis de relación señal/ruido.

## Persistencia de Configuración
Todos los parámetros se guardan automáticamente en `core/config.json`:
- Rangos de visualización y estados de "Auto Escala".
- Parámetros de hardware (Ref Level, IQ BW, VBW Smoothing).
- Rutas de archivos y metadatos de la última sesión.
