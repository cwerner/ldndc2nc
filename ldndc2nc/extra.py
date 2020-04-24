# -*- coding: utf-8 -*-
"""ldndc2nc.extra: extra module within the ldndc2nc package."""

import logging
import os
from pathlib import Path
from pkg_resources import Requirement, resource_filename
import shutil
import string

import numpy as np
import param
import yaml
import xarray as xr

log = logging.getLogger(__name__)


def enum(*sequential, **named):
    enums = dict(zip(sequential, range(len(sequential))), **named)
    return type('Enum', (), enums)


def _copy_default_config():
    """ copy default conf file to user dir """

    #TODO somewhat redundand, merge with set_config code

    fname = resource_filename(
        Requirement.parse("ldndc2nc"), "ldndc2nc/data/ldndc2nc.conf")
    shutil.copyfile(fname, Path.home() / "ldndc2nc.conf")


def _find_config():
    """ look for cfgFile in the default locations """
    cfgFile = None
    locations = [Path('.'), Path.home(), Path("/etc/ldndc2nc"),
                 os.environ.get("LDNDC2NC_CONF")]
    locations = [x for x in locations if x is not None]

    for loc in locations:
        f = loc / "ldndc2nc.conf"
        if f.is_file(f):
            cfgFile = str(f)
            break

    return cfgFile


def _parse_config(cfgFile):
    """ read yaml config file and modify special properties"""

    with open(cfgFile, 'r') as ymlfile:
        cfg = yaml.load(ymlfile, Loader=yaml.FullLoader)

    for k, vs in cfg['variables'].items():
        vs_new = []
        for v in vs:

            def is_multipart_item(x):
                return ';' in x

            if is_multipart_item(v):
                x = v.split(';')
                vs_new.append((x[0], x[1:]))
            else:
                vs_new.append(v)

            cfg['variables'][k] = vs_new

    return cfg


def parse_config(cfg, section=None):
    """ parse config data structure, return data of required section """

    def is_valid_section(s):
        valid_sections = ['info', 'project', 'variables', 'refdata']
        return s in valid_sections

    cfg_data = None
    if is_valid_section(section):
        try:
            cfg_data = cfg[section]
        except KeyError:
            log.critical(cfg.keys())
            log.critical("Section <%s> not found in config" % section)
            exit(1)
    else:
        log.critical("Section <%s> not a valid name" % section)
        exit(1)
    return cfg_data


def get_config(cfgFile=None):
    """ locate and read config file """

    cfg = None
    locations = []

    def cfgfile_exists(cfgFile):
        return cfgFile != None

    if cfgfile_exists(cfgFile):
        if not os.path.isfile(cfgFile):
            log.critical("Specified configuration file not found.")
            exit(1)
    else:
        cfgFile = _find_config()

        if not cfgfile_exists(cfgFile):
            log.info("Copying config file")
            _copy_default_config()
            cfgFile = _find_config()

    cfg = _parse_config(cfgFile)

    return cfg


def set_config(cfg):
    """ write cfg file to user dir """
    fname = os.path.join(os.path.expanduser("~"), 'ldndc2nc.conf')
    with open(fname, 'w') as f:
        f.write(yaml.dump(cfg, default_flow_style=False))

