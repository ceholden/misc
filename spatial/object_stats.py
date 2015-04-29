#!/usr/bin/env python
# /*****************************************************************************
# * Name:       object_stats.py
# * Author:     Chris Holden (ceholden@bu.edu)
# * Version:    1.0
# * Purpose:    To read an image and segmentation image using GDAL and to 
# *             calculate statistics for each segment using the image.  
# * Methods:    Use GDAL (gdal.org) to read the images and import into numpy
# *             arrays. Next, use find_objects to get i, j coordinates in image
# *             of pixels in i=1:n segments. Finally, use ndimage library
# *             to calculate statistic for given segment.
# *
# *****************************************************************************\
import sys
import os
import argparse

import numpy
from scipy import ndimage

try:
    from osgeo import gdal
    from osgeo.gdalnumeric import *
except ImportError:
    import gdal
    from gdalnumeric import *

def objstats(args):
    # Register all drivers
    gdal.AllRegister()

    # Open up images as datasets
    try:
        imgDs = gdal.Open(args.image, gdal.GA_ReadOnly)
    except:
        imgDs is None
    if imgDs is None:
        print 'Error: Could not open ' + args.image
        sys.exit(1)
        
    try:
        segDs = gdal.Open(args.segment, gdal.GA_ReadOnly)
    except:
        segDs is None
    if segDs is None:
        print 'Error: Could not open ' + args.segment
        sys.exit(1)
    
    # Get dimensions
    cols = imgDs.RasterXSize
    rows=imgDs.RasterYSize
    bands=imgDs.RasterCount

    # Init img as numpy matrix
    img=zeros([rows, cols])

    # Init seg as numpy matrix
    seg=zeros([rows, cols])
    # Get segment band from dataset and read in as numpy matrix
    segBand = segDs.GetRasterBand(1)
    seg = segBand.ReadAsArray(0, 0, cols, rows).astype(
        gdal.GetDataTypeName(segBand.DataType))
    # Get list of unique segments
    useg = unique(seg)
    
    # Hack - if calc is num, do only for 1 band
    if args.stat == 'num':
        bands = 1
    # Create output driver
    driver = gdal.GetDriverByName(args.format)
    outDs = driver.Create(args.output, cols, rows, bands, gdal.GDT_Float32)
    # Create output same as image
    out = zeros_like(img)
    
    # Loop through image  bands
    print 'About to loop through ' + str(bands) + ' bands'
    for b in range(bands):
        print 'Band ' + str(b + 1)
        # Get each band and read into numpy matrix
        imgBand = imgDs.GetRasterBand(b+1)
        NDV = imgBand.GetNoDataValue()
        img = imgBand.ReadAsArray(0, 0, cols, rows).astype(
            gdal.GetDataTypeName(imgBand.DataType))
        
        if args.stat == 'mean':
            # Mean for all regions
            out = ndimage.mean(img, seg, useg)
            out = out[seg - seg.min()]
        elif args.stat == 'var':
            # Variance for all regions
            out = ndimage.variance(img, seg, useg)
            out = out[seg - seg.min()]
        elif args.stat == 'num':
            # Number of pixels in segment
            count = ones_like(seg)
            out = ndimage.sum(count, seg, useg)
            out = out[seg - seg.min()]
        elif args.stat == 'sum':
            # Sum of each band in segments
            out = ndimage.sum(img, seg, useg)
            out = out[seg - seg.min()]
        elif args.stat == 'min':
            # Minimum pixel in each segment
            out = ndimage.minimum(img, seg, useg)
            out = out[seg - seg.min()]
        elif args.stat == 'max':
            # Maximum pixel in each segment
            out = ndimage.maximum(img, seg, useg)
            out = out[seg - seg.min()]
            
        # Write out the data
        outBand = outDs.GetRasterBand(b+1)
        if NDV is not None:
            outBand.SetNoDataValue(NDV)
        outBand.WriteArray(out, 0, 0)
        outBand.FlushCache()
        
    outDs.SetGeoTransform(imgDs.GetGeoTransform())
    outDs.SetProjection(imgDs.GetProjection())
    
    imgDs = None
    segDs = None
    outDs = None    
    
    
# Main program
def main():
    desc = "Calculate a given statistic for pixels in each segment"
    parser = argparse.ArgumentParser(prog='window_stats.py', description=desc)
    
    parser.add_argument('-s', action='store', dest='stat', type=str,
        help='statistic to calculate (mean, var, num, max, min, sum)',
        default='mean')
    
    parser.add_argument('--f', dest='format', default='GTiff',
        help='GDAL format for output file (default "GTiff")')

    parser.add_argument('image', action='store', type=str, 
        help='input image raster file')
    parser.add_argument('segment', action='store', type=str,
        help='input segment raster file')
    parser.add_argument('output', action='store', type=str, 
        help='output raster file')

    args = parser.parse_args()

    possible = ['mean', 'var', 'num', 'max', 'min', 'sum']
    if (args.stat in possible) is False:
        print 'Error: statistic incorrect or not available.'
        print parser.print_help()
        sys.exit(1)
    else:
        objstats(args)

    sys.exit(1)
    
if __name__ == '__main__':
     main()
