---
type: concept
tags: [uic, radiotelescopio, dsp, mathematics]
created: 2026-04-21
sources: [core/advanced_dsp.py, core/dsp_engine.py]
---

# Implementación de Algoritmos DSP

La plataforma implementa una suite de algoritmos de alta resolución para la estimación de la Densidad Espectral de Potencia (PSD), permitiendo separar emisiones cósmicas de interferencias (RFI).

## Modelado Matemático y Algoritmos

### 1. Modelo Autorregresivo (Burg)
El método de **Burg** estima los parámetros de un modelo AR minimizando los errores de predicción hacia adelante ($e_f$) y hacia atrás ($e_b$).

**Fórmula del Coeficiente de Reflexión ($k_m$):**
$$k_m = \frac{-2 \sum_{n=m}^{N-1} e_{f,m-1}[n] e_{b,m-1}^*[n-1]}{\sum_{n=m}^{N-1} |e_{f,m-1}[n]|^2 + \sum_{n=m}^{N-1} |e_{b,m-1}[n-1]|^2}$$

En `advanced_dsp.py`, esto se implementa mediante la recursión de **Levinson-Durbin** para actualizar los coeficientes del filtro.

### 2. Pseudo-MUSIC
Utilizado para la estimación de frecuencias con super-resolución mediante la descomposición del sub-espacio de ruido ($\mathbf{E}_n$).

**Pseudo-espectro:**
$$P_{\text{MUSIC}}(f) = \frac{1}{\mathbf{a}^H(f) \mathbf{E}_n \mathbf{E}_n^H \mathbf{a}(f)}$$
Donde $\mathbf{a}(f)$ es el vector de dirección (steering vector).

### 3. Método de Welch (Periodograma Promediado)
Reduce la varianza de la estimación espectral dividiendo la señal en $K$ segmentos solapados.

**Estimador PSD:**
$$\hat{P}_{Welch}(f) = \frac{1}{K \cdot U} \sum_{i=1}^{K} |X_i(f)|^2, \quad U = \sum_{n=0}^{M-1} w^2[n]$$
Donde $w[n]$ es la ventana de Hanning y $U$ es el factor de normalización de potencia.

## Optimizaciones en `dsp_engine.py`

### Filtro de Media Móvil (MA) Ultra-rápido
Para mitigar RFI en tiempo real, implementamos la media móvil usando la **Suma Acumulada (Cumulative Sum)**, lo que reduce la complejidad de $O(N \cdot W)$ a $O(N)$:

$$y[n] = \frac{1}{W} \sum_{k=0}^{W-1} x[n-k] \implies y[n] = \frac{1}{W} (\text{cumsum}[n] - \text{cumsum}[n-W])$$

**Código Python:**
```python
def fast_ma(x, w):
    cs = np.cumsum(np.pad(x, (w//2, w//2), mode='edge'))
    return (cs[w:] - cs[:-w]) / w
```

## Caracterización Estadística de la Señal
El sistema ajusta los histogramas de magnitud a distribuciones de probabilidad para detectar anomalías:
- **Distribución de Rayleigh**: Modelado de ruido térmico puro.
- **Distribución Rician/Weibull**: Presencia de componentes deterministas (señales) sobre el ruido.
