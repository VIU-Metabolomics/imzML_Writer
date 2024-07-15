##docker run -e WINEDEBUG=-all -v -q '/Users/josephmonaghan/Documents/nanoDESI_raw_to_imzml/DataFiles chambm/pwiz-skyline-i-agree-to-the-vendor-licenses wine msconvert /data/*.raw --mzML --64 --zlib=off --filter "peakPicking true 1-"'
    #command = 'docker run -e WINEDEBUG=-all -v '+path_to_folder+'/:/data chambm/pwiz-skyline-i-agree-to-the-vendor-licenses  /data/*.'+orig_format+' --'+file_format+' --64  --zlib=off --filter "peakPicking true 1-"'


import docker
import os
import time
import shutil

tic = time.time()


# DOCKER_IMAGE = "chambm/pwiz-skyline-i-agree-to-the-vendor-licenses"
# client = docker.from_env()
# client.images.pull(DOCKER_IMAGE)
# path=os.getcwd()
# working_directory = path + "/DataFiles"





# vol = {working_directory: {'bind': "/"+DOCKER_IMAGE+"/data", 'mode': 'rw'}}

# comm = 'wine msconvert /'+DOCKER_IMAGE+'/data/*.raw --zlib=off --mzML --64 --outdir "/'+DOCKER_IMAGE+'/data" --filter "peakPicking true 1-"'
# env_vars = {"WINEDEBUG": "-all"}

# client.containers.run(
#     image=DOCKER_IMAGE,
#     environment=env_vars,
#     volumes = vol,
#     command=comm,
#     working_dir=working_directory,
#     auto_remove=True
#     )

os.mkdir("./DataFiles/mzML Output")
os.mkdir("./DataFiles/RAW Files")
for file in os.listdir("./DataFiles"):
    if ".mzML" in file:
        shutil.move("./DataFiles/"+file,"./DataFiles/mzML Output/"+file)
    elif ".raw" in file:
        shutil.move("./DataFiles/"+file,"./DataFiles/RAW Files/"+file)





toc = time.time()
print(f"Time elapsed: {round(toc - tic,1)} s")


