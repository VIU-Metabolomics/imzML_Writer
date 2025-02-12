import os
import gui_functions
import time

TGT_DIR = "/Users/josephmonaghan/Documents/JM Images/Lum2Tumors/IMAGING CAMPAIGN/Bulk Process"
X_SPEED = 40
Y_STEP = 150
WRITE_MODE = "Centroid"
FILETYPE = "raw"

class progress_dummy():
    def __init__(self):
        pass

    def stop(self):
        pass

    def config(self,*args, **kwargs):
        pass

def wait_for_mzML(path):
    all_files = os.listdir(path)
    num_files = 0
    for file in all_files:
        if file.split(".")[-1] == FILETYPE:
            num_files+=1
    
    num_mzML = 0
    while num_mzML < num_files:
        num_mzML = 0
        all_files = os.listdir(path)
        for file in all_files:
            if file.split(".")[-1] == "mzML":
                num_mzML += 1
        
        time.sleep(1)
    
    time.sleep(5)

    
def main(TGT_DIR:str=TGT_DIR,X_SPEED:float=X_SPEED,Y_STEP:float=Y_STEP,WRITE_MODE:str=WRITE_MODE,FILETYPE:str=FILETYPE):
    all_dirs = os.listdir(TGT_DIR)
    ALL_Data_DIRS = []
    for dir in all_dirs:
        if not dir.startswith("."):
            ALL_Data_DIRS.append(dir)

    num_files = len(ALL_Data_DIRS)
    for _idx, _filename in enumerate(ALL_Data_DIRS):
        print(f"Starting file {_idx+1} / {num_files+1}")
        path = os.path.join(TGT_DIR,_filename)

        print("Initiating mzML conversion")
        gui_functions.RAW_to_mzML(path,"/",WRITE_MODE)
        #wait for mzML files to be written from docker image
        wait_for_mzML(path)

        
        gui_functions.clean_raw_files(path,"/",FILETYPE)
        progress = progress_dummy()
        print("Starting to write imzML")
        mzML_path = os.path.join(path,"Output mzML Files/")
        gui_functions.mzML_to_imzML_convert(progress,mzML_path)

        print("Annotating imzML")
        gui_functions.imzML_metadata_process(mzML_path,"/",X_SPEED,Y_STEP,progress,path)



if __name__=="__main__":
    main()
