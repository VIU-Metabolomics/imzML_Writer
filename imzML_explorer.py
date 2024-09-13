import pyimzml.ImzMLParser as imzmlp
import matplotlib.pyplot as plt
import tkinter as tk
from tkinter import ttk, filedialog
from RangeSlider.RangeSlider import RangeSliderV
import os
from matplotlib.figure import Figure 
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg, NavigationToolbar2Tk)
from matplotlib.backend_tools import ToolBase, ToolToggleBase 
import warnings
import numpy as np


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

    max_x_dimension = metadata["scan_settings"]["scanSettings1"]["max dimension x"]

    return y_pix_size/x_pix_size, x_pix_size, y_pix_size, max_x_dimension

def plot_ion_image(*_):
    global raw_ion_image, aspect_ratio,x_pix,y_pix, coordinate_map, imzML_object, max_x_dimension
    target_mz = float(mz_entry.get())
    tolerance = float(tolerance_entry.get())
    filename = file_entry.get()
    window=target_mz*tolerance/1e6

    with warnings.catch_warnings(action="ignore"):
        coordinate_map = []
        imzML_object = imzmlp.ImzMLParser(filename=filename,parse_lib='lxml')
    ion_image = imzmlp.getionimage(imzML_object,target_mz,window)
    [aspect_ratio, x_pix, y_pix, max_x_dimension] = get_aspect_ratio(imzML_object)

    #Normalize ion image (or don't) as specified in GUI
    norm_method = normalization_method.get()

    if norm_method == "custom":
        norm_mz = float(normalize_custom_entry.get())
        norm_window = norm_mz * tolerance / 1e6
        norm_grid = imzmlp.getionimage(imzML_object,mz_value=norm_mz,tol=norm_window)
        ion_image = np.divide(ion_image,norm_grid,out=np.zeros_like(ion_image),where=norm_grid!=0)
    elif norm_method == "tic":
        norm_grid = imzmlp.getionimage(imzML_object,mz_value=200,tolerance=9999)
        ion_image = np.divide(ion_image,norm_grid,out=np.zeros_like(ion_image),where=norm_grid!=0)
    
    raw_ion_image = ion_image

    update_ion_image()

def update_ion_image(*_):
    global raw_ion_image,aspect_ratio,x_pix,y_pix

    low_thres = v_bottom.get()
    up_thres=v_top.get()
    target_mz = float(mz_entry.get())
    tolerance = float(tolerance_entry.get())

    ion_image = raw_ion_image

    ##Absolute threshold method
    # ion_image_max = np.max(ion_image)
    # low_cutoff = ion_image_max * low_thres
    # up_cutoff = ion_image_max * up_thres

    ##Percentile method (preferred)
    low_cutoff = np.percentile(ion_image,low_thres*100)
    up_cutoff = np.percentile(ion_image,up_thres*100)


    ion_image = np.where(ion_image > up_cutoff,up_cutoff,ion_image)
    ion_image = np.where(ion_image < low_cutoff,low_cutoff,ion_image)

    fig = Figure(figsize= (1.25*aspect_ratio,1.25),dpi=300,facecolor=TEAL,layout='tight')
    
    plot1 = fig.add_subplot()
    img=plot1.imshow(ion_image,aspect=aspect_ratio,interpolation="none",vmin=0,vmax=up_cutoff)
    plot1.axis('off')
    #fig.colorbar(img,location="top",fraction=0.07)

    try:
        canvas.destroy()
        title_label.destroy()
        export_button.destroy()
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

    export_button=tk.Button(text="Export Image",bg=TEAL,highlightbackground=TEAL,command=lambda:export_image(fig))
    export_button.grid(row=7,column=0,columnspan=3)

    fig.canvas.callbacks.connect('button_press_event',report_coordinates)
    
def export_image(fig):
    file = filedialog.asksaveasfilename(initialdir=os.getcwd())
    if file:
        file_format = file.split(".")[-1]
        fig.savefig(fname=file,
                    transparent=True,
                    dpi=300,
                    format=file_format,
                    bbox_inches="tight",
                    pad_inches=0)

def check_normalization():
    if normalization_method.get() == "custom":
        normalize_custom_entry.grid(row=2,column=6)
        normalize_custom_entry.bind("<Return>",plot_ion_image)
        normalize_custom_entry.bind("<FocusOut>",plot_ion_image)
    else:
        try:
            normalize_custom_entry.grid_remove()
        except:
            pass
    
    try:
        plot_ion_image()
    except:
        pass

def report_coordinates(event):
    global coordinate_map, max_x_dimension, x_pix
    if event.xdata != None:
        scans_per_line = int(max_x_dimension / x_pix)
        line_scan_num = int(round(event.ydata,0))+1
        scan_along_line = int(round(event.xdata,0))+1
        scan_idx = line_scan_num*scans_per_line + scan_along_line
        plot_mass_spectrum(scan_idx)
    


def plot_mass_spectrum(scan_idx):
    global imzML_object, mz, intensities
    [mz, intensities] = imzML_object.getspectrum(scan_idx)

    fig_spectrum = Figure(figsize=(4,4),dpi=100,facecolor=TEAL,layout='tight')

    plot2 = fig_spectrum.add_subplot()
    plot2.plot(mz,intensities)
    plot2.set_xlabel("m/z")
    plot2.set_ylabel("Intensity")

    try:
        canvas_mass_spectrum.destroy()
    except:
        pass

    canvas_mass_spectrum = FigureCanvasTkAgg(fig_spectrum)
    canvas_mass_spectrum.draw()
    toolbar = NavigationToolbar2Tk(canvas_mass_spectrum, pack_toolbar=False)
    toolbar.update()
    canvas_mass_spectrum.get_tk_widget().grid(row=5,column=6,columnspan=3)
    toolbar.grid(row=6,column=6,columnspan=3)

    fig_spectrum.canvas.callbacks.connect("button_press_event",change_target_mz)

def change_target_mz(event):
    new_mz = event.xdata
    match_idx = (np.abs(mz - new_mz)).argmin()
    new_mz = mz[match_idx]

    if new_mz != None:
        mz_entry.delete(0,tk.END)
        mz_entry.insert(0,round(new_mz,4))
        plot_ion_image()







window = tk.Tk()
window.title("IMZML Explorer")
# window.geometry("900x500")
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

##Normalization buttons
normalize_custom_entry=tk.Entry(highlightbackground=TEAL,background=BEIGE,fg="black",justify='center')

normalization_method = tk.StringVar()
no_normalization = tk.Radiobutton(bg=TEAL,command=check_normalization,fg="white",text="No Normalization",variable=normalization_method,value="none")
no_normalization.grid(row=1,column=4)
no_normalization.select()
custom_method = tk.Radiobutton(bg=TEAL,command=check_normalization,fg="white",text="Custom Normalize",variable=normalization_method,value="custom")
custom_method.grid(row=2,column=4)
tic_method = tk.Radiobutton(bg=TEAL,command=check_normalization,fg="white",text="TIC Normalize",variable=normalization_method,value="TIC")
tic_method.grid(row=3,column=4)

##Slider
v_top = tk.DoubleVar(value=0.9)
v_bottom = tk.DoubleVar(value=0.05)
v_slider = RangeSliderV(window,[v_bottom,v_top],padY=12,bgColor=TEAL,valueSide="RIGHT",font_color='#ffffff',font_family="Helvetica",line_s_color=BEIGE,digit_precision='.2f',step_size=0.01)
v_slider.grid(row=4,column=4,rowspan=4)
v_top.trace_add('write',update_ion_image)
v_bottom.trace_add('write',update_ion_image)

window.mainloop()
