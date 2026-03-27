import os
import shutil

dirs = ['core', 'ui', 'scripts', 'docs', 'data']
for d in dirs:
    os.makedirs(d, exist_ok=True)

moves = {
    'dsp_engine.py': 'core',
    'constants.py': 'core',
    'config.json': 'core',
    'charts.py': 'ui',
    'tabs': 'ui',
    'components': 'ui',
    'make_word.py': 'scripts',
    'create_dummy_iq.py': 'scripts',
    'test_file.py': 'scripts',
    'Explicacion_Arquitectura.docx': 'docs',
    'Revisión tesis 1.docx': 'docs',
    'Explicacion_Proyecto.txt': 'docs',
    'IQREC_Milk2025-02-12_11h41m26s_1.iq': 'data',
    'test_signal.iq': 'data'
}

for src, dst in moves.items():
    if os.path.exists(src):
        dest_path = os.path.join(dst, os.path.basename(src))
        shutil.move(src, dest_path)
        print(f"Moved {src} to {dest_path}")
    else:
        print(f"Missing {src}")
