# LEAME: Plataforma DSP - Radiotelescopio UIC

## 1. ¿Qué es este proyecto?
Este proyecto es una **Plataforma de Procesamiento Digital de Señales (DSP)** diseñada para funcionar como un radiotelescopio en tiempo real. Su objetivo principal es detectar y analizar las señales del **Hidrógeno Neutro (HI)** que provienen del espacio (específicamente a la frecuencia de 1420.405 MHz).

Imagina que es una "radio" extremadamente potente conectada a una antena parabólica. En lugar de reproducir música, convierte las ondas de radio del espacio en gráficas visuales para que los científicos puedan estudiar la composición del universo.

## 2. ¿Para qué sirve?
- **Observación Astronómica**: Detectar la radiación que emiten las nubes de hidrógeno en nuestra galaxia.
- **Análisis de Señales**: Procesar millones de datos por segundo (hasta 40 millones de muestras) para separar las señales útiles del "ruido" o interferencias terrestres.
- **Visualización en Tiempo Real**: Mostrar espectrogramas (mapas de calor de frecuencias) y estadísticas instantáneas para entender qué estamos "escuchando".

---

## 3. Manual de Usuario (Paso a Paso)

¡Bienvenido! Esta guía te enseñará de forma sencilla cómo utilizar el radiotelescopio.

### A. Preparación de los Equipos
- **Conectar el equipo**: Conecta el receptor SDR (BB60C o RTL-SDR) a tu computadora. Si usas el BB60C, asegúrate de conectar ambos extremos del cable USB "en Y" a puertos USB 3.0 de tu PC para que tenga suficiente energía.
- **Archivos de datos**: Si no tienes una antena conectada, puedes usar grabaciones previas. Asegúrate de tener tus archivos guardados en formato `.iq` o `.npy`.

### B. Iniciar la Observación
Abre el programa y ve a la pestaña **Inicio & Configuración**:
- **Origen de los datos (Source Mode)**: Elige `sdr` para captar señales en vivo o `file` para reproducir un archivo grabado.
- **Frecuencia Central**: Para buscar hidrógeno en el espacio, escribe **1420.40 MHz**.
- **Tasa de Muestreo (Sample Rate)**: Controla cuánta información se procesa. Usa **1.0 a 5.0 MSps** para observaciones generales y no sobrecargar tu PC. Usa **40.0 MSps** si necesitas ver detalles muy finos.
- **Nivel de Señal (Reference Level)**: Ponlo en **-30 o -40 dBm**. Si aparece el aviso `ADC OVERFLOW`, súbelo a **-10 o 0 dBm**.

### C. Entendiendo las Gráficas
- **Auto-Escala**: A la derecha de la pantalla verás botones de "Auto X" y "Auto Y". Mantenlos encendidos para que el programa ajuste el zoom automáticamente y siempre veas la señal, incluso si cambia de intensidad.
- **Sintonía Automática**: Al cargar un archivo, el programa puede centrar automáticamente las señales fuertes, facilitando el hallazgo de picos de emisión.

### D. Limpiando Interferencias y Captura Automática
- **Filtro Moving Average (Pestaña Monitoreo)**: Actívalo para eliminar interferencias rápidas (como las de radares locales o electrónica cercana) y dejar solo las señales espaciales lentas y estables.
- **Smart Trigger (Pestaña Estadística)**: Define un "Umbral Alto". Si una señal (por ejemplo, el reflejo de un meteoro) supera ese nivel, el programa grabará automáticamente 3 segundos y los guardará en la carpeta `/data` para que los revises luego.

---

## 4. Instalación y Skills Integrados (Entorno de Desarrollo)
Si eres desarrollador y deseas contribuir al código de este proyecto, nuestro entorno utiliza diversas librerías ("skills") avanzadas:
- **Ciencia y Matemáticas**: Se integran `astropy` para manejar coordenadas celestes y validación astronómica (Línea de HI 21cm); `sympy` para ecuaciones simbólicas (MUSIC/CWT); `scikit-learn` y `statsmodels` para la detección automática de picos y análisis estadístico.
- **Interfaz y Arquitectura**: Utilizamos patrones de diseño estrictos (`python-design-patterns`) para separar la carga del motor matemático de la interfaz visual. Se emplea optimización de renderizado (`scientific-visualization`) para lograr gráficos de publicación mediante Matplotlib a 30 FPS en Flet.
- **Optimización de Rendimiento**: Vectorización profunda con NumPy para procesar datos a 40 MSps en tiempo real sin cuellos de botella.
