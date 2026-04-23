---
type: concept
tags: [uic, radiotelescopio, objectives, roadmap]
created: 2026-04-21
sources: [[raw/ANEXO 2 FORMATO PERFIL GUITARRA JHON v2.1.docx]]
---

# Objetivos del Proyecto

El proyecto tiene como fin último la autonomía tecnológica en la observación astronómica local mediante el desarrollo de herramientas propias de procesamiento.

## Objetivo Principal
**Implementar una plataforma para el procesamiento digital de señales (DSP) de radiotelescopios.**

Esta plataforma servirá como base escalable para observaciones astronómicas complejas, incluyendo la identificación de púlsares en diversas bandas.

## Objetivos Específicos (Actividades)

| Actividad                     | Descripción                                                                                                      |
| :---------------------------- | :--------------------------------------------------------------------------------------------------------------- |
| **1. Análisis de Señales**    | Revisión matemática de señales electromagnéticas en banda base y estudio de datos I/Q de receptores SDR.         |
| **2. Desarrollo de Software** | Codificación de la arquitectura troncal en Python, integrando bibliotecas gráficas y cálculo matricial.          |
| **3. Trabajo Experimental**   | Recolección de datos en 1420.40 MHz usando el radiotelescopio del Observatorio Astronómico de Quito.             |
| **4. Implementación DSP**     | Programación de algoritmos de estimación espectral (Burg, Yule-Walker) y análisis estadístico (Weibull, Rician). |
| **5. Validación**             | Pruebas de tiempo real, evaluación de latencia y ajustes de rendimiento para evitar cuellos de botella.          |

## Alineación Estratégica
- **ODS 9**: Fortalecimiento de la innovación e infraestructura científica nacional.
- **ODS 4**: Educación de calidad, sirviendo como recurso didáctico para futuros investigadores.
