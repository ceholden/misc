#!/usr/bin/env python
""" Checks CCDC results for errors in the MATLAB files

Usage:
    check_results.py [options] <location>

Options:
    --pattern <pattern>     Result file pattern [default: record_*.mat]
    -v --verbose            Show check for all files
    -h --help               Show help

"""
from __future__ import print_function

import fnmatch
import logging
import os
import sys

from docopt import docopt
import scipy.io as spio

logging.basicConfig(format='%(asctime)s %(module)s %(levelname)s: %(message)s',
                    level=logging.INFO,
                    datefmt='%H:%M:%S')
logger = logging.getLogger(__name__)

def check_results(location, pattern='record_*.mat'):
    """ Check results matching pattern within location for errors
    
    Args:
      location (str): directory location of the results
      pattern (str, optional): file pattern to check

    """
    results = fnmatch.filter(os.listdir(location), pattern)
    if not results:
        logger.error('Found 0 results')
        sys.exit(1)
    results.sort()

    errors = 0
    for r in results:
        r = os.path.join(location, r)
        try:
            mat = spio.loadmat(r)
        except:
            logger.error('Could not open {r}'.format(r=r))
            errors += 1
        else:
            logger.debug('Opened {r}'.format(r=r))

    logger.info('Completed')
    logger.info('    {e} of {n} failed to open'.format(
            e=errors, n=len(results)))

if __name__ == '__main__':
    args = docopt(__doc__)

    if args['--verbose']:
        logger.setLevel(logging.DEBUG)
    
    location = args['<location>']
    if not os.path.isdir(location):
        logger.error('{d} is not a directory'.format(d=location))
        sys.exit(1)

    pattern = args['--pattern']
    if '*' not in pattern:
        pattern += '*'

    logger.debug('Searching in {d} for files matching {p}'.format(
            d=location, p=pattern))
    check_results(location, pattern=pattern)
