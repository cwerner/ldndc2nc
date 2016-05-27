# -*- coding: utf-8 -*-
#
# ldndc2nc.py
# ==================
#
# Christian Werner 
# christian.werner@senckenberg.de

"""ldndc2nc.ldndc2nc: provides entry point main()."""
  
__version__ = "0.0.1"


import sys
from .extra import Extra, getConfig


def main():
    print("Executing ldndc2nc version %s." % __version__)
    print("List of argument strings: %s" % sys.argv[1:])
 
    cfg = getConfig()
    if cfg == None:
        print 'No ldndc2nc.conf file found in the required places... exit'
        exit(1)
    
    # cfg is a dotmap
    print "Using the following ldndc2nc.conf information"
    cfg.pprint()


class Boo( Extra ):
    pass


