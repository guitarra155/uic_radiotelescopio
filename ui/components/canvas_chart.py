import flet as ft
import flet.canvas as cv
import numpy as np

class CanvasChart(ft.Container):
    def __init__(self, chart_id: str, title: str, line_colors: list, y_min: float, y_max: float):
        self.chart_id = chart_id
        self.title = title
        self.line_colors = line_colors
        self.y_min = y_min
        self.y_max = y_max
        self.x_min = 0.0
        self.x_max = 1.0
        
        # Path para la señal (línea)
        self.paths = []
        for color in self.line_colors:
            p = cv.Path(
                elements=[cv.Path.MoveTo(0, 200.0)],
                paint=ft.Paint(
                    color=color,
                    stroke_width=1.5,
                    style=ft.PaintingStyle.STROKE
                )
            )
            self.paths.append(p)
        
        self.canvas = cv.Canvas(
            shapes=self.paths,
            expand=True
        )
        
        super().__init__(
            content=self.canvas,
            expand=True
        )

    def get_actual_size(self):
        """Calcula el tamaño real estimado de este chart basado en el tamaño de la ventana de Flet"""
        if not self.page:
            return 400.0, 200.0
            
        page_w = float(self.page.width or 1280)
        page_h = float(self.page.height or 720)
        
        from core.dsp_engine import engine_instance
        max_id = getattr(engine_instance, "maximized_dual_chart", None)
        
        # Parámetros fijos de layout
        sidebar_w = 60.0
        right_w = 320.0
        header_h = 56.0
        footer_h = 25.0
        
        # Área útil neta para las gráficas
        net_w = max(100.0, page_w - sidebar_w - right_w - 40.0)
        net_h = max(50.0, page_h - header_h - footer_h - 70.0)
        
        if max_id is not None:
            if max_id == self.chart_id:
                return net_w, net_h
            else:
                return 10.0, 10.0  # Minimizada/Oculta
        else:
            # Grid 2x2 normal
            return net_w / 2.0 - 10.0, net_h / 2.0 - 10.0

    def update_plot(self, x_data: np.ndarray, y_datas: list, x_min=None, x_max=None, y_min=None, y_max=None):
        if x_min is not None: self.x_min = float(x_min)
        if x_max is not None: self.x_max = float(x_max)
        if y_min is not None: self.y_min = float(y_min)
        if y_max is not None: self.y_max = float(y_max)

        if not isinstance(y_datas, list):
            y_datas = [y_datas]

        # Calcular tamaño actual del canvas dinámicamente
        canvas_width, canvas_height = self.get_actual_size()

        dx = self.x_max - self.x_min
        dy = self.y_max - self.y_min
        if dx == 0: dx = 1.0
        if dy == 0: dy = 1.0

        for curve_idx, y_data in enumerate(y_datas):
            if curve_idx >= len(self.paths):
                break
                
            n = len(y_data)
            # Decimación dinámica: si la pantalla es muy pequeña, dibujamos menos puntos
            pts = 256 if canvas_width > 300 else 128
            step = max(1, n // pts)
            x_points = x_data[::step]
            y_points = y_data[::step]

            elements = []
            first = True

            for px, py in zip(x_points, y_points):
                cx = ((px - self.x_min) / dx) * canvas_width
                cy = canvas_height - ((py - self.y_min) / dy) * canvas_height
                
                cx = max(0.0, min(canvas_width, cx))
                cy = max(0.0, min(canvas_height, cy))

                if first:
                    elements.append(cv.Path.MoveTo(cx, cy))
                    first = False
                else:
                    elements.append(cv.Path.LineTo(cx, cy))

            if not elements:
                elements.append(cv.Path.MoveTo(0, canvas_height))
                elements.append(cv.Path.LineTo(canvas_width, canvas_height))

            self.paths[curve_idx].elements = elements
            
        if self.page:
            self.update()
