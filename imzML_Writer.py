##Standalone notes - Runs ok with no gui_functions
##Compile with: 
# pyinstaller --noconfirm --windowed --add-data=/Users/josephmonaghan/Documents/nanoDESI_raw_to_imzml/Images/Logo-01.png:./Images imzML_Writer.py

import tkinter as tk
from tkinter import ttk, filedialog
import os
from gui_functions import *
import threading
import imzML_Scout as scout
import sys
import time

timing_mode = False

##Colors and FONTS
TEAL = "#2da7ad"
BEIGE = "#dbc076"
GREEN = "#22d10f"
FONT = ("HELVETICA", 18, 'bold')


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

        if FILE_TYPE != "mzML":
            mzML_process.grid_remove()
            imzML_metadata.grid_remove()
        elif FILE_TYPE == "mzML":
            full_process.grid_remove()
            imzML_metadata.grid_remove()
        elif FILE_TYPE == "imzML":
            full_process.grid_remove()
            mzML_process.grid_remove()

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
    RAW_to_mzML(path=CD_entry.get(),sl=get_os())
    RAW_progress.config(mode="indeterminate")
    RAW_progress.start()
    follow_raw_progress(file_type)

def follow_raw_progress(raw_filetype):
    global tic
    files = os.listdir(CD_entry.get())
    num_raw_files = 0
    num_mzML_files = 0

    for file in files:
        if file.startswith(".")==False:
            if f".{raw_filetype}" in file:
                num_raw_files+=1
            elif "mzML" in file:
                num_mzML_files+=1
    progress = int(num_mzML_files * 100 / num_raw_files)
    if progress > 0:
        RAW_progress.stop()
        RAW_progress.config(mode="determinate",value=progress)
        # RAW_progress.config(value=progress)

    if progress < 100:
        window.after(3000,lambda:follow_raw_progress(raw_filetype))
    elif progress >= 100:
        if timing_mode:
            global tic
            toc = time.time()
            print(f"RAW to mzML: {round(toc - tic,1)}s")
        slashes = get_os()
        clean_raw_files(path=CD_entry.get(),sl=slashes,file_type=raw_filetype)
        RAW_label.config(fg=GREEN)

        slashes = get_os()
        new_path = fr"{CD_entry.get()}{slashes}Output mzML Files"
        CD_entry.delete(0,tk.END)
        CD_entry.insert(0,new_path)
        populate_list(CD_entry.get())

        mzML_to_imzML()

    
def mzML_to_imzML():
    ##Run main conversion script from mzML to imzML, stop at annotation stage
    cur_path = CD_entry.get()
    write_imzML_progress.config(mode="indeterminate")
    write_imzML_progress.start()
    if os.path.basename(cur_path) != "Output mzML Files":
        clean_raw_files(cur_path,get_os(),"     ")
        cur_path = os.path.join(cur_path,"Output mzML Files")
    
    sl = get_os()
    path_name=fr"{cur_path}{sl}"
    thread = threading.Thread(target=lambda:mzML_to_imzML_convert(PATH=path_name,progress_target=write_imzML_progress,LOCK_MASS=lock_mass_entry.get()))
    thread.daemon=True
    thread.start()
    check_imzML_completion(thread)
    
def check_imzML_completion(thread):
    if thread.is_alive():
        window.after(2000,check_imzML_completion,thread)
    else:
        if timing_mode:
            global tic
            toc = time.time()
            print(f"mzML to imzML: {round(toc - tic,1)}s")
        write_imzML_Label.config(fg=GREEN)

        full_path = CD_entry.get()
        slash = get_os()
        new_path = full_path.split(fr"{slash}Output mzML Files")[0]
        CD_entry.delete(0,tk.END)
        CD_entry.insert(0,new_path)
        populate_list(os.getcwd())

        write_metadata(path_in="indirect")

def write_metadata(path_in="direct"):
    global path_to_models
    Annotate_progress.config(mode="indeterminate")
    Annotate_progress.start()
    slashes = get_os()
    if path_in == "direct":
        path_to_models = filedialog.askdirectory(initialdir=os.getcwd())
    else:
        path_to_models = fr"{CD_entry.get()}{slashes}Output mzML Files"
    
    thread = threading.Thread(target=lambda:imzML_metadata_process(path_to_models,slashes,x_speed=int(speed_entry.get()),y_step=int(Y_step_entry.get()),tgt_progress=Annotate_progress,path=CD_entry.get()))
    thread.daemon=True
    thread.start()

    check_metadata_completion(thread)

def check_metadata_completion(thread):
    global path_to_models
    if thread.is_alive():
        window.after(2000,check_metadata_completion,thread)
    else:
        if timing_mode:
            global tic
            toc = time.time()
            print(f"imzML metadata: {round(toc - tic,1)}s")
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
    tgt_file = file_list.selection_get()
    if tgt_file.split(".")[-1]=="ibd":
        file_start = tgt_file.split("ibd")[0]
        tgt_file = file_start+"imzML"
    path = CD_entry.get()
    file_path = f"{path}/{tgt_file}"
    scout.main(_tgt_file=file_path)
    

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

window = tk.Tk()
window.title("IMZML WRITER")
window.config(padx=5,pady=5,bg=TEAL)
style = ttk.Style()
style.theme_use('clam')



##Logo
try:
    canvas = tk.Canvas(width = 313,height=205,bg=TEAL,highlightthickness=0)
    img = tk.PhotoImage(file="./Images/Logo-01.png")
    canvas.create_image(313/2, 205/2,image=img)
    canvas.grid(column=0,row=0,columnspan=2)
except:
    try:
        canvas = tk.Canvas(width = 313,height=205,bg=TEAL,highlightthickness=0)
        img = tk.PhotoImage(file=resource_path("./Images/Logo-01.png"))
        canvas.create_image(313/2, 205/2,image=img)
        canvas.grid(column=0,row=0,columnspan=2)
    except:
        pass



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
imzML_metadata.grid(row=3,column=4,columnspan=3)

##Visualize .imzML
visualize = tk.Button(text="View imzML",bg=TEAL,highlightbackground=TEAL,command=launch_scout)
visualize.grid(row=4,column=4,columnspan=3)

window.mainloop()