LandscapeDNDC inventory postprocessor to netCDF format
===============================

author: Christian Werner (christian.werner@kit.edu)

Overview
--------

This package converts LanscapeDNDC output to netCDF files for selected variables.
Currently used for Viet Nam inventory, but in general applicable for all raster-
based LandscapeDNDC simulations.

Installation / Usage
--------------------

To install use pip:

    $ pip install ldndc2nc


Or clone the repo:

    $ git clone https://github.com/cwerner/ldndc2nc.git
    $ python setup.py install
    
Contributing
------------

TBD

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

