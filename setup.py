# -*- coding: utf-8 -*-

from setuptools import setup, find_packages
from codecs import open
from os import path
import re


version = re.search(
    '^__version__\s*=\s*"(.*)"',
    open('ldndc2nc/ldndc2nc.py').read(),
    re.M
    ).group(1)
 
 
# Get the long description from the README file
with open("README.rst", "rb") as f:
    long_descr = f.read().decode("utf-8")
 

here = path.abspath(path.dirname(__file__))



# get the dependencies and installs
with open(path.join(here, 'requirements.txt'), encoding='utf-8') as f:
    all_reqs = f.read().split('\n')

install_requires = [x.strip() for x in all_reqs if 'git+' not in x]
dependency_links = [x.strip().replace('git+', '') for x in all_reqs if 'git+' not in x]

setup(
    name='ldndc2nc',
    version=__version__,
    description='This package converts LandscapeDNDC output to yearly netCDF files for selected variables',
    long_description=long_description,
    url='https://gitlab.com/cw_code/ldndc2nc',
    download_url='https://gitlab.com/cw_code/ldndc2nc/tarball/' + __version__,
    license='ND',
    classifiers=[
      'Development Status :: 3 - Alpha',
      'Intended Audience :: Developers',
      'Programming Language :: Python :: 2',
    ],
    keywords='',
    packages=find_packages(exclude=['docs', 'tests*']),
    include_package_data=True,
    author='Christian Werner',
    install_requires=install_requires,
    dependency_links=dependency_links,
    author_email='christian.werner@senckenberg.de'
)
