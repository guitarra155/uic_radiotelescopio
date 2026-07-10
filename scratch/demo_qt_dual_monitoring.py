import sys
import os
import numpy as np
import time

try:
    import pyqtgraph as pg
    from pyqtgraph.Qt import QtWidgets, QtCore
except ImportError:
    print("ERROR: Faltan librerías requeridas.")
    sys.exit(1)

# --- Configuración Visual ---
pg.setConfigOption('background', '#0b1319')
pg.setConfigOption('foreground', '#888888')

class DualMonitoringWindow(QtWidgets.QMainWindow):
    def __init__(self, iq_file_path):
        super().__init__()
        self.setWindowTitle(f"Reproductor IQ OpenGL (LOD Dinámico y Sincronizado): {os.path.basename(iq_file_path)}")
        self.resize(1200, 850)
        
        # --- Parámetros Reales ---
        self.sample_rate = 2.5e6
        self.n_samples = 8192     
        self.history_seconds = 10.0  
        self.max_visual_points = 8192 
        
        # Cargar datos a memoria
        raw_data = np.fromfile(iq_file_path, dtype=np.int16)
        self.real_part = raw_data[0::2].astype(np.float32) / 32767.0
        self.imag_part = raw_data[1::2].astype(np.float32) / 32767.0
        
        # Filtro global offline (Optimización)
        kernel = np.ones(10) / 10.0
        self.filt_part_i = np.convolve(self.real_part, kernel, mode='same')
        self.filt_part_q = np.convolve(self.imag_part, kernel, mode='same')
        
        self.total_samples = len(self.real_part)
        self.total_time_sec = self.total_samples / self.sample_rate
        self.current_index = 0
        
        self.playback_start_time = None
        self.start_index = 0
        self.auto_scroll = True 
        
        # UI
        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)
        layout = QtWidgets.QGridLayout(central_widget)
        
        top_panel = QtWidgets.QHBoxLayout()
        self.time_label = QtWidgets.QLabel("Tiempo: 0.000 s / 0.000 s")
        self.time_label.setStyleSheet("color: #00D2FF; font-weight: bold; font-size: 14px; width: 200px;")
        
        self.progress_bar = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.progress_bar.setRange(0, self.total_samples)
        self.progress_bar.sliderMoved.connect(self.seek_position)
        
        self.fps_label = QtWidgets.QLabel("FPS: 0")
        self.fps_label.setStyleSheet("color: #00FF88; font-weight: bold;")
        
        self.pause_btn = QtWidgets.QPushButton("Pausar Reproducción")
        self.pause_btn.clicked.connect(self.toggle_playback)
        self.is_paused = False
        
        top_panel.addWidget(self.time_label)
        top_panel.addWidget(self.progress_bar)
        top_panel.addWidget(self.pause_btn)
        top_panel.addWidget(self.fps_label)
        layout.addLayout(top_panel, 0, 0, 1, 2)
        
        # --- Gráficas ---
        # 1 y 2: Espectros RAW y Filtrado (Instantáneos)
        self.plot_spec_raw = pg.PlotWidget(title="<span style='color: #00D2FF'>Espectro RAW</span>")
        self.plot_spec_raw.setLabel('left', 'Potencia (dBFS)')
        self.plot_spec_raw.setLabel('bottom', 'Frecuencia (MHz)')
        self.plot_spec_raw.setYRange(-100, 0)
        self.curve_spec_raw = self.plot_spec_raw.plot(pen=pg.mkPen('#00D2FF', width=1.5))
        layout.addWidget(self.plot_spec_raw, 1, 0)
        
        self.plot_spec_filt = pg.PlotWidget(title="<span style='color: #00FF88'>Espectro Filtrado (MA)</span>")
        self.plot_spec_filt.setLabel('left', 'Potencia (dBFS)')
        self.plot_spec_filt.setLabel('bottom', 'Frecuencia (MHz)')
        self.curve_spec_filt = self.plot_spec_filt.plot(pen=pg.mkPen('#00FF88', width=1.5))
        
        # Sincronizar vista de ambos espectros (X e Y compartidos)
        self.plot_spec_filt.setXLink(self.plot_spec_raw)
        self.plot_spec_filt.setYLink(self.plot_spec_raw)
        
        layout.addWidget(self.plot_spec_filt, 1, 1)
        
        # 3 y 4: Amplitudes (Con LOD Dinámico para Zoom Inteligente)
        self.plot_amp_raw = pg.PlotWidget(title=f"<span style='color: #00D2FF'>Amplitud Dinámica (RAW)</span>")
        self.plot_amp_raw.setLabel('left', 'Amplitud (V)')
        self.plot_amp_raw.setLabel('bottom', 'Tiempo Absoluto (s)')
        self.curve_amp_raw_i = self.plot_amp_raw.plot(pen=pg.mkPen('#00D2FF', width=1.0))
        self.curve_amp_raw_q = self.plot_amp_raw.plot(pen=pg.mkPen('#E040FB', width=1.0))
        layout.addWidget(self.plot_amp_raw, 2, 0)
        
        self.plot_amp_filt = pg.PlotWidget(title=f"<span style='color: #00FF88'>Amplitud Filtrada Dinámica</span>")
        self.plot_amp_filt.setLabel('left', 'Amplitud (V)')
        self.plot_amp_filt.setLabel('bottom', 'Tiempo Absoluto (s)')
        self.curve_amp_filt_i = self.plot_amp_filt.plot(pen=pg.mkPen('#00FF88', width=1.0))
        self.curve_amp_filt_q = self.plot_amp_filt.plot(pen=pg.mkPen('#FF9100', width=1.0))
        
        # Sincronizar eje de tiempo entre las gráficas RAW y FILTRADA
        self.plot_amp_filt.setXLink(self.plot_amp_raw)
        
        layout.addWidget(self.plot_amp_filt, 2, 1)

        # Solo conectamos el evento a UNA gráfica (la maestra), ya que están eslabonadas
        self.plot_amp_raw.getViewBox().sigXRangeChanged.connect(self.on_zoom_changed)

        # Ejes y Ventanas constantes
        self.freq_axis = np.linspace(-self.sample_rate/2, self.sample_rate/2, self.n_samples) / 1e6
        self.window = np.hamming(self.n_samples)
        
        self.last_fps_time = time.perf_counter()
        self.frames = 0
        
        # Timer
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.playback_tick)
        self.timer.start(30) 

    def toggle_playback(self):
        self.is_paused = not self.is_paused
        if self.is_paused:
            self.timer.stop()
            self.pause_btn.setText("Reanudar Reproducción")
            self.pause_btn.setStyleSheet("background-color: #d32f2f;")
            self.auto_scroll = False 
        else:
            self.playback_start_time = time.perf_counter()
            self.start_index = self.current_index
            self.timer.start(30)
            self.pause_btn.setText("Pausar Reproducción")
            self.pause_btn.setStyleSheet("")
            self.auto_scroll = True

    def seek_position(self, position):
        self.current_index = position
        self.playback_start_time = time.perf_counter()
        self.start_index = self.current_index
        if self.is_paused:
            self.redraw_spectrums()
            self.force_amplitude_auto_scroll()

    def on_zoom_changed(self):
        self.auto_scroll = False
        self.redraw_amplitudes_lod()

    def force_amplitude_auto_scroll(self):
        end_idx = self.current_index + self.n_samples
        history_samples = int(self.history_seconds * self.sample_rate)
        start_hist_idx = max(0, end_idx - history_samples)
        
        start_time_sec = start_hist_idx / self.sample_rate
        end_time_sec = end_idx / self.sample_rate
        
        # Fijar vista (Solo a la gráfica principal, la eslabonada la sigue)
        self.plot_amp_raw.setXRange(start_time_sec, end_time_sec, padding=0)
        self.auto_scroll = True

    def playback_tick(self):
        now = time.perf_counter()
        if self.playback_start_time is None:
            self.playback_start_time = now
            self.start_index = self.current_index
            
        elapsed_sec = now - self.playback_start_time
        target_idx = self.start_index + int(elapsed_sec * self.sample_rate)
        
        if target_idx >= self.total_samples - self.n_samples:
            target_idx = 0
            self.playback_start_time = now
            self.start_index = 0
            
        self.current_index = target_idx
        
        self.redraw_spectrums()
        
        if self.auto_scroll:
            self.force_amplitude_auto_scroll()
            
        current_time_sec = self.current_index / self.sample_rate
        self.time_label.setText(f"Tiempo: {current_time_sec:.3f} s / {self.total_time_sec:.3f} s")
        self.progress_bar.blockSignals(True)
        self.progress_bar.setValue(self.current_index)
        self.progress_bar.blockSignals(False)

        self.frames += 1
        if now - self.last_fps_time >= 1.0:
            fps = self.frames / (now - self.last_fps_time)
            self.fps_label.setText(f"FPS: {fps:.1f}")
            self.frames = 0
            self.last_fps_time = now

    def redraw_spectrums(self):
        end_idx = self.current_index + self.n_samples
        if end_idx >= self.total_samples: return
        
        window_i = self.real_part[self.current_index:end_idx]
        window_q = self.imag_part[self.current_index:end_idx]
        window_filt_i = self.filt_part_i[self.current_index:end_idx]
        window_filt_q = self.filt_part_q[self.current_index:end_idx]
        
        c_raw = (window_i + 1j * window_q) * self.window
        f_raw = np.fft.fftshift(np.fft.fft(c_raw))
        spec_raw = 10.0 * np.log10(np.abs(f_raw)**2 / self.n_samples + 1e-12)
        
        c_filt = (window_filt_i + 1j * window_filt_q) * self.window
        f_filt = np.fft.fftshift(np.fft.fft(c_filt))
        spec_filt = 10.0 * np.log10(np.abs(f_filt)**2 / self.n_samples + 1e-12)
        
        self.curve_spec_raw.setData(self.freq_axis, spec_raw)
        self.curve_spec_filt.setData(self.freq_axis, spec_filt)

    def redraw_amplitudes_lod(self):
        try:
            x_min, x_max = self.plot_amp_raw.viewRange()[0]
        except:
            return
            
        if x_max <= x_min: return
        
        idx_min = int(x_min * self.sample_rate)
        idx_max = int(x_max * self.sample_rate)
        
        idx_min = max(0, min(idx_min, self.total_samples))
        idx_max = max(0, min(idx_max, self.total_samples))
        
        n_visible = idx_max - idx_min
        if n_visible < 2: return
        
        if n_visible > self.max_visual_points:
            step = n_visible // self.max_visual_points
            hist_i = self.real_part[idx_min:idx_max:step]
            hist_q = self.imag_part[idx_min:idx_max:step]
            hist_filt_i = self.filt_part_i[idx_min:idx_max:step]
            hist_filt_q = self.filt_part_q[idx_min:idx_max:step]
            time_axis = np.linspace(x_min, x_max, len(hist_i))
        else:
            hist_i = self.real_part[idx_min:idx_max]
            hist_q = self.imag_part[idx_min:idx_max]
            hist_filt_i = self.filt_part_i[idx_min:idx_max]
            hist_filt_q = self.filt_part_q[idx_min:idx_max]
            time_axis = np.linspace(x_min, x_max, n_visible)
            
        # Al actualizar las curvas, ambas gráficas se rellenan con el mismo array que cubre la vista común
        self.curve_amp_raw_i.setData(time_axis, hist_i)
        self.curve_amp_raw_q.setData(time_axis, hist_q)
        self.curve_amp_filt_i.setData(time_axis, hist_filt_i)
        self.curve_amp_filt_q.setData(time_axis, hist_filt_q)

def select_and_run():
    app = QtWidgets.QApplication(sys.argv)
    file_path, _ = QtWidgets.QFileDialog().getOpenFileName(
        None, "Selecciona Archivo IQ", os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data")), "IQ (*.iq);;All (*.*)"
    )
    if file_path:
        window = DualMonitoringWindow(file_path)
        window.show()
        sys.exit(app.exec())

if __name__ == '__main__':
    select_and_run()
