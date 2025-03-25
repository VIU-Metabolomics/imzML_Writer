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
