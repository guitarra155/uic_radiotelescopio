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
- `main.py`: Punto de entrada del sistema y controlador central de la interfaz gráfica.
- `core/dsp_engine.py`: Gestión de concurrencia y procesamiento central.
- `core/cfar_detector.py`: Implementación del algoritmo CFAR para mantener una tasa constante de falsa alarma en la detección de la señal.
- `ui/tabs/`: Directorio de controladores individuales orientados a las distintas representaciones (espectrogramas, histogramas, modelos 3D de potencia espectral).
- `ui/components/`: Definición de componentes visuales, barra superior, widgets compartidos y disposición estructural.

## 4. Dependencias del Sistema
- **Lenguaje Base:** Python 3.x
- **GUI:** Flet
- **Cómputo Científico:** NumPy, SciPy (Análisis y procesamiento estadístico)
- **Gráficos:** Matplotlib (Visualización científica avanzada)
