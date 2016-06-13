import logging
from logging.handlers import RotatingFileHandler
import sys

try:    # python 2.7+
    from logging import NullHandler
except ImportError:
    class NullHandler(logging.Handler):
        def emit(self, record):
            pass

logging.getLogger(__name__).addHandler(NullHandler())

logPath='.'
fileName='ldndc2nc'

FORMAT = "%(asctime)s [%(levelname)-8s] %(message)s"
DEBUG_FORMAT = FORMAT + " (%(filename)s:%(lineno)s)"

class MultiLineFormatter(logging.Formatter):
    """ A custom multi-line logging formatter """
    def format(self, record):
        str = logging.Formatter.format(self, record)
        header, footer = str.split(record.message)
        str = str.replace('\n', '\n' + ' '*len(header))
        return str

logFormatter = MultiLineFormatter(FORMAT, datefmt='%Y-%m-%d %H:%M:%S')
logFormatterDebug = MultiLineFormatter(DEBUG_FORMAT, datefmt='%Y-%m-%d %H:%M:%S')

rootLogger = logging.getLogger()
rootLogger.setLevel(logging.DEBUG)

consoleHandler = logging.StreamHandler()
consoleHandler.setFormatter(logFormatter)
consoleHandler.setLevel(logging.INFO)
rootLogger.addHandler(consoleHandler)

fileHandler = RotatingFileHandler("{0}/{1}.log".format(logPath, fileName), maxBytes=10000)
fileHandler.setFormatter(logFormatterDebug)
fileHandler.setLevel(logging.DEBUG)
rootLogger.addHandler(fileHandler)


