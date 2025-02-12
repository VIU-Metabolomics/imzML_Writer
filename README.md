#**MAC Install instructions:**#

1. Download and install the latest version of python (https://www.python.org/downloads/)

2. Download and Install VS Code (https://code.visualstudio.com/download)

3. Download and Install Docker (https://www.docker.com/products/docker-desktop/)

4. After both are successfully installed, launch both and open a terminal window in VS Code (Terminal --> New Terminal in top ribbon or CMD+SHIFT+`)

5. In the command line, enter the command:

```
   docker pull chambm/pwiz-skyline-i-agree-to-the-vendor-licenses
```

Note: This will take ~5 - 10 mins to install, you can follow the progress in the terminal, when complete, the new docker image will appear under images in the docker GUI

6. Download or clone the repo for imzML_Writer, and navigate your terminal to the resulting folder

7. In VS Code, navigate to the folder where you installed imzML_Writer by clicking File --> Open in the top ribbon

8. Install the requisite packages by running the command:

```
   pip3 install -r requirements.txt
```

Note: If this fails, try replacing pip3 with pip (Apple silicon chips need pip3/python3, older intel chips use pip/python)

9. Launch imzML_Writer by typing the command:

```
   python3 imzML_Writer.py
```

#**PC Install instructions**#

1. Download and install the latest version of python (https://www.python.org/downloads/)

2. Download and Install VS Code (https://code.visualstudio.com/download)

3. Download and Install msConvert (https://proteowizard.sourceforge.io/download.html)

4. Add the path to your msConvert folder (containing msConvert.exe)
   Note: This may vary depending on which version of windows you are using, instructions here:
   https://www.eukhost.com/kb/how-to-add-to-the-path-on-windows-10-and-windows-11/
   This will likely require restarting your PC

5. Test you've successfully installed everything by entering into the terminal:

```
   msconvert
```

Note: This should return an info page on msConvert

6. Download or clone the repo for imzML_Writer, and navigate your terminal to the resulting folder

7. In VS Code, navigate to the folder where you installed imzML_Writer by clicking File --> Open in the top ribbon

8. Install the requisite packages by running the command:

```
   pip install -r requirements.txt
```

9. Launch imzML_Writer by typing the command:

```
   python imzML_Writer.py
```

##Customizing colormaps:##
You can change the available colormaps by editing/creating a "Scout_Config.xlsx" file in the working directory (where imzML_Scout.py is located). A default sheet is available in the Github repo. You can edit which colormaps are available by adding/removing colormap names in the spreadsheet. Additional colormaps can be found here in the matplotlib documentation:
https://matplotlib.org/stable/users/explain/colors/colormaps.html

##Troubleshooting:##

Nothing's working! Why?!?!

1. Start with a clean installation and try the test files to ensure all packages/msConvert/Docker are installed correctly

2. Verify that no 'hanging' imzML files are in the working directory where imzML_Writer is installed, these can result from failed file conversions and will cause errors if you try to process a new dataset without removing them

Everything turned green, but I don't have any imzML files and the progress bars look wacky?
-This can occur for non-thermo files that specify the filter string in a new and exciting way I hadn't found yet. If comfortable, please share a test file and I'll add it to the library so it will convert correctly

Please direct any questions, concerns, or feature requests to me at Joseph.Monaghan@viu.ca
