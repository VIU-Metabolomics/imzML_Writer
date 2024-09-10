import tkinter as tk
from tkinter import ttk, filedialog
from sys import platform
import os
from gui_functions import *
import threading



##Colors and FONTS
TEAL = "#2da7ad"
BEIGE = "#dbc076"
GREEN = "#22d10f"
FONT = ("HELVETICA", 18, 'bold')


##UI Functions
def get_path():
    global FILE_TYPE
    directory = filedialog.askdirectory(initialdir=os.getcwd())

    if directory:
        CD_entry.delete(0,tk.END)
        CD_entry.insert(0,directory)

        populate_list(directory)
        FILE_TYPE = get_file_types(directory)

def populate_list(dir):
    files = os.listdir(dir)
    ticker = 0
    for file in files:
        if not file.startswith("."):
            file_list.insert(ticker,file)
            ticker+=1

def get_file_types(dir):
    files = os.listdir(dir) 
    for file in files:
        split_file = file.split(".")
        file_type = split_file[-1]

    file_type_label = tk.Label(text=f"File type: .{file_type}",bg=TEAL,font=FONT)
    file_type_label.grid(row=1,column=3,columnspan=3)
    return file_type

def get_os():
    if platform == "linux" or platform == "darwin":
        slashes = "/"
    else:
        slashes= "'\'"

    return slashes

def full_convert():
    #RAW to mzML conversion, then call mzML to imzML function
    RAW_to_mzML(path=CD_entry.get())
    follow_raw_progress()

def follow_raw_progress():
    files = os.listdir(CD_entry.get())
    num_raw_files = 0
    num_mzML_files = 0
    for file in files:
        if ".raw" in file:
            num_raw_files+=1
        elif ".mzML" in file:
            num_mzML_files+=1

    progress = int(num_mzML_files * 100 / num_raw_files)
    RAW_progress.config(value=progress)

    if progress < 100:
        window.after(3000,follow_raw_progress)
    elif progress >= 100:
        slashes = get_os()
        clean_raw_files(path=CD_entry.get(),sl=slashes)
        RAW_label.config(fg=GREEN)

        slashes = get_os()
        new_path = CD_entry.get()+slashes+"Output mzML Files"
        CD_entry.delete(0,tk.END)
        CD_entry.insert(0,new_path)

        mzML_to_imzML()


    
    

    
    #clean_raw_files(path=CD_entry.get(),sl=slashes)
    

def mzML_to_imzML():
    ##Run main conversion script from mzML to imzML, stop at annotation stage
    sl = get_os()
    path_name=CD_entry.get()+sl
    thread = threading.Thread(target=lambda:mzML_to_imzML_convert(PATH=path_name,progress_target=write_imzML_progress))
    thread.daemon=True
    thread.start()
    check_imzML_completion(thread)
    
    

def check_imzML_completion(thread):
    if thread.is_alive():
        window.after(2000,check_imzML_completion,thread)
    else:
        write_imzML_Label.config(fg=GREEN)

        full_path = CD_entry.get()
        slash = get_os()
        new_path = full_path.split(slash+"Output mzML Files")[0]
        CD_entry.delete(0,tk.END)
        CD_entry.insert(0,new_path)

        write_metadata(path_in="indirect")





def write_metadata(path_in="direct"):
    slashes = get_os()
    if path_in == "direct":
        path_to_models = filedialog.askdirectory(initialdir=os.getcwd())
    else:
        path_to_models = CD_entry.get()+slashes+"Output mzML Files"
    
    thread = threading.Thread(target=lambda:imzML_metadata_process(path_to_models,slashes,x_speed=int(speed_entry.get()),y_step=int(Y_step_entry.get()),tgt_progress=Annotate_progress))
    thread.daemon=True
    thread.start()

    check_metadata_completion(thread)

def check_metadata_completion(thread):
    if thread.is_alive():
        window.after(2000,check_metadata_completion,thread)
    else:
        Annotate_recalibrate_label.config(fg=GREEN)


    
    


window = tk.Tk()
window.title("IMZML WRITER")
window.geometry("750x410")
window.config(padx=5,pady=5,bg=TEAL)
style = ttk.Style()
style.theme_use('clam')



##Logo
canvas = tk.Canvas(width = 313,height=205,bg=TEAL,highlightthickness=0)
img = tk.PhotoImage(file="./Images/Logo-01.png")
canvas.create_image(313/2, 205/2,image=img)
canvas.grid(column=0,row=0,columnspan=2)


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
Annotate_recalibrate_label = tk.Label(text="Metadata/Recalibrate:",bg=TEAL,font=FONT)
Annotate_recalibrate_label.grid(row=7,column=0)

Annotate_progress=ttk.Progressbar(length=525,style="success.Striped.Horizontal.TProgressbar")
Annotate_progress.grid(row=7,column=1,columnspan=5)



#Listbox for files in target folder
file_list = tk.Listbox(window,bg=BEIGE,fg="black",height=10,highlightcolor=TEAL,width=35)
file_list.grid(row=0,column=4,rowspan=2,columnspan=3)

##Processing buttons
full_process = tk.Button(text="Full Conversion",bg=TEAL,highlightbackground=TEAL,command=full_convert)
full_process.grid(row=2,column=4)

mzML_process = tk.Button(text="mzML to imzML",bg=TEAL,highlightbackground=TEAL,command=mzML_to_imzML)
mzML_process.grid(row=2,column=5)

imzML_metadata = tk.Button(text="Write imzML metadata",bg=TEAL,highlightbackground=TEAL,command=write_metadata)
imzML_metadata.grid(row=3,column=4,columnspan=3)

window.mainloop()