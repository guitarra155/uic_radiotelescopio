"""
advanced_dsp.py
Módulo de algoritmos DSP avanzados para estimación espectral de alta resolución.

Algoritmos implementados:
  - AR / Burg      : Modelo autorregresivo por el método de Burg
  - CWT / Morlet   : Transformada Wavelet Continua (análisis tiempo-frecuencia)
  - Pseudo-MUSIC   : Estimación de frecuencias con sub-espacio de ruido
  - ESPRIT         : Estimación por rotación invariante de sub-espacio (bonus)
  - Welch          : Estimación espectral directa por promediado de periodogramas
  - Correlograma   : Estimación espectral indirecta vía FFT de autocorrelación
  - ASLT           : (stub) pendiente de archivos externos; async-ready

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


# ─────────────────────────────────────────────────────────────────────────────
# 5. Welch — Estimación espectral directa (periodograma promediado)
# ─────────────────────────────────────────────────────────────────────────────

def run_welch(iq: np.ndarray, fft_size: int = 1024, overlap: float = 0.5,
             sample_rate: float = 2_400_000,
             center_freq: float = 1420.40) -> dict:
    """
    Estima el PSD por método de Welch (periodograma promediado con solapamiento).

    Args:
        iq          : Muestras IQ (señal compleja o real).
        fft_size    : Tamaño de cada segmento (potencia de 2 recomendada).
        overlap     : Fracción de solapamiento entre segmentos [0, 0.9].
        sample_rate : Tasa de muestreo en Hz.
        center_freq : Frecuencia central en MHz.

    Returns:
        dict con 'freqs' (MHz), 'psd' (dB), 'peaks', 'noise_floor', 'method'.
        Schema idéntico a run_ar_burg para compatibilidad con chart_ar_spectrum().
    """
    sig = _to_complex(iq)
    N = len(sig)
    step = max(1, int(fft_size * (1.0 - overlap)))
    window = np.hanning(fft_size)
    win_power = np.sum(window ** 2)  # Normalización de potencia de ventana

    psd_accum = np.zeros(fft_size)
    n_segments = 0

    start = 0
    while start + fft_size <= N:
        seg = sig[start:start + fft_size] - np.mean(sig[start:start + fft_size])  # DC removal
        fft_block = np.fft.fftshift(np.fft.fft(seg * window))
        psd_accum += np.abs(fft_block) ** 2
        n_segments += 1
        start += step

    if n_segments == 0:
        # Señal demasiado corta: usar toda como un solo segmento con padding
        seg = np.zeros(fft_size, dtype=np.complex128)
        seg[:min(N, fft_size)] = sig[:min(N, fft_size)]
        fft_block = np.fft.fftshift(np.fft.fft(seg * window))
        psd_accum = np.abs(fft_block) ** 2
        n_segments = 1

    psd = psd_accum / (n_segments * win_power + 1e-30)
    psd_db = 10 * np.log10(psd + 1e-30)

    fs_mhz = sample_rate / 1_000_000
    freqs_mhz = np.linspace(center_freq - fs_mhz / 2,
                             center_freq + fs_mhz / 2, fft_size)

    thresh = np.median(psd_db) + 10.0
    from scipy.signal import find_peaks
    peak_idx, _ = find_peaks(psd_db, height=thresh, distance=fft_size // 100)
    peaks = [(float(freqs_mhz[i]), float(psd_db[i])) for i in peak_idx]

    return {
        "freqs": freqs_mhz,
        "psd": psd_db,
        "peaks": peaks,
        "noise_floor": float(np.median(psd_db)),
        "n_segments": n_segments,
        "method": "Welch"
    }


# ─────────────────────────────────────────────────────────────────────────────
# 6. Correlograma — Estimación espectral indirecta (Wiener-Khinchin)
# ─────────────────────────────────────────────────────────────────────────────

def run_correlogram(iq: np.ndarray, max_lag: int = 512, fft_size: int = 2048,
                   sample_rate: float = 2_400_000,
                   center_freq: float = 1420.40) -> dict:
    """
    Estima el PSD mediante el Correlograma (método indirecto):
    PSD = FFT(autocorrelación truncada con ventana de Bartlett).
    Implementa el teorema de Wiener-Khinchin.

    Args:
        iq          : Muestras IQ.
        max_lag     : Máximo retardo para truncar la autocorrelación.
        fft_size    : Puntos de la FFT final (> 2*max_lag recomendado para zero-pad).
        sample_rate : Tasa de muestreo en Hz.
        center_freq : Frecuencia central en MHz.

    Returns:
        dict con 'freqs' (MHz), 'psd' (dB), 'peaks', 'noise_floor', 'method'.
    """
    sig = _normalize(_to_complex(iq))
    N = len(sig)
    max_lag = min(max_lag, N // 2)

    # Autocorrelación directa para lags 0..max_lag
    acf = np.zeros(2 * max_lag + 1, dtype=np.complex128)
    for k in range(max_lag + 1):
        acf[max_lag + k] = np.dot(sig[:N - k], sig[k:].conj()) / N
        acf[max_lag - k] = acf[max_lag + k].conj()

    # Ventana de Bartlett para suavizado espectral
    bartlett = np.bartlett(2 * max_lag + 1)
    acf_windowed = acf * bartlett

    # FFT con zero-padding + fftshift para centrar en DC
    fft_size_eff = max(fft_size, 2 * (2 * max_lag + 1))
    psd_raw = np.abs(np.fft.fftshift(np.fft.fft(acf_windowed, n=fft_size_eff)))
    psd_db = 10 * np.log10(psd_raw + 1e-30)

    # Recortar/interpolar al tamaño solicitado
    if len(psd_db) != fft_size:
        idx = np.round(np.linspace(0, len(psd_db) - 1, fft_size)).astype(int)
        psd_db = psd_db[idx]

    fs_mhz = sample_rate / 1_000_000
    freqs_mhz = np.linspace(center_freq - fs_mhz / 2,
                             center_freq + fs_mhz / 2, fft_size)

    thresh = np.median(psd_db) + 8.0
    from scipy.signal import find_peaks
    peak_idx, _ = find_peaks(psd_db, height=thresh, distance=fft_size // 100)
    peaks = [(float(freqs_mhz[i]), float(psd_db[i])) for i in peak_idx]

    return {
        "freqs": freqs_mhz,
        "psd": psd_db,
        "peaks": peaks,
        "noise_floor": float(np.median(psd_db)),
        "max_lag": max_lag,
        "method": "Correlograma"
    }


# ─────────────────────────────────────────────────────────────────────────────
# 7. ASLT — Stub async-ready (pendiente de archivos externos)
# ─────────────────────────────────────────────────────────────────────────────

def run_aslt(iq: np.ndarray, sample_rate: float = 2_400_000,
            center_freq: float = 1420.40, **kwargs) -> dict:
    """
    ASLT: Advanced Sparse Local Transform (placeholder).
    Diseñado para ejecutarse con asyncio.to_thread desde sdr_config.py.

    IMPORTANTE: Esta función es un stub. Los archivos de implementación
    aún no están disponibles. Al integrarlos, reemplaza el cuerpo de
    esta función manteniendo la firma y el schema de retorno.

    Returns:
        dict vacío compatible con chart_ar_spectrum() marcado como 'ASLT'.

    Raises:
        NotImplementedError: siempre, hasta que se integren los archivos externos.
    """
    raise NotImplementedError(
        "ASLT: archivos externos pendientes de integración. "
        "Reemplaza el cuerpo de run_aslt() cuando estén disponibles."
    )
