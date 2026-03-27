import shutil, os
base = r"c:\uic_radiotelescopio\uic_radiotelescopio"
for d in ["components", "tabs"]:
    src = os.path.join(base, "ui", d, d)
    dst = os.path.join(base, "ui", d)
    if os.path.exists(src):
        for item in os.listdir(src):
            try:
                shutil.move(os.path.join(src, item), os.path.join(dst, item))
            except Exception as e:
                pass
        shutil.rmtree(src, ignore_errors=True)
print("Fix Done")
