import imzml_writer.utils as imzml_utils

import os
import shutil



def check_files(path:str, base_name:str,ext:str,num_lines:int):
    expected = [f"{base_name}{val+1:02d}{ext}" for val in range(num_lines)]
    actual = [file for file in os.listdir(path) if file.endswith(ext)]
    matches = 0
    for file in expected:
        if file in actual:
            matches += 1
    
    return matches, len(actual)

def cleanup_tests():
    """Restores test raw data files from backup after testing is complete"""
    folder_list = ["Agilent", "Thermo", "Waters"]
    base_folder = "tests/test_files"
    backups = "tests/test_files/Backup"

    for current_test in folder_list:
        check_dir = os.path.join(base_folder,current_test)
        if os.path.isdir(check_dir):
            print(f"Deleting files from {current_test} folder")
            shutil.rmtree(check_dir)

        source_dir = os.path.join(backups,current_test)
        print(f"Restoring files from backup for {current_test}")
        shutil.copytree(source_dir, check_dir)


def test_files():
    """Ensures the correct files are available in the test suite"""
    #Thermo
    match_num, num_files = check_files(
        path="tests/test_files/Thermo",
        base_name="20241207_LUM2_Li",
        ext=".raw",
        num_lines=33)
    assert match_num == num_files #Thermo file list should match

    #Agilent
    match_num, num_files = check_files(
        path="tests/test_files/Agilent",
        base_name="PAH cal and samples_0",
        ext=".D",
        num_lines=5
    )
    assert match_num == num_files #Agilent files should match

    #Waters
    match_num, num_files = check_files(
        path="tests/test_files/Waters",
        base_name="AK_comb_",
        ext=".raw",
        num_lines=16
    )
    assert match_num == num_files #Agilent files should match

def test_overall_conversion():
    """Runs the overall conversion on default settings for each file type and ensures you get the expected # of imzML files out (not nec. right yet - RE: scan filter problem for Agilent)"""
    #Thermo
    path = "tests/test_files/Thermo"
    imzml_utils.RAW_to_mzML(path=os.path.abspath(path))
    imzml_utils.clean_raw_files(path,".raw")
    imzml_utils.mzML_to_imzML_convert(PATH=os.path.join(path,"Output mzML Files"))
    imzml_utils.imzML_metadata_process(os.path.join(path,"Output mzML Files"),x_speed=40,y_step=150,path=path)
    out_path = os.path.join(path, "20241207_LUM2_Li")
    out_path_imzMLs = [file for file in os.listdir(out_path) if file.endswith("imzML")]
    assert len(out_path_imzMLs) == 3

    #Agilent
    path = "tests/test_files/Agilent"
    imzml_utils.RAW_to_mzML(path=os.path.abspath(path))
    imzml_utils.clean_raw_files(path,".D")
    imzml_utils.mzML_to_imzML_convert(PATH=os.path.join(path,"Output mzML Files"))
    imzml_utils.imzML_metadata_process(os.path.join(path,"Output mzML Files"),x_speed=40,y_step=150,path=path)
    out_path = os.path.join(path, "PAH cal and samples_00")
    out_path_imzMLs = [file for file in os.listdir(out_path) if file.endswith("imzML")]
    assert len(out_path_imzMLs) == 1

    #Waters
    path = "tests/test_files/Waters"
    imzml_utils.RAW_to_mzML(path=os.path.abspath(path))
    imzml_utils.clean_raw_files(path,".raw")
    imzml_utils.mzML_to_imzML_convert(PATH=os.path.join(path,"Output mzML Files"))
    imzml_utils.imzML_metadata_process(os.path.join(path,"Output mzML Files"),x_speed=40,y_step=150,path=path)
    out_path = os.path.join(path, "AK_comb_")
    out_path_imzMLs = [file for file in os.listdir(out_path) if file.endswith("imzML")]
    assert len(out_path_imzMLs) == 1
    

def test_file_cleanup():
    cleanup_tests()
    test_files()

    

if __name__ == "__main__":
    test_file_cleanup()

