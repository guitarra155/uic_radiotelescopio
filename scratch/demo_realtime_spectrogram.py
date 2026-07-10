import numpy as np
import time
import matplotlib.pyplot as plt

# Configurar estilo oscuro coherente con el sistema
plt.style.use('dark_background')

print("--- DEMOSTRACIÓN DEL ESPECTROGRAMA EN TIEMPO REAL (60 FPS) ---")
print("Cargando ventana interactiva de Matplotlib...")

# Parámetros del Espectrograma
nfft = 1024
overlap = 512
step = nfft - overlap
n_windows = 120  # Número de líneas verticales en la cascada
fs = 1.0e6       # 1 MSps

# Generar ventana de Hamming
window_hamming = np.hamming(nfft)

# Crear matriz inicial de la cascada llena de ruido base (-80 dBFS)
spectrogram_data = np.random.uniform(-80.0, -75.0, (n_windows, nfft))

# Crear la ventana gráfica interactiva
fig, ax = plt.subplots(figsize=(9, 6))

# Desplazar la frecuencia para centrar en 0 (FFTShift)
freq_axis = np.fft.fftshift(np.fft.fftfreq(nfft, 1/fs)) / 1e3 # kHz

im = ax.imshow(
    spectrogram_data,
    extent=[freq_axis[0], freq_axis[-1], n_windows, 0],
    cmap='inferno',
    aspect='auto',
    vmax=-10,
    vmin=-75
)

ax.set_title("Espectrograma 2D en Cascada (Simulación en Tiempo Real)", fontsize=12, weight='bold', color='#00D2FF', pad=15)
ax.set_xlabel("Frecuencia (kHz)", color='#888888')
ax.set_ylabel("Líneas de Historial", color='#888888')
cbar = fig.colorbar(im, ax=ax, orientation='horizontal', pad=0.12, shrink=0.7)
cbar.set_label('Potencia Espectral de Densidad (dBFS)', color='#888888', fontsize=9)
cbar.ax.tick_params(labelsize=8, colors='#888888')

plt.tight_layout()

# Habilitar modo interactivo de Matplotlib para renderizado al vuelo
plt.ion()
plt.show()

# Parámetros de simulación de señal
t_start = time.perf_counter()
frame_count = 0
fps_timer = time.perf_counter()
fps = 0.0

# Bucle interactivo de alta velocidad
print("\nIniciando renderizado en vivo... Cierra la ventana gráfica para detener.")
try:
    while plt.fignum_exists(fig.number):
        # 1. Simular nueva señal IQ con un tono cuya frecuencia varía sinusoidalmente en el tiempo
        elapsed = time.perf_counter() - t_start
        # Frecuencia del tono variando entre -250 kHz y +250 kHz
        freq_sweep = 250e3 * np.sin(2.0 * np.pi * 0.4 * elapsed)
        
        # Generar un bloque de 1024 muestras IQ con ruido
        t_block = np.arange(nfft) / fs
        noise = (np.random.normal(0, 0.3, nfft) + 1j * np.random.normal(0, 0.3, nfft))
        tone = np.exp(2j * np.pi * freq_sweep * t_block)
        block = tone + noise
        
        # 2. Calcular la FFT del nuevo bloque y pasar a escala de potencia en dBFS
        segmento = block * window_hamming
        fft_res = np.fft.fft(segmento)
        potencia_db = 10.0 * np.log10(np.abs(fft_res) ** 2 / nfft + 1e-10)
        
        # Centrar frecuencias (FFTShift)
        potencia_db_shifted = np.fft.fftshift(potencia_db)
        
        # 3. Desplazar la cascada hacia arriba (scroll vertical) e insertar la nueva traza al inicio
        spectrogram_data = np.roll(spectrogram_data, -1, axis=0)
        spectrogram_data[-1, :] = potencia_db_shifted
        
        # 4. Actualizar únicamente los datos de la imagen (sin reconstruir los ejes) para máxima velocidad
        im.set_data(spectrogram_data)
        
        # 5. Calcular FPS en tiempo real
        frame_count += 1
        curr_time = time.perf_counter()
        if curr_time - fps_timer >= 1.0:
            fps = frame_count / (curr_time - fps_timer)
            ax.set_title(f"Espectrograma 2D en Cascada - RENDIMIENTO: {fps:.1f} FPS", color='#00FF88' if fps > 30 else '#FFD200')
            frame_count = 0
            fps_timer = curr_time
            
        # Refrescar los eventos y el renderizador de la GUI de Matplotlib de forma ultra-rápida
        fig.canvas.restore_region(fig.canvas.copy_from_bbox(ax.bbox))
        ax.draw_artist(im)
        fig.canvas.blit(ax.bbox)
        fig.canvas.flush_events()
        
        # Breve pausa para no saturar al 100% el hilo del procesador principal
        time.sleep(0.01)

except KeyboardInterrupt:
    print("\nSimulación detenida por el usuario.")
except Exception as e:
    print(f"\nVentana cerrada o finalizada: {e}")

print("Simulación terminada.")
