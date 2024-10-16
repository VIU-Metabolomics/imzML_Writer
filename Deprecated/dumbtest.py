import docker
import os
import sys
import subprocess

path = "C:/Users/JMRA/Downloads/Initial RAW files"



def _viaPWIZ(path):
    ##check pwiz availability:
    try:
        check = subprocess.run("msconvert",capture_output=True)
    except:
        raise Exception("msConvert not available, check installation and verify path is specified correctly")

    command = fr"msconvert {path}\*.raw --zlib=off --mzML --64 --filter '"'peakPicking true 1-'"' --simAsSpectra --srmAsSpectra"
    
    subprocess.run(command)


def RAW_to_mzML(path,sl):
    if "win" in sys.platform:
        _viaPWIZ(path)
    else:
        DOCKER_IMAGE = "chambm/pwiz-skyline-i-agree-to-the-vendor-licenses"
        client = docker.from_env()
        client.images.pull(DOCKER_IMAGE)
        
        operating_system = sys.platform
        working_directory = path

        vol = {working_directory: {'bind': fr"{sl}{DOCKER_IMAGE}{sl}data", 'mode': 'rw'}}

        comm = fr"wine msconvert {sl}{DOCKER_IMAGE}{sl}data{sl}*.raw --zlib=off --mzML --64 --outdir {sl}{DOCKER_IMAGE}{sl}data --filter '"'peakPicking true 1-'"' --simAsSpectra --srmAsSpectra"

        env_vars = {"WINEDEBUG": "-all"}

        client.containers.run(
            image=DOCKER_IMAGE,
            environment=env_vars,
            volumes = vol,
            command=comm,
            working_dir=working_directory,
            auto_remove=True,
            detach=True
            )


RAW_to_mzML("test","sl")