"""
charts.py
Agrupa toda la lógica de Python matemático y ploteo con Matplotlib.
Retorna URIs en Base64 para consumo de Flet.
"""

import math
import io
import base64
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from constants import *

matplotlib.use("Agg")

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
    """Aplica formato Dark Theme nativo a un eje de Matplotlib."""
    ax.set_facecolor(MPL_AXBG)
    ax.tick_params(colors=MPL_TEXT, labelsize=8)
    for sp in ax.spines.values():
        sp.set_edgecolor(BORDER_COL)
    ax.set_title(title, color=ACCENT_CYAN, fontsize=9, pad=6)
    ax.set_xlabel(xlabel, color=TEXT_MUTED, fontsize=8)
    ax.set_ylabel(ylabel, color=TEXT_MUTED, fontsize=8)
    ax.grid(True, color=MPL_GRID, linestyle="--", linewidth=0.5, alpha=0.6)

def chart_amplitude(offset=0.0) -> str:
    fig, ax = plt.subplots(figsize=(7, 2.8))
    fig.patch.set_facecolor(MPL_BG)
    t = np.linspace(0, 10, 1000)
    
    # Simula la fase continua añadiendo el offset
    sig = (0.5 * np.sin(2*np.pi*1.5*(t + offset)) 
           + 0.3*np.sin(2*np.pi*4.2*(t + offset)+0.8)
           + np.random.normal(0, 0.12, len(t)))
           
    # Simula un pulso RFI esporádico si el offset coincide con cierta ventana
    m = (t > 4.5) & (t < 5.5)
    sig[m] += 1.8 * np.sin(2*np.pi*5*t[m])
    
    ax.plot(t, sig, color=ACCENT_CYAN, linewidth=0.9, alpha=0.85)
    ax.fill_between(t, sig, alpha=0.15, color=ACCENT_CYAN)
    ax.axvline(5.0, color=ACCENT_RED, linestyle="--", linewidth=0.9,
               alpha=0.85, label="Pico RFI")
    ax.legend(fontsize=7, facecolor=MPL_AXBG, edgecolor=BORDER_COL, labelcolor=MPL_TEXT)
    style_ax(ax, "Amplitud vs Tiempo (Vivo)", "Tiempo (s)", "Amplitud (dBm)")
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
