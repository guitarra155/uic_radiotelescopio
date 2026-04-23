# Wiki Log

Append-only record of all wiki operations.

## [2026-04-21] setup | Infrastructure Initialization
- Created `raw/` and `wiki/` directories.
- Established `CLAUDE.md` schema.
- Initialized `index.md` and `log.md`.
- Moved initial source `ANEXO 2 FORMATO PERFIL GUITARRA JHON v2.1.docx` to `raw/`.

## [2026-04-21] ingest | ANEXO 2 FORMATO PERFIL GUITARRA JHON v2.1.docx
- Processed document extraction using `extract_docx.py`.
- Created [[Summary_Project_Profile]] with key project metadata.
- Updated `index.md` with new entries.

## [2026-04-21] ingest | Project Objectives from ANEXO 2
- Extracted principal objective and specific activities from the source document.
- Created [[Project_Objectives]] page with detailed activity breakdown.
- Mapped alignment with ODS 4 and 9.

## [2026-04-21] ingest | Python Codebase Architecture
- Analyzed `main.py`, `dsp_engine.py`, and `advanced_dsp.py`.
- Mapped system flow from SDR acquisition to Flet-based UI.
- Documented implementation of algorithms (Burg, MUSIC, ESPRIT, Welch, Morlet).
- Created [[Technical_Architecture]] and [[DSP_Implementation]] pages.

## [2026-04-21] update | Mathematical Enrichment & Style
- Added LaTeX formulas (Burg, MUSIC, Welch) to [[DSP_Implementation]] for scientific rigor.
- Connected Python logic (Moving Average with `cumsum`) with its physical derivation.
- Created [[Project_Conventions]] documenting UI design tokens and nomenclature.

## [2026-04-21] ingest | Modular Structure & Function Mapping
- Mapped all key functions from `core` and `ui` to their respective mathematical formulas.
- Documented the modular UI architecture (Flet Tabs + PubSub).
- Added technical details on SDR hardware interface (BB60C).
- Created [[Function_Reference]] as a technical dictionary of the project.

## [2026-04-21] ingest | BB60C Comprehensive Documentation
- Ingested `documentacion_completa_bb60c.md` containing detailed hardware specs.
- Updated [[SDR_Hardware_Interface]] with:
    - DANL specs and frequency ranges.
    - System requirements (CPU, SSD, USB 3.0).
    - Power management functions (`bbSetPowerState`).
    - Safety limits (+20 dBm threshold).
