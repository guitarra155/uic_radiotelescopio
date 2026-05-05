# AI Skills Integration Matrix - UIC Radiotelescopio

This document tracks the AI skills integrated into the development environment to potentiate the Radioastronomy DSP platform.

## Core Pillars & Skills

| Pillar | Integrated Skill | Purpose | Impact |
| :--- | :--- | :--- | :--- |
| **Ciencia y Procesamiento** | `astropy` | Celestial coordinates, physical units, FITS handling. | Astronomical validation (HI Line 21cm). |
| | `sympy` | Symbolic mathematics and equation derivation. | Algorithmic precision (MUSIC/CWT). |
| | `scikit-learn` | Statistical analysis and peak detection. | Automated signal characterization. |
| | `statsmodels` | Detailed statistical models and inference. | Enhanced signal analysis and SNR validation. |
| **Interfaz de Usuario** | `scientific-visualization` | Publication-quality figures & Matplotlib optimization. | High-performance UI (~30 FPS in Flet). |
| | `python-design-patterns` | Architectural rigor (Singleton, SoC). | Scalable `DSPEngine` and UI separation. |
| **Eficiencia de la IA** | `token-optimizer` | Context window auditing and token reduction. | Long-term memory and complex context management. |
| | `claude-mem:smart-explore` | Token-optimized structural code search (AST). | Efficient codebase navigation without full reads. |
| | `claude-mem:make-plan` | Phased implementation planning. | Systematic development of DSP features. |
| | `python-performance-optimization` | Bottleneck analysis and NumPy vectorization. | Real-time processing efficiency (2.4 MSps). |

## Integration Status
- [x] Skills Load Configuration
- [x] Documentation Mapping
- [ ] Implementation of Advanced DSP Algorithms
- [ ] UI Render Optimization (Artist Cache)
