import sys
import os
import socket
import numpy as np
import pyqtgraph as pg
from PyQt6 import QtWidgets, QtCore

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
        self.plot_spec_raw.setYRange(-150, -40)
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
        self.plot_amp_raw = pg.PlotWidget(title="<span style='color: #00D2FF'>Amplitud RAW (Decimada)</span>")
        self.plot_amp_raw.setLabel('left', 'Amplitud')
        self.plot_amp_raw.setYRange(-0.5, 0.5)
        self.curve_amp_raw = self.plot_amp_raw.plot(pen=pg.mkPen('#00D2FF', width=1.0))
        layout.addWidget(self.plot_amp_raw, 1, 0)

        # 4. Amplitud Temporal Filtrada
        self.plot_amp_filt = pg.PlotWidget(title="<span style='color: #00FF88'>Amplitud Filtrada</span>")
        self.plot_amp_filt.setLabel('left', 'Amplitud')
        self.plot_amp_filt.setYRange(-0.5, 0.5)
        self.curve_amp_filt = self.plot_amp_filt.plot(pen=pg.mkPen('#00FF88', width=1.0))
        layout.addWidget(self.plot_amp_filt, 1, 1)

        # Socket UDP para recibir datos del motor DSP
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("127.0.0.1", 9999))
        self.sock.setblocking(False)

        # Timer de renderizado rápido (10 ms)
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.read_udp)
        self.timer.start(10)

    def read_udp(self):
        data = None
        while True:
            try:
                packet, _ = self.sock.recvfrom(262144)  # Buffer de lectura más grande para soportar FFTs grandes
                data = packet
            except BlockingIOError:
                break
            except Exception as e:
                print(f"Error UDP: {e}")
                break

        if data is None:
            return

        # El header tiene 4 floats (16 bytes): center_freq, sample_rate, fft_size, wave_size
        if len(data) < 16:
            return

        header = np.frombuffer(data[:16], dtype=np.float32)
        center_freq = header[0]
        sample_rate = header[1]
        fft_size = int(header[2])
        wave_size = int(header[3])

        # Verificar que el tamaño total del paquete sea correcto
        # Header (16 bytes) + (fft_size * 2 + wave_size * 2) * 4 bytes
        expected_size = 16 + (fft_size * 2 + wave_size * 2) * 4
        if len(data) != expected_size:
            return

        # Desempaquetar los arrays
        payload = np.frombuffer(data[16:], dtype=np.float32)
        
        # Segmentar los datos
        spec_raw = payload[0 : fft_size]
        spec_filt = payload[fft_size : 2 * fft_size]
        amp_raw = payload[2 * fft_size : 2 * fft_size + wave_size]
        amp_filt = payload[2 * fft_size + wave_size : 2 * fft_size + 2 * wave_size]

        # Calcular eje de frecuencias en MHz
        fs_mhz = sample_rate / 1_000_000.0
        freqs = np.linspace(center_freq - fs_mhz / 2, center_freq + fs_mhz / 2, fft_size)

        # Actualizar curvas
        self.curve_spec_raw.setData(freqs, spec_raw)
        self.curve_spec_filt.setData(freqs, spec_filt)
        self.curve_amp_raw.setData(amp_raw)
        self.curve_amp_filt.setData(amp_filt)

    def closeEvent(self, event):
        self.sock.close()
        event.accept()

def launch_gpu_monitor():
    """Lanza este script como un proceso independiente para no bloquear el bucle de Flet"""
    import subprocess
    script_path = os.path.abspath(__file__)
    python_exe = sys.executable
    subprocess.Popen([python_exe, script_path], creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS)

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    win = DualMonitorWindow()
    win.show()
    sys.exit(app.exec())
