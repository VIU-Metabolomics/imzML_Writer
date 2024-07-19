import os
import shutil

RAW_PATH = "./DataFiles/Initial RAW files/"
DEST_PATH = "./DataFiles/"

raw_files = os.listdir(RAW_PATH)


for file in raw_files:
    shutil.move(RAW_PATH+file,file)

shutil.rmtree("./DataFiles/")
os.mkdir("./DataFiles")

for file in raw_files:
    shutil.move(file, DEST_PATH+file)