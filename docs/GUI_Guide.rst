How to use the GUI
==================
1. Launch
++++++++++
Launch imzML Writer by double clicking the ``.app`` / ``.exe``:

**Mac:**

.. image:: /images/LaunchFromFinder.png
    :width: 500
    :alt: Finder window showing imzML_Writer.app highlighted

**PC**

.. image:: /images/PC_InstallFileStructure.png
    :width: 500
    :alt: Finder window showing imzML_Writer.app highlighted

Or from python using::
   
    import imzml_writer.imzML_Writer as iw

    iw.gui()

.. image:: ./images/EmptyWindow.png
   :width: 500
   :alt: imzML Writer Launch Screen

2. Select target folder
++++++++++++++++++++++++
Click select Folder to choose the directory containing the ``.raw``, ``.mzML``, or ``.imzML`` data files

.. image:: /images/HighLightSelectFolder.png
   :width: 500
   :alt: Highlighted choose directory button

.. image:: /images/FileNav.png
   :width: 500
   :alt: Navigating to target directory

1. Specify imaging parameters
++++++++++++++++++++++++++++++
Type in the experimental parameters (i.e., X scan speed, Y step, Lock mass) and choose the MS data mode of interest (i.e., Centroid or Profile)
 
.. image:: /images/PopulatedWindow.png
   :width: 500
   :alt: Populated user-input parameters

:X scan speed (µm/s): the speed at which the stage is moving, and the sample is scanned along the x direction

:Y step (µm): stepping size in µm unit (the distance between two adjacent lines in the y direction)

:Lock mass: m/z of a known ion (typically m/z of an internal standard). This serves as a reference point to correct any mass measurement errors that may occur due to instrumental drift or other factors. Leave at 0 to apply no correction.

:Profile: This mode writes the continuous signal from the raw vendor data. Providing a richer dataset, but larger file sizes and longer processing times.

:Centroid: Writes centroid data using msconvert's peakPicking method.

If desired, you can also specify some advanced option by clicking the advanced options button, which will show the following page:

.. image:: /images/ConfigWindow.png
   :width: 500
   :alt: Populated user-input parameters

:0-indexed: Specifies whether coordinates (X, Y) start counting from 0 or 1. Default is 1-indexed.
:Duplicated spectra: Specifies what to do for sparsely sampled regions. Default duplicates and flags spectra in the resulting imzML, but can also be left as an empty pixel when this is checked.
:Lock mass tolerance: Specifies how wide the search window is to look for the lock mass.

1. Start the conversion
++++++++++++++++++++++++
Select one of the conversion options (i.e., Full Conversion, mzML to imzML, or Write imzML Metadata). These should appear contextually based on the
most-abundant file type in your directory. The process will then be begin and can be monitored with the progress bars:

.. image:: /images/PartialimzML.png
    :width: 500
    :alt: Partially converted dataset

:Raw → mzML: progress bar for the conversion of ``.raw`` files to ``.mzML`` format.

:Write imzML: progress bar for the conversion of ``.mzML`` files to ``.imzML`` format.  

:Metadata: Data from the source ``.mzML`` file and user-input parameters are used to populate metadata in the ``.imzML`` file(s).
 
1. View the image with imzML Scout
+++++++++++++++++++++++++++++++++++
Choose an ``.imzML`` file from the file list once the process is complete. Files are split up by scan filters as specified in the mzML. You can view the selected imzML in imzML Scout by clicking ``view imzML``:

.. image:: /images/SelectanImzML.png
    :width: 500
    :alt: Highlighted view imzML button
 

6. Explore the data
+++++++++++++++++++
.. image:: /images/exploreTheData.png
    :width: 500
    :alt: Basic imzML Scout view

View, explore, and/or export the ion images of all m/z features in the chosen scan filter using imzML Scout.
 
Click on any pixel on the ion image, the pixel will turn red and the corresponding mass spectrum will be shown on the right.
 
.. image:: /images/mzAndTolerance.png
    :width: 500
    :alt: Clicked pixel and corresponding mass spectrum shown.

Within imzML Scout, you can select a new m/z to view in two ways:

:Target m/z: Type in the mass-to-charge (m/z) in the input field (red label)
:Mass spectrum: Hover the cursor over the mass spectrum and click on the desired m/z (black label). 

The mass spectrum can be zoomed in by punching in the Start *m/z* and End *m/z* to able to click on the low abundant peaks.
 
Additional parameters can be specified as well:

:Tolerance (ppm): The isolation width (full window; ppm) around the measured mass-to-charge (m/z) that is summed to generate the image. 
:Normalization Method: Select from TIC normalization, custom (e.g. internal standard) normalization, or no normalization.
 
If desired, a custom normalization can be applied (e.g. to compare absolute abundances across images):

.. image:: /images/CustomNorm.png
    :width: 500
    :alt: Highlight box for custom normalization

You can also generate the TIC image by checking the ``View TIC image`` button.

Colormaps are drawn from matplotlib's `standard colormaps <https://matplotlib.org/stable/users/explain/colors/colormaps.html>`_, with several common ones included in the base install. Additional
colormaps can be added by clicking `more cmaps`:

.. image:: /images/MoreCmaps.png
    :width: 500
    :alt: Cmap config display

This calls a popup where you can easily add/remove colormaps from the selection window (settings will be saved for the next time you launch imzML Scout):

.. image:: /images/cmaps.png
    :width: 500
    :alt: Cmap config display

.. image:: /images/pic8.jpg
    :width: 500
    :alt: Various colormaps of the same sample.

You can adjust the contrast settings by sliding the bars to right of the image:

.. image:: /images/ContrastHigh.png
    :width: 250
    :alt: Narrow contrast

.. image:: /images/ContrastLow.png
    :width: 250
    :alt: Wide contrast
  
imzML Scout also supports batch export of images in several image formats (``TIF``, ``png``, ``jpg``) or as a numeric matrix (``csv``). To batch
export, click the ``Bulk export`` or ``Bulk CSV export`` button and navigate to the target spreadsheet (``.xlsx``) specifying which images to export in the form:

.. image:: /images/ExportImage.png
    :width: 500
    :alt: Example spreadsheet layout


.. image:: /images/pic11.png
    :width: 250
    :alt: Example spreadsheet layout
 
The ``include TIC?`` checkbox specifies whether the TIC image / TIC array should be included in the bulk export.

Single targeted m/z can be also be exported by choosing either Export Image or csv Export. 



