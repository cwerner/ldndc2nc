# -*- coding: utf-8 -*-
 
 
"""ldndc2nc.extra: extra module within the ldndc2nc package."""
 

import yaml, os
from dotmap import DotMap

def getConfig( cfgFile=None):

    cfg = None
    
    locations = []

    if cfgFile != None:
        if os.path.isfile(cfgFile):
            locations += [cfgFile]

    locations += [os.curdir, os.path.expanduser("~"), "/etc/ldndc2nc", os.environ.get("LDNDC2NC_CONF")]

    for loc in locations:
        try:
            if 'ldndc2nc.conf' in os.path.basename(loc):
                pass
            else:
                loc = os.path.join( loc, "ldndc2nc.conf" )

            if cfgFile == loc:
                loc = cfgFile

            with open( loc, 'r') as ymlfile:
                cfg = yaml.load(ymlfile)
                cfg = DotMap( cfg )

            # processing of variables section
            # convert variables section to regular dict 

            cfg.variables = cfg.variables.toDict()

            for k, vs in cfg.variables.items():
                vs_new = []
                for v in vs:
                    # if we have ';' in yaml line this means we want to
                    # create a new column based on multiple original ones
                    if ';' in v:
                        # create tuple from chained items: (newDataItem, [origItem1, origItem2, ...]
                        x = v.split(';')
                        vs_new.append( (x[0], x[1:]) )
                    else:
                        vs_new.append( v )
                    cfg.variables[k] = vs_new

        except IOError:
            pass

    return cfg

class Extra( object ):
    pass
