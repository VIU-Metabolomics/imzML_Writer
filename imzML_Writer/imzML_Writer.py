##Standalone notes - Runs ok with no gui_functions
##Compile with: 
# pyinstaller --noconfirm --windowed --add-data=/Users/josephmonaghan/Documents/nanoDESI_raw_to_imzml/Images/Logo-01.png:./Images imzML_Writer.py

import tkinter as tk
from tkinter import ttk, filedialog,messagebox
import os
from imzML_Writer.utils import *
import threading
import imzML_Writer.imzML_Scout as scout
import sys
import time
from importlib import resources

timing_mode = False
PC_compiled = False
_on_startup=True
tries = 0

##Colors and FONTS
TEAL = "#2da7ad"
BEIGE = "#dbc076"
GREEN = "#22d10f"
FONT = ("HELVETICA", 18, 'bold')

def gui(tgt_dir:str=None):
    global _on_startup
    """Main control loop for imzML_Writer GUI. No arguments required, but if a directory is passed imzML writer will launch with that directory opened.
    
    :param tgt_dir: (optional) - initial directory for imzML Writer to open in (str)"""

    ##UI Functions
    def get_path():
        """No arguments, prompts the user via dialog box for the directory containing the data to be processed.
        Will call populate_list() method to show files in the UI listbox"""
        global FILE_TYPE
        directory = filedialog.askdirectory(initialdir=os.getcwd())

        if directory:
            CD_entry.delete(0,tk.END)
            CD_entry.insert(0,directory)

            populate_list(directory)
            FILE_TYPE = get_file_types(directory)

            if FILE_TYPE.lower() != "mzML".lower():
                mzML_process.grid_remove()
                imzML_metadata.grid_remove()
            elif FILE_TYPE.lower() == "mzML".lower():
                full_process.grid_remove()
                imzML_metadata.grid_remove()
            elif FILE_TYPE.lower() == "imzML".lower():
                full_process.grid_remove()
                mzML_process.grid_remove()

    def populate_list(dir:str):
        """takes an argument dir and populates the UI listbox based on its contents
        dir: pathname for active directory as a string"""
        file_list.delete(0,tk.END)
        files = os.listdir(dir)
        human_sort(files)
        # files.sort()
        ticker = 0
        for file in files:
            if not file.startswith(".") and not file.endswith(".ibd"):
                if file.endswith(".imzML"):
                    search_txt = file.split(".imzML")[0] + ".ibd"
                    if search_txt in files:
                        file_list.insert(ticker,file)
                    ticker+=1
                else:                
                    file_list.insert(ticker,file)
                    ticker+=1

    def get_file_types(dir) -> str:
        """dir: pathname for active directory
        returns file_type as a str
        [taken as first non-hidden (i.e. doesn't start with ".") file in the directory]"""
        files = os.listdir(dir) 
        for file in files:
            split_file = file.split(".")
            file_type = split_file[-1]

        file_type_label = tk.Label(text=f"File type: .{file_type}",bg=TEAL,font=FONT)
        file_type_label.grid(row=1,column=3,columnspan=3)
        return file_type

    def get_os() -> str:
        """Legacy code - returns "/" """
        return "/"

    def full_convert():
        """Initiates file conversion from vendor format in the current directory"""
        if timing_mode:
            global tic
            tic = time.time()
        #RAW to mzML conversion, then call mzML to imzML function
        file_type = get_file_type(CD_entry.get())
        RAW_to_mzML(path=CD_entry.get(),sl=get_os(),write_mode=write_option_var.get())
        RAW_progress.config(mode="indeterminate")
        RAW_progress.start()
        follow_raw_progress(file_type)

    def follow_raw_progress(raw_filetype:str):
        """Monitors progress of raw file conversion to mzML by comparing the number of raw vendor files to mzML files in the working directory
        Input:
        raw_filetype: string specifying the file extension of the raw files"""
        global tic, tries

        #Retrieve list of files in working directory
        files = os.listdir(CD_entry.get())
        num_raw_files = 0
        num_mzML_files = 0
        mzML_files = []

        ##Iterate through each file, counting each type
        for file in files:
            if file.startswith(".")==False:
                if f".{raw_filetype}" in file:
                    num_raw_files+=1
                elif "mzML" in file:
                    num_mzML_files+=1
                    mzML_files.append(file)
        
        #Calculate progress based on number of each
        progress = int(num_mzML_files * 100 / num_raw_files)
        
        #Check that the mzML files are all roughly the same size (smallest at least >75% the size of the mean) to ensure
        #last file actually finished
        sizes = []
        for file in mzML_files:
            file_size = os.path.getsize(f"{CD_entry.get()}/{file}")
            sizes.append(file_size)
        
        last_one_ready=False
        tries_threshold = 3
        if progress >= 100:
            if len(sizes) > 0:
                tries+=1
                if not np.min(sizes) < np.mean(sizes)*0.85 or tries > tries_threshold:
                    last_one_ready = True
                
        #Update progress bar to show how many mzML files are finished compared to total
        if progress > 0:
            RAW_progress.stop()
            RAW_progress.config(mode="determinate",value=progress)

        #If not finished, start this function over again after waiting 3 seconds for more progress to be made
        if progress < 100 or not last_one_ready:
            window.after(3000,lambda:follow_raw_progress(raw_filetype))
        #If finished, move on to the next stage in the process
        elif progress >= 100 and last_one_ready:

            
            if timing_mode:
                global tic
                toc = time.time()
                print(f"RAW to mzML: {round(toc - tic,1)}s")
            slashes = get_os()
            #Clean up file structure by placing mzML and raw files in separate folders
            clean_raw_files(path=CD_entry.get(),file_type=raw_filetype)
            #Make it obvious the process is complete by changing the label to green
            RAW_label.config(fg=GREEN)

            slashes = get_os()
            ##Change the directory to the new mzML folder
            new_path = fr"{CD_entry.get()}{slashes}Output mzML Files"
            CD_entry.delete(0,tk.END)
            CD_entry.insert(0,new_path)
            populate_list(CD_entry.get())

            ##Initiate the next step in the pipeline
            window.after(500,mzML_to_imzML())

        
    def mzML_to_imzML():
        """Run main conversion script from mzML to imzML, stop at annotation stage"""
        cur_path = CD_entry.get()

        ##Retrieve settings
        duplicate_spectra = duplicate_bool.get()
        zero_indexed = index_bool.get()
        search_tolerance = search_tol.get()
        try:
            search_tolerance = float(search_tolerance)
        except:
            search_tolerance = 20
            messagebox.showwarning(title="ERROR",message="Invalid search tolerance specified - proceeding with 20 ppm")

        ##Start the progress bar whirling to indicate to user that things are working
        write_imzML_progress.config(mode="indeterminate")
        write_imzML_progress.start()
        if os.path.basename(cur_path) != "Output mzML Files":
            clean_raw_files(cur_path,"     ")
            cur_path = os.path.join(cur_path,"Output mzML Files")
        

        ##Start thread to convert the process
        thread = threading.Thread(
            target=lambda:mzML_to_imzML_convert(
                PATH=cur_path,
                progress_target=write_imzML_progress,
                LOCK_MASS=lock_mass_entry.get(),
                TOLERANCE=search_tolerance,
                no_duplicating=duplicate_spectra,
                zero_indexed=zero_indexed))
        thread.daemon=True
        thread.start()

        ##Start monitoring process to see if imzML files have been successfully written
        check_imzML_completion(thread)
        
    def check_imzML_completion(thread):
        """monitors imzML conversion process by checking if the thread is still alive"""
        if thread.is_alive():
            window.after(2000,check_imzML_completion,thread) #If thread is still going, check back again in 2 seconds
        else: #Otherwise, move on to the next step
            if timing_mode:
                global tic
                toc = time.time()
                print(f"mzML to imzML: {round(toc - tic,1)}s")
            #Update progress bar label to green to make it obvious things have completed
            write_imzML_Label.config(fg=GREEN)

            ##Update folder to directory where the intermediate imzML files are saved (directory w/ the python code)
            full_path = CD_entry.get()
            slash = get_os()
            new_path = full_path.split(fr"{slash}Output mzML Files")[0]
            CD_entry.delete(0,tk.END)
            CD_entry.insert(0,new_path)
            populate_list(os.getcwd())

            ##Initiate the metadata writing process
            write_metadata(path_in="indirect")

    def write_metadata(path_in:str="direct"):
        """Initiates metadata writing on the intermediate mzML files"""
        global path_to_models

        #Start progress bar whirring to indicate process has started to user
        Annotate_progress.config(mode="indeterminate")
        Annotate_progress.start()
        slashes = get_os()
        #If conversion was called directly, prompt user for source mzml files to retrieve metadata from
        if path_in == "direct":
            path_to_models = filedialog.askdirectory(initialdir=os.getcwd())
        else:
            path_to_models = fr"{CD_entry.get()}{slashes}Output mzML Files"
        
        #Start the annotation in a new thread
        thread = threading.Thread(
            target=lambda:imzML_metadata_process(
                model_files=path_to_models,
                x_speed=int(speed_entry.get()),
                y_step=int(Y_step_entry.get()),
                tgt_progress=Annotate_progress,
                path=CD_entry.get()))
        thread.daemon=True
        thread.start()

        ##Monitor the annotation
        check_metadata_completion(thread)

    def check_metadata_completion(thread):
        """Follows metadata writing process, moving on if thread has terminated or checking again if it hasn't"""
        global path_to_models
        ##If thread is still going, run this function again after waiting 2 seconds
        if thread.is_alive():
            window.after(2000,check_metadata_completion,thread)
        else: ##Otherwise, move on
            if timing_mode:
                global tic
                toc = time.time()
                print(f"imzML metadata: {round(toc - tic,1)}s")
            ##Update label to green, update file list to indicate process completion to user
            Annotate_recalibrate_label.config(fg=GREEN)
            model_file_list = os.listdir(path_to_models)
            model_file_list.sort()

            str_array = [letter for letter in model_file_list[0]]
            OUTPUT_NAME = "".join(str_array)
            while OUTPUT_NAME not in model_file_list[-1]:
                str_array.pop(-1)
                OUTPUT_NAME = "".join(str_array)

            new_path = f"{CD_entry.get()}/{OUTPUT_NAME}"
            CD_entry.delete(0,tk.END)
            CD_entry.insert(0,new_path)
            populate_list(CD_entry.get())
                
            

    def launch_scout():
        """Launches imzML_Scout.py when the user selects an imzML file on the indicated file"""
        tgt_file = file_list.selection_get()
        if tgt_file.split(".")[-1]=="ibd":
            file_start = tgt_file.split("ibd")[0]
            tgt_file = file_start+"imzML"
        path = CD_entry.get()
        file_path = f"{path}/{tgt_file}"
        if PC_compiled:
            print(f"Attempting to open imzML - attempt #{1}")
            res = subprocess.run(["imzML_Scout",file_path])
            i = 1
            while res.returncode != 0:
                print(f"Return code: {res.returncode}")
                print(res)
                i+=1
                print(f"Attempting to open imzML - attempt #{i}")
                res = subprocess.run(["imzML_Scout",file_path])
        else:
            scout.main(tgt_file=file_path)
        

    def resource_path(relative_path):
        """Future placeholder for making standalone application work"""
        try:
            base_path = sys._MEIPASS
        except Exception:
            base_path = os.path.abspath(".")

        return os.path.join(base_path, relative_path)

    
    def launch_advanced():
        def update_search_tol(*args):
            try:
                float(lock_mass_search_tol_entry.get())
                search_tol.set(lock_mass_search_tol_entry.get())
            except:
                messagebox.showwarning(title="ERROR",message="Search tolerance must be specified as number")
        
        def update_index_bool(*args):
            if not index_bool.get():
                index_bool.set(True)
            else:
                index_bool.set(False)
        
        def update_duplicate_bool(*args):
            if not duplicate_bool.get():
                duplicate_bool.set(True)
            else:
                duplicate_bool.set(False)

        advanced_window = tk.Tk()
        advanced_window.title("Advanced Options...")
        advanced_window.config(padx=5,pady=5,bg=TEAL)

        #0 vs 1 indexed (checkbox, 1 default, 0 optional)
        index_check = tk.Checkbutton(advanced_window,text="0-Indexed?",bg=TEAL,font=FONT,variable=index_bool,command=update_index_bool)
        index_check.grid(row=1,column=1,columnspan=2)
        if index_bool.get():
            index_check.select()

        #Duplicate pixels? (checkbox, duplicate default)
        duplicate_check = tk.Checkbutton(advanced_window,text="no duplicated spectra?",bg=TEAL,font=FONT,command=update_duplicate_bool)
        duplicate_check.grid(row=2,column=1,columnspan=2)
        if duplicate_bool.get():
            duplicate_check.select()

        #Lock mass search tolerance (entry, 20 ppm default)
        lock_mass_search_tol_label = tk.Label(advanced_window,text="Lock mass search tolerance (ppm):",bg=TEAL,font=FONT)
        lock_mass_search_tol_entry = tk.Entry(advanced_window,text="Enter tolerance here",highlightbackground=TEAL,background=BEIGE,fg="black",justify='center')
        lock_mass_search_tol_entry.insert(0,search_tol.get())
        lock_mass_search_tol_entry.bind("<Return>",update_search_tol)
        lock_mass_search_tol_entry.bind("<FocusOut>",update_search_tol)

        lock_mass_search_tol_entry.grid(row=3,column=2)
        lock_mass_search_tol_label.grid(row=3,column=1)


            


    ##Build tkinter window
    window = tk.Tk()
    window.title("IMZML WRITER")
    window.config(padx=5,pady=5,bg=TEAL)
    style = ttk.Style()
    style.theme_use('clam')



    ##Logo
    try:
        canvas = tk.Canvas(width = 313,height=205,bg=TEAL,highlightthickness=0)
        img = tk.PhotoImage(file=resource_path("./Images/Logo-01.png"))
        window.iconbitmap(resource_path("./Images/imzML_Writer.ico"))
        canvas.create_image(313/2, 205/2,image=img)
        canvas.grid(column=0,row=0,columnspan=2)
    except:
        try:
            canvas = tk.Canvas(width = 313,height=205,bg=TEAL,highlightthickness=0)
            with resources.path('imzML_Writer.Images','Logo-01.png') as path:
                img=tk.PhotoImage(file=resource_path(path))
                canvas.create_image(313/2, 205/2,image=img)
                canvas.grid(column=0,row=0,columnspan=2)
            with resources.path('imzML_Writer.Images','imzML_Writer.ico') as path:
                window.iconbitmap(resource_path(path))
        except:
            pass
    
    ##Initialize defaults for advanced options
    search_tol = tk.StringVar(window)
    search_tol.set("20")
    duplicate_bool = tk.BooleanVar(window)
    duplicate_bool.set(False)
    index_bool = tk.BooleanVar(window)
    index_bool.set(False)

    ##Scan-speed entry
    speed_label=tk.Label(text="x scan speed (µm/s):",bg=TEAL,font=FONT)
    speed_entry = tk.Entry(text="Enter speed here",highlightbackground=TEAL,background=BEIGE,fg="black",justify='center')
    speed_entry.insert(0,"40")

    speed_label.grid(row=2,column=0)
    speed_entry.grid(row=2,column=1)

    ##Y-step entry
    Y_step_label=tk.Label(text="y step (µm):",bg=TEAL,font=FONT)
    Y_step_entry=tk.Entry(highlightbackground=TEAL,background=BEIGE,fg="black",justify='center')
    Y_step_entry.insert(0,"150")

    Y_step_label.grid(row=3,column=0)
    Y_step_entry.grid(row=3,column=1)

    ##Lock mass entry
    lock_mass_label=tk.Label(text="Lock Mass:",bg=TEAL,font=FONT)
    lock_mass_entry=tk.Entry(highlightbackground=TEAL,background=BEIGE,fg="black",justify='center')
    lock_mass_entry.insert(0,"0")

    lock_mass_label.grid(row=4,column=0)
    lock_mass_entry.grid(row=4,column=1)

    ##Choose Directory Button
    CD_button = tk.Button(text="Select Folder",bg=TEAL,highlightbackground=TEAL,command=get_path)
    CD_button.grid(row=1,column=0)

    CD_entry = tk.Entry(text="Enter Directory Here",highlightbackground=TEAL,background=BEIGE,fg="black",justify='center')
    CD_entry.grid(row=1,column=1)

    ##RAW conversion progress bar
    RAW_label = tk.Label(text="RAW --> mzML:",bg=TEAL,font=FONT)
    RAW_label.grid(row = 5,column=0)

    RAW_progress = ttk.Progressbar(length=525,style="danger.Striped.Horizontal.TProgressbar")
    RAW_progress.grid(row=5,column=1,columnspan=5)


    ##Write imzML progress bar
    write_imzML_Label=tk.Label(text="Write imzML:",bg=TEAL,font=FONT)
    write_imzML_Label.grid(row=6,column=0)

    write_imzML_progress=ttk.Progressbar(length=525,style="info.Striped.Horizontal.TProgressbar")
    write_imzML_progress.grid(row=6,column=1,columnspan=5)


    ##Annotate / m/z recalibration progress bar:
    Annotate_recalibrate_label = tk.Label(text="Metadata:",bg=TEAL,font=FONT)
    Annotate_recalibrate_label.grid(row=7,column=0)

    Annotate_progress=ttk.Progressbar(length=525,style="success.Striped.Horizontal.TProgressbar")
    Annotate_progress.grid(row=7,column=1,columnspan=5)



    #Listbox for files in target folder
    file_list = tk.Listbox(window,bg=BEIGE,fg="black",height=10,highlightcolor=TEAL,width=35,justify='left')
    file_list.grid(row=0,column=4,rowspan=2,columnspan=3)

    ##Processing buttons
    full_process = tk.Button(text="Full Conversion",bg=TEAL,highlightbackground=TEAL,command=full_convert)
    full_process.grid(row=2,column=4)

    mzML_process = tk.Button(text="mzML to imzML",bg=TEAL,highlightbackground=TEAL,command=mzML_to_imzML)
    mzML_process.grid(row=2,column=5)

    imzML_metadata = tk.Button(text="Write imzML metadata",bg=TEAL,highlightbackground=TEAL,command=write_metadata)
    imzML_metadata.grid(row=3,column=4)

    #Advanced option
    adv_options = tk.Button(text="Advanced Options...",bg=TEAL,highlightbackground=TEAL,command=launch_advanced)
    adv_options.grid(row=3,column=5)
    

    ##Visualize .imzML
    visualize = tk.Button(text="View imzML",bg=TEAL,highlightbackground=TEAL,command=launch_scout)
    visualize.grid(row=4,column=5,columnspan=2)

    ##Centroid or Profile?
    data_writing_options = ["Centroid", "Profile"]
    write_option_var = tk.StringVar(window)
    write_option_var.set(data_writing_options[0])
    write_options_dropdown=tk.OptionMenu(window,write_option_var,*data_writing_options)
    write_options_dropdown.grid(row=4,column=4)

    if _on_startup:
        _on_startup = False
        if tgt_dir != None:
            CD_entry.delete(0,tk.END)
            CD_entry.insert(0,tgt_dir)

            populate_list(tgt_dir)
            FILE_TYPE = get_file_types(tgt_dir)

            if FILE_TYPE.lower() != "mzML".lower():
                mzML_process.grid_remove()
                imzML_metadata.grid_remove()
            elif FILE_TYPE.lower() == "mzML".lower():
                full_process.grid_remove()
                imzML_metadata.grid_remove()
            elif FILE_TYPE.lower() == "imzML".lower():
                full_process.grid_remove()
                mzML_process.grid_remove()

    window.mainloop()

if __name__=="__main__":
    try:
        gui(sys.argv[1])
    except:
        gui()