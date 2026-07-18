"""
constantes.py
Variables globales, colores de tema y estilos base.
Sistema de paletas: dark, light, white.
"""

# ─────────────────────────────────────────────────────────────────────────────
# Definición de paletas
# ─────────────────────────────────────────────────────────────────────────────

PALETTES = {
    "dark": {
        "DARK_BG":      "#0D1117",
        "PANEL_BG":     "#161B22",
        "ACCENT_CYAN":  "#00D2FF",
        "ACCENT_GREEN": "#3FD18D",
        "ACCENT_RED":   "#FF4C4C",
        "ACCENT_AMBER": "#FFB347",
        "TEXT_MAIN":    "#E6EDF3",
        "TEXT_MUTED":   "#8B949E",
        "BORDER_COL":   "#30363D",
        "MPL_BG":       "#0D1117",
        "MPL_AXBG":     "#161B22",
        "MPL_GRID":     "#21262D",
        "MPL_TEXT":     "#E6EDF3",
        "SIDEBAR_ACTIVE_BG": "#0D2137",
        # Colores adicionales dinámicos para contraste
        "COLOR_PURPLE": "#B380FF",
        "COLOR_ORANGE": "#FF9100",
        "COLOR_PINK":   "#E040FB",
        "COLOR_GOLD":   "#FFD700",
        "COLOR_KDE":    "#FFFF00",
    },
    "light": {
        "DARK_BG":      "#CFD8DC",
        "PANEL_BG":     "#B0BEC5",
        "ACCENT_CYAN":  "#006064",
        "ACCENT_GREEN": "#1B5E20",
        "ACCENT_RED":   "#B71C1C",
        "ACCENT_AMBER": "#E65100",
        "TEXT_MAIN":    "#212121",
        "TEXT_MUTED":   "#546E7A",
        "BORDER_COL":   "#90A4AE",
        "MPL_BG":       "#CFD8DC",
        "MPL_AXBG":     "#B0BEC5",
        "MPL_GRID":     "#90A4AE",
        "MPL_TEXT":     "#212121",
        "SIDEBAR_ACTIVE_BG": "#90A4AE",
        "COLOR_PURPLE": "#5E35B1",
        "COLOR_ORANGE": "#BF360C",
        "COLOR_PINK":   "#880E4F",
        "COLOR_GOLD":   "#FF6F00",
        "COLOR_KDE":    "#311B92",
    },
    "white": {
        "DARK_BG":      "#FFFFFF",
        "PANEL_BG":     "#F6F8FA",
        "ACCENT_CYAN":  "#0550AE",
        "ACCENT_GREEN": "#1A7F37",
        "ACCENT_RED":   "#CF222E",
        "ACCENT_AMBER": "#9A6700",
        "TEXT_MAIN":    "#1F2328",
        "TEXT_MUTED":   "#57606A",
        "BORDER_COL":   "#D0D7DE",
        "MPL_BG":       "#FFFFFF",
        "MPL_AXBG":     "#F6F8FA",
        "MPL_GRID":     "#D0D7DE",
        "MPL_TEXT":     "#1F2328",
        "SIDEBAR_ACTIVE_BG": "#DDF4FF",
        "COLOR_PURPLE": "#6200EA",
        "COLOR_ORANGE": "#D50000",
        "COLOR_PINK":   "#C51162",
        "COLOR_GOLD":   "#E65100",
        "COLOR_KDE":    "#1A237E",
    },
}

# Tema activo
current_theme = "dark"

# ─────────────────────────────────────────────────────────────────────────────
# Variables globales inicializadas con la paleta oscura (por defecto)
# ─────────────────────────────────────────────────────────────────────────────

DARK_BG      = PALETTES["dark"]["DARK_BG"]
PANEL_BG     = PALETTES["dark"]["PANEL_BG"]
ACCENT_CYAN  = PALETTES["dark"]["ACCENT_CYAN"]
ACCENT_GREEN = PALETTES["dark"]["ACCENT_GREEN"]
ACCENT_RED   = PALETTES["dark"]["ACCENT_RED"]
ACCENT_AMBER = PALETTES["dark"]["ACCENT_AMBER"]
TEXT_MAIN    = PALETTES["dark"]["TEXT_MAIN"]
TEXT_MUTED   = PALETTES["dark"]["TEXT_MUTED"]
BORDER_COL   = PALETTES["dark"]["BORDER_COL"]
MPL_BG       = PALETTES["dark"]["MPL_BG"]
MPL_AXBG     = PALETTES["dark"]["MPL_AXBG"]
MPL_GRID     = PALETTES["dark"]["MPL_GRID"]
MPL_TEXT     = PALETTES["dark"]["MPL_TEXT"]
SIDEBAR_ACTIVE_BG = PALETTES["dark"]["SIDEBAR_ACTIVE_BG"]
COLOR_PURPLE = PALETTES["dark"]["COLOR_PURPLE"]
COLOR_ORANGE = PALETTES["dark"]["COLOR_ORANGE"]
COLOR_PINK   = PALETTES["dark"]["COLOR_PINK"]
COLOR_GOLD   = PALETTES["dark"]["COLOR_GOLD"]
COLOR_KDE    = PALETTES["dark"]["COLOR_KDE"]


def set_theme(name: str):
    """Cambia el tema activo y actualiza todas las variables globales del módulo."""
    global current_theme
    global DARK_BG, PANEL_BG, ACCENT_CYAN, ACCENT_GREEN, ACCENT_RED, ACCENT_AMBER
    global TEXT_MAIN, TEXT_MUTED, BORDER_COL
    global MPL_BG, MPL_AXBG, MPL_GRID, MPL_TEXT
    global SIDEBAR_ACTIVE_BG, COLOR_PURPLE, COLOR_ORANGE, COLOR_PINK, COLOR_GOLD, COLOR_KDE

    if name not in PALETTES:
        return
    current_theme = name
    p = PALETTES[name]
    DARK_BG      = p["DARK_BG"]
    PANEL_BG     = p["PANEL_BG"]
    ACCENT_CYAN  = p["ACCENT_CYAN"]
    ACCENT_GREEN = p["ACCENT_GREEN"]
    ACCENT_RED   = p["ACCENT_RED"]
    ACCENT_AMBER = p["ACCENT_AMBER"]
    TEXT_MAIN    = p["TEXT_MAIN"]
    TEXT_MUTED   = p["TEXT_MUTED"]
    BORDER_COL   = p["BORDER_COL"]
    MPL_BG       = p["MPL_BG"]
    MPL_AXBG     = p["MPL_AXBG"]
    MPL_GRID     = p["MPL_GRID"]
    MPL_TEXT     = p["MPL_TEXT"]
    SIDEBAR_ACTIVE_BG = p["SIDEBAR_ACTIVE_BG"]
    COLOR_PURPLE = p["COLOR_PURPLE"]
    COLOR_ORANGE = p["COLOR_ORANGE"]
    COLOR_PINK   = p["COLOR_PINK"]
    COLOR_GOLD   = p["COLOR_GOLD"]
    COLOR_KDE    = p["COLOR_KDE"]


# ─────────────────────────────────────────────────────────────────────────────
# Unidad de potencia del sistema (dBm — con offset de calibración aplicado)
# ─────────────────────────────────────────────────────────────────────────────
POWER_UNIT = "dBm"


def get(key: str) -> str:
    """Retorna el valor actual de un color del tema activo."""
    return PALETTES[current_theme].get(key, "#FF00FF")
