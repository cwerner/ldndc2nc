# -*- coding: utf-8 -*-
#
# ldndc2nc.py
# ==================
#
# Christian Werner
# christian.werner@senckenberg.de
"""ldndc2nc.ldndc2nc: provides entry point main()."""

import argparse
import calendar
import datetime as dt
import glob
import logging
import os
import re
import string
import sys
from collections import OrderedDict

import numpy as np
import pandas as pd
import param
import xarray as xr

from .extra import get_config, parse_config, RefDataBuilder

__version__ = "0.0.2"

log = logging.getLogger(__name__)

# default attributes for netCDF variable of dataarrays
NODATA = -9999
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


def _ndays(yr):
    """ return the number of days in year """
    ndays = 365
    if calendar.isleap(yr):
        ndays = 366
    return ndays


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
        log.critical("Multiple matches! fname: %s" % fname)
        exit(1)
    return fileno


def _select_files(inpath, ldndc_file_type, limiter=""):
    """ find all ldndc outfiles of given type from inpath (limit using limiter)
    
        :param str inpath: path where files are located
        :param str ldndc_file_type: LandscapeDNDC txt filename pattern (i.e. soilcheistry-daily.txt)
        :param str limiter: (optional) limit selection using this expression
        :return: list of matching LandscapeDNDC txt files in indir
        :rtype: list
    """
    infile_pattern = os.path.join(inpath, "*" + ldndc_file_type)
    infiles = glob.glob(infile_pattern)

    if limiter != "":
        infiles = [x for x in infiles if limiter in os.path.basename(x)]

    infiles.sort()

    if len(infiles) == 0:
        msg  = "No LandscapeDNDC input files of type <%s>\n" % ldndc_file_type
        msg += "Input dir:    %s\n" % inpath
        msg += "Pattern used: %s" % infile_pattern
        if limiter != "":
            msg += "\nFilter used:  %s" % limiter
        log.critical(msg)
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
    log.debug("nRows: %s" % ','.join([str(len(x)) for x in df_all]))

    df = pd.concat(df_all, axis=1)
    df.reset_index(inplace=True)

    return (varnames, df)


class CustomFormatter(argparse.ArgumentDefaultsHelpFormatter,
                      argparse.RawDescriptionHelpFormatter):
    pass


def command_line_interface():
    """ command line interface """

    EPILOG  = "Use this tool to create netCDF files based on standard\n"
    EPILOG += "LandscapeDNDC txt output files\n"

    DESCR = "ldndc2nc :: LandscapeDNDC output converter (v%s)\n" % __version__

    parser = argparse.ArgumentParser(description=DESCR,
                                     epilog=EPILOG,
                                     formatter_class=CustomFormatter)

    parser.add_argument('INDIR', help="location of source ldndc txt files")
    parser.add_argument('OUTDIR', help="destination of created netCDF files")

    parser.add_argument("-c",
                        "--config",
                        dest="config",
                        help="use this ldndc2nc config (default if not given)")

    parser.add_argument("-l",
                        "--limit",
                        dest="limiter",
                        help="limit files by this pattern in indir")

    parser.add_argument("-o",
                        "--outfile",
                        dest="outfile",
                        default="outfile.nc",
                        help="name of the output netCDF file (def:outfile.nc)")

    parser.add_argument(
        "-r",
        "--refnc",
        dest="refinfo",
        help="reference netCDF file (syntax: filename.nc,cidvar)")

    parser.add_argument("-s",
                        "--split",
                        dest="split",
                        action='store_true',
                        default=False,
                        help="split output to yearly netCDF files")

    parser.add_argument("-S",
                        "--store-config",
                        dest="storeconfig",
                        action='store_true',
                        default=False,
                        help="make the passed cfg file the new default")

    parser.add_argument("-v",
                        "--verbose",
                        dest="verbose",
                        action="store_true",
                        default=False,
                        help="increase output verbosity")

    parser.add_argument("-y",
                        "--years",
                        dest="years",
                        default="2000-2015",
                        help="range of years to consider")

    args = parser.parse_args()

    print(DESCR)
    log.debug('-' * 50)
    log.debug('ldndc2nc called at: %s' % dt.datetime.now())

    if args.verbose:
        handlers = logging.getLogger().handlers
        for handler in handlers:
            if type(handler) is logging.StreamHandler:
                handler.setLevel(logging.DEBUG)

    if args.storeconfig and (args.config is None):
        log.critical("Option -S requires that you pass a file with -c.")
        exit(1)

    return args


def main():

    args = command_line_interface()

    # process (some) cli arguments
    a = [int(x) for x in string.split(args.years, '-')]
    years = range(a[0], a[1] + 1)

    # read config
    cfg = get_config(args.config)

    if args.storeconfig:
        set_config(cfg)

    def use_passed_conf_file():
        return args.refinfo is not None

    if use_passed_conf_file():
        try:
            refname, refvar = args.refinfo.split(',')
        except:
            log.critical("Specified refinfo not valid: %s" % args.refinfo)
            exit(1)

        if os.path.isfile(refname):
            with (xr.open_dataset(refname)) as refnc:
                if refvar not in refnc.data_vars:
                    log.critical("Var <%s> not in %s" % (refvar, refname))
                    exit(1)
                cell_ids = np.flipud(refnc[refvar].values)
                lats = refnc['lat'].values
                lons = refnc['lon'].values
        else:
            log.critical("Specified reffile %s not found" % refname)
            exit(1)
    else:
        rdb = RefDataBuilder(cfg)
        cell_ids, lats, lons = rdb.build()

    # read source output from ldndc
    varnames, df = read_ldndc_txt(args.INDIR,
                                  cfg['variables'],
                                  years,
                                  limiter=args.limiter)

    Dlut = {}
    for j in range(len(cell_ids)):
        for i in range(len(cell_ids[0])):
            if not np.isnan(cell_ids[j, i]):
                Dlut[int(cell_ids[j, i])] = (len(cell_ids) - j, i)

    ds_all = []

    for yr, yr_group in df.groupby('year'):

        data = {}

        for vname in varnames:
            _blank = np.ma.ones(_ndays(yr), len(cell_ids), len(cell_ids[0]))
            data[vname] = _blank * NODATA
            data[vname][:] = np.ma.masked

        # loop group-wise (group: id)
        for id, id_group in yr_group.groupby('id'):

            jdx, idx = Dlut[id]  # get cell position in array

            for vname in varnames:
                # check for incomplete year data, fill with nodata value till end of year
                if len(id_group[vname]) < len(data[vname][:, 0, 0]):
                    missingvals = _ndays(yr) - len(id_group[vname])
                    dslice = np.concatenate(id_group[vname],
                                            np.asarray([NODATA] * missingvals))
                    log.warn("Data length encountered shorter than expected!")
                else:
                    dslize = id_group[vname]

                data[vname][:, jdx, idx] = dslize

        ds = xr.Dataset()

        # loop over variables and add those the netcdf file
        times = pd.date_range('%s-01-01' % yr,
                              freq='D',
                              periods=_ndays(yr),
                              tz=None)

        for vname in varnames:
            name, units = _split_colname(vname)

            # create dataarray (we need to flip it (!)
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

        if args.split:
            outfilename = args.outfile[:-3] + '_%d' % yr + '.nc'

            ds.to_netcdf(
                os.path.join(args.OUTDIR, outfilename),
                format='NETCDF4_CLASSIC')
            ds.close()
        else:
            ds_all.append(ds)

    if not args.split:
        ds = xr.concat(ds_all, dim='time')
        ds.to_netcdf(
            os.path.join(args.OUTDIR, args.outfile),
            format='NETCDF4_CLASSIC')
        ds.close()
