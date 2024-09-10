import pyimzml.ImzMLParser as imzmlp
import matplotlib.pyplot as plt

TARGET_MZ=311.2562 #Arachidonic acid
#TARGET_MZ = 363.3082 #MG(18:1)

python_conversion = "./DataFiles/Brain_Li/Brain_Li_FTMS + p ESI Full ms [70.0000-1000.imzML"
TOLERANCE=2 #ppm
window=TARGET_MZ*TOLERANCE/1e6

file_python = imzmlp.ImzMLParser(filename=python_conversion,parse_lib='lxml')
img_python = imzmlp.getionimage(file_python,TARGET_MZ,TOLERANCE)

plt.imshow(img_python)
plt.show()


