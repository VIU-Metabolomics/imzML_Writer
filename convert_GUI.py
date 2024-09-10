import tkinter as tk
from tkinter import ttk, filedialog
from sys import platform
import os



##Colors
TEAL = "#2da7ad"

FONT = ("HELVETICA", 18, 'bold')


##UI Functions
def get_path():
    directory = filedialog.askdirectory()
    end_directory = directory.split("/")

    if directory:
        CD_entry.delete(0,tk.END)
        CD_entry.insert(0,directory)

        populate_list(directory)

def populate_list(dir):
    files = os.listdir()
    ticker = 0
    for file in files:
        if not file.startswith("."):
            file_list.insert(ticker,file)
            ticker+=1


def get_os():
    global slashes
    if platform == "linux" or platform == "darwin":
        slashes = "/"
    else:
        slashes= "'\'"

    
window = tk.Tk()
window.title("IMZML WRITER")
window.geometry("750x410")
window.config(padx=5,pady=5,bg=TEAL)
style = ttk.Style()
style.theme_use('clam')
style.configure("red.Horizontal.TProgressbar", foreground='red', background=TEAL)


##Logo
canvas = tk.Canvas(width = 313,height=205,bg=TEAL,highlightthickness=0)
img = tk.PhotoImage(file="./Images/Logo-01.png")
canvas.create_image(313/2, 205/2,image=img)
canvas.grid(column=0,row=0,columnspan=2)


##Scan-speed entry
speed_label=tk.Label(text="x scan speed (µm/s):",bg=TEAL,font=FONT)
speed_entry = tk.Entry(text="Enter speed here",highlightbackground=TEAL)

speed_label.grid(row=2,column=0)
speed_entry.grid(row=2,column=1)

##Y-step entry
Y_step_label=tk.Label(text="y step (µm):",bg=TEAL,font=FONT)
Y_step_entry=tk.Entry(text="Enter y step here",highlightbackground=TEAL)

Y_step_label.grid(row=3,column=0)
Y_step_entry.grid(row=3,column=1)

##Lock mass entry
lock_mass_label=tk.Label(text="Lock Mass:",bg=TEAL,font=FONT)
lock_mass_entry=tk.Entry(text="Enter Lock Mass Here",highlightbackground=TEAL)

lock_mass_label.grid(row=4,column=0)
lock_mass_entry.grid(row=4,column=1)

##Choose Directory Button
CD_button = tk.Button(text="Select Folder",bg=TEAL,highlightbackground=TEAL,command=get_path)
CD_button.grid(row=1,column=0)

CD_entry = tk.Entry(text="Enter Directory Here",highlightbackground=TEAL)
CD_entry.grid(row=1,column=1)

##RAW conversion progress bar
RAW_label = tk.Label(text="RAW --> mzML:",bg=TEAL,font=FONT)
RAW_label.grid(row = 5,column=0)

RAW_progress = ttk.Progressbar(length=525,mode="indeterminate")
RAW_progress.grid(row=5,column=1,columnspan=5)
RAW_progress.start()

##Write imzML progress bar
write_imzML_Label=tk.Label(text="Write imzML:",bg=TEAL,font=FONT)
write_imzML_Label.grid(row=6,column=0)

write_imzML_progress=ttk.Progressbar(length=525)
write_imzML_progress.grid(row=6,column=1,columnspan=5)
write_imzML_progress.start()

##Annotate / m/z recalibration progress bar:
Annotate_recalibrate_label = tk.Label(text="Annotate/Recalibrate:",bg=TEAL,font=FONT)
Annotate_recalibrate_label.grid(row=7,column=0)

Annotate_progress=ttk.Progressbar(length=525)
Annotate_progress.grid(row=7,column=1,columnspan=5)
Annotate_progress.start()


#Listbox for files in target folder
file_list = tk.Listbox(window,bg='white',height=10,highlightcolor=TEAL,width=35)
file_list.grid(row=0,column=4,rowspan=2,columnspan=3)

window.mainloop()