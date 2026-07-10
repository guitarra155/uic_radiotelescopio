import os
import ctypes
import numpy as np
import time

# Obtener la ruta absoluta del directorio actual
current_dir = os.path.dirname(os.path.abspath(__file__))
dll_path = os.path.join(current_dir, "dsp_opt.dll")

print("--- SISTEMA HÍBRIDO DSP (PYTHON + C++) ---")

if not os.path.exists(dll_path):
    print(f"ERROR: No se encontró la DLL compiled en: {dll_path}")
    print("Por favor, ejecuta primero el comando de compilación en tu consola:")
    print("g++ -O3 -shared -o scratch/dsp_opt.dll scratch/dsp_opt.cpp")
    exit(1)

# 1. Cargar la biblioteca dinámica (.dll)
try:
    dsp_lib = ctypes.CDLL(dll_path)
except Exception as e:
    print(f"ERROR al cargar la DLL: {e}")
    exit(1)

# 2. Definir tipos de argumentos y retorno
dsp_lib.calcular_potencia_promedio.argtypes = [
    ctypes.POINTER(ctypes.c_double),
    ctypes.c_int
]
dsp_lib.calcular_potencia_promedio.restype = ctypes.c_double

# 3. Datos de prueba (1,000,000 bins espectrales en dBFS)
print("\nGenerando 1,000,000 de bins espectrales de prueba...")
data = np.random.uniform(-100.0, -10.0, 1000000).astype(np.float64)
ptr_data = data.ctypes.data_as(ctypes.POINTER(ctypes.c_double))

# 4. Medir tiempo en C++
print("Ejecutando en C++ optimizado...")
t0 = time.perf_counter()
resultado_cpp = dsp_lib.calcular_potencia_promedio(ptr_data, len(data))
t_cpp = time.perf_counter() - t0

# 5. Medir tiempo en Python (usando NumPy)
print("Ejecutando en Python (NumPy)...")
t0 = time.perf_counter()
resultado_py = 10.0 * np.log10(np.mean(10.0 ** (data / 10.0)))
t_py = time.perf_counter() - t0

# 6. Mostrar resultados
print("\n=== RESULTADOS ===")
print(f"Potencia promedio (C++):    {resultado_cpp:.6f} dBFS")
print(f"Potencia promedio (NumPy):  {resultado_py:.6f} dBFS")
print(f"Diferencia matemática:     {abs(resultado_cpp - resultado_py):.2e} dBFS")
print(f"Tiempo de ejecución C++:   {t_cpp * 1000:.3f} ms")
print(f"Tiempo de ejecución NumPy: {t_py * 1000:.3f} ms")
print(f"Factor de velocidad C++:   {t_py / t_cpp:.1f}x más rápido")
print("==================")
