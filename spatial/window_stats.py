#!/usr/bin/env python
# /*****************************************************************************
# * Name:       window_stats.py
# * Author:     Chris Holden (ceholden@bu.edu)
# * Version:    1.0
# * Purpose:    To read an image using GDAL and calculate moving window 
# *             statistics
# * Methods:    Use GDAL (gdal.org) to read the image and import as numpy array.
# *             Next, use scipy's ndimage functions to calculate statistic and 
# *             output result as single band image.
# *
# *****************************************************************************\

import sys
import os
import argparse
from argparse import RawTextHelpFormatter

import numpy
import scipy.ndimage

try:
    from osgeo import gdal
    from osgeo.gdalnumeric import *
except ImportError:
    import gdal
    from gdalnumeric import *


def do_it(args):

    ### Set up
    window = args.window    
    # Setup window sizes
    maskX = (window - 1) / 2
    maskX = range(-1 * maskX, maskX + 1)
    maskY = (window - 1) / 2
    maskY = range(-1 * maskY, maskY + 1)
    
    # Register all drivers
    gdal.AllRegister()
    
    # Open input file
    try:
        inDs = gdal.Open(args.input, gdal.GA_ReadOnly)
    except:
        inDs is None
    if inDs is None:
        print 'Error: Could not open ' + args.input
        sys.exit(1)

    cols = inDs.RasterXSize
    rows = inDs.RasterYSize
    bands = inDs.RasterCount
    
    xBlockSize = inDs.GetRasterBand(1).GetBlockSize()[0]
    yBlockSize = inDs.GetRasterBand(1).GetBlockSize()[1]
    
    nXBlocks = (int)((cols + xBlockSize - 1) / (xBlockSize))
    nXBlocks = (int)((rows + yBlockSize - 1) / (yBlockSize))
    
    # Initialize output dataset
    driver = gdal.GetDriverByName(args.format)
    outDs = driver.Create(args.output, cols, rows, bands, gdal.GDT_Float32)
    if outDs is None:
        print 'Could not write to ' + args.output
        sys.exit(1)
    
    # Read in data
    inData = zeros([rows, cols])
    for b in range(bands):
        inBand = inDs.GetRasterBand(b + 1)
        NoData = inBand.GetNoDataValue()
        
        if NoData is None:
            NoData = -9999
        inData[:,:] = inBand.ReadAsArray(0, 0, cols, rows).astype(float)
        
        # Process statistic
        if args.stat == 'mean':
            outData = moving_mean(inData, window)
        elif args.stat == 'var':
            outData = moving_var(inData, window)
        elif args.stat == 'contrast':
            outData = moving_contrast(inData, window)
        elif args.stat == 'sobel':
            outData = sobel_mean(inData, window)

        # Write out data
        outBand = outDs.GetRasterBand(b+1)
        outBand.SetNoDataValue(NoData)
        outBand.WriteArray(outData, 0, 0)
        outBand.FlushCache()
        
    outDs.SetGeoTransform(inDs.GetGeoTransform())
    outDs.SetProjection(inDs.GetProjection())
    
    inDs = None
    outDs = None
    
    print 'Results written to ' + args.output


def moving_mean(Ic, window):
    # Init output image
    Im = empty(Ic.shape, dtype='Float32')
    # Uniform filter -> mean
    scipy.ndimage.filters.uniform_filter(Ic, window, output=Im)
    
    return Im


def moving_var(Ic, window):
    # Init output image
    Im = numpy.empty(Ic.shape, dtype='Float32')
    scipy.ndimage.filters.uniform_filter(Ic, window, output=Im)
    # Subtracting mean
    Im *= -1 
    Im += Ic
    # Squaring difference
    Im **= 2
    # Summing and dividing differences by pix in window
    scipy.ndimage.filters.uniform_filter(Im, window, output=Im)
    return Im


def moving_contrast(Ic, window):
    # Init output image
    Im = empty(Ic.shape, dtype='Float32')
    # Set up contrast kernel
    center = window * window - 1
    k = ones([window, window]) * -1
    k[(window - 1) / 2, (window - 1) / 2] = center
    # Filter the image
    Im = scipy.ndimage.convolve(Ic, k, mode='reflect')

    return Im


def sobel_mean(Ic, window):
    """
    Returns mean filtered sobel gradient magnitude of input image
    """
    # Get directional components
    dx = scipy.ndimage.sobel(Ic, 0)
    dy = scipy.ndimage.sobel(Ic, 1)
    # Get magnitude
    mag = numpy.hypot(dx, dy)
    # Clear memory
    del dx
    del dy
    # Normalize
    mag *= 255.0 / numpy.max(mag)
    ### TODO: re-impliment or delete Gaussian filter part
    # apply Gaussian filter
    # scipy.ndimage.filters.gaussian_filter(mag, sigma, output=Ic)
    ### Using mean filter instead of gaussian
    Ic = moving_mean(mag, window)

    return Ic


# Main program
def main():
    desc = "Calculate a given statistic for a moving window"
    example = """
    Example\n 
    For a 3x3 window image mean:
    window_stats.py -w 3 -s mean input.tif output.tif\n
    For a 5x5 window image variance:
    window_stats.py -w 5 -s var input.tif output.tif
    """
    parser = argparse.ArgumentParser(prog='window_stats.py', 
        description=desc, 
        epilog=example,
        formatter_class=RawTextHelpFormatter)

    parser.add_argument('-w', action='store', dest='window', type=int,
        help='size of moving window', 
        default=3)
    parser.add_argument('-s', action='store', dest='stat', type=str,
        help='statistic to calculate (mean, var, contrast, sobel)',
        default='mean')
    
    parser.add_argument('--f', dest='format', default='GTiff',
        help='GDAL format for output file (default "GTiff")')

    parser.add_argument('input', action='store', type=str, 
        help='input raster file')
    parser.add_argument('output', action='store', type=str, 
        help='output raster file')

    args = parser.parse_args()

    possible = ['mean', 'var', 'contrast', 'sobel']
    if (args.stat in possible) is False:
        print 'Error: statistic incorrect or not available.'
        print parser.print_help()
        sys.exit(1)
    # Check if window is odd number (for non-sobel)
    elif (args.window % 2 == 0 and args.stat != 'sobel') is True:
        print 'Error: window size must be odd integer value'
        print parser.print_help()
        sys.exit(1)
    else:
        do_it(args)

    sys.exit(0)
    
if __name__ == '__main__':
    main()
