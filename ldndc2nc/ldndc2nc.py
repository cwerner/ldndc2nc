# -*- coding: utf-8 -*-
#
# ldndc2nc.py
# ==================
"""ldndc2nc.ldndc2nc: provides entry point main()."""

import calendar
import datetime as dt
import gzip
import logging
import re
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

from .cli import cli
from .config_handler import ConfigHandler

log = logging.getLogger(__name__)

# default attributes for netCDF variable of dataarrays
NODATA = -9999
defaultAttrsDA = {"_FillValue": NODATA, "missing_value": NODATA}

# standard columns
basecols = ["id"]


# functions
def _split_colname(colname):
    """ split colname into varname and units

        :param str colname: original ldndc outputfile colname
        :return: varname and unit
        :rtype: tuple
    """
    out = (colname, "unknown")
    if "[" in colname:
        name, var_units = colname.split("[")
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


def _gapfill_df(df, dates, ids):
    """ gap-fill data.frame """
    basecoldata = [(0, d.year, d.timetuple().tm_yday) for d in dates]
    df_ref_all = []
    for id in ids:
        df_ref = pd.DataFrame(basecoldata, columns=basecols)
        df_ref.id = id
        df_ref_all.append(df_ref)
    df_template = pd.concat(df_ref_all, axis=0)
    df = pd.merge(df_template, df, how="left", on=basecols)
    df = df.fillna(0.0)
    df.reset_index()
    return df


def _ndays(yr):
    """ return the number of days in year """
    ndays = 365
    if calendar.isleap(yr):
        ndays = 366
    return ndays


def _is_composite_var(v):
    return type(v) == tuple


def _all_items_identical(x):
    return x.count(x[0]) == len(x)


def create_id_mapper(cell_ids: xr.DataArray):
    dm = {}
    for ila, la in enumerate(cell_ids.lat.values):
        for ilo, lo in enumerate(cell_ids.lon.values):
            the_id = cell_ids.loc[{"lat": la, "lon": lo}].values
            if not np.isnan(the_id):
                dm[int(the_id)] = (la, lo)
    return dm


def _extract_fileno(fname):
    """ extract file iterator

        :param str fname: ldndc txt filename
        :return: file number
        :rtype: int

        example: GLOBAL_002_soilchemistry-daily.txt -> 002 -> 2
    """
    fname = fname.name
    fileno = 0
    # find fileno in string (must be 2-6 digits long)
    x = re.findall(r"[0-9]{2,6}(?![0-9])", fname)
    if len(x) == 0:
        pass
    elif len(x) in [1, 2]:
        fileno = int(x[0])
    else:
        log.critical("Multiple matches! fname: %s" % fname)
        exit(1)
    return fileno


def _select_files(inpath, ldndc_file_type, limiter=""):
    """ find all ldndc outfiles of given type from inpath (limit using limiter)

        :param str inpath: path where files are located
        :param str ldndc_file_type: LandscapeDNDC txt filename pattern
                   (i.e. soilchemistry-daily.txt)
        :param str limiter: (optional) limit selection using this expression
        :return: list of matching LandscapeDNDC txt files in indir
        :rtype: list
    """

    infiles = list(Path(inpath).glob(f"*{ldndc_file_type}"))
    infiles.extend(list(Path(inpath).glob(f"*{ldndc_file_type}.gz")))

    if limiter != "":
        infiles = [x for x in infiles if limiter in x.name]

    infiles.sort()

    if len(infiles) == 0:
        msg = "No LandscapeDNDC input files of type <%s>\n" % ldndc_file_type
        msg += "Input dir:    %s\n" % inpath
        if limiter != "":
            msg += "\nFilter used:  %s" % limiter
        log.critical(msg)
        exit(1)

    return infiles


def _construct_date_columns(df):
    df["datetime"] = df.datetime.astype("datetime64[ns]")
    if "year" not in df.columns:
        df["year"] = df.datetime.dt.year
    if "julianday" not in df.columns:
        df["julianday"] = df.datetime.dt.dayofyear
    return df


def _limit_df_years(years, df, yearcol="year"):
    """ limit data.frame to specified years """
    if (years[-1] - years[0] == len(years) - 1) and (len(years) > 1):
        df = df[(df.time.dt.year >= years[0]) & (df.time.dt.year <= years[-1])]
    else:
        df = df[df.time.dt.year.isin(years)]
    if len(df) == 0:
        if len(years) == 1:
            log.critical("Year %d not in data" % years[0])
        else:
            log.critical("Year range %d-%d not in data" % (years[0], years[-1]))
        exit(1)
    df = df.sort_values(by=basecols)
    return df


def read_ldndc_txt(inpath, varData, years, limiter=""):
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
        for var in varData[ldndc_file_type]:
            varnames.append(var.name)
            datacols.extend(var.sources)

        # iterate over all files of one ldndc file type
        for fcnt, fname in enumerate(infiles):
            fno = _extract_fileno(fname)
            basecols_extended = []

            # conditional open (either regular or gzip based on suffix)
            opener = gzip.open if str(fname).endswith(".gz") else open

            with opener(fname, "rt") as f:
                header = f.readline()
                if "datetime" in header:
                    basecols_extended.append("datetime")
                for b in basecols:
                    if b in header:
                        basecols_extended.append(b)

            df = pd.read_table(
                fname, error_bad_lines=False, usecols=basecols_extended + datacols
            )
            if "datetime" in df.columns:
                df["time"] = df.datetime.astype("datetime64[ns]")
                df = df.drop("datetime", axis=1)
            Dids.setdefault(fno, sorted(list(set(df["id"]))))

            df = _limit_df_years(years, df)
            df = df.sort_values(by=["id", "time"])
            dfs.append(df)

        # we don't have any dataframes, return
        # TODO: the control flow here should be more obvious
        if len(dfs) == 0:
            log.warn("No data.frame filetype %s!" % ldndc_file_type)
            continue

        df = pd.concat(dfs, axis=0)
        df = df.sort_values(by=["id", "time"])
        df = df.set_index(["id", "time"])

        cols_to_drop, cols_to_keep = [], []

        # sum columns if this was requested in the conf file
        for var in varData[ldndc_file_type]:
            df[var.name] = df[var.sources].sum(axis=1)
            if var.name not in cols_to_keep:
                cols_to_keep.append(var.name)
            else:
                raise ValueError(
                    "Variable requested multiple times. Check your conf file."
                )

            cols_to_drop.extend(var.sources)
            cols_to_drop.append(var.text)

        cols_to_drop = list(set(cols_to_drop).difference(set(cols_to_keep)))

        df = df.drop(cols_to_drop, axis=1)
        df_all.append(df)

    # check if all tables have the same number of rows
    if _all_items_identical([len(x) for x in df_all]):
        log.debug("All data.frames have the same length (n=%d)" % len(df_all[0]))
    else:
        log.debug(
            "Rows differ in data.frames: %s" % "".join([str(len(x)) for x in df_all])
        )

    df = pd.concat(df_all, axis=1).fillna(0.0)
    df = df.reset_index()

    return (varnames, df)


def main():
    # parse args
    args = cli()

    config = ConfigHandler(args.config)

    if args.storeconfig:
        config.write()

    # read or build refdata array
    def use_cli_refdata():
        return args.refinfo is not None

    if use_cli_refdata():
        reffile, refvar = args.refinfo
        reffile = Path(reffile)
        if reffile.is_file():
            with (xr.open_dataset(reffile)) as refnc:
                if refvar not in refnc.data_vars:
                    log.critical("Var <%s> not in %s" % (refvar, reffile))
                    exit(1)
                cell_ids = refnc[refvar].where(refnc[refvar] > 0)
                lats, lons = refnc.lat.values, refnc.lon.values
        else:
            log.critical("Specified reffile %s not found" % reffile)
            exit(1)
    else:
        log.error("You need to specify a reffile")
        exit(1)

    # read source output from ldndc
    log.debug(config.variables)
    varinfos, df = read_ldndc_txt(
        args.indir, config.section("variables"), args.years, limiter=args.limiter
    )

    id_mapper = create_id_mapper(cell_ids)
    df["lat"], df["lon"] = zip(*df.id.map(id_mapper))
    df = df.set_index(["time", "lat", "lon"])

    df = df.drop("id", axis=1)
    df.sort_index(inplace=True)

    # iterate over cellids and variables
    ENCODING = {
        "complevel": 5,
        "zlib": True,
        "chunksizes": (10, 20, 40),
        "shuffle": True,
    }

    def get_datavar_encodings(ds):
        ENCODINGS = {}
        for v in ds.data_vars:
            new_chunksizes = []
            for chk_data, chk_default in zip(ds[v].shape, ENCODING["chunksizes"]):
                if chk_data < chk_default:
                    new_chunksizes.append(chk_data)
                else:
                    new_chunksizes.append(chk_default)
            new_encoding = ENCODING.copy()
            new_encoding.update({"chunksizes": tuple(new_chunksizes)})

            ENCODINGS[v] = new_encoding
        return ENCODINGS

    ds_all = []
    for yr, yr_group in df.groupby(df.index.get_level_values("time").year):
        with xr.Dataset() as ds:
            ds = ds.from_dataframe(yr_group)

            # make sure we have a full year and full lat lon extent of data
            days = pd.date_range(start=f"1/1/{yr}", end=f"12/31/{yr}")
            ds = ds.reindex({"time": days, "lat": lats, "lon": lons})

            # TODO: fix NaN values in reindexed time steps (i.e. from yearly files)
            #       ideally they should be zero (but only the locations with actual sims)

            ENCODINGS = get_datavar_encodings(ds)
            for v in ds.data_vars:
                units = next(
                    (var.unit for var in config.variables if var.name == v), None
                )
                if units:
                    ds[v].attrs["units"] = units

            if args.split:
                outfilename = f"{args.outfile[:-3]}_{yr}.nc"
                ds.attrs = config.global_info
                ds.to_netcdf(
                    Path(args.outdir) / outfilename,
                    format="NETCDF4_CLASSIC",
                    encoding=ENCODINGS,
                )
            else:
                ds_all.append(ds)

    if not args.split:
        with xr.concat(ds_all, dim="time") as ds:
            ENCODINGS = get_datavar_encodings(ds)
            ds.attrs = config.global_info
            ds.to_netcdf(
                Path(args.outdir) / args.outfile,
                format="NETCDF4_CLASSIC",
                encoding=ENCODINGS,
            )
