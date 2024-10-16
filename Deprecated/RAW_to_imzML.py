import os
import pymzml
import numpy as np
import pyimzml.ImzMLWriter as imzmlw
import time
from move_files import move_files
from recalibrate_mz import recalibrate
from make_mzML import convert_RAW_to_mzML
from annotate import annotate_imzML
from Progress_Bar import printProgressBar


tic = time.time()
convert_RAW_to_mzML()

LOCK_MASS = -1 #What peak to look for, ideally present in every scan
TOLERANCE = 20 #Specified in ppm

PATH = "./DataFiles/Output mzML Files/"
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
        tmp = pymzml.run.Reader(PATH+file)
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
    tmp = pymzml.run.Reader(PATH+mzml_files[idx])
    last_spectrum_idx = tmp.get_spectrum_count()
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
    image_files[filt] = imzmlw.ImzMLWriter(output_filename=OUTPUT_NAME+"_" + filt)
    output_files[filt]=(OUTPUT_NAME+"_" + filt)

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
    printProgressBar(y_row,y_pixels-1,prefix="Writing imzML")

update_files = os.listdir()
update_files.sort()

for filt in scan_filts:
    image_files[filt].close()

iter = 0
for filt in scan_filts:
    path_to_mzML = "./DataFiles/Output mzML Files/"
    first_mzML = path_to_mzML+mzml_files[0]

    #Find the target file
    iter+=1
    for file in update_files:
        if ".imzML" in file:
            partial_filter_string = file.split(OUTPUT_NAME+"_")[1].split(".imzML")[0]
            if partial_filter_string in filt:
                target_file = file
    final_time_point = time_targets[filt][-1]

    annotate_imzML(target_file,first_mzML,final_time_point,filt)
    printProgressBar(iter, len(scan_filts),prefix="Annotate")


move_files(OUTPUT_NAME)

toc = time.time()
print(f"Overall time: {round(toc - tic,1)}s")












    

        

