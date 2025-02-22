#**Steps to build mac GUI**

1. Run pyinstaller to write the bulk .app file (from the Build executables directory):

```
   pyinstaller imzML_Writer_Mac.spec --noconfirm --distpath dist_Mac
```

2. Double check that it was successful - should have a new folder dist with the .app file

3. Ensure the mac_fixer can be executed (credit and many thanks to to: https://github.com/pyinstaller/pyinstaller/issues/5154#issuecomment-2508011279):

```
   chmod +x mac_build_fix.sh
```

4. Run the mac fixer:

```
   sh mac_build_fix.sh
```

5. Double check that it was successful by opening the imzML_Writer.app (show package contents), there should be two executables in the Contents/MacOS/ folder - imzML_Writer (~200 bytes) and imzML_Writer_cli (~50 MB)

6. Paste the obo folder into Contents/MacOS folder alongside the executables, this allows pymzml to run (not the cleanest implementation :/), additionally, in the frameworks folder add a new directory "imzML_Writer" to provide a place to save settings
7. Exit the imzML_Writer package contents, and paste the entire .app bundle into the Applications folder - this should allow it to run normally and you're good to go!

#**NOTES:**
-It takes a little while to launch (~20-30 secs on my laptop) as it initializes the environment, a terminal will launch to indicate something is happening, don't X this out
-The .app bundle MUST be in the application folder to run properly
-The above instructions are only to build NEW versions of the .app distributable, if you're only interested in running imzML_Writer just run the already available application
