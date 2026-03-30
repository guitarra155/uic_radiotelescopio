"""
dsp_engine.py
Motor de Procesamiento Digital de Señales (DSP) ejecutado en segundo plano.
Lee archivos .iq, calcula FFT y las mantiene en buffers circulares 
para que charts.py los renderice.
"""

import threading
import time
import numpy as np
from core.constants import *

class DSPEngine:
    def __init__(self):
        self.is_playing = False
        self.filename = None
        self.sample_rate = 2_400_000
        self.center_freq = 1420.40
        self.data_format = "uint8" # RTL-SDR por defecto
        self.fft_size = 4096
        
        # Buffers circulares
        self.spectrum_data = np.zeros(self.fft_size)
        
        # Waterfall dinámico por tiempo
        self._waterfall_sec = 2.0
        self.waterfall_steps = int(self._waterfall_sec * (self.sample_rate / (self.fft_size * 40)))
        self.waterfall_data = np.full((self.waterfall_steps, self.fft_size), -100.0)
        
        # Amplitude buffer
        self.amplitude_data = np.zeros(2000)
        
        # Histogram samples
        self.histogram_data = np.random.normal(0, 1, 1000)

        # Power vs Time buffer (dBFS instantáneo, 2000 muestras)
        self.power_time_data = np.full(2000, -100.0)
        self.power_samples_written = 0
        
        # SNR por bin de frecuencia (misma longitud que spectrum_data)
        self.snr_data = np.zeros(self.fft_size)
        
        # Señales de interés detectadas: lista de (freq_mhz, snr_db)
        self.signals_of_interest: list = []

        # Resultados de algoritmos DSP avanzados (b64 PNG strings)
        # Se pueblan desde sdr_config y se leen en las pestañas individuales
        self.algo_results: dict = {"ar": None, "cwt": None,
                                   "music": None, "esprit": None}
        self.algo_params: dict = {"ar_order": 64, "n_signals": 3,
                                  "method": "AR/Burg"}

        self.worker_thread = None
        self.playback_speed = 1.0

        import os
        # Configuraciones globales para que el Header pueda iniciar el stream
        self.stream_mode = "file"
        self.active_tab = 0
        self.current_file_time = 0.0
        self.total_file_time = 0.0
        self.iq_filename = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_signal.iq")
        self.iq_format = "uint8"
        
        # Rangos de potencia espectro (-105 a -85 dB)
        self.db_min = -105
        self.db_max = -85
        
        # Rangos de gráfica Potencia vs Tiempo
        self.power_db_min = -100
        self.power_db_max = 0
        
        # Referencias de Y para SNR vs Frecuencia
        self.snr_db_min = -10
        self.snr_db_max = 40
        # Rango de frecuencia dinámico relativo a la frecuencia central
        # Iniciamos visualmente f_min desde center_freq para ocultar el espectro imagen negativo 
        self.f_min = self.center_freq
        self.f_max = self.center_freq + (self.sample_rate / 2_000_000)
        
        # Rango de amplitud de onda pura en la grafica
        self.amp_min = 0.0
        self.amp_max = 1.0

    @property
    def waterfall_history_sec(self): return self._waterfall_sec

    @waterfall_history_sec.setter
    def waterfall_history_sec(self, val):
        self._waterfall_sec = max(0.1, val)
        batches_per_sec = self.sample_rate / (self.fft_size * 40)
        new_steps = int(self._waterfall_sec * batches_per_sec)
        new_steps = max(10, new_steps)
        if new_steps != self.waterfall_steps:
            self.waterfall_steps = new_steps
            # Reset the array size
            self.waterfall_data = np.zeros((self.waterfall_steps, self.fft_size))

    def start_stream(self, mode: str, kwargs: dict):
        """
        Inicia el streaming. mode = 'file' o 'sdr'
        kwargs puede contener 'filename', 'format' o ajustes propios del SDR
        """
        self.is_playing = True
        self.power_samples_written = 0  # reiniciar el contador al empezar
        self.power_time_data.fill(-100.0) # limpiar buffer
        
        if self.worker_thread is not None and self.worker_thread.is_alive():
            return
            
        if mode == 'file':
            self.filename = kwargs.get('filename')
            self.data_format = kwargs.get('format', 'uint8')
            self.worker_thread = threading.Thread(target=self._process_file_loop, daemon=True)
        else: # mode == 'sdr'
            self.worker_thread = threading.Thread(target=self._process_sdr_loop, daemon=True)
            
        self.worker_thread.start()

    def stop_stream(self):
        self.is_playing = False

    def _process_dsp_core(self, iq, batches=40):
        """Bloque matemático en común para señales reales e irreales"""
        # 1. Amplitud pura (Magnitud del último fragmento)
        mag = np.abs(iq[-4096:])
        self.amplitude_data = np.roll(self.amplitude_data, -len(mag))
        self.amplitude_data[-len(mag):] = mag[-len(self.amplitude_data):]
        
        # 2. Espectro de Potencia (FFT) Promediado
        window = np.hanning(self.fft_size)
        pwr_avg = np.zeros(self.fft_size)
        
        for b in range(batches):
            block_iq = iq[b*self.fft_size : (b+1)*self.fft_size]
            
            # Eliminar la componente DC (VCO / Oscilador Local colándose) restando la media
            block_iq = block_iq - np.mean(block_iq)
            
            fft_complex = np.fft.fftshift(np.fft.fft(block_iq * window))
            pwr_avg += np.abs(fft_complex)**2 / self.fft_size
            
        pwr = 10 * np.log10(pwr_avg / batches + 1e-12)
        
        # IIR simple sobre el tiempo
        alpha = 0.3
        self.spectrum_data = (1 - alpha) * self.spectrum_data + alpha * pwr
        
        # 3. Waterfall (Espectrograma) - Nueva data al fondo, viejo sube
        self.waterfall_data = np.roll(self.waterfall_data, 1, axis=0)
        self.waterfall_data[0, :] = self.spectrum_data
        
        # 4. Histograma
        self.histogram_data = np.random.choice(mag, size=2000, replace=True)
        
        # 5. Potencia instantánea vs Tiempo (dBFS promedio de este batch)
        inst_pwr_db = float(np.mean(pwr))
        self.power_time_data = np.roll(self.power_time_data, -1)
        self.power_time_data[-1] = inst_pwr_db
        if self.power_samples_written < len(self.power_time_data):
            self.power_samples_written += 1
        
        # 6. SNR estimado por bin: potencia - piso de ruido local (mediana como estimador)
        noise_floor = np.median(self.spectrum_data)
        self.snr_data = self.spectrum_data - noise_floor
        
        # 7. Detectar señales de interés: bins con SNR > umbral_snr dB
        SNR_THRESH = 6.0  # dB sobre el piso de ruido
        fc = self.center_freq
        fs_mhz = self.sample_rate / 1_000_000
        freqs = np.linspace(fc - fs_mhz/2, fc + fs_mhz/2, self.fft_size)
        hot_mask = self.snr_data > SNR_THRESH
        if np.any(hot_mask):
            hot_freqs = freqs[hot_mask]
            hot_snrs  = self.snr_data[hot_mask]
            # Agrupar picos cercanos: tomar el pico de cada cluster
            clusters = []
            prev_f = None
            best_f = best_s = None
            for f, s in sorted(zip(hot_freqs, hot_snrs), key=lambda x: x[0]):
                if prev_f is None or f - prev_f > 0.01:  # 10 kHz gap mínimo
                    if best_f is not None:
                        clusters.append((float(best_f), float(best_s)))
                    best_f, best_s = f, s
                else:
                    if s > best_s:
                        best_f, best_s = f, s
                prev_f = f
            if best_f is not None:
                clusters.append((float(best_f), float(best_s)))
            self.signals_of_interest = clusters[:20]  # máximo 20
        else:
            self.signals_of_interest = []


    def _process_sdr_loop(self):
        """
        Streaming físico usando PyRTLSDR (o un dummy si el hardware no está conectado).
        """
        try:
            # Aquí iría: from rtlsdr import RtlSdr
            # sdr = RtlSdr()
            # sdr.sample_rate = self.sample_rate
            # sdr.center_freq = self.center_freq * 1e6
            
            batches = 40
            samples_to_read = self.fft_size * batches
            
            while self.is_playing:
                # Simulación temporal de la lectura del SDR de Hardware si libreria falla:
                # iq_samples = sdr.read_samples(samples_to_read)
                
                # Para la maqueta, simulamos el SDR leyendo ruido estático en vivo
                iq = np.random.normal(0, 0.1, samples_to_read) + 1j * np.random.normal(0, 0.1, samples_to_read)
                
                self._process_dsp_core(iq, batches)
                
                # El hardware dicta el ritmo. El sdr.read_samples() es una operación BLOQUEANTE, 
                # así que físicamente ya te entrega exacto los cuadros de tiempo real. 
                # Por consistencia térmica del dummy, ponemos un sleep idéntico al hardware:
                hardware_delay = samples_to_read / self.sample_rate
                time.sleep(hardware_delay)
                
        except Exception as e:
            print(f"SDR Hardware Error: {e}")
            self.is_playing = False


    def _process_file_loop(self):
        """Streaming virtual leyendo un fichero .iq grabado previamente"""
        try:
            with open(self.filename, 'rb') as f:
                import os
                if not os.path.exists(self.filename): return
                file_size = os.path.getsize(self.filename)
                
                bytes_per_sample = 2 if self.data_format in ('uint8', 'int8') else 8 
                batches = 40 
                chunk_bytes = self.fft_size * bytes_per_sample * batches
                base_sleep_time = (self.fft_size * batches) / self.sample_rate
                
                self.current_file_time = 0.0
                self.total_file_time = (file_size / bytes_per_sample) / self.sample_rate
                
                import time
                start_real_time = time.time()
                
                while self.is_playing:
                    raw_data = f.read(chunk_bytes)
                    if not raw_data or len(raw_data) < chunk_bytes:
                        self.is_playing = False # Termina y se apaga
                        break
                    
                    if self.data_format == "uint8":
                        samples = np.frombuffer(raw_data, dtype=np.uint8).astype(np.float32)
                        samples = (samples - 127.5) / 128.0
                        # Lectura e intercalado COMPLEJO tal como lo pediste: I (pares) + j * Q (impares) -> x + yj
                        iq = samples[0::2] + 1j * samples[1::2]
                    elif self.data_format == "int8":
                        samples = np.frombuffer(raw_data, dtype=np.int8).astype(np.float32)
                        samples = samples / 128.0
                        # Lectura e intercalado COMPLEJO real
                        iq = samples[0::2] + 1j * samples[1::2]
                    elif self.data_format == "complex64":
                        iq = np.frombuffer(raw_data, dtype=np.complex64)
                    else:
                        break 
                        
                    # Sanitizar datos para evitar NaNs o Infs en caso de formato erróneo
                    iq = np.nan_to_num(iq, nan=0.0, posinf=1.0, neginf=-1.0)
                    self._process_dsp_core(iq, batches)

                    self.current_file_time += (len(raw_data) / bytes_per_sample) / self.sample_rate
                    
                    # Sincronización perfecta con el reloj del sistema operativo (Real-Time real)
                    target_elapsed = self.current_file_time / max(0.1, self.playback_speed)
                    actual_elapsed = time.time() - start_real_time
                    
                    sleep_time = target_elapsed - actual_elapsed
                    if sleep_time > 0:
                        time.sleep(sleep_time)

        except Exception as e:
            print(f"File Stream Error: {e}")
            self.is_playing = False


    def save_config(self):
        conf = {
            'db_min': self.db_min, 'db_max': self.db_max,
            'f_min': self.f_min, 'f_max': self.f_max,
            'power_db_min': getattr(self, 'power_db_min', -100),
            'power_db_max': getattr(self, 'power_db_max', 0),
            'snr_db_min': getattr(self, 'snr_db_min', -10),
            'snr_db_max': getattr(self, 'snr_db_max', 40),
            'amp_min': getattr(self, 'amp_min', 0.0), 'amp_max': getattr(self, 'amp_max', 1.0),
            'waterfall': self._waterfall_sec,
            'iq_filename': self.iq_filename, 'iq_format': self.iq_format,
            'stream_mode': self.stream_mode,
            'algo_params': self.algo_params
        }
        try:
            import json, os
            with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json'), 'w') as f:
                json.dump(conf, f)
        except Exception as e: print("Save Config Error:", e)

    def load_config(self):
        try:
            import json, os
            p = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')
            if os.path.exists(p):
                with open(p, 'r') as f:
                    conf = json.load(f)
                self.db_min = conf.get('db_min', self.db_min)
                self.db_max = conf.get('db_max', self.db_max)
                self.power_db_min = conf.get('power_db_min', self.power_db_min)
                self.power_db_max = conf.get('power_db_max', self.power_db_max)
                self.f_min = conf.get('f_min', self.f_min)
                self.f_max = conf.get('f_max', self.f_max)
                self.amp_min = conf.get('amp_min', self.amp_min)
                self.amp_max = conf.get('amp_max', self.amp_max)
                self.waterfall_history_sec = conf.get('waterfall', self._waterfall_sec)
                self.iq_filename = conf.get('iq_filename', self.iq_filename)
                self.iq_format = conf.get('iq_format', self.iq_format)
                self.stream_mode = conf.get('stream_mode', self.stream_mode)
                
                self.snr_db_min = conf.get('snr_db_min', self.snr_db_min)
                self.snr_db_max = conf.get('snr_db_max', self.snr_db_max)
                
                ap = conf.get('algo_params')
                if ap and isinstance(ap, dict):
                    self.algo_params.update(ap)
        except Exception as e: print("Load Config Error:", e)

# Instancia global del DSP (Singleton pattern simple)
engine_instance = DSPEngine()

