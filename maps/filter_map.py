#!/usr/bin/env python
# -*- coding: utf-8 -*
# vim: set expandtab:ts=4
"""Filter map

Filters a change map for high-frequency "noisy" changes using moving window.
Retains change pixel if neighborhood contains at least [threshold] number of
changes.

Usage:
    filter_map.py [options] ( --erode | --dilate ) <input> <output>

Options:
    -w --window=<w>         Convolution window size (must be odd) [default: 3]
    -t --threshold=<t>      Threshold changes within window (default: 3)
    -n --ndv <ndv>          No data value [default: 0]
    -f --format=<format>    Output data format [default: GTiff]
    -v --debug              Show (verbose) debugging messages
    -h --help               Show help

Examples:
    filter_map.py -w 5 -t 4 --erode input.gtif output.gtif
"""
from docopt import docopt

try:
    from osgeo import gdal
    from osgeo.gdalconst import GA_ReadOnly
except ImportError:
    import gdal
    from gdalconst import GA_ReadOnly

import os
import sys

import numpy as np
import scipy.ndimage

DEBUG = False

def filter_map(in_name, out_name, out_driver, 
               choice, threshold, window, ndv):
    """
    Opens map, applies filter of choice, and handles the output of map
    """
    # Read in input data
    src_ds = gdal.Open(in_name, GA_ReadOnly)
    if src_ds is None:
        print 'Error: could not open {0}'.format(in_name)
        sys.exit(1)
    image = src_ds.GetRasterBand(1).ReadAsArray()
    
    if choice == 'erode':
        out_image = erode_map(image, threshold, window, ndv)
    elif choice == 'dilate':
        out_image = dilate_map(image, threshold, window, ndv)
   
    # Write mask to disk
    dst_ds = out_driver.Create(out_name,
                           src_ds.RasterXSize, src_ds.RasterYSize, 1,
                           gdal.GDT_Byte)
    if dst_ds is None:
        print 'Error: could not write to {0}'.format(out_name)

    dst_ds.SetProjection(src_ds.GetProjection())
    dst_ds.SetGeoTransform(src_ds.GetGeoTransform())
    
    dst_ds.GetRasterBand(1).SetNoDataValue(ndv)

    dst_ds.GetRasterBand(1).WriteArray(out_image)

    # Close
    src_ds = None
    dst_ds = None

def erode_map(image, threshold=3, window=3, ndv=0):
    """
    Applies a filter for high-frequency change "noise". Removes change if the
    number of changes within the window size is not greater than or equal to
    the threshold
    """
    # Setup convolution
    kernel = np.ones(window ** 2).reshape(window, window).astype(np.byte)
    # Get binary mask
    mask = (image != ndv).astype(np.byte)
    # Filter binary mask
    mask_f = scipy.ndimage.filters.convolve(mask, kernel)
    mask = ((mask_f >= threshold) & (mask == 1)).astype(np.byte)

    # Return applied  mask
    return image * mask

def dilate_map(image, threshold=3, window=3, ndv=0):
    """
    Dilates changes only when number of neighboring changes is above threshold.
    Preserves non-dilated changes.
    """
    # Setup convolution for threshold
    kernel = np.ones(window ** 2).reshape(window, window).astype(np.byte)
    # Get binary mask
    mask = (image != ndv).astype(np.byte)
    # Apply filter for dilation mask - note this also gap fills a bit
    mask_d = scipy.ndimage.filters.convolve(mask, kernel)
    mask_d = (mask_d > threshold).astype(np.byte)
    # Now dilate
    dilate = scipy.ndimage.morphology.grey_dilation(image * mask_d, 
                size=(window, window))
    # Retain original features before diliting
    mask_b = ((dilate != ndv) & (image != ndv)).astype(np.byte)
    dilate = (mask_b == 0) * dilate + image * mask_b
    # Now gather dilated & non-dilated for output
    return (mask_d == 0) * image + (mask_d == 1) * dilate

def main():
    ### Handle input arguments and options
    # Threshold
    threshold = arguments['--threshold']
    try:
        threshold = int(threshold)
    except ValueError:
        print 'Error: input threshold must be an integer'
        sys.exit(1)
    # Input image
    in_name = arguments['<input>']
    if os.path.dirname(in_name) == '':
        in_name = './' + in_name
    if not os.path.exists(in_name):
        print 'Could not find input image {0}'.format(in_name)
        sys.exit(1)
    elif not os.access(in_name, os.R_OK):
        print 'Cannot read input image {0}'.format(in_name)
        sys.exit(1)
    # Output image
    out_name = arguments['<output>']
    if os.path.dirname(out_name) == '':
        out_name = './' + out_name
    if not os.access(os.path.dirname(out_name), os.W_OK):
        print 'Cannot write to output image {0}'.format(out_name)
        sys.exit(1)
    # Window size
    window = arguments['--window']
    try:
        window = int(window)
    except ValueError:
        print 'Error: window size must be an integer'
        sys.exit(1)
    else:
        if window % 2 == 0:
            print 'Error: window size must be an odd integer'
            sys.exit(1)
    # Output file format
    format = arguments['--format']
    out_driver = gdal.GetDriverByName(format)
    if out_driver is None:
        print 'Error: could not create driver for format {f}'.format(f=format)
        sys.exit(1)
    # No data value
    ndv = arguments['--ndv']
    try:
        ndv = int(ndv)
    except ValueError:
        print 'Error: NoDataValue must be an integer'
        sys.exit(1)

    # Register drivers
    gdal.AllRegister()
    # Filter map
    choice = 'erode' if arguments['--erode'] else 'dilate'
    filter_map(in_name, out_name, out_driver, choice, threshold, window, ndv)

if __name__ == '__main__':
    arguments = docopt(__doc__)
    if arguments['--debug']:
        DEBUG = True
    if DEBUG:
        print 'User inputs:'
        for k, v in arguments.iteritems():
            print '{k} : {v}'.format(k=k, v=v)
    main()
