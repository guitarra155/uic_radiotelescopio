import sys
import os
import socket
import numpy as np
import pyqtgraph as pg
from PyQt6 import QtWidgets, QtCore, QtGui

class DualMonitorWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Monitoreo Dual Acelerado por GPU — Radiotelescopio")
        self.resize(1280, 720)
        
        # Color del tema
        self.setStyleSheet("""
            QMainWindow {
                background-color: #0b1319;
            }
            QWidget {
                color: #e2e8f0;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 13px;
            }
            QGroupBox {
                border: 1px solid #1e293b;
                border-radius: 6px;
                margin-top: 15px;
                font-weight: bold;
                color: #38bdf8;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QLabel {
                color: #94a3b8;
            }
            QLineEdit, QSpinBox, QDoubleSpinBox {
                background-color: #0f172a;
                border: 1px solid #334155;
                border-radius: 4px;
                padding: 4px;
                color: #f1f5f9;
            }
            QLineEdit:focus, QSpinBox:focus {
                border-color: #0ea5e9;
            }
            QCheckBox {
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 1px solid #334155;
                border-radius: 3px;
                background-color: #0f172a;
            }
            QCheckBox::indicator:checked {
                background-color: #0ea5e9;
                border-color: #0ea5e9;
            }
            QPushButton {
                background-color: #0284c7;
                border: none;
                border-radius: 4px;
                color: white;
                padding: 6px 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0369a1;
            }
        """)

        # Configuración inicial de pyqtgraph
        pg.setConfigOption('background', '#0b1319')
        pg.setConfigOption('foreground', '#94a3b8')

        # Widget principal con splitter para dividir gráficas de la barra lateral
        main_widget = QtWidgets.QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QtWidgets.QHBoxLayout(main_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)

        # ── CONTENEDOR DE GRÁFICAS (Izquierda) ──
        grid_widget = QtWidgets.QWidget()
        grid_layout = QtWidgets.QGridLayout(grid_widget)
        grid_layout.setContentsMargins(0, 0, 0, 0)
        grid_layout.setSpacing(8)

        # 1. Espectro RAW
        self.plot_spec_raw = pg.PlotWidget(title="<span style='color: #00D2FF; font-weight: bold; font-size: 14px;'>ESPECTRO ORIGINAL</span>")
        self.plot_spec_raw.setLabel('left', 'Potencia', units='dBm')
        self.plot_spec_raw.setLabel('bottom', 'Frecuencia', units='MHz')
        self.plot_spec_raw.showGrid(x=True, y=True, alpha=0.15)
        self.curve_spec_raw = self.plot_spec_raw.plot(pen=pg.mkPen('#00D2FF', width=1.5))
        grid_layout.addWidget(self.plot_spec_raw, 0, 0)

        # 2. Espectro Filtrado
        self.plot_spec_filt = pg.PlotWidget(title="<span style='color: #3FD18D; font-weight: bold; font-size: 14px;'>ESPECTRO FILTRADO</span>")
        self.plot_spec_filt.setLabel('left', 'Potencia', units='dBm')
        self.plot_spec_filt.setLabel('bottom', 'Frecuencia', units='MHz')
        self.plot_spec_filt.showGrid(x=True, y=True, alpha=0.15)
        self.curve_spec_filt = self.plot_spec_filt.plot(pen=pg.mkPen('#3FD18D', width=1.5))
        grid_layout.addWidget(self.plot_spec_filt, 0, 1)

        # Sync ejes X e Y del espectro
        self.plot_spec_filt.setXLink(self.plot_spec_raw)
        self.plot_spec_filt.setYLink(self.plot_spec_raw)

        # 3. Amplitud RAW
        self.plot_amp_raw = pg.PlotWidget(title="<span style='color: #00D2FF; font-weight: bold; font-size: 14px;'>AMPLITUD ORIGINAL</span>")
        self.plot_amp_raw.setLabel('left', 'Amplitud')
        self.plot_amp_raw.showGrid(x=True, y=True, alpha=0.15)
        self.curve_amp_raw_i = self.plot_amp_raw.plot(pen=pg.mkPen('#00D2FF', width=1.0))
        self.curve_amp_raw_q = self.plot_amp_raw.plot(pen=pg.mkPen('#E040FB', width=1.0))
        grid_layout.addWidget(self.plot_amp_raw, 1, 0)

        # 4. Amplitud Filtrada
        self.plot_amp_filt = pg.PlotWidget(title="<span style='color: #FFB347; font-weight: bold; font-size: 14px;'>AMPLITUD FILTRADA (MA)</span>")
        self.plot_amp_filt.setLabel('left', 'Amplitud')
        self.plot_amp_filt.showGrid(x=True, y=True, alpha=0.15)
        self.curve_amp_filt_i = self.plot_amp_filt.plot(pen=pg.mkPen('#FFB347', width=1.0))
        self.curve_amp_filt_q = self.plot_amp_filt.plot(pen=pg.mkPen('#E040FB', width=1.0))
        grid_layout.addWidget(self.plot_amp_filt, 1, 1)

        splitter.addWidget(grid_widget)

        # ── PANEL DE CONFIGURACIÓN (Derecha) ──
        self.sidebar = QtWidgets.QWidget()
        self.sidebar.setMaximumWidth(320)
        self.sidebar.setMinimumWidth(260)
        sidebar_layout = QtWidgets.QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(10, 0, 10, 0)
        
        title_lbl = QtWidgets.QLabel("CONFIGURACIÓN DE MONITOREO")
        title_lbl.setStyleSheet("font-size: 15px; font-weight: bold; color: #f8fafc; margin-bottom: 10px;")
        sidebar_layout.addWidget(title_lbl)

        # 1. Filtro Media Móvil
        filter_group = QtWidgets.QGroupBox("FILTRO MEDIA MÓVIL")
        filter_layout = QtWidgets.QVBoxLayout(filter_group)
        self.chk_ma_enabled = QtWidgets.QCheckBox("Activar Filtro")
        self.chk_ma_enabled.setChecked(True)
        self.chk_ma_enabled.toggled.connect(self.send_ma_enabled)
        filter_layout.addWidget(self.chk_ma_enabled)
        
        n_layout = QtWidgets.QHBoxLayout()
        n_layout.addWidget(QtWidgets.QLabel("Ventana (N):"))
        self.spin_ma_samples = QtWidgets.QSpinBox()
        self.spin_ma_samples.setRange(1, 1000)
        self.spin_ma_samples.setValue(4)
        self.spin_ma_samples.valueChanged.connect(self.send_ma_samples)
        n_layout.addWidget(self.spin_ma_samples)
        filter_layout.addLayout(n_layout)
        sidebar_layout.addWidget(filter_group)

        # 2. Configuración de Ejes de Espectro
        spec_group = QtWidgets.QGroupBox("LÍMITES DE ESPECTRO")
        spec_layout = QtWidgets.QVBoxLayout(spec_group)
        
        self.chk_spec_autoy = QtWidgets.QCheckBox("Auto Escala Y")
        self.chk_spec_autoy.setChecked(False)
        self.chk_spec_autoy.toggled.connect(self.toggle_spec_autoy)
        spec_layout.addWidget(self.chk_spec_autoy)
        
        ymin_layout = QtWidgets.QHBoxLayout()
        ymin_layout.addWidget(QtWidgets.QLabel("Y Mín (dBm):"))
        self.spin_spec_ymin = QtWidgets.QDoubleSpinBox()
        self.spin_spec_ymin.setRange(-200, 0)
        self.spin_spec_ymin.setValue(-150)
        self.spin_spec_ymin.valueChanged.connect(self.send_spec_limits)
        ymin_layout.addWidget(self.spin_spec_ymin)
        spec_layout.addLayout(ymin_layout)
        
        ymax_layout = QtWidgets.QHBoxLayout()
        ymax_layout.addWidget(QtWidgets.QLabel("Y Máx (dBm):"))
        self.spin_spec_ymax = QtWidgets.QDoubleSpinBox()
        self.spin_spec_ymax.setRange(-200, 0)
        self.spin_spec_ymax.setValue(-40)
        self.spin_spec_ymax.valueChanged.connect(self.send_spec_limits)
        ymax_layout.addWidget(self.spin_spec_ymax)
        spec_layout.addLayout(ymax_layout)
        
        sidebar_layout.addWidget(spec_group)

        # 3. Configuración de Ejes de Amplitud
        amp_group = QtWidgets.QGroupBox("LÍMITES DE AMPLITUD")
        amp_layout = QtWidgets.QVBoxLayout(amp_group)
        
        self.chk_amp_autoy = QtWidgets.QCheckBox("Auto Escala Y")
        self.chk_amp_autoy.setChecked(True)
        self.chk_amp_autoy.toggled.connect(self.toggle_amp_autoy)
        amp_layout.addWidget(self.chk_amp_autoy)
        
        aymin_layout = QtWidgets.QHBoxLayout()
        aymin_layout.addWidget(QtWidgets.QLabel("Y Mín:"))
        self.spin_amp_ymin = QtWidgets.QDoubleSpinBox()
        self.spin_amp_ymin.setRange(-10, 10)
        self.spin_amp_ymin.setValue(-0.5)
        self.spin_amp_ymin.valueChanged.connect(self.send_amp_limits)
        aymin_layout.addWidget(self.spin_amp_ymin)
        amp_layout.addLayout(aymin_layout)
        
        aymax_layout = QtWidgets.QHBoxLayout()
        aymax_layout.addWidget(QtWidgets.QLabel("Y Máx:"))
        self.spin_amp_ymax = QtWidgets.QDoubleSpinBox()
        self.spin_amp_ymax.setRange(-10, 10)
        self.spin_amp_ymax.setValue(0.5)
        self.spin_amp_ymax.valueChanged.connect(self.send_amp_limits)
        aymax_layout.addWidget(self.spin_amp_ymax)
        amp_layout.addLayout(aymax_layout)
        
        sidebar_layout.addWidget(amp_group)
        
        sidebar_layout.addStretch()
        
        # Botón cerrar
        btn_close = QtWidgets.QPushButton("Regresar a la Plataforma")
        btn_close.clicked.connect(self.close)
        sidebar_layout.addWidget(btn_close)
        
        splitter.addWidget(self.sidebar)

        # UDP Sockets
        self.sock_data = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock_data.bind(("127.0.0.1", 9999))
        self.sock_data.setblocking(False)
        
        self.sock_cmd = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # Timer de refresco de datos (16ms = 60 FPS)
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.read_udp_data)
        self.timer.start(16)

        # Aplicar límites iniciales
        self.toggle_spec_autoy()
        self.toggle_amp_autoy()

    def send_cmd(self, msg: str):
        try:
            self.sock_cmd.sendto(msg.encode('utf-8'), ("127.0.0.1", 9998))
        except:
            pass

    def send_ma_enabled(self):
        val = self.chk_ma_enabled.isChecked()
        self.send_cmd(f"cmd:set_ma_enabled {val}")

    def send_ma_samples(self):
        val = self.spin_ma_samples.value()
        self.send_cmd(f"cmd:set_ma_samples {val}")

    def toggle_spec_autoy(self):
        auto = self.chk_spec_autoy.isChecked()
        self.spin_spec_ymin.setEnabled(not auto)
        self.spin_spec_ymax.setEnabled(not auto)
        if auto:
            self.plot_spec_raw.enableAutoRange(axis=pg.ViewBox.YAxis)
        else:
            self.send_spec_limits()
        self.send_cmd(f"cmd:set_chart_config mon_raw_spec auto_y {auto}")
        self.send_cmd(f"cmd:set_chart_config mon_filt_spec auto_y {auto}")

    def send_spec_limits(self):
        ymin = self.spin_spec_ymin.value()
        ymax = self.spin_spec_ymax.value()
        if ymin < ymax:
            self.plot_spec_raw.setYRange(ymin, ymax)
            self.send_cmd(f"cmd:set_chart_config mon_raw_spec ymin {ymin}")
            self.send_cmd(f"cmd:set_chart_config mon_raw_spec ymax {ymax}")

    def toggle_amp_autoy(self):
        auto = self.chk_amp_autoy.isChecked()
        self.spin_amp_ymin.setEnabled(not auto)
        self.spin_amp_ymax.setEnabled(not auto)
        if auto:
            self.plot_amp_raw.enableAutoRange(axis=pg.ViewBox.YAxis)
            self.plot_amp_filt.enableAutoRange(axis=pg.ViewBox.YAxis)
        else:
            self.send_amp_limits()
        self.send_cmd(f"cmd:set_chart_config mon_raw_amp auto_y {auto}")
        self.send_cmd(f"cmd:set_chart_config mon_filt_amp auto_y {auto}")

    def send_amp_limits(self):
        ymin = self.spin_amp_ymin.value()
        ymax = self.spin_amp_ymax.value()
        if ymin < ymax:
            self.plot_amp_raw.setYRange(ymin, ymax)
            self.plot_amp_filt.setYRange(ymin, ymax)
            self.send_cmd(f"cmd:set_chart_config mon_raw_amp ymin {ymin}")
            self.send_cmd(f"cmd:set_chart_config mon_raw_amp ymax {ymax}")

    def read_udp_data(self):
        data = None
        while True:
            try:
                packet, _ = self.sock_data.recvfrom(262144)
                data = packet
            except BlockingIOError:
                break
            except Exception:
                break

        if data is None or len(data) < 200:
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
        self.sock_data.close()
        self.sock_cmd.close()
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
    win.show()
    sys.exit(app.exec())
