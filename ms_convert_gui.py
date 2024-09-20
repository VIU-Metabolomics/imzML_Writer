import tkinter as tk
from tkinter import ttk, filedialog
import os
import threading
import sys

##Colors and FONTS
TEAL = "#2da7ad"
BEIGE = "#dbc076"
GREEN = "#22d10f"
FONT = ("HELVETICA", 18, 'bold')

def main(tgt_dir=""):

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

        file_type_label = tk.Label(window_msconvert,text=f"File type: .{file_type}",bg=TEAL,font=FONT)
        file_type_label.grid(row=1,column=3,columnspan=3)
        return file_type

    def call_msconvert():
        pass



    
    window_msconvert = tk.Tk()
    window_msconvert.title("MAC - msConvert GUI")
    window_msconvert.config(padx=5,pady=5,bg=TEAL)
    style = ttk.Style()
    style.theme_use('clam')

    ##Choose Directory Button
    CD_button = tk.Button(window_msconvert,text="Select Folder",bg=TEAL,highlightbackground=TEAL,command=get_path)
    CD_button.grid(row=1,column=0)

    CD_entry = tk.Entry(window_msconvert,text="Enter Directory Here",highlightbackground=TEAL,background=BEIGE,fg="black",justify='center')
    CD_entry.grid(row=1,column=1)

    ##Processing buttons
    convert_mzML = tk.Button(window_msconvert,text="Full Conversion",bg=TEAL,highlightbackground=TEAL,command=call_msconvert)
    convert_mzML.grid(row=2,column=4)

    #Listbox for files in target folder
    file_list = tk.Listbox(window_msconvert,bg=BEIGE,fg="black",height=10,highlightcolor=TEAL,width=35,justify='left')
    file_list.grid(row=0,column=4,rowspan=2,columnspan=3)

    window_msconvert.mainloop()




if __name__ == "__main__":
    try:
        main(sys.argv[1])
    except:
        main()