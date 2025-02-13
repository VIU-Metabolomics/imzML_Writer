import docker
import subprocess
import shutil
import os
import sys
import pymzml
import numpy as np
import pyimzml.ImzMLWriter as imzmlw
from imzML_Writer.recalibrate_mz import recalibrate
from bs4 import BeautifulSoup, Tag
import string



def get_drives():
    from ctypes import windll
    drives = []
    bitmask = windll.kernel32.GetLogicalDrives()
    for letter in string.ascii_uppercase:
        if bitmask & 1:
            drives.append(letter)
        
        bitmask >>= 1
    
    return drives


def find_file(target, folder):
    try:
        for f in os.listdir(folder):
            path = os.path.join(folder,f)
            if os.path.isdir(path):
                result = find_file(target, path)
                if result is not None:
                    return result
                continue
            if f == target:
                return path
    except Exception as e:
        pass

def find_msconvert():
    drives = get_drives()

    candidates = []
    for drive in drives:
        drive_str = (f"{drive}:\\".__repr__()).replace("'","")
        candidates.append(find_file("msconvert.exe",drive_str))
    

    for candidate in candidates:
        if candidate is not None:
            if "msconvert.exe" in candidate:
                res = subprocess.run(candidate, shell=True,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT,
                            stdin=subprocess.PIPE,
                            cwd=os.getcwd(),
                            env=os.environ)
                if res.returncode == 0:
                    #msconvert successfully found and called
                    return candidate


def _viaPWIZ(path:str,write_mode:str):
    """Method to call msConvert directly if the detected platform is on windows, takes as argument:
    path - path to the target files (string)
    write_mode - "Centroid" or "Profile" as specified in the GUI"""
    ##check pwiz availability:
    file_type = get_file_type(path)
    current_dir = os.getcwd()
    os.chdir(path)
    msconvert = "msconvert"
    try:
        res = subprocess.run(msconvert, shell=True,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT,
                            stdin=subprocess.PIPE,
                            cwd=os.getcwd(),
                            env=os.environ) 
        if res.returncode != 0:
            print("msconvert not in PATH - searching drives for install")
            msconvert = find_msconvert()
            print("Found it!")
    except:
        raise Exception("msConvert not available, check installation and verify msConvert path is specified correctly")

    ##Call the actual conversion
    if write_mode=="Centroid":
        subprocess.Popen([msconvert, fr"{path}\*.{file_type}", "--mzML", "--64", "--filter", "peakPicking true 1-", "--simAsSpectra", "--srmAsSpectra"],stdout=subprocess.DEVNULL,
                    shell=True,
                        stderr=subprocess.STDOUT,
                        stdin=subprocess.PIPE,
                        cwd=os.getcwd(),
                        env=os.environ)
    elif write_mode=="Profile":
                subprocess.Popen([msconvert, fr"{path}\*.{file_type}", "--mzML", "--64", "--simAsSpectra", "--srmAsSpectra"],stdout=subprocess.DEVNULL,
                    shell=True,
                        stderr=subprocess.STDOUT,
                        stdin=subprocess.PIPE,
                        cwd=os.getcwd(),
                        env=os.environ)
    else:
        raise("Invalid data write mode!")
    
    os.chdir(current_dir)

def get_file_type(path:str):
    """Identifies the file type in the specified path, ignoring hidden files starting with .
    Returns the file extension"""
    files = os.listdir(path)
    while files[0].startswith("."):
        files.pop(0)

    return files[0].split(".")[-1]

def RAW_to_mzML(path:str,sl:str,write_mode:str):
    """Calls msConvert via docker on linux and Mac, or calls _viaPwiz method on PC to manage conversion of raw vendor files to mzML format within the specified path"""
    if "win" in sys.platform and sys.platform != "darwin":
        _viaPWIZ(path,write_mode)
    else:
        ##Setup the docker image including internal file structure and command
        DOCKER_IMAGE = "chambm/pwiz-skyline-i-agree-to-the-vendor-licenses"
        client = docker.from_env()
        client.images.pull(DOCKER_IMAGE)

        working_directory = path
        file_type = get_file_type(path)

        vol = {working_directory: {'bind': fr"{sl}{DOCKER_IMAGE}{sl}data", 'mode': 'rw'}}

        if write_mode=="Centroid":
            comm = fr"wine msconvert {sl}{DOCKER_IMAGE}{sl}data{sl}*.{file_type} --zlib=off --mzML --64 --outdir {sl}{DOCKER_IMAGE}{sl}data --filter '"'peakPicking true 1-'"' --simAsSpectra --srmAsSpectra"
        elif write_mode=="Profile":
            comm = fr"wine msconvert {sl}{DOCKER_IMAGE}{sl}data{sl}*.{file_type} --zlib=off --mzML --64 --outdir {sl}{DOCKER_IMAGE}{sl}data --simAsSpectra --srmAsSpectra"
        else:
            raise("Invalid data write mode!")
            

        env_vars = {"WINEDEBUG": "-all"}
        
        ##Call/run the docker container
        client.containers.run(
            image=DOCKER_IMAGE,
            environment=env_vars,
            volumes = vol,
            command=comm,
            working_dir=working_directory,
            auto_remove=True,
            detach=True
            )
        

def clean_raw_files(path:str,sl:str,file_type:str):
    """Cleans up file system after RAW_to_mzML has completed, creating two folders within the specified path:
    Initial RAW files - raw vendor files
    Output mzML Files - processed mzML files output by msConvert
    Inputs:
    path - path to directory to clean up
    sl - legacy code, should just be '/'
    file_type - extension for raw files to know what to sort"""
    mzML_folder = fr"{path}{sl}Output mzML Files"
    RAW_folder = fr"{path}{sl}Initial RAW files"
    os.mkdir(mzML_folder)
    os.mkdir(RAW_folder)
    for file in os.listdir(path):
        if ".mzML".lower() in file.lower():
            shutil.move(fr"{path}{sl}{file}",fr"{mzML_folder}{sl}{file}")
        elif file_type in file and file != "Initial RAW files":
            shutil.move(fr"{path}{sl}{file}",fr"{RAW_folder}{sl}{file}")

def mzML_to_imzML_convert(progress_target,PATH:str=os.getcwd(),LOCK_MASS:float=0,TOLERANCE:float=20):
    """Handles conversion of mzML files to the imzML format using the pyimzml library. Converts data line-by-line (one mzML at a time),
    aligning data based on scan time and splitting into separate imzML files for each scan in the source mzML.
    Inputs:
    progress_target - tkinter progress bar object from the GUI to update as conversion progresses
    path - Working path for source mzML files
    Lock mass - m/z to use for coarse m/z recalibration if desired. 0 = No recalibration
    Tolerance - search tolerance (in ppm) with which to correct m/z based on the specified lock mass. Default 20 ppm"""

    ##Ensure lock mass and tolerance are formatted as float
    LOCK_MASS = float(LOCK_MASS)
    TOLERANCE = float(TOLERANCE)
    files = os.listdir(PATH)
    files.sort()

    ##Extracts filter strings, num pixels for each scan, etc
    scan_filts=[]
    file_iter=-1
    spectrum_counts=[]
    mzml_files=[]
    spec_counts=[]
    list_type = False
    for file in files:
        if ".mzML".lower() in file.lower():
            file_iter+=1
            tmp = pymzml.run.Reader(fr"{PATH}{file}")
            spec_counts.append(tmp.get_spectrum_count())
            ##Ignore partially collected datafiles that were cut-short (threshold of <85% the scans of the mean datafile)
            if np.mean(spec_counts)*0.5 > tmp.get_spectrum_count():
                break
            
            
            mzml_files.append(file)
            

            ##Retrieve list of filter strings from first file
            if file_iter==0:
                for spectrum in tmp:
                    if isinstance(spectrum["filter string"],list):
                            list_type = True
                    if list_type:
                        scan_filts = spectrum["filter string"][0]
                    else: 
                        if spectrum["filter string"] not in scan_filts:
                            scan_filts.append(spectrum["filter string"])
            if not list_type:
                tmp_spectrum_counts = {filt_name:0 for filt_name in scan_filts}
            else:
                str_list = set(spectrum["filter string"])
                str_list = list(str_list)
                tmp_spectrum_counts={}
                for entry in str_list:
                    tmp_spectrum_counts[entry]=0

            for spectrum in tmp:
                if not list_type:
                    tmp_spectrum_counts[spectrum["filter string"]] += 1
                elif list_type:
                    tmp_spectrum_counts[spectrum["filter string"][0]]+= 1
            
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
    if isinstance(scan_filts,str):
        scan_filts = [scan_filts]

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
            # scan_time = spectrum["scan time"]
            scan_time = spectrum.scan_time_in_minutes()
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
        if filt == None:
            image_files[filt]=imzmlw.ImzMLWriter(output_filename=fr"{OUTPUT_NAME}_None")
        else:
            image_files[filt] = imzmlw.ImzMLWriter(output_filename=fr"{OUTPUT_NAME}_{filt.split(".")[0]}")
        output_files[filt]=(fr"{OUTPUT_NAME}_{filt}")

    #Build image grid, write directly to an imzML
    for y_row in range(y_pixels):
        active_file = pymzml.run.Reader(PATH + mzml_files[y_row])
        for filt in scan_filts:
            tmp_times = []
            spec_list = []
            for spectrum in active_file:
                if spectrum["filter string"] == filt:
                    tmp_times.append(spectrum.scan_time_in_minutes())
                    spec_list.append(spectrum)
                elif list_type:
                    tmp_times.append(spectrum.scan_time_in_minutes())
                    spec_list.append(spectrum)

            pvs_ppm_off = 0
            for x_row in range(max_x_pixels[filt]):
                align_time = time_targets[filt][x_row]
                time_diffs = abs(tmp_times - align_time)
                match_idx = np.where(time_diffs == min(time_diffs))[0][0]
                match_spectra = spec_list[match_idx]

                [recalibrated_mz, pvs_ppm_off] = recalibrate(mz=match_spectra.mz, int=match_spectra.i,lock_mz=LOCK_MASS,search_tol=TOLERANCE,ppm_off=pvs_ppm_off)
                if len(recalibrated_mz) != 0:
                    image_files[filt].addSpectrum(recalibrated_mz,match_spectra.i,(x_row+1,y_row+1,1))

        ##Update progress bar in the GUI as each mzML finishes
        progress = int(y_row*100/(y_pixels-1)) 
        if progress > 0:   
            progress_target.stop() 
            progress_target.config(mode="determinate",value=int(y_row*100/(y_pixels-1)))

    ##Close imzML objects for downstream annotation
    update_files = os.listdir()
    update_files.sort()

    for filt in scan_filts:
        image_files[filt].close()

def imzML_metadata_process(model_files:str,sl:str,x_speed:float,y_step:float,tgt_progress,path:str):
    """Manages annotation of imzML files with metadata from source mzML files and user-specified fields (GUI). Inputs:
    model_files - Directory to the folder containing mzML files
    sl - legacy, use '/'
    x_speed - scan speed in the x-direction, µm/sec
    y_step - step between strip lines, µm
    tgt_progress - Tkinter progress bar object to update as the process continues
    path - path to the directory where imzML files should be stored after annotation"""
    global OUTPUT_NAME, time_targets

    ##Retrieve and sort files from the working directory (imzML) and model file directory (mzML)
    update_files = os.listdir()
    update_files.sort()

    scan_filts=[]
    model_file_list = os.listdir(model_files)
    model_file_list.sort()

    ##Ignore hidden files
    while model_file_list[0].startswith("."):
        model_file_list.pop(0)

    ##Extract filter strings from the first mzML source file
    tmp = pymzml.run.Reader(os.path.join(model_files,model_file_list[0]))
    for spectrum in tmp:
        if spectrum["filter string"] not in scan_filts:
            scan_filts.append(spectrum["filter string"])
    
        # final_time_point = spectrum["scan time"]
        final_time_point = spectrum.scan_time_in_minutes()

    ##Extract common output name based on common characters in first and last mzML file
    str_array = [letter for letter in model_file_list[0]]
    OUTPUT_NAME = "".join(str_array)
    while OUTPUT_NAME not in model_file_list[-1]:
        str_array.pop(-1)
        OUTPUT_NAME = "".join(str_array)


    ##Loop to annotate each imzML file
    iter = 0
    for filt in scan_filts:
        #Find the target file based on a filter string match
        iter+=1
        for file in update_files:
            if ".imzML" in file:
                partial_filter_string = file.split(OUTPUT_NAME+"_")[-1].split(".imzML")[0]
                if partial_filter_string == "None":
                    target_file = file
                elif partial_filter_string in filt:
                    target_file = file

        ##Calls the actual annotation function
        annotate_imzML(target_file,model_files+sl+model_file_list[0],final_time_point,filt,x_speed=x_speed,y_step=y_step)

        ##Update progress bar in the GUI
        progress = int(iter*100/len(scan_filts))
        if progress > 0:
            tgt_progress.stop()
            tgt_progress.config(mode="determinate",value=progress)

    ##After conversion is complete, clean up files by putting the annotated imzML files in a new directory within the datafile folder           
    move_files(OUTPUT_NAME,path)

def move_files(probe_txt:str,path:str):
    """Moves the annotated imzML files into the same directory as the source raw files of the image under a new folder matching the datafile names"""
    files = os.listdir()
    try:
        new_directory = f"{path}/{probe_txt}"
        os.mkdir(new_directory)
    except:
        pass
    
    for file in files:
        if probe_txt in file:
            shutil.move(file,f"{path}/{probe_txt}/{file}")

def annotate_imzML(annotate_file:str,SRC_mzML:str,scan_time:float=0.001,filter_string:str="none given",x_speed:float=1,y_step:float=1):
    """Takes pyimzml output imzML files and annotates them using GUI inputs and the corresponding mzML source file. 
    annotate_file = the imzML file to be annotated
    SRC_mzML = the source file to pull metadata from
    scan_time = how long it took to scan across the tissue (default = 0.001)
    filter_string = what scan filter is actually captured  (default = "none given")
    """

    #Error handling for when scan filter extraction fails
    result_file = annotate_file
    if filter_string == None:
        filter_string = "None"

    #Retrieve data from source mzml
    with open(SRC_mzML) as file:
        data = file.read()
    data = BeautifulSoup(data,'xml')

    #Grab instrument model from the source mzML
    try:
        instrument_model = data.referenceableParamGroup.cvParam.get("name")
    except:
        instrument_model = "Could not find"

    #Open un-annotated imzML
    with open(annotate_file) as file:
        data_need_annotation = file.read()
    data_need_annotation = BeautifulSoup(data_need_annotation,'xml')

    #Replace template data with key metadata from mzML
    replace_list = ['instrumentConfigurationList']
    for replace_item in replace_list:
        data_need_annotation.find(replace_item).replace_with(data.find(replace_item))

    #Write instrument model to imzML, filter string
    data_need_annotation.instrumentConfigurationList.instrumentConfiguration.attrs['id']=instrument_model
    new_tag = Tag(builder=data_need_annotation.builder,
                  name="cvParam",
                  attrs={'accession':'MS:1000031',"cvRef":"MS","name":instrument_model})
    # new_tag = data_need_annotation.new_tag("cvParam", accession="MS:1000031", cvRef="MS")
    data_need_annotation.instrumentConfigurationList.instrumentConfiguration.append(new_tag)

    #Remove empty instrument ref from imzML template
    for paramgroup in data_need_annotation.select("referenceableParamGroupRef"):
        if paramgroup['ref']=="CommonInstrumentParams":
            paramgroup.extract()
    
    for cvParam in data_need_annotation.select("cvParam"):
        if cvParam["accession"]=="MS:1000530":
            del cvParam["value"]
        if cvParam["accession"]=="IMS:1000411":
            cvParam["accession"]="IMS:1000413"
            cvParam["name"]="flyback"



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


    for cvParam in data_need_annotation.select("cvParam"):
        if cvParam["accession"] in accessions:
            cvParam["unitCvRef"]="UO"
            cvParam["unitAccession"]="UO:0000017"
            cvParam["unitName"]="micrometer"

    #Write the new file
    with open(result_file,'w') as file:
        file.write(str(data_need_annotation.prettify()))





    