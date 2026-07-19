"""
dsp_engine.py
Motor de Procesamiento Digital de Señales (DSP) ejecutado en segundo plano.
Lee archivos .iq, calcula FFT y las mantiene en buffers circulares
para que charts.py los renderice.
"""

import threading
import time
import json
import os
import collections
import datetime
import numpy as np
import scipy.signal
from scipy.ndimage import uniform_filter1d
from core.constants import *

try:
    from core.bbdevice.bb_api import *
    HAS_BB_API = True
except ImportError:
    HAS_BB_API = False


class DSPEngine:
    def __init__(self):
        self.is_playing = False
        self.is_paused = False   # True = pausa voluntaria del usuario (no stop)
        self.filename = None
        self._center_freq = 1420.00
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

        # Buffer IQ de alta resolución para el Correlograma
        # Se vincula al 'Historial Cascada' (waterfall_history_sec)
        self._corr_buf_size  = max(50_000, int(self._sample_rate * self._waterfall_sec))
        self.corr_iq_buffer  = np.zeros(self._corr_buf_size, dtype=np.complex64)
        self._corr_buf_idx   = 0            # próximo índice de escritura
        self._corr_buf_full  = False        # True una vez que el buffer ha sido llenado al menos una vez

        # Matrices 2D tipo cascada para métodos avanzados (CWT, AR/Burg, Correlograma)
        # Mismas dimensiones que waterfall_data; se actualizan línea a línea en _process_dsp_core
        self.cwt_wf_data  = np.full((self.waterfall_steps, self.fft_size), -100.0, dtype=np.float32)
        self.cwt_wf_idx   = 0
        self.ar_wf_data   = np.full((self.waterfall_steps, self.fft_size), -100.0, dtype=np.float32)
        self.ar_wf_idx    = 0
        self.corr_wf_data = np.full((self.waterfall_steps, self.fft_size), -100.0, dtype=np.float32)
        self.corr_wf_idx  = 0

        # Histogram samples
        self.histogram_mode = "Magnitud"
        self.histogram_data = np.random.normal(0, 1, 1000)

        # Power vs Time buffer (dBm — con offset cal_offset_dbm, sincronizado con waterfall_steps)
        self.power_time_data = np.full(self.waterfall_steps, -130.0)
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

        # Configuraciones globales para que el Header pueda iniciar el stream
        self.stream_mode = "file"
        self.active_tab = 0
        self.current_file_time = 0.0
        self.total_file_time = 0.0
        self.iq_filename = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "test_signal.iq"
        )
        self.iq_format = "int16"

        # Offset calibración dBFS→dBm: igual al Reference Level del BB60C
        # Fuente: Signal Hound API Reference — P_dBm = P_dBFS + Reference_Level
        # Con bb60c_ref_level=-30 dBm → 0 dBFS equivale a -30 dBm en la entrada RF
        self.cal_offset_dbm: float = -30.0

        # Rangos de potencia espectro en dBm (AUTO-DETECTADOS)
        self.dbm_min = -150
        self.dbm_max = -80
        self.db_noise_floor = -130  # Piso de ruido detectado (filtrado, dBm)
        self.db_noise_floor_raw = -130  # Piso de ruido detectado (RAW, dBm)

        # Rangos de gráfica Potencia vs Tiempo (dBm)
        self.power_dbm_min = -150
        self.power_dbm_max = -80

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
        self.auto_spectral_lock = True     # Habilitar/Deshabilitar auto-calibración fina (Checkbox)
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
        self.trigger_active = False
        self.trigger_high = 15.0
        self.trigger_low = 5.0
        self.trigger_state = 0
        self.trigger_ring_buffer = collections.deque()

        # ── Navegación de Frames en Pausa ──────────────────────────────────
        # Almacena snapshots compactos de los outputs DSP para review post-pausa.
        # Máx 300 frames ≈ 300 ventanas de análisis de 1s ≈ 5 minutos de historial.
        self._frame_snapshots = collections.deque(maxlen=300)
        self._review_offset = 0      # 0 = frame más reciente, N = N frames atrás
        self._review_active = False  # True cuando el usuario navega frames en pausa

    @property
    def center_freq(self):
        return getattr(self, "_center_freq", 1420.00)

    @center_freq.setter
    def center_freq(self, val):
        val = float(val)
        # Solo actuar si el valor realmente cambió
        if abs(val - self._center_freq) < 0.0001:
            return
        delta = val - self._center_freq
        self._center_freq = val
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
        print(f"[DSP] Sample Rate -> {self._sample_rate/1e6} MSps (Decimacion {self.bb60c_decimation})", flush=True)

    def _resize_corr_buffer(self):
        """Redimensiona el buffer IQ del correlograma al sample rate e historial actual.
        También redimensiona las matrices 2D (cascada continua) de CWT, AR/Burg y Correlograma.
        """
        target_sec  = self.waterfall_history_sec
        new_size    = max(50_000, int(self._sample_rate * target_sec))
        
        # 🛸 LÍMITE DE SEGURIDAD (CAP DE RAM):
        # Limitamos el buffer IQ a un máximo de 10,000,000 muestras (~80MB de RAM).
        MAX_SAFE_SAMPLES = 10_000_000
        if new_size > MAX_SAFE_SAMPLES:
            new_size = MAX_SAFE_SAMPLES

        if new_size != getattr(self, "_corr_buf_size", 0):
            self._corr_buf_size = new_size
            self.corr_iq_buffer = np.zeros(new_size, dtype=np.complex64)
            self._corr_buf_idx  = 0
            self._corr_buf_full = False
            print(f"[Correlograma] Buffer redimensionado: {new_size} muestras = {target_sec:.1f}s @ {self._sample_rate/1e6:.2f} MSps (Cap de Seguridad Activo)")

        # ── Matrices 2D tipo cascada para métodos avanzados (igual que waterfall_data) ──
        # Mismo número de pasos que el waterfall clásico, columnas = fft_size
        n_steps = max(1, int(self.waterfall_history_sec / self.analysis_window_sec))
        n_cols  = self.fft_size

        # Reusar si las dimensiones no cambiaron (evita sobreescribir historial)
        cur_cwt  = getattr(self, "cwt_wf_data",  None)
        cur_ar   = getattr(self, "ar_wf_data",   None)
        cur_corr = getattr(self, "corr_wf_data", None)

        if cur_cwt  is None or cur_cwt.shape  != (n_steps, n_cols):
            self.cwt_wf_data  = np.full((n_steps, n_cols), -100.0, dtype=np.float32)
            self.cwt_wf_idx   = 0
        if cur_ar   is None or cur_ar.shape   != (n_steps, n_cols):
            self.ar_wf_data   = np.full((n_steps, n_cols), -100.0, dtype=np.float32)
            self.ar_wf_idx    = 0
        if cur_corr is None or cur_corr.shape != (n_steps, n_cols):
            self.corr_wf_data = np.full((n_steps, n_cols), -100.0, dtype=np.float32)
            self.corr_wf_idx  = 0

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
            self.power_time_data = np.full(self.waterfall_steps, -100.0)
            self.waterfall_idx = 0
            self.power_samples_written = 0
        
        # Redimensionar el buffer del correlograma para que coincida con el nuevo historial
        self._resize_corr_buffer()

    # ── Grabación IQ a disco ────────────────────────────────────────────────

    def start_iq_recording(self) -> str:
        """Inicia la grabación IQ. Devuelve la ruta del archivo creado."""
        if getattr(self, "_iq_recording", False):
            return ""
        folder = os.path.join(os.path.dirname(os.path.dirname(__file__)), "RecordingsIQ")
        os.makedirs(folder, exist_ok=True)
        ts   = datetime.datetime.now().strftime("%Y%m%d_%Hh%Mm%Ss")
        freq = f"{self.center_freq:.3f}MHz".replace(".", "p")
        sr   = f"{self.sample_rate/1e6:.2f}Msps".replace(".", "p")
        name = f"IQREC_{ts}_{freq}_{sr}.iq"
        path = os.path.join(folder, name)

        self._iq_rec_path = path
        self._iq_rec_file = open(path, "wb")
        self._iq_recording = True
        self._iq_rec_samples = 0
        print(f"[REC] Grabacion IQ iniciada: {path}", flush=True)
        return path

    def stop_iq_recording(self) -> str:
        """Detiene la grabación IQ. Devuelve la ruta del archivo guardado."""
        if not getattr(self, "_iq_recording", False):
            return ""
        self._iq_recording = False
        path = getattr(self, "_iq_rec_path", "")
        try:
            self._iq_rec_file.close()
        except Exception:
            pass
        self._iq_rec_file = None
        print(f"✅ Grabación IQ detenida. Archivo: {path}  ({getattr(self,'_iq_rec_samples',0)} muestras)", flush=True)
        return path

    def _write_iq_chunk(self, iq: "np.ndarray"):
        """Escribe un bloque IQ en el archivo de grabación (formato int16 interleaved)."""
        if not getattr(self, "_iq_recording", False):
            return
        try:
            raw = np.empty(len(iq) * 2, dtype=np.int16)
            raw[0::2] = np.clip(iq.real * 32767, -32768, 32767).astype(np.int16)
            raw[1::2] = np.clip(iq.imag * 32767, -32768, 32767).astype(np.int16)
            self._iq_rec_file.write(raw.tobytes())
            self._iq_rec_samples += len(iq)
        except Exception as exc:
            print(f"⚠ Error escribiendo IQ: {exc}", flush=True)
            self.stop_iq_recording()

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

        # Limpiar matrices 2D de métodos avanzados (cascada continua)
        for attr, idx_attr in [("cwt_wf_data", "cwt_wf_idx"),
                                ("ar_wf_data",  "ar_wf_idx"),
                                ("corr_wf_data","corr_wf_idx")]:
            if hasattr(self, attr):
                getattr(self, attr).fill(-100.0)
                setattr(self, idx_attr, 0)

        # Limpiar potencia y estadísticas
        if hasattr(self, 'power_time_data'):
            self.power_time_data.fill(-100.0)
            self.power_samples_written = 0
            
        # Limpiar variables globales de tiempo y conteos
        self.elapsed_samples = 0
        self.rfi_event_count = 0
        if hasattr(self, 'current_file_time'):
            self.current_file_time = 0.0

    def seek_frames(self, delta: int) -> int:
        """Navega delta frames en el historial de snapshots.
        delta > 0 = hacia atrás (frames más antiguos).
        delta < 0 = hacia adelante (frames más recientes).
        Retorna el offset actual tras el movimiento.
        """
        n = len(self._frame_snapshots)
        if n == 0:
            return 0

        self._review_active = True
        new_offset = max(0, min(n - 1, self._review_offset + delta))

        # En modo archivo: no retroceder más allá del frame cuyo tiempo es 0
        if delta > 0 and self.stream_mode == "file":
            snaps = list(self._frame_snapshots)
            candidate_idx = n - 1 - new_offset
            candidate_time = snaps[candidate_idx]["file_time"]
            if candidate_time <= 0.0:
                # Buscar el último frame con tiempo > 0 que sí es retrocedible
                for off in range(new_offset, self._review_offset):
                    t = snaps[n - 1 - off]["file_time"]
                    if t > 0.0:
                        new_offset = off
                        break
                else:
                    # Ya estamos en el primero disponible, no retroceder
                    return self._review_offset

        self._review_offset = new_offset
        snaps = list(self._frame_snapshots)
        idx = n - 1 - self._review_offset
        snap = snaps[idx]

        # Restaurar los buffers de renderizado con los datos de ese frame
        np.copyto(self.spectrum_data,     snap["spectrum"])
        np.copyto(self.spectrum_raw_data, snap["spectrum_raw"])
        self.amplitude_data    = snap["amplitude"].copy()
        self.amplitude_ma_data = snap["amplitude_ma"].copy()

        if "histogram" in snap:
            self.histogram_data = snap["histogram"].copy()
        if "snr" in snap:
            self.snr_data = snap["snr"].copy()
        if "power_time" in snap:
            self.power_time_data = snap["power_time"].copy()
            self.power_samples_written = snap["power_samples"]

        self.current_file_time = snap["file_time"]
        self.elapsed_samples   = snap["elapsed"]

        # En modo archivo ajustar file_position para que al reanudar continúe desde aquí
        if self.stream_mode == "file":
            self.file_position = snap["file_pos"]

        return self._review_offset

    def exit_review_mode(self):
        """Sale del modo review — vuelve al frame más reciente y reanuda la grabación."""
        if self._review_offset != 0 and len(self._frame_snapshots) > 0:
            # Restaurar el snapshot más reciente antes de reanudar
            snap = list(self._frame_snapshots)[-1]
            np.copyto(self.spectrum_data,     snap["spectrum"])
            np.copyto(self.spectrum_raw_data, snap["spectrum_raw"])
            self.amplitude_data    = snap["amplitude"].copy()
            self.amplitude_ma_data = snap["amplitude_ma"].copy()
            
            if "histogram" in snap:
                self.histogram_data = snap["histogram"].copy()
            if "snr" in snap:
                self.snr_data = snap["snr"].copy()
            if "power_time" in snap:
                self.power_time_data = snap["power_time"].copy()
                self.power_samples_written = snap["power_samples"]
                
        self._review_offset = 0
        self._review_active = False

    def start_stream(self, mode, params):
        # Si ya hay un hilo reproduciendo, lo apagamos y esperamos a que muera para evitar solapamientos
        if hasattr(self, "stream_thread") and self.stream_thread and self.stream_thread.is_alive():
            self.is_playing = False
            try:
                # Dar tiempo suficiente para que el hilo salga de cualquier time.sleep()
                self.stream_thread.join(timeout=0.5)
            except:
                pass
                
            if self.stream_thread.is_alive():
                print("⚠️ No se pudo detener el hilo de streaming anterior a tiempo. Abortando.")
                return

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
        # ── Detener grabación IQ si estaba activa ──
        if getattr(self, "_iq_recording", False):
            self.stop_iq_recording()
        # ── Reset completo (equivalente a abrir el programa de nuevo) ──
        # Si es una pausa voluntaria, preservar snapshots y posición para review
        if not self.is_paused:
            self.file_position = 0
            self.current_file_time = 0.0
            self._review_offset = 0
            self._review_active = False
            self._frame_snapshots.clear()
            self.reset_buffers()
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
        t_start = time.perf_counter()
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
                        import os
                        if not os.path.exists("data"): os.makedirs("data")
                        fname = f"data/trigger_{int(time.time())}.npy"
                        np.save(fname, trimmed_iq)
                        print(f"\\n[SMART TRIGGER] EVENTO CAPTURADO! Guardado en {fname}")
                        print(f"   -> Centro: {center_idx}, Recorte: +-1.5s ({len(trimmed_iq)} pts), ZCR: {zcr:.4f}\\n")
                        
                    # Resetear para esperar el próximo evento o desactivarse si la UI lo dicta
                    self.trigger_state = 0
                    self.trigger_active = False # Auto-desarmar tras capturar

        # ── 2. Buffer RAW: Guardar el bloque completo para permitir Zoom de Alta Resolución ──
        self.amplitude_data = iq.copy()

        # ── 3. Moving Average Filter (IMPLEMENTACIÓN ULTRA-RÁPIDA Y CORRECTA) ────────
        win_len = max(1, int(self.moving_avg_samples))
        
        if self.ma_enabled and win_len > 1:
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

        # Buffer de amplitud filtrada completo para permitir Zoom de Alta Resolución
        self.amplitude_ma_data = iq_f.copy()

        # ── 3b. Espectro RAW (FFT sobre señal sin filtrar) → solo para Tab 1 ───
        try:
            from core.dsp_c_wrapper import compute_spectrum_fast
            pwr_raw = compute_spectrum_fast(
                iq_complex=iq,
                fft_size=self.fft_size,
                window=self.window_raw.astype(np.float32),
                window_pwr=self.window_raw_pwr,
                cal_offset=self.cal_offset_dbm
            )
        except Exception as e:
            # Fallback a numpy puro si la DLL falla
            pwr_raw_avg = np.zeros(self.fft_size)
            for b in range(batches):
                blk = iq[b * self.fft_size : (b + 1) * self.fft_size]
                if len(blk) < self.fft_size:
                    break
                blk = blk - np.mean(blk)
                fft_c = np.fft.fftshift(np.fft.fft(blk * self.window_raw))
                pwr_raw_avg += np.abs(fft_c) ** 2
            pwr_raw = 10 * np.log10(pwr_raw_avg / (max(1, batches) * self.window_raw_pwr) + 1e-12) + self.cal_offset_dbm
        
        # 🛸 Alpha efectivo: 1.0 en modo RAW (sin suavizado)
        alpha_eff = 1.0 if self.raw_mode else self.vbw_alpha
        
        self.spectrum_raw_data = (1 - alpha_eff) * self.spectrum_raw_data + alpha_eff * pwr_raw

        t_pre_welch = time.perf_counter()
        # ── 4. Espectro de Potencia (FFT) sobre señal FILTRADA ───────────────
        if self.use_welch:
            from core.advanced_dsp import run_welch  # importación diferida: solo cuando use_welch está activo
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
            try:
                from core.dsp_c_wrapper import compute_spectrum_fast
                pwr = compute_spectrum_fast(
                    iq_complex=iq_f,
                    fft_size=self.fft_size,
                    window=self.window_raw.astype(np.float32),
                    window_pwr=self.window_raw_pwr,
                    cal_offset=self.cal_offset_dbm
                )
            except Exception as e:
                pwr_avg = np.zeros(self.fft_size)
                for b in range(batches):
                    block_iq = iq_f[b * self.fft_size : (b + 1) * self.fft_size]
                    if len(block_iq) < self.fft_size:
                        break
                    block_iq = block_iq - np.mean(block_iq)
                    fft_complex = np.fft.fftshift(np.fft.fft(block_iq * self.window_raw))
                    pwr_avg += np.abs(fft_complex) ** 2
                pwr = 10 * np.log10(pwr_avg / (max(1, batches) * self.window_raw_pwr) + 1e-12) + self.cal_offset_dbm

        # ---- Estabilización Absoluta del Piso de Ruido (Anti-Flicker / Anti-Líneas) ----
        # Esto fuerza a que todos los frames tengan exactamente la misma mediana de ruido base.
        # Elimina por completo las fluctuaciones horizontales sin importar qué tan estricta sea la escala de color.
        current_median = float(np.median(pwr))
        
        if not hasattr(self, '_baseline_noise'):
            self._baseline_noise = current_median
            self._pwr_history = pwr.copy()
            
        # Si la mediana salta más de 10 dB, asumimos que es pura estática/RFI y clonamos el frame anterior
        if current_median > self._baseline_noise + 10.0:
            pwr = self._pwr_history.copy()
            # EVITAR CONGELAMIENTO: Permitir que se adapte lentamente aunque sea un salto grande
            self._baseline_noise = 0.95 * self._baseline_noise + 0.05 * current_median
        else:
            # Alinear el frame actual a la línea base para que la energía térmica no 'parpadee'
            pwr = pwr - current_median + self._baseline_noise
            self._pwr_history = pwr.copy()
            # Dejar que la línea base se adapte muuuuuy lentamente a cambios térmicos reales del LNA
            self._baseline_noise = 0.90 * self._baseline_noise + 0.10 * current_median

        # IIR simple sobre el tiempo (suavizado VBW)
        self.spectrum_data = (1 - alpha_eff) * self.spectrum_data + alpha_eff * pwr

        # ── 5. Waterfall (Espectrograma) sobre señal RAW ────────────────────
        # Cada llamada a _process_dsp_core ahora representa una ráfaga (aprox 34ms)
        # por lo que añadimos una línea directamente para mantener el cronómetro real.
        self.waterfall_idx = (self.waterfall_idx - 1) % self.waterfall_steps
        self.waterfall_data[self.waterfall_idx, :] = self.spectrum_raw_data

        # ── 5b. Cascada Continua para métodos avanzados (CWT, AR/Burg, Correlograma) ──
        # Computa UNA línea 1D por frame con algoritmos ultrarrápidos y la inserta
        # en el buffer circular correspondiente. Lee los parámetros del usuario.
        _active_method = getattr(self, "active_spec_method", "waterfall")
        if _active_method != "waterfall" and self.active_tab == 2:
            _iq_frame = iq.astype(np.complex64)  # RAW: sin filtrar MA
            _n_frame  = len(_iq_frame)
            _sr       = float(self.sample_rate)
            _offset   = float(self.db_noise_floor_raw) - 20.0
            _N_out    = self.fft_size   # columnas de salida

            try:
                if _active_method == "cwt" and hasattr(self, "cwt_wf_data"):
                    # CWT rápida: banco Morlet con N_SC escalas (configurado por el usuario)
                    # Cap: máximo 1024 escalas para evitar OOM con bloques grandes de IQ
                    _N_SC    = max(32, min(1024, int(self.algo_params.get("cwt_n_scales", 512))))
                    _dt      = 1.0 / _sr
                    _pwr_lin = 10.0 ** ((pwr_raw - _offset) / 10.0)
                    
                    # Cachear la matriz de wavelets (sólo recalcular si cambian parámetros)
                    cache_key = (_sr, self.fft_size, _N_SC)
                    if not hasattr(self, "_cwt_cache_key") or self._cwt_cache_key != cache_key:
                        _omega   = (2 * np.pi * np.linspace(-_sr/2, _sr/2, self.fft_size, endpoint=False)).astype(np.float32)
                        # Aumentar omega0 de 6 a 24 mejora drásticamente la resolución en frecuencia (hace el pico más fino)
                        _omega0  = 2 * np.pi * 24.0 
                        _fq_hz   = np.linspace(-_sr * 0.49, _sr * 0.49, _N_SC, dtype=np.float32)
                        _fq_safe = np.where(_fq_hz == 0, 1e-5, _fq_hz)
                        _s_col   = (_omega0 / (2 * np.pi * np.abs(_fq_safe)))[:, None]
                        _sgn_col = np.sign(_fq_safe)[:, None]
                        _arg     = (_s_col * _omega[None, :] - _sgn_col * _omega0).astype(np.float32)
                        _supp    = (_sgn_col * _omega[None, :] > 0).astype(np.float32)
                        _nrm     = (np.pi ** -0.25) * np.sqrt(2 * np.pi * _s_col / _dt)
                        _psi_pw  = ((_nrm ** 2) * np.exp(-(_arg ** 2)) * _supp).astype(np.float32)
                        _psi_pw_sum = np.sum(_psi_pw, axis=1, keepdims=True)
                        _psi_pw_sum = np.where(_psi_pw_sum == 0, 1.0, _psi_pw_sum)
                        _psi_pw /= _psi_pw_sum
                        self._cwt_cached_matrix = _psi_pw
                        self._cwt_cache_key = cache_key

                    _line_lin = self._cwt_cached_matrix @ _pwr_lin.astype(np.float32)
                    _line_db  = (10.0 * np.log10(_line_lin + 1e-30) + _offset).astype(np.float32)
                    # Interpolar N_SC → N_out con np.interp (vectorizado, <1ms)
                    if _N_SC != _N_out:
                        _x_in  = np.linspace(0, 1, _N_SC)
                        _x_out = np.linspace(0, 1, _N_out)
                        _line_db = np.interp(_x_out, _x_in, _line_db).astype(np.float32)
                    self.cwt_wf_idx = (self.cwt_wf_idx - 1) % self.cwt_wf_data.shape[0]
                    self.cwt_wf_data[self.cwt_wf_idx, :] = _line_db

                elif _active_method == "ar_burg_2d" and hasattr(self, "ar_wf_data"):
                    # AR/Burg 1D: usa el orden configurado por el usuario.
                    # Cap: orden ≤ 50 (costo O(N*order) con N=1024 → manejable ~5ms)
                    _ORDER  = max(2, min(50, int(self.algo_params.get("ar_order", 20))))
                    _N_SIG  = min(1024, _n_frame)  # usar más muestras para mejor resolución
                    _sig    = (_iq_frame[:_N_SIG] - _iq_frame[:_N_SIG].mean()).astype(np.complex64)
                    _ef, _eb = _sig[1:].copy(), _sig[:-1].copy()
                    _ar_c   = np.zeros(_ORDER, dtype=np.complex64)
                    _t_err  = float(np.dot(_sig, _sig.conj()).real) / _N_SIG
                    for _m in range(_ORDER):
                        _num = -2.0 * complex(np.dot(_ef, _eb.conj()))
                        _den = float(np.dot(_ef, _ef.conj()).real) + float(np.dot(_eb, _eb.conj()).real)
                        _km  = _num / (_den + 1e-30)
                        if _m > 0:
                            _ar_c[:_m] = _ar_c[:_m] + _km * _ar_c[:_m][::-1].conj()
                        _ar_c[_m]  = _km
                        _ef_n = _ef[1:] + _km * _eb[1:]
                        _eb_n = _eb[:-1] + np.conj(_km) * _ef[:-1]
                        _ef, _eb = _ef_n, _eb_n
                        _t_err *= max(0.0, 1.0 - abs(_km) ** 2)
                    # Evaluación del polinomio AR vectorizada en N_out puntos
                    _fn   = np.linspace(-0.5, 0.5, _N_out, dtype=np.float32)
                    _z    = np.exp((2j * np.pi * _fn).astype(np.complex64))
                    _dnom = np.ones(_N_out, dtype=np.complex64)
                    for _ki in range(_ORDER):
                        _dnom += _ar_c[_ki] * (_z ** (-(_ki + 1)))
                    _psd_lin = float(_t_err) / (np.abs(_dnom) ** 2 + 1e-30)
                    _psd_db  = (10.0 * np.log10(_psd_lin + 1e-30) + _offset).astype(np.float32)
                    self.ar_wf_idx = (self.ar_wf_idx - 1) % self.ar_wf_data.shape[0]
                    self.ar_wf_data[self.ar_wf_idx, :] = _psd_db

                elif _active_method == "correlogram_2d" and hasattr(self, "corr_wf_data"):
                    # Correlograma 1D: usa el lag configurado por el usuario.
                    # Cap: lag ≤ 200 con N_SIG adaptado (4×lag) para mantener velocidad
                    _MAX_LAG = max(4, min(200, int(self.algo_params.get("corr_max_lag", 37))))
                    _N_SIG   = min(max(4 * _MAX_LAG, 512), _n_frame)  # N adaptado al lag
                    _sig2    = _iq_frame[:_N_SIG].astype(np.complex64)
                    _sig2   -= _sig2.mean()
                    _p = max(1e-30, float(np.dot(_sig2, _sig2.conj()).real) / _N_SIG)
                    _sig2 /= np.sqrt(_p)
                    # ACF vectorizada: correlate full → tomar lags 0.._MAX_LAG
                    _acf_full = np.correlate(_sig2, _sig2, mode="full")  # len=2*N_SIG-1
                    _mid      = _N_SIG - 1
                    _acf_1s   = _acf_full[_mid : _mid + _MAX_LAG + 1] / _N_SIG
                    # Reconstruir ACF simétrica, ventana Bartlett y FFT
                    _lag_vec  = 2 * _MAX_LAG + 1
                    _acf_sym  = np.zeros(_lag_vec, dtype=np.complex64)
                    _acf_sym[_MAX_LAG:] = _acf_1s
                    _acf_sym[:_MAX_LAG] = np.conj(_acf_1s[1:])[::-1]
                    _bart     = np.bartlett(_lag_vec).astype(np.float32)
                    _n_fft2   = max(_N_out, 2 * _lag_vec)
                    _psd_r    = np.abs(np.fft.fftshift(np.fft.fft(_acf_sym * _bart, n=_n_fft2)))
                    _psd_db2  = (10.0 * np.log10(_psd_r + 1e-30)).astype(np.float32)
                    if len(_psd_db2) != _N_out:
                        _x_in2  = np.linspace(0, 1, len(_psd_db2))
                        _x_out2 = np.linspace(0, 1, _N_out)
                        _psd_db2 = np.interp(_x_out2, _x_in2, _psd_db2).astype(np.float32)
                    _psd_db2 += _offset
                    self.corr_wf_idx = (self.corr_wf_idx - 1) % self.corr_wf_data.shape[0]
                    self.corr_wf_data[self.corr_wf_idx, :] = _psd_db2
            except Exception:
                pass  # Nunca detener el stream por un error de DSP avanzado

        t_pre_hist = time.perf_counter()
        # ── 6. Histograma (Distribución) sobre señal RAW ────────────────────
        if getattr(self, "histogram_mode", "Magnitud") == "Magnitud":
            self.histogram_data = np.abs(self.amplitude_data).copy()
        else:
            self.histogram_data = np.angle(self.amplitude_data).copy()

        # ── 7. Potencia instantánea vs Tiempo sobre señal RAW ───────────────
        inst_pwr_db = float(np.mean(pwr_raw))
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

        # ── 8. SNR logarítmico por bin sobre señal RAW ───────────────────
        # Fórmula: SNR[dB] = P_señal[dBm] - P_ruido[dBm]  (offset se cancela, SNR es relativo)
        # El piso de ruido se estima con un filtro de mediana local (baseline dinámico)
        # para que las señales fuertes no levanten artificialmente el fondo.
        _k_size = max(3, int(len(self.spectrum_raw_data) * 0.04))
        if _k_size % 2 == 0: _k_size += 1
        noise_floor = scipy.signal.medfilt(self.spectrum_raw_data, kernel_size=_k_size)
        self.snr_data = self.spectrum_raw_data - noise_floor

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
                self.rfi_last_time = datetime.datetime.now().strftime("%H:%M:%S") + " UTC"
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

        # Broadcast UDP a qt_monitor.py (Evita que Flet se congele corriendo Qt en hilos)
        if getattr(self, "udp_active", True):
            try:
                import socket
                if not hasattr(self, "_udp_sock"):
                    self._udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    self._udp_addr = ("127.0.0.1", 9999)
                
                # Decimar IQ a 1024 puntos para no saturar el buffer de red
                raw_y = np.real(iq).astype(np.float32)
                filt_y = np.real(self.amplitude_ma_data).astype(np.float32)
                step = max(1, len(raw_y) // 1024)
                step_f = max(1, len(filt_y) // 1024)
                
                payload = (
                    self.frequencies_mhz.astype(np.float32).tobytes() +
                    self.spectrum_raw_data.astype(np.float32).tobytes() +
                    self.spectrum_data.astype(np.float32).tobytes() +
                    raw_y[::step][:1024].tobytes() +
                    filt_y[::step_f][:1024].tobytes()
                )
                self._udp_sock.sendto(payload, self._udp_addr)
            except Exception as e:
                pass

        # ── 11. Snapshot de frame para navegación en pausa ───────────────────
        # Solo guardar si NO estamos en modo review (para no sobreescribir historial con datos del seek)
        if not self._review_active:
            snap = {
                "spectrum":     self.spectrum_data.copy(),
                "spectrum_raw": self.spectrum_raw_data.copy(),
                "amplitude":    self.amplitude_data.copy(),
                "amplitude_ma": self.amplitude_ma_data.copy(),
                "histogram":    getattr(self, "histogram_data", np.array([])).copy(),
                "snr":          getattr(self, "snr_data", np.array([])).copy(),
                "power_time":   getattr(self, "power_time_data", np.array([])).copy(),
                "power_samples": getattr(self, "power_samples_written", 0),
                "file_time":    getattr(self, "current_file_time", 0.0),
                "file_pos":     getattr(self, "file_position", 0),
                "elapsed":      self.elapsed_samples,
            }
            self._frame_snapshots.append(snap)

        t_total = time.perf_counter() - t_start
        print(f"[DSP PERF] Frame {self.elapsed_samples // len(iq)} | "
              f"Filtrado MA: {((t_pre_welch - t_start) * 1000):.2f} ms | "
              f"FFT/Pwr: {((t_pre_hist - t_pre_welch) * 1000):.2f} ms | "
              f"CFAR/Detección: {((t_total - (t_pre_hist - t_start)) * 1000):.2f} ms | "
              f"Total DSP: {(t_total * 1000):.2f} ms")

    def _auto_detect_ranges(self):
        """Auto-detecta los rangos óptimos basándose en los datos actuales, evitando NaNs."""
        if not self.is_playing:
            return

        # 1. Sanitizar datos de entrada para evitar cálculos corruptos
        spec = np.nan_to_num(self.spectrum_data, nan=-100.0)
        spec_raw = np.nan_to_num(self.spectrum_raw_data, nan=-100.0)
        # IMPORTANTE: amplitude_data tiene shape (N_muestras,) que puede ser 2M+.
        # np.nan_to_num internamente llama np.isnan() creando un bool array de 2M = OOM.
        # Usamos solo un slice de 4096 muestras — suficiente para estadísticas de amplitud.
        _AMP_SAMPLE = 4096
        _a_raw = self.amplitude_data[:_AMP_SAMPLE]
        _a_f   = self.amplitude_ma_data[:_AMP_SAMPLE]
        amp   = np.abs(_a_raw[np.isfinite(_a_raw)])
        amp_f = np.abs(_a_f[np.isfinite(_a_f)])
        
        # Ignorar los bordes caídos del filtro anti-aliasing SDR para calcular el ruido
        c_start = len(spec) // 4
        c_end = len(spec) - c_start
        valid_spec = spec[c_start:c_end]
        valid_spec_raw = spec_raw[c_start:c_end]
        
        self.db_noise_floor = float(np.nanmedian(valid_spec))
        self.db_noise_floor_raw = float(np.nanmedian(valid_spec_raw))
        
        fs_mhz = self.sample_rate / 1e6
        # Se muestra el ancho de banda analógico completo (100% del Sample Rate) en modo automático.
        # Anteriormente se limitaba al 75% para ocultar la caída de los filtros anti-aliasing.
        span_mhz = fs_mhz
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
                    a_max = max(0.001, float(np.nanmax(data_y)))
                    cfg["ymin"] = float(-a_max * 1.2)
                    cfg["ymax"] = float(a_max * 1.2)
                elif chart_id == "pow_time":
                    written = min(self.power_samples_written, len(self.power_time_data))
                    if written > 2 and cfg.get("auto_y", True):
                        p_valid = self.power_time_data[:written]
                        p_min = float(np.nanmin(p_valid))
                        p_max = float(np.nanmax(p_valid))
                        cfg["ymin"] = float(p_min - 0.1)
                        cfg["ymax"] = float(p_max + 0.1)
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

        # Al reanudar SDR en live: salir del modo review, el historial anterior se descarta
        self._review_active = False
        self._review_offset = 0

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
                
                # Grabar IQ a disco si está activo el modo grabación
                self._write_iq_chunk(iq)
                
                # Procesar en el núcleo DSP (lote completo)
                self._process_dsp_core(iq, batches=None)

        except Exception as e:
            print(f"SDR Hardware Error: {e}", flush=True)
        finally:
            # Si es pausa voluntaria, no llamar stop_stream() para preservar
            # los snapshots y el historial de frames capturados antes de pausar.
            if not self.is_paused:
                self.stop_stream()
            else:
                # Solo liberar el hardware SDR, sin borrar datos
                with self._hw_lock:
                    if self.sdr_handle != -1:
                        try:
                            bb_abort(self.sdr_handle)
                            bb_close_device(self.sdr_handle)
                            self.sdr_handle = -1
                            print("SDR BB60C pausado (hardware liberado, historial preservado).")
                        except:
                            pass

    def _process_file_loop(self):
        """Streaming virtual leyendo un fichero .iq grabado previamente"""
        # 1. Intentar auto-detectar metadatos (etiquetas externas o nombre)
        self._try_load_metadata(self.filename)
        
        if not os.path.exists(self.filename):
            return
        try:
            with open(self.filename, "rb") as f:
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

                # Solo resetear el tiempo si estamos empezando desde el inicio
                resuming_from_seek = hasattr(self, "file_position") and self.file_position > 0
                if not resuming_from_seek:
                    self.current_file_time = 0.0
                self.total_file_time = (file_size / bytes_per_sample) / self.sample_rate

                # Salir del modo review para que los nuevos frames vuelvan a grabarse
                self._review_active = False
                self._review_offset = 0

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
                    if not raw_data or len(raw_data) < chunk_bytes or not self.is_playing:
                        self.is_playing = False  # Termina y se apaga
                        break

                    if not self.is_playing:
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

                    if not self.is_playing:
                        break

                    # Sanitizar datos para evitar NaNs o Infs en caso de formato erróneo
                    iq = np.nan_to_num(iq, nan=0.0, posinf=1.0, neginf=-1.0)

                    # --- Auto-bloqueo espectral (solo en el primer bloque si no hay metadatos) ---
                    if getattr(self, "_needs_spectral_lock", False):
                        self._needs_spectral_lock = False
                        self._perform_spectral_lock(iq)

                    # --- Desplazamiento de Frecuencia Digital para Simular Sintonía en Archivos ---
                    file_cf = getattr(self, "file_center_freq", 1420.40575)
                    tuned_cf = self.center_freq
                    delta_f = file_cf - tuned_cf
                    
                    if abs(delta_f) > 1e-6:
                        nyquist_limit = (self.sample_rate / 2.0) / 1e6
                        if abs(delta_f) > nyquist_limit:
                            # Fuera de banda: reemplazamos la señal grabada por ruido térmico simulado a nivel del piso de ruido
                            iq = np.random.normal(0, 0.005, len(iq)) + 1j * np.random.normal(0, 0.005, len(iq))
                        else:
                            # Dentro de banda: aplicamos desplazamiento digital de frecuencia (complejo)
                            n = np.arange(len(iq))
                            phase = 2.0 * np.pi * (delta_f * 1e6) * n / self.sample_rate
                            iq = iq * np.exp(1j * phase)

                    if not self.is_playing:
                        break

                    self._process_dsp_core(iq, batches=None)

                    # Sincronización con playback_speed (con escape rápido a micro-intervalos si se detiene)
                    target_time = self.current_file_time / max(0.1, self.playback_speed)
                    elapsed = time.time() - start_real_time
                    sleep_time = target_time - elapsed
                    if sleep_time > 0:
                        steps = int(sleep_time / 0.03) # Intervalos de 30ms para respuesta ultra-instantánea
                        for _ in range(steps):
                            if not self.is_playing:
                                break
                            time.sleep(0.03)
                        residual = sleep_time % 0.03
                        if residual > 0 and self.is_playing:
                            time.sleep(residual)

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
        # Si ya estábamos reproduciendo este mismo archivo y reanudamos desde pausa,
        # NO reiniciamos la auto-calibración espectral ni sobreescribimos los cambios del usuario.
        if getattr(self, "file_position", 0) > 0:
            self._needs_spectral_lock = False
            return

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
        self._needs_spectral_lock = not meta_found and getattr(self, "auto_spectral_lock", True)
        if not meta_found:
            self.file_center_freq = 1420.40575
        else:
            self.file_center_freq = self.center_freq

    def _perform_spectral_lock(self, iq_data):
        """Analiza el primer bloque de datos para detectar la frecuencia central real."""
        if not getattr(self, "auto_spectral_lock", True):
            print("✅ Auto-calibración fina desactivada por el usuario. Mapeando a frecuencia manual.", flush=True)
            self.file_center_freq = self.center_freq
            return
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
            
            # Solo auto-calibrar si el usuario ya está intentando sintonizar cerca de la frecuencia de Hidrógeno
            if abs(self.center_freq - 1420.40575) <= 1.0:
                self.center_freq = 1420.40575
                self.metadata_updated = True
                print("✨ Auto-calibrado fino a Línea de Hidrógeno (1420.4 MHz)", flush=True)
            else:
                print("✅ Sintonización manual mantenida por el usuario.", flush=True)
            self.file_center_freq = 1420.40575
        else:
            # Si no hay pico claro, mantenemos la frecuencia por defecto del archivo de hidrógeno
            self.file_center_freq = 1420.40575

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
        # Si el motor está pausado, marcar para que el refresh_loop
        # redibuje la gráfica activa con los nuevos límites de ejes
        if getattr(self, "is_paused", False):
            self._seek_refresh = True

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
            "auto_spectral_lock": getattr(self, "auto_spectral_lock", True),
            "theme": getattr(self, "theme", "dark"),
        }
        try:
            sanitized = self._sanitize(conf)
            config_dir = os.path.dirname(os.path.abspath(__file__))
            target  = os.path.join(config_dir, "config.json")
            tmp     = target + ".tmp"
            # Escritura atómica: escribir a .tmp y renombrar
            # Evita JSON corrupto si la app crashea durante la escritura
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(sanitized, f, indent=4)
            os.replace(tmp, target)  # Operación atómica en Windows y POSIX
        except Exception as e:
            print("Save Config Error:", e)

    def load_config(self):
        try:
            p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
            if os.path.exists(p):
                with open(p, "r", encoding="utf-8") as f:
                    conf = json.load(f)
                self.center_freq = conf.get("center_freq", self.center_freq)
                self.sample_rate = conf.get("sample_rate", self.sample_rate)
                self.trigger_high = conf.get("trigger_high", getattr(self, "trigger_high", 15.0))
                self.trigger_low = conf.get("trigger_low", getattr(self, "trigger_low", 5.0))
                self.cal_offset_dbm = conf.get("cal_offset_dbm", self.cal_offset_dbm)
                # Compatibilidad: acepta tanto dbm_min/max (nuevo) como db_min/max (legacy)
                self.dbm_min = conf.get("dbm_min", conf.get("db_min", self.dbm_min))
                self.dbm_max = conf.get("dbm_max", conf.get("db_max", self.dbm_max))
                self.power_dbm_min = conf.get("power_dbm_min", conf.get("power_db_min", getattr(self, "power_dbm_min", -150)))
                self.power_dbm_max = conf.get("power_dbm_max", conf.get("power_db_max", getattr(self, "power_dbm_max", -80)))
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

                self.bb60c_ref_level = conf.get("bb60c_ref_level", self.bb60c_ref_level)
                self.bb60c_iq_bw = conf.get("bb60c_iq_bw", self.bb60c_iq_bw)
                self.vbw_alpha = conf.get("vbw_alpha", self.vbw_alpha)
                self.ma_enabled = conf.get("ma_enabled", self.ma_enabled)
                self.raw_mode = conf.get("raw_mode", self.raw_mode)
                self.auto_spectral_lock = conf.get("auto_spectral_lock", True)
                self.theme = conf.get("theme", "dark")
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
