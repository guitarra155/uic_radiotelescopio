"""
core/algo_registry.py
Registro centralizado de todos los algoritmos DSP avanzados.

Esta es la ÚNICA fuente de verdad para:
  - Nombre completo y descripción de cada algoritmo
  - Color de acento en la UI
  - Parámetros configurables (nombre de clave en algo_params)
  - Función runner en advanced_dsp.py
  - Función de chart en ui/charts/

Para AGREGAR un nuevo algoritmo:
  1. Implementar la función runner en core/advanced_dsp.py
  2. Implementar la función de chart en ui/charts/algorithms.py
  3. Añadir una entrada en ALGO_REGISTRY aquí
  → No se requieren cambios en main.py, algo_result.py, ni sdr_config.py.
"""

# ─────────────────────────────────────────────────────────────────────────────
# Registro principal
# ─────────────────────────────────────────────────────────────────────────────

ALGO_REGISTRY: dict[str, dict] = {
    "AR/Burg": {
        # Metadata visual
        "color":     "#B380FF",
        "full_name": "Modelo Autorregresivo (AR / Burg)",
        "desc": (
            "Modelo Autorregresivo por método de Burg.\n"
            "Alta resolución espectral con pocas muestras.\n"
            "Ideal para señales CW estrechas."
        ),
        "params_hint": "Orden: configurable en el panel derecho (Orden AR).",
        # Claves en engine_instance.algo_params
        "param_keys": ["ar_order", "ar_n_freqs"],
        # Nombres de función (usados para dispatch dinámico)
        "runner":    "run_ar_burg",
        "chart_fn":  "chart_ar_spectrum",
        # Clave interna para algo_results
        "result_key": "ar",
    },
    "CWT/Morlet": {
        "color":     "#00C8FF",
        "full_name": "Transformada Wavelet Continua (CWT / Morlet)",
        "desc": (
            "Transformada Wavelet Continua con Morlet.\n"
            "Análisis tiempo-frecuencia simultáneo.\n"
            "Útil para señales transitorias o moduladas."
        ),
        "params_hint": "Escala automática: 64 bandas logarítmicas.",
        "param_keys": ["cwt_n_scales"],
        "runner":    "run_cwt",
        "chart_fn":  "chart_cwt_map",
        "result_key": "cwt",
    },
    "Pseudo-MUSIC": {
        "color":     "#FF4C4C",
        "full_name": "Pseudo-MUSIC (MUltiple SIgnal Classification)",
        "desc": (
            "MUltiple SIgnal Classification.\n"
            "Resolución super-FFT mediante sub-espacio de ruido.\n"
            "Detecta frecuencias con gran precisión."
        ),
        "params_hint": "# Señales: configurable en el panel derecho.",
        "param_keys": ["n_signals"],
        "runner":    "run_pseudo_music",
        "chart_fn":  "chart_music_spectrum",
        "result_key": "music",
    },
    "ESPRIT": {
        "color":     "#FF80AB",
        "full_name": "ESPRIT (Rotational Invariance Techniques)",
        "desc": (
            "Estimation of Signal Parameters via\n"
            "Rotational Invariance Techniques.\n"
            "Más eficiente que MUSIC para pocos componentes."
        ),
        "params_hint": "# Señales configurable (comparte parámetro con MUSIC).",
        "param_keys": ["n_signals"],
        "runner":    "run_esprit",
        "chart_fn":  "chart_music_spectrum",
        "result_key": "esprit",
    },
    "Welch": {
        "color":     "#FFD700",
        "full_name": "Estimación Espectral de Welch (Método Directo)",
        "desc": (
            "Densidad Espectral de Potencia (Welch).\n"
            "Reduce el ruido promediando periodogramas solapados."
        ),
        "params_hint": "FFT size y overlap configurables en el engine.",
        "param_keys": ["welch_fft", "welch_overlap"],
        "runner":    "run_welch",
        "chart_fn":  "chart_welch_spectrum",
        "result_key": "welch",
    },
    "Correlograma": {
        "color":     "#40E0D0",
        "full_name": "Correlograma — Método Indirecto (Wiener-Khinchin)",
        "desc": (
            "Estimación espectral indirecta (Wiener-Khinchin).\n"
            "FFT de la autocorrelación truncada (Blackman-Tukey).\n"
            "Útil para señales inmersas en ruido."
        ),
        "params_hint": "Lag máximo configurable (corr_max_lag).",
        "param_keys": ["corr_max_lag"],
        "runner":    "run_correlogram",
        "chart_fn":  "chart_correlogram_spectrum",
        "result_key": "correlogram",
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# Helpers de conveniencia
# ─────────────────────────────────────────────────────────────────────────────

def get_algo_names() -> list[str]:
    """Retorna la lista ordenada de nombres de algoritmos registrados."""
    return list(ALGO_REGISTRY.keys())


def get_algo_meta(name: str) -> dict:
    """Retorna la metadata de un algoritmo o un dict vacío si no existe."""
    return ALGO_REGISTRY.get(name, {})


def get_algo_color(name: str) -> str:
    """Retorna el color de acento de un algoritmo."""
    return ALGO_REGISTRY.get(name, {}).get("color", "#00D2FF")
