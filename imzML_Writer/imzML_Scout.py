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
from imzML_Writer.analyte_list_cleanup import *
import json

def main(tgt_file:str = ""):
    """Main control loop for imzML Scout GUI. Callable either with no arguments (find file via GUI) or by passing the file path to
    the target imzML.
    
    :param tgt_file: Path to imzML file for visualization."""
    ##Colors and FONTS
    TEAL = "#2da7ad"
    BEIGE = "#dbc076"
    FONT = ("HELVETICA", 18, 'bold')


    def browse_for_file():
        """Launch dialog box for user to find and select a target imzML file"""
        path_to_file = filedialog.askopenfilename(initialdir=os.getcwd(),filetypes=[("imzML Files","*.imzML")])
        file_entry.delete(0,tk.END)
        file_entry.insert(0,path_to_file)

    def get_aspect_ratio(img_file):
        """Tries to extract aspect ratio information (relative pixel dimensions) from the imzML. Uses 1x1 pixels if it fails"""
        try:
            metadata = img_file.metadata.pretty()
            x_pix_size = metadata["scan_settings"]["scanSettings1"]["pixel size (x)"]
            y_pix_size = metadata["scan_settings"]["scanSettings1"]["pixel size y"]

            max_x_dimension = metadata["scan_settings"]["scanSettings1"]["max dimension x"]

            return y_pix_size/x_pix_size, x_pix_size, y_pix_size, max_x_dimension
        except:
            return 1, 1, 1, 1

    def plot_ion_image(*_):
        """Deals with data update for plotting a new ion image, retrieving targets from the user input fields"""
        global raw_ion_image, aspect_ratio,x_pix,y_pix, imzML_object, max_x_dimension

        #Get the target data for the iamge
        target_mz = float(mz_entry.get())
        tolerance = float(tolerance_entry.get())
        filename = file_entry.get()
        mz_window=target_mz*tolerance/1e6

        #Open the imzML datafile if needed
        with warnings.catch_warnings(action="ignore"):
            # coordinate_map = []
            if "imzML_object" in globals():
                if imzML_object.filename != filename:
                    imzML_object = imzmlp.ImzMLParser(filename=filename,parse_lib='lxml')
            else:
                imzML_object = imzmlp.ImzMLParser(filename=filename,parse_lib='lxml')

        #Check if TIC image was requested, view entire spectrum if so. Otherwise generate datagrid of requested m/z and tolerance combo
        if view_tic_option.get():
            ion_image = imzmlp.getionimage(imzML_object,mz_value=200,tol=9999)
        else:
            ion_image = imzmlp.getionimage(imzML_object,target_mz,mz_window)
        
        #Get aspect ratio
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
        
        #Initiate new raw data variable so we can freely manipulate the ion image as needed
        raw_ion_image = ion_image

        fig = update_ion_image()
        return fig

    def update_ion_image(*_):
        """Updates the actual ion image in the GUI, with various checks for user input settings and handling to remove old images"""
        global raw_ion_image,aspect_ratio,x_pix,y_pix,canvas_ionimage,title_label,fig,ion_image, plot1, last_selected_patch, last_selected_pixel, red_highlight_patch, color_NL

        ##Retrieve contrast cutoffs for low-end and top-end
        low_thres = v_bottom.get()
        up_thres=v_top.get()
        target_mz = float(mz_entry.get())
        tolerance = float(tolerance_entry.get())

        ion_image = raw_ion_image

        ##Apply the cutoffs, setting those below to 0 and those above to high_cutoff value
        low_cutoff = np.percentile(ion_image,low_thres*100)
        up_cutoff = np.percentile(ion_image,up_thres*100)

        ion_image = np.where(ion_image > up_cutoff,up_cutoff,ion_image)
        ion_image = np.where(ion_image < low_cutoff,0,ion_image)

        #If custom normalization set, apply it to the colormap
        if NL_state.get():
            color_NL = norm_value.get()
        else:
            color_NL= up_cutoff

        ##Initiate and raw ion image
        fig = Figure(dpi=100,facecolor=TEAL,layout='tight')
        
        plot1 = fig.add_subplot()
        plot1.imshow(ion_image,aspect=aspect_ratio,interpolation="none",vmin=0,vmax=color_NL,cmap=cmap_selected.get())
        plot1.axis('off')

        #Remove old image objects before inserting a new one
        if not first_img.get():
            canvas_ionimage.get_tk_widget().destroy()
            title_label.destroy()
        else:
            last_selected_pixel = None
            last_selected_patch = None
            red_highlight_patch = None

        #Add the ion image to the tkinter window
        canvas_ionimage = FigureCanvasTkAgg(fig,master=window_scout)
        
        #Draw the selected patch if available on update of the ion image
        if last_selected_patch != None:
            draw_last_selected_patch()
        canvas_ionimage.draw()
        toolbar = NavigationToolbar2Tk(canvas_ionimage, pack_toolbar=False)
        toolbar.update()
        canvas_ionimage.get_tk_widget().grid(row=5,column=0,columnspan=3)

        ##Draw a label for the ion image with target m/z, tolerance, and pixel dimensions
        title_string=[]
        title_string = f"{int(round(x_pix,0))} µm x {int(round(y_pix,1))} µm pixels; m/z {target_mz} @ {tolerance} ppm"
        title_label = tk.Label(window_scout,text=title_string,bg=TEAL,font=FONT)
        title_label.grid(row=6,column=0,columnspan=4)

        #Initiate callbacks for when users mouse over the ion image for viewing/selecting highlighted pixel
        fig.canvas.mpl_connect("motion_notify_event",image_move)
        fig.canvas.callbacks.connect('button_press_event',report_coordinates)
        first_img.set(False)
        
        return fig

    def draw_last_selected_patch():
        """Draws a red patch wherever the last selected pixel was"""
        global last_selected_patch, last_selected_pixel
        lx, ly = last_selected_pixel

        # Prepare the green overlay for the selected pixel
        selected_overlay = np.zeros((ion_image.shape[0], ion_image.shape[1], 4))  # New overlay
        
        num_lines, pixels_per_line = ion_image.shape
        selected_min_y = int(max(0, ly))
        selected_max_y = int(min(num_lines, ly + 1))
        selected_min_x = int(max(0, lx - pixels_per_line*0.008))
        selected_max_x = int(min(pixels_per_line, lx + 1))


        # Set the green color with some opacity for the selection overlay
        selected_overlay[selected_min_y:selected_max_y, selected_min_x:selected_max_x] = [1, 0, 0, 0.8]  # Green with 80% opacity

        last_selected_patch = plot1.imshow(selected_overlay, aspect=aspect_ratio, interpolation="none")
        
    def image_move(event):
        """Handle mouse movement over the ion image and raws a green patch over the currently selectable region."""
        global ion_image, plot1, last_selected_patch, red_highlight_patch,canvas_ionimage, color_NL  # Track selected and red patches

        if event.xdata is not None and event.ydata is not None:
            # Get the pixel index
            x_index = int(event.xdata)
            y_index = int(event.ydata)

            # Create a copy of the original image to modify for hover
            highlight_image = np.zeros((ion_image.shape[0], ion_image.shape[1], 4))  # RGBA image for highlight

            # Define bounds for the highlight area
            pixels_per_line = ion_image.shape

            min_y = int(max(0, y_index))
            max_y = int(min(ion_image.shape[0], y_index+1))
            min_x = int(max(0, x_index - pixels_per_line[1]*0.008))
            max_x = int(min(ion_image.shape[1], x_index + 1))

            # Set the green color with varying opacity for the hover overlay
            highlight_image[min_y:max_y, min_x:max_x] = [0, 1, 0, 0.8]  # Green with 80% opacity        
            
            # Draw the ion image first
            plot1.imshow(ion_image, aspect=aspect_ratio, interpolation="none", vmin=np.min(ion_image), vmax=color_NL, cmap=cmap_selected.get())

            # Overlay the red highlight
            if red_highlight_patch is not None:
                red_highlight_patch.remove()  # Remove previous red highlight if it exists
                
            red_highlight_patch = plot1.imshow(highlight_image, aspect=aspect_ratio, interpolation="none")  # Store new red highlight

            # If we have a last selected pixel, keep it drawn
            if last_selected_pixel:
                draw_last_selected_patch()

            # Refresh the canvas to show updates
            canvas_ionimage.draw()

    def export_csv():
        """Exports the current image data as a csv file, prompts the user as to where they'd like to save it."""
        global raw_ion_image
        dataframe = pd.DataFrame(raw_ion_image)
        path = os.path.dirname(file_entry.get()) 
        file_name = filedialog.asksaveasfilename(initialdir=path,filetypes=[("CSV file",".csv")])
        dataframe.to_csv(path_or_buf=file_name,header=False,index=False)

    def bulk_export_csv():
        """Exports a batch of images as csv files, prompts the user for a spreadsheet of target m/z and names"""
        global red_highlight_patch, last_selected_patch, raw_ion_image

        ##Prompt user for a spreadsheet of target m/z and names to give them
        target_list_file = filedialog.askopenfilename(initialdir=os.getcwd(),filetypes=[("Excel Spreadsheet",".xlsx"),("CSV File",".csv")])
        target_list = pd.read_excel(target_list_file)
        target_list=cleanup_table(target_list,target_list_file)

        ##Generate ion image for each entry, write the raw data to a CSV file
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

        ##Optionally, write the TIC image as well
        if include_TIC_var.get():
            view_tic_check.invoke()
            file = os.path.join(folder_name,f"TIC_Image.{used_extension}")
            dataframe = pd.DataFrame(raw_ion_image)
            dataframe.to_csv(path_or_buf=file,header=False,index=False)

    def find_scan_idx(event):
        """Based on where the user clicks, find the corresponding scan index in the imzML file"""
        scans_per_line = int(max_x_dimension / x_pix)
        line_scan_num = int(round(event.ydata,0))+1
        scan_along_line = int(round(event.xdata,0))+1
        return line_scan_num*scans_per_line + scan_along_line


    def export_image(fig):
        """Export the currently viewed image as an image file (tif, png, jpg), prompt the user for where to put it"""
        global red_highlight_patch, last_selected_patch

        ##Remove any highlight patches from the data
        if red_highlight_patch != None:
            red_highlight_patch.remove()
        
        if last_selected_patch !=None:
            last_selected_patch.remove()
        
        #Prompt the user for where to save it
        file = filedialog.asksaveasfilename(initialdir=os.getcwd(),filetypes=[("TIF", ".tif"),("PNG",".png"),("JPG", ".jpg")])
        if file:
            #Save the file
            file_format = file.split(".")[-1]
            fig.savefig(fname=file,
                        transparent=True,
                        #dpi=300,
                        format=file_format,
                        bbox_inches="tight",
                        pad_inches=0)


    def check_normalization():
        """Handles contextual display on whether a custom normalization m/z is being applied"""
        if normalization_method.get() == "custom": ##If custom NL, add an entry for that m/z and listeners to update the ion image when it changes
            normalize_custom_entry.grid(row=2,column=6)
            normalize_custom_entry.bind("<Return>",plot_ion_image)
            normalize_custom_entry.bind("<FocusOut>",plot_ion_image)
        else:
            try:
                normalize_custom_entry.grid_remove() #Remove the box for space if the box is unchecked
            except:
                pass
        
        try:
            plot_ion_image()
        except:
            pass
        
    def report_coordinates(event):
        """Reports the current pixel x/y and updates the mass spectrum from the scan_idx"""
        global scan_idx, last_selected_pixel
        if event.xdata != None:
            scan_idx = find_scan_idx(event)
            last_selected_pixel = (event.xdata, event.ydata)
            update_plot_for_selected_pixel()
            plot_mass_spectrum(scan_idx)
        
    def update_plot_for_selected_pixel():
        """Update the plot with the new selected pixel and draw the previous selection in red."""
        global ion_image, plot1, canvas_ionimage, last_selected_pixel, last_selected_patch

        # Draw the ion image
        plot1.imshow(ion_image, aspect=aspect_ratio, interpolation="none", vmin=np.min(ion_image), vmax=color_NL, cmap=cmap_selected.get())
        
        # Remove old highlights
        if last_selected_patch is not None:
            last_selected_patch.remove()

        # Add red highlight, if a pixel is selected
        if last_selected_pixel:
            draw_last_selected_patch()

        # Refresh the canvas
        canvas_ionimage.draw()


    def plot_mass_spectrum(scan_idx):
        """Plot a mass spectrum and add listeners to watch for mouseovers/clicks to update the ion image to the nearest detectable m/z"""
        global imzML_object, mz, intensities, MS_vline, plot2, canvas_mass_spectrum

        ##Retrieve the data for the target spectrum
        [mz, intensities] = imzML_object.getspectrum(scan_idx)

        ##Plot the actual mass spectrum using vlines
        fig_spectrum = Figure(figsize=(4,4),dpi=100,facecolor=TEAL)
        plot2 = fig_spectrum.add_subplot()
        plot2.vlines(x=mz,ymin=0,ymax=intensities)
        plot2.set_ylim(0,plot2.get_ylim()[1])
        if not first_MS.get():
            #Set the x lims and y lims, as input by the user
            plot2.set_xlim(float(start_var.get()),float(end_var.get()))
            in_bounds = [idx for idx, value in enumerate(mz) if float(start_var.get()) < value < float(end_var.get())]
            new_ylim = np.max(intensities[in_bounds]) *1.3
            plot2.set_ylim(0,new_ylim)
            
        plot2.set_xlabel("m/z")
        plot2.set_ylabel("Intensity")

        try:
            ##Remove old mass spectra so they aren't layered on top of each other
            canvas_mass_spectrum.destroy()
        except:
            pass
        
        ##Add mass spectrum to the GUI window
        canvas_mass_spectrum = FigureCanvasTkAgg(fig_spectrum,master=window_scout)
        canvas_mass_spectrum.get_tk_widget().grid(row=5,column=6,columnspan=4)


        if first_MS.get():
            ##Handling for start/stop xlims entries, listeners to update when these are changed, etc.
            MS_vline = None
            start_mz = tk.Label(window_scout,text="Start m/z",bg=TEAL,font=FONT)
            end_mz = tk.Label(window_scout, text = "End m/z",bg=TEAL,font=FONT)
            start_mz.grid(row=6,column=6)
            end_mz.grid(row=6,column=8)
            start_var.set(f"{plot2.get_xlim()[0]:.1f}")
            start_mz_entry = tk.Entry(window_scout,textvariable=start_var,highlightbackground=TEAL,background=BEIGE,fg="black",justify='center',width=10)
            end_var.set(f"{plot2.get_xlim()[1]:.1f}")
            end_mz_entry = tk.Entry(window_scout,textvariable=end_var,highlightbackground=TEAL,background=BEIGE,fg='black',justify='center',width=10)
            start_mz_entry.grid(row=6,column=7)
            end_mz_entry.grid(row=6,column=9)
            start_mz_entry.bind("<Return>",lambda event:plot_mass_spectrum(scan_idx=scan_idx))
            start_mz_entry.bind("<FocusOut>",lambda event:plot_mass_spectrum(scan_idx=scan_idx))
            end_mz_entry.bind("<Return>",lambda event:plot_mass_spectrum(scan_idx=scan_idx))
            end_mz_entry.bind("<FocusOut>",lambda event:plot_mass_spectrum(scan_idx=scan_idx))

        ##Show previously selected m/z as needed
        current_mz = mz_entry.get()
        current_mz = float(current_mz)
        xlim = plot2.get_xlim()
        percentage = (current_mz - xlim[0]) / (xlim[1] - xlim[0])
        if percentage > 0.75:
            ha = 'right'  # align label to the right if near the end
            label_x_pos = current_mz - 0.5  # adjust label position to the left
        else:
            ha = 'left'   # align label to the left otherwise
            label_x_pos = current_mz + 0.5
        
        y_position = 4/5 * plot2.get_ylim()[1]
        plot2.axvline(x=current_mz,color='red',linestyle='--')
        plot2.text(label_x_pos, y_position, f"{current_mz:.4f}", color='red', fontsize=10, ha=ha, va='center')
        canvas_mass_spectrum.draw()

        ##Add listeners for mouseover and click on the mass spectrum
        fig_spectrum.canvas.mpl_connect("motion_notify_event",on_MS_move)
        fig_spectrum.canvas.callbacks.connect("button_press_event",change_target_mz)
        first_MS.set(False)
    
    def on_MS_move(event):
        """Listener for mouseover events on the mass spectrum, finds the nearest m/z when you do so and displays it on the window"""
        new_mz = event.xdata
        if new_mz is not None:
            new_target = find_target_mz(new_mz)

            global MS_vline, plot2, canvas_mass_spectrum, MS_label
            if MS_vline is not None:
                MS_vline.remove()

            if 'MS_label' in globals() and MS_label is not None:
                MS_label.remove()

            xlim = plot2.get_xlim()
            percentage = (new_target - xlim[0]) / (xlim[1] - xlim[0]) #percentage along x-axis
            y_position = 2 / 3 * plot2.get_ylim()[1]

            # Contextual align label left/right of the bar depending on how close to the end of viewing window we are
            if percentage > 0.75:
                ha = 'right'  # align label to the right if near the end
                label_x_pos = new_target - 0.5  # adjust label position to the left
            else:
                ha = 'left'   # align label to the left otherwise
                label_x_pos = new_target + 0.5  # adjust label position to the right

            MS_vline = plot2.axvline(x=new_target, color='black', linestyle='--')
            
            # Create the label with adjusted properties
            MS_label = plot2.text(label_x_pos, y_position, f"{new_target:.4f}",
                                color='black', fontsize=10, ha=ha, va='center')

            canvas_mass_spectrum.draw()

    def find_target_mz(new_mz):
        """Finds the target m/z value based on surrounding, detectable m/z values."""
        if new_mz is None:
            return None  # Handle case for None input

        iter = 1
        new_target = []
        
        # Loop until a target value is found
        while len(new_target) == 0:
            low_pass = new_mz - (0.005 * iter)
            high_pass = new_mz + (0.005 * iter)
            iter += 1

            # Find indices of values within the low and high pass range
            matches_idx = [idx for idx, value in enumerate(mz) if low_pass < value < high_pass]
            filt_mz = mz[matches_idx]
            filt_int = intensities[matches_idx]
            
            # Get index of the maximum intensity value
            if len(filt_int) > 0:
                max_idx = [idx for idx, val in enumerate(filt_int) if val == max(filt_int)]
                new_target = filt_mz[max_idx]

        return new_target.item()  # Return the found target m/z value

    def change_target_mz(event):
        """Update ion image with the newly selected m/z"""
        global scan_idx
        new_mz = event.xdata
        if new_mz != None:
            new_target = find_target_mz(new_mz)
            mz_entry.delete(0,tk.END)
            mz_entry.insert(0,round(new_target,4))
            plot_ion_image()
            plot_mass_spectrum(scan_idx)

    def bulk_export():
        """Export a series of ion images with the currently selected view settings. Prompts the user for a spreadsheet with target m/z and labels."""
        global fig, red_highlight_patch, last_selected_patch
        #prompt the user for the target list
        target_list_file = filedialog.askopenfilename(initialdir=os.getcwd(),filetypes=[("Excel Spreadsheet",".xlsx"),("CSV File",".csv")])
        target_list = pd.read_excel(target_list_file)
        #Contextual code to clean up table depending on whether headers were included, column order, etc.
        target_list=cleanup_table(target_list,target_list_file)

        ##Iterate through each target m/z, drawing and then writing the ion image
        for iter,row in target_list.iterrows():
            mz_entry.delete(0,tk.END)
            mz_entry.insert(0,row.values[1])
            plot_ion_image()
            if red_highlight_patch != None:
                red_highlight_patch.remove()
                red_highlight_patch = None
        
            if last_selected_patch !=None:
                last_selected_patch.remove()
                last_selected_patch = None



            folder_name = os.path.join(os.path.dirname(file_entry.get()),"ion_images")
            img_name_base = f"{row.values[0]}-{str(row.values[1]).split(".")[0]}"
            if iter == 0:
                if os.path.exists(folder_name):
                    messagebox.showwarning(title="Folder already exists!",message="You already have an ion image folder here, please rename, move, or delete it")
                    break
                os.mkdir(folder_name)
                #Prompt user for file extension to use
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

        ##optionally, export a TIC image if selected
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

    def custom_NL():
        """Applies custom normalization limit as specified by the user"""
        ##0 = no custom, 1 = custom NL
        global NL_entry, norm_value, raw_ion_image

        custom_NL_desired = NL_state.get()
        if not custom_NL_desired:
            try:
                NL_entry.destroy() #remove entries for custom normalization limit when unchecked
                update_NL_button.destroy()
            except:
                pass
            update_ion_image()
        elif custom_NL_desired: ##Add the entries when checked
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

    def more_cmaps():
        def add_a_map():
            try:
                new_map = all_options.selection_get()
            except:
                new_map = None
            if new_map != None and not new_map in colormap_options:
                colormap_options.append(new_map)
                selected_options.insert(tk.END,new_map)

        def remove_a_map():
            try:
                remove_map = selected_options.selection_get()
            except:
                remove_map = None
            
            if remove_map != None:
                for idx, map in enumerate(colormap_options):
                    if remove_map == map:
                        del_idx = idx
                
                colormap_options.pop(del_idx)
                selected_options.delete(del_idx)

        def save_exit():
            mod_path = os.path.dirname(os.path.abspath(__file__))
            config_file = os.path.join(mod_path,"cmap_targets.json")
            json_dump = {"options":colormap_options}
            with open(config_file,'w') as file:
                json.dump(json_dump,file,indent=4)
            
            cmap_selected.set(colormap_options[0])
            cmap_selector['menu'].delete(0,'end')
            for map in colormap_options:
                cmap_selector['menu'].add_command(label=map,command=tk._setit(cmap_selected,map))
            cmap_window.destroy()

        cmap_window = tk.Tk()
        cmap_window.title("Colormap Options...")
        cmap_window.config(padx=5,pady=5,bg=TEAL)

        #Listbox for all cmap options
        all_options = tk.Listbox(cmap_window,bg=BEIGE,fg="black",height=10,highlightcolor=TEAL,width=35,justify='center')
        all_options.grid(row=0,column=1,rowspan=4)

        cmaps = plt.colormaps()
        for idx, map in enumerate(cmaps):
            all_options.insert(idx,map)
        
        #Listbox for cmap options to choose from
        selected_options = tk.Listbox(cmap_window,bg=BEIGE,fg="black",height=10,highlightcolor=TEAL,width=35,justify='center')
        selected_options.grid(row=0,column=3,rowspan=4)

        mod_path = os.path.dirname(os.path.abspath(__file__))
        config_file = os.path.join(mod_path,"cmap_targets.json")
        with open(config_file,'r') as file:
            cmap_options = json.load(file)
        colormap_options = cmap_options["options"]
        for idx, map in enumerate(colormap_options):
            selected_options.insert(idx,map)

        ##Add button
        add_button=tk.Button(cmap_window,text=">>>",bg=TEAL,highlightbackground=TEAL, command=add_a_map)
        add_button.grid(row=1,column=2)

        ##Remove button
        remove_button=tk.Button(cmap_window,text="<<<",bg=TEAL,highlightbackground=TEAL, command=remove_a_map)
        remove_button.grid(row=2,column=2)

        ##Save button
        save_button=tk.Button(cmap_window,text="Save & Exit",bg=TEAL,highlightbackground=TEAL, command=save_exit)
        save_button.grid(row=5,column=2)
        



    ##Build the GUI window
    window_scout = tk.Tk()
    window_scout.title("IMZML Scout")
    window_scout.config(padx=5,pady=5,bg=TEAL)
    style = ttk.Style()
    style.theme_use('clam')

    ##Target image:
    file_var = tk.StringVar(window_scout)
    file_var.set(tgt_file)
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
    try:
        mod_path = os.path.dirname(os.path.abspath(__file__))
        config_file = os.path.join(mod_path,"cmap_targets.json")
        with open(config_file,'r') as file:
            cmap_options = json.load(file)
        colormap_options = cmap_options["options"]
    except:
        mod_path = os.path.dirname(os.path.abspath(__file__))
        config_file = os.path.join(mod_path,"cmap_targets.json")
        json_dump = {'options':["viridis","plasma","cividis","hot","jet"]}
        with open(config_file,'w') as file:
            json.dump(json_dump,file,indent=4)

        mod_path = os.path.dirname(os.path.abspath(__file__))
        config_file = os.path.join(mod_path,"cmap_targets.json")
        with open(config_file,'r') as file:
            cmap_options = json.load(file)
        colormap_options = cmap_options["options"]
    
    cmap_selected = tk.StringVar(window_scout)
    cmap_selected.set(colormap_options[0])
    cmap_selector = tk.OptionMenu(window_scout,cmap_selected,*colormap_options)
    cmap_selector.grid(row=1,column=2)
    cmap_selected.trace_add('write',update_ion_image)

    ##cmap options
    cmap_options_button = tk.Button(window_scout,text="More cmaps...",bg=TEAL,font=TEAL,highlightbackground=TEAL,command=more_cmaps)
    cmap_options_button.grid(row=2,column=2)

    ##View TIC image
    view_tic_option = tk.BooleanVar(window_scout)
    view_tic_check = tk.Checkbutton(window_scout,text="View TIC?",bg=TEAL,font=FONT,var=view_tic_option,command=view_tic)
    view_tic_check.grid(row=3,column=2)

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


    start_var = tk.StringVar(window_scout)
    start_var.set(None)
    end_var = tk.StringVar(window_scout)
    end_var.set(None)
    first_img = tk.BooleanVar(window_scout)
    first_img.set(True)
    first_MS = tk.BooleanVar(window_scout)
    first_MS.set(True)
    on_startup = True

    if on_startup:
        if tgt_file != "":
            plot_ion_image()
        
        on_startup=False

    window_scout.mainloop()

if __name__ == "__main__":
    try:
        main(sys.argv[1])
    except:
        main()
