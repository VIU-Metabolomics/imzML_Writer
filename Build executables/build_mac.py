import subprocess
import os
import shutil

#Run pyinstaller
build = subprocess.run(["pyinstaller","imzML_Writer_Mac.spec", "--noconfirm", "--distpath", "dist_Mac"])

if build.returncode == 0:
    #give permission to the bash script
    print("Giving permissions to bash script...")
    give_perms = subprocess.run(["chmod", "+x", "mac_build_fix.sh"])
    
    #run the bash script to get the CLI launcher working
    if give_perms.returncode == 0:
        print("Building CLI binary...")
        make_CLI = subprocess.run(["sh", "mac_build_fix.sh"])
        
        #if successful, clean up the associated files needed for imzML_Writer to run
        if make_CLI.returncode == 0:
            print("Adding supplementary files...")
            os.mkdir("./dist_Mac/imzML_Writer.app/Contents/Frameworks/imzML_Writer")
            obo_dir = "obo"
            files = os.listdir(obo_dir)
            dest_dir = "./dist_Mac/imzML_Writer.app/Contents/MacOS/obo"
            os.mkdir(dest_dir)
            for file in files:
                shutil.copy(os.path.join(obo_dir,file),os.path.join(dest_dir,file))
            print("Done!")


