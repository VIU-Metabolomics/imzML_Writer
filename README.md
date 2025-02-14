[![Documentation Status](https://readthedocs.org/projects/imzml-writer/badge/?version=latest)](https://imzml-writer.readthedocs.io/en/latest/?badge=latest)

# **Installation:**

Installing imzML Writer has gotten easier! We're now available as:

1. (**Recommended**) As a python package available from pip:

```
pip install imzml-writer
```

2. (**Experimental**) Standalone app bundles / executables for Mac and PC in the builds folder of the Github.

3. (**Developer mode**) By cloning the Github repo for direct usage.

# **Installation:**

Using imzML Writer depends on msconvert for conversion of raw vendor files to the open format mzML. On PC, this can be installed normally
from Proteowizard:
https://proteowizard.sourceforge.io/download.html

On Mac, you can still run msconvert via a docker image. First, install Docker:
https://www.docker.com/products/docker-desktop/

Then, open `Terminal.app` and run the command:

```
docker pull chambm/pwiz-skyline-i-agree-to-the-vendor-licenses
```

Once complete, you should be good to go.

# **Quickstart**

Once the python package (`pip install imzML-Writer`) and msconvert (or the docker image) have been successful installed, you can quickly
launch the GUI with the script:

```
import imzML_Writer.imzML_Writer as iw

iw.gui()
```

# **Documentation**

Detailed installation instructions, quickstart guides, and documentation are available on the ReadTheDocs page:
https://imzml-writer.readthedocs.io/en/latest/

# **Contact us**

Please direct any questions, concerns, or feature requests to me at Joseph.Monaghan@viu.ca
