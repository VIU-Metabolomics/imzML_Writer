import os
import shutil

def move_files(probe_txt):
    files = os.listdir()
    try:
        new_directory = "./DataFiles/"+probe_txt
        os.mkdir(new_directory)
    except:
        pass
    
    for file in files:
        if probe_txt in file:
            shutil.move(file,"./DataFiles/"+probe_txt+"/"+file)