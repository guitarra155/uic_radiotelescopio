import sys
import os
import socket
import numpy as np
import pyqtgraph as pg
from PyQt6 import QtWidgets, QtCore
import ctypes

# Estructura RECT para Win32
class RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long)
    ]

class DualMonitorWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Monitor Acelerado por GPU (SDR++)")
        
        # Hacerla sin bordes (Frameless) y siempre visible sobre Flet (WindowStaysOnTopHint)
        self.setWindowFlags(
            QtCore.Qt.WindowType.FramelessWindowHint | 
            QtCore.Qt.WindowType.WindowStaysOnTopHint |
            QtCore.Qt.WindowType.SubWindow
        )
        
        # Tema Oscuro Premium
        pg.setConfigOption('background', '#0b1319')
        pg.setConfigOption('foreground', '#888888')

        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        layout = QtWidgets.QGridLayout(central)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(10)

        # 1. Espectro RAW
        self.plot_spec_raw = pg.PlotWidget(title="<span style='color: #00D2FF; font-weight: bold;'>ESPECTRO ORIGINAL</span>")
        self.plot_spec_raw.setLabel('left', 'Potencia', units='dBm')
        self.plot_spec_raw.setLabel('bottom', 'Frecuencia', units='MHz')
        self.plot_spec_raw.setYRange(-150, -40)
        self.plot_spec_raw.showGrid(x=True, y=True, alpha=0.15)
        self.curve_spec_raw = self.plot_spec_raw.plot(pen=pg.mkPen('#00D2FF', width=1.5))
        layout.addWidget(self.plot_spec_raw, 0, 0)

        # 2. Espectro Filtrado
        self.plot_spec_filt = pg.PlotWidget(title="<span style='color: #3FD18D; font-weight: bold;'>ESPECTRO FILTRADO</span>")
        self.plot_spec_filt.setLabel('left', 'Potencia', units='dBm')
        self.plot_spec_filt.setLabel('bottom', 'Frecuencia', units='MHz')
        self.plot_spec_filt.showGrid(x=True, y=True, alpha=0.15)
        self.curve_spec_filt = self.plot_spec_filt.plot(pen=pg.mkPen('#3FD18D', width=1.5))
        layout.addWidget(self.plot_spec_filt, 0, 1)

        # Sync ejes X e Y
        self.plot_spec_filt.setXLink(self.plot_spec_raw)
        self.plot_spec_filt.setYLink(self.plot_spec_raw)

        # 3. Amplitud Temporal RAW
        self.plot_amp_raw = pg.PlotWidget(title="<span style='color: #00D2FF; font-weight: bold;'>AMPLITUD ORIGINAL</span>")
        self.plot_amp_raw.setLabel('left', 'Amplitud')
        self.plot_amp_raw.setYRange(-0.5, 0.5)
        self.plot_amp_raw.showGrid(x=True, y=True, alpha=0.15)
        self.curve_amp_raw_i = self.plot_amp_raw.plot(pen=pg.mkPen('#00D2FF', width=1.0))
        self.curve_amp_raw_q = self.plot_amp_raw.plot(pen=pg.mkPen('#E040FB', width=1.0))
        layout.addWidget(self.plot_amp_raw, 1, 0)

        # 4. Amplitud Temporal Filtrada
        self.plot_amp_filt = pg.PlotWidget(title="<span style='color: #FFB347; font-weight: bold;'>AMPLITUD FILTRADA (MA)</span>")
        self.plot_amp_filt.setLabel('left', 'Amplitud')
        self.plot_amp_filt.setYRange(-0.5, 0.5)
        self.plot_amp_filt.showGrid(x=True, y=True, alpha=0.15)
        self.curve_amp_filt_i = self.plot_amp_filt.plot(pen=pg.mkPen('#FFB347', width=1.0))
        self.curve_amp_filt_q = self.plot_amp_filt.plot(pen=pg.mkPen('#E040FB', width=1.0))
        layout.addWidget(self.plot_amp_filt, 1, 1)

        # Socket UDP para datos
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("127.0.0.1", 9999))
        self.sock.setblocking(False)

        self.flet_hwnd = None
        self.is_visible_state = False

        # Timer rápido (16ms = 60 FPS) para datos y auto-seguimiento de ventana
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.loop_tick)
        self.timer.start(16)

    def find_flet_hwnd(self):
        user32 = ctypes.windll.user32
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
        self.flet_hwnd = hwnd_out[0]

    def loop_tick(self):
        # 1. Leer socket
        self.read_udp()

        # 2. Seguir la ventana de Flet en pantalla
        if not self.is_visible_state:
            return

        if not self.flet_hwnd:
            self.find_flet_hwnd()
            if not self.flet_hwnd:
                return

        user32 = ctypes.windll.user32
        
        # Verificar si Flet está minimizado o activo
        if user32.IsIconic(self.flet_hwnd):
            if self.isVisible():
                self.hide()
            return
        elif not self.isVisible() and self.is_visible_state:
            self.show()

        # Obtener coordenadas de la ventana de Flet
        rect = RECT()
        user32.GetWindowRect(self.flet_hwnd, ctypes.byref(rect))
        
        w_flet = rect.right - rect.left
        h_flet = rect.bottom - rect.top

        # Estimar offsets de layout basándonos en la estructura de Flet
        # Sidebar colapsado: 52px, panel derecho: 320px
        # Header: ~56px, Footer: ~25px
        # Bordes de ventana Windows típica: 8px izquierda/derecha, 30px arriba (título)
        border_x = 8
        title_y = 31
        
        sidebar_w = 52
        right_panel_w = 320
        header_h = 56
        footer_h = 25

        x = rect.left + border_x + sidebar_w + 10
        y = rect.top + title_y + header_h + 10
        w = w_flet - (border_x * 2) - sidebar_w - right_panel_w - 20
        h = h_flet - title_y - border_x - header_h - footer_h - 20

        # Si el tamaño cambia o la ventana se mueve, ajustar
        self.setGeometry(int(x), int(y), int(w), int(h))

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

        # Comandos de control
        if len(data) < 200:
            try:
                text = data.decode('utf-8')
                if text.startswith("cmd:"):
                    cmd = text.split(" ")[0]
                    if cmd == "cmd:show":
                        self.is_visible_state = True
                        self.show()
                    elif cmd == "cmd:hide":
                        self.is_visible_state = False
                        self.hide()
            except:
                pass
            return

        # Header (16 bytes)
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

        # Actualizar curvas
        self.curve_spec_raw.setData(freqs, spec_raw)
        self.curve_spec_filt.setData(freqs, spec_filt)
        
        # En la amplitud temporal de PyQtGraph dibujamos parte Real (I) e Imaginaria (Q) por separado
        # El tamaño recibido es wave_size, pero en dsp_engine decimamos I y Q de forma sintonizada
        self.curve_amp_raw_i.setData(amp_raw)
        # Para simplificar y simular Q, mostramos un desfase o calculamos magnitud
        # En dsp_engine enviamos solo Real de IQ raw y Real de IQ filtrado. 
        # Modifiquemos dsp_engine para que envíe I y Q reales, o grafiquemos solo una.
        # Grafiquemos por ahora la parte Real. 
        # Para pintar Q también, use y_raw.imag en dsp_engine.
        
        self.curve_amp_filt_i.setData(amp_filt)

    def closeEvent(self, event):
        self.sock.close()
        event.accept()

def launch_gpu_monitor():
    import subprocess
    script_path = os.path.abspath(__file__)
    python_exe = sys.executable
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(0.1)
    try:
        s.bind(("127.0.0.1", 9999))
        s.close()
        subprocess.Popen([python_exe, script_path], creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS)
    except:
        s.close()

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    win = DualMonitorWindow()
    win.hide()
    sys.exit(app.exec())
