import sys
import numpy as np
import pyqtgraph as pg
from PyQt6 import QtWidgets, QtCore
from core.dsp_engine import engine_instance

class DualMonitorWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Monitor Acelerado por GPU (SDR++)")
        self.resize(1200, 800)
        
        # Tema Oscuro
        pg.setConfigOption('background', '#0b1319')
        pg.setConfigOption('foreground', '#888888')

        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        layout = QtWidgets.QGridLayout(central)

        # 1. Espectro RAW
        self.plot_spec_raw = pg.PlotWidget(title="<span style='color: #00D2FF'>Espectro RAW (C++)</span>")
        self.plot_spec_raw.setLabel('left', 'Potencia', units='dBm')
        self.plot_spec_raw.setLabel('bottom', 'Frecuencia', units='MHz')
        self.curve_spec_raw = self.plot_spec_raw.plot(pen=pg.mkPen('#00D2FF', width=1.5))
        layout.addWidget(self.plot_spec_raw, 0, 0)

        # 2. Espectro Filtrado
        self.plot_spec_filt = pg.PlotWidget(title="<span style='color: #00FF88'>Espectro Filtrado (C++)</span>")
        self.plot_spec_filt.setLabel('left', 'Potencia', units='dBm')
        self.plot_spec_filt.setLabel('bottom', 'Frecuencia', units='MHz')
        self.curve_spec_filt = self.plot_spec_filt.plot(pen=pg.mkPen('#00FF88', width=1.5))
        layout.addWidget(self.plot_spec_filt, 0, 1)

        # Sync ejes X e Y
        self.plot_spec_filt.setXLink(self.plot_spec_raw)
        self.plot_spec_filt.setYLink(self.plot_spec_raw)

        # 3. Amplitud Temporal RAW
        self.plot_amp_raw = pg.PlotWidget(title="<span style='color: #00D2FF'>Amplitud RAW</span>")
        self.plot_amp_raw.setLabel('left', 'Amplitud')
        self.curve_amp_raw = self.plot_amp_raw.plot(pen=pg.mkPen('#00D2FF', width=1.0))
        layout.addWidget(self.plot_amp_raw, 1, 0)

        # 4. Amplitud Temporal Filtrada
        self.plot_amp_filt = pg.PlotWidget(title="<span style='color: #00FF88'>Amplitud Filtrada</span>")
        self.plot_amp_filt.setLabel('left', 'Amplitud')
        self.curve_amp_filt = self.plot_amp_filt.plot(pen=pg.mkPen('#00FF88', width=1.0))
        layout.addWidget(self.plot_amp_filt, 1, 1)

        # Timer de 60 FPS (16 ms)
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_plots)
        self.timer.start(16)

    def update_plots(self):
        if not engine_instance.is_playing:
            return

        # Espectros
        freqs = engine_instance.frequencies_mhz
        
        # Nos aseguramos que C++ haya generado los datos
        spec_raw = getattr(engine_instance, "spectrum_raw_data", None)
        spec_filt = getattr(engine_instance, "spectrum_data", None)
        
        if freqs is not None and len(freqs) > 0:
            if spec_raw is not None and len(spec_raw) == len(freqs):
                self.curve_spec_raw.setData(freqs, spec_raw)
            if spec_filt is not None and len(spec_filt) == len(freqs):
                self.curve_spec_filt.setData(freqs, spec_filt)

        # Amplitudes (LOD decimation para dibujar rápido)
        iq_raw = getattr(engine_instance, "current_iq", None)
        iq_filt = getattr(engine_instance, "amplitude_ma_data", None)
        
        if iq_raw is not None:
            # Dibujamos solo la parte Real para rendimiento
            y = np.real(iq_raw)
            # Decimación simple para no dibujar 1 millón de puntos (máx 4096)
            step = max(1, len(y) // 4096)
            self.curve_amp_raw.setData(y[::step])

        if iq_filt is not None:
            y_f = np.real(iq_filt)
            step_f = max(1, len(y_f) // 4096)
            self.curve_amp_filt.setData(y_f[::step_f])

# Para lanzarlo sin bloquear Flet, usamos un QThread o Multiprocessing.
# La opción más simple en Windows es abrir PyQt en un proceso separado o usar QApplication 
# en un hilo, pero Qt requiere estar en el hilo principal. 
# Si Flet ya usa el hilo principal, lanzaremos Qt en un sub-proceso pasándole los datos,
# o podemos iniciar PyQt en un hilo y cruzar los dedos (a veces funciona en Win).

import threading
_qt_app = None

def run_qt_app():
    global _qt_app
    if _qt_app is None:
        _qt_app = QtWidgets.QApplication(sys.argv)
    
    win = DualMonitorWindow()
    win.show()
    _qt_app.exec()

def launch_gpu_monitor():
    t = threading.Thread(target=run_qt_app, daemon=True)
    t.start()
