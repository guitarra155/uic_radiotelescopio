# Ecuaciones y Referencias: Transformada Wavelet Continua (CWT)

Este documento detalla las ecuaciones matemáticas y las referencias bibliográficas utilizadas en el script `main_cwt.m`.

## 1. Implementación en MATLAB

El código utiliza la función `cwt` de MATLAB. Desde la versión R2016b, si no se especifica una wavelet madre, MATLAB utiliza por defecto la **Wavelet Morse Generalizada (Analítica)**.

## 2. Ecuación de la Transformada (CWT)

La operación fundamental es la convolución de la señal $x(t)$ con una wavelet escalada y trasladada $\psi(t)$.

$$
W*\psi(u,s) = \int^{\infty}_{-\infty} x(t) \frac{1}{\sqrt{s}} \psi^*\left(\frac{t-u}{s}\right) dt
$$

**Donde:**

- $x(t)$: Señal de entrada.
- $s$: Escala (inversamente proporcional a la frecuencia).
- $u$: Desplazamiento temporal.
- $\psi^*$: Conjugado complejo de la Wavelet Madre.
- $W_\psi(u,s)$: Coeficientes complejos resultantes (variable `cfs` en el código).

## 3. La Wavelet Específica: Wavelet Morse Generalizada

MATLAB implementa esta wavelet en el dominio de la frecuencia. La ecuación que define su forma es:

$$
\Psi*{P,\gamma}(\omega) = U(\omega) a*{P,\gamma} \omega^\beta e^{-\omega^\gamma}
$$

**Parámetros utilizados (Valores por defecto de MATLAB):**

- **$\gamma$ (Gamma) = 3**: Controla la simetría de la wavelet.
- **$P^2$ (Producto Tiempo-Ancho de Banda) = 60**: Controla la compacidad.
- **$\beta$ = 20**: Parámetro de decaimiento ($\beta = P^2 / \gamma$).
- **$U(\omega)$**: Escalón unitario (hace que la wavelet sea analítica, 0 para frecuencias negativas).

## 4. Ecuación de Post-Procesamiento (Magnitud)

Para visualizar los resultados (escalograma), el código convierte los coeficientes complejos a magnitud logarítmica (dB):

$$
Mag*{dB} = 20 \cdot \log*{10}(|W*\psi(u,s)|) + \text{Offset}*{calibracion}
$$

## 5. Referencias Bibliográficas

Estas ecuaciones se basan en el trabajo de **J. M. Lilly** y **S. C. Olhede**.

1. **Referencia Principal (Definición Morse):**

   > J. M. Lilly and S. C. Olhede, "Generalized Morse Wavelets as a Superfamily of Analytic Wavelets," in _IEEE Transactions on Signal Processing_, vol. 60, no. 11, pp. 6036-6041, Nov. 2012.

2. **Referencia Secundaria (Propiedades):**

   > J. M. Lilly and S. C. Olhede, "Higher-Order Properties of Analytic Wavelets," in _IEEE Transactions on Signal Processing_, vol. 57, no. 1, pp. 146-160, Jan. 2009.

3. **Contexto General:**

   > Stéphane Mallat, "A Wavelet Tour of Signal Processing".
