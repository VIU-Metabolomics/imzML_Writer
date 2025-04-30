import scipy.ndimage
import cv2 as cv
import numpy as np
from tkinter import ttk, filedialog, messagebox
import tkinter as tk
import matplotlib.pyplot as plt
from matplotlib.widgets import PolygonSelector
from matplotlib.path import Path
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk


roi_mask = None
verts = None
mask_list = None
TEAL = "#2da7ad"
BEIGE = "#dbc076"
FONT = ("HELVETICA", 18, 'bold')


def unsharp_mask(image, kernel_size=(5, 5), sigmaX=1.0, sigmaY=1.0, amount=1.0, threshold=0):
    """Return a sharpened version of the image, using an unsharp mask."""
    blurred = cv.GaussianBlur(image, kernel_size, sigmaX=sigmaX, sigmaY=sigmaY)
    sharpened = float(amount + 1) * image - float(amount) * blurred
    sharpened = np.maximum(sharpened, np.zeros(sharpened.shape))
    sharpened = np.minimum(sharpened, np.max(image) * np.ones(sharpened.shape))
    # sharpened = sharpened.round().astype(np.uint8)
    if threshold > 0:
        low_contrast_mask = np.absolute(image - blurred) < threshold
        np.copyto(sharpened, image, where=low_contrast_mask)
    return sharpened

def smooth_image(img_data,asp:float, factor:int=3,base_sigma:float=10,weight_factor:float=0.5):
    zoomed_img = scipy.ndimage.zoom(img_data,factor)
    sharpened_img = unsharp_mask(zoomed_img, sigmaX=base_sigma, sigmaY=base_sigma/asp, kernel_size=(9,9), amount=weight_factor)
    return sharpened_img

def ROI_select(ROI_button:tk.Button, ion_image:np.array, aspect_ratio:float, color_NL=float):
    global mask_list
    roi_selector = tk.Toplevel()
    roi_selector.title("ROI Selector")
    roi_selector.config(padx=5,pady=5,bg=TEAL)

    fig, ax = plt.subplots()
    canvas = FigureCanvasTkAgg(fig, master=roi_selector)
    plt.imshow(ion_image,aspect=aspect_ratio,interpolation="none",vmin=0,vmax=color_NL,cmap='viridis')
    plt.title("Select your ROI")
    
    selector = []
    selector.append(PolygonSelector(ax, props=dict(color='red')))
    fig.set_facecolor(TEAL)
    fig.tight_layout()
    canvas.get_tk_widget().pack()

    def add_additional_ROI():
        nonlocal selector
        selector.append(PolygonSelector(ax, props=dict(color='red')))

    add_another = tk.Button(roi_selector, text="Add another inclusion region", bg=TEAL,highlightbackground=TEAL,command=add_additional_ROI)
    add_another.pack()

    def quit_select():
        nonlocal roi_selector
        mask_list = []
        vert_list = []
        for idx, roi in enumerate(selector):
            if len(roi.verts) > 2:
                # Create coordinate arrays
                h, w = ion_image.shape[:2]
                y, x = np.mgrid[:h, :w]
                coors = np.hstack((x.reshape(-1, 1), y.reshape(-1, 1)))  # (N, 2) array
                
                # Create path from vertices
                path = Path(roi.verts)
                mask = path.contains_points(coors)
                mask = mask.reshape(h, w).astype(int)  # Reshape to image dimensions
                mask_list.append(mask)
                vert_list.append(roi.verts)


        if len(mask_list) >= 1:
            global roi_mask, verts
            final_mask = mask_list[0]
            for mask in mask_list:
                final_mask = np.maximum(final_mask,mask)
            roi_mask = final_mask

            all_verts = []
            for idx, vert in enumerate(vert_list):
                for vertex in vert:
                    all_verts.append((idx, vertex[0], vertex[1]))
            
            verts = all_verts
        plt.close(fig)
        canvas.get_tk_widget().destroy()
        roi_selector.destroy()

    roi_selector.protocol("WM_DELETE_WINDOW", quit_select)
    quit_selecting = tk.Button(roi_selector, text="Stop selecting", bg=TEAL,highlightbackground=TEAL, command=quit_select)
    quit_selecting.pack()



def save_ROI():
    save_location = filedialog.asksaveasfile(defaultextension='.npz')
    np.savez(save_location.name, roi_mask=roi_mask, verts=verts, mask_list=mask_list)

def load_ROI():
    global roi_mask, verts
    file_location =filedialog.askopenfilename(defaultextension='.npz')

    loaded_data = np.load(file_location)
    verts = loaded_data['verts']
    roi_mask = loaded_data['roi_mask']
    mask_list = loaded_data['mask_list']




        


        
