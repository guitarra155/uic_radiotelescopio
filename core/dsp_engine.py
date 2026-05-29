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
        self._center_freq = 1420.40
        self._sample_rate = 2_400_000
        self.data_format = "int16"
        self.fft_size = 4096
        
        # Parámetros básicos (Definir antes de cualquier setter)
        self.db_min = -100.0
        self.db_max = 0.0
        self.f_min = 1420.0
        self.f_max = 1421.0
        self.window_width = 1280
        self.window_height = 720
        self.is_config_collapsed = False
        
        # Opciones de Ventana y Visualización
        self.window_res = "Auto-Detect (Pantalla Actual)"
        self.window_mode = "Normal"
        self.trigger_high = 15.0
        self.trigger_low = 5.0
        self.iq_filename = ""
        self.iq_format = "int16"
        self.algo_params = {}
        self.moving_avg_samples = 240
        self._analysis_window_sec = 1.0
        self._waterfall_sec = 10.0
        self.use_welch = False
        
        # Estado del hardware BB60C
        self.sdr_handle = -1
        self._hw_lock = threading.Lock()
        self.stream_mode = "sdr"
        self.bb60c_decimation = 1
        
        self._initializing = True
        # Asignar directamente sin pasar por el setter (evita prints en arranque)
        # load_config() restaurará los valores reales guardados
        self._sample_rate = 40_000_000
        self.bb60c_decimation = 1
        self.chart_line_width = 1.0
        self._initializing = False
        
        self.window_raw = np.hanning(self.fft_size)
        self.window_raw_pwr = np.sum(self.window_raw**2)

        self.bb60c_ref_level = -30.0
        self.bb60c_gain = BB_AUTO_GAIN
        self.bb60c_atten = BB_AUTO_ATTEN
        self.bb60c_iq_bw = 20.0    # Ancho de banda digital (MHz)
        self.vbw_alpha = 0.3       # Factor de suavizado (0.1 a 1.0)
        self.ma_enabled = True      # Interruptor del filtro Moving Average
        self.raw_mode = False       # Modo 100% RAW (sin suavizado VBW)
        
        # 🔗 Sincronización (Modo Espejo)
        self.sync_active = False
        self._pre_sync_state = {}
        self.sdr_overflow = False   # Indica si hay saturación ADC
        self.metadata_updated = False # Flag para avisar a la UI que refresque campos
        self.elapsed_samples = 0    # Contador global para eje de tiempo absoluto
        self.waterfall_idx = 0      # Índice circular para evitar O(N) roll
        self.data_ready = False     # Flag para notificar a la UI que un bloque de 1s está listo
        self._initializing = False  # Bandera para evitar guardados accidentales
        
        # Por defecto, los switches de auto-escala inician activados
        if hasattr(self, "charts_config"):
            for k in self.charts_config:
                self.charts_config[k]["auto_x"] = True
                self.charts_config[k]["auto_y"] = True
        self.spectrum_data = np.zeros(self.fft_size)  # FFT sobre señal FILTRADA
        self.spectrum_raw_data = np.zeros(self.fft_size)  # FFT sobre señal RAW

        # Waterfall dinámico por tiempo
        self._analysis_window_sec = 1.0
        self._waterfall_sec = 10.0
        self.waterfall_steps = int(
            self._waterfall_sec / self._analysis_window_sec
        )
        self.waterfall_data = np.full((self.waterfall_steps, self.fft_size), -100.0)

        self.amplitude_data = np.zeros(2000, dtype=np.complex64)
        # Amplitude buffer — señal filtrada por Moving Average
        self.amplitude_ma_data = np.zeros(2000, dtype=np.complex64)

        # Buffer IQ de alta resolución para el Correlograma 2D
        # Se vincula al 'Historial Cascada' (waterfall_history_sec)
        self._corr_buf_size  = max(50_000, int(self._sample_rate * self._waterfall_sec))
        self.corr_iq_buffer  = np.zeros(self._corr_buf_size, dtype=np.complex64)
        self._corr_buf_idx   = 0            # próximo índice de escritura
        self._corr_buf_full  = False        # True una vez que el buffer ha sido llenado al menos una vez

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
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "test_signal.iq"
        )
        self.iq_format = "int16"

        # Rangos de potencia espectro (AUTO-DETECTADOS)
        self.db_min = -90
        self.db_max = -50
        self.db_noise_floor = -80  # Piso de ruido detectado (filtrado)
        self.db_noise_floor_raw = -80 # Piso de ruido detectado (RAW)

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
        self.moving_avg_samples = 240   # Filtro suave directo en cantidad de muestras
        self.use_welch = False          # Desactivado para garantizar comparación 1:1 con la Pestaña 1
        self.visual_span_mhz = 2.4      # Span visual por defecto (MHz)

        # Flags de auto-escala globales (compatibilidad parcial)
        self.auto_scale_spectrum = True
        self.auto_scale_power = True
        self.auto_scale_snr = True
        self.auto_scale_waterfall = True

        # Contador para auto-detección de rangos
        self._frames_since_autoscale = 0
        self._autoscale_enabled = True
        self._needs_spectral_lock = False  # Flag para auto-calibración al cargar archivos
        self._file_initialized = False     # Evita bucles de detección al cargar metadatos

        # NUEVO: Configuración granular por gráfica
        # Estructura: xmin, xmax, ymin, ymax, auto_x, auto_y
        self.charts_config = {
            "mon_raw_spec": {"xmin": 1419.0, "xmax": 1421.0, "ymin": -100.0, "ymax": -20.0, "auto_x": True, "auto_y": True},
            "mon_raw_amp":  {"xmin": 0.0, "xmax": 1.0, "ymin": 0.0, "ymax": 1.0, "auto_x": True, "auto_y": True},
            "mon_filt_spec": {"xmin": 1419.0, "xmax": 1421.0, "ymin": -100.0, "ymax": -20.0, "auto_x": True, "auto_y": True},
            "mon_filt_amp": {"xmin": 0.0, "xmax": 1.0, "ymin": 0.0, "ymax": 1.0, "auto_x": True, "auto_y": True},
            "spec_wf":      {"xmin": 1419.0, "xmax": 1421.0, "ymin": -100.0, "ymax": -20.0, "auto_x": True, "auto_y": True},
            "spec_cwt":     {"xmin": 1419.0, "xmax": 1421.0, "ymin": -100.0, "ymax": -20.0, "auto_x": True, "auto_y": True},
            "spec_ar":      {"xmin": 1419.0, "xmax": 1421.0, "ymin": -100.0, "ymax": -20.0, "auto_x": True, "auto_y": True},
            "spec_corr":    {"xmin": 1419.0, "xmax": 1421.0, "ymin": -100.0, "ymax": -20.0, "auto_x": True, "auto_y": True},
            "stat_hist":    {"xmin": 0.0, "xmax": 1.5, "ymin": 0.0, "ymax": 100.0, "auto_x": True, "auto_y": True},
            "pow_time":     {"xmin": 0.0, "xmax": 20.0, "ymin": -100.0, "ymax": -20.0, "auto_x": True, "auto_y": True},
            "snr_freq":     {"xmin": 1419.0, "xmax": 1421.0, "ymin": -5.0, "ymax": 40.0, "auto_x": True, "auto_y": True},
        }

        # ── Variables para Smart Trigger / Recorte Automático ──
        import collections
        self.trigger_active = False
        self.trigger_high = 15.0
        self.trigger_low = 5.0
        self.trigger_state = 0
        self.trigger_ring_buffer = collections.deque()

    @property
    def center_freq(self):
        return getattr(self, "_center_freq", 1420.40)

    @center_freq.setter
    def center_freq(self, val):
        val = float(val)
        # Solo actuar si el valor realmente cambió
        if abs(val - self._center_freq) < 0.0001:
            return
        delta = val - self._center_freq
        self._center_freq = val
        if self.stream_mode == "sdr":
            self._retune_requested = True
        
        # Desplazar los límites X de las gráficas de frecuencia si están en modo manual
        if hasattr(self, "charts_config"):
            for chart_id in ["mon_raw_spec", "mon_filt_spec", "spec_wf", "spec_cwt", "spec_ar", "spec_corr", "snr_freq"]:
                cfg = self.charts_config.get(chart_id)
                if cfg and not cfg.get("auto_x", False):
                    cfg["xmin"] += delta
                    cfg["xmax"] += delta
        self.save_config()

    @property
    def sample_rate(self):
        return getattr(self, "_sample_rate", 40_000_000)

    @sample_rate.setter
    def sample_rate(self, val):
        val = float(val)
        # Calcular el valor nativo BB60C
        ideal_decimation = 40_000_000 / val
        if ideal_decimation < 1.5: pow2 = 0
        elif ideal_decimation < 3: pow2 = 1
        elif ideal_decimation < 6: pow2 = 2
        elif ideal_decimation < 12: pow2 = 3
        elif ideal_decimation < 24: pow2 = 4
        elif ideal_decimation < 48: pow2 = 5
        elif ideal_decimation < 96: pow2 = 6
        else: pow2 = 7
        
        new_dec = 2 ** pow2
        new_sr = 40_000_000 // new_dec
        
        # Solo actuar si el valor realmente cambió
        old_sr = getattr(self, "_sample_rate", 0)
        if new_sr == old_sr and self.bb60c_decimation == new_dec:
            return
        
        self.bb60c_decimation = new_dec
        self._sample_rate = new_sr
        
        if self.stream_mode == "sdr":
            self._retune_requested = True
        
        # Redimensionar buffer del correlograma al nuevo sample rate
        self._resize_corr_buffer()
        
        self.metadata_updated = True
        self.save_config()
        print(f"🔄 Sample Rate ajustado a valor nativo BB60C: {self._sample_rate/1e6} MSps (Decimación {self.bb60c_decimation})")

    def _resize_corr_buffer(self):
        """Redimensiona el buffer IQ del correlograma al sample rate e historial actual."""
        target_sec  = self.waterfall_history_sec
        new_size    = max(50_000, int(self._sample_rate * target_sec))
        if new_size != getattr(self, "_corr_buf_size", 0):
            self._corr_buf_size = new_size
            self.corr_iq_buffer = np.zeros(new_size, dtype=np.complex64)
            self._corr_buf_idx  = 0
            self._corr_buf_full = False
            print(f"[Correlograma] Buffer redimensionado: {new_size} muestras = {target_sec:.1f}s @ {self._sample_rate/1e6:.2f} MSps")

    @property
    def analysis_window_sec(self):
        return getattr(self, "_analysis_window_sec", 1.0)

    @analysis_window_sec.setter
    def analysis_window_sec(self, val):
        self._analysis_window_sec = max(0.1, float(val))
        # Forzar recálculo del waterfall
        self.waterfall_history_sec = getattr(self, "_waterfall_sec", 10.0)

    @property
    def waterfall_history_sec(self):
        return getattr(self, "_waterfall_sec", 10.0)

    @waterfall_history_sec.setter
    def waterfall_history_sec(self, val):
        self._waterfall_sec = max(0.1, float(val))
        new_steps = int(self._waterfall_sec / self.analysis_window_sec)
        new_steps = max(1, new_steps)
        if new_steps != self.waterfall_steps:
            self.waterfall_steps = new_steps
            self.waterfall_data = np.full((self.waterfall_steps, self.fft_size), -100.0)
            self.waterfall_idx = 0
        
        # Redimensionar el buffer del correlograma para que coincida con el nuevo historial
        self._resize_corr_buffer()

    def reset_buffers(self):
        """Limpia los historiales para que las gráficas se llenen de arriba hacia abajo al iniciar."""
        # Limpiar cascada principal
        if hasattr(self, 'waterfall_data'):
            self.waterfall_data.fill(-100.0)
            self.waterfall_idx = 0
            
        # Limpiar historial IQ para CWT/AR/Correlograma
        if hasattr(self, 'corr_iq_buffer'):
            self.corr_iq_buffer.fill(0j)
            self._corr_buf_idx = 0
            self._corr_buf_full = False
            
        # Limpiar potencia y estadísticas
        if hasattr(self, 'power_time_data'):
            self.power_time_data.fill(-100.0)
            self.power_samples_written = 0

    def start_stream(self, mode, params):
        if self.is_playing:
            return
        
        # Si se cambia de archivo, reiniciar posición
        if mode == "file" and params.get("filename") != getattr(self, "iq_filename", None):
            self.file_position = 0
            
        self.stream_mode = mode
        if mode == "file":
            self.iq_filename = params.get("filename", "")
            self.filename = self.iq_filename
            self.data_format = params.get("format", "uint8")
            
            # Resetear si llegó al final o va a iniciar
            if self.current_file_time >= self.total_file_time or self.file_position == 0:
                self.file_position = 0
                self.current_file_time = 0.0
                self.reset_buffers()
                
            self.is_playing = True
            self.stream_thread = threading.Thread(target=self._process_file_loop, daemon=True)
            self.stream_thread.start()
        else:
            self.is_playing = True
            self.reset_buffers()
            self.stream_thread = threading.Thread(target=self._process_sdr_loop, daemon=True)
            self.stream_thread.start()

    def stop_stream(self):
        self.is_playing = False
        with self._hw_lock:
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
        # ── 1. Calcular batches para promediar todo el bloque ─────────
        if batches is None:
            batches = max(1, len(iq) // self.fft_size)

        # Actualizar contador de tiempo global
        self.elapsed_samples += len(iq)

        # ── 1.b Smart Trigger (Recorte Automático +- 1.5s) ─────────────
        if getattr(self, 'trigger_active', False):
            self.trigger_ring_buffer.append(iq.copy())
            
            # Mantener ~5 segundos de datos en el buffer circular
            total_len = sum(len(x) for x in self.trigger_ring_buffer)
            target_len = int(5.0 * self.sample_rate)
            while total_len > target_len and len(self.trigger_ring_buffer) > 1:
                total_len -= len(self.trigger_ring_buffer[0])
                self.trigger_ring_buffer.popleft()
                
            energy = iq.real**2 + iq.imag**2
            
            if self.trigger_state == 0:
                if np.max(energy) > self.trigger_high:
                    self.trigger_state = 1
            elif self.trigger_state == 1:
                if np.min(energy) < self.trigger_low:
                    # Fin del evento. Procesar buffer completo.
                    full_iq = np.concatenate(list(self.trigger_ring_buffer))
                    full_energy = full_iq.real**2 + full_iq.imag**2
                    
                    start_idx = -1
                    end_idx = -1
                    # Bucle FOR pedido para detectar cruces de umbral
                    for i in range(len(full_energy)):
                        if start_idx == -1 and full_energy[i] > self.trigger_high:
                            start_idx = i
                        elif start_idx != -1 and full_energy[i] < self.trigger_low:
                            end_idx = i
                            break
                            
                    if start_idx != -1 and end_idx != -1:
                        center_idx = (start_idx + end_idx) // 2
                        trim_samples = int(1.5 * self.sample_rate)
                        
                        trim_start = max(0, center_idx - trim_samples)
                        trim_end = min(len(full_iq), center_idx + trim_samples)
                        
                        trimmed_iq = full_iq[trim_start:trim_end]
                        
                        # Zero-Crossing Rate de la señal extraída
                        zcr = np.mean(np.abs(np.diff(np.sign(trimmed_iq.real))))
                        
                        # Guardar a disco
                        import time, os
                        if not os.path.exists("data"): os.makedirs("data")
                        fname = f"data/trigger_{int(time.time())}.npy"
                        np.save(fname, trimmed_iq)
                        print(f"\\n[SMART TRIGGER] EVENTO CAPTURADO! Guardado en {fname}")
                        print(f"   -> Centro: {center_idx}, Recorte: +-1.5s ({len(trimmed_iq)} pts), ZCR: {zcr:.4f}\\n")
                        
                    # Resetear para esperar el próximo evento o desactivarse si la UI lo dicta
                    self.trigger_state = 0
                    self.trigger_active = False # Auto-desarmar tras capturar

        # ── 2. Buffer RAW: Guardar primeras 2000 muestras contiguas (Alta Resolución, sin diezmado) ──
        n_samples = len(self.amplitude_data)
        if len(iq) >= n_samples:
            self.amplitude_data[:] = iq[:n_samples]
        else:
            self.amplitude_data[:] = np.pad(iq, (0, n_samples - len(iq)), mode='constant')

        # ── 3. Moving Average Filter (IMPLEMENTACIÓN ULTRA-RÁPIDA Y CORRECTA) ────────
        win_len = max(1, int(self.moving_avg_samples))
        
        if self.ma_enabled and win_len > 1:
            from scipy.ndimage import uniform_filter1d
            iq_f = uniform_filter1d(iq.real, size=win_len, mode='nearest') + 1j * uniform_filter1d(iq.imag, size=win_len, mode='nearest')
        else:
            iq_f = iq  # Sin filtrado

        # ── 2b. Buffer IQ crudo para Correlograma (sin decimación, circular, usando filtrado MA) ──
        iq_c64  = iq_f.astype(np.complex64)
        n_new   = len(iq_c64)
        buf_sz  = self._corr_buf_size
        if n_new >= buf_sz:
            # El bloque es mayor que el buffer: tomar las últimas buf_sz muestras
            self.corr_iq_buffer[:] = iq_c64[-buf_sz:]
            self._corr_buf_idx  = 0
            self._corr_buf_full = True
        else:
            end = self._corr_buf_idx + n_new
            if end <= buf_sz:
                self.corr_iq_buffer[self._corr_buf_idx:end] = iq_c64
            else:
                first = buf_sz - self._corr_buf_idx
                self.corr_iq_buffer[self._corr_buf_idx:] = iq_c64[:first]
                self.corr_iq_buffer[:n_new - first]      = iq_c64[first:]
                self._corr_buf_full = True
            self._corr_buf_idx = end % buf_sz
            if end >= buf_sz:
                self._corr_buf_full = True

        # Buffer de amplitud filtrada (primeras 2000 muestras contiguas sin diezmado)
        if len(iq_f) >= n_samples:
            self.amplitude_ma_data[:] = iq_f[:n_samples]
        else:
            self.amplitude_ma_data[:] = np.pad(iq_f, (0, n_samples - len(iq_f)), mode='constant')

        # ── 3b. Espectro RAW (FFT sobre señal sin filtrar) → solo para Tab 1 ───
        pwr_raw_avg = np.zeros(self.fft_size)
        for b in range(batches):
            blk = iq[b * self.fft_size : (b + 1) * self.fft_size]
            if len(blk) < self.fft_size:
                break
            blk = blk - np.mean(blk)
            fft_c = np.fft.fftshift(np.fft.fft(blk * self.window_raw))
            pwr_raw_avg += np.abs(fft_c) ** 2
        pwr_raw = 10 * np.log10(pwr_raw_avg / (max(1, batches) * self.window_raw_pwr) + 1e-12)
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
            pwr_avg = np.zeros(self.fft_size)
            for b in range(batches):
                block_iq = iq_f[b * self.fft_size : (b + 1) * self.fft_size]
                if len(block_iq) < self.fft_size:
                    break
                block_iq = block_iq - np.mean(block_iq)
                fft_complex = np.fft.fftshift(np.fft.fft(block_iq * self.window_raw))
                pwr_avg += np.abs(fft_complex) ** 2
            pwr = 10 * np.log10(pwr_avg / (max(1, batches) * self.window_raw_pwr) + 1e-12)

        # IIR simple sobre el tiempo (suavizado VBW)
        self.spectrum_data = (1 - alpha_eff) * self.spectrum_data + alpha_eff * pwr

        # ── 5. Waterfall (Espectrograma) sobre señal filtrada ───────────────
        # Cada llamada a _process_dsp_core ahora representa una ráfaga (aprox 34ms)
        # por lo que añadimos una línea directamente para mantener el cronómetro real.
        self.waterfall_idx = (self.waterfall_idx - 1) % self.waterfall_steps
        self.waterfall_data[self.waterfall_idx, :] = self.spectrum_data

        # ── 6. Histograma (Relación Señal/Ruido SNR en dB) ──────────────────
        self.histogram_data = self.snr_data.copy()

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
        if self._frames_since_autoscale >= 2 and self._autoscale_enabled: # Solo 2 frames porque ahora son de 1 segundo
            self._frames_since_autoscale = 0
            self._auto_detect_ranges()

        self.data_ready = True # Notificar a la UI

    def _auto_detect_ranges(self):
        """Auto-detecta los rangos óptimos basándose en los datos actuales, evitando NaNs."""
        if not self.is_playing:
            return

        # 1. Sanitizar datos de entrada para evitar cálculos corruptos
        spec = np.nan_to_num(self.spectrum_data, nan=-100.0)
        spec_raw = np.nan_to_num(self.spectrum_raw_data, nan=-100.0)
        amp = np.nan_to_num(np.abs(self.amplitude_data), nan=0.0)
        amp_f = np.nan_to_num(np.abs(self.amplitude_ma_data), nan=0.0)
        
        # Ignorar los bordes caídos del filtro anti-aliasing SDR para calcular el ruido
        c_start = len(spec) // 4
        c_end = len(spec) - c_start
        valid_spec = spec[c_start:c_end]
        valid_spec_raw = spec_raw[c_start:c_end]
        
        self.db_noise_floor = float(np.nanmedian(valid_spec))
        self.db_noise_floor_raw = float(np.nanmedian(valid_spec_raw))
        
        fs_mhz = self.sample_rate / 1e6
        # El BB60C tiene un ancho de banda analógico útil de ~75% del sample rate.
        # Recortamos el span visual para que la señal plana ocupe todo el ancho y esconda los bordes.
        span_mhz = fs_mhz * 0.75

        # 2. Aplicar lógica a cada gráfica configurada
        for chart_id, cfg in self.charts_config.items():
            if not isinstance(cfg, dict): continue

            # --- Eje X (Frecuencia o Tiempo) ---
            if cfg.get("auto_x"):
                if "spec" in chart_id or "wf" in chart_id or "snr" in chart_id:
                    # Centrar en center_freq con el span real del SDR
                    cfg["xmin"] = float(self.center_freq - span_mhz / 2)
                    cfg["xmax"] = float(self.center_freq + span_mhz / 2)
                elif "amp" in chart_id:
                    # El eje X de amplitud debe representar la ventana de análisis completa (ej: 1s)
                    cfg["xmin"] = 0.0
                    cfg["xmax"] = float(self.analysis_window_sec)
                elif chart_id == "pow_time":
                    # El tiempo en potencia crece hasta el máximo del buffer
                    n_pwr = len(self.power_time_data)
                    cfg["xmin"] = 0.0
                    cfg["xmax"] = float(n_pwr * self.analysis_window_sec)

            # --- Eje Y (Potencia o Amplitud) ---
            if cfg.get("auto_y"):
                if chart_id in ["mon_raw_spec", "mon_filt_spec", "spec_wf"]:
                    p_max = float(np.nanpercentile(valid_spec, 99.9))
                    altura_senal = max(10.0, p_max - self.db_noise_floor)
                    # Enmarcar la señal real: Piso de ruido abajo, picos arriba.
                    cfg["ymin"] = float(self.db_noise_floor - altura_senal * 0.2) # Piso cerca del fondo
                    cfg["ymax"] = float(p_max + altura_senal * 0.3) # Margen sobre los picos
                elif "amp" in chart_id:
                    data_y = amp_f if "filt" in chart_id else amp
                    a_max = float(np.nanmax(data_y))
                    a_min = float(np.nanmin(data_y))
                    diff = max(0.001, a_max - a_min)
                    cfg["ymin"] = float(max(0.0, a_min - diff * 0.1))
                    cfg["ymax"] = float(a_max + diff * 0.2)
                elif chart_id == "pow_time":
                    written = min(self.power_samples_written, len(self.power_time_data))
                    if written > 2 and cfg.get("auto_y", True):
                        p_valid = self.power_time_data[:written]
                        p_min = float(np.nanmin(p_valid))
                        p_max = float(np.nanmax(p_valid))
                        cfg["ymin"] = float(p_min - 5.0)
                        cfg["ymax"] = float(p_max + 5.0)
                elif chart_id == "snr_freq":
                    s_max = float(np.nanpercentile(self.snr_data, 99))
                    if cfg.get("auto_y", True):
                        # El centro de SNR siempre es 0 dB
                        span_y = float(max(10.0, s_max + 5.0))
                        cfg["ymin"] = -span_y
                        cfg["ymax"] = span_y
                elif chart_id == "stat_hist":
                    h_min = float(np.nanpercentile(self.histogram_data, 0.1))
                    h_max = float(np.nanpercentile(self.histogram_data, 99.9))
                    if cfg.get("auto_x", True):
                        margin = max(1.0, (h_max - h_min) * 0.15)
                        cfg["xmin"] = float(h_min - margin)
                        cfg["xmax"] = float(h_max + margin)

            # --- Validación Final Anti-Colapso (ymin < ymax y sin NaNs) ---
            for attr in ["xmin", "xmax", "ymin", "ymax"]:
                if np.isnan(cfg[attr]) or np.isinf(cfg[attr]):
                    # Fallback a valores seguros por defecto
                    if "min" in attr: cfg[attr] = -100.0 if "spec" in chart_id else 0.0
                    else: cfg[attr] = 0.0 if "spec" in chart_id else 1.0

            if cfg["ymax"] <= cfg["ymin"]:
                cfg["ymax"] = cfg["ymin"] + 10.0 if "spec" in chart_id else cfg["ymin"] + 0.1
            if cfg["xmax"] <= cfg["xmin"]:
                cfg["xmax"] = cfg["xmin"] + 1.0


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
            with self._hw_lock:
                if self.sdr_handle == -1:
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
            # Para evitar el Warning 4 (clamping), el BW no debe exceder el 60% del SR en el BB60C (según SDK para 40MSps)
            sr_effective = 40.0 / self.bb60c_decimation
            max_bw = sr_effective * 0.60 
            bw_actual = min(bw_safe, max_bw)
            
            res_iq_cfg = bb_configure_IQ(h, self.bb60c_decimation, bw_actual * 1e6)
            if res_iq_cfg["status"] != 0:
                print(f"⚠ Error en bb_configure_IQ: {res_iq_cfg['status']}. Reintentando con parámetros base...")
                bb_configure_IQ(h, 1, 20e6) # Fallback seguro
            
            # Actualizar sample_rate interno real
            self._sample_rate = 40_000_000 // self.bb60c_decimation

            # 3. Iniciar modo streaming
            bb_initiate(h, BB_STREAMING, BB_STREAM_IQ)
            print(f"BB60C iniciado @ {self.sample_rate/1e6} MSps (Mega-muestras por segundo)")

            # Leer ráfagas según la ventana de análisis
            samples_per_read = int(self.sample_rate * self.analysis_window_sec) 

            while self.is_playing:
                # Retune en vivo (Live Tuning completo)
                if getattr(self, "_retune_requested", False):
                    self._retune_requested = False
                    
                    ref_safe = max(-100.0, min(20.0, float(self.bb60c_ref_level)))
                    bw_safe  = max(0.1, min(40.0, float(self.bb60c_iq_bw)))
                    
                    # Recalcular decimación por si el sample_rate fue modificado
                    self.bb60c_decimation = max(1, int(40_000_000 // max(1, self.sample_rate)))
                    self.sample_rate = 40_000_000 // self.bb60c_decimation
                    
                    print(f"Reconfigurando SDR en vivo (Frec: {self.center_freq} MHz, Ref: {ref_safe} dBm, SR: {self.sample_rate/1e6} MSps)...")
                    
                    bb_abort(h)
                    bb_configure_ref_level(h, ref_safe)
                    bb_configure_gain_atten(h, self.bb60c_gain, self.bb60c_atten)
                    bb_configure_IQ_center(h, self.center_freq * 1e6)
                    bb_configure_IQ(h, self.bb60c_decimation, bw_safe * 1e6)
                    bb_initiate(h, BB_STREAMING, BB_STREAM_IQ)
                    
                    # Actualizar lecturas por ventana tras cambiar el SR
                    samples_per_read = int(self.sample_rate * self.analysis_window_sec)

                # 4. Capturar bloque IQ
                # purge=BB_FALSE para mantener continuidad
                res_iq = bb_get_IQ_unpacked(h, samples_per_read, BB_FALSE)
                self.sdr_overflow = (res_iq["status"] == 2) # ADC Overflow Detection

                if res_iq["status"] < 0:
                    print(f"Error de lectura IQ: {res_iq['status']}")
                    break
                
                iq = res_iq["iq"]
                
                # Procesar en el núcleo DSP (lote completo)
                self._process_dsp_core(iq, batches=None)

        except Exception as e:
            print(f"SDR Hardware Error: {e}", flush=True)
        finally:
            self.stop_stream()

    def _process_file_loop(self):
        """Streaming virtual leyendo un fichero .iq grabado previamente"""
        # 1. Intentar auto-detectar metadatos (etiquetas externas o nombre)
        self._try_load_metadata(self.filename)
        
        try:
            with open(self.filename, "rb") as f:
                import os

                if not os.path.exists(self.filename):
                    return
                file_size = os.path.getsize(self.filename)

                # NUEVO: Recuperar posición guardada
                if hasattr(self, "file_position") and self.file_position > 0:
                    f.seek(self.file_position)
                else:
                    self.current_file_time = 0.0

                def get_bytes_per_sample(fmt):
                    if fmt in ("uint8", "int8"): return 2
                    if fmt == "int16": return 4
                    return 8 # complex64 / float32

                bytes_per_sample = get_bytes_per_sample(self.data_format)
                # Leer ráfagas según la ventana de análisis
                chunk_bytes = int(self.sample_rate * self.analysis_window_sec) * bytes_per_sample

                self.current_file_time = 0.0
                self.total_file_time = (file_size / bytes_per_sample) / self.sample_rate

                import time

                start_real_time = time.time() - (self.current_file_time / max(0.1, self.playback_speed))

                while self.is_playing:
                    # NUEVO: Manejar cambios de parámetros en vivo (como el Sample Rate o Formato)
                    if getattr(self, "_retune_requested", False):
                        self._retune_requested = False
                        # Recalcular cuántos bytes leer por bloque y el tiempo total del archivo
                        bytes_per_sample = get_bytes_per_sample(self.data_format)
                        chunk_bytes = int(self.sample_rate * self.analysis_window_sec) * bytes_per_sample
                        self.total_file_time = (file_size / bytes_per_sample) / self.sample_rate
                        # Resincronizar el tiempo real para evitar saltos en el playback_speed
                        start_real_time = time.time() - (self.current_file_time / max(0.1, self.playback_speed))

                    # Calcular tiempo actual basado en la posición real del puntero del archivo
                    pos = f.tell()
                    self.current_file_time = (pos / bytes_per_sample) / self.sample_rate

                    raw_data = f.read(chunk_bytes)
                    if not raw_data or len(raw_data) < chunk_bytes:
                        self.is_playing = False  # Termina y se apaga
                        break

                    if self.data_format == "uint8":
                        samples = np.frombuffer(raw_data, dtype=np.uint8).astype(
                            np.float32
                        )
                        samples = (samples - 127.5) / 128.0
                        iq = samples[0::2] + 1j * samples[1::2]
                    elif self.data_format == "int8":
                        samples = np.frombuffer(raw_data, dtype=np.int8).astype(
                            np.float32
                        )
                        samples = samples / 128.0
                        iq = samples[0::2] + 1j * samples[1::2]
                    elif self.data_format == "int16":
                        samples = np.frombuffer(raw_data, dtype=np.int16).astype(
                            np.float32
                        )
                        samples = samples / 32768.0
                        iq = samples[0::2] + 1j * samples[1::2]
                    elif self.data_format == "complex64":
                        iq = np.frombuffer(raw_data, dtype=np.complex64)
                    else:
                        break

                    # Sanitizar datos para evitar NaNs o Infs en caso de formato erróneo
                    iq = np.nan_to_num(iq, nan=0.0, posinf=1.0, neginf=-1.0)

                    # --- Auto-bloqueo espectral (solo en el primer bloque si no hay metadatos) ---
                    if getattr(self, "_needs_spectral_lock", False):
                        self._needs_spectral_lock = False
                        self._perform_spectral_lock(iq)

                    self._process_dsp_core(iq, batches=None)

                    # Sincronización con playback_speed
                    target_time = self.current_file_time / max(0.1, self.playback_speed)
                    elapsed = time.time() - start_real_time
                    sleep_time = target_time - elapsed
                    if sleep_time > 0:
                        time.sleep(sleep_time)

                # Guardar posición al salir (Pausar)
                self.file_position = f.tell()

        except Exception as e:
            print(f"File Stream Error: {e}", flush=True)
            self.is_playing = False

    def _try_load_metadata(self, filename):
        """
        NIVEL 1: Carga metadatos explícitos (JSON/TXT/Nombre).
        NIVEL 2: Análisis espectral ciego para detectar la frecuencia real.
        """
        import os, json, re
        
        base = os.path.splitext(filename)[0]
        meta_found = False
        
        # --- Fase 1: Metadatos Externos ---
        for ext in [".json", ".iq.json", ".txt"]:
            meta_path = base + ext
            if os.path.exists(meta_path):
                try:
                    if ext.endswith("json"):
                        with open(meta_path, "r") as f:
                            d = json.load(f)
                            if "center_freq" in d: self.center_freq = float(d["center_freq"])
                            if "sample_rate" in d: self.sample_rate = float(d["sample_rate"])
                            if "format" in d: self.data_format = d["format"]
                            print(f"📦 Metadatos cargados desde {meta_path}")
                            meta_found = True
                            break
                except: pass
        
        if not meta_found:
            # Intentar parsear el nombre
            fn = os.path.basename(filename)
            f_match = re.search(r"(\d+\.?\d*)\s*(MHz|GHz|Hz)", fn, re.I)
            if f_match:
                val, unit = float(f_match.group(1)), f_match.group(2).upper()
                if unit == "GHZ": val *= 1000
                elif unit == "HZ": val /= 1e6
                self.center_freq = val
                meta_found = True
            
            s_match = re.search(r"(\d+\.?\d*)\s*(Msps|ksps|Hz)", fn, re.I)
            if s_match:
                val, unit = float(s_match.group(1)), s_match.group(2).upper()
                if unit == "MSPS": val *= 1e6
                elif unit == "KSPS": val *= 1000
                self.sample_rate = val
                meta_found = True

        # --- Fase 2: Análisis Espectral Ciego (Si no hay metadatos) ---
        # Si seguimos en 1420.4 pero el archivo no dice nada, intentamos 'lock-on' al pico
        # Esto se ejecutará en el primer frame de _process_file_loop
        self._needs_spectral_lock = not meta_found

    def _perform_spectral_lock(self, iq_data):
        """Analiza el primer bloque de datos para detectar la frecuencia central real."""
        # Calculamos una FFT rápida del primer bloque
        spec = np.abs(np.fft.fftshift(np.fft.fft(iq_data[:self.fft_size] * self.window_raw)))
        spec = 20 * np.log10(spec + 1e-12)
        
        # 1. Detectar bordes del filtro (Opción 2: Sample Rate)
        # Buscamos dónde cae la potencia drásticamente (>20dB)
        mid = len(spec) // 2
        noise_floor = np.median(spec)
        
        # 2. Detectar Pico (Opción 1: Frecuencia)
        # Ignorar el centro (pico DC típico de SDRs)
        spec[mid-10:mid+10] = noise_floor
        peak_idx = np.argmax(spec)
        
        if spec[peak_idx] > noise_floor + 10:
            print(f"🎯 Pico detectado en bin {peak_idx}. Posible señal de interés.", flush=True)
            
            # Solo auto-calibrar si no estamos ya cerca de la frecuencia de Hidrógeno
            if abs(self.center_freq - 1420.40575) > 0.5:
                self.center_freq = 1420.40575
                self.metadata_updated = True
                print("✨ Auto-calibrado a Línea de Hidrógeno (1420.4 MHz)", flush=True)
            else:
                print("✅ Ya sintonizado en la banda de interés.", flush=True)

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
        # No guardar durante la inicialización
        if getattr(self, "_initializing", False):
            return
        self._do_save_config()

    def _do_save_config(self):
        conf = {
            "center_freq": self.center_freq,
            "sample_rate": self.sample_rate,
            "trigger_high": getattr(self, "trigger_high", 15.0),
            "trigger_low": getattr(self, "trigger_low", 5.0),
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
            "moving_avg_samples": self.moving_avg_samples,
            "bb60c_ref_level": self.bb60c_ref_level,
            "bb60c_iq_bw": self.bb60c_iq_bw,
            "vbw_alpha": self.vbw_alpha,
            "ma_enabled": self.ma_enabled,
            "raw_mode": self.raw_mode,
            "use_welch": self.use_welch,
            "visual_span_mhz": self.visual_span_mhz,
            "charts_config": self.charts_config,
            "window_res": getattr(self, "window_res", "Auto-Detect (Pantalla Actual)"),
            "window_mode": getattr(self, "window_mode", "Normal"),
            "chart_line_width": getattr(self, "chart_line_width", 1.0),
        }
        try:
            import json, os
            sanitized = self._sanitize(conf)

            with open(
                os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json"),
                "w", encoding="utf-8"
            ) as f:
                json.dump(sanitized, f, indent=4)
        except Exception as e:
            print("Save Config Error:", e)

    def load_config(self):
        try:
            import json, os

            p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
            if os.path.exists(p):
                with open(p, "r", encoding="utf-8") as f:
                    conf = json.load(f)
                self.center_freq = conf.get("center_freq", self.center_freq)
                self.sample_rate = conf.get("sample_rate", self.sample_rate)
                self.trigger_high = conf.get("trigger_high", getattr(self, "trigger_high", 15.0))
                self.trigger_low = conf.get("trigger_low", getattr(self, "trigger_low", 5.0))
                self.db_min = conf.get("db_min", self.db_min)
                self.db_max = conf.get("db_max", self.db_max)
                self.power_db_min = conf.get("power_db_min", getattr(self, "power_db_min", -100))
                self.power_db_max = conf.get("power_db_max", getattr(self, "power_db_max", 0))
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
                self.window_res = conf.get("window_res", getattr(self, "window_res", "Auto-Detect (Pantalla Actual)"))
                self.window_mode = conf.get("window_mode", getattr(self, "window_mode", "Normal"))
                self.chart_line_width = conf.get("chart_line_width", getattr(self, "chart_line_width", 1.0))

                ap = conf.get("algo_params")
                if ap and isinstance(ap, dict):
                    self.algo_params.update(ap)

                self.analysis_window_sec = conf.get(
                    "analysis_window_sec", self.analysis_window_sec
                )
                self.moving_avg_samples = conf.get(
                    "moving_avg_samples", self.moving_avg_samples
                )
                self.use_welch = False  # Forzar apagado incluso si hay una config vieja guardada

                # --- NUEVO: Cargar parámetros de hardware BB60C ---
                self.bb60c_ref_level = conf.get("bb60c_ref_level", self.bb60c_ref_level)
                self.bb60c_iq_bw = conf.get("bb60c_iq_bw", self.bb60c_iq_bw)
                self.vbw_alpha = conf.get("vbw_alpha", self.vbw_alpha)
                self.ma_enabled = conf.get("ma_enabled", self.ma_enabled)
                self.raw_mode = conf.get("raw_mode", self.raw_mode)
                if "visual_span_mhz" in conf:
                    self.update_visual_span(conf["visual_span_mhz"])

                # Cargar configuración granular si existe
                cc = conf.get("charts_config")
                if cc and isinstance(cc, dict):
                    # Actualizar con cuidado para no perder keys nuevas si el config es viejo
                    for k, v in cc.items():
                        if k in self.charts_config:
                            self.charts_config[k].update(v)
                            # Ya NO forzamos False en auto_x/y, permitimos que persista el deseo del usuario
        except Exception as e:
            print("Load Config Error:", e)
        finally:
            # Siempre redimensionar el buffer del correlograma al SR restaurado
            self._resize_corr_buffer()


# Instancia global del DSP (Singleton pattern simple)
engine_instance = DSPEngine()
