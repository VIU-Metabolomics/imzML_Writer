import pandas as pd


def cleanup_table(input_data,path):
    input_data = check_headers(input_data,path)
    input_data = check_column_order(input_data)
    input_data = name_cleanup(input_data)

    return input_data

def name_cleanup(input_data):
    names = input_data.iloc[:,0]
    repl_chars = ["/",".","'"]
    for char in repl_chars:
        names = names.str.replace(char,"_")

    input_data.iloc[:,0]=names

    return input_data

def check_headers(input_data,path):
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

def check_column_order(input_data):
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
