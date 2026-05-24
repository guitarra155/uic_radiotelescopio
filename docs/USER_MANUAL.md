# Manual de Usuario: Plataforma UIC Radiotelescopio

Esta guía detalla el flujo de trabajo operativo para realizar observaciones radioastronómicas exitosas utilizando el hardware BB60C o archivos IQ.

## 1. Preparación del Sistema
Antes de iniciar, asegúrese de:
- Conectar el BB60C usando el cable USB 3.0 en "Y" (ambos conectores al PC).
- Si usa archivos, que estén en formato `.iq` o `.npy`.
- Verificar que el archivo `bb_api.dll` esté en la raíz del proyecto.

## 2. Configuración de Adquisición
En la pestaña **Inicio & Configuración**:
- **Source Mode**: Seleccione `sdr` para tiempo real o `file` para análisis offline.
- **Frecuencia Central**: Para hidrógeno, use **1420.40 MHz**. El sistema permite "Live Tuning" (cambio en caliente).
- **Sample Rate**: 
    - Use **1.0 a 5.0 MSps** para búsqueda general (bajo consumo de CPU).
    - Use **40.0 MSps** para análisis de alta resolución (requiere PC potente).
- **Nivel de Referencia (dBm)**: 
    - Ajuste a **-30 o -40 dBm** para señales de antena.
    - Si la consola muestra `ADC OVERFLOW`, suba el nivel a **-10 o 0 dBm**.

## 3. Uso de la Visualización Inteligente
El sistema incluye algoritmos que "entienden" la señal:

### A. Auto-Escala (Modo Inteligente)
En el panel derecho de cualquier pestaña, encontrará los switches de **Auto X** y **Auto Y**.
- **Recomendación**: Mantenga **Auto Y** activado en la pestaña de Potencia. El sistema calculará el mínimo y máximo del buffer cada segundo para que nunca pierda de vista la señal, incluso si hay deriva térmica.
- **Limpieza**: Si ve "cuadros blancos", no se preocupe. El sistema ahora redondea automáticamente los valores cargados para que la interfaz sea siempre legible.

### B. Spectral Lock (Auto-Sintonía)
Cuando cargue un archivo, el motor escaneará los primeros bloques de datos. Si detecta un pico de energía significativo, aparecerá un mensaje de **Auto-calibración**. El sistema ajustará la frecuencia central automáticamente para centrar el pico detectado, ideal para confirmar líneas de emisión astronómicas.

## 4. Mitigación de RFI (Interferencias)
En la pestaña **Monitoreo y RFI**:
- Observe la gráfica **Amplitud vs Tiempo**. Pulsos cortos y repetitivos indican interferencias de radares o electrónica local.
- Utilice el **Filtro Moving Average** para suavizar el ruido térmico y resaltar señales estables y débiles.

## 5. Captura de Eventos (Smart Trigger)
En **Estadística & Smart Trigger**:
- Defina un **Umbral Alto** (Trigger High). Cuando la energía supere este nivel, el sistema guardará automáticamente una ráfaga de 3 segundos en la carpeta `/data`.
- Esto es ideal para capturar meteoros o tránsitos rápidos de satélites.
