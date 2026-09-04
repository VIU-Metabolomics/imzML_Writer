[![Documentation Status](https://readthedocs.org/projects/imzml-writer/badge/?version=latest)](https://imzml-writer.readthedocs.io/en/latest/?badge=latest)

# **Installation:**

Installing imzML Writer has gotten easier! We're now available as:

1. (**Recommended**) As a python package available from pip:

```
pip install imzml-writer
```

2. (**Experimental**) Standalone app bundles / executables for Mac and PC in the builds folder of the Github.

# **Installation:**

Using imzML Writer depends on msconvert for conversion of raw vendor files to the open format mzML. On PC, this can be installed normally
from Proteowizard:
https://proteowizard.sourceforge.io/download.html

imzML Writer will prompt you for the path to msconvert the first time you try to convert raw files (see Docs), or you can add msconvert to the system path if you'd like to run msconvert from the command line.

On Mac, you can still run msconvert via a docker image. First, install Docker:
https://www.docker.com/products/docker-desktop/

Similarly, imzML Writer will prompt you to download the docker image the first time you try to call it. If you'd like to do this in advance you can open `Terminal.app` and run the command:

```
docker pull chambm/pwiz-skyline-i-agree-to-the-vendor-licenses
```

# **Quickstart**

Once the python package (`pip install imzML-Writer`) and msconvert (or the docker image) have been successful installed, you can quickly
launch the GUI with the script:

```
import imzML_Writer.imzML_Writer as iw

iw.gui()
```

## Combined Zarr output

On Python 3.12 or 3.13, install the optional Thyra integration:

```bash
pip install 'imzML-Writer[zarr]'
```

To convert a directory of completed imzML scan-filter files into one Zarr
store, with one named SpatialData dataset per scan filter:

```python
from imzml_writer.zarr_writer import write_combined_zarr

write_combined_zarr("path/to/imzML/files", "path/to/sample.zarr")
```

Scan filters are summarized into compact labels such as `Positive fullscan`,
`Negative fullscan`, and `Positive product ion scan (m/z 885.5497)`. These are
also written into each MSI table for viewers such as VIUChem. The original
instrument scan-filter string remains available alongside the display name in
the root `imzml_writer_scan_filters` metadata.

Combined conversion enables Thyra's automatic common-mass-axis resampling by
default. This avoids enormous raw union axes for centroid imzML data and keeps
interactive viewers responsive. Pass
`thyra_options={"resampling_config": None}` only when the unresampled union
axis is specifically required.

The final metadata stage can do the same operation directly by passing
`write_zarr=True` to `imzML_metadata_process`.

In the desktop GUI, **Create combined Zarr** appears contextually whenever the
active folder contains completed `.imzML`/`.ibd` pairs. It asks for the Zarr
destination and then opens an optional optical-TIFF picker. Cancel the TIFF
picker to create MSI-only output; selecting an image adds it and opens the
registration preview before the transform is saved.

An optical TIFF can be added to an existing store by path, or selected with a
native file dialog when the path is omitted:

```python
from imzml_writer.zarr_writer import add_optical_image

add_optical_image(
    "path/to/sample.zarr",
    "path/to/optical-image.tiff",
)
add_optical_image("path/to/sample.zarr")  # opens a file dialog
```

The optical image can then be translationally coregistered to the MSI data.
By default, two-class k-means uses every m/z feature in each pixel spectrum to
identify tissue/background. The optical dark and bright masks are both tested,
and a non-wrapping cross-correlation supplies a coarse placement. A
translation-only search across the valid field then uses normalized mutual
information and normalized cross-correlation against the continuous
full-spectrum clustering confidence:

```python
from imzml_writer.zarr_writer import coregister_optical_image

result = coregister_optical_image(
    "path/to/sample.zarr",
    "optical_optical-image",
)
print(result.translation_pixels, result.dice_overlap)
```

This displays the registered intensity and tissue-mask overlays with **Save
automatic**, **Manual override**, and **Discard** buttons. Manual override keeps
the optical image fixed while allowing the colored ion image to be dragged into
place. Its live field accepts one or several comma-separated m/z values;
**Previous** and **Next** cycle through them, and **Next dataset** switches scan
filters. Weak NMI/NCC agreement is highlighted in the automatic preview. MSI
x/y spacing is read independently from Thyra's imzML detection
metadata, so rectangular MSI pixels are displayed and registered in their true
physical aspect ratio. Pass `msi_pixel_size_um=(40, 150)` to override that
metadata. Optical spacing is read from OME-XML or calibrated TIFF resolution
tags when the image is added. It can be overridden with
`optical_pixel_size_um=2.5`. Use `save=True` to save without prompting, or
`save=False` to calculate and return a non-mutating result.

The complete optical image is searched by default; no tissue ROI selection is
required. An explicit crop can still be supplied with
`optical_roi=(x0, y0, x1, y1)`, or selected interactively with
`select_roi=True` for unusually large optical fields.

Pass `ion_image_name="<dataset>_z0_tic"` to register against one specific ion
dataset instead of combining the tissue masks from all MSI tables. The earlier
intensity-only behavior remains available with `segmentation="tic"`. The method
estimates translation only; it does not correct rotation or nonlinear distortion.

By default, scan-filter masks are weighted by spatial coherence and border
contact, allowing a strong tissue silhouette to dominate noisy or weak filters.
Set `minimum_tissue_votes=2` (or another integer) to use a fixed cross-filter
vote threshold instead.

Accepting the registration also stores the aggregate mask as the SpatialData
label `msi_spectral_tissue_mask`. Every selected MSI table receives a boolean
`obs["tissue"]` column and a continuous `obs["tissue_confidence"]` column, so
background spectra can be excluded directly:

```python
from spatialdata import read_zarr

sdata = read_zarr("path/to/sample.zarr")
table = sdata.tables["<scan-filter>_z0"]
tissue_only = table[table.obs["tissue"]].copy()
```

The accepted mapping is written both to the physical `global` coordinate system
and to the MSI-to-optical `registered` coordinate system used by viu_chem.
Standalone label metadata is normalized automatically to avoid ome-zarr's
spurious `no parent found` message. Existing stores can be repaired without
rerunning registration:

```python
from imzml_writer.zarr_writer import repair_standalone_label_metadata

repair_standalone_label_metadata("path/to/sample.zarr")
```

# **Compatibility**

| Software                                                               | Functioning? | Comments                                                           |
| ---------------------------------------------------------------------- | ------------ | ------------------------------------------------------------------ |
| [Cardinal MSI](https://cardinalmsi.org)                                | Yes          |                                                                    |
| [METASPACE](https://metaspace2020.org)                                 | Yes          |                                                                    |
| [M2aia](https://m2aia.de)                                              | Yes          |                                                                    |
| [MSIReader](https://msireader.com)                                     | Yes          |                                                                    |
| [Julia mzML_imzML](https://github.com/CINVESTAV-LABI/julia_mzML_imzML) | Yes          |                                                                    |
| [SCiLS Lab](https://www.bruker.com/en.html)                            | Yes          | Pixel dimensions must be written as an integer to be read properly |
| [Mozaic](https://spectroswiss.ch/software/)                            | Yes          |

# **Documentation**

Detailed installation instructions, quickstart guides, and documentation are available on the ReadTheDocs page:
https://imzml-writer.readthedocs.io/en/latest/

# **Contact us**

Please direct any questions, concerns, or feature requests to me at Joseph.Monaghan@viu.ca
