import pyimzml.ImzMLParser as imzmlp
import matplotlib.pyplot as plt
import tkinter as tk
from tkinter import ttk, filedialog
import os
from matplotlib.figure import Figure 
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg, NavigationToolbar2Tk) 
import warnings

##Colors and FONTS
TEAL = "#2da7ad"
BEIGE = "#dbc076"
GREEN = "#22d10f"
FONT = ("HELVETICA", 18, 'bold')

def browse_for_file():
    path_to_file = filedialog.askopenfilename(initialdir=os.getcwd())
    file_entry.delete(0,tk.END)
    file_entry.insert(0,path_to_file)

def get_aspect_ratio(img_file):
    metadata = img_file.metadata.pretty()
    x_pix_size = metadata["scan_settings"]["scanSettings1"]["pixel size (x)"]
    y_pix_size = metadata["scan_settings"]["scanSettings1"]["pixel size y"]
    return y_pix_size/x_pix_size, x_pix_size, y_pix_size

def plot_ion_image(*_):
    target_mz = float(mz_entry.get())
    tolerance = float(tolerance_entry.get())
    filename = file_entry.get()
    window=target_mz*tolerance/1e6

    with warnings.catch_warnings(action="ignore"):
        imzML_object = imzmlp.ImzMLParser(filename=filename,parse_lib='lxml')
    ion_image = imzmlp.getionimage(imzML_object,target_mz,window)
    [aspect_ratio, x_pix, y_pix] = get_aspect_ratio(imzML_object)
    

    fig = Figure(figsize= (1.25*aspect_ratio,1.25),dpi=300,facecolor=TEAL,layout='tight')
    
    plot1 = fig.add_subplot()
    plot1.imshow(ion_image,aspect=aspect_ratio)
    plot1.axis('off')

    try:
        canvas.destroy()
        title_label.destroy()
    except:
        pass

    canvas = FigureCanvasTkAgg(fig)
    canvas.draw()
    toolbar = NavigationToolbar2Tk(canvas, pack_toolbar=False)
    toolbar.update()
    canvas.get_tk_widget().grid(row=5,column=0,columnspan=3)

    title_string = f"{int(round(x_pix,0))} µm x {int(round(y_pix,1))} µm pixels; m/z {target_mz} @ {tolerance} ppm"
    title_label = tk.Label(text=title_string,bg=TEAL,font=FONT)
    title_label.grid(row=6,column=0,columnspan=3)
    
def plot_mass_spectrum():
    pass

window = tk.Tk()
window.title("IMZML Explorer")
window.geometry("900x500")
window.config(padx=5,pady=5,bg=TEAL)
style = ttk.Style()
style.theme_use('clam')

##Target image:
file_var = tk.StringVar()
file_var.set("")
file_button=tk.Button(text="Browse for file",bg=TEAL,highlightbackground=TEAL, command=browse_for_file)
file_entry = tk.Entry(textvariable=file_var,highlightbackground=TEAL,background=BEIGE,fg="black",justify='center')
file_var.trace_add('write',plot_ion_image)

file_button.grid(row=1,column=0)
file_entry.grid(row=1,column=1)


##mz entry
mz_var = tk.StringVar()
mz_var.set("104.1069")
mz_label=tk.Label(text="Target m/z:",bg=TEAL,font=FONT)
mz_entry = tk.Entry(textvariable=mz_var,highlightbackground=TEAL,background=BEIGE,fg="black",justify='center')
#mz_var.trace_add('write',plot_ion_image)
mz_entry.bind("<Return>",plot_ion_image)
mz_entry.bind("<FocusOut>",plot_ion_image)

mz_label.grid(row=2,column=0)
mz_entry.grid(row=2,column=1)

##Tolerance entry
tol_var = tk.StringVar()
tol_var.set("10")
tolerance_label=tk.Label(text="Tolerance (ppm):",bg=TEAL,font=FONT)
tolerance_entry = tk.Entry(textvariable=tol_var,highlightbackground=TEAL,background=BEIGE,fg="black",justify='center')
#tol_var.trace_add('write',plot_ion_image)
tolerance_entry.bind("<Return>",plot_ion_image)
tolerance_entry.bind("<FocusOut>",plot_ion_image)

tolerance_label.grid(row=3,column=0)
tolerance_entry.grid(row=3,column=1)

window.mainloop()
