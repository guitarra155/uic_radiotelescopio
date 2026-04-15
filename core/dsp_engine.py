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

try:
    from core.bbdevice.bb_api import *
    HAS_BB_API = True
except ImportError:
    HAS_BB_API = False


class DSPEngine:
    def __init__(self):
        self.is_playing = False
        self.filename = None
        self.sample_rate = 2_400_000
        self.center_freq = 1420.40
        self.data_format = "uint8"  # RTL-SDR por defecto
        self.fft_size = 4096

        # Estado del hardware BB60C
        self.sdr_handle = -1
        self.bb60c_ref_level = -30.0
        self.bb60c_gain = BB_AUTO_GAIN
        self.bb60c_atten = BB_AUTO_ATTEN
        self.bb60c_decimation = 1  # 40 MS/s por defecto

        # Buffers circulares
        self.spectrum_data = np.zeros(self.fft_size)  # FFT sobre señal FILTRADA
        self.spectrum_raw_data = np.zeros(self.fft_size)  # FFT sobre señal RAW

        # Waterfall dinámico por tiempo
        self._waterfall_sec = 2.0
        self.waterfall_steps = int(
            self._waterfall_sec * (self.sample_rate / (self.fft_size * 40))
        )
        self.waterfall_data = np.full((self.waterfall_steps, self.fft_size), -100.0)

        # Amplitude buffer — señal RAW (sin filtrar), solo para comparación visual
        self.amplitude_data = np.zeros(2000)
        # Amplitude buffer — señal filtrada por Moving Average
        self.amplitude_ma_data = np.zeros(2000)

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
        self.algo_results: dict = {
            "ar": None,
            "cwt": None,
            "music": None,
            "esprit": None,
            "welch": None,
            "correlogram": None,
            "aslt": None,
        }
        self.algo_params: dict = {
            "ar_order": 64,
            "n_signals": 3,
            "method": "AR/Burg",
            "welch_fft": 1024,
            "welch_overlap": 0.5,
            "corr_max_lag": 512,
        }

        self.worker_thread = None
        self.playback_speed = 1.0

        import os

        # Configuraciones globales para que el Header pueda iniciar el stream
        self.stream_mode = "file"
        self.active_tab = 0
        self.current_file_time = 0.0
        self.total_file_time = 0.0
        self.iq_filename = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "test_signal.iq"
        )
        self.iq_format = "uint8"

        # Rangos de potencia espectro (AUTO-DETECTADOS)
        self.db_min = -90
        self.db_max = -50
        self.db_noise_floor = -80  # Piso de ruido detectado

        # Rangos de gráfica Potencia vs Tiempo
        self.power_db_min = -90
        self.power_db_max = -50

        # Referencias de Y para SNR vs Frecuencia
        self.snr_db_min = -5
        self.snr_db_max = 30

        # Rango de frecuencia dinámico relativo a la frecuencia central
        self.f_min = self.center_freq
        self.f_max = self.center_freq + (self.sample_rate / 2_000_000)

        # Rango de amplitud de onda pura en la grafica
        self.amp_min = 0.0
        self.amp_max = 0.3

        # ── Parámetros de adquisición y filtrado ──────────────────────────────────────
        self.analysis_window_sec = 0.5
        self.moving_avg_window_ms = 0.1  # 0.1ms = ~240 muestras, filtro suave
        self.use_welch = False

        # Contador para auto-detección de rangos
        self._frames_since_autoscale = 0
        self._autoscale_enabled = True

        # Flags de auto-escala por pestaña (GUI)
        self.auto_scale_spectrum = True
        self.auto_scale_power = True
        self.auto_scale_snr = True
        self.auto_scale_waterfall = True

    @property
    def waterfall_history_sec(self):
        return self._waterfall_sec

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
        self.power_time_data.fill(-100.0)  # limpiar buffer

        if self.worker_thread is not None and self.worker_thread.is_alive():
            return

        if mode == "file":
            self.filename = kwargs.get("filename")
            self.data_format = kwargs.get("format", "uint8")
            self.worker_thread = threading.Thread(
                target=self._process_file_loop, daemon=True
            )
        else:  # mode == 'sdr'
            self.worker_thread = threading.Thread(
                target=self._process_sdr_loop, daemon=True
            )

        self.worker_thread.start()

    def stop_stream(self):
        self.is_playing = False
        if self.sdr_handle != -1:
            try:
                bb_abort(self.sdr_handle)
                bb_close_device(self.sdr_handle)
                self.sdr_handle = -1
                print("SDR BB60C desconectado correctamente.")
            except:
                pass

    def _process_dsp_core(self, iq, batches=None):
        """Bloque matemático en común para señales reales e irreales.

        Flujo de señal:
          iq_raw ──┬──→ amplitude_data        (tab 1: amplitud original)
                   ├──→ FFT RAW → spectrum_raw_data (tab 1: espectro original)
                   └──→ MA Filter → iq_f ──┬──→ amplitude_ma_data  (tab 2)
                                        ├──→ spectrum_data     (tab 2+)
                                        ├──→ Waterfall
                                        ├──→ Histograma
                                        ├──→ Potencia vs Tiempo
                                        └──→ SNR
        """
        # ── 1. Calcular batches dinámicamente desde analysis_window_sec ─────────
        # Usar solo los batches que caben en los datos disponibles
        if batches is None:
            max_batches = len(iq) // self.fft_size
            batches = max(
                1, min(max_batches, 4)
            )  # Máximo 4 batches por llamada para tiempo real

        # ── 2. Buffer RAW: solo la magnitud del último fragmento ───────────────
        mag_raw = np.abs(iq[-self.fft_size :])
        self.amplitude_data = np.roll(self.amplitude_data, -len(mag_raw))
        self.amplitude_data[-len(mag_raw) :] = mag_raw[-len(self.amplitude_data) :]

        # ── 3. Moving Average Filter ───────────────────────────────────────
        win_len = max(1, int(self.moving_avg_window_ms * 1e-3 * self.sample_rate))
        if win_len > 1:
            kernel = np.ones(win_len, dtype=np.float64) / win_len
            # Aplicar a parte real e imaginaria por separado para preservar
            # la fase de la señal compleja
            iq_f = np.convolve(iq.real, kernel, mode="same") + 1j * np.convolve(
                iq.imag, kernel, mode="same"
            )
        else:
            iq_f = iq  # Sin filtrado si la ventana es 1 muestra

        # Buffer de amplitud filtrada
        mag_f = np.abs(iq_f[-self.fft_size :])
        self.amplitude_ma_data = np.roll(self.amplitude_ma_data, -len(mag_f))
        self.amplitude_ma_data[-len(mag_f) :] = mag_f[-len(self.amplitude_ma_data) :]

        # ── 3b. Espectro RAW (FFT sobre señal sin filtrar) → solo para Tab 1 ───
        window_raw = np.hanning(self.fft_size)
        pwr_raw_avg = np.zeros(self.fft_size)
        for b in range(batches):
            blk = iq[b * self.fft_size : (b + 1) * self.fft_size]
            if len(blk) < self.fft_size:
                break
            blk = blk - np.mean(blk)
            fft_c = np.fft.fftshift(np.fft.fft(blk * window_raw))
            pwr_raw_avg += np.abs(fft_c) ** 2 / self.fft_size
        pwr_raw = 10 * np.log10(pwr_raw_avg / max(1, batches) + 1e-12)
        alpha = 0.3
        self.spectrum_raw_data = (1 - alpha) * self.spectrum_raw_data + alpha * pwr_raw

        # ── 4. Espectro de Potencia (FFT) sobre señal FILTRADA ───────────────
        if self.use_welch:
            from core.advanced_dsp import run_welch

            welch_res = run_welch(
                iq_f,
                fft_size=self.algo_params.get("welch_fft", 1024),
                overlap=self.algo_params.get("welch_overlap", 0.5),
                sample_rate=self.sample_rate,
                center_freq=self.center_freq,
            )
            # Interpolar al tamaño de fft_size del engine si difieren
            if len(welch_res["psd"]) != self.fft_size:
                idx = np.round(
                    np.linspace(0, len(welch_res["psd"]) - 1, self.fft_size)
                ).astype(int)
                pwr = welch_res["psd"][idx]
            else:
                pwr = welch_res["psd"]
        else:
            window = np.hanning(self.fft_size)
            pwr_avg = np.zeros(self.fft_size)
            for b in range(batches):
                block_iq = iq_f[b * self.fft_size : (b + 1) * self.fft_size]
                if len(block_iq) < self.fft_size:
                    break  # Ignorar bloque incompleto al final
                block_iq = block_iq - np.mean(block_iq)  # DC removal
                fft_complex = np.fft.fftshift(np.fft.fft(block_iq * window))
                pwr_avg += np.abs(fft_complex) ** 2 / self.fft_size
            pwr = 10 * np.log10(pwr_avg / max(1, batches) + 1e-12)

        # IIR simple sobre el tiempo
        alpha = 0.3
        self.spectrum_data = (1 - alpha) * self.spectrum_data + alpha * pwr

        # ── 5. Waterfall (Espectrograma) sobre señal filtrada ───────────────
        self.waterfall_data = np.roll(self.waterfall_data, 1, axis=0)
        self.waterfall_data[0, :] = self.spectrum_data

        # ── 6. Histograma (magnitud de señal filtrada) ─────────────────────
        self.histogram_data = np.random.choice(mag_f, size=2000, replace=True)

        # ── 7. Potencia instantánea vs Tiempo ────────────────────────────
        inst_pwr_db = float(np.mean(pwr))
        # Usar índice circular simple en lugar de roll
        if self.power_samples_written < len(self.power_time_data):
            idx = self.power_samples_written
            self.power_time_data[idx] = inst_pwr_db
            self.power_samples_written += 1
        else:
            # Buffer lleno: usar indexación circular
            idx = self.power_samples_written % len(self.power_time_data)
            self.power_time_data[idx] = inst_pwr_db
            self.power_samples_written += 1

        # ── 8. SNR logarítmico por bin ─────────────────────────────────
        # Fórmula: SNR[dB] = P_señal[dBFS] - P_ruido[dBFS]
        # El piso de ruido se estima con la mediana (estimador robusto)
        noise_floor = np.median(self.spectrum_data)
        self.snr_data = self.spectrum_data - noise_floor

        # ── 9. Detectar señales de interés: bins con SNR > umbral ──────────
        SNR_THRESH = 6.0  # dB sobre el piso de ruido
        fc = self.center_freq
        fs_mhz = self.sample_rate / 1_000_000
        freqs = np.linspace(fc - fs_mhz / 2, fc + fs_mhz / 2, self.fft_size)
        hot_mask = self.snr_data > SNR_THRESH
        if np.any(hot_mask):
            hot_freqs = freqs[hot_mask]
            hot_snrs = self.snr_data[hot_mask]
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

        # ── 10. Auto-detección de rangos óptimos ───────────────────────────
        # Solo ajustar cada 30 frames para evitar fluctuaciones
        self._frames_since_autoscale += 1
        if self._frames_since_autoscale >= 30 and self._autoscale_enabled:
            self._frames_since_autoscale = 0
            self._auto_detect_ranges()

    def _auto_detect_ranges(self):
        """Auto-detecta los rangos óptimos basándose en los datos actuales.
        Calcula el piso de ruido y centra el rango para cada gráfica.
        """
        # ── 1. Espectro y Waterfall (Sincronizados) ─────────────────────────────────
        if getattr(self, "auto_scale_spectrum", True) or getattr(self, "auto_scale_waterfall", True):
            if np.any(self.spectrum_data != 0):
                # El piso de ruido es la mediana (robusto contra picos de señal)
                noise_floor = np.median(self.spectrum_data)
                self.db_noise_floor = float(noise_floor)

                # Calculamos el rango dinámico actual (pico vs ruido)
                spec_max = np.percentile(self.spectrum_data, 99)
                dynamic_range = spec_max - noise_floor

                # Centro el rango: el ruido queda en el tercio inferior,
                # dejando espacio para la señal arriba y margen abajo
                margin_below = 20 # dB debajo del ruido
                margin_above = max(10, dynamic_range * 0.2) # Margen proporcional al pico

                self.db_min = noise_floor - margin_below
                self.db_max = spec_max + margin_above

                # Si auto_scale_waterfall está activo, usa estos mismos rangos
                if getattr(self, "auto_scale_waterfall", True):
                    # Waterfall usa los mismos db_min/db_max que el espectro
                    pass

        # ── 2. Potencia vs Tiempo ──────────────────────────────────────────────────
        if getattr(self, "auto_scale_power", True):
            if self.power_samples_written > 10:
                pwr_valid = self.power_time_data[: self.power_samples_written]
                valid_pwr = pwr_valid[pwr_valid > -120]
                if len(valid_pwr) > 5:
                    pwr_median = np.median(valid_pwr)
                    pwr_max = np.max(valid_pwr)

                    # Centramos basándonos en el nivel promedio de potencia
                    range_width = pwr_max - pwr_median
                    margin = max(10, range_width * 0.3)

                    self.power_db_min = pwr_median - margin
                    self.power_db_max = pwr_max + margin

        # ── 3. SNR vs Frecuencia ────────────────────────────────────────────────────
        if getattr(self, "auto_scale_snr", True):
            if np.any(self.snr_data != 0):
                # El SNR es relativo al ruido, así que el "piso" es 0 dB
                snr_valid = self.snr_data[np.abs(self.snr_data) < 100]
                if len(snr_valid) > 100:
                    snr_max = np.percentile(snr_valid, 99)

                    # Centramos el eje Y para que el 0 (ruido) sea visible
                    # y el pico de señal esté bien encuadrado
                    self.snr_db_min = -5.0 # Margen constante bajo el ruido
                    self.snr_db_max = snr_max + 5.0

    def reset_to_defaults(self):
        """Restaura los rangos de visualización a los óptimos detectados por el sistema,
        desactivando la configuración manual (reactiva auto_scale)."""
        self.auto_scale_spectrum = True
        self.auto_scale_power = True
        self.auto_scale_snr = True
        self.auto_scale_waterfall = True

        # Forzar re-detección inmediata en el siguiente ciclo
        self._frames_since_autoscale = 30
        self.save_config()

    def _process_sdr_loop(self):
        """
        Streaming físico usando BB60C de Signal Hound.
        """
        if not HAS_BB_API:
            print("Error: API de Signal Hound no encontrada.")
            self.is_playing = False
            return

        try:
            print("Iniciando conexión con BB60C...")
            # 1. Abrir dispositivo
            res_open = bb_open_device()
            if res_open["status"] != 0:
                print(f"No se pudo abrir el BB60C: {res_open['status']}")
                self.is_playing = False
                return
            
            self.sdr_handle = res_open["handle"]
            h = self.sdr_handle

            # 2. Configurar hardware
            bb_configure_ref_level(h, self.bb60c_ref_level)
            bb_configure_gain_atten(h, self.bb60c_gain, self.bb60c_atten)
            # Frecuencia central en Hz
            bb_configure_IQ_center(h, self.center_freq * 1e6)
            
            # Ancho de banda y decimación
            # Nota: sample_rate real = 40e6 / decimation
            bw = 20.0e6 / self.bb60c_decimation
            bb_configure_IQ(h, self.bb60c_decimation, bw)
            
            # Actualizar sample_rate interno para que el DSP sea correcto
            self.sample_rate = 40_000_000 // self.bb60c_decimation

            # 3. Iniciar modo streaming
            bb_initiate(h, BB_STREAMING, BB_STREAM_IQ)
            print(f"BB60C iniciado @ {self.sample_rate/1e6} MHz bandwidth")

            samples_per_read = self.fft_size # Leer un bloque FFT por vez

            while self.is_playing:
                # 4. Capturar bloque IQ
                # purge=BB_FALSE para mantener continuidad si procesado es rápido
                res_iq = bb_get_IQ_unpacked(h, samples_per_read, BB_FALSE)
                if res_iq["status"] != 0:
                    print(f"Error de lectura IQ: {res_iq['status']}")
                    break
                
                iq = res_iq["iq"]
                
                # Procesar en el núcleo DSP
                self._process_dsp_core(iq, batches=1)

        except Exception as e:
            print(f"SDR Hardware Error: {e}")
        finally:
            self.stop_stream()

    def _process_file_loop(self):
        """Streaming virtual leyendo un fichero .iq grabado previamente"""
        try:
            with open(self.filename, "rb") as f:
                import os

                if not os.path.exists(self.filename):
                    return
                file_size = os.path.getsize(self.filename)

                bytes_per_sample = 2 if self.data_format in ("uint8", "int8") else 8
                # Leer exactamente fft_size muestras por iteración para tiempo real
                chunk_bytes = self.fft_size * bytes_per_sample

                self.current_file_time = 0.0
                self.total_file_time = (file_size / bytes_per_sample) / self.sample_rate

                import time

                start_real_time = time.time()

                while self.is_playing:
                    raw_data = f.read(chunk_bytes)
                    if not raw_data or len(raw_data) < chunk_bytes:
                        self.is_playing = False  # Termina y se apaga
                        break

                    if self.data_format == "uint8":
                        samples = np.frombuffer(raw_data, dtype=np.uint8).astype(
                            np.float32
                        )
                        samples = (samples - 127.5) / 128.0
                        # Lectura e intercalado COMPLEJO tal como lo pediste: I (pares) + j * Q (impares) -> x + yj
                        iq = samples[0::2] + 1j * samples[1::2]
                    elif self.data_format == "int8":
                        samples = np.frombuffer(raw_data, dtype=np.int8).astype(
                            np.float32
                        )
                        samples = samples / 128.0
                        # Lectura e intercalado COMPLEJO real
                        iq = samples[0::2] + 1j * samples[1::2]
                    elif self.data_format == "complex64":
                        iq = np.frombuffer(raw_data, dtype=np.complex64)
                    else:
                        break

                    # Sanitizar datos para evitar NaNs o Infs en caso de formato erróneo
                    iq = np.nan_to_num(iq, nan=0.0, posinf=1.0, neginf=-1.0)
                    self._process_dsp_core(iq, batches=1)

                    # Tiempo simulado: fft_size / sample_rate = tiempo de 1 bloque
                    block_time = self.fft_size / self.sample_rate
                    self.current_file_time += block_time

                    # Sincronización con playback_speed
                    target_time = self.current_file_time / max(0.1, self.playback_speed)
                    elapsed = time.time() - start_real_time
                    sleep_time = target_time - elapsed
                    if sleep_time > 0:
                        time.sleep(sleep_time)

        except Exception as e:
            print(f"File Stream Error: {e}")
            self.is_playing = False

    def save_config(self):
        conf = {
            "db_min": self.db_min,
            "db_max": self.db_max,
            "f_min": self.f_min,
            "f_max": self.f_max,
            "power_db_min": getattr(self, "power_db_min", -100),
            "power_db_max": getattr(self, "power_db_max", 0),
            "snr_db_min": getattr(self, "snr_db_min", -10),
            "snr_db_max": getattr(self, "snr_db_max", 40),
            "amp_min": getattr(self, "amp_min", 0.0),
            "amp_max": getattr(self, "amp_max", 1.0),
            "waterfall": self._waterfall_sec,
            "iq_filename": self.iq_filename,
            "iq_format": self.iq_format,
            "stream_mode": self.stream_mode,
            "algo_params": self.algo_params,
            "analysis_window_sec": self.analysis_window_sec,
            "moving_avg_window_ms": self.moving_avg_window_ms,
            "use_welch": self.use_welch,
            "auto_scale_spectrum": getattr(self, "auto_scale_spectrum", True),
            "auto_scale_power": getattr(self, "auto_scale_power", True),
            "auto_scale_snr": getattr(self, "auto_scale_snr", True),
            "auto_scale_waterfall": getattr(self, "auto_scale_waterfall", True),
        }
        try:
            import json, os

            with open(
                os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json"),
                "w",
            ) as f:
                json.dump(conf, f)
        except Exception as e:
            print("Save Config Error:", e)

    def load_config(self):
        try:
            import json, os

            p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
            if os.path.exists(p):
                with open(p, "r") as f:
                    conf = json.load(f)
                self.db_min = conf.get("db_min", self.db_min)
                self.db_max = conf.get("db_max", self.db_max)
                self.power_db_min = conf.get("power_db_min", self.power_db_min)
                self.power_db_max = conf.get("power_db_max", self.power_db_max)
                self.f_min = conf.get("f_min", self.f_min)
                self.f_max = conf.get("f_max", self.f_max)
                self.amp_min = conf.get("amp_min", self.amp_min)
                self.amp_max = conf.get("amp_max", self.amp_max)
                self.waterfall_history_sec = conf.get("waterfall", self._waterfall_sec)
                self.iq_filename = conf.get("iq_filename", self.iq_filename)
                self.iq_format = conf.get("iq_format", self.iq_format)
                self.stream_mode = conf.get("stream_mode", self.stream_mode)

                self.snr_db_min = conf.get("snr_db_min", self.snr_db_min)
                self.snr_db_max = conf.get("snr_db_max", self.snr_db_max)

                ap = conf.get("algo_params")
                if ap and isinstance(ap, dict):
                    self.algo_params.update(ap)

                self.analysis_window_sec = conf.get(
                    "analysis_window_sec", self.analysis_window_sec
                )
                self.moving_avg_window_ms = conf.get(
                    "moving_avg_window_ms", self.moving_avg_window_ms
                )
                self.use_welch = conf.get("use_welch", self.use_welch)

                # Auto-scale flags
                self.auto_scale_spectrum = conf.get("auto_scale_spectrum", True)
                self.auto_scale_power = conf.get("auto_scale_power", True)
                self.auto_scale_snr = conf.get("auto_scale_snr", True)
                self.auto_scale_waterfall = conf.get("auto_scale_waterfall", True)
        except Exception as e:
            print("Load Config Error:", e)


# Instancia global del DSP (Singleton pattern simple)
engine_instance = DSPEngine()
