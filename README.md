LandscapeDNDC inventory postprocessor to netCDF format
===============================

![Version](https://img.shields.io/github/v/release/cwerner/ldndc2nc?include_prereleases&sort=semver)
![Python](https://img.shields.io/badge/python-3.6%20%7C%203.7%20%7C%203.8-blue)
![CI](https://github.com/cwerner/ldndc2nc/workflows/CI/badge.svg)
![Style](https://img.shields.io/badge/code%20style-black-000000.svg)

Overview
--------

This package converts LanscapeDNDC output to netCDF files for selected variables.
Currently used for Viet Nam inventory, but in general applicable for all raster-
based LandscapeDNDC simulations.

Installation / Usage
--------------------

To install use pip:

    $ pip install ldndc2nc

    
Contributing
------------

Please file a pull request (PR) at github [here](https://github.com/cwerner/ldndc2nc/pulls).

Example
-------

ldndc2nc -r REFDATA.nc,cid -y 2000-2010 -o output.nc ldndc_results_dir ldndc_netcdf_dir

Usage
-----

```
usage: ldndc2nc [-h] [-c MYCONF] [-l PATTERN] [-o OUTFILE] [-r FILE,VAR] [-s]
                [-S] [-v] [-y YEARS]
                indir outdir

positional arguments:
  indir        location of source ldndc txt files
  outdir       destination of created netCDF files

optional arguments:
  -h, --help   show this help message and exit
  -c MYCONF    use MYCONF file as config (default: None)
  -l PATTERN   limit files by PATTERN (default: None)
  -o OUTFILE   name of the output netCDF file (default: outfile.nc)
  -r FILE,VAR  refdata from netCDF file (default: None)
  -s           split output to yearly netCDF files (default: False)
  -S           make passed config (-c) the new default (default: False)
  -v           increase output verbosity (default: False)
  -y YEARS     range of years to consider (default: 2000-2015)
```

