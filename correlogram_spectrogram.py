import numpy as np
import matplotlib.pyplot as plt
from scipy.signal.windows import bartlett

# ── CONFIGURACIÓN (idéntica a main_indirecto.m) ──────────────────────────────
IQ_FILE   = r"C:\uic_radiotelescopio\data\test_signal_1.iq"
fs        = 2.4e6          # Hz
fc        = 1420e6       # Hz  (línea HI)
PERCENT_TO_ANALYZE = 0.05
nfft      = 1024
max_lag   = 37
window_len = 128
overlap    = window_len // 2
step_win   = window_len - overlap

# Visualización
anchoBanda         = 400e3      # Hz
f_min_visual       = 1415e6  # Hz
f_max_visual       = 1425e6  # Hz
rangoColores       = None        # <--- AHORA ES AUTOMÁTICO
alinearRuido       = False       # Ver niveles reales
nivelRuidoObjetivo = -80.0      # dBm
offset_calibracion = -120.0     # dBm  (igual a MATLAB)
umbral_guardado    = -70.0      # dBm

# Bloques
blockSize    = 5000
overlap_blk  = blockSize // 2
step_blk     = blockSize - overlap_blk

# ── 1. LECTURA DEL ARCHIVO IQ ─────────────────────────────────────────────────
raw = np.fromfile(IQ_FILE, dtype=np.int16)          # igual que fread(...,'short=>single')
y   = raw[0::2].astype(np.float32) + 1j * raw[1::2].astype(np.float32)

totalMuestrasArchivo = len(y)
duracionTotalArchivo = totalMuestrasArchivo / fs

y = y[:int(totalMuestrasArchivo * PERCENT_TO_ANALYZE)]  # Usar porcentaje configurable
muestrasAnalizadas = len(y)
duracionAnalizada = muestrasAnalizadas / fs

print(f"--- INFO DEL ARCHIVO ---")
print(f"Duración Total del Archivo: {duracionTotalArchivo:.2f} segundos")
print(f"Porcentaje Seleccionado:    {PERCENT_TO_ANALYZE*100:.1f}%")
print(f"Duración a Analizar:       {duracionAnalizada:.2f} segundos ({muestrasAnalizadas} muestras)")
print(f"-------------------------")

t_signal = np.arange(len(y)) / fs   # timeOff = 0 (archivo completo)

# ── 2. VECTORES DE FRECUENCIA ─────────────────────────────────────────────────
f_vec = np.arange(-nfft // 2, nfft // 2) * (fs / nfft)  # centrado en 0
f_abs = fc + f_vec                                         # frecuencia real

# ── 3. VENTANA BARTLETT para lags ─────────────────────────────────────────────
w_lag = bartlett(2 * max_lag + 1)

# ── 4. PROCESAMIENTO POR BLOQUES ──────────────────────────────────────────────
numBlocks = (len(y) - overlap_blk) // step_blk

all_t_seg  = []   # tiempos centrales de cada segmento
all_P_dBm  = []   # [freq x segs] acumulados

for k in range(numBlocks):
    idx_s   = k * step_blk
    idx_e   = idx_s + blockSize
    y_blk   = y[idx_s:idx_e]
    t_start = t_signal[idx_s]

    # Segmentar bloque (buffer con overlap)
    seg_starts = np.arange(0, len(y_blk) - window_len + 1, step_win)
    num_seg    = len(seg_starts)
    if num_seg == 0:
        continue

    t_seg_abs = t_start + (seg_starts + window_len / 2) / fs
    P_blk     = np.zeros((nfft, num_seg), dtype=np.float64)

    for i, s0 in enumerate(seg_starts):
        seg = y_blk[s0 : s0 + window_len]

        # xcorr biased (igual que MATLAB xcorr(seg, max_lag, 'biased'))
        R_full = np.correlate(seg, seg, mode='full')          # lags: -(N-1)...(N-1)
        mid    = len(R_full) // 2
        R      = R_full[mid - max_lag : mid + max_lag + 1]    # lags -max_lag...max_lag
        R      = R / len(seg)                                  # biased

        # Ventana Bartlett sobre los lags
        R_w = R * w_lag

        # FFT del correlograma → estimación espectral (Blackman-Tukey)
        P_i       = np.fft.fftshift(np.abs(np.fft.fft(R_w, n=nfft)))
        P_blk[:, i] = P_i

    # Potencia en dBm
    P_dBm = 10 * np.log10(P_blk + np.finfo(float).eps) + offset_calibracion

    # Nivel de ruido del bloque
    r_est = np.median(P_dBm)
    if (k+1)%100 == 0: 
        print(f"   > Nivel de Ruido Bloque {k+1}: {r_est:.2f} dBm")

    if alinearRuido:
        P_dBm += (nivelRuidoObjetivo - r_est)

    all_t_seg.append(t_seg_abs)
    all_P_dBm.append(P_dBm)

    if (k + 1) % 100 == 0:
        print(f" Bloque {k+1}/{numBlocks} ({100*(k+1)/numBlocks:.0f}%)")

# Concatenar y asegurar que el tiempo sea monótono
t_all_raw = np.concatenate(all_t_seg)
P_all_raw = np.hstack(all_P_dBm)

# Calcular ruido promedio real antes de cualquier otra cosa
ruido_promedio_total = np.median(P_all_raw)
print(f"\n>>> NIVEL DE RUIDO REAL DETECTADO: {ruido_promedio_total:.2f} dBm <<<\n")

# Ordenar por tiempo
idx_unique = np.unique(t_all_raw, return_index=True)[1]
t_all = t_all_raw[idx_unique]
P_all = P_all_raw[:, idx_unique]

# ── 5. VISUALIZACIÓN ──────────────────────────────────────────────────────────
mask_vis = (f_abs >= f_min_visual) & (f_abs <= f_max_visual)
f_vis    = f_abs[mask_vis] / 1e6   # MHz
P_vis    = P_all[mask_vis, :]      # [freq_vis x segs]

# --- Perfil Espectral Promedio ---
P_lin_all  = 10 ** (P_all / 10)
spec_profile = 10 * np.log10(np.mean(P_lin_all, axis=1))

fig_p, ax_p = plt.subplots(figsize=(10, 4))
ax_p.plot(f_abs / 1e6, spec_profile, 'k', linewidth=1.2)
ax_p.axvline(x=fc / 1e6, color='r', linestyle='--', linewidth=1.0)
ax_p.set_xlabel('Frecuencia (MHz)')
ax_p.set_ylabel('Amplitud Promedio (dBm)')
ax_p.set_title(f'Perfil Espectral Promedio ({PERCENT_TO_ANALYZE*100:.1f}%)')
ax_p.grid(True)
fig_p.savefig(r"C:\uic_radiotelescopio\data\correlogram_perfil.png", dpi=100)
print("✔ Perfil espectral guardado.")
MAX_SEGS_PLOT = 1000 
if len(t_all) > MAX_SEGS_PLOT:
    step_p = len(t_all) // MAX_SEGS_PLOT
    t_plot = t_all[::step_p]
    P_plot = P_vis[:, ::step_p]
else:
    t_plot = t_all
    P_plot = P_vis

# --- Auto-escala dinámica ---
ruido_ref = np.median(P_vis)
v_min = ruido_ref - 5   # 5 dB por debajo del ruido
v_max = np.max(P_vis) + 2 # O podrías usar ruido_ref + 40
if v_max < v_min + 10: v_max = v_min + 30 # Asegurar un mínimo de rango dinámico

print(f"Auto-Escala: vmin={v_min:.1f} dBm, vmax={v_max:.1f} dBm")

fig2d, ax2d = plt.subplots(figsize=(10, 6))
im = ax2d.pcolormesh(
    f_vis, t_plot, P_plot.T,
    cmap='jet',
    vmin=v_min, vmax=v_max,
    shading='nearest'
)
plt.colorbar(im, ax=ax2d, label='Potencia (dBm)')
ax2d.set_xlabel('Frecuencia (MHz)')
ax2d.set_ylabel('Tiempo (s)')
ax2d.set_title(f'Correlograma 2D ({PERCENT_TO_ANALYZE*100:.1f}%) — Línea HI 1420 MHz')
ax2d.axvline(x=fc / 1e6, color='r', linestyle='--', linewidth=1.0)
fig2d.savefig(r"C:\uic_radiotelescopio\data\correlogram_2D.png", dpi=100)
print("✔ Espectrograma 2D guardado.")
plt.show()
print("Proceso completado.")