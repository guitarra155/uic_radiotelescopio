import os
import numpy as np
import matplotlib.pyplot as plt

# 1. Identificación del Proyecto: UIC Radiotelescopio (Plataforma DSP para Radioastronomía)
# Fichero de datos IQ pre-grabado por defecto en formato int16 (I: 16-bit, Q: 16-bit)
FILE_PATH = os.path.join("data", "test_signal.iq")
SAMPLE_RATE = 10_000_000  # 10 MSps (ejemplo)
WINDOW_SIZE = 50          # Ancho del Moving Average

# 2. Leer muestras del archivo IQ
# Cada muestra compleja consta de I (int16) y Q (int16) -> 4 bytes por muestra
num_samples = 2000
bytes_to_read = num_samples * 2 * 2  # 2 canales * 2 bytes/muestra

if not os.path.exists(FILE_PATH):
    raise FileNotFoundError(f"No se encontró el archivo de datos en {FILE_PATH}")

with open(FILE_PATH, "rb") as f:
    raw_data = f.read(bytes_to_read)

# Decodificar int16 y normalizar a rango [-1.0, 1.0]
samples = np.frombuffer(raw_data, dtype=np.int16).astype(np.float32) / 32768.0
iq_raw = samples[0::2] + 1j * samples[1::2]
t = np.arange(len(iq_raw)) / SAMPLE_RATE

# 3. Aplicar Filtro Moving Average (Promedio Móvil)
# Se aplica np.convolve de forma directa sobre la señal compleja
window = np.ones(WINDOW_SIZE) / WINDOW_SIZE
iq_filtered = np.convolve(iq_raw, window, mode='same')

# 4. Graficar Señales
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6), sharex=True)

# Gráfica Superior: Señal IQ Cruda
ax1.plot(t * 1e6, iq_raw.real, label="Componente I (Real)", color="cyan", alpha=0.7)
ax1.plot(t * 1e6, iq_raw.imag, label="Componente Q (Imaginario)", color="magenta", alpha=0.7)
ax1.set_title("Señal IQ Original (Sin Filtrar)")
ax1.set_ylabel("Amplitud (V)")
ax1.legend(loc="upper right")
ax1.grid(True, linestyle="--", alpha=0.5)

# Gráfica Inferior: Señal Filtrada (Moving Average)
ax2.plot(t * 1e6, iq_filtered.real, label="Componente I Filtrado", color="green", alpha=0.9)
ax2.plot(t * 1e6, iq_filtered.imag, label="Componente Q Filtrado", color="orange", alpha=0.9)
ax2.set_title(f"Señal Filtrada - Filtro Moving Average (Ventana = {WINDOW_SIZE})")
ax2.set_xlabel("Tiempo (μs)")
ax2.set_ylabel("Amplitud (V)")
ax2.legend(loc="upper right")
ax2.grid(True, linestyle="--", alpha=0.5)

plt.tight_layout()
plt.show()
