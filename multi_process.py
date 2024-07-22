import os
import shutil

MULTI_JOB_PATH = "./Job_Queue/"
MULTI_DEST_PATH = "./Processed_Images/"
DATAFILE_PATH = "./DataFiles/"


IMAGE_FOLDERS = os.listdir(MULTI_JOB_PATH)

for image_folder in IMAGE_FOLDERS:
    if not image_folder.startswith("."):
        image_files_in_folder = os.listdir(MULTI_JOB_PATH+image_folder+"/")
        for image_file_in_folder in image_files_in_folder:
            if ".raw" in image_file_in_folder:
                shutil.move(MULTI_JOB_PATH+image_folder+"/"+image_file_in_folder,DATAFILE_PATH+image_file_in_folder)
    
        os.system("python3 RAW_to_imzML.py")

        os.mkdir(MULTI_DEST_PATH+image_folder)
        output_folder_names = os.listdir(DATAFILE_PATH)
        for _name in output_folder_names:
            if not _name.startswith("."):
                os.mkdir(MULTI_DEST_PATH+image_folder+"/"+_name)
                file_movelist = os.listdir(DATAFILE_PATH+_name+"/")
                for _file in file_movelist:
                    if not _file.startswith("."):
                        shutil.move(DATAFILE_PATH+_name+"/"+_file,MULTI_DEST_PATH+image_folder+"/"+_name+"/"+_file)
                shutil.rmtree(DATAFILE_PATH+_name)

    



    

