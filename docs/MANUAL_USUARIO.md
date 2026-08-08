# Manual de Usuario — Plataforma DSP para Radiotelescopio (UIC)

> **Versión:** Flet 0.84 / Python 3.10+  
> **Hardware compatible:** Signal Hound BB60C  
> **Última revisión:** 2026-08-07

---

## 1. Requisitos y Preparación del Sistema

### 1.1 Requisitos de Software

| Componente | Versión mínima |
|---|---|
| Sistema Operativo | Windows 10 / 11 (64-bit) |
| Python | 3.10 o superior |
| pip | Instalado en el entorno activo |

### 1.2 Instalación de Dependencias

Desde la carpeta raíz del proyecto, ejecute:

```bash
pip install -r requirements.txt
```

El archivo `requirements.txt` incluye todos los paquetes necesarios:
`flet`, `numpy`, `scipy`, `matplotlib`, `pillow`, `PyQt6`, `pyqtgraph`,
`lxml`, `python-docx`, `colorama` y sus dependencias transitivas.

### 1.3 Drivers y Binarios Nativos

Para el modo SDR en tiempo real, los siguientes archivos deben estar presentes en `core/bbdevice/`:
- `bb_api.dll` — API nativa de Signal Hound BB60C (x64).
- `ftd2xx.dll` — Driver USB FTDI requerido por `bb_api.dll`.

Estos archivos **no se instalan via pip**; se distribuyen junto al repositorio del proyecto.

### 1.4 Conexión del Hardware (Modo SDR Real)

1. Conecte el **Signal Hound BB60C** a un puerto **USB 3.0** (azul) de su equipo. Evite hubs USB sin alimentación propia.
2. Acople el cable coaxial de la antena al puerto `RF IN` del BB60C.
3. Opcionalmente, conecte una antena GPS al puerto `GPS` del dispositivo para sincronización temporal de alta precisión.
4. Asegúrese de que ningún otro software (por ejemplo, *Spike* de Signal Hound) esté usando el dispositivo.

---

## 2. Puesta en Marcha

### 2.1 Ejecución de la Aplicación

Abra una terminal en la carpeta raíz del proyecto y ejecute:

```bash
python main.py
```

O mediante el ejecutor de Flet:

```bash
flet run main.py
```

### 2.2 Estructura Visual al Iniciar

Al arrancar, la interfaz presenta:

- **Barra superior (Header):** Nombre del proyecto, botones de control global (Play/Pause/Stop/Record) e indicadores de estado del motor.
- **Barra lateral izquierda (Sidebar):** Navegación entre las 6 pestañas de análisis. Se expande con el ratón o se puede fijar con el botón de toggle `◀/▶`.
- **Área central:** Contenido de la pestaña activa.
- **Panel derecho:** Configuración de adquisición (visible en todas las pestañas excepto la pestaña 0).
- **Pie de página (Footer):** Indicadores de frecuencia central, tasa de muestreo y estado del stream.

### 2.3 Modos de Navegación

La barra lateral puede operar de dos formas:
- **Modo Lateral (por defecto):** Sidebar vertical colapsable a la izquierda.
- **Modo Superior:** Barra horizontal de pestañas. Se activa con el botón en la parte inferior del sidebar o con `Ctrl+Shift+S`.

---

## 3. Panel de Configuración (Lateral Derecho)

Este panel controla en tiempo real el comportamiento del motor DSP y del hardware:

| Control | Descripción |
|---|---|
| **Origen de Datos** | Alterna entre `Modo SDR` (hardware real) y `Modo Archivo` (archivo `.iq`) |
| **Cargar archivo .iq** | Abre el selector de archivo (también `Ctrl+O`) |
| **Frecuencia Central (MHz)** | Sintonía del oscilador local. Se aplica al vuelo sin detener el stream |
| **Tasa de Muestreo (MSps)** | Ancho de banda capturado. Valores altos requieren mayor CPU |
| **Nivel de Referencia (dBm)** | Ganancia física del SDR. Use valores bajos para señales débiles de radioastronomía |
| **Ancho de Banda IQ (MHz)** | Filtro digital del SDR |
| **VBW Smoothing** | Factor de suavizado temporal del espectro (0.1 = muy suave, 1.0 = tiempo real) |
| **Moving Average** | Activa/desactiva el filtro de promedio móvil sobre la señal |
| **Umbral Alto / Bajo (dB)** | Umbrales del Smart Trigger para detección de pulsos |
| **FFT Size** | Puntos de la transformada (mayor = más resolución frecuencial, más lento) |
| **Ventana de Adquisición (s)** | Duración del bloque de muestras procesado por actualización |
| **Historial Cascada (s)** | Duración del historial temporal en el espectrograma |
| **Tema** | Alterna entre los modos visual `Oscuro`, `Claro` y `Blanco` |
| **Resolución / Modo Ventana** | Ajuste de dimensiones y estado de la ventana principal |
| **Grosor de Línea** | Ajuste global del ancho de las líneas en todas las gráficas |
| **Restablecer Config.** | Vuelve todos los parámetros a los valores predeterminados de fábrica |

---

## 4. Controles de Flujo (Header)

| Botón / Tecla | Acción |
|---|---|
| ▶ Play / F5 | Inicia la adquisición de datos |
| ⏸ Pause | Pausa el stream manteniendo el último bloque en memoria |
| ⏹ Stop / F5 (segunda vez) | Detiene y cierra el stream limpiamente |
| ⏺ Grabar | Inicia grabación binaria del stream IQ a disco |
| F8 | Parada de emergencia inmediata |
| F11 | Pantalla completa / restaurar |

Cuando el motor está en **Pausa**:
- Los botones `◀` y `▶` del header se activan para navegar frame a frame por el historial.
- También puede usar las teclas `←` / `→` (o `,` / `.`) para el mismo efecto.
- Los algoritmos avanzados de la pestaña Estado se recalculan sobre el bloque congelado.

---

## 5. Descripción de Pestañas

### Pestaña 0 — Inicio y Estado

Panel de bienvenida e información del sistema:
- **Estado del Hardware:** Indica si el BB60C está conectado y el modo de operación activo.
- **Parámetros del Motor:** Muestra en tiempo real la frecuencia, tasa de muestreo, tamaño FFT y estado del hilo de procesamiento.
- **Configuración de Ventana:** Permite cambiar la resolución, el modo (Normal/Maximizada/Pantalla Completa) y el grosor de líneas de las gráficas.
- **Enciclopedia y Glosario:** Consulta rápida de términos técnicos de radioastronomía y DSP.

### Pestaña 1 — Señal y Señal Filtrada

Muestra la señal IQ en el dominio del tiempo y su espectro de frecuencias:
- **Amplitud RAW:** Señal compleja en bruto (I y Q separados o módulo).
- **Amplitud MA:** Señal suavizada por el filtro *Moving Average* para reducir ruido de alta frecuencia.
- **Espectro RAW:** PSD estimada sin suavizado adicional.
- **Espectro Suavizado:** PSD con el filtro VBW aplicado.

Teclas `F1`–`F4` seleccionan cuál de los cuatro paneles ocupa el foco. `Ctrl+F1`–`Ctrl+F4` maximiza el panel seleccionado.

### Pestaña 2 — Espectrograma

Representación tiempo × frecuencia × potencia (waterfall):

| Método | Descripción |
|---|---|
| **FFT (Waterfall)** | Espectrograma clásico. Rápido y eficiente |
| **CWT (Morlet)** | Transformada Wavelet Continua. Resolución adaptativa en tiempo-frecuencia |
| **AR/Burg** | Espectrograma autorregresivo de alta resolución |
| **Correlograma** | Estimación espectral indirecta por FFT de la autocorrelación |

Seleccione el método con `F1`–`F4`. `Ctrl+F1`–`Ctrl+F4` maximiza el panel. Use `Ctrl+Shift+1…6` para colapsar/expandir el panel de control del tab.

### Pestaña 3 — Histograma

Análisis estadístico de las amplitudes IQ:
- **Histograma:** Distribución de amplitudes de las muestras I y Q.
- **KDE Gaussiana:** Ajuste de densidad kernel. Si la curva se desvía de una Gaussiana, indica saturación del ADC o interferencia no gaussiana.
- **Señal en Tiempo:** Vista corta de la forma de onda para inspección visual.

### Pestaña 4 — Potencia vs. Tiempo

Registra la potencia integrada instantánea de la señal analítica ($P = I^2 + Q^2$) en un buffer circular:
- Útil para detectar ráfagas rápidas de radio (FRB) o pulsos de corta duración.
- El eje X representa el tiempo relativo acumulado; el eje Y la potencia en unidades lineales o dBm.

### Pestaña 5 — SNR vs. Frecuencia

Calcula la Relación Señal a Ruido (SNR) por canal de frecuencia respecto al piso de ruido estimado:
- El umbral de detección (configurable en el panel derecho) se muestra como línea horizontal.
- Las frecuencias que superan el umbral se marcan visualmente como detecciones válidas.
- Especialmente útil para identificar la línea de hidrógeno neutro (1420.405 MHz).

---

## 6. Funciones Avanzadas

### 6.1 Smart Trigger — Detección Automática de Pulsos

El Smart Trigger captura pulsos de radioastronomía de forma automática:

1. **Umbral Alto:** Cuando la energía de la señal supera este valor (dB), se inicia la captura.
2. **Umbral Bajo:** Cuando la energía cae por debajo de este valor, se finaliza la captura (histéresis doble para evitar disparos falsos por ruido térmico).
3. **Recorte Inteligente (±1.5 s):** El motor localiza el pico de energía exacto y extrae una ventana de 3 segundos centrada en él.
4. **Exportación Automática:** El bloque recortado se guarda en `Resultados_Datos/` con nombre y marca de tiempo.

### 6.2 Grabación de Datos IQ

Para guardar el stream en bruto:
1. Asegúrese de estar en **Modo SDR** con el stream activo.
2. Presione el botón **⏺ Grabar** en el header (el botón cambia de color al activarse).
3. Presione **Detener Grabación** para cerrar el archivo de forma atómica y evitar corrupción de datos.
4. El archivo resultante (`.iq` binario, pares `int16` o `float32`) puede cargarse luego en **Modo Archivo**.

### 6.3 Exportación de Gráficas

Cualquier gráfica visible puede exportarse en alta resolución:
- Presione el botón de **Captura** disponible en cada tab o en el header.
- Las imágenes se guardan automáticamente en `Resultados_Datos/` en formato PNG o SVG con nombre auto-generado que incluye el tipo de gráfica y la marca de tiempo exacta.

---

## 7. Atajos de Teclado Completos

| Tecla | Acción |
|---|---|
| `F5` | Iniciar / Detener stream |
| `F8` | Parada de emergencia |
| `F11` | Pantalla completa / restaurar |
| `←` / `,` *(en pausa)* | Retroceder un frame |
| `→` / `.` *(en pausa)* | Avanzar un frame |
| `Ctrl+Tab` | Ir a la siguiente pestaña |
| `Ctrl+Shift+Tab` | Ir a la pestaña anterior |
| `Ctrl+1` … `Ctrl+6` | Ir directamente a la pestaña N |
| `Ctrl+Shift+1` … `Ctrl+Shift+6` | Colapsar / Expandir panel de la pestaña N |
| `Ctrl+O` | Abrir selector de archivo .iq |
| `Ctrl+B` | Colapsar / Expandir panel del tab activo |
| `Ctrl+Shift+B` | Toggle completo del sidebar / topbar |
| `Ctrl+Shift+S` | Alternar modo lateral ↔ modo superior |
| `F1`–`F4` *(Tab 1 o 2)* | Seleccionar subgráfica activa |
| `Ctrl+F1`–`Ctrl+F4` *(Tab 1 o 2)* | Maximizar subgráfica seleccionada |

---

## 8. Generación de Datos de Prueba (Sin Hardware)

Si no dispone del hardware BB60C, puede generar un archivo `.iq` sintético:

```bash
python scripts/create_dummy_iq.py
```

El script crea un archivo con una señal sinusoidal más ruido gaussiano listo para cargar en **Modo Archivo**.

Para verificar la conexión con el hardware real:

```bash
python scripts/test_bb60c.py
```

El script intenta abrir el dispositivo y reporta el modelo y estado detectado.

---

## 9. Solución de Problemas

| Síntoma | Causa probable | Solución |
|---|---|---|
| "Hardware no detectado" o "Error BB60C" | Dispositivo desconectado, otro software ocupa el puerto, o falta `bb_api.dll` | Verificar conexión USB 3.0, cerrar Spike u otro software de Signal Hound, confirmar presencia de `bb_api.dll` en `core/bbdevice/` |
| Gráficas lentas o congeladas | Tasa de muestreo excesiva para la CPU disponible | Reducir la tasa de muestreo o aumentar el valor de FFT Size para procesar menos bloques por segundo |
| Histograma con barras planas en los extremos | Saturación del ADC (`ADC Overflow`) | Aumentar el Nivel de Referencia (ej. de -80 dBm a -40 dBm) para atenuar la señal de entrada |
| La interfaz no abre en Windows | Falta de drivers visuales C++ | Instalar el runtime de Visual C++ Redistributable 2015–2022 x64 |
| Error `ImportError` al iniciar | Paquete Python faltante | Ejecutar `pip install -r requirements.txt` dentro del entorno virtual activo |
| Archivo `.iq` no carga | Formato o ruta incorrectos | Verificar que el archivo sea binario de pares `int16` consecutivos (I, Q, I, Q, …) o `float32` según el formato configurado |

---

## 10. Carpetas de Salida

| Carpeta | Contenido |
|---|---|
| `Resultados_Datos/` | Capturas PNG/SVG de gráficas, archivos `.iq` exportados por Smart Trigger y grabaciones manuales |
| `core/config.json` | Configuración persistente del motor (se actualiza automáticamente al cerrar la app) |
