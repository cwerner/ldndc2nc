# -*- coding: utf-8 -*-
 
 
"""ldndc2nc.extra: extra module within the ldndc2nc package."""
 

import yaml, os
from dotmap import DotMap

def getConfig():
    cfg = None
    for loc in os.curdir, os.path.expanduser("~"), "/etc/ldndc2nc", os.environ.get("LDNDC2NC_CONF"):
        try:
            if 'ldndc2nc.conf' in os.path.basename(loc):
                pass
            else:
                loc = os.path.join( loc, "ldndc2nc.conf" )

            print loc

            with open( loc, 'r') as ymlfile:
                cfg = yaml.load(ymlfile)
        except IOError:
            pass

    return DotMap(cfg)

class Extra( object ):
    pass
