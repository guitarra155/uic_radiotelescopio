# Detalles Técnicos del Proyecto: UIC Radiotelescopio

## 1. Arquitectura del Sistema
El sistema se diseña con un enfoque modular, dividido en tres capas principales:
- **Capa de Interfaz de Usuario (UI):** Construida sobre el framework Flet (Python), provee un entorno gráfico de usuario interactivo para la visualización de datos de radioastronomía.
- **Capa de Lógica y Procesamiento (Core/DSP):** Motor de procesamiento digital de señales, responsable del análisis espectral, algoritmos de detección (CFAR) y modelado estadístico paramétrico.
- **Capa de Persistencia y Documentación:** Manejo de datos crudos (I/Q), registros binarios locales y documentación técnica de ingeniería.

## 2. Flujo de Funcionamiento
1. **Adquisición:** Recepción de muestras de radiofrecuencia (datos I/Q) provenientes del hardware SDR.
2. **Procesamiento de Señal:**
   - Estimación espectral y reducción de ruido térmico y RFI impulsivo a través del backend DSP.
   - Ejecución del algoritmo CFAR de umbral adaptativo para la detección de picos de emisión coherentes (línea de hidrógeno neutro).
   - Cálculo del histograma de amplitudes y ajuste probabilístico mediante estimadores de máxima verosimilitud (MLE) para distribuciones Gaussianas y de Weibull.
3. **Representación Visual:** Renderizado de gráficas bidimensionales y tridimensionales, espectrogramas en cascada y perfiles temporales de acumulación de potencia.

## 3. Descripción Detallada de Funciones y Módulos
- `main.py`: Punto de entrada del sistema y controlador central de la interfaz gráfica. Contiene el gestor de eventos PubSub y el orquestador del cambio de tema dinámico del sistema.
- `core/constants.py`: Archivo de constantes globales y definición del sistema de paleta de colores para los modos **Oscuro (Dark)**, **Claro (Light)** y **Blanco (White)**.
- `core/dsp_engine.py`: Gestión de concurrencia y procesamiento central. Carga y guarda los archivos de configuración local (`config.json`), incluyendo el estado persistente del tema visual seleccionado.
- `ui/charts/base.py`: Controlador de graficación basado en Matplotlib con soporte de tamaño dinámico, renderizado en formato SVG y limpieza dinámica de caché de figuras para el cambio de temas.
- `ui/tabs/`: Directorio de controladores individuales orientados a las distintas representaciones (espectrogramas, histogramas, modelos de potencia espectral).
- `ui/components/`: Definición de componentes visuales, barra superior, widgets compartidos y disposición estructural.

## 4. Dependencias del Sistema
- **Lenguaje Base:** Python 3.x
- **GUI:** Flet
- **Cómputo Científico:** NumPy, SciPy (Análisis y procesamiento estadístico)
- **Gráficos:** Matplotlib (Visualización científica avanzada)

## 5. Material Documental de Tesis
Se incorpora material estructurado de apoyo para la defensa oral del proyecto:
- [PROPUESTA_DIAPOSITIVAS.md](file:///c:/uic_radiotelescopio/docs/PROPUESTA_DIAPOSITIVAS.md): Planificación detallada para una exposición de 20 a 25 minutos. Asocia el texto preciso para cada diapositiva, estimaciones temporales de disertación y la correspondencia visual con los diagramas de arquitectura, secuencias de comunicación de hardware e interfaces gráficas del sistema.
