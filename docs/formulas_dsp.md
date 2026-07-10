# Formulación Matemática del Procesamiento Digital de Señales

Este documento expone las ecuaciones matemáticas implementadas en la plataforma de procesamiento para la caracterización temporal y espectral de las señales en el radiotelescopio.

---

## 1. Caracterización Temporal de Potencia (Pestaña 5)

Para obtener la evolución temporal de la potencia promedio de la señal en dBFS, se realiza la conversión lineal de las amplitudes logarítmicas de cada bin espectral de la FFT, se calcula el promedio y finalmente se reconvierte a la escala logarítmica de decibelios fondo de escala (dBFS) en cada intervalo:

$$P_{\text{lineal}} = \frac{1}{N} \sum_{k=0}^{N-1} 10^{\frac{P_{\text{raw}}[k]}{10}}$$

$$P_{\text{promedio}} \text{ [dBFS]} = 10 \log_{10} \left( P_{\text{lineal}} \right)$$

Donde:
*   $P_{\text{raw}}[k]$ representa la potencia de la señal en dBFS para el bin de frecuencia discreto $k$.
*   $N$ es la cantidad total de bins que componen la Transformada Rápida de Fourier (FFT).
*   $P_{\text{promedio}}$ es el nivel de potencia media integrada calculada para la ventana de análisis temporal.

---

## 2. Análisis Espectral de Relación Señal-Ruido (Pestaña 6)

La relación señal-ruido ($SNR$) en cada canal de frecuencia discreta $k$ se evalúa en el dominio lineal como el cociente entre la potencia espectral cruda medida y la potencia estimada del piso de ruido circundante:

$$SNR_{\text{lineal}}[k] = \frac{P_{\text{raw, lineal}}[k]}{P_{\text{ruido, lineal}}[k]}$$

En el dominio logarítmico, la operación se reduce a una sustracción aritmética directa:

$$SNR[k] \text{ [dB]} = P_{\text{raw}}[k] \text{ [dBFS]} - P_{\text{ruido}}[k] \text{ [dBFS]}$$

Donde:
*   $P_{\text{raw}}[k]$ es la potencia espectral bruta del bin $k$ en dBFS.
*   $P_{\text{ruido}}[k]$ es el nivel estimado del piso de ruido para el bin $k$ mediante el algoritmo adaptativo de tasa de falsa alarma constante (CFAR).

---

## Referencias Bibliográficas

*   Oppenheim, A. V., & Schafer, R. W. (2010). *Discrete-Time Signal Processing* (3rd ed.). Prentice Hall. (Sección 10.2: Fourier Analysis of Signals Using the DFT, págs. 705-720). [https://www.pearson.com/en-us/subject-catalog/p/discrete-time-signal-processing/P200000003228](https://www.pearson.com/en-us/subject-catalog/p/discrete-time-signal-processing/P200000003228)
*   Richards, M. A. (2014). *Fundamentals of Radar Signal Processing* (2nd ed.). McGraw-Hill Education. (Sección 7.3: Constant False Alarm Rate (CFAR) Detection, págs. 345-360). [https://www.mheducation.com/cover-images/Jpeg_400_high/0071798323.jpeg](https://www.mheducation.com/cover-images/Jpeg_400_high/0071798323.jpeg)
