#!/usr/bin/env python
# /*****************************************************************************
# * Name:       object_stats.py
# * Author:     Chris Holden (ceholden@gmail.com)
# * Version:    1.0
# * Purpose:    To read an image and segmentation image using GDAL and to
# *             calculate statistics for each segment using the image.
# * Methods:    Use GDAL (gdal.org) to read the images and import into numpy
# *             arrays. Next, use find_objects to get i, j coordinates in image
# *             of pixels in i=1:n segments. Finally, use ndimage library
# *             to calculate statistic for given segment.
# *
# *****************************************************************************\
from __future__ import division, print_function
import argparse
import logging
import sys

import numpy as np
from scipy import ndimage

from osgeo import gdal, gdal_array

__version__ = '1.0.0'

gdal.AllRegister()
gdal.UseExceptions()

logging.basicConfig(format='%(asctime)s.%(levelname)s: %(message)s',
                    level=logging.INFO,
                    datefmt='%H:%M:%S')
logger = logging.getLogger(__name__)

STATISTICS = ['mean', 'var', 'num', 'max', 'min', 'sum']


def objstats(args):
    # Open and read from image and segmentation
    try:
        img_ds = gdal.Open(args.image, gdal.GA_ReadOnly)
    except:
        logger.error('Could not open image: {}'.format(i=args.image))
        sys.exit(1)

    try:
        seg_ds = gdal.Open(args.segment, gdal.GA_ReadOnly)
    except:
        logger.error('Could not open segmentation image: {}'.format(
            i=args.segment))
        sys.exit(1)

    cols, rows = img_ds.RasterXSize, img_ds.RasterYSize
    bands = img_ds.RasterCount

    seg_band = seg_ds.GetRasterBand(1)
    seg = seg_band.ReadAsArray(0, 0, cols, rows).astype(
        gdal_array.GDALTypeCodeToNumericTypeCode(seg_band.DataType))
    logger.debug('Read segmentation image into memory')

    # Get list of unique segments
    useg = np.unique(seg)
    sequential = False
    if np.array_equal(useg, np.arange(useg.min(), useg.max(), 1)):
        logger.debug('Segmentation image is sequential. Can use fast method')
        sequential = True
    else:
        logger.debug(
            'Segmentation image is not sequential. Processing will be slower')

    # If calc is num, do only for 1 band
    if args.stat == 'num':
        bands = 1

    # Create output driver
    driver = gdal.GetDriverByName(args.format)
    out_ds = driver.Create(args.output, cols, rows, bands, gdal.GDT_Float32)

    # Loop through image  bands
    out_2d = np.empty_like(seg, dtype=np.float32)
    for b in range(bands):
        logger.info('Processing band: {i}'.format(i=b + 1))
        img_band = img_ds.GetRasterBand(b + 1)
        ndv = img_band.GetNoDataValue()
        img = img_band.ReadAsArray().astype(
            gdal_array.GDALTypeCodeToNumericTypeCode(img_band.DataType))
        logger.debug('Read image band {b} into memory'.format(b=b + 1))

        # Mask out segment values where img == NoDataValue
        ndv_seg = seg.copy()
        # if ndv is not None:
        #     ndv_seg[img == ndv] = 0

        if args.stat == 'mean':
            # Mean for all regions
            logger.debug('Calculating mean')
            out = ndimage.mean(img, ndv_seg, useg)
        elif args.stat == 'var':
            # Variance for all regions
            out = ndimage.variance(img, ndv_seg, useg)
        elif args.stat == 'num':
            # Number of pixels in segment
            count = np.ones_like(ndv_seg)
            out = ndimage.sum(count, ndv_seg, useg)
        elif args.stat == 'sum':
            # Sum of each band in segments
            out = ndimage.sum(img, ndv_seg, useg)
        elif args.stat == 'min':
            # Minimum pixel in each segment
            out = ndimage.minimum(img, ndv_seg, useg)
        elif args.stat == 'max':
            # Maximum pixel in each segment
            out = ndimage.maximum(img, ndv_seg, useg)
        logger.debug('Computed statistic for all segment IDs')

        # Transform to 2D
        if sequential:
            out = out[ndv_seg - ndv_seg.min()]
        else:
            for i, u in np.ndenumerate(useg):
                r, c = np.where(ndv_seg == u)
                out_2d[r, c] = out[i]
        logger.debug('Applied statistic to entire image')

        # Write out the data
        out_band = out_ds.GetRasterBand(b + 1)
        if ndv is not None:
            out_band.SetNoDataValue(ndv)
        logger.debug('Writing object statistic for band {b}'.format(b=b + 1))
        out_band.WriteArray(out_2d, 0, 0)
        out_band.FlushCache()
        logger.debug('Wrote out object statistic for band {b}'.format(b=b + 1))

    out_ds.SetGeoTransform(img_ds.GetGeoTransform())
    out_ds.SetProjection(img_ds.GetProjection())

    img_ds = None
    seg_ds = None
    out_ds = None
    logger.info('Completed object statistic calculation')


# Main program
def main():
    desc = "Calculate a given statistic for pixels in each segment"
    parser = argparse.ArgumentParser(prog='object_stats.py', description=desc)

    parser.add_argument('--version', action='version',
                        version='%(prog)s v{v}'.format(v=__version__))
    parser.add_argument('--verbose', '-v', help="increase output verbosity",
                        action="store_true")
    parser.add_argument(
        '-s', action='store', dest='stat', type=str,
        help='statistic to calculate ({c})'.format(c=', '.join(STATISTICS)),
        default='mean')
    parser.add_argument(
        '-of', dest='format', default='GTiff',
        help='GDAL format for output file (default "GTiff")')
    parser.add_argument(
        'image', action='store', type=str,
        help='input image raster file')
    parser.add_argument(
        'segment', action='store', type=str,
        help='input segment raster file')
    parser.add_argument(
        'output', action='store', type=str,
        help='output raster file')

    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)

    if args.stat not in STATISTICS:
        logger.error('Statistic {s} is incorrect or not available.'.format(
            s=args.stat))
        parser.print_help()
        sys.exit(1)
    else:
        objstats(args)


if __name__ == '__main__':
    main()
