imzml\_writer
=====================

imzml\_writer.imzML\_Writer
----------------------------------

.. automodule:: imzML_Writer.imzML_Writer
   :members:
   :undoc-members:
   :show-inheritance:

Typical launch will appear as::

   import imzml_writer.imzML_Writer as iw

   ##Launch with no target directory - navigate with UI
   iw.gui()

   ##Launch with target directory to open directory
   path = "/path/to/your/imzML/files/example.imzML"
   iw.gui(path)

For detailed instructions on navigating the GUI, see the user guide.

imzml\_writer.imzML\_Scout
---------------------------------

.. automodule:: imzml_writer.imzML_Scout
   :members:
   :undoc-members:
   :show-inheritance:

Typically called during normal operation of imzML_Writer, but call also be called directly::

   import imzml_writer.imzML_Scout as scout

   ##Call with no arguments opens it empty and you can use the GUI to search for your file
   scout.main()

   ##Call with full or relative pathing to the imzML will open the specified file
   path_to_imzML = "/Example/File/path/my_image.imzML"
   scout.main(path_to_imzML)

For detailed instructions on navigating the GUI, see the user guide.

imzml\_writer.ms\_convert\_gui
-------------------------------------

.. automodule:: imzml_writer.ms_convert_gui
   :members:
   :undoc-members:
   :show-inheritance:

imzml\_writer.utils
-----------------------------------

.. automodule:: imzml_writer.utils
   :members:
   :undoc-members:
   :show-inheritance:

imzml\_writer.recalibrate\_mz
------------------------------------

.. automodule:: imzml_writer.recalibrate_mz
   :members:
   :undoc-members:
   :show-inheritance:

imzml\_writer.analyte\_list\_cleanup
-------------------------------------------

.. automodule:: imzml_writer.analyte_list_cleanup
   :members:
   :undoc-members:
   :show-inheritance:


