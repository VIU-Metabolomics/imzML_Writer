#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Aug 23 14:31:50 2022
Python code to convert raw/mzML/mzXML ms DDA or DIA data to mzXML or mzML. 
!!! convertRAWMP will move your files if core_number>1, make sure to have a back up !!!
@author: Jens Settelmeier
ToDos: - Adjust variable names, descriptions etc. since not only raw files can be converted.
- Consider using python suprocess, since os.system command is ugly practice...
- Fix the thread prameter core_number. It is not fully functional. 
jsettelmeier@ethz.ch 
"""

import os
import numpy as np
import shutil
import joblib
import argparse
import glob
from datetime import datetime
from joblib import Parallel, delayed

def convertRAW(path_to_folder, orig_format = 'raw', file_format = 'mzML'):
    """
    This function requires the docker msconvert docker container and 
    downloads it while execution
    https://hub.docker.com/r/chambm/pwiz-skyline-i-agree-to-the-vendor-licenses
    for more information check also: 
        https://yufree.cn/en/2019/10/15/use-msconvert-in-linux-or-mac/

    Parameters
    ----------
    path_to_folder : path to folder, for example '~/aweseome_proteins/data/raw/Hela'.
    file_format : TYPE, optional
        DESCRIPTION. The default is 'mzML' and transforms the raw file to mzML
        (necessary for DIA-NN for example!). Other options are:
            -mzXML

    Returns
    -------
    None. Writes the mzML or mzXML files into the same folder where the raw
    data is located. 

    """
    # download latest docker msconvert container
    os.system('docker pull chambm/pwiz-skyline-i-agree-to-the-vendor-licenses')
    # execute file conversion
    #if orig_format == 'raw':
    command = 'docker run -e WINEDEBUG=-all -v '+path_to_folder+'/:/data chambm/pwiz-skyline-i-agree-to-the-vendor-licenses wine msconvert /data/*.'+orig_format+' --'+file_format+' --64  --zlib=off --filter "peakPicking true 1-"'
    #else:
     #   command = 'docker run -e WINEDEBUG=-all -v '+path_to_folder+'/:/data chambm/pwiz-skyline-i-agree-to-the-vendor-licenses wine msconvert /data/*.'+orig_format+' --'+file_format+' --64 -z [ --zlib ] [=arg(=off)]'
    #print('Executed command:', command)
    os.system(command)
    #return #print('executing:', command)


def convertRAWMP(path_to_folder, orig_format='raw', file_format = 'mzML', core_number=-1):
    """

    Parameters
    ----------
    path_to_folder : path to folder, for example '~/aweseome_proteins/data/raw/Hela'.
    file_format : TYPE, optional
        The default is 'mzML' and transforms the raw file to mzML
        (necessary for DIA-NN for example!). Other options are:
            -mzXML
    core_number: int
        Specifies the amount of threads used for file conversion. Default is -1.
        -1 means use all available. 
    Returns
    -------
    None. Writes the mzML or mzXML files into the same folder where the raw
    data is located. 

    """
    
    # determine how many temp folder will be greated min(number_of_files,number_of_cores)
    # determine how many files will be moved to the temp folders 

    os.chdir(path_to_folder)
    if core_number==-1:
        core_number = joblib.cpu_count()
    filenames = np.sort(glob.glob(f'*.{orig_format}'))
    number_of_files = len(filenames)
    #print(f'Use {core_number} threads for the conversion of {number_of_files} files to {file_format}\n')

    
    if core_number > 1:
        result_path = os.path.join(path_to_folder,'Output mzML Files')
        converted_files_path = os.path.join(path_to_folder,f'Initial RAW files')
        os.mkdir(result_path)
        os.mkdir(converted_files_path)
        #print(f'Results will be available in {result_path}. Start conversion....\n')
        
    
        if number_of_files > core_number:
            folder_number = core_number
            files_per_folder = int(number_of_files/core_number)
            remaining_files = number_of_files % core_number
        else:
            folder_number = number_of_files
            files_per_folder = 1
            remaining_files = 0
        
        files_per_folder_vec = np.ones(folder_number)*files_per_folder
        
        t = 0
        while remaining_files != 0:
            files_per_folder_vec[t]=files_per_folder_vec[t]+1
            t = t+1
            remaining_files = remaining_files-1
        
        # build temporary folders
        k=0
        dst_folders = []
        for i in range(folder_number):
            dst = os.path.join(path_to_folder,f'tmp{i}')
            dst_folders.append(dst)
            os.mkdir(dst)
            files_in_curr_tmp_folder = int(files_per_folder_vec[i])
            for j in range(files_in_curr_tmp_folder):
                jth_file = filenames[j+k]
                src = os.path.join(path_to_folder,jth_file)
                dst_fn = os.path.join(dst,jth_file)
                shutil.move(src,dst_fn)
            k = k+j+1 
         
        #execute file conversion    
        o = Parallel(n_jobs=core_number,backend='multiprocessing', verbose=1) (delayed(convertRAW) (path_to_folder,orig_format=orig_format, file_format=file_format) for path_to_folder in dst_folders)
        
        #move files back and put results in result folder, delete tempory folders
        for tmp_folder in dst_folders:
            cur_raw_files = np.sort(glob.glob(os.path.join(tmp_folder,f'*.{orig_format}')))
            
            for path_to_file in cur_raw_files:
                shutil.move(path_to_file,converted_files_path)
                
            cur_converted_files = np.sort(glob.glob(os.path.join(tmp_folder,f'*.{file_format}')))
            for path_to_converted_file in cur_converted_files:
                shutil.move(path_to_converted_file,result_path)
            
            os.rmdir(tmp_folder)
    else:
        #print(f'Results will be available in {path_to_folder}. Start conversion....\n')
        convertRAW(path_to_folder, orig_format, file_format)
    return 



def parse_args():
    """
    Returns
    -------
    args : TYPE
        Default argument parser for console execution.

    """
    parser = argparse.ArgumentParser(description='Convert raw data to mzML or mzXML.')
    parser.add_argument('--p', '--path_to_folder', type=str, default = os.getcwd()+"/DataFiles", help='absolute path to the folder containing all raw files to be converted')
    parser.add_argument('--s', '--orig_format', type = str, default = 'raw', help='source file format')
    parser.add_argument('--f', '--file_format', type = str, default = 'mzML', help='target file format')
    parser.add_argument('--c', '--core_number', type = int, default = -1, help='Determines the number of threads should be taken to convert all files. -1 corresponds to all possible.')
    args = parser.parse_args()
    return args

if __name__ == "__main__":
    args = parse_args()
    convertRAWMP(args.p, args.s, args.f, args.c) # why is **args or *args not working? Responder will be invited for a drink :)