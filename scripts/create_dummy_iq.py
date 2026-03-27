import numpy as np

def create_fake_iq():
    print("Generando archivo test_signal.iq simulado (2.4 MSps, 1 seg)...")
    t = np.arange(0, 1.0, 1/2.4e6)  # 1 seg de datos
    
    # 1. Tono CW fuerte en +200 kHz (simula la línea de Hidrógeno mal centrada o RFI)
    # 2. Ruido ambiente moderado
    signal = 0.6 * np.exp(1j * 2 * np.pi * 200e3 * t) 
    noise  = np.random.normal(0, 0.15, len(t)) + 1j * np.random.normal(0, 0.15, len(t))
    
    iq_complex = signal + noise
    
    # 3. Convertir a formato RTL-SDR (uint8 intercalado I,Q de 0 a 255)
    # En RTL-SDR, 0V es aprox 127.5
    iq_scaled = np.clip((iq_complex * 127.0) + 127.5, 0, 255)
    
    iq_interleaved = np.empty(len(iq_scaled) * 2, dtype=np.uint8)
    iq_interleaved[0::2] = np.real(iq_scaled).astype(np.uint8)
    iq_interleaved[1::2] = np.imag(iq_scaled).astype(np.uint8)
    
    with open("test_signal.iq", "wb") as f:
        f.write(iq_interleaved.tobytes())
        
    print(f"Archivo 'test_signal.iq' creado con {len(iq_interleaved)} bytes.")

if __name__ == "__main__":
    create_fake_iq()
