import os
import shutil

def move_files(probe_txt):
    files = os.listdir()
    try:
        os.mkdir(probe_txt)
    except:
        pass
    
    for file in files:
        if probe_txt in file:
            shutil.move(file,"./"+probe_txt+"/"+file)