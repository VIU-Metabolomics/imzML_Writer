from bs4 import BeautifulSoup
import openpyxl


def annotate_imzML(annotate_file,SRC_mzML,scan_time=0.001,filter_string="none given"):
    """Takes pyimzml output imzML files and annotates them using some user input (imaging_parameters.xlsx)
    and the corresponding mzML source file. Designed to be embeded as part of overall nanoDESI Raw-to-imzML pipeline.
    annotate_file = the imzML file to be annotated
    SRC_mzML = the source file to pull metadata from
    scan_time = how long it took to scan across the tissue (default = 0.001)
    filter_string = what scan filter is actually captured  (default = "none given")
    """

    result_file = annotate_file
    #Read in imaging settings from image_parameters.xlsx spreadsheet
    wb = openpyxl.load_workbook("Image_Parameters.xlsx")
    ws = wb.active
    excel_data={}
    for row in ws.iter_rows(values_only=True):
        excel_data[row[0]]=row[1]

    #What metadata do I want to capture: spectrum type, source file (just use first mzML), filter string, pixel info, instrument info
    #Source file - filename from first mzML
    #Spectrum type - borrow from mzML
    #Filter String - write from extracted list (already embedded in imzML filename)
    #pixel info - Read from excel sheet (image parameters)
    #Lock Mass - read from excel sheet
    #Instrument info - Read from mzML


    ##Required inputs when this is expanded to a function
    # SRC_mzML = "C3R5B2_Slide4_Dosed01.mzML"
    # annotate_file = "C3R5B2_Slide4_Dosed_FTMS + p ESI Full ms [95.0000-900.imzML"
    # result_file = "test.imzML"
    # scan_time = 3.6
    # filter_string = "TEST FILT STRING"


    #Retrieve data from source mzml
    with open(SRC_mzML) as file:
        data = file.read()
    data = BeautifulSoup(data,'xml')

    #Grab instrument model from the source mzML
    instrument_model = data.referenceableParamGroup.cvParam.get("name")


    #Open un-annotated imzML
    with open(annotate_file) as file:
        data_need_annotation = file.read()
    data_need_annotation = BeautifulSoup(data_need_annotation,'xml')

    #Replace template data with key metadata from mzML
    replace_list = ['instrumentConfigurationList']
    for replace_item in replace_list:
        data_need_annotation.find(replace_item).replace_with(data.find(replace_item))

    #Write instrument model to mzML, filter string
    data_need_annotation.instrumentConfigurationList.instrumentConfiguration.attrs['id']=instrument_model

    for tag in data_need_annotation.referenceableParamGroupList:
        if "scan1" in str(tag):
            for tag2 in tag:
                if "MS:1000512" in str(tag2):
                    tag2["value"] = filter_string
                    

        
    #Read pixel grid information from imzML
    for tag in data_need_annotation.scanSettingsList.scanSettings:
        if 'cvParam' in str(tag):
            if tag.get("accession") == "IMS:1000042": #num pixels x
                x_pixels = tag.get("value")
            elif tag.get("accession") == "IMS:1000043": #num pixels y
                y_pixels = tag.get("value")

    #Calculate pixel sizes and overall dimensions from size of pixel grid, scan speed, step sizes
    x_pix_size = int(excel_data["x_speed"] * scan_time * 60 / float(x_pixels))
    max_x = int(x_pix_size * float(x_pixels))
    y_pix_size = excel_data["y_step"]
    max_y = int(y_pix_size * float(y_pixels))

    accessions = ["IMS:1000046", "IMS:1000047", "IMS:1000044", "IMS:1000045"]
    names = ["pixel size x", "pixel size y", "max dimension x", "max dimension y"]
    values = [x_pix_size, y_pix_size, max_x, max_y]

    #Actual insertion of data - need to write string into a beautiful soup object with NO FORMATTING to append it
    for i in range(4):
        append_item = f'<cvParam cvRef="IMS" accession="{accessions[i]}" name="{names[i]}" value="{values[i]}"/>\n'
        append_item = BeautifulSoup(append_item,'xml')
        data_need_annotation.scanSettingsList.scanSettings.append(append_item)


    #Write the new file
    with open(result_file,'w') as file:
        file.write(str(data_need_annotation.prettify()))
