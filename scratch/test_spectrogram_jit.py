import numpy as np
import time
import matplotlib.pyplot as plt
import os
from numba import jit

# Configurar estilo visual oscuro coherente con el radiotelescopio
plt.style.use('dark_background')

print("--- DEMOSTRACIÓN DE ESPECTROGRAMA 2D ACELERADO CON JIT/C ---")

# 1. Simulación de señal IQ de prueba: Tono sintonizado a 100 kHz con ruido térmico aditivo
fs = 1.0e6  # Tasa de muestreo (1 MSps)
t = np.arange(131072) / fs
# Generar señal analítica compleja (I + j*Q)
f_signal = 120e3  # Frecuencia del tono
iq_signal = np.exp(2j * np.pi * f_signal * t) + (np.random.normal(0, 0.4, len(t)) + 1j * np.random.normal(0, 0.4, len(t)))

nfft = 1024       # Tamaño de la FFT
overlap = 512     # Solapamiento de ventanas (50%)
n_windows = (len(iq_signal) - nfft) // (nfft - overlap) + 1

# Ventana Hamming teórica precalculada
window_hamming = np.hamming(nfft)

# 2. Algoritmo de Espectrograma en Python Puro (Bucle tradicional)
def calcular_espectrograma_python(iq, nfft, overlap, win):
    step = nfft - overlap
    n_win = (len(iq) - nfft) // step + 1
    # Matriz 2D de salida (Ventanas temporales x Bins espectrales)
    spectrogram = np.zeros((n_win, nfft))
    
    for i in range(n_win):
        start = i * step
        end = start + nfft
        # Segmentar y aplicar ventana
        segmento = iq[start:end] * win
        # Transformada Discreta de Fourier (espectro de magnitud lineal)
        # Nota: Emulamos el bucle matemático para ver el impacto del compilador
        fft_res = np.fft.fft(segmento)
        spectrogram[i, :] = 10.0 * np.log10(np.abs(fft_res) ** 2 + 1e-10)
        
    return spectrogram

# 3. Algoritmo de Espectrograma en Numba JIT (Emulación directa de bucles C/C++)
# Usamos fastmath y paralelismo para máxima optimización
@jit(nopython=True, fastmath=True)
def calcular_espectrograma_jit(iq, nfft, overlap, win):
    step = nfft - overlap
    n_win = (len(iq) - nfft) // step + 1
    spectrogram = np.zeros((n_win, nfft))
    
    for i in range(n_win):
        start = i * step
        # Extraer el bloque y aplicar la ventana de Hamming elemento por elemento
        segmento = np.zeros(nfft, dtype=np.complex128)
        for j in range(nfft):
            segmento[j] = iq[start + j] * win[j]
            
        # Transformada de Fourier discreta nativa
        fft_res = np.fft.fft(segmento)
        
        # Calcular densidad espectral de potencia y convertir a dBFS
        for j in range(nfft):
            potencia_lineal = (fft_res[j].real ** 2) + (fft_res[j].imag ** 2)
            spectrogram[i, j] = 10.0 * np.log10(potencia_lineal + 1e-10)
            
    return spectrogram

# --- PRUEBAS DE VELOCIDAD ---

print(f"\nProcesando buffer de {len(iq_signal)} muestras IQ complejas...")
print(f"Dimensiones de la matriz 2D resultante: {n_windows} ventanas x {nfft} bins espectrales.")

# A. Ejecución en Python Puro
print("\nEjecutando espectrograma en Python Puro (Bucle)...")
t0 = time.perf_counter()
spec_py = calcular_espectrograma_python(iq_signal, nfft, overlap, window_hamming)
t_py = (time.perf_counter() - t0) * 1000.0

# B. Ejecución en JIT (Calentamiento de compilación primero)
calcular_espectrograma_jit(iq_signal[:2048], nfft, overlap, window_hamming)
print("Ejecutando espectrograma en JIT (Velocidad C/C++)...")
t0 = time.perf_counter()
spec_jit = calcular_espectrograma_jit(iq_signal, nfft, overlap, window_hamming)
t_jit = (time.perf_counter() - t0) * 1000.0

print(f"\nTiempo Python Puro: {t_py:.2f} ms")
print(f"Tiempo JIT (C++):   {t_jit:.2f} ms")
print(f"--> ¡Aceleración de {t_py / t_jit:.1f} veces más rápido!")

# --- GENERACIÓN DEL ESPECTROGRAMA GRÁFICO (CASCADA) ---

print("\nGenerando imagen del espectrograma 2D en cascada...")

fig, (ax_sig, ax_spec) = plt.subplots(2, 1, figsize=(10, 7), gridspec_kw={'height_ratios': [1, 2]})

# Graficar traza de señal temporal
time_axis = np.arange(len(iq_signal)) / fs * 1000.0 # ms
ax_sig.plot(time_axis[:2000], iq_signal.real[:2000], color=ACCENT_CYAN, label='Componente I (Real)', alpha=0.8)
ax_sig.plot(time_axis[:2000], iq_signal.imag[:2000], color=ACCENT_AMBER, label='Componente Q (Imag)', alpha=0.6)
ax_sig.set_title("Señal IQ Cruda Temporal (Fragmento inicial)", fontsize=11, weight='bold', color=ACCENT_CYAN)
ax_sig.set_ylabel("Amplitud", color='#888888')
ax_sig.set_xlabel("Tiempo (ms)", color='#888888')
ax_sig.legend(loc='upper right', frameon=False, fontsize=8)
ax_sig.grid(alpha=0.15)

# Graficar Espectrograma 2D (cascada)
# Centrar el espectro desplazando la frecuencia central (FFTShift)
spec_shift = np.fft.fftshift(spec_jit, axes=1)
freq_axis = np.fft.fftshift(np.fft.fftfreq(nfft, 1/fs)) / 1e3 # kHz

im = ax_spec.imshow(
    spec_shift,
    extent=[freq_axis[0], freq_axis[-1], n_windows, 0],
    cmap='inferno',
    aspect='auto',
    vmax=spec_shift.max(),
    vmin=spec_shift.max() - 45 # Rango dinámico de 45 dB
)

ax_spec.set_title("Espectrograma 2D en Cascada (Generado a Velocidad Nativa)", fontsize=11, weight='bold', color=ACCENT_GREEN)
ax_spec.set_xlabel("Frecuencia (kHz)", color='#888888')
ax_spec.set_ylabel("Ventana Temporal (Índice)", color='#888888')

# Colorbar estilizada
cbar = fig.colorbar(im, ax=ax_spec, orientation='horizontal', pad=0.15, shrink=0.7)
cbar.set_label('Potencia Espectral de Densidad (dBFS)', color='#888888', fontsize=9)
cbar.ax.tick_params(labelsize=8, colors='#888888')

plt.tight_layout()

# Guardar la imagen en scratch
current_dir = os.path.dirname(os.path.abspath(__file__))
image_path = os.path.join(current_dir, "espectrograma_acelerado.png")
plt.savefig(image_path, dpi=150)
plt.close()

print(f"\nEspectrograma guardado exitosamente en:\n{image_path}")
print("Puedes abrir este archivo para visualizar la cascada generada.")
print("============================================================")
