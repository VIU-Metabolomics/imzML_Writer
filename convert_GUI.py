import tkinter as tk

window = tk.Tk()
window.title("IMZML WRITER")
window.geometry("500x500")



##Scan-speed entry
speed_label=tk.Label(text="x scan speed (µm/s):")
speed_entry = tk.Entry(text="Enter speed here")

speed_label.grid(row=1,column=0)
speed_entry.grid(row=1,column=1)

##Y-step entry
Y_step_label=tk.Label(text="y step (µm):")
Y_step_entry=tk.Entry(text="Enter y step here")

Y_step_label.grid(row=2,column=0)
Y_step_entry.grid(row=2,column=1)

##Lock mass entry
lock_mass_label=tk.Label(text="Lock Mass:")
lock_mass_entry=tk.Entry(text="Enter Lock Mass Here")

lock_mass_label.grid(row=3,column=0)
lock_mass_entry.grid(row=3,column=1)


window.mainloop()