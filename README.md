##MAC Install instructions:
1. Download and install the latest version of python (https://www.python.org/downloads/)
2. Download and Install VS Code (https://code.visualstudio.com/download)
3. Download and Install Docker (https://www.docker.com/products/docker-desktop/)
4. After both are successfully installed, launch both and open a terminal window in VS Code (Terminal --> New Terminal in top ribbon)
5. In the command line, enter the command:
docker pull chambm/pwiz-skyline-i-agree-to-the-vendor-licenses
Note: This will take ~5 - 10 mins to install, you can follow the progress in the terminal, when complete, the new docker image will appear under images in the docker GUI
6. Download or clone the repo for imzML_Writer, and navigate your terminal to the resulting folder
7. Install the requisite packages by running the command:
pip3 install -r requirements.txt
Note: If this fails, try replacing pip3 with pip (Apple silicon chips need pip3/python3, older intel chips use pip/python)
8. Launch imzML_Writer by typing the command:
python3 convert_GUI.py


##PC Install instructions
1. Download and install the latest version of python (https://www.python.org/downloads/)
2. Download and Install VS Code (https://code.visualstudio.com/download)
3. Download and Install msConvert (https://www.docker.com/products/docker-desktop/)
4. Add the path to your msConvert folder (containing msConvert.exe)
Note: This may vary depending on which version of windows you are using, instructions here:
https://www.eukhost.com/kb/how-to-add-to-the-path-on-windows-10-and-windows-11/
This will likely require restarting your PC
5. Test you've successfully installed everything by entering into the terminal:
msconvert
Note: This should return an info page on msConvert
6. Download or clone the repo for imzML_Writer, and navigate your terminal to the resulting folder
7. Install the requisite packages by running the command:
pip install -r requirements.txt
8. Launch imzML_Writer by typing the command:
python convert_GUI.py