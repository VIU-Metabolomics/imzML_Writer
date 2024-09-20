import pyimzml.ImzMLParser as imzmlp
import matplotlib.pyplot as plt
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from RangeSlider.RangeSlider import RangeSliderV
import os
import sys
from matplotlib.figure import Figure 
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg, NavigationToolbar2Tk)
from matplotlib.backend_tools import ToolBase, ToolToggleBase 
import warnings
import numpy as np
import pandas as pd

def main(_tgt_file = ""):
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
        mz_window=target_mz*tolerance/1e6

        with warnings.catch_warnings(action="ignore"):
            # coordinate_map = []
            if "imzML_object" in globals():
                if imzML_object.filename != filename:
                    imzML_object = imzmlp.ImzMLParser(filename=filename,parse_lib='lxml')
            else:
                imzML_object = imzmlp.ImzMLParser(filename=filename,parse_lib='lxml')

        if view_tic_option.get():
            ion_image = imzmlp.getionimage(imzML_object,mz_value=200,tol=9999)
        else:
            ion_image = imzmlp.getionimage(imzML_object,target_mz,mz_window)
        
        [aspect_ratio, x_pix, y_pix, max_x_dimension] = get_aspect_ratio(imzML_object)

        #Normalize ion image (or don't) as specified in GUI
        norm_method = normalization_method.get()
        if norm_method == "custom":
            norm_mz = float(normalize_custom_entry.get())
            norm_window = norm_mz * tolerance / 1e6
            norm_grid = imzmlp.getionimage(imzML_object,mz_value=norm_mz,tol=norm_window)
            ion_image = np.divide(ion_image,norm_grid,out=np.zeros_like(ion_image),where=norm_grid!=0)
        elif norm_method == "TIC":
            norm_grid = imzmlp.getionimage(imzML_object,mz_value=200,tol=9999)
            ion_image = np.divide(ion_image,norm_grid,out=np.zeros_like(ion_image),where=norm_grid!=0)
        
        raw_ion_image = ion_image

        fig = update_ion_image()
        return fig

    def update_ion_image(*_):
        global raw_ion_image,aspect_ratio,x_pix,y_pix,canvas_ionimage,title_label,export_button,b_export,include_TIC_var,fig

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

        if NL_state.get():
            color_NL = norm_value.get()
        else:
            color_NL= up_cutoff

        fig = Figure(dpi=100,facecolor=TEAL,layout='tight')
        
        plot1 = fig.add_subplot()
        plot1.imshow(ion_image,aspect=aspect_ratio,interpolation="none",vmin=0,vmax=color_NL,cmap=cmap_selected.get())
        plot1.axis('off')

        try:
            canvas_ionimage.destroy()
            title_label.destroy()
            # export_button.destroy()
            # b_export.destroy()
            # csv_export.destroy()
            # b_csv_export.destroy()
        except:
            pass

        canvas_ionimage = FigureCanvasTkAgg(fig,master=window_scout)
        canvas_ionimage.draw()
        toolbar = NavigationToolbar2Tk(canvas_ionimage, pack_toolbar=False)
        toolbar.update()
        canvas_ionimage.get_tk_widget().grid(row=5,column=0,columnspan=3)

        title_string=[]
        title_string = f"{int(round(x_pix,0))} µm x {int(round(y_pix,1))} µm pixels; m/z {target_mz} @ {tolerance} ppm"
        title_label = tk.Label(window_scout,text=title_string,bg=TEAL,font=FONT)
        title_label.grid(row=6,column=0,columnspan=4)

        fig.canvas.callbacks.connect('button_press_event',report_coordinates)
        return fig

    def export_csv():
        global raw_ion_image
        dataframe = pd.DataFrame(raw_ion_image)
        path = os.path.dirname(file_entry.get()) 
        file_name = filedialog.asksaveasfilename(initialdir=path,filetypes=[("CSV file",".csv")])
        dataframe.to_csv(path_or_buf=file_name,header=False,index=False)

    def bulk_export_csv():
        global raw_ion_image
        target_list_file = filedialog.askopenfilename(initialdir=os.getcwd(),filetypes=[("Excel Spreadsheet",".xlsx"),("CSV File",".csv")])
        target_list = pd.read_excel(target_list_file)

        for iter,row in target_list.iterrows():
            mz_entry.delete(0,tk.END)
            mz_entry.insert(0,row.values[1])
            plot_ion_image()

            folder_name = os.path.join(os.path.dirname(file_entry.get()),"ion_images")
            img_name_base = f"{row.values[0]}-{str(row.values[1]).split(".")[0]}"
            if iter == 0:
                if os.path.exists(folder_name):
                    messagebox.showwarning(title="Folder already exists!",message="You already have an ion image folder here, please rename, move, or delete it")
                    break
                os.mkdir(folder_name)
                file = filedialog.asksaveasfilename(initialdir=folder_name,filetypes=[("CSV", ".csv")],initialfile=img_name_base)
                used_extension = file.split(".")[-1]
            else:
                file = os.path.join(folder_name,f"{img_name_base}.{used_extension}")
            
            dataframe = pd.DataFrame(raw_ion_image)
            dataframe.to_csv(path_or_buf=file,header=False,index=False)

        if include_TIC_var.get():
            view_tic_check.invoke()
            file = os.path.join(folder_name,f"TIC_Image.{used_extension}")
            dataframe = pd.DataFrame(raw_ion_image)
            dataframe.to_csv(path_or_buf=file,header=False,index=False)



    def export_image(fig):
        file = filedialog.asksaveasfilename(initialdir=os.getcwd(),filetypes=[("TIF", ".tif"),("PNG",".png"),("JPG", ".jpg")])
        if file:
            file_format = file.split(".")[-1]
            fig.savefig(fname=file,
                        transparent=True,
                        #dpi=300,
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
        plot2.vlines(x=mz,ymin=0,ymax=intensities)
        plot2.set_xlabel("m/z")
        plot2.set_ylabel("Intensity")

        try:
            canvas_mass_spectrum.destroy()
        except:
            pass

        canvas_mass_spectrum = FigureCanvasTkAgg(fig_spectrum,master=window_scout)
        canvas_mass_spectrum.draw()
        toolbar = NavigationToolbar2Tk(canvas_mass_spectrum, pack_toolbar=False)
        toolbar.update()
        canvas_mass_spectrum.get_tk_widget().grid(row=5,column=6,columnspan=3)
        toolbar.grid(row=6,column=6,columnspan=3)

        fig_spectrum.canvas.callbacks.connect("button_press_event",change_target_mz)

    def change_target_mz(event):
        new_mz = event.xdata

        if new_mz != None:
            iter = 1
            new_target = []
            while len(new_target) == 0:
                low_pass = new_mz - (0.4*iter)
                high_pass = new_mz + (0.4*iter)
                iter += 1

                matches_idx = [idx for idx, value in enumerate(mz) if value>low_pass and value<high_pass]
                filt_mz = mz[matches_idx]
                filt_int = intensities[matches_idx]
                max_idx = [idx for idx,val in enumerate(filt_int) if val==max(filt_int)]
                new_target = filt_mz[max_idx]
            new_target= new_target.item()
            mz_entry.delete(0,tk.END)
            mz_entry.insert(0,round(new_target,4))
            plot_ion_image()

    def bulk_export():
        global fig
        target_list_file = filedialog.askopenfilename(initialdir=os.getcwd(),filetypes=[("Excel Spreadsheet",".xlsx"),("CSV File",".csv")])
        target_list = pd.read_excel(target_list_file)

        for iter,row in target_list.iterrows():
            mz_entry.delete(0,tk.END)
            mz_entry.insert(0,row.values[1])
            plot_ion_image()

            folder_name = os.path.join(os.path.dirname(file_entry.get()),"ion_images")
            img_name_base = f"{row.values[0]}-{str(row.values[1]).split(".")[0]}"
            if iter == 0:
                if os.path.exists(folder_name):
                    messagebox.showwarning(title="Folder already exists!",message="You already have an ion image folder here, please rename, move, or delete it")
                    break
                os.mkdir(folder_name)
                file = filedialog.asksaveasfilename(initialdir=folder_name,filetypes=[("TIF", ".tif"),("PNG",".png"),("JPG", ".jpg")],initialfile=img_name_base)
                used_extension = file.split(".")[-1]
            else:
                file = os.path.join(folder_name,f"{img_name_base}.{used_extension}")
            
            fig.savefig(fname=file,
                        transparent=True,
                        #dpi=300,
                        format=used_extension,
                        bbox_inches="tight",
                        pad_inches=0)

        if include_TIC_var.get():
            view_tic_check.invoke()
            file = os.path.join(folder_name,f"TIC_Image.{used_extension}")
            fig.savefig(fname=file,
                transparent=True,
                #dpi=300,
                format=used_extension,
                bbox_inches="tight",
                pad_inches=0)


    def view_tic():
        if view_tic_option.get():
            draw_tic_image()
        else:
            plot_ion_image()        

    def draw_tic_image():
        plot_ion_image()
        # global raw_ion_image
        # raw_ion_image = imzmlp.getionimage(imzML_object,mz_value=200,tol=9999)
        # update_ion_image()

    def custom_NL():
        ##0 = no custom, 1 = custom NL
        global NL_entry, norm_value, raw_ion_image

        custom_NL_desired = NL_state.get()
        if not custom_NL_desired:
            try:
                NL_entry.destroy()
                update_NL_button.destroy()
            except:
                pass
            update_ion_image()
        elif custom_NL_desired:
            norm_value = tk.StringVar(window_scout)
            if norm_value.get()=="":    
                norm_value.set(np.percentile(raw_ion_image,v_top.get()*100))
            
            NL_entry = tk.Entry(window_scout,textvariable=norm_value,highlightbackground=TEAL,bg=TEAL,background=BEIGE,fg="black",justify='center')
            NL_entry.grid(row=4,column=1)
            update_NL_button = tk.Button(window_scout,text="Get this NL",bg=TEAL,highlightbackground=TEAL,command=update_NL)
            update_NL_button.grid(row=4,column=2)
            NL_entry.bind("<Return>",update_ion_image)
            NL_entry.bind("<FocusOut>",update_ion_image)
        
        
    def update_NL():
        norm_value.set(np.percentile(raw_ion_image,v_top.get()*100))
        update_ion_image()





    window_scout = tk.Tk()
    window_scout.title("IMZML Scout")
    window_scout.config(padx=5,pady=5,bg=TEAL)
    style = ttk.Style()
    style.theme_use('clam')

    ##Target image:
    file_var = tk.StringVar(window_scout)
    file_var.set(_tgt_file)
    file_button=tk.Button(window_scout,text="Browse for file",bg=TEAL,highlightbackground=TEAL, command=browse_for_file)
    file_entry = tk.Entry(window_scout,textvariable=file_var,highlightbackground=TEAL,background=BEIGE,fg="black",justify='center')
    file_var.trace_add('write',plot_ion_image)

    file_button.grid(row=1,column=0)
    file_entry.grid(row=1,column=1)


    ##mz entry
    mz_var = tk.StringVar(window_scout)
    mz_var.set("104.1069")
    mz_label=tk.Label(window_scout,text="Target m/z:",bg=TEAL,font=FONT)
    mz_entry = tk.Entry(window_scout,textvariable=mz_var,highlightbackground=TEAL,background=BEIGE,fg="black",justify='center')
    #mz_var.trace_add('write',plot_ion_image)
    mz_entry.bind("<Return>",plot_ion_image)
    mz_entry.bind("<FocusOut>",plot_ion_image)

    mz_label.grid(row=2,column=0)
    mz_entry.grid(row=2,column=1)

    ##Tolerance entry
    tol_var = tk.StringVar(window_scout)
    tol_var.set("10")
    tolerance_label=tk.Label(window_scout,text="Tolerance (ppm):",bg=TEAL,font=FONT)
    tolerance_entry = tk.Entry(window_scout,textvariable=tol_var,highlightbackground=TEAL,background=BEIGE,fg="black",justify='center')
    #tol_var.trace_add('write',plot_ion_image)
    tolerance_entry.bind("<Return>",plot_ion_image)
    tolerance_entry.bind("<FocusOut>",plot_ion_image)

    tolerance_label.grid(row=3,column=0)
    tolerance_entry.grid(row=3,column=1)

    ##Normalization buttons
    normalize_custom_entry=tk.Entry(window_scout,highlightbackground=TEAL,background=BEIGE,fg="black",justify='center')

    normalization_method = tk.StringVar(window_scout)
    no_normalization = tk.Radiobutton(window_scout,bg=TEAL,command=check_normalization,fg="white",text="No Normalization",variable=normalization_method,value="none")
    no_normalization.grid(row=1,column=4)
    no_normalization.select()
    custom_method = tk.Radiobutton(window_scout,bg=TEAL,command=check_normalization,fg="white",text="Custom Normalize",variable=normalization_method,value="custom")
    custom_method.grid(row=2,column=4)
    tic_method = tk.Radiobutton(window_scout,bg=TEAL,command=check_normalization,fg="white",text="TIC Normalize",variable=normalization_method,value="TIC")
    tic_method.grid(row=3,column=4)

    ##Slider
    v_top = tk.DoubleVar(window_scout,value=0.9)
    v_bottom = tk.DoubleVar(window_scout,value=0.05)
    v_slider = RangeSliderV(window_scout,[v_bottom,v_top],padY=12,bgColor=TEAL,valueSide="RIGHT",font_color='#ffffff',font_family="Helvetica",line_s_color=BEIGE,digit_precision='.2f',step_size=0.01)
    v_slider.grid(row=4,column=4,rowspan=4)
    v_top.trace_add('write',update_ion_image)
    v_bottom.trace_add('write',update_ion_image)

    ##Custom normalization limit
    NL_state = tk.BooleanVar(window_scout)
    NL_checkbox = tk.Checkbutton(window_scout,text="Custom normalization limit?",bg=TEAL,font=FONT,variable=NL_state,command=custom_NL)
    NL_checkbox.grid(row=4,column=0)

    ##Colormap set
    colormap_options = ["viridis","plasma","cividis","hot","jet"]
    cmap_selected = tk.StringVar(window_scout)
    cmap_selected.set(colormap_options[0])
    cmap_selector = tk.OptionMenu(window_scout,cmap_selected,*colormap_options)
    cmap_selector.grid(row=1,column=2)
    cmap_selected.trace_add('write',update_ion_image)

    ##View TIC image
    view_tic_option = tk.BooleanVar(window_scout)
    view_tic_check = tk.Checkbutton(window_scout,text="View TIC?",bg=TEAL,font=FONT,var=view_tic_option,command=view_tic)
    view_tic_check.grid(row=2,column=2)

    ##Export buttons
    export_button=tk.Button(window_scout,text="Export Image",bg=TEAL,highlightbackground=TEAL,command=lambda:export_image(fig))
    export_button.grid(row=7,column=2)

    b_export = tk.Button(window_scout,text="Bulk Export",bg=TEAL,highlightbackground=TEAL,command=bulk_export)
    b_export.grid(row=7,column=0)

    csv_export = tk.Button(window_scout,text="csv Export",bg=TEAL,highlightbackground=TEAL,command=export_csv)
    csv_export.grid(row=8,column=2)
    b_csv_export = tk.Button(window_scout,text="Bulk csv export",bg=TEAL,highlightbackground=TEAL,command=bulk_export_csv)
    b_csv_export.grid(row=8,column=0)
    include_TIC_var = tk.BooleanVar(window_scout)
    include_tic = tk.Checkbutton(window_scout,text="Include TIC?",bg=TEAL,font=FONT,var=include_TIC_var)
    include_tic.grid(row=9,column=0)

    on_startup = True
    if on_startup:
        if _tgt_file != "":
            plot_ion_image()
        
        on_startup=False

    window_scout.mainloop()

if __name__ == "__main__":
    try:
        main(sys.argv[1])
    except:
        main()
