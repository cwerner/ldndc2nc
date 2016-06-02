# -*- coding: utf-8 -*-
"""ldndc2nc.extra: extra module within the ldndc2nc package."""

import yaml, os
from dotmap import DotMap

from pkg_resources import Requirement, resource_filename

def _copy_default_config():
    fname = resource_filename(Requirement.parse("ldndc2nc"),"ldndc2nc.conf")
    print fname
    exit()

def get_config(cfgFile=None):
    """ locate and read config file """

    cfg = None
    locations = []

    def cfgfile_was_specified(cfgFile):
        return cfgFile != None

    if cfgfile_was_specified(cfgFile):
        if os.path.isfile(cfgFile):
            locations += [cfgFile]

    # disable os.curdir for the moment

    #locations += [os.curdir, os.path.expanduser("~"), "/etc/ldndc2nc",
    #              os.environ.get("LDNDC2NC_CONF")]

    locations += [os.path.expanduser("~"), "/etc/ldndc2nc",
                  os.environ.get("LDNDC2NC_CONF")]

    locations = [x for x in locations if x is not None]

    was_found = False

    for loc in locations:
        try:
            if 'ldndc2nc.conf' not in os.path.basename(loc):
                loc = os.path.join(loc, "ldndc2nc.conf")

            with open(loc, 'r') as ymlfile:
                cfg = yaml.load(ymlfile)
                cfg = DotMap(cfg)


            was_found = True
            cfg.variables = cfg.variables.toDict()

            for k, vs in cfg.variables.items():
                vs_new = []
                for v in vs:

                    def is_multipart_item(x):
                        return ';' in x

                    if is_multipart_item(v):
                        x = v.split(';')
                        vs_new.append((x[0], x[1:]))
                    else:
                        vs_new.append(v)

                    cfg.variables[k] = vs_new

        except IOError:
            pass


    if not was_found:
        _copy_default_config()

    return cfg


class Extra(object):
    pass
