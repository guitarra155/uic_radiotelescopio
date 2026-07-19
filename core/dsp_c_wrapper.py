import ctypes
import os
import platform
import numpy as np

# Cargar la librería compartida
_lib_path = os.path.join(os.path.dirname(__file__), "dsp_fast.dll")

if not os.path.exists(_lib_path):
    raise FileNotFoundError(f"Librería DSP compilada no encontrada en: {_lib_path}")

_dsp = ctypes.CDLL(_lib_path)

# Definir la firma de la función en C
# void compute_spectrum(const float* iq_in, int num_samples, int fft_size, const float* window, float window_pwr, float cal_offset, float* out_pwr)
_dsp.compute_spectrum.argtypes = [
    ctypes.POINTER(ctypes.c_float),  # iq_in (interleaved I/Q)
    ctypes.c_int,                    # num_samples
    ctypes.c_int,                    # fft_size
    ctypes.POINTER(ctypes.c_float),  # window
    ctypes.c_float,                  # window_pwr
    ctypes.c_float,                  # cal_offset
    ctypes.POINTER(ctypes.c_float)   # out_pwr
]
_dsp.compute_spectrum.restype = None

def compute_spectrum_fast(iq_complex: np.ndarray, fft_size: int, window: np.ndarray, window_pwr: float, cal_offset: float) -> np.ndarray:
    """
    Llama a la función en C para calcular el espectro en dBm.
    
    Args:
        iq_complex: Array numpy de tipo complex64.
        fft_size: Tamaño de la FFT (potencia de 2).
        window: Array numpy de tipo float32 con la ventana (ej. Blackman).
        window_pwr: Potencia de la ventana.
        cal_offset: Offset de calibración en dBm (ej. -30.0).
        
    Returns:
        Array numpy de tipo float32 con el espectro de potencia en dBm de tamaño fft_size.
    """
    num_samples = len(iq_complex)
    
    # Asegurar que los datos están contiguos y en el tipo correcto (float32, interleaved es igual a complex64 en memoria)
    iq_c64 = np.ascontiguousarray(iq_complex, dtype=np.complex64)
    win_f32 = np.ascontiguousarray(window, dtype=np.float32)
    
    # Pre-reservar el array de salida
    out_pwr = np.zeros(fft_size, dtype=np.float32)
    
    # Obtener punteros
    iq_ptr = iq_c64.ctypes.data_as(ctypes.POINTER(ctypes.c_float))
    win_ptr = win_f32.ctypes.data_as(ctypes.POINTER(ctypes.c_float))
    out_ptr = out_pwr.ctypes.data_as(ctypes.POINTER(ctypes.c_float))
    
    # Llamar a C
    _dsp.compute_spectrum(
        iq_ptr, 
        ctypes.c_int(num_samples), 
        ctypes.c_int(fft_size), 
        win_ptr, 
        ctypes.c_float(window_pwr), 
        ctypes.c_float(cal_offset), 
        out_ptr
    )
    
    return out_pwr
