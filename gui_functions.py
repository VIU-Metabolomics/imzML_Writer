import docker
import subprocess
import shutil
import os
import sys
import pymzml
import numpy as np
import pyimzml.ImzMLWriter as imzmlw
from recalibrate_mz import recalibrate
from bs4 import BeautifulSoup

def _viaPWIZ(path):
    ##check pwiz availability:
    current_dir = os.getcwd()
    os.chdir(path)
    try:
        check = subprocess.run("msconvert",capture_output=True,
                            shell=True,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT,
                            stdin=subprocess.PIPE,
                            cwd=os.getcwd(),
                            env=os.environ)
    except:
        raise Exception("msConvert not available, check installation and verify path is specified correctly")
    subprocess.run(["msconvert", fr"{path}\*.raw", "--mzML", "--64", "--filter", "peakPicking true 1-", "--simAsSpectra", "--srmAsSpectra"],stdout=subprocess.DEVNULL,
                   shell=True,
                    stderr=subprocess.STDOUT,
                    stdin=subprocess.PIPE,
                    cwd=os.getcwd(),
                    env=os.environ)
    os.chdir(current_dir)


def RAW_to_mzML(path,sl):
    if "win" in sys.platform and sys.platform != "darwin":
        _viaPWIZ(path)
    else:
        DOCKER_IMAGE = "chambm/pwiz-skyline-i-agree-to-the-vendor-licenses"
        client = docker.from_env()
        client.images.pull(DOCKER_IMAGE)

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
        

def clean_raw_files(path,sl):
    mzML_folder = fr"{path}{sl}Output mzML Files"
    RAW_folder = fr"{path}{sl}Initial RAW files"
    os.mkdir(mzML_folder)
    os.mkdir(RAW_folder)
    for file in os.listdir(path):
        if ".mzML" in file:
            shutil.move(fr"{path}{sl}{file}",fr"{mzML_folder}{sl}{file}")
        elif ".raw" in file:
            shutil.move(fr"{path}{sl}{file}",fr"{RAW_folder}{sl}{file}")

def mzML_to_imzML_convert(progress_target,PATH=os.getcwd(),LOCK_MASS=0,TOLERANCE=20):
    LOCK_MASS = float(LOCK_MASS)
    TOLERANCE = float(TOLERANCE)
    files = os.listdir(PATH)
    files.sort()

    ##Extracts filter strings, num pixels for each scan, etc
    num_scans=[]
    scan_filts=[]
    file_iter=-1
    spectrum_counts=[]
    mzml_files=[]
    spec_counts=[]
    for file in files:
        if ".mzML" in file:
            file_iter+=1
            tmp = pymzml.run.Reader(fr"{PATH}{file}")
            spec_counts.append(tmp.get_spectrum_count())
            if np.mean(spec_counts)*0.85 > tmp.get_spectrum_count():
                break
            
            
            mzml_files.append(file)

            if file_iter==0:
                for spectrum in tmp:
                    if spectrum["filter string"] not in scan_filts:
                        scan_filts.append(spectrum["filter string"])
            
            tmp_spectrum_counts = {filt_name:0 for filt_name in scan_filts}
            for spectrum in tmp:
                tmp_spectrum_counts[spectrum["filter string"]] += 1
            
            spectrum_counts.append(tmp_spectrum_counts)

    tmp.close()
    del spectrum

    #Find conserved portion of name for output filename
    str_array = [letter for letter in mzml_files[0]]
    OUTPUT_NAME = "".join(str_array)
    while OUTPUT_NAME not in mzml_files[-1]:
        str_array.pop(-1)
        OUTPUT_NAME = "".join(str_array)

    #Compute max number of pixels in each scan filter to construct pixel grids
    max_x_pixels = {}
    y_pixels = len(spectrum_counts)
    contender_idx=[]

    for filt in scan_filts:
        max_x = 0
        idx =-1
        for spec_file in spectrum_counts:
            idx += 1
            if spec_file[filt] > max_x:
                max_x = spec_file[filt]
                contender_idx.append(idx)
        max_x_pixels[filt] = max_x

    #Retrieve max times for time-alignment on longest spectra, build ideal time array
    max_times = []
    for idx in contender_idx:
        tmp = pymzml.run.Reader(fr"{PATH}{mzml_files[idx]}")
        for spectrum in tmp:
            scan_time = spectrum["scan time"]
        max_times.append(scan_time)

    time_targets={}
    iter = -1
    for key in max_x_pixels:
        iter += 1
        time_array = np.linspace(0,max_times[iter],max_x_pixels[key])
        time_targets[key] = time_array

    #Initiate imzmL objects
    image_files = {}
    output_files ={}
    for filt in scan_filts:
        image_files[filt] = imzmlw.ImzMLWriter(output_filename=fr"{OUTPUT_NAME}_{filt}")
        output_files[filt]=(fr"{OUTPUT_NAME}_{filt}")

    #Build image grid, write directly to an imzML

    for y_row in range(y_pixels):
        active_file = pymzml.run.Reader(PATH + mzml_files[y_row])
        for filt in scan_filts:
            tmp_times = []
            spec_list = []
            for spectrum in active_file:
                if spectrum["filter string"] == filt:
                    tmp_times.append(spectrum["scan time"])
                    spec_list.append(spectrum)

            pvs_ppm_off = 0
            for x_row in range(max_x_pixels[filt]):
                align_time = time_targets[filt][x_row]
                time_diffs = abs(tmp_times - align_time)
                match_idx = np.where(time_diffs == min(time_diffs))[0][0]
                match_spectra = spec_list[match_idx]

                [recalibrated_mz, pvs_ppm_off] = recalibrate(mz=match_spectra.mz, int=match_spectra.i,lock_mz=LOCK_MASS,search_tol=TOLERANCE,ppm_off=pvs_ppm_off)

                image_files[filt].addSpectrum(recalibrated_mz,match_spectra.i,(x_row,y_row))
        progress_target.config(value=int(y_row*100/(y_pixels-1)))

    update_files = os.listdir()
    update_files.sort()

    for filt in scan_filts:
        image_files[filt].close()

def imzML_metadata_process(model_files,sl,x_speed,y_step,tgt_progress,path):
    global OUTPUT_NAME, time_targets
    update_files = os.listdir()
    update_files.sort()

    scan_filts=[]
    model_file_list = os.listdir(model_files)

    ##Extract scan filter list
    tmp = pymzml.run.Reader(model_files+sl+model_file_list[0])
    for spectrum in tmp:
        if spectrum["filter string"] not in scan_filts:
            scan_filts.append(spectrum["filter string"])
    
        final_time_point = spectrum["scan time"]

    ##Extract common output name
    str_array = [letter for letter in model_file_list[0]]
    OUTPUT_NAME = "".join(str_array)
    while OUTPUT_NAME not in model_file_list[-1]:
        str_array.pop(-1)
        OUTPUT_NAME = "".join(str_array)

    #Retrieve max times for time-alignment on longest spectra, build ideal time array
    #Compute max number of pixels in each scan filter to construct pixel grids

    iter = 0
    for filt in scan_filts:
        #Find the target file
        iter+=1
        for file in update_files:
            if ".imzML" in file:
                partial_filter_string = file.split(OUTPUT_NAME+"_")[1].split(".imzML")[0]
                if partial_filter_string in filt:
                    target_file = file

        annotate_imzML(target_file,model_files+sl+model_file_list[0],final_time_point,filt,x_speed=x_speed,y_step=y_step)
        #printProgressBar(iter, len(scan_filts),prefix="Annotate")
        tgt_progress.config(value=int(iter*100/len(scan_filts)))
               


    move_files(OUTPUT_NAME,path)

def move_files(probe_txt,path):
    files = os.listdir()
    try:
        new_directory = f"{path}/{probe_txt}"
        os.mkdir(new_directory)
    except:
        pass
    
    for file in files:
        if probe_txt in file:
            shutil.move(file,f"{path}/{probe_txt}/{file}")

def annotate_imzML(annotate_file,SRC_mzML,scan_time=0.001,filter_string="none given",x_speed=1,y_step=1):
    """Takes pyimzml output imzML files and annotates them using some user input (imaging_parameters.xlsx)
    and the corresponding mzML source file. Designed to be embeded as part of overall nanoDESI Raw-to-imzML pipeline.
    annotate_file = the imzML file to be annotated
    SRC_mzML = the source file to pull metadata from
    scan_time = how long it took to scan across the tissue (default = 0.001)
    filter_string = what scan filter is actually captured  (default = "none given")
    """

    result_file = annotate_file

    #Retrieve data from source mzml
    with open(SRC_mzML) as file:
        data = file.read()
    data = BeautifulSoup(data,'xml')

    #Grab instrument model from the source mzML
    instrument_model = data.referenceableParamGroup.cvParam.get("name")


    #Open un-annotated imzML
    with open(annotate_file) as file:
        data_need_annotation = file.read()
    data_need_annotation = BeautifulSoup(data_need_annotation,'xml')

    #Replace template data with key metadata from mzML
    replace_list = ['instrumentConfigurationList']
    for replace_item in replace_list:
        data_need_annotation.find(replace_item).replace_with(data.find(replace_item))

    #Write instrument model to mzML, filter string
    data_need_annotation.instrumentConfigurationList.instrumentConfiguration.attrs['id']=instrument_model

    for tag in data_need_annotation.referenceableParamGroupList:
        if "scan1" in str(tag):
            for tag2 in tag:
                if "MS:1000512" in str(tag2):
                    tag2["value"] = filter_string
                    

        
    #Read pixel grid information from imzML
    for tag in data_need_annotation.scanSettingsList.scanSettings:
        if 'cvParam' in str(tag):
            if tag.get("accession") == "IMS:1000042": #num pixels x
                x_pixels = tag.get("value")
            elif tag.get("accession") == "IMS:1000043": #num pixels y
                y_pixels = tag.get("value")

    #Calculate pixel sizes and overall dimensions from size of pixel grid, scan speed, step sizes
    x_pix_size = float(x_speed * scan_time * 60 / float(x_pixels))
    max_x = int(x_pix_size * float(x_pixels))
    y_pix_size = y_step
    max_y = int(y_pix_size * float(y_pixels))

    accessions = ["IMS:1000046", "IMS:1000047", "IMS:1000044", "IMS:1000045"]
    names = ["pixel size (x)", "pixel size y", "max dimension x", "max dimension y"]
    values = [x_pix_size, y_pix_size, max_x, max_y]

    #Actual insertion of data - need to write string into a beautiful soup object with NO FORMATTING to append it
    for i in range(4):
        append_item = f'<cvParam cvRef="IMS" accession="{accessions[i]}" name="{names[i]}" value="{values[i]}"/>\n'
        append_item = BeautifulSoup(append_item,'xml')
        data_need_annotation.scanSettingsList.scanSettings.append(append_item)


    #Write the new file
    with open(result_file,'w') as file:
        file.write(str(data_need_annotation.prettify()))













    