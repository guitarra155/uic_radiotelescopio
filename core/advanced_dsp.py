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
    fs_mhz = sample_rate / 1_000_000
    f_vec = np.arange(-n_freqs // 2, n_freqs // 2) * (sample_rate / n_freqs)
    freqs_norm = f_vec / sample_rate
    z = np.exp(2j * np.pi * freqs_norm)

    denom = np.ones(n_freqs, dtype=np.complex128)
    for k, a in enumerate(ar_coeffs):
        denom += a * z ** (-(k + 1))

    psd = total_err / (np.abs(denom) ** 2 + 1e-30)
    psd_db = 10 * np.log10(psd + 1e-30)

    freqs_mhz = (center_freq * 1e6 + f_vec) / 1e6

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
    [Legacy] CWT básica sobre señal corta. Usar run_cwt_2d para el espectrograma completo.
    """
    return run_cwt_2d(iq, sample_rate=sample_rate, n_scales=n_scales,
                      center_freq=1420.40, block_size=min(5000, len(iq)))


def run_cwt_2d(iq: np.ndarray, sample_rate: float = 2_400_000,
               n_scales: int = 48, center_freq: float = 1420.40,
               block_size: int = 5000, block_overlap: float = 0.5,
               f_min_visual: float = None, f_max_visual: float = None,
               offset_calibracion: float = 0.0) -> dict:
    """
    CWT 2D por bloques con Wavelet de Morlet Bilateral Simétrica.
    Garantiza una alineación perfecta (1:1) de los ejes de frecuencia
    compleja con el Waterfall FFT y el Correlograma.
    Procesa tanto frecuencias analíticas (positivas) como anti-analíticas (negativas).
    """
    from core.dsp_engine import engine_instance as _eng
    N = len(iq)
    dt = 1.0 / sample_rate
    fc_hz = center_freq * 1e6

    # ── Eje de frecuencias lineal y bilateral (-fs/2 a fs/2) ──────────────────
    f_lo = -sample_rate * 0.49
    f_hi = sample_rate * 0.49
    freqs_hz  = np.linspace(f_lo, f_hi, n_scales).astype(np.float32)
    freqs_mhz = (fc_hz + freqs_hz) / 1e6   # MHz centradas

    # ── global_step: igual que correlograma → máximo ~150 bloques ─────────────
    num_segs_target    = 150
    total_samples_hist = _eng.waterfall_history_sec * sample_rate
    global_step        = max(block_size, int(total_samples_hist / num_segs_target))

    # Posiciones de inicio de cada bloque
    block_starts = np.arange(0, N - block_size + 1, global_step)
    n_blocks     = len(block_starts)

    if n_blocks == 0:
        empty = np.zeros((1, n_scales), dtype=np.float32) + offset_calibracion
        return {
            "matrix": empty, "times_s": np.array([0.0]),
            "freqs_mhz": freqs_mhz,
            "v_min": offset_calibracion - 5, "v_max": offset_calibracion + 20,
            "noise_floor": float(offset_calibracion),
            "cwt_matrix": empty.T, "freqs_hz": freqs_hz,
            "freqs_mhz_norm": freqs_mhz, "scales": np.ones(n_scales, dtype=np.float32),
            "method": "CWT/Morlet 2D",
        }

    # ── Banco de filtros Morlet en dominio de frecuencia (Bilateral) ──────────
    n_fft_wav = 2 ** int(np.round(np.log2(block_size)))
    omega  = 2 * np.pi * np.fft.fftfreq(n_fft_wav, d=dt).astype(np.float32)  # (n_fft,)
    omega0 = 2 * np.pi * 6.0   # parámetro estándar de Morlet (ω₀ = 6)
    
    # Evitar división por cero
    freqs_hz_safe = np.where(freqs_hz == 0.0, 1e-5, freqs_hz)
    scales = (omega0 / (2 * np.pi * np.abs(freqs_hz_safe))).astype(np.float32) # (n_scales,)

    sc_col   = scales[:, None]                  # (n_scales, 1)
    sign_col = np.sign(freqs_hz_safe)[:, None]  # (n_scales, 1)

    # arg = s*omega - sign(f)*omega0
    arg = sc_col * omega[None, :] - sign_col * omega0 # (n_scales, n_fft)
    
    # support: H(omega) para positivas, H(-omega) para negativas
    support = (sign_col * omega[None, :] > 0).astype(np.float32)

    norms   = (np.pi ** -0.25) * np.sqrt(2 * np.pi * sc_col / dt)
    psi_hat = (norms * np.exp(-0.5 * arg * arg) * support).astype(np.complex64)
    # psi_hat: (n_scales, n_fft_wav)

    # ── Procesamiento por bloques vectorial ultrarrápido (Teorema de Parseval) ──
    # Precalcular potencia de la respuesta al impulso en frecuencia (Parseval)
    psi_hat_power = (np.abs(psi_hat) ** 2).astype(np.float32)  # (n_scales, n_fft_wav)

    # Construir matriz de segmentos (n_blocks × block_size) en un solo indexado
    idx_matrix = block_starts[:, None] + np.arange(block_size)   # (n_blocks, block_size)
    seg_matrix = iq[idx_matrix].astype(np.complex64)             # (n_blocks, block_size)

    # Eliminar DC por fila
    seg_matrix = seg_matrix - seg_matrix.mean(axis=1, keepdims=True)

    # FFT de todos los bloques en un solo paso
    BLK = np.fft.fft(seg_matrix, n=n_fft_wav, axis=1).astype(np.complex64)
    BLK_power = np.abs(BLK) ** 2  # (n_blocks, n_fft_wav)

    # Parseval en lote: multiplicación de matrices ultrarrápida
    spec_matrix = (BLK_power @ psi_hat_power.T) / (n_fft_wav ** 2)
    spec_matrix = spec_matrix.astype(np.float32)

    times_s = (block_starts + block_size / 2) * dt

    # ── Convertir a dB ────────────────────────────────────────────────────────
    spec_db = 10.0 * np.log10(spec_matrix + np.finfo(float).eps) + offset_calibracion

    noise_floor = float(np.median(spec_db))
    v_min = noise_floor - 3.0
    v_max = float(np.max(spec_db)) + 2.0
    if v_max < v_min + 10.0:
        v_max = v_min + 20.0

    # ── Máscara visual ────────────────────────────────────────────────────────
    if f_min_visual is not None and f_max_visual is not None:
        mask = (freqs_mhz >= f_min_visual) & (freqs_mhz <= f_max_visual)
        if np.any(mask):
            freqs_mhz = freqs_mhz[mask]
            spec_db   = spec_db[:, mask]

    return {
        "matrix":         spec_db,          # (n_blocks × n_scales_vis)
        "times_s":        times_s,
        "freqs_mhz":      freqs_mhz,
        "v_min":          v_min,
        "v_max":          v_max,
        "noise_floor":    noise_floor,
        "cwt_matrix":     spec_db.T,        # legacy
        "freqs_hz":       freqs_hz,
        "freqs_mhz_norm": freqs_mhz,
        "scales":         scales,
        "method": "CWT/Morlet 2D",
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

_welch_window_cache = {}

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
    
    if fft_size not in _welch_window_cache:
        w = np.hanning(fft_size)
        _welch_window_cache[fft_size] = (w, np.sum(w ** 2))
    window, win_power = _welch_window_cache[fft_size]

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
# 7. Helpers 1D para espectrogramas 2D (ventana deslizante)
# ─────────────────────────────────────────────────────────────────────────────

def _burg_psd_1d(sig: np.ndarray, order: int, n_freqs: int) -> np.ndarray:
    """Calcula PSD por Burg para un solo segmento. Retorna array 1D en dB."""
    N = len(sig)
    order = min(order, N // 2 - 1)

    ef = sig[1:].copy()
    eb = sig[:-1].copy()
    ar_coeffs = np.zeros(order, dtype=np.complex128)
    total_err = np.dot(sig, sig.conj()).real / N

    for m in range(order):
        num = -2.0 * np.dot(ef, eb.conj())
        den = np.dot(ef, ef.conj()) + np.dot(eb, eb.conj())
        km = num / (den + 1e-30)

        ar_new = ar_coeffs[:m+1].copy()
        ar_new[m] = km
        ar_new[:m] = ar_coeffs[:m] + km * ar_coeffs[:m][::-1].conj()
        ar_coeffs[:m+1] = ar_new

        ef_new = ef[1:] + km * eb[1:]
        eb_new = eb[:-1] + km.conj() * ef[:-1]
        ef, eb = ef_new, eb_new
        total_err *= (1.0 - abs(km) ** 2)

    freqs_norm = np.linspace(-0.5, 0.5, n_freqs)
    z = np.exp(2j * np.pi * freqs_norm)

    denom = np.ones(n_freqs, dtype=np.complex128)
    for k, a in enumerate(ar_coeffs):
        denom += a * z ** (-(k + 1))

    psd = total_err / (np.abs(denom) ** 2 + 1e-30)
    return 10 * np.log10(np.fft.fftshift(psd) + 1e-30)


def _correlogram_psd_1d(sig: np.ndarray, max_lag: int, fft_size: int) -> np.ndarray:
    """Calcula PSD por correlograma para un solo segmento. Retorna array 1D en dB."""
    N = len(sig)
    max_lag = min(max_lag, N // 2)

    acf = np.zeros(2 * max_lag + 1, dtype=np.complex128)
    for k in range(max_lag + 1):
        acf[max_lag + k] = np.dot(sig[:N - k], sig[k:].conj()) / N
        acf[max_lag - k] = acf[max_lag + k].conj()

    bartlett = np.bartlett(2 * max_lag + 1)
    acf_windowed = acf * bartlett

    fft_size_eff = max(fft_size, 2 * (2 * max_lag + 1))
    psd_raw = np.abs(np.fft.fftshift(np.fft.fft(acf_windowed, n=fft_size_eff)))
    psd_db = 10 * np.log10(psd_raw + 1e-30)

    if len(psd_db) != fft_size:
        idx = np.round(np.linspace(0, len(psd_db) - 1, fft_size)).astype(int)
        psd_db = psd_db[idx]

    return psd_db


# ─────────────────────────────────────────────────────────────────────────────
# 8. AR/Burg 2D — Espectrograma paramétrico (ventana deslizante)
# ─────────────────────────────────────────────────────────────────────────────

def run_ar_burg_2d(iq: np.ndarray, order: int = 20, n_freqs: int = 1024,
                   window_len: int = 128, overlap: float = 0.5,
                   block_size: int = 5000, block_overlap: float = 0.5,
                   sample_rate: float = 2_400_000,
                   center_freq: float = 1420.40,
                    offset_calibracion: float = -60.0,
                   f_min_visual: float = None,
                   f_max_visual: float = None) -> dict:
    """
    Espectrograma paramétrico AR/Burg 2D por bloques: replica el main_ar.m de MATLAB.
    Procesa el buffer IQ completo en bloques de block_size, aplica pyulear equivalente
    (Burg) sobre ventanas deslizantes dentro de cada bloque, acumulando filas en la
    matriz 2D tiempo-frecuencia.

    El método de Burg estima los coeficientes AR minimizando simultáneamente el
    error de predicción hacia adelante y hacia atrás (Burg, 1967).

    Args:
        iq               : Muestras IQ (buffer completo).
        order            : Orden del modelo AR (default=20, igual que MATLAB).
        n_freqs          : Puntos en el eje de frecuencia (igual que nfft en MATLAB).
        window_len       : Longitud de ventana interna (igual que window_len MATLAB).
        overlap          : Fracción de solapamiento de ventana interna.
        block_size       : Tamaño de bloque externo (igual a blockSize=5000 en MATLAB).
        block_overlap    : Fracción de solapamiento entre bloques.
        sample_rate      : Tasa de muestreo en Hz.
        center_freq      : Frecuencia central en MHz.
        offset_calibracion: Offset de calibración en dB (igual que MATLAB).
        f_min_visual     : Frecuencia mínima para máscara visual (MHz).
        f_max_visual     : Frecuencia máxima para máscara visual (MHz).

    Returns:
        dict con 'matrix' (n_segs × n_freqs), 'times_s', 'freqs_mhz',
        'v_min', 'v_max', 'noise_floor', 'method'.

    Ref: J. P. Burg, "Maximum entropy spectral analysis", Ph.D. Dissertation,
         Stanford University, 1975.
    """
    N = len(iq)
    fc_hz  = center_freq * 1e6
    fs_mhz = sample_rate / 1e6

    # Vector de frecuencia: centrado en fc (igual que f_abs = fc + f_vec en MATLAB)
    f_vec     = np.arange(-n_freqs // 2, n_freqs // 2) * (sample_rate / n_freqs)
    freqs_mhz = (fc_hz + f_vec) / 1e6

    overlap_samples   = int(window_len * overlap)
    step_win          = window_len - overlap_samples
    block_overlap_len = int(block_size * block_overlap)
    step_block        = block_size - block_overlap_len
    n_blocks          = max(1, (N - block_overlap_len) // step_block)

    # Limitar el número máximo de segmentos para rendimiento (≈150 filas en pantalla)
    from core.dsp_engine import engine_instance as _eng
    total_segs_target = 150
    total_samples_history = _eng.waterfall_history_sec * sample_rate
    global_step = max(1, int(total_samples_history / total_segs_target))

    seg_starts_global = np.arange(0, N - window_len + 1, global_step)
    num_seg = len(seg_starts_global)
    if num_seg == 0:
        empty = np.full((1, n_freqs), offset_calibracion)
        return {
            "matrix": empty, "times_s": np.array([0.0]),
            "freqs_mhz": freqs_mhz,
            "v_min": offset_calibracion - 5, "v_max": offset_calibracion + 30,
            "noise_floor": float(offset_calibracion),
            "method": "AR/Burg 2D",
        }

    t_signal = np.arange(N, dtype=np.float32) / sample_rate
    t_seg_abs = t_signal[seg_starts_global] + (window_len / 2) / sample_rate

    # ── Pre-calcular ventana de Hanning ───────────────────────────────────────
    hann_win = np.hanning(window_len).astype(np.float32)
    eff_order = min(order, window_len // 2 - 1)

    # Pre-calcular la matriz de Vandermonde para la evaluación del polinomio AR
    freqs_eval = (f_vec / sample_rate).astype(np.float64)
    z_eval     = np.exp(2j * np.pi * freqs_eval)                      # (n_freqs,)
    k_idx      = np.arange(1, eff_order + 1, dtype=np.float64)
    powers     = (z_eval[:, None] ** (-k_idx[None, :])).astype(np.complex64) # (n_freqs, eff_order)

    # Promediar n_sub sub-ventanas por cada intervalo de global_step para consistencia absoluta
    n_sub = 1
    sub_offsets = np.linspace(0, max(0, global_step - window_len), n_sub, dtype=int)
    spec_matrix_accum = np.zeros((num_seg, n_freqs), dtype=np.float32)

    for offset_val in sub_offsets:
        starts_shifted = np.clip(seg_starts_global + offset_val, 0, N - window_len).astype(np.int64)
        idx_matrix = starts_shifted[:, None] + np.arange(window_len)  # (num_seg, window_len)
        seg_matrix = iq[idx_matrix].astype(np.complex64)              # (num_seg, window_len)

        # Eliminar DC + aplicar ventana de Hanning
        seg_matrix = (seg_matrix - seg_matrix.mean(axis=1, keepdims=True)) * hann_win

        # ── Algoritmo de Burg vectorizado por lote (lotes de todos los segmentos) ──
        ef = seg_matrix[:, 1:].copy()       # error hacia adelante (num_seg, window_len - 1)
        eb = seg_matrix[:, :-1].copy()      # error hacia atrás (num_seg, window_len - 1)
        ar_coeffs = np.zeros((num_seg, eff_order), dtype=np.complex64)
        total_err = np.sum(np.abs(seg_matrix) ** 2, axis=1) / window_len  # (num_seg,)

        for m in range(eff_order):
            # Coeficiente de reflexión (km) de Burg vectorizado para todos los segmentos
            num = -2.0 * np.sum(ef * np.conj(eb), axis=1) # (num_seg,)
            den = np.sum(np.abs(ef) ** 2, axis=1) + np.sum(np.abs(eb) ** 2, axis=1) # (num_seg,)
            km = num / (den + 1e-30) # (num_seg,)

            # Actualización de Levinson-Durbin vectorizada
            ar_new = ar_coeffs[:, :m].copy()
            ar_coeffs[:, :m] = ar_new + km[:, None] * np.conj(ar_new[:, ::-1])
            ar_coeffs[:, m] = km

            # Actualización de errores hacia adelante y hacia atrás
            ef_new = ef[:, 1:] + km[:, None] * eb[:, 1:]
            eb_new = eb[:, :-1] + np.conj(km[:, None]) * ef[:, :-1]
            ef, eb = ef_new, eb_new

            total_err *= (1.0 - np.abs(km) ** 2)

        # Denominador vectorizado utilizando el producto matricial (Vandermonde x coeficientes)
        # powers: (n_freqs, eff_order), ar_coeffs: (num_seg, eff_order) -> denom: (num_seg, n_freqs)
        denom = 1.0 + ar_coeffs @ powers.T
        psd = total_err[:, None] / (np.abs(denom) ** 2 + 1e-30)
        spec_matrix_accum += psd.real

    spec_matrix = 10 * np.log10(spec_matrix_accum / n_sub + 1e-30)


    # ── Calibración y máscara ─────────────────────────────────────────────────
    P_dBm = spec_matrix + offset_calibracion
    noise_floor = float(np.median(P_dBm))

    if f_min_visual is not None and f_max_visual is not None:
        mask = (freqs_mhz >= f_min_visual) & (freqs_mhz <= f_max_visual)
        if np.any(mask):
            freqs_mhz = freqs_mhz[mask]
            P_dBm = P_dBm[:, mask]

    v_min = noise_floor - 5.0
    v_max = float(np.max(P_dBm)) + 2.0
    if v_max < v_min + 10.0:
        v_max = v_min + 20.0

    return {
        "matrix":      P_dBm,
        "times_s":     t_seg_abs,
        "freqs_mhz":   freqs_mhz,
        "v_min":       v_min,
        "v_max":       v_max,
        "noise_floor": noise_floor,
        "method":      "AR/Burg 2D",
    }



# ─────────────────────────────────────────────────────────────────────────────
# 9. Correlograma 2D — Método Blackman-Tukey (xcorr biased + Bartlett)
# ─────────────────────────────────────────────────────────────────────────────

def run_correlogram_2d(iq: np.ndarray, max_lag: int = 37, n_freqs: int = 1024,
                       window_len: int = 128, overlap: float = 0.5,
                       block_size: int = 5000, block_overlap: float = 0.5,
                       offset_calibracion: float = -120.0,
                       f_min_visual: float = None,
                       f_max_visual: float = None,
                       sample_rate: float = 2_400_000,
                       center_freq: float = 1420.40) -> dict:
    """
    Espectrograma 2D por Correlograma método Blackman-Tukey.
    Optimizado para rendimiento en tiempo real: procesa un número fijo
    de segmentos a lo largo del buffer, independientemente del tamaño.
    """
    N = len(iq)

    # 1. Adaptar el tamaño de la ventana al max_lag deseado por el usuario
    # Para estimar autocorrelación hasta max_lag, necesitamos al menos 2*max_lag + 1 muestras
    # Ignoramos el window_len hardcodeado para dar prioridad al max_lag elegido en UI
    window_len_eff = max(int(max_lag * 2.5), 128)
    lag_eff = min(max_lag, window_len_eff // 2)

    fs_mhz    = sample_rate / 1_000_000
    f_vec     = np.arange(-n_freqs // 2, n_freqs // 2) * (sample_rate / n_freqs)
    freqs_mhz = (center_freq * 1e6 + f_vec) / 1e6   # MHz

    if N < window_len_eff:
        empty = np.full((1, n_freqs), offset_calibracion)
        return {
            "matrix": empty, "times_s": np.array([0.0]),
            "freqs_mhz": freqs_mhz,
            "v_min": offset_calibracion - 5, "v_max": offset_calibracion + 30,
            "noise_floor": float(offset_calibracion),
            "method": "Correlograma 2D (Blackman-Tukey)",
        }

    t_signal  = np.arange(N) / sample_rate

    # 2. Rendimiento extremo: Extraemos segmentos con un PASO FIJO en el tiempo.
    # Así la textura de los datos pasados no cambia al añadir datos nuevos.
    num_segs_target = 150
    # Calculamos cuántas muestras representan el avance entre una línea y otra en la pantalla
    from core.dsp_engine import engine_instance
    total_samples_in_history = engine_instance.waterfall_history_sec * sample_rate
    step_win = max(1, int(total_samples_in_history / num_segs_target))
    
    seg_starts = np.arange(0, N - window_len_eff + 1, step_win)

    num_seg = len(seg_starts)
    if num_seg == 0:
        empty = np.full((1, n_freqs), offset_calibracion)
        return {
            "matrix": empty, "times_s": np.array([0.0]),
            "freqs_mhz": freqs_mhz,
            "v_min": offset_calibracion - 5, "v_max": offset_calibracion + 30,
            "noise_floor": float(offset_calibracion),
            "method": "Correlograma 2D (Blackman-Tukey)",
        }

    P_blk = np.zeros((n_freqs, num_seg), dtype=np.float64)
    t_seg_abs = t_signal[seg_starts] + (window_len_eff / 2) / sample_rate

    # ── Vectorización total: sin loop Python ─────────────────────────────────
    # Construir matriz de segmentos (num_seg × window_len_eff) en un solo indexing
    idx_matrix = seg_starts[:, None] + np.arange(window_len_eff)   # (num_seg, window_len)
    seg_matrix = iq[idx_matrix].astype(np.complex64)                 # (num_seg, window_len)

    # Autocorrelación batch vía FFT: O(num_seg × N log N)
    n_fft_ac = 2 ** int(np.ceil(np.log2(2 * window_len_eff - 1)))
    SEG  = np.fft.fft(seg_matrix, n=n_fft_ac, axis=1)               # (num_seg, n_fft_ac)
    Rcirc = np.fft.ifft(SEG * np.conj(SEG), axis=1)                 # (num_seg, n_fft_ac) (Complejo)

    # Extraer lags [-lag_eff ... +lag_eff]
    w = np.bartlett(2 * lag_eff + 1)
    R_neg = Rcirc[:, n_fft_ac - lag_eff:]                           # (num_seg, lag_eff)
    R_pos = Rcirc[:, :lag_eff + 1]                                  # (num_seg, lag_eff+1)
    R = np.concatenate([R_neg, R_pos], axis=1) * (n_fft_ac / window_len_eff) # (num_seg, 2*lag+1)
    R_w = R * w                                                       # broadcast row-wise

    # PSD batch (num_seg × n_freqs)
    P_batch = np.fft.fftshift(
        np.abs(np.fft.fft(R_w, n=n_freqs, axis=1)), axes=1
    )                                                                 # (num_seg, n_freqs)
    P_blk = P_batch.T                                                 # (n_freqs, num_seg)

    P_all = 10 * np.log10(P_blk + np.finfo(float).eps) + offset_calibracion
    t_all = t_seg_abs

    # ── Máscara de frecuencia visual (= mask_vis del script de referencia) ────
    if f_min_visual is not None and f_max_visual is not None:
        mask = (freqs_mhz >= f_min_visual) & (freqs_mhz <= f_max_visual)
        if np.any(mask):
            freqs_mhz = freqs_mhz[mask]
            P_all     = P_all[mask, :]

    # ── Auto-escala dinámica ──────────────────────────────────────────────────
    noise_floor = float(np.median(P_all))
    v_min = noise_floor - 5.0
    v_max = float(np.max(P_all)) + 2.0
    if v_max < v_min + 20.0:
        v_max = v_min + 20.0

    return {
        "matrix": P_all.T,        # (n_segs × n_freqs_vis)
        "times_s": t_all,
        "freqs_mhz": freqs_mhz,
        "v_min": v_min,
        "v_max": v_max,
        "noise_floor": noise_floor,
        "method": "Correlograma 2D (Blackman-Tukey)",
    }


# ─────────────────────────────────────────────────────────────────────────────
# 10. ASLT — Stub async-ready (pendiente de archivos externos)
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
