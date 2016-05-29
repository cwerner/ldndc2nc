# -*- coding: utf-8 -*-
#
# ldndc2nc.py
# ==================
#
# Christian Werner
# christian.werner@senckenberg.de
"""ldndc2nc.ldndc2nc: provides entry point main()."""

import glob
import os
import pprint
import re
import sys
import datetime as dt
from collections import OrderedDict
from optparse import OptionParser

import pandas as pd
import param

from .extra import Extra, get_config

__version__ = "0.0.1"

# __version__ = param.Version(release=(0,0,1), fpath=__file__,
#                            commit="$Format:%h$", reponame='ldndc2nc')

# default attributes for netCDF variable
defaultAttrsDA = {'_FillValue': -9999, 'missing_value': -9999}


# functions
def _split_colname(vname):
    """ split ldndc colname into varname and units (based on [) """

    out = (vname, "unknown")
    if '[' in vname:
        name, var_units = vname.split('[')
        units = var_units[:-1]
        out = (name, units)
    return out


def daterange(start_date, end_date):
    for n in range(int((end_date - start_date).days)):
        yield start_date + dt.timedelta(n)


def get_ldndc_txt_fileno(fname):
    fname  = os.path.basename(fname)
    fileno = 0 
    # find leading zero filenumber in string
    # (must be 2-6 digits long)
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


def select_ldndc_files(inpath, ldndc_file_type, limiter=None):
    """ get all ldndc outfiles of given filetype from inpath (limit using limiter) """
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



def read_ldndc_txt(inpath, varData, limiter):
    """ parse ldndc txt output files and return dataframe """

    YEARS = range(2000, 2015)

    ldndc_file_types = varData.keys()

    varnames = []  # (updated) column names
    Dids = {}  # file ids

    df_all = []


    for ldndc_file_type in ldndc_file_types:

        dfs = []
        df_names = []

        infiles = select_ldndc_files(inpath, ldndc_file_type)

        # special treatment for tuple entries in varData
        for vals in varData[ldndc_file_type]:
            if type(vals) == tuple:
                varnames.append(vals[0])
                df_names += vals[1]
            else:
                varnames.append(vals)
                df_names.append(vals)

        # standard columns
        basecols = ['id', 'year', 'julianday']

        # iterate over all files of one ldndc file type
        for fcnt, fname in enumerate(infiles):

            fno = get_ldndc_txt_fileno(fname)

            # read target columns (basecols + df_names)
            df = pd.read_csv(fname,
                             delim_whitespace=True,
                             error_bad_lines=False,
                             usecols=basecols + df_names)

            # store a full set of cell ids in file
            if Dids.has_key(fno) == False:
                Dids[fno] = sorted(list(OrderedDict.fromkeys(df['id'])))

            # limit data to specified year range

            def limit_years(years, df):
                """ limit df to specified years """
                if years[-1] - years[0] == len(years) - 1:
                    df = df[(df.year >= years[0]) & (df.year <= years[-1])]
                else:
                    df = df[df.year.isin(years)]
                return df

            df = limit_years(YEARS, df)
            df = df.sort(basecols)

            # create date range (in case we have missing data)
            dates_in_file = list(daterange(
                dt.date(YEARS[0], 1, 1), dt.date(YEARS[-1] + 1, 1, 1)))

            # calculate full table length ids * dates
            full_df_length = len(Dids[fid]) * len(dates_in_file)

            # we have less data rows than we should have (i.e. report files)
            # fix this by stretching the dataframe to the appropriate length
            if len(df) < full_df_length:

                dtuples = [(0, x.year, x.timetuple().tm_yday)
                           for x in dates_in_file]

                df_ref_all = []
                for id in Dids[fid]:
                    df_ref = pd.DataFrame(dtuples, columns=basecols)
                    df_ref['id'] = id
                    df_ref_all.append(df_ref)
                df_ref = pd.concat(df_ref_all, axis=0)

                # merge data dataframe with this reference df
                df = pd.merge(df_ref, df, how='left', on=basecols)

                # fill all new rows with zeros
                df = df.fillna(0.0)
                df.reset_index()

            # sort again (just to be sure)
            df = df.sort(basecols)

        # we don't have any dataframes, return
        if len(dfs) == 0:
            continue

        # concat the dataframes for the split output (000, 001, ...)
        df = pd.concat(dfs, axis=0)
        df.set_index(['id', 'year', 'julianday'], inplace=True)

        # merge mulitple entry columns (from individual output files: i.e. soilchemistry, harvest-report, ...)
        for v in varData[ldndc_txt_file]:

            # we have an occurance of 'create a new column based on multiple original ones'
            if type(v) == tuple:
                # sum original columns
                df[v[0]] = df[v[1]].sum(axis=1)

                # drop original columns if they are not requested
                for v2 in varData[ldndc_txt_file]:
                    if type(v2) != tuple:
                        if v2 in v[1]:
                            v[1].remove(v2)

                for v3 in v[1]:
                    df.drop(v3, axis=1)

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
        "-s",
        "--split",
        dest="split",
        action='store_true',
        default=False,
        help="split output in yearly netCDF files with daily resolution")

    parser.add_option(
        "-y",
        "--years",
        dest="years",
        default="2000-2015",
        help="give the range of years to consider (def:2000-2015)")

    parser.add_option("-o",
                      "--outfile",
                      dest="outname",
                      default="outfile.nc",
                      help="name of the output netCDF file (def:outfile.nc)")

    parser.add_option(
        "-c",
        "--config",
        dest="config",
        default=None,
        help="use specific ldndc2nc config file, otherwise look in default locations")

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

    # get command line args and options
    options, args = cli()

    INPATH = args[0]
    OUTPATH = args[1]

    # parse rcfile
    cfg = get_config(options.config)
    if cfg == None:
        print 'No ldndc2nc.conf file found in the required places... exit'
        exit(1)

    inpath = '.'
    varData = cfg.variables
    limiter = ''  # restrict files by this string

    # parse ldndc output files
    varnames, df = read_ldndc_txt(inpath, cfg.variables, limiter)

    NODATA = -9999
    PATHREFDATA = '.'
    REFNC = 'VN_MISC4.nc'

    # read sim ids from reference file
    with (xr.open_dataset(os.path.join(PATHREFDATA, REFNC))) as refnc:
        ids = refnc['cid'].values
        lats = refnc['lat'].values
        lons = refnc['lon'].values

    # create dictionary to quickly map id to ix, jx coordinates of netcdf file
    idx = np.array(range(len(ids[0])) * len(ids)).reshape(ids.shape)
    jdx = np.array([[x] * len(ids[0]) for x in range(len(ids))])

    # TODO make this nicer
    # create lookup dictionary
    Dlut = {}
    for i in range(len(ids)):
        for j in range(len(ids[0])):
            if np.isnan(ids[i, j]) == False:
                Dlut[int(ids[i, j])] = (idx[i, j], jdx[i, j])

    if SPLIT:
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
                ds[vname] = da

            # write netcdf file
            ds.attrs.update(defaultAttrsDS)
            ds.to_netcdf(
                os.path.join(OUTPATH, options.outfile),
                format='NETCDF4_CLASSIC')

            ds.close()


class Boo(Extra):
    pass
