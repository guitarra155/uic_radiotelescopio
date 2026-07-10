import numpy as np
import time
import matplotlib.pyplot as plt
import os
from numba import jit

# Configurar estilo visual oscuro coherente con la UI del radiotelescopio
plt.style.use('dark_background')

print("--- SISTEMA ACELERADO JIT (PYTHON + NUMBA) ---")

# 1. Función clásica en Python puro (Bucle)
def calcular_potencia_promedio_python(raw_spectrum):
    suma_lineal = 0.0
    size = len(raw_spectrum)
    for i in range(size):
        suma_lineal += 10.0 ** (raw_spectrum[i] / 10.0)
    promedio_lineal = suma_lineal / size
    return 10.0 * np.log10(promedio_lineal)

# 2. Función compilada con Numba JIT
@jit(nopython=True, fastmath=True)
def calcular_potencia_promedio_numba(raw_spectrum):
    suma_lineal = 0.0
    size = len(raw_spectrum)
    for i in range(size):
        suma_lineal += 10.0 ** (raw_spectrum[i] / 10.0)
    promedio_lineal = suma_lineal / size
    return 10.0 * np.log10(promedio_lineal)

# 3. Preparar datos de prueba (1,000,000 bins espectrales en dBFS)
print("\nGenerando 1,000,000 de bins espectrales de prueba...")
data = np.random.uniform(-100.0, -10.0, 1000000).astype(np.float64)

# 4. Medir tiempo en Python puro
print("Ejecutando en Python puro (Bucle)...")
t0 = time.perf_counter()
resultado_py = calcular_potencia_promedio_python(data)
t_py = (time.perf_counter() - t0) * 1000.0 # Convertir a ms

# 5. Medir tiempo con Numba JIT (Calentamiento + Medida)
calcular_potencia_promedio_numba(data[:10])
print("Ejecutando en Numba JIT (Código Máquina)...")
t0 = time.perf_counter()
resultado_jit = calcular_potencia_promedio_numba(data)
t_jit = (time.perf_counter() - t0) * 1000.0 # Convertir a ms

# 6. Medir tiempo de NumPy optimizado (C nativo por debajo)
print("Ejecutando con NumPy vectorizado...")
t0 = time.perf_counter()
resultado_numpy = 10.0 * np.log10(np.mean(10.0 ** (data / 10.0)))
t_numpy = (time.perf_counter() - t0) * 1000.0 # Convertir a ms

# 7. Graficar resultados
metodos = ['Python Puro (Bucle)', 'Numba JIT (Compilado)', 'NumPy Vectorizado']
tiempos = [t_py, t_jit, t_numpy]
colores = ['#FF4C4C', '#00D2FF', '#00FF88'] # Rojo, Cian, Verde

fig, ax = plt.subplots(figsize=(8, 5))
bars = ax.bar(metodos, tiempos, color=colores, width=0.5, edgecolor='#333333', linewidth=1)

# Añadir valores exactos sobre las barras
for bar in bars:
    height = bar.get_height()
    ax.annotate(f'{height:.2f} ms',
                xy=(bar.get_x() + bar.get_width() / 2, height),
                xytext=(0, 3),  # Desplazamiento vertical de 3 puntos
                textcoords="offset points",
                ha='center', va='bottom', fontsize=9, color='#FFFFFF', weight='bold')

ax.set_ylabel('Tiempo de ejecución (milisegundos)', color='#888888', fontsize=10)
ax.set_title('Comparativa de Rendimiento DSP (1M puntos)', color='#00D2FF', fontsize=12, weight='bold', pad=15)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['left'].set_color('#333333')
ax.spines['bottom'].set_color('#333333')
ax.tick_params(colors='#888888', labelsize=9)
ax.grid(axis='y', linestyle='--', alpha=0.2, color='#555555')

# Guardar la gráfica en la carpeta scratch
current_dir = os.path.dirname(os.path.abspath(__file__))
image_path = os.path.join(current_dir, "comparativa_tiempos.png")
plt.tight_layout()
plt.savefig(image_path, dpi=150)
plt.close()

print("\n=== GRÁFICA GENERADA ===")
print(f"La gráfica comparativa ha sido guardada en: {image_path}")
print("Puedes abrir esa imagen para visualizar la relación de velocidades.")
print("========================")
