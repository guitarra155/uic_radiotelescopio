# Contexto del Proyecto

## Objetivo

Desarrollar una plataforma de procesamiento digital de señales (DSP) para radioastronomía, específicamente para la detección y análisis de la línea de emisión del **Hidrógeno Neutro (HI)** a 21cm.

## Parámetros Técnicos

- **Frecuencia central**: 1420.405 MHz (línea HI)
- **Sample Rate**: 2.4 MSps (RTL-SDR)
- **FFT Size**: 4096
- **Formato IQ**: uint8 (interleaved) / int8 / complex64

## Flujo de Señal

```
1. Adquisición: Archivo .iq o SDR en tiempo real
2. Filtrado: Moving Average para suavizado
3. FFT: Cálculo del espectro de potencia
4. Análisis: SNR, detección de señales, algoritmos avanzados
5. Visualización: Múltiples pestañas con gráficas en tiempo real
```

## Pestañas

1. **Monitoreo**: Señal original + espectro RAW
2. **Monitoreo Filtrado**: Señal filtrada + espectro filtrado
3. **Espectrograma**: Waterfall/cascada temporal
4. **Estadística**: Histogramas, análisis estadístico
5. **Potencia vs Tiempo**: Evolución temporal de potencia
6. **SNR vs Frecuencia**: Relación señal/ruido por frecuencia
7. **Algoritmos**: AR, MUSIC, ESPRIT, Welch, CWT

## Configuración

Todos los parámetros se guardan en `core/config.json`:
- Rangos de visualización (dB min/max)
- Parámetros de filtrado (Moving Average)
- Frecuencia central y sample rate
- FFT size y ventana de análisis
