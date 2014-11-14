#!/usr/bin/env python
"""Erode map

Erodes a classification map for identification of homogeneous landscape patches
according to a given window size. Can further reduce size of classes by
sampling each class.

Usage:
    erode_map.py [options] <input> <output>

Options:
    -w --window=<w>     Convolution window size (must be odd) [default: 3]
    -m --max=<max>...   Maximum number of pixels per class
    -n --ndv=<ndv>      Override output map NoDataValue
    -f --format=<f>     Output data format [default: GTiff]
    -v --debug          Show (verbose) debugging messages
    -h --help           Show help

Examples:

    > erode_map.py -w 5 -n 0 -f ENVI input.bsq output.bsq

Notes:

    Optional argument "--max" may specify the maximum number of pixels in each
    class in one of two ways:

        1. One single value used for all classes (e.g., "--max 5")
        2. One value per unmasked class with each value separated by spaces
            or commas (e.g., in 3 class map, "--max 5, 10 ,5)"

"""
from __future__ import print_function, division
import logging
import os
import sys

from docopt import docopt

try:
    from osgeo import gdal
    from osgeo.gdalconst import GA_ReadOnly
except ImportError:
    import gdal
    from gdalconst import GA_ReadOnly

import scipy.ndimage
import numpy as np

logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s',
                    level=logging.INFO,
                    datefmt='%H:%M:%S')
logger = logging.getLogger(__name__)


def process_map(in_name, out_name, out_driver, window, ndv, max_pix):
    """
    Opens map applies erosion filter and handles output of map
    """
    # Open source input image
    src_ds = gdal.Open(in_name, GA_ReadOnly)
    if src_ds is None:
        print('Error: could not open {0}'.format(in_name))
        sys.exit(1)

    # Read map into NumPy array
    source_map = src_ds.GetRasterBand(1).ReadAsArray()
    if not ndv:
        ndv = src_ds.GetRasterBand(1).GetNoDataValue()

    # Create initial mask and masked map
    mask = np.ma.masked_equal(source_map, ndv)
    masked_map = source_map * (source_map != ndv)

    # Find unique values (classes) from map
    classes = np.unique(mask.compressed())

    # Check that either:
    #   1. max_pix is None
    #   2. max_pix has 1 value for all classes
    #   3. max_pix has values for all classes
    if (max_pix is not None and
            len(max_pix) != 1 and
            len(max_pix) != len(classes)):
        print('Error: must specify maximum number of pixels for each class'
              'individually or specify one number for all classes')
        print('        {n} classes in map'.format(n=len(classes)))
        print('        {n} maximum pixel counts given'.format(n=len(max_pix)))
        print('        classes:')
        print(classes)
        sys.exit(1)

    # Setup output matrix for erosion
    map_erode = np.zeros_like(masked_map)

    for i, u in enumerate(classes):
        # Don't work on 0 since 0 is not classified
        if u == 0:
            continue

        # Do erosion
        eroded = scipy.ndimage.morphology.binary_erosion(masked_map == u)

        # Erode further, if required
        if max_pix is not None:
            # Find number specified for this class
            if len(max_pix) == 1:
                m = max_pix[0]
            else:
                m = max_pix[i]

            logger.debug('Sampling class {u} to {n} pixels'.format(u=u, n=m))

            # Find number of pixels
            n_pix = np.sum(eroded)

            # Iterate until smaller than specified
            if n_pix > m:
                logger.debug('   Sampling class {u}'.format(u=u))
                logger.debug('        {n} > {m}'.format(n=n_pix, m=m))

                # Sample
                ind = np.ravel_multi_index(np.where(eroded == 1), eroded.shape)

                ind = np.random.choice(ind, m, replace=False)

                eroded = np.zeros_like(eroded)
                eroded[np.unravel_index(ind, eroded.shape)] = 1

#                # Erode again
#                eroded = scipy.ndimage.morphology.binary_erosion(eroded)
                # Recalculate
                n_pix = np.sum(eroded)

            logger.debug('Finished sampling class {u} to size {n}'.format(
                u=u, n=n_pix))

        # Add in this class to full map
        map_erode = map_erode + eroded * u

    # Clean up memory
    del(eroded)

    # Add NDV back in
    unmasked_erode = ndv * (source_map == ndv) + map_erode

    dst_ds = out_driver.Create(out_name,
                               src_ds.RasterXSize, src_ds.RasterYSize,
                               1, src_ds.GetRasterBand(1).DataType)
    if dst_ds is None:
        print('Error: could not write to {0}'.format(out_name))
        sys.exit(1)

    # Write data
    dst_ds.GetRasterBand(1).SetNoDataValue(ndv)
    dst_ds.GetRasterBand(1).WriteArray(unmasked_erode)

    # Write projection/etc
    dst_ds.SetProjection(src_ds.GetProjection())
    dst_ds.SetGeoTransform(src_ds.GetGeoTransform())

    # Close files
    src_ds = None
    dst_ds = None


def main():
    gdal.UseExceptions()
    gdal.AllRegister()
    ### Parse arguments
    window = arguments['--window']
    try:
        window = int(window)
    except ValueError:
        print('Error: input window must be an integer')
        sys.exit(1)
    else:
        if window % 2 == 0:
            print('Error: window size must be an odd integer')
            sys.exit(1)

    # Maximum number of pixels per class
    max_pix = arguments['--max']
    if max_pix:
        try:
            max_pix = [int(m) for m in max_pix.replace(' ', ',').split(',')
                       if m != '']
        except:
            print('Error: could not convert maximum pixel input to array of'
                  'integers')
            sys.exit(1)

    # Input image
    in_name = arguments['<input>']
    if os.path.dirname(in_name) == '':
        in_name = './' + in_name
    if not os.path.exists(in_name):
        print('Could not find input image {0}'.format(in_name))
        sys.exit(1)
    elif not os.access(in_name, os.R_OK):
        print('Cannot read input image {0}'.format(in_name))
        sys.exit(1)

    # Output image
    out_name = arguments['<output>']
    if os.path.dirname(out_name) == '':
        out_name = './' + out_name
    if os.path.exists(out_name):
        if not os.access(out_name, os.W_OK):
            print('Error: output image exists and cannot overwrite')
            sys.exit(1)
    else:
        if not os.access(os.path.dirname(out_name), os.W_OK):
            print('Cannot write to output image {0}'.format(out_name))
            sys.exit(1)

    # Output image driver
    format = arguments['--format']
    out_driver = gdal.GetDriverByName(format)
    if out_driver is None:
        print('Error: could not create driver for format {f}'.format(f=format))
        sys.exit(1)

    # NoData value
    ndv = arguments['--ndv']
    if ndv:
        try:
            ndv = int(ndv)
        except ValueError:
            print('Error: Nodata value must be an integer')
            sys.exit(1)

    ## perform file handling and send to erosion function
    process_map(in_name, out_name, out_driver, window, ndv, max_pix)


if __name__ == '__main__':
    arguments = docopt(__doc__)
    if arguments['--debug']:
        logger.setLevel(logging.DEBUG)

    main()
