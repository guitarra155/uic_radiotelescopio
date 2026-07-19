import sys
import os
import socket
import numpy as np
import pyqtgraph as pg
from PyQt6 import QtWidgets, QtCore
import ctypes

class DualMonitorWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Monitor Acelerado por GPU (SDR++)")
        self.resize(800, 600)
        
        # Tema Oscuro
        pg.setConfigOption('background', '#0b1319')
        pg.setConfigOption('foreground', '#888888')

        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        layout = QtWidgets.QGridLayout(central)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

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

        # Socket UDP para recibir datos del motor DSP y comandos de control
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("127.0.0.1", 9999))
        self.sock.setblocking(False)

        # Timer de renderizado rápido (10 ms)
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.read_udp)
        self.timer.start(10)

        # Buscar e incrustar la ventana en Flet (Win32)
        self.embedded = False
        QtCore.QTimer.singleShot(100, self.try_embed)

    def try_embed(self):
        """Intenta encontrar la ventana de Flet e incrustarse como hijo"""
        if self.embedded:
            return
            
        user32 = ctypes.windll.user32
        
        # Encontrar HWND de Flet
        hwnd_out = [0]
        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_void_p)
        
        def enum_cb(hwnd, extra):
            length = user32.GetWindowTextLengthW(hwnd)
            buff = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buff, length + 1)
            title = buff.value
            if title.startswith("Procesamiento DSP"):
                hwnd_out[0] = hwnd
                return False
            return True
            
        user32.EnumWindows(WNDENUMPROC(enum_cb), 0)
        flet_hwnd = hwnd_out[0]
        
        if flet_hwnd:
            qt_hwnd = int(self.winId())
            
            # Cambiar estilo a ventana hija (WS_CHILD = 0x40000000)
            GWL_STYLE = -16
            WS_CHILD = 0x40000000
            WS_POPUP = 0x80000000
            WS_CAPTION = 0x00C00000
            WS_THICKFRAME = 0x00040000
            
            style = user32.GetWindowLongW(qt_hwnd, GWL_STYLE)
            style = (style | WS_CHILD) & ~WS_POPUP & ~WS_CAPTION & ~WS_THICKFRAME
            user32.SetWindowLongW(qt_hwnd, GWL_STYLE, style)
            
            # Establecer Flet como padre
            user32.SetParent(qt_hwnd, flet_hwnd)
            self.embedded = True
            
            # Forzar actualización
            user32.SetWindowPos(qt_hwnd, 0, 0, 0, 0, 0, 0x0027) # SWP_FRAMECHANGED | SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER

    def read_udp(self):
        data = None
        while True:
            try:
                packet, _ = self.sock.recvfrom(262144)
                data = packet
            except BlockingIOError:
                break
            except Exception as e:
                break

        if data is None:
            return

        # ── Manejo de Comandos de Control (Texto Corto) ──
        if len(data) < 200:
            try:
                text = data.decode('utf-8')
                if text.startswith("cmd:"):
                    parts = text.split(" ")
                    cmd = parts[0]
                    if cmd == "cmd:show":
                        self.show()
                        self.try_embed() # Re-intentar incrustar por si Flet cambió
                    elif cmd == "cmd:hide":
                        self.hide()
                    elif cmd == "cmd:layout" and len(parts) == 5:
                        x = int(parts[1])
                        y = int(parts[2])
                        w = int(parts[3])
                        h = int(parts[4])
                        # Mover y redimensionar ventana
                        self.setGeometry(x, y, w, h)
                    return
            except:
                pass
            return

        # El header tiene 4 floats (16 bytes)
        if len(data) < 16:
            return

        header = np.frombuffer(data[:16], dtype=np.float32)
        center_freq = header[0]
        sample_rate = header[1]
        fft_size = int(header[2])
        wave_size = int(header[3])

        expected_size = 16 + (fft_size * 2 + wave_size * 2) * 4
        if len(data) != expected_size:
            return

        payload = np.frombuffer(data[16:], dtype=np.float32)
        
        spec_raw = payload[0 : fft_size]
        spec_filt = payload[fft_size : 2 * fft_size]
        amp_raw = payload[2 * fft_size : 2 * fft_size + wave_size]
        amp_filt = payload[2 * fft_size + wave_size : 2 * fft_size + 2 * wave_size]

        fs_mhz = sample_rate / 1_000_000.0
        freqs = np.linspace(center_freq - fs_mhz / 2, center_freq + fs_mhz / 2, fft_size)

        self.curve_spec_raw.setData(freqs, spec_raw)
        self.curve_spec_filt.setData(freqs, spec_filt)
        self.curve_amp_raw.setData(amp_raw)
        self.curve_amp_filt.setData(amp_filt)

    def closeEvent(self, event):
        self.sock.close()
        event.accept()

def launch_gpu_monitor():
    """Lanza este script como un proceso independiente si no está ya corriendo"""
    import subprocess
    script_path = os.path.abspath(__file__)
    python_exe = sys.executable
    # Intentar enviar un ping UDP en el puerto 9999 para saber si ya está abierto
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(0.1)
    try:
        # Si logramos bindiar, significa que NO está corriendo
        s.bind(("127.0.0.1", 9999))
        s.close()
        # Iniciar proceso
        subprocess.Popen([python_exe, script_path], creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS)
    except:
        # Ya está corriendo
        s.close()

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    win = DualMonitorWindow()
    # Empezar oculta hasta que Flet mande la orden de mostrar y redimensionar
    win.hide()
    sys.exit(app.exec())
