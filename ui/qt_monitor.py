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
        
        # Frameless window
        self.setWindowFlags(QtCore.Qt.WindowType.FramelessWindowHint)
        
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
        self.embedded = False
        self.is_visible_state = False

        # Timer rápido (16ms = 60 FPS) para datos y ajuste
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

    def try_embed(self):
        """Incrusta la ventana Qt como hija real de Flet mediante Win32 y aplica WS_CLIPCHILDREN"""
        if self.embedded or not self.flet_hwnd:
            return
            
        user32 = ctypes.windll.user32
        qt_hwnd = int(self.winId())
        
        # 1. Cambiar estilo de la ventana de Qt a ventana hija (WS_CHILD = 0x40000000)
        GWL_STYLE = -16
        WS_CHILD = 0x40000000
        WS_POPUP = 0x80000000
        WS_CAPTION = 0x00C00000
        WS_THICKFRAME = 0x00040000
        
        style = user32.GetWindowLongW(qt_hwnd, GWL_STYLE)
        style = (style | WS_CHILD) & ~WS_POPUP & ~WS_CAPTION & ~WS_THICKFRAME
        user32.SetWindowLongW(qt_hwnd, GWL_STYLE, style)
        
        # 2. Forzar al Flet parent a recortar el pintado en la zona de su hijo (WS_CLIPCHILDREN = 0x02000000)
        # Esto previene que el motor de pintado de Flet dibuje sobre la ventana de Qt
        WS_CLIPCHILDREN = 0x02000000
        parent_style = user32.GetWindowLongW(self.flet_hwnd, GWL_STYLE)
        user32.SetWindowLongW(self.flet_hwnd, GWL_STYLE, parent_style | WS_CLIPCHILDREN)
        
        # 3. Establecer Flet como padre
        user32.SetParent(qt_hwnd, self.flet_hwnd)
        self.embedded = True
        
        # Forzar refresco
        user32.SetWindowPos(qt_hwnd, 0, 0, 0, 0, 0, 0x0027)

    def loop_tick(self):
        self.read_udp()

        if not self.flet_hwnd:
            self.find_flet_hwnd()
            if not self.flet_hwnd:
                return

        if not self.embedded:
            self.try_embed()

        user32 = ctypes.windll.user32
        
        # Si la pestaña no está activa, ocultamos la ventana hija
        if not self.is_visible_state:
            if self.isVisible():
                self.hide()
            return
        
        # Si Flet está minimizado, ocultamos
        if user32.IsIconic(self.flet_hwnd):
            if self.isVisible():
                self.hide()
            return
        elif not self.isVisible() and self.is_visible_state:
            self.show()

        # Obtener el tamaño del área cliente interna de Flet
        rect = RECT()
        user32.GetClientRect(self.flet_hwnd, ctypes.byref(rect))
        w_client = rect.right - rect.left
        h_client = rect.bottom - rect.top

        # Escala DPI de Flet
        dpi = user32.GetDpiForWindow(self.flet_hwnd)
        scale = dpi / 96.0

        sidebar_w = int(52 * scale)
        right_panel_w = int(320 * scale)
        header_h = int(56 * scale)
        footer_h = int(25 * scale)

        # Coordenadas relativas al área cliente de Flet
        x = sidebar_w + int(10 * scale)
        y = header_h + int(10 * scale)
        w = w_client - sidebar_w - right_panel_w - int(20 * scale)
        h = h_client - header_h - footer_h - int(20 * scale)

        logical_x = x / scale
        logical_y = y / scale
        logical_w = w / scale
        logical_h = h / scale

        # Posicionar ventana de Qt dentro de Flet
        self.setGeometry(int(logical_x), int(logical_y), int(logical_w), int(logical_h))

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
        self.curve_amp_raw_i.setData(amp_raw)
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
