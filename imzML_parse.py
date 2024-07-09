import pyimzml.ImzMLParser as imzmlp
import matplotlib.pyplot as plt

TARGET_MZ=538.3873

python_conversion = "./C3R5B2_Slide4_Dosed/C3R5B2_Slide4_Dosed_FTMS + p ESI Full ms [95.0000-900.imzML"
TOLERANCE=2 #ppm
window=TARGET_MZ*TOLERANCE/1e6

file_python = imzmlp.ImzMLParser(filename=python_conversion,parse_lib='lxml')
img_python = imzmlp.getionimage(file_python,TARGET_MZ,TOLERANCE)

plt.imshow(img_python)
plt.show()


