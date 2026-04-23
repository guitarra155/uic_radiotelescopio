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
        self.bb60c_iq_bw = 20.0    # Ancho de banda digital (MHz)
        self.vbw_alpha = 0.3       # Factor de suavizado (0.1 a 1.0)
        self.ma_enabled = True      # Interruptor del filtro Moving Average
        self.raw_mode = False       # Modo 100% RAW (sin suavizado VBW)
        
        # 🔗 Sincronización (Modo Espejo)
        self.sync_active = False
        self._pre_sync_state = {}
        self.sdr_overflow = False   # Indica si hay saturación ADC
        self.elapsed_samples = 0    # Contador global para eje de tiempo absoluto

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

        # 🛸 Estado RFI (Interferencias)
        self.rfi_mitigation_on = False
        self.rfi_event_count = 0
        self.rfi_last_time = "--:--:--"
        self._rfi_cooldown = 0 # Evitar contar el mismo evento mil veces

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
        span = self.sample_rate / 2_000_000
        self.f_min = self.center_freq - span
        self.f_max = self.center_freq + span

        # Rango de amplitud de onda pura en la grafica
        self.amp_min = 0.0
        self.amp_max = 0.3

        # ── Parámetros de adquisición y filtrado ──────────────────────────────────────
        self.analysis_window_sec = 0.5
        self.moving_avg_window_ms = 0.1  # 0.1ms = ~240 muestras, filtro suave
        self.use_welch = True           # Iniciar con Welch (el modo 'bonito' / smooth)
        self.visual_span_mhz = 2.4      # Span visual por defecto (MHz)

        # Flags de auto-escala globales (compatibilidad parcial)
        self.auto_scale_spectrum = True
        self.auto_scale_power = True
        self.auto_scale_snr = True
        self.auto_scale_waterfall = True

        # Contador para auto-detección de rangos
        self._frames_since_autoscale = 0
        self._autoscale_enabled = True

        # NUEVO: Configuración granular por gráfica
        # Estructura: xmin, xmax, ymin, ymax, auto_x, auto_y
        self.charts_config = {
            "mon_raw_spec": {"xmin": 1419.0, "xmax": 1421.0, "ymin": -100.0, "ymax": -20.0, "auto_x": True, "auto_y": True},
            "mon_raw_amp":  {"xmin": 0.0, "xmax": 1.0, "ymin": 0.0, "ymax": 1.0, "auto_x": True, "auto_y": True},
            "mon_filt_spec": {"xmin": 1419.0, "xmax": 1421.0, "ymin": -100.0, "ymax": -20.0, "auto_x": True, "auto_y": True},
            "mon_filt_amp": {"xmin": 0.0, "xmax": 1.0, "ymin": 0.0, "ymax": 1.0, "auto_x": True, "auto_y": True},
            "spec_wf":      {"xmin": 1419.0, "xmax": 1421.0, "ymin": -100.0, "ymax": -20.0, "auto_x": True, "auto_y": True},
            "stat_hist":    {"xmin": 0.0, "xmax": 1.5, "ymin": 0.0, "ymax": 100.0, "auto_x": True, "auto_y": True},
            "pow_time":     {"xmin": 0.0, "xmax": 20.0, "ymin": -100.0, "ymax": -20.0, "auto_x": False, "auto_y": True},
            "snr_freq":     {"xmin": 1419.0, "xmax": 1421.0, "ymin": -5.0, "ymax": 40.0, "auto_x": True, "auto_y": True},
        }

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
                1, min(max_batches, 100) 
            ) # Permitir promediar ráfagas grandes (ej. 40 bloques)

        # Actualizar contador de tiempo global
        self.elapsed_samples += len(iq)

        # ── 2. Buffer RAW: solo la magnitud del último fragmento ───────────────
        mag_raw = np.abs(iq[-self.fft_size :])
        self.amplitude_data = np.roll(self.amplitude_data, -len(mag_raw))
        self.amplitude_data[-len(mag_raw) :] = mag_raw[-len(self.amplitude_data) :]

        # ── 3. Moving Average Filter (IMPLEMENTACIÓN ULTRA-RÁPIDA) ────────
        win_len = max(1, int(self.moving_avg_window_ms * 1e-3 * self.sample_rate))
        
        if self.ma_enabled and win_len > 1:
            # Optimizamos usando Suma Acumulada para que sea O(N) independientemente de la ventana
            # Esto es lo mismo que np.convolve pero instantáneo.
            def fast_ma(x, w):
                # Padding para mantener modo "same"
                pad = w // 2
                x_padded = np.pad(x, (pad, pad), mode='edge')
                cs = np.cumsum(x_padded, dtype=np.float64)
                res = (cs[w:] - cs[:-w]) / w
                return res[:len(x)]

            iq_f = fast_ma(iq.real, win_len) + 1j * fast_ma(iq.imag, win_len)
        else:
            iq_f = iq  # Sin filtrado

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
            pwr_raw_avg += np.abs(fft_c) ** 2
        pwr_raw = 10 * np.log10(pwr_raw_avg / (max(1, batches) * np.sum(window_raw**2)) + 1e-12)
        # 🛸 Alpha efectivo: 1.0 en modo RAW (sin suavizado)
        alpha_eff = 1.0 if self.raw_mode else self.vbw_alpha
        
        self.spectrum_raw_data = (1 - alpha_eff) * self.spectrum_raw_data + alpha_eff * pwr_raw

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
            win_pwr = np.sum(window**2)
            pwr_avg = np.zeros(self.fft_size)
            for b in range(batches):
                block_iq = iq_f[b * self.fft_size : (b + 1) * self.fft_size]
                if len(block_iq) < self.fft_size:
                    break
                block_iq = block_iq - np.mean(block_iq)
                fft_complex = np.fft.fftshift(np.fft.fft(block_iq * window))
                pwr_avg += np.abs(fft_complex) ** 2
            pwr = 10 * np.log10(pwr_avg / (max(1, batches) * win_pwr) + 1e-12)

        # IIR simple sobre el tiempo (suavizado VBW)
        self.spectrum_data = (1 - alpha_eff) * self.spectrum_data + alpha_eff * pwr

        # ── 5. Waterfall (Espectrograma) sobre señal filtrada ───────────────
        # Cada llamada a _process_dsp_core ahora representa una ráfaga (aprox 34ms)
        # por lo que añadimos una línea directamente para mantener el cronómetro real.
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
        
        # 🛸 Lógica RFI: Si una señal es MUY fuerte (>15dB), es interferencia
        if self.rfi_mitigation_on:
            rfi_mask = self.snr_data > 15.0
            if np.any(rfi_mask) and self._rfi_cooldown == 0:
                self.rfi_event_count += 1
                from datetime import datetime
                self.rfi_last_time = datetime.now().strftime("%H:%M:%S") + " UTC"
                self._rfi_cooldown = 30 # Bloquear detección por ~1 segundo (30 frames)
            
            if self._rfi_cooldown > 0:
                self._rfi_cooldown -= 1

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
        """Auto-detecta los rangos óptimos basándose en los datos actuales."""
        if not self.is_playing:
            return

        # --- 1. Calcular indicadores clave ---
        noise_floor = np.median(self.spectrum_data)
        self.db_noise_floor = float(noise_floor)
        peak_idx = np.argmax(self.spectrum_data)
        fs_mhz = self.sample_rate / 1e6
        peak_freq = self.center_freq + (peak_idx / self.fft_size - 0.5) * fs_mhz

        # --- 2. Aplicar lógica a cada gráfica configurada ---
        
        # 2.1 Especros (RAW y Filtered) y Waterfall
        for spec_id in ["mon_raw_spec", "mon_filt_spec", "spec_wf"]:
            cfg = self.charts_config.get(spec_id)
            if not cfg: continue
            
            # Eje Y: Centrado en nivel de referencia con margen generoso
            if cfg["auto_y"]:
                spec_max = np.percentile(self.spectrum_data, 99.8)
                cfg["ymin"] = noise_floor - 30.0
                cfg["ymax"] = spec_max + 20.0
                
            # Eje X: Centrado en la frecuencia central con el ancho de banda real
            if cfg["auto_x"]:
                span = self.sample_rate / 2_000_000 # MHz
                cfg["xmin"] = self.center_freq - span
                cfg["xmax"] = self.center_freq + span
                
            # Evitar rangos absurdos (como los 100MHz vistos en el screenshot)
            if (cfg["xmax"] - cfg["xmin"]) > 50.0:
                cfg["xmin"] = self.center_freq - 1.2
                cfg["xmax"] = self.center_freq + 1.2

        # 2.2 Amplitud (Time Domain)
        for amp_id in ["mon_raw_amp", "mon_filt_amp"]:
            cfg = self.charts_config.get(amp_id)
            if cfg:
                if cfg["auto_y"]:
                    data = self.amplitude_ma_data if "filt" in amp_id else self.amplitude_data
                    mag_max = np.percentile(data, 99)
                    cfg["ymin"] = 0.0
                    cfg["ymax"] = max(0.1, float(mag_max * 1.5))
                    if cfg["ymax"] <= cfg["ymin"] + 0.001:
                        cfg["ymax"] = cfg["ymin"] + 1.0
                if cfg["auto_x"]:
                    duration_ms = (len(self.amplitude_data) / self.sample_rate) * 1000
                    cfg["xmin"] = 0
                    cfg["xmax"] = max(0.1, float(duration_ms))

        # 2.3 Potencia vs Tiempo
        cfg = self.charts_config.get("pow_time")
        if cfg and cfg["auto_y"]:
            # Solo usar los datos que ya han sido escritos para no promediar el vacío (-100)
            written = self.power_samples_written
            d_len = len(self.power_time_data)
            p_subset = self.power_time_data[:written] if written < d_len else self.power_time_data
            
            pwr_valid = p_subset[p_subset > -110] # Ignorar valores de inicialización
            if len(pwr_valid) > 5:
                p_max = np.percentile(pwr_valid, 98)
                p_min = np.percentile(pwr_valid, 2)
                cfg["ymin"] = float(p_min - 5)
                cfg["ymax"] = float(p_max + 10)
            
            # Garantizar que no sean idénticos
            if cfg["ymax"] <= cfg["ymin"] + 0.1:
                cfg["ymax"] = cfg["ymin"] + 10.0

        # 2.4 SNR vs Frecuencia
        cfg = self.charts_config.get("snr_freq")
        if cfg:
            if cfg["auto_y"]:
                snr_max = np.percentile(self.snr_data, 99)
                cfg["ymin"] = -5
                cfg["ymax"] = snr_max + 10
            if cfg["auto_x"]:
                cfg["xmin"] = peak_freq - 1.0
                cfg["xmax"] = peak_freq + 1.0

        # 2.5 Histograma
        cfg = self.charts_config.get("stat_hist")
        if cfg and cfg["auto_x"]:
            cfg["xmin"] = 0
            cfg["xmax"] = np.percentile(self.histogram_data, 99) * 1.2

    def reset_to_defaults(self):
        """Restaura los rangos de visualización a los óptimos detectados por el sistema."""
        for cfg in self.charts_config.values():
            cfg["auto_x"] = True
            cfg["auto_y"] = True

        # Forzar re-detección inmediata
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

            # Límites de seguridad para evitar errores de hardware (Clamping)
            ref_safe = max(-100.0, min(20.0, float(self.bb60c_ref_level)))
            bw_safe  = max(0.1, min(40.0, float(self.bb60c_iq_bw)))
            
            bb_configure_ref_level(h, ref_safe)
            bb_configure_gain_atten(h, self.bb60c_gain, self.bb60c_atten)
            # Frecuencia central en Hz
            bb_configure_IQ_center(h, self.center_freq * 1e6)
            
            # Ancho de banda y decimación
            bb_configure_IQ(h, self.bb60c_decimation, bw_safe * 1e6)
            
            # Actualizar sample_rate interno para que el DSP sea correcto
            self.sample_rate = 40_000_000 // self.bb60c_decimation

            # 3. Iniciar modo streaming
            bb_initiate(h, BB_STREAMING, BB_STREAM_IQ)
            print(f"BB60C iniciado @ {self.sample_rate/1e6} MHz bandwidth")

            # Leer ráfagas de 40 bloques para optimizar CPU y fluidez
            samples_per_read = self.fft_size * 40 

            while self.is_playing:
                # 4. Capturar bloque IQ
                # purge=BB_FALSE para mantener continuidad si procesado es rápido
                res_iq = bb_get_IQ_unpacked(h, samples_per_read, BB_FALSE)
                self.sdr_overflow = (res_iq["status"] == 2) # ADC Overflow Detection

                if res_iq["status"] < 0:
                    print(f"Error de lectura IQ: {res_iq['status']}")
                    break
                
                iq = res_iq["iq"]
                
                # Procesar en el núcleo DSP
                self._process_dsp_core(iq, batches=1)
                self.elapsed_samples += len(iq)

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
                # Leer ráfagas de 40 bloques por iteración para tiempo real
                chunk_bytes = self.fft_size * 40 * bytes_per_sample

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

                    # Tiempo simulado: 40 bloques por cada iteración
                    block_time = (self.fft_size * 40) / self.sample_rate
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

    def update_visual_span(self, span_mhz: float):
        """Ajusta el zoom visual de las gráficas de espectro."""
        self.visual_span_mhz = max(0.001, min(100.0, float(span_mhz)))
        
        half_span = self.visual_span_mhz / 2.0
        new_xmin = self.center_freq - half_span
        new_xmax = self.center_freq + half_span
        
        for spec_id in ["mon_raw_spec", "mon_filt_spec"]:
            if spec_id in self.charts_config:
                self.charts_config[spec_id].update({
                    "xmin": new_xmin,
                    "xmax": new_xmax,
                    "auto_x": False # Desactivar auto-x para respetar el zoom manual
                })
        self.save_config()

    def apply_sync_mode(self, active: bool):
        """Alterna el modo espejo donde la Pestaña 2 imita a la Pestaña 1."""
        self.sync_active = active
        if active:
            # 1. Guardar estado actual
            self._pre_sync_state = {
                "ma_enabled": self.ma_enabled,
                "use_welch": self.use_welch,
                "raw_mode": self.raw_mode,
                "filt_spec": self.charts_config["mon_filt_spec"].copy(),
                "filt_amp": self.charts_config["mon_filt_amp"].copy()
            }
            # 2. Forzar modo RAW total
            self.ma_enabled = False
            self.use_welch = False
            self.raw_mode = True
            
            # 3. Clonar ejes de Pestaña 1 a Pestaña 2
            self.charts_config["mon_filt_spec"].update({
                "xmin": self.charts_config["mon_raw_spec"]["xmin"],
                "xmax": self.charts_config["mon_raw_spec"]["xmax"],
                "ymin": self.charts_config["mon_raw_spec"]["ymin"],
                "ymax": self.charts_config["mon_raw_spec"]["ymax"],
                "auto_x": self.charts_config["mon_raw_spec"]["auto_x"],
                "auto_y": self.charts_config["mon_raw_spec"]["auto_y"],
            })
            self.charts_config["mon_filt_amp"].update({
                "xmin": self.charts_config["mon_raw_amp"]["xmin"],
                "xmax": self.charts_config["mon_raw_amp"]["xmax"],
                "ymin": self.charts_config["mon_raw_amp"]["ymin"],
                "ymax": self.charts_config["mon_raw_amp"]["ymax"],
                "auto_x": self.charts_config["mon_raw_amp"]["auto_x"],
                "auto_y": self.charts_config["mon_raw_amp"]["auto_y"],
            })
        else:
            # Restaurar estado previo
            if self._pre_sync_state:
                self.ma_enabled = self._pre_sync_state["ma_enabled"]
                self.use_welch = self._pre_sync_state["use_welch"]
                self.raw_mode = self._pre_sync_state["raw_mode"]
                self.charts_config["mon_filt_spec"].update(self._pre_sync_state["filt_spec"])
                self.charts_config["mon_filt_amp"].update(self._pre_sync_state["filt_amp"])

        self.save_config()

    def _sanitize(self, obj):
        """Convierte tipos de NumPy a tipos nativos recursivamente para JSON."""
        if isinstance(obj, dict):
            return {str(k): self._sanitize(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple, np.ndarray)):
            return [self._sanitize(v) for v in obj]
        elif isinstance(obj, (np.generic, np.ndarray)):
            return obj.item() if hasattr(obj, 'item') else obj.tolist()
        elif isinstance(obj, (float, np.float32, np.float64)):
            return float(obj)
        elif isinstance(obj, (int, np.int32, np.int64)):
            return int(obj)
        return obj

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
            "bb60c_ref_level": self.bb60c_ref_level,
            "bb60c_iq_bw": self.bb60c_iq_bw,
            "vbw_alpha": self.vbw_alpha,
            "ma_enabled": self.ma_enabled,
            "raw_mode": self.raw_mode,
            "use_welch": self.use_welch,
            "charts_config": self.charts_config,
        }
        try:
            import json, os
            sanitized = self._sanitize(conf)

            with open(
                os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json"),
                "w",
            ) as f:
                json.dump(sanitized, f, indent=4)
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

                # Cargar configuración granular si existe
                cc = conf.get("charts_config")
                if cc and isinstance(cc, dict):
                    # Actualizar con cuidado para no perder keys nuevas si el config es viejo
                    for k, v in cc.items():
                        if k in self.charts_config:
                            self.charts_config[k].update(v)
        except Exception as e:
            print("Load Config Error:", e)


# Instancia global del DSP (Singleton pattern simple)
engine_instance = DSPEngine()
