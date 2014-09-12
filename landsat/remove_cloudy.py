#!/usr/bin/env python
""" Remove Cloud Images

Usage:
    remove_cloudy.py [options] <min_clear> <directory>

Options:
    --fmask=<pattern>       Fmask pattern [default: *Fmask]
    --band=<band>           Fmask band in image [default: 1]
    --clear=<clear values>  Acceptable Fmask values [default: 0, 1]
    --store=<directory>     Directory to store cloudy images [default: cloudy]
    --dry-run               Dry-run (do not move files)
    -v --verbose            Show verbose messages
    --help                  Show help

"""
from docopt import docopt

import fnmatch
import os
import shutil
import sys

from osgeo import gdal
import numpy as np

DEBUG = False
DRY = False

ndv = 255

def remove_cloudy(min_clear, directory, fmask, band, clear, storage):
    """ Find all mask images, check the clear percent of pixels in each, and 
    move or retain accordingly
    """
    images = []
    # Search folder for Fmask images
    for root, dirs, files in os.walk(directory):

        for f in fnmatch.filter(files, fmask):
            f = os.path.join(root, f)
            
            if os.path.dirname(f) in [os.path.dirname(_d) for _d in images]:
                print 'Error: multiple Fmask images in folder {f}'.format(
                    f=os.path.dirname(f))
                sys.exit(1)
            
            images.append(f)

    print 'Found {n} Fmask images'.format(n=len(images))

    # Loop through images, checking
    count = len(images)
    for _i, img in enumerate(images):
        dir = os.path.dirname(img)

        if DEBUG is True:
            print 'Working on: ' + dir + ' ({i}/{t})'.format(i=_i, t=count)

        # Open dataset
        try:
            ds = gdal.Open(img, gdal.GA_ReadOnly)
        except:
            print 'Error: could not open {f}'.format(f=img)
            sys.exit(1)

        # Read in mask image
        mask = ds.GetRasterBand(band).ReadAsArray()

        if mask is None:
            print 'Error: cannot read in Fmask band'
        
        # Determine number of observed pixels
        nobs = (mask != ndv).sum()
        # Determine number of good pixels
        nclear = reduce(np.logical_or, [mask == c for c in clear]).sum()
        # Determine percent clear
        pct_clear = float(nclear) / float(nobs) * 100

        if pct_clear < min_clear:
            # Warn
            print 'Image {i} does not meet minimum ({f:0.1f}%)'.format(
                i=img, f=pct_clear)
            # Destroy dataset
            ds = None
            # Move folder
            if DRY is False:
                try:
                    shutil.move(dir, 
                                os.path.join(storage, os.path.basename(dir)))
                except:
                    print 'Error: could not move folder into storage'
                    sys.exit(1)

        ds = None
    
    print 'Filtered all cloudy images'

def main():
    gdal.UseExceptions()
    # Minimum clear percent of pixels
    min_clear = args['<min_clear>']
    try:
        min_clear = float(min_clear)
    except:
        print 'Error: minimum clear must be a real number'

        sys.exit(1)

    # Directoy of images
    directory = args['<directory>']
    if not os.path.exists(directory):
        print 'Error: input directory does not exist'
        sys.exit(1)

    # Fmask pattern
    fmask = args['--fmask']
    if '*' not in fmask:
        print 'Warning: pre-appending wildcard since none in Fmask pattern'
        fmask = '*' + fmask

    band = args['--band']
    try:
        band = int(band)
    except:
        print 'Error: band specified is not an integer'
        sys.exit(1)

    # Clear values
    clear = args['--clear']
    clear = clear.replace(' ', ',').split(',')
    try:
        clear = [int(c) for c in clear if c != '']
    except:
        print 'Error: Fmask clear values must be integers'
        sys.exit(1)

    # Make storage directory for cloudy images
    storage = args['--store'] 
    if not os.path.exists(storage):
        try:
            os.mkdir(storage)
        except:
            print 'Error: cannot make storage directory {d}'.format(d=storage)
            sys.exit(1)

    remove_cloudy(min_clear, directory, fmask, band, clear, storage)


if __name__ == '__main__':
    args = docopt(__doc__)
    if args['--verbose']:
        DEBUG = True
    if args['--dry-run']:
        DRY = True
    main()
