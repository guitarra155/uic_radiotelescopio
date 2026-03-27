import os
import shutil

base = r"c:\uic_radiotelescopio\uic_radiotelescopio"
tabs_src = os.path.join(base, "ui", "tabs", "tabs")
tabs_dst = os.path.join(base, "ui", "tabs")

if os.path.exists(tabs_src):
    for f in os.listdir(tabs_src):
        src_path = os.path.join(tabs_src, f)
        dst_path = os.path.join(tabs_dst, f)
        if os.path.isfile(src_path):
            shutil.move(src_path, dst_path)
    os.rmdir(tabs_src)
    print("tabs moved!")

comp_src = os.path.join(base, "ui", "components", "components")
comp_dst = os.path.join(base, "ui", "components")

if os.path.exists(comp_src):
    for f in os.listdir(comp_src):
        src_path = os.path.join(comp_src, f)
        dst_path = os.path.join(comp_dst, f)
        if os.path.isfile(src_path):
            shutil.move(src_path, dst_path)
    os.rmdir(comp_src)
    print("comps moved!")
