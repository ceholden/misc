#!/usr/bin/env python
# -*- coding: utf-8 -*
# vim: set expandtab:ts=4
""" Mosaic Maps by Number of Observations

Usage:
    mosaic_map_nobs.py [options] <map_mosaic> <nobs_mosaic> <output_map>

Options:
    --of=<format>                   Output format [default: GTiff]
    --masks=<filename>              Save the mask image?
    -v --debug                      Show (verbose) debugging messages
    -q --quiet                      Do not show messages
    -h --help                       Show help
"""
from docopt import docopt

import os
import sys

try:
    from osgeo import gdal
except:
    import gdal

import numpy as np

# Make stdout unbuffered
sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)

QUIET = False
DEBUG = False

def create_map(map_mosaic, nobs_mosaic, output, mask_fn, out_format):
    """
    Creates one map using the land cover estimated from the most number of
    observations
    """
    # Read in data
    map_ds = gdal.Open(map_mosaic, gdal.GA_ReadOnly)
    if DEBUG:
        print 'Opened input file {f}'.format(f=map_mosaic)
    nobs_ds = gdal.Open(nobs_mosaic, gdal.GA_ReadOnly)
    if DEBUG:
        print 'Opened #Obs file {f}'.format(f=nobs_mosaic)

    # Fetch NoDataValue
    ndv = map_ds.GetRasterBand(1).GetNoDataValue()

    # Check number of bands
    bands = map_ds.RasterCount
    if bands != nobs_ds.RasterCount:
        print 'Error: map and #Obs files differ in band number'
        sys.exit(1)
    if DEBUG:
        print 'Input image has {n} map bands'.format(n=bands)

    # Read in number of observations into list of np.array
    nobs = []
    for i in xrange(bands):
        nobs.append(nobs_ds.GetRasterBand(i + 1).ReadAsArray())
        if nobs[i] is None:
            print 'Error: could not read band {b} from image'.format(b=i + 1)
            sys.exit(1)
    if DEBUG:
        print 'Read in the number of observations bands'
        
    # Setup and generate masks
    masks = []
    if DEBUG:
        print 'Starting the masking...'
    for i in xrange(bands):
        if i == 0:
            # Don't worry about pixels already being filled
            masks.append(reduce(np.logical_and, 
                            [np.greater_equal(nobs[i], n) 
                            for n in nobs if n is not nobs[i]]))
        else:
            # Also need to check to make sure hasn't been filled
            masks.append(reduce(np.logical_and,
                            [np.logical_and(
                                np.greater_equal(nobs[i], b), m == False) 
                                for b in nobs if b is not nobs[i] 
                                for m in masks
                            ]
                        )
                    )
            masks[i] = masks[i] * masks[i] != ndv
        if DEBUG:
            print 'Masked image {i} of {t}'.format(i=(i + 1), t=bands)

    if mask_fn is not None:
        mask_driver = gdal.GetDriverByName(out_format)
        mask_ds = mask_driver.Create(mask_fn, map_ds.RasterXSize, 
                                     map_ds.RasterYSize, 1)
        if mask_ds is None:
            print 'Error: could not write output mask {f}'.format(f=mask_fn)
            sys.exit(1)
        if DEBUG:
            print 'Writing out mask rule image'
        
        # Condense mask
        mask = np.zeros_like(masks[0])
        for i, m in enumerate(masks):
            mask = mask + m * (i + 1)
        
        # Write to disk
        mask_ds.GetRasterBand(1).WriteArray(mask)
        mask_ds.SetProjection(map_ds.GetProjection())
        mask_ds.SetGeoTransform(map_ds.GetGeoTransform())

        del(mask)
        mask_ds = None

    # Clear memory by removing nobs
    del(nobs)
    nobs_ds = None

    # Read in land cover maps
    maps = []
    for i in xrange(bands):
        maps.append(map_ds.GetRasterBand(i + 1).ReadAsArray())
        if maps[i] is None:
            print 'Could not read in band {b} from image'.format(b=(i + 1))
            sys.exit(1)
    if DEBUG:
        print 'Read in the maps'

    # Create composite land cover map
    lc_map = np.zeros_like(maps[0])
    for i in xrange(bands):
        lc_map = lc_map + masks[i] * maps[i]

    # Write out
    out_driver = gdal.GetDriverByName(out_format)
    out_ds = out_driver.Create(output, map_ds.RasterXSize, map_ds.RasterYSize, 
                               1, map_ds.GetRasterBand(1).DataType)
    if out_ds is None:
        print 'Error: could not create output file {f}'.format(f=output)
        sys.exit(1)
    out_ds.GetRasterBand(1).WriteArray(lc_map)
    out_ds.SetProjection(map_ds.GetProjection())
    out_ds.SetGeoTransform(map_ds.GetGeoTransform())

    # Close
    map_ds = None
    out_ds = None

    if not QUIET:
        print 'Wrote output map mosaic to {f}'.format(f=output)

def main():
    # Input filename
    map_mosaic = arguments['<map_mosaic>']
    if not os.path.exists(map_mosaic):
        print 'Could not find map_mosaic image {0}'.format(map_mosaic)
        sys.exit(1)
    elif not os.access(map_mosaic, os.R_OK):
        print 'Cannot read map_mosaic image {0}'.format(map_mosaic)
        sys.exit(1)

    nobs_mosaic = arguments['<nobs_mosaic>']
    if not os.path.exists(nobs_mosaic):
        print 'Could not find nobs_mosaic image {0}'.format(nobs_mosaic)
        sys.exit(1)
    elif not os.access(nobs_mosaic, os.R_OK):
        print 'Cannot read nobs_mosaic image {0}'.format(nobs_mosaic)
        sys.exit(1)

    # Output image
    output = arguments['<output_map>']
    if os.path.dirname(output) == '':
        output = './' + output
    if not os.access(os.path.dirname(output), os.W_OK):
        print 'Cannot write to output location'
        sys.exit(1)
    # Mask image
    mask_fn = arguments['--masks']
    if mask_fn is not None:
        if os.path.dirname(mask_fn) == '':
            mask_fn = './' + mask_fn
        if not os.access(os.path.dirname(mask_fn), os.W_OK):
            print 'Cannot write to mask output location'
            sys.exit(1)
    # Format
    out_format = arguments['--of']
    test_driver = gdal.GetDriverByName(out_format)
    if test_driver is None:
        print 'Error: invalid file format - {0}'.format(out_format)
        sys.exit(1)

    create_map(map_mosaic, nobs_mosaic, output, mask_fn, out_format)

if __name__ == '__main__':
    arguments = docopt(__doc__)
    if arguments['--debug']:
        DEBUG = True
    main()
