import subprocess
import os
import shutil

build_writer = subprocess.run(["python3", "-m", "PyInstaller", "_pc_imzML_Writer.spec", "--noconfirm"])

if build_writer.returncode == 0:
    obo_dir = "obo"
    files = os.listdir(obo_dir)
    # dest_dir = "./dist_Mac/imzML_Writer.app/Contents/MacOS/obo"
    dest_dir = "./dist/imzML_Writer/obo"

    os.mkdir(dest_dir)
    for file in files:
        shutil.copy(os.path.join(obo_dir,file),os.path.join(dest_dir,file))