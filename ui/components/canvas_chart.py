import flet as ft
import flet.canvas as cv
import numpy as np

class CanvasChart(ft.Container):
    def __init__(self, title: str, line_color: str, y_min: float, y_max: float):
        self.title = title
        self.line_color = line_color
        self.y_min = y_min
        self.y_max = y_max
        self.x_min = 0.0
        self.x_max = 1.0
        
        # Logical resolution for scaling
        self.logical_width = 800.0
        self.logical_height = 400.0
        
        # Path para la señal (línea)
        self.path = cv.Path(
            elements=[cv.Path.MoveTo(0, self.logical_height)],
            paint=ft.Paint(
                color=self.line_color,
                stroke_width=1.5,
                style=ft.PaintingStyle.STROKE
            )
        )
        
        # Contenedor del Canvas con resolución lógica fija (auto-escalable por Flutter)
        self.canvas = cv.Canvas(
            shapes=[self.path],
            width=self.logical_width,
            height=self.logical_height,
            expand=True
        )
        
        # Inicializar el Container padre con el canvas como contenido
        super().__init__(
            content=self.canvas,
            expand=True
        )

    def update_plot(self, x_data: np.ndarray, y_data: np.ndarray, x_min=None, x_max=None, y_min=None, y_max=None):
        if x_min is not None: self.x_min = float(x_min)
        if x_max is not None: self.x_max = float(x_max)
        if y_min is not None: self.y_min = float(y_min)
        if y_max is not None: self.y_max = float(y_max)

        # Downsampling inteligente para no saturar Flet (256 puntos es el sweet spot para 60 FPS)
        n = len(y_data)
        step = max(1, n // 256)
        x_points = x_data[::step]
        y_points = y_data[::step]

        elements = []
        first = True
        
        dx = self.x_max - self.x_min
        dy = self.y_max - self.y_min
        
        # Prevenir división por cero
        if dx == 0: dx = 1.0
        if dy == 0: dy = 1.0

        for px, py in zip(x_points, y_points):
            # Mapeo lineal a coordenadas del Canvas [0, logical_width] x [logical_height, 0]
            cx = ((px - self.x_min) / dx) * self.logical_width
            cy = self.logical_height - ((py - self.y_min) / dy) * self.logical_height
            
            # Recortar coordenadas para evitar dibujo fuera de los límites
            cx = max(0.0, min(self.logical_width, cx))
            cy = max(0.0, min(self.logical_height, cy))

            if first:
                elements.append(cv.Path.MoveTo(cx, cy))
                first = False
            else:
                elements.append(cv.Path.LineTo(cx, cy))

        # Si no hay datos, dibujar una línea plana en el fondo
        if not elements:
            elements.append(cv.Path.MoveTo(0, self.logical_height))
            elements.append(cv.Path.LineTo(self.logical_width, self.logical_height))

        self.path.elements = elements
        if self.page:
            self.update()
