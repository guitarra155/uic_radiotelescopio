"""
advanced_dsp.py
Módulo de algoritmos DSP avanzados para estimación espectral de alta resolución.

Algoritmos implementados:
  - AR / Burg      : Modelo autorregresivo por el método de Burg
  - CWT / Morlet   : Transformada Wavelet Continua (análisis tiempo-frecuencia)
  - Pseudo-MUSIC   : Estimación de frecuencias con sub-espacio de ruido
  - ESPRIT         : Estimación por rotación invariante de sub-espacio (bonus)

Cada función retorna un diccionario con los datos necesarios para chart.py.
"""

import numpy as np


# ─────────────────────────────────────────────────────────────────────────────
# Utilidades comunes
# ─────────────────────────────────────────────────────────────────────────────

def _to_complex(iq: np.ndarray) -> np.ndarray:
    """Garantiza que la señal sea compleja (si no lo es, la convierte)."""
    if np.iscomplexobj(iq):
        return iq.astype(np.complex128)
    return iq.astype(np.float64)


def _normalize(sig: np.ndarray) -> np.ndarray:
    """Centra en cero y normaliza potencia unitaria."""
    s = sig - np.mean(sig)
    p = np.sqrt(np.mean(np.abs(s) ** 2) + 1e-12)
    return s / p


# ─────────────────────────────────────────────────────────────────────────────
# 1. Modelo Autorregresivo — Método de Burg
# ─────────────────────────────────────────────────────────────────────────────

def run_ar_burg(iq: np.ndarray, order: int = 64, n_freqs: int = 2048,
                sample_rate: float = 2_400_000, center_freq: float = 1420.40) -> dict:
    """
    Estima el PSD mediante Modelo AR con el algoritmo de Burg.

    Args:
        iq          : Muestras IQ (array complejo o real).
        order       : Orden del modelo AR (más alto = más resolución, más costoso).
        n_freqs     : Puntos en el eje de frecuencia del pseudo-espectro.
        sample_rate : Tasa de muestreo en Hz.
        center_freq : Frecuencia central en MHz.

    Returns:
        dict con 'freqs' (MHz), 'psd' (dB), 'order', 'peaks'.
    """
    sig = _normalize(_to_complex(iq))
    N = len(sig)
    order = min(order, N // 2 - 1)

    # Algoritmo de Burg: estimación iterativa de coeficientes de reflexión
    ef = sig[1:].copy()       # error hacia adelante
    eb = sig[:-1].copy()      # error hacia atrás
    ar_coeffs = np.zeros(order, dtype=np.complex128)
    total_err = np.dot(sig, sig.conj()).real / N

    for m in range(order):
        # Coeficiente de reflexión (km) de Burg
        num = -2.0 * np.dot(ef, eb.conj())
        den = np.dot(ef, ef.conj()) + np.dot(eb, eb.conj())
        km = num / (den + 1e-30)

        # Actualizar coeficientes AR con la fórmula de Levinson-Durbin
        ar_new = ar_coeffs[:m+1].copy()
        ar_new[m] = km
        ar_new[:m] = ar_coeffs[:m] + km * ar_coeffs[:m][::-1].conj()
        ar_coeffs[:m+1] = ar_new

        # Actualizar errores
        ef_new = ef[1:] + km * eb[1:]
        eb_new = eb[:-1] + km.conj() * ef[:-1]
        ef, eb = ef_new, eb_new

        total_err *= (1.0 - abs(km) ** 2)

    # PSD a partir de los coeficientes AR
    freqs_norm = np.linspace(-0.5, 0.5, n_freqs)
    z = np.exp(2j * np.pi * freqs_norm)

    denom = np.ones(n_freqs, dtype=np.complex128)
    for k, a in enumerate(ar_coeffs):
        denom += a * z ** (-(k + 1))

    psd = total_err / (np.abs(denom) ** 2 + 1e-30)
    psd_db = 10 * np.log10(np.fft.fftshift(psd) + 1e-30)

    fs_mhz = sample_rate / 1_000_000
    freqs_mhz = np.linspace(center_freq - fs_mhz / 2,
                             center_freq + fs_mhz / 2, n_freqs)

    # Detección de picos por umbral (>10 dB sobre mediana)
    thresh = np.median(psd_db) + 10.0
    from scipy.signal import find_peaks
    peak_idx, _ = find_peaks(psd_db, height=thresh, distance=n_freqs // 100)
    peaks = [(float(freqs_mhz[i]), float(psd_db[i])) for i in peak_idx]

    return {
        "freqs": freqs_mhz,
        "psd": psd_db,
        "order": order,
        "peaks": peaks,
        "noise_floor": float(np.median(psd_db)),
        "method": "AR/Burg"
    }


# ─────────────────────────────────────────────────────────────────────────────
# 2. Transformada Wavelet Continua — Morlet
# ─────────────────────────────────────────────────────────────────────────────

def run_cwt(iq: np.ndarray, sample_rate: float = 2_400_000,
            n_scales: int = 64, max_freq_ratio: float = 0.45) -> dict:
    """
    Calcula la CWT con wavelet Morlet compleja.

    Args:
        iq             : Muestras IQ.
        sample_rate    : Tasa de muestreo en Hz.
        n_scales       : Número de escalas (resolución tiempo-frecuencia).
        max_freq_ratio : Fracción de Nyquist para la frecuencia más alta.

    Returns:
        dict con 'cwt_matrix' (n_scales × n_samples), 'freqs_norm', 'times_s', 'scales'.
    """
    sig = _normalize(_to_complex(iq))

    # Limitar longitud para velocidad (máx 8192 muestras)
    max_len = 8192
    if len(sig) > max_len:
        sig = sig[:max_len]

    N = len(sig)
    dt = 1.0 / sample_rate

    # Escalas logarítmicas
    f_min = sample_rate * 0.005
    f_max = sample_rate * max_freq_ratio
    freqs = np.geomspace(f_min, f_max, n_scales)   # Hz
    scales = sample_rate / freqs                     # escala ∝ 1/f

    # Wavelet Morlet compleja: ψ(t) = π^{-1/4} * e^{j2πf0t} * e^{-t²/2}
    f0 = 1.0  # frecuencia central normalizada de Morlet

    cwt_matrix = np.zeros((n_scales, N), dtype=np.complex128)
    for i, sc in enumerate(scales):
        t_wav = np.arange(-(6 * sc), 6 * sc + 1) * dt
        morlet = (np.pi ** -0.25) * np.exp(2j * np.pi * f0 * t_wav / sc) \
                 * np.exp(-0.5 * (t_wav / sc) ** 2)
        # Convolución mediante correlación cruzada
        from scipy.signal import fftconvolve
        conv = fftconvolve(sig, morlet[::-1].conj(), mode="same")
        # Asegurarnos de que el array tenga exactamente N de tamaño (por seguridad de broadcast)
        if len(conv) > N:
            start = (len(conv) - N) // 2
            conv = conv[start:start+N]
        elif len(conv) < N:
            # Padding con ceros si fuera menor (raro en mode="same")
            conv = np.pad(conv, (0, N - len(conv)))
            
        cwt_matrix[i, :] = conv / np.sqrt(abs(sc))

    times_s = np.arange(N) * dt
    freqs_mhz_norm = freqs / 1_000_000

    return {
        "cwt_matrix": np.abs(cwt_matrix) ** 2,   # potencia
        "freqs_hz": freqs,
        "freqs_mhz_norm": freqs_mhz_norm,
        "times_s": times_s,
        "scales": scales,
        "method": "CWT/Morlet"
    }


# ─────────────────────────────────────────────────────────────────────────────
# 3. Pseudo-MUSIC (MUltiple SIgnal Classification)
# ─────────────────────────────────────────────────────────────────────────────

def run_pseudo_music(iq: np.ndarray, n_signals: int = 3,
                     n_freqs: int = 2048, subarray_len: int = 128,
                     sample_rate: float = 2_400_000,
                     center_freq: float = 1420.40) -> dict:
    """
    Pseudo-espectro MUSIC para estimación de frecuencias de alta resolución.

    Args:
        iq           : Muestras IQ.
        n_signals    : Número estimado de señales presentes.
        n_freqs      : Puntos del pseudo-espectro.
        subarray_len : Longitud del sub-array (M).
        sample_rate  : Tasa de muestreo en Hz.
        center_freq  : Frecuencia central en MHz.

    Returns:
        dict con 'freqs' (MHz), 'music_spectrum' (dB), 'peaks'.
    """
    sig = _normalize(_to_complex(iq))
    N = len(sig)
    M = min(subarray_len, N // 4)

    # Construir matriz de correlación de Toeplitz con método de correlación directa
    L = N - M + 1
    X = np.array([sig[i:i + M] for i in range(L)])   # L × M
    R = (X.conj().T @ X) / L                          # M × M covarianza

    # Descomposición en valores propios
    eigenvalues, eigenvectors = np.linalg.eigh(R)
    # eigh retorna en orden ascendente; invertir para orden descendente
    idx = np.argsort(eigenvalues)[::-1]
    eigenvalues = eigenvalues[idx]
    eigenvectors = eigenvectors[:, idx]

    n_signals = min(n_signals, M - 1)
    En = eigenvectors[:, n_signals:]                  # Sub-espacio de ruido

    # Barrido de frecuencias
    freqs_norm = np.linspace(-0.5, 0.5, n_freqs)
    music_spectrum = np.zeros(n_freqs)

    for k, fn in enumerate(freqs_norm):
        a = np.exp(-2j * np.pi * fn * np.arange(M))  # Vector de dirección
        proj = a.conj() @ En @ En.conj().T @ a
        music_spectrum[k] = 1.0 / (abs(proj) + 1e-30)

    music_db = 10 * np.log10(music_spectrum + 1e-30)
    # Normalizar respecto al máximo
    music_db -= np.max(music_db)

    fs_mhz = sample_rate / 1_000_000
    freqs_mhz = np.linspace(center_freq - fs_mhz / 2,
                             center_freq + fs_mhz / 2, n_freqs)

    # Detección de picos
    from scipy.signal import find_peaks
    thresh_db = np.max(music_db) - 20.0
    peak_idx, _ = find_peaks(music_db, height=thresh_db, distance=n_freqs // 80)
    peaks = [(float(freqs_mhz[i]), float(music_db[i])) for i in peak_idx[:10]]

    return {
        "freqs": freqs_mhz,
        "music_spectrum": music_db,
        "peaks": peaks,
        "eigenvalues": eigenvalues.real.tolist(),
        "n_signals": n_signals,
        "method": "Pseudo-MUSIC"
    }


# ─────────────────────────────────────────────────────────────────────────────
# 4. ESPRIT — Estimation of Signal Parameters via Rotational Invariance
# ─────────────────────────────────────────────────────────────────────────────

def run_esprit(iq: np.ndarray, n_signals: int = 3,
               subarray_len: int = 128, sample_rate: float = 2_400_000,
               center_freq: float = 1420.40,
               n_freqs: int = 2048) -> dict:
    """
    ESPRIT: estima frecuencias directamente desde el sub-espacio de señal,
    sin barrer frecuencias. Más eficiente que MUSIC para señales estrechas.

    Returns:
        dict con 'freqs' (MHz) estimadas, 'esprit_spectrum' (pseudo-espectro
        gaussiano centrado en cada pico), 'peaks'.
    """
    sig = _normalize(_to_complex(iq))
    N = len(sig)
    M = min(subarray_len, N // 4)
    n_signals = min(n_signals, M // 2)

    L = N - M + 1
    X = np.array([sig[i:i + M] for i in range(L)])
    R = (X.conj().T @ X) / L

    eigenvalues, eigenvectors = np.linalg.eigh(R)
    idx = np.argsort(eigenvalues)[::-1]
    eigenvectors = eigenvectors[:, idx]

    Es = eigenvectors[:, :n_signals]    # Sub-espacio de señal

    # Sub-arrays desplazados (explotamos la estructura rotacional)
    Es1 = Es[:-1, :]
    Es2 = Es[1:, :]

    # Phi = pseudo-inversa(Es1) @ Es2  →  valores propios = e^{j2πf}
    Phi = np.linalg.pinv(Es1) @ Es2
    freq_eigs = np.linalg.eigvals(Phi)

    # Extraer frecuencias normalizadas del ángulo
    freqs_norm = np.angle(freq_eigs) / (2 * np.pi)  # en [−0.5, 0.5]
    freqs_norm = np.sort(freqs_norm)

    fs_mhz = sample_rate / 1_000_000
    freqs_est_mhz = center_freq + freqs_norm * fs_mhz

    # Construir pseudo-espectro gaussiano centrado en cada frecuencia estimada
    freqs_axis = np.linspace(center_freq - fs_mhz / 2,
                              center_freq + fs_mhz / 2, n_freqs)
    sigma_mhz = fs_mhz / n_freqs * 8   # anchura de la campana

    esprit_spectrum = np.zeros(n_freqs)
    for fe in freqs_est_mhz:
        esprit_spectrum += np.exp(-0.5 * ((freqs_axis - fe) / sigma_mhz) ** 2)

    esprit_db = 10 * np.log10(esprit_spectrum + 1e-30)
    esprit_db -= np.max(esprit_db)

    peaks = [(float(f), 0.0) for f in freqs_est_mhz]

    return {
        "freqs": freqs_axis,
        "esprit_spectrum": esprit_db,
        "freqs_estimated": freqs_est_mhz.tolist(),
        "peaks": peaks,
        "n_signals": n_signals,
        "method": "ESPRIT"
    }
