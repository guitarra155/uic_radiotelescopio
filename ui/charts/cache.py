"""
ui/charts/cache.py
Objeto ChartCache Singleton y configuración global de Matplotlib.
"""

import matplotlib as mpl
mpl.use('Agg')  # Backend ultra-rápido sin UI

# Optimizaciones extremas para gráficas muy densas
mpl.rcParams['path.simplify'] = True
mpl.rcParams['path.simplify_threshold'] = 1.0
mpl.rcParams['agg.path.chunksize'] = 10000

import matplotlib
matplotlib.rcParams['svg.fonttype'] = 'none'


class ChartCache:
    def __init__(self):
        self.figs = {}      # {name: Figure}
        self.axes = {}      # {name: Axes}
        self.artists = {}   # {name: dict}
        self.colorbars = {} # {name: Colorbar}


# Singleton compartido por todos los submódulos
cache = ChartCache()
