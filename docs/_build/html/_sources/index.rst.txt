.. imzML Writer documentation master file, created by
   sphinx-quickstart on Thu Feb 13 08:52:30 2025.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

.. image:: ../imzML_Writer/Images/Logo-01.png
   :width: 250
   :alt: imzML Writer Logo

Welcome & Guide
==========================
Welcome to the `imzML_Writer <https://github.com/VIU-Metabolomics/imzML_Writer>`_ documentation page! 

imzML_Writer is available as:

#. (**Recommended**) A distributable package on pypi (for CLI, stable GUI, ``pip install imzML-Writer``).
#. (**Experimental**) A simple standalone executable on both Mac and PC (.app and .exe respectively).*

*: Both imzML Writer and Scout are available on Mac, but only Writer is available on PC at this time.


Installation
============

.. _msconvertlabel:

MS Convert
**********
For both versions, imzML Writer relies on MS convert to convert raw instrument data into the open format mzML, requiring a working install.

**On PC**, download the latest msconvert release from `ProteoWizard <https://proteowizard.sourceforge.io/download.html>`_ and navigate through the installer. 
If you want to run msconvert from the command line, make sure that msconvert is added to the system PATH, either during installation or by following the instructions `here <https://www.eukhost.com/kb/how-to-add-to-the-path-on-windows-10-and-windows-11/>`_.

For use with imzML Writer, you can skip this step and will instead be prompted to search (automatically or manually) for msconvert's install location the first time you go to convert files:

.. image:: /images/MSConvert_popup.png
   :width: 300
   :alt: msconvert popup when it isn't in the path


**On Mac**, download  `Docker <https://www.docker.com/products/docker-desktop/>`_ and open up the GUI dashboard. You will be prompted to install the docker image for msconvert the first time you try to convert some raw files:

.. image:: /images/DockerImagePrompt.png
   :width: 250
   :alt: Docker image install/update

Note that this may take several minutes to download/install. If this isn't working, you can manually `download the docker image <https://hub.docker.com/r/chambm/pwiz-skyline-i-agree-to-the-vendor-licenses>`_ by opening the **Terminal app** and running the command:

``docker pull chambm/pwiz-skyline-i-agree-to-the-vendor-licenses``

You can verify successful install in the Docker dashboard under the images tab:

.. image:: /images/DockerImage.png
   :width: 600
   :alt: Docker GUI showing successful msconvert image


Python package
*****************
Running imzML Writer from the python package is the **recommended** option for most users, allowing for both stable GUI use and a command line interface (CLI) for batch processing.

To install, make sure you have Docker (Mac) or MSconvert (PC) installed as above. Then, in your python environment run:

``pip install imzML-Writer``

Once active, you can easily launch the GUI by creating a python ``example.py`` with contents::

   import imzML_Writer.imzML_Writer as iw

   iw.gui()


Then run the script (``python example.py``) to launch the GUI. If you already have some imzML files and just want to view them with the scout, restructure ``example.py``::

   import imzML_Writer.imzML_Scout as scout

   ##Call with no arguments opens it empty and you can use the GUI to search for your file
   scout.main()

   ##Call with full or relative pathing to the imzML will open the specified file
   path_to_imzML = "/Example/File/path/my_image.imzML"
   scout.main(path_to_imzML)
   

This covers the basic GUI functionality, for further details on running the CLI see the documentation pages.



Standalone apps
******************
Mac
---
Download the `App Bundle from Github <https://github.com/VIU-Metabolomics/imzML_Writer/releases/tag/alpha>`_ and grab the Mac distribution.


Move the **imzML_Writer.app** file into your Applications folder (**Note**: This step is required). Then double-click the .app bundle to launch the application.
Depending on your security settings, Apple may block the launch with the following pop-up:


.. image:: /images/SecurityPopup.png
   :width: 300
   :alt: Security popup for imzML_Writer.

If so, click ok (***not** move to trash*), navigate to your security settings (``System Settings --> Privacy & Security``), scroll to the bottom, and click "open anyways" for imzML_Writer.


.. image:: /images/SecurityAddPerms.png
   :width: 300
   :alt: Security popup for imzML_Writer.


This should launch the UI and the application is ready for typical operation.

PC
--
Download the `PC distribution from the Github release <https://github.com/VIU-Metabolomics/imzML_Writer/releases/tag/alpha>`_, move the entire PC executable folder (imzML_Writer.exe, obo folder, & _internal folder) and place it somewhere convenient on your PC.


.. image:: /images/PC_InstallFileStructure.png
   :width: 600
   :alt: File structure for PC installation.


Then, open the folder and launch *imzML Writer* by double-clicking imzML_Writer.exe. This will launch a terminal window and the GUI. Provided msconvert is installed and added to the path, you should be good to go!

.. toctree::
   :maxdepth: 3
   :caption: Table of Contents

   index
   Quick Start <QuickStart>
   GUI User Guide <GUI_Guide>
   Function Documentation <modules>

