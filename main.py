"""
Plataforma de Procesamiento Digital de Señales de Radiotelescopios
Flet 0.82 | Matplotlib | NumPy  |  1420.40 MHz (Línea HI)
"""

import flet as ft
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
import io, base64, math

matplotlib.use("Agg")

# ═══════════════════════════════════════════════════════
# PALETA DE COLORES
# ═══════════════════════════════════════════════════════
DARK_BG      = "#0D1117"
PANEL_BG     = "#161B22"
ACCENT_CYAN  = "#00D2FF"
ACCENT_GREEN = "#3FD18D"
ACCENT_RED   = "#FF4C4C"
ACCENT_AMBER = "#FFB347"
TEXT_MAIN    = "#E6EDF3"
TEXT_MUTED   = "#8B949E"
BORDER_COL   = "#30363D"
MPL_BG       = "#0D1117"
MPL_AXBG     = "#161B22"
MPL_GRID     = "#21262D"
MPL_TEXT     = "#E6EDF3"


# ═══════════════════════════════════════════════════════
# UTILIDADES MATPLOTLIB → BASE64
# ═══════════════════════════════════════════════════════
def fig_to_b64(fig: Figure) -> str:
    """Retorna una data URI PNG lista para usar en ft.Image(src=...)."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=96)
    buf.seek(0)
    enc = base64.b64encode(buf.read()).decode()
    buf.close()
    plt.close(fig)
    return f"data:image/png;base64,{enc}"


def style_ax(ax, title="", xlabel="", ylabel=""):
    ax.set_facecolor(MPL_AXBG)
    ax.tick_params(colors=MPL_TEXT, labelsize=8)
    for sp in ax.spines.values():
        sp.set_edgecolor(BORDER_COL)
    ax.set_title(title, color=ACCENT_CYAN, fontsize=9, pad=6)
    ax.set_xlabel(xlabel, color=TEXT_MUTED, fontsize=8)
    ax.set_ylabel(ylabel, color=TEXT_MUTED, fontsize=8)
    ax.grid(True, color=MPL_GRID, linestyle="--", linewidth=0.5, alpha=0.6)


# ═══════════════════════════════════════════════════════
# GRÁFICOS SIMULADOS
# ═══════════════════════════════════════════════════════
def chart_amplitude() -> str:
    fig, ax = plt.subplots(figsize=(7, 2.8))
    fig.patch.set_facecolor(MPL_BG)
    t = np.linspace(0, 10, 1000)
    sig = (0.5 * np.sin(2*np.pi*1.5*t) + 0.3*np.sin(2*np.pi*4.2*t+0.8)
           + np.random.normal(0, 0.12, len(t)))
    m = (t > 4.5) & (t < 5.5)
    sig[m] += 1.8 * np.sin(2*np.pi*5*t[m])
    ax.plot(t, sig, color=ACCENT_CYAN, linewidth=0.9, alpha=0.85)
    ax.fill_between(t, sig, alpha=0.15, color=ACCENT_CYAN)
    ax.axvline(5.0, color=ACCENT_RED, linestyle="--", linewidth=0.9,
               alpha=0.85, label="Pico RFI")
    ax.legend(fontsize=7, facecolor=MPL_AXBG, edgecolor=BORDER_COL, labelcolor=MPL_TEXT)
    style_ax(ax, "Amplitud vs Tiempo", "Tiempo (s)", "Amplitud (dBm)")
    fig.tight_layout(pad=0.6)
    return fig_to_b64(fig)


def chart_spectrum() -> str:
    fig, ax = plt.subplots(figsize=(7, 2.8))
    fig.patch.set_facecolor(MPL_BG)
    freq = np.linspace(1418, 1423, 500)
    hi   = 2.5 * np.exp(-0.5 * ((freq - 1420.40)/0.15)**2)
    spec = hi + np.random.normal(0, 0.12, len(freq)) - 80
    ax.plot(freq, spec, color=ACCENT_GREEN, linewidth=1.0)
    ax.fill_between(freq, spec, min(spec), alpha=0.2, color=ACCENT_GREEN)
    ax.axvline(1420.40, color=ACCENT_AMBER, linestyle="--", linewidth=1.0,
               alpha=0.9, label="HI 1420.40 MHz")
    ax.legend(fontsize=7, facecolor=MPL_AXBG, edgecolor=BORDER_COL, labelcolor=MPL_TEXT)
    style_ax(ax, "Espectro de Frecuencia", "Frecuencia (MHz)", "Potencia (dBm)")
    fig.tight_layout(pad=0.6)
    return fig_to_b64(fig)


def chart_spectrogram() -> str:
    fig, ax = plt.subplots(figsize=(10, 5))
    fig.patch.set_facecolor(MPL_BG)
    np.random.seed(42)
    T, F = 250, 200
    data = np.random.normal(-85, 4, (F, T))
    g = np.exp(-0.5 * ((np.linspace(0,1,25)-0.5)/0.15)**2)
    data[90:115, :] += 18 * g[:, np.newaxis]
    data[40:55, 60:85]    += 22
    data[150:165, 170:200] += 15
    for i in range(T):
        r = max(0, min(F-1, 100+int(10*np.sin(2*np.pi*i/T))))
        data[r, i] += 8
    im = ax.imshow(data, aspect="auto", origin="lower",
                   extent=[0,10,1418,1423], cmap="inferno",
                   vmin=-95, vmax=-60, interpolation="bilinear")
    cb = fig.colorbar(im, ax=ax, shrink=0.9, pad=0.02)
    cb.set_label("Potencia (dBm)", color=MPL_TEXT, fontsize=9)
    cb.ax.yaxis.set_tick_params(color=MPL_TEXT)
    plt.setp(cb.ax.yaxis.get_ticklabels(), color=MPL_TEXT, fontsize=8)
    ax.axhline(1420.40, color=ACCENT_CYAN, linestyle="--", linewidth=1.2,
               alpha=0.85, label="HI 1420.40 MHz")
    ax.legend(fontsize=8, facecolor=MPL_AXBG, edgecolor=BORDER_COL,
              labelcolor=MPL_TEXT, loc="upper right")
    style_ax(ax, "Espectrograma Tiempo-Frecuencia (1418–1423 MHz)",
             "Tiempo (s)", "Frecuencia (MHz)")
    fig.tight_layout(pad=0.6)
    return fig_to_b64(fig)


def chart_histogram() -> str:
    fig, ax = plt.subplots(figsize=(5.5, 4.0))
    fig.patch.set_facecolor(MPL_BG)
    np.random.seed(7)
    noise   = np.random.normal(0, 1, 8000)
    skewed  = np.random.gamma(shape=2.5, scale=0.9, size=1500) + 1.5
    samples = np.concatenate([noise, skewed])
    ax.hist(samples, bins=70, density=True, color=ACCENT_CYAN,
            alpha=0.55, edgecolor=MPL_BG, linewidth=0.3, label="Distribución muestral")
    x = np.linspace(samples.min(), samples.max(), 300)
    gauss = (1/math.sqrt(2*math.pi)) * np.exp(-0.5*x**2)
    ax.plot(x, gauss, color=ACCENT_GREEN, linewidth=1.5, label="Gaussiana teórica")
    xp = np.linspace(0, 8, 300)
    g25 = 1.3293  # Γ(2.5)
    pdf = (xp**1.5 * np.exp(-xp/0.9)) / (0.9**2.5 * g25)
    ax.plot(xp+1.5, pdf*(1500/9500), color=ACCENT_AMBER, linewidth=1.5,
            linestyle="--", label="Señal HI (asimétrica)")
    ax.axvline(3.2, color=ACCENT_RED, linewidth=1.2, linestyle=":", label="Umbral anomalía")
    ax.legend(fontsize=7, facecolor=MPL_AXBG, edgecolor=BORDER_COL, labelcolor=MPL_TEXT)
    style_ax(ax, "Histograma de Amplitud", "Amplitud (σ)", "Densidad de prob.")
    fig.tight_layout(pad=0.6)
    return fig_to_b64(fig)


# ═══════════════════════════════════════════════════════
# HELPER: CONTENEDORES ESTILO PANEL
# ═══════════════════════════════════════════════════════
def border_all(width=1, color=BORDER_COL) -> ft.Border:
    s = ft.BorderSide(width, color)
    return ft.Border(top=s, right=s, bottom=s, left=s)


def panel(padding_val=18, **kwargs) -> ft.Container:
    return ft.Container(
        bgcolor=PANEL_BG,
        border_radius=12,
        border=border_all(),
        padding=ft.Padding(left=padding_val, top=padding_val,
                           right=padding_val, bottom=padding_val),
        **kwargs,
    )


def txt_field(label, value="", hint="") -> ft.TextField:
    return ft.TextField(
        label=label, value=value, hint_text=hint,
        color=TEXT_MAIN, bgcolor=DARK_BG,
        border_color=BORDER_COL, focused_border_color=ACCENT_CYAN,
        cursor_color=ACCENT_CYAN, border_radius=8, expand=True,
    )


# ═══════════════════════════════════════════════════════
# PESTAÑA 1 — Monitoreo y RFI
# ═══════════════════════════════════════════════════════
def build_monitoring(page: ft.Page) -> ft.Control:
    rfi_switch = ft.Switch(
        label="Mitigación Automática de RFI",
        value=False,
        active_color=ACCENT_GREEN,
        label_text_style=ft.TextStyle(color=TEXT_MAIN, size=13),
    )
    rfi_status = ft.Text("Estado: INACTIVO", color=ACCENT_RED, size=11,
                         weight=ft.FontWeight.W_600)

    def on_rfi(e):
        on = rfi_switch.value
        rfi_status.value = "Estado: ACTIVO" if on else "Estado: INACTIVO"
        rfi_status.color = ACCENT_GREEN if on else ACCENT_RED
        page.update()

    rfi_switch.on_change = on_rfi

    img_amp  = ft.Image(src=chart_amplitude(),  fit=ft.BoxFit.CONTAIN,
                        border_radius=8, expand=True)
    img_spec = ft.Image(src=chart_spectrum(),   fit=ft.BoxFit.CONTAIN,
                        border_radius=8, expand=True)

    graphs = ft.Column([
        ft.Container(content=img_amp,  expand=1, bgcolor=PANEL_BG,
                     border_radius=8, border=border_all(), padding=4),
        ft.Container(content=img_spec, expand=1, bgcolor=PANEL_BG,
                     border_radius=8, border=border_all(), padding=4),
    ], expand=True, spacing=10)

    side = panel(
        width=230,
        content=ft.Column([
            ft.Text("🛡️  Control RFI", color=ACCENT_CYAN, size=14,
                    weight=ft.FontWeight.BOLD),
            ft.Divider(color=BORDER_COL, height=14),
            rfi_switch,
            rfi_status,
            ft.Divider(color=BORDER_COL, height=14),
            ft.Text("Última detección:", color=TEXT_MUTED, size=11),
            ft.Text("12:43:07 UTC",      color=TEXT_MAIN,  size=11),
            ft.Divider(color=BORDER_COL, height=10),
            ft.Text("Eventos hoy:",      color=TEXT_MUTED, size=11),
            ft.Text("7 interferencias",  color=ACCENT_AMBER, size=11,
                    weight=ft.FontWeight.W_600),
            ft.Divider(color=BORDER_COL, height=10),
            ft.Text("Rango activo:",      color=TEXT_MUTED, size=11),
            ft.Text("1419.8–1421.0 MHz", color=TEXT_MAIN,  size=10),
        ], spacing=8),
    )

    return ft.Container(
        content=ft.Row([graphs, side], spacing=12, expand=True),
        expand=True,
        padding=ft.Padding(left=14, top=14, right=14, bottom=14),
    )


# ═══════════════════════════════════════════════════════
# PESTAÑA 2 — Espectrograma
# ═══════════════════════════════════════════════════════
def build_spectrogram(page: ft.Page) -> ft.Control:
    img = ft.Image(src=chart_spectrogram(), fit=ft.BoxFit.CONTAIN,
                   border_radius=10, expand=True)

    def sw(color): return ft.Container(width=14, height=14, bgcolor=color, border_radius=4)

    legend = ft.Row([
        sw(ACCENT_RED),   ft.Text("RFI Intenso",     color=TEXT_MAIN, size=10),
        sw(ACCENT_AMBER), ft.Text("Señal moderada",  color=TEXT_MAIN, size=10),
        sw("#3F51B5"),    ft.Text("Ruido base",      color=TEXT_MAIN, size=10),
        sw(ACCENT_CYAN),  ft.Text("HI 1420.40 MHz", color=TEXT_MAIN, size=10),
    ], spacing=8, alignment=ft.MainAxisAlignment.CENTER)

    return ft.Container(
        content=ft.Column([
            ft.Container(content=img, expand=True, bgcolor=PANEL_BG,
                         border_radius=10, border=border_all(), padding=6),
            legend,
        ], expand=True, spacing=8),
        expand=True,
        padding=ft.Padding(left=14, top=14, right=14, bottom=14),
    )


# ═══════════════════════════════════════════════════════
# PESTAÑA 3 — Estadística & Smart Trigger
# ═══════════════════════════════════════════════════════
def build_statistics(page: ft.Page) -> ft.Control:
    thresh = ft.TextField(
        label="Umbral de anomalía (%)", value="15",
        color=TEXT_MAIN, bgcolor=DARK_BG,
        border_color=BORDER_COL, focused_border_color=ACCENT_CYAN,
        cursor_color=ACCENT_CYAN, border_radius=8, width=200,
        keyboard_type=ft.KeyboardType.NUMBER,
    )
    stat_txt = ft.Text("Smart Trigger: INACTIVO", color=TEXT_MUTED,
                       size=12, weight=ft.FontWeight.W_600)
    active = [False]

    trigger_btn = ft.Button(
        content="⚡  Activar Smart Trigger",
        bgcolor=ACCENT_GREEN, color="#000000",
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)),
    )

    def on_trigger(e):
        active[0] = not active[0]
        if active[0]:
            stat_txt.value  = f"Smart Trigger: ACTIVO  (umbral={thresh.value}%)"
            stat_txt.color  = ACCENT_GREEN
            trigger_btn.content = "⛔  Desactivar Smart Trigger"
            trigger_btn.bgcolor = ACCENT_RED
        else:
            stat_txt.value  = "Smart Trigger: INACTIVO"
            stat_txt.color  = TEXT_MUTED
            trigger_btn.content = "⚡  Activar Smart Trigger"
            trigger_btn.bgcolor = ACCENT_GREEN
        page.update()

    trigger_btn.on_click = on_trigger

    img = ft.Image(src=chart_histogram(), fit=ft.BoxFit.CONTAIN,
                   border_radius=8, expand=True)

    stat_data = [("Media (σ)", "0.023", ACCENT_GREEN),
                 ("Std Dev",   "1.041", ACCENT_GREEN),
                 ("Kurtosis",  "3.87",  ACCENT_AMBER),
                 ("Sesgo",     "1.14",  ACCENT_AMBER)]

    stat_rows = [ft.Row([ft.Text(k, color=TEXT_MAIN, size=10, expand=1),
                          ft.Text(v, color=c, size=10, expand=1,
                                  weight=ft.FontWeight.W_600)])
                 for k, v, c in stat_data]

    side = panel(
        width=240,
        content=ft.Column([
            ft.Text("⚡  Smart Trigger", color=ACCENT_CYAN, size=14,
                    weight=ft.FontWeight.BOLD),
            ft.Divider(color=BORDER_COL, height=12),
            thresh,
            ft.Container(height=8),
            trigger_btn,
            ft.Container(height=6),
            stat_txt,
            ft.Divider(color=BORDER_COL, height=12),
            ft.Text("Estadísticas de sesión:", color=TEXT_MUTED, size=11),
            *stat_rows,
        ], spacing=8),
    )

    return ft.Container(
        content=ft.Row([
            ft.Container(content=img, expand=True, bgcolor=PANEL_BG,
                         border_radius=10, border=border_all(), padding=6),
            side,
        ], spacing=12, expand=True),
        expand=True,
        padding=ft.Padding(left=14, top=14, right=14, bottom=14),
    )


# ═══════════════════════════════════════════════════════
# PESTAÑA 4 — Configuración SDR
# ═══════════════════════════════════════════════════════
def build_config(page: ft.Page) -> ft.Control:
    def dd(label, value, options):
        return ft.Dropdown(
            label=label, value=value,
            options=[ft.dropdown.Option(o) for o in options],
            color=TEXT_MAIN, bgcolor=DARK_BG,
            border_color=BORDER_COL, focused_border_color=ACCENT_CYAN,
            border_radius=8, expand=True,
        )

    algo_dd = dd("Algoritmo Espectral", "Periodograma",
                 ["Periodograma", "Burg", "Yule-Walker"])
    fft_dd  = dd("Ventana FFT", "Hanning",
                 ["Hanning", "Hamming", "Blackman", "Kaiser", "Rectangular"])

    freq_f = txt_field("Frecuencia Central (MHz)", "1420.40", "e.g. 1420.40")
    gain_f = txt_field("Ganancia (dB)", "40", "0 – 49.6 dB")
    rate_f = txt_field("Sample Rate (Msps)", "2.4", "e.g. 2.4")
    fft_sz = txt_field("Tamaño FFT (puntos)", "4096", "potencia de 2")
    avg_f  = txt_field("Promediado (frames)", "10", "1 – 100")

    save_btn  = ft.Button(
        content="💾  Aplicar Configuración", bgcolor=ACCENT_CYAN, color=DARK_BG,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)))
    reset_btn = ft.Button(
        content="↺  Restablecer Defaults", color=TEXT_MUTED,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8),
                             side=ft.BorderSide(1, BORDER_COL)))

    def sec(t): return ft.Text(t, color=ACCENT_CYAN, size=13, weight=ft.FontWeight.BOLD)

    form = panel(
        width=560,
        padding_val=24,
        content=ft.Column([
            sec("📡  Parámetros del Receptor SDR"),
            ft.Divider(color=BORDER_COL, height=14),
            ft.Row([algo_dd], expand=True),
            ft.Divider(color=BORDER_COL, height=10),
            sec("🔧  Parámetros de Adquisición"),
            ft.Divider(color=BORDER_COL, height=8),
            ft.Row([freq_f, gain_f], spacing=14, expand=True),
            ft.Row([rate_f], expand=True),
            ft.Divider(color=BORDER_COL, height=16),
            sec("⚙️  Procesamiento de Señal"),
            ft.Divider(color=BORDER_COL, height=8),
            ft.Row([fft_dd], expand=True),
            ft.Row([fft_sz, avg_f], spacing=14, expand=True),
            ft.Divider(color=BORDER_COL, height=20),
            ft.Row([save_btn, reset_btn], spacing=12),
        ], spacing=10),
    )

    dev_rows = [("Modelo SDR",  "RTL-SDR v3 / HackRF", TEXT_MAIN),
                ("Conexión",    "USB 2.0",              TEXT_MAIN),
                ("Estado",      "Desconectado",         ACCENT_RED),
                ("Temperatura", "-- °C",                TEXT_MUTED),
                ("Driver",      "rtlsdr 0.6.0",         TEXT_MAIN),
                ("PPM Offset",  "0 ppm",                TEXT_MUTED),
                ("Buffer",      "16 × 512 KB",          TEXT_MAIN)]

    info_rows = [ft.Row([ft.Text(k, color=TEXT_MUTED, size=11, expand=1),
                          ft.Text(v, color=c, size=11, expand=1,
                                  weight=ft.FontWeight.W_600)])
                 for k, v, c in dev_rows]

    status_p = panel(
        expand=True,
        content=ft.Column([
            ft.Text("📊  Estado del Dispositivo", color=ACCENT_CYAN, size=13,
                    weight=ft.FontWeight.BOLD),
            ft.Divider(color=BORDER_COL, height=12),
            *info_rows,
            ft.Divider(color=BORDER_COL, height=12),
            ft.Text("💡 Instrucciones", color=ACCENT_GREEN, size=11,
                    weight=ft.FontWeight.BOLD),
            ft.Text(
                "1. Conecte el SDR por USB.\n"
                "2. Configure la frecuencia central y el sample rate.\n"
                "3. Seleccione el algoritmo espectral deseado.\n"
                "4. Presione 'Aplicar Configuración'.\n"
                "5. Active el Smart Trigger en la pestaña de Estadística.",
                color=TEXT_MUTED, size=10, selectable=True,
            ),
        ], spacing=8),
    )

    return ft.Container(
        content=ft.Row([form, status_p], spacing=12, expand=True),
        expand=True,
        padding=ft.Padding(left=14, top=14, right=14, bottom=14),
    )


# ═══════════════════════════════════════════════════════
# APLICACIÓN PRINCIPAL
# ═══════════════════════════════════════════════════════
def main(page: ft.Page):
    page.title      = "Plataforma DSP — Radiotelescopio 1420.40 MHz"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor    = DARK_BG
    page.window.width     = 1280
    page.window.height    = 820
    page.window.min_width = 900
    page.window.min_height= 620
    page.padding = 0
    page.spacing = 0
    page.theme   = ft.Theme(color_scheme_seed=ACCENT_CYAN, use_material3=True)

    # ── Header ────────────────────────────────────────
    sdr_dot = ft.Text("●", color=ACCENT_RED, size=16)
    sdr_lbl = ft.Text("Estado SDR: Desconectado", color=ACCENT_RED,
                      size=12, weight=ft.FontWeight.W_600)

    def on_emergency(e):
        sb = ft.SnackBar(
            content=ft.Text("⛔  EMERGENCIA: Adquisición detenida.",
                            color="#FFFFFF", weight=ft.FontWeight.BOLD),
            bgcolor=ACCENT_RED,
        )
        page.overlay.append(sb)
        sb.open = True
        page.update()

    emg_btn = ft.Button(
        content="⛔  Emergencia / Detener",
        bgcolor=ACCENT_RED, color="#FFFFFF",
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)),
        on_click=on_emergency,
    )

    header = ft.Container(
        bgcolor=PANEL_BG,
        border=ft.Border(bottom=ft.BorderSide(1, BORDER_COL)),
        padding=ft.Padding(left=20, top=10, right=20, bottom=10),
        content=ft.Row([
            ft.Icon(ft.Icons.WIFI_TETHERING, color=ACCENT_CYAN, size=26),
            ft.Text(
                "Procesamiento de Señales — Radiotelescopio (1420.40 MHz)",
                color=TEXT_MAIN, size=15, weight=ft.FontWeight.BOLD, expand=True,
            ),
            ft.Row([sdr_dot, sdr_lbl], spacing=5,
                   vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ft.Container(width=24),
            emg_btn,
        ], vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=12),
    )

    # ── Tabs con nueva API de Flet 0.82 ──────────────
    tab_labels = [
        "📡  Monitoreo y RFI",
        "🌈  Espectrograma",
        "📊  Estadística & Smart Trigger",
        "⚙️  Configuración SDR",
    ]
    tab_contents = [
        build_monitoring(page),
        build_spectrogram(page),
        build_statistics(page),
        build_config(page),
    ]

    tab_bar  = ft.TabBar(
        tabs=[ft.Tab(label=lbl) for lbl in tab_labels],
        label_color=ACCENT_CYAN,
        unselected_label_color=TEXT_MUTED,
        indicator_color=ACCENT_CYAN,
        divider_color=BORDER_COL,
    )
    tab_view = ft.TabBarView(controls=tab_contents, expand=True)

    tabs = ft.Tabs(
        content=ft.Column([
            tab_bar,
            tab_view
        ], expand=True, spacing=0),
        length=len(tab_labels),
        selected_index=0,
        expand=True,
    )

    # ── Footer ────────────────────────────────────────
    footer = ft.Container(
        bgcolor=PANEL_BG,
        border=ft.Border(top=ft.BorderSide(1, BORDER_COL)),
        padding=ft.Padding(left=20, top=6, right=20, bottom=6),
        content=ft.Row([
            ft.Text("UIC Radiotelescopio  •  v1.0.0",         color=TEXT_MUTED, size=10),
            ft.Text("•",                                        color=BORDER_COL, size=10),
            ft.Text("HI 1420.405751 MHz",                      color=TEXT_MUTED, size=10),
            ft.Text("•",                                        color=BORDER_COL, size=10),
            ft.Text("Backend: RTL-SDR / GNU Radio",            color=TEXT_MUTED, size=10),
            ft.Container(expand=True),
            ft.Text("2026-03-22  13:05 CST",                   color=TEXT_MUTED, size=10),
        ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
    )

    page.add(ft.Column([
        header,
        tabs,
        footer,
    ], expand=True, spacing=0))


if __name__ == "__main__":
    ft.app(target=main)
