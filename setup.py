from setuptools import setup, find_packages
from os import path
from imzML_Writer import __version__

working_directory = path.abspath(path.dirname(__file__))

with open(path.join(working_directory,'README.md'),encoding='UTF-8') as f:
    long_description = f.read()

with open('requirements.txt','r') as f:
    requirements = f.read().splitlines()

setup (
    name = "imzML_Writer",
    version = __version__,
    url = "https://github.com/VIU-Metabolomics/imzML_Writer",
    author = "Joseph Monaghan",
    author_email = "Joseph.Monaghan@viu.ca",
    description = "User friendly writing of imzML mass spectrometry imaging files from continuous MSI data",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    include_package_data=True,
    package_data={
        'imzML_Writer': ['Images/*']
    },
    install_requires=requirements,
)