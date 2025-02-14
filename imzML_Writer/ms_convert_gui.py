import tkinter as tk
from tkinter import ttk, filedialog
import os
import threading
import sys
import docker
from imzML_Writer.utils import get_file_type

##Colors and FONTS
TEAL = "#2da7ad"
BEIGE = "#dbc076"
GREEN = "#22d10f"
FONT = ("HELVETICA", 18, 'bold')

def main(tgt_dir:str=None):
    """**Experimental** - Provides a Mac GUI for MSConvert as a wrapper around the msconvert Docker image.
    
    :param tgt_dir: (optional) Initial directory for the GUI to open in."""

    def get_path():
        """No arguments, prompts the user via dialog box for the directory containing the data to be processed.
    Will call populate_list() method to show files in the UI listbox"""
        global FILE_TYPE
        directory = filedialog.askdirectory(initialdir=os.getcwd())

        if directory:
            CD_entry.delete(0,tk.END)
            CD_entry.insert(0,directory)

            populate_list(directory)
            #FILE_TYPE = get_file_types(directory)
    
    def populate_list(dir:str):
        """takes an argument dir and populates the UI listbox based on its contents
        dir: pathname for active directory as a string"""
        file_list.delete(0,tk.END)
        files = os.listdir(dir)
        files.sort()
        ticker = 0
        for file in files:
            if not file.startswith("."):
                file_list.insert(ticker,file)
                ticker+=1

    def call_msconvert():
        sl = "/"
        path = CD_entry.get()
        if "win" in sys.platform and sys.platform != "darwin":
            print("This GUI is for Mac/Linux, please use the MSConvert GUI from Proteowizard for PCs")
        else:
            DOCKER_IMAGE = "chambm/pwiz-skyline-i-agree-to-the-vendor-licenses"
            client = docker.from_env()
            client.images.pull(DOCKER_IMAGE)

            working_directory = path
            file_type = get_file_type(path)

            vol = {working_directory: {'bind': fr"{sl}{DOCKER_IMAGE}{sl}data", 'mode': 'rw'}}

            comm = fr"wine msconvert {sl}{DOCKER_IMAGE}{sl}data{sl}*.{file_type} --zlib=off --mzML --64 --outdir {sl}{DOCKER_IMAGE}{sl}data --filter '"'peakPicking true 1-'"' --simAsSpectra --srmAsSpectra"
            print(comm)

            comm = fr"wine msconvert {sl}{DOCKER_IMAGE}{sl}data{sl}*.{file_type} --mzML --64 --outdir {sl}{DOCKER_IMAGE}{sl}data --filter '"'peakPicking true 1-'"'"

            if zlib.get():
                comm = comm + " --zlib=off"

            if SIM_as_spectra.get():
                comm = comm + " --simAsSpectra"

            if SRM_as_spectra.get():
                comm = comm + " --srmAsSpectra"

            env_vars = {"WINEDEBUG": "-all"}
            print(comm)
            client.containers.run(
                image=DOCKER_IMAGE,
                environment=env_vars,
                volumes = vol,
                command=comm,
                working_dir=working_directory,
                auto_remove=True,
                detach=True
                )



    
    window_msconvert = tk.Tk()
    window_msconvert.title("MAC - msConvert GUI")
    window_msconvert.config(padx=5,pady=5,bg=TEAL)
    style = ttk.Style()
    style.theme_use('clam')

    ##Choose Directory Button
    CD_button = tk.Button(window_msconvert,text="Select Folder",bg=TEAL,highlightbackground=TEAL,command=get_path)
    CD_button.grid(row=0,column=0)

    CD_entry = tk.Entry(window_msconvert,text="Enter Directory Here",highlightbackground=TEAL,background=BEIGE,fg="black",justify='center')
    CD_entry.grid(row=0,column=1)

    ##Processing buttons
    convert_mzML = tk.Button(window_msconvert,text="Convert to mzML",bg=TEAL,highlightbackground=TEAL,command=call_msconvert)
    convert_mzML.grid(row=3,column=4,columnspan=3)

    #Listbox for files in target folder
    file_list = tk.Listbox(window_msconvert,bg=BEIGE,fg="black",height=10,highlightcolor=TEAL,width=35,justify='left')
    file_list.grid(row=0,column=4,rowspan=3,columnspan=3)

    zlib = tk.BooleanVar(window_msconvert)
    zlib_check = tk.Checkbutton(window_msconvert,text="zlib compression?",bg=TEAL,font=FONT,var=zlib)
    zlib_check.grid(row=1,column=0,columnspan=2)

    SIM_as_spectra = tk.BooleanVar(window_msconvert)
    SIM_check = tk.Checkbutton(window_msconvert,text="SIM as spectra?",bg=TEAL,font=FONT,var=SIM_as_spectra)
    SIM_check.grid(row=2,column=0,columnspan=2)

    SRM_as_spectra = tk.BooleanVar(window_msconvert)
    SRM_check = tk.Checkbutton(window_msconvert,text="SRM as spectra?",bg=TEAL,font=FONT,var=SRM_as_spectra)
    SRM_check.grid(row=3,column=0,columnspan=2)

    window_msconvert.mainloop()




if __name__ == "__main__":
    try:
        main(sys.argv[1])
    except:
        main()