import pandas as pd


def cleanup_table(input_data:pd.DataFrame,path:str):
    """Takes pandas dataframe of columns [mz, name] or vice versa and sanitizes it for imzML scout by:

    1. Making sure headers are consistent with expected (presence) - check_headers()

    2. Makes sure orders are expected (name then mz) - check_column_order()

    3. Cleans up any incompatible characters in the same that will prevent file saving - name_cleanup()
    
    This allows users to specify 'messy' excel sheets for bulk export without imzML Scout failing.

    :param input_data: Pandas dataframe of input mz and name
    :param path: Path to the corresponding excel sheet, unless it needs to be reread to omit headers
    :return: Sanitized pandas dataframe of mz and names compatible with image/csv export of imzML Scout.
"""
    
    input_data = check_headers(input_data,path)
    input_data = check_column_order(input_data)
    input_data = name_cleanup(input_data)

    return input_data

def name_cleanup(input_data:pd.DataFrame):
    """Takes a pandas dataframe of form name, mz and reads the first column (names) replacing 'dangerous' characters with '_' to ensure safe storage.
    
    :param input_data: Pandas dataframe of form [name, mz]
    :return: Pandas dataframe with trouble characters removed."""

    names = input_data.iloc[:,0]
    repl_chars = ["/",".","'"]
    for char in repl_chars:
        names = names.str.replace(char,"_")

    input_data.iloc[:,0]=names

    return input_data

def check_headers(input_data:pd.DataFrame,path:str):
    """Takes a pandas dataframe of mz and name and checks if the headers are missing 
    - taken as a header being convertible to a integer (i.e. an mz value in header). If headers are missing, it
    rereads the sheet specified at [path] with no headers and manually inserts them.
    
    :param input_data: Pandas dataframe with columns of mz and names
    :param path: Absolute or relative path specified as a string
    
    :return: pandas dataframe of mz and names with header inserted, if needed"""
    data_headers = list(input_data)
    no_head = False
    for head in data_headers:
        try: 
            int(head)
            no_head = True
        except:
            pass

    if no_head:
        output_data=pd.read_excel(path,header=None)
    else:
        output_data=input_data
    return output_data

def check_column_order(input_data:pd.DataFrame):
    """Takes a pandas dataframe of mz and names and checks that they're in the order assumed by imzML_Scout (name, mz). If not, reorganizes
    columns to match expected order.
    
    :param input_data: Pandas dataframe containing mz and names of targets
    :return: same dataframe with columns ordered [name, mz]"""
    data_formats = [dtype for dtype in input_data.dtypes]
    headers = list(input_data)
    if data_formats[0]=="float64":
        #mz in column 0, reorder
        input_data=input_data[[headers[1],headers[0]]]
    
    return input_data


# path_file="/Users/josephmonaghan/Downloads/pos_analyte.xlsx"
# data=pd.read_excel(path_file)
# data=cleanup_table(data,path_file)

# print(data)
