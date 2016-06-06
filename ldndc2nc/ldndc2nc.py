# -*- coding: utf-8 -*-
#
# ldndc2nc.py
# ==================
#
# Christian Werner
# christian.werner@senckenberg.de
"""ldndc2nc.ldndc2nc: provides entry point main()."""

import calendar
import glob
import os
import re
import string
import sys
import datetime as dt
from collections import OrderedDict
from optparse import OptionParser

import numpy as np
import pandas as pd
import param
import xarray as xr

from .extra import get_config

__version__ = "0.0.1"

# __version__ = param.Version(release=(0,0,1), fpath=__file__,
#                            commit="$Format:%h$", reponame='ldndc2nc')

NODATA = -9999

# default attributes for netCDF variable of dataarrays
defaultAttrsDA = {'_FillValue': NODATA, 'missing_value': NODATA}


# functions
def _split_colname(colname):
    """ split colname into varname and units 

        :param str colname: original ldndc outputfile colname
        :return: varname and unit
        :rtype: tuple
    """
    out = (colname, "unknown")
    if '[' in colname:
        name, var_units = colname.split('[')
        units = var_units[:-1]
        out = (name, units)
    return out


def _daterange(start_date, end_date):
    """ create timeseries
    
        :param str start_date: start date
        :param str end_date: start date

        :return: list of dates
        :rtype: iterator
    """
    for n in range(int((end_date - start_date).days)):
        yield start_date + dt.timedelta(n)


def _is_composite_var(v):
    return type(v) == tuple


def _extract_fileno(fname):
    """ extract file iterator
    
        :param str fname: ldndc txt filename
        :return: file number
        :rtype: int

        example: GLOBAL_002_soilchemistry-daily.txt -> 002 -> 2
    """
    fname = os.path.basename(fname)
    fileno = 0
    # find fileno in string (must be 2-6 digits long)
    x = re.findall(r"[0-9]{2,6}(?![0-9])", fname)
    if len(x) == 0:
        pass
    elif len(x) == 1:
        fileno = int(x[0])
    else:
        print 'Multiple matches! This should not be.'
        print fname
        raise
    return fileno


def _select_files(inpath, ldndc_file_type, limiter=None):
    """ find all ldndc outfiles of given type from inpath (limit using limiter)
    
        :param str inpath: path where files are located
        :param str ldndc_file_type: LandscapeDNDC txt filename pattern (i.e. soilcheistry-daily.txt)
        :param str limiter: (optional) limit selection using this expression
        :return: list of matching LandscapeDNDC txt files in indir
        :rtype: list
    """
    infile_pattern = os.path.join(inpath, "*" + ldndc_file_type)
    infiles = glob.glob(infile_pattern)

    if limiter is not None:
        infiles = [x for x in infiles if limiter in os.path.basename(x)]

    infiles.sort()

    if len(infiles) == 0:
        print '\nNo LDNDC output files of type "%s"' % ldndc_file_type
        print 'Input directory:', inpath
        print 'Pattern used:   ', infile_pattern
        if limiter is not None:
            print 'Filter used:', limiter
        exit(1)

    return infiles


def _limit_years(years, df, yearcol='year'):
    """ limit data.frame to specified years """
    if years[-1] - years[0] == len(years) - 1:
        df = df[(df[yearcol] >= years[0]) & (df[yearcol] <= years[-1])]
    else:
        df = df[df[yearcol].isin(years)]
    return df


def read_ldndc_txt(inpath, varData, years, limiter=''):
    """ parse ldndc txt output files and return dataframe """

    ldndc_file_types = varData.keys()

    varnames = []  # (updated) column names
    Dids = {}  # file ids

    df_all = []

    for ldndc_file_type in ldndc_file_types:

        dfs = []
        datacols = []

        infiles = _select_files(inpath, ldndc_file_type, limiter=limiter)

        # special treatment for tuple entries in varData
        for v in varData[ldndc_file_type]:
            if _is_composite_var(v):
                varnames.append(v[0])
                datacols += v[1]
            else:
                varnames.append(v)
                datacols.append(v)

        # standard columns
        basecols = ['id', 'year', 'julianday']

        # iterate over all files of one ldndc file type
        for fcnt, fname in enumerate(infiles):

            fno = _extract_fileno(fname)

            df = pd.read_csv(fname,
                             delim_whitespace=True,
                             error_bad_lines=False,
                             usecols=basecols + datacols)

            # store a full set of cell ids in file
            if Dids.has_key(fno) == False:
                Dids[fno] = sorted(list(OrderedDict.fromkeys(df['id'])))

            df = _limit_years(years, df)
            df = df.sort_values(by=basecols)

            # calculate full table length ids * dates

            daterange_file = list(_daterange(
                dt.date(years[0], 1, 1), dt.date(years[-1] + 1, 1, 1)))

            expected_len_df = len(Dids[fno]) * len(daterange_file)
            actual_len_df = len(df)

            if actual_len_df < expected_len_df:
                basecoldata = [(0, d.year, d.timetuple().tm_yday)
                               for d in daterange_file]

                df_ref_all = []
                for id in Dids[fno]:
                    df_ref = pd.DataFrame(basecoldata, columns=basecols)
                    df_ref.id = id
                    df_ref_all.append(df_ref)
                df_template = pd.concat(df_ref_all, axis=0)

                # merge data from file to df template, values of missing days
                # in file will be assigned 0.0
                df = pd.merge(df_template, df, how='left', on=basecols)
                df = df.fillna(0.0)
                df.reset_index()

            df = df.sort_values(by=basecols)
            dfs.append(df)

        # we don't have any dataframes, return
        if len(dfs) == 0:
            continue

        # concat the dataframes for the split output (000, 001, ...)
        df = pd.concat(dfs, axis=0)
        df.set_index(['id', 'year', 'julianday'], inplace=True)

        for v in varData[ldndc_file_type]:

            if _is_composite_var(v):
                new_colname, src_colnames = v
                drop_colnames = []

                df[new_colname] = df[src_colnames].sum(axis=1)

                # drop original columns if they are not explicitly requested
                for v2 in varData[ldndc_file_type]:
                    if not _is_composite_var(v2):
                        if v2 in src_colnames:
                            drop_colnames.append(v2)

                df.drop(drop_colnames, axis=1)

        # TODO check why we have this line
        df = df[~df.index.duplicated(keep='first')]
        df_all.append(df)

    # check if all tables have the same number of rows
    print [len(x) for x in df_all]

    df = pd.concat(df_all, axis=1)
    df.reset_index(inplace=True)

    return (varnames, df)


class MyParser(OptionParser):
    def format_epilog(self, formatter):
        return self.epilog


def cli():
    """ command line interface """

    parser = MyParser( "usage: %prog [options] indir outdir", \
            epilog="""
Use this tool to create netCDF files based on standard
LandscapeDNDC txt output files
""")

    parser.add_option(
        "-c",
        "--config",
        dest="config",
        default=None,
        help="use specific ldndc2nc config file, otherwise look in default locations")

    parser.add_option(
        "-l",
        "--limit",
        dest="limiter",
        default='',
        help="limit files by this pattern in indir")

    parser.add_option(
        "-o",
        "--outfile",
        dest="outfile",
        default="outfile.nc",
        help="name of the output netCDF file (def:outfile.nc)")

    parser.add_option(
        "-r",
        "--refnc",
        dest="refinfo",
        default="",
        help="reference nc file (syntax: filename.nc,cidvar)")

    parser.add_option(
        "-s",
        "--split",
        dest="split",
        action='store_true',
        default=False,
        help="split output in yearly netCDF files with daily resolution")

    parser.add_option(
        "-S",
        "--store-config",
        dest="storeconfig",
        action='store_true',
        default=False,
        help="make the passed config file the new default")

    parser.add_option(
        "-y",
        "--years",
        dest="years",
        default="2000-2015",
        help="give the range of years to consider (def:2000-2015)")

    (options, args) = parser.parse_args()

    if len(args) != 2:
        print "\nYou need to specify an input and output directory.\nExiting...\n"
        parser.print_help()
        exit(1)

    return (options, args)


def greetScreen():

    header = """ldndc2nc :: LandscapeDNDC output converter (v%s)""" % __version__
    print(header)


def main():

    greetScreen()

    # process command line args and options
    options, args = cli()

    inpath = args[0]
    outpath = args[1]

    a = [int(x) for x in string.split(options.years, '-')]
    years = range(a[0], a[1] + 1)

    # read config
    cfg = get_config(options.config)

    # store it
    if options.storeconfig:
        if options.config is not None:
            set_config( cfg )
        else:
            print 'You need to pass a valid config file with the -c option.'
            exit(1)

    if options.refinfo != "":
        # use cli-specified refnc file
        try:
            refname, refvar = options.refinfo.split(',')
        except:
            print "Error"
            raise

        if os.path.isfile( refname ):
            with (xr.open_dataset( refname )) as refnc:
                if refvar not in refnc.data_vars:
                    print "Reffile cell id variable <%s> not found in file\n%s" % (refvar, refname)
                    exit(1)
                ids = refnc[refvar].values
                lats = refnc['lat'].values
                lons = refnc['lon'].values
        else:
            print "Reffile %s not found."
            exit(1)

    # read source output from ldndc
    varnames, df = read_ldndc_txt(inpath, cfg.variables, years, limiter=options.limiter)

    idx = np.array(range(len(ids[0])) * len(ids)).reshape(ids.shape)
    jdx = np.array([[x] * len(ids[0]) for x in range(len(ids))])

    # TODO make this nicer
    # create lookup dictionary
    Dlut = {}
    for i in range(len(ids)):
        for j in range(len(ids[0])):
            if np.isnan(ids[i, j]) == False:
                Dlut[int(ids[i, j])] = (idx[i, j], jdx[i, j])

    if options.split:
        print " Splitting into yearly chucks"

        # loop group-wise (group: year)
        for yr, yr_group in df.groupby('year'):

            data = {}
            zsize = 365
            if calendar.isleap(yr): zsize = 366

            for vname in varnames:
                data[vname] = np.ma.ones((zsize, len(ids), len(ids[0])
                                          )) * NODATA
                data[vname][:] = np.ma.masked

            # loop group-wise (group: id)
            for id, id_group in yr_group.groupby('id'):

                idx, jdx = Dlut[id]  # get cell position in array

                for vname in varnames:
                    # check for incomplete year data, fill with nodata value till end of year
                    if len(id_group[vname]) < len(data[vname][:, 0, 0]):
                        missingvals = zsize - len(id_group[vname])
                        dslice = np.concatenate(id_group[vname],
                                                np.asarray([NODATA] *
                                                           missingvals))
                        print len(dslice)
                    else:
                        dslize = id_group[vname]

                    data[vname][:, jdx, idx] = dslize

            # create an empty netcdf dataset
            ds = xr.Dataset()

            # loop over variables and add those the netcdf file
            times = pd.date_range('%s-01-01' % yr,
                                  freq='D',
                                  periods=zsize,
                                  tz=None)

            for vname in varnames:
                name, units = _split_colname(vname)
                da = xr.DataArray(data[vname],
                                  coords=[('time', times), ('lat', lats),
                                          ('lon', lons)])
                da.name = name
                da.attrs.update(defaultAttrsDA)
                da.attrs['units'] = units

                # more optimization for faster netcdfs !!!
                da.encoding.update({'complevel': 5,
                                    'zlib': True,
                                    'chunksizes': (10, 40, 20),
                                    'shuffle': True})  # add compression
                ds[name] = da

            # write netcdf file
            # TODO enable, read info from ldndc.conf
            #ds.attrs.update(defaultAttrsDS)
            outfilename = options.outfile

            if options.split:
                outfilename = outfilename[:-3] + '_%d' % yr + '.nc'

            ds.to_netcdf(
                os.path.join(outpath, outfilename),
                format='NETCDF4_CLASSIC')

            ds.close()
