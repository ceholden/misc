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
from scipy import ndimage, stats

from osgeo import gdal, gdal_array, ogr, osr

__version__ = '1.0.0'

gdal.AllRegister()
gdal.UseExceptions()

logging.basicConfig(format='%(asctime)s.%(levelname)s: %(message)s',
                    level=logging.INFO,
                    datefmt='%H:%M:%S')
logger = logging.getLogger(__name__)

STATISTICS = ['mean', 'var', 'num', 'max', 'min', 'sum', 'mode']


def scipy_mode(arr):
    return stats.mode(arr, axis=None)[0]


def objstats(args):
    # Open and read from image and segmentation
    try:
        img_ds = gdal.Open(args.image, gdal.GA_ReadOnly)
    except:
        logger.error('Could not open image: {}'.format(i=args.image))
        sys.exit(1)

    try:
        seg_ds = ogr.Open(args.segment, 0)
        seg_layer = seg_ds.GetLayer()
    except:
        logger.error('Could not open segmentation vector file: {}'.format(
            i=args.segment))
        sys.exit(1)

    cols, rows = img_ds.RasterXSize, img_ds.RasterYSize
    bands = range(1, img_ds.RasterCount + 1)
    if args.bands is not None:
        bands = args.bands

    # Rasterize segments
    logger.debug('About to rasterize segment vector file')
    img_srs = osr.SpatialReference()
    img_srs.ImportFromWkt(img_ds.GetProjectionRef())

    mem_raster = gdal.GetDriverByName('MEM').Create(
        '', cols, rows, 1, gdal.GDT_UInt32)
    mem_raster.SetProjection(img_ds.GetProjection())
    mem_raster.SetGeoTransform(img_ds.GetGeoTransform())

    # Create artificial 'FID' field
    fid_layer = seg_ds.ExecuteSQL(
        'select FID, * from {l}'.format(l=seg_layer.GetName()))
    gdal.RasterizeLayer(mem_raster, [1], fid_layer, options=['ATTRIBUTE=FID'])
    logger.debug('Rasterized segment vector file')

    seg = mem_raster.GetRasterBand(1).ReadAsArray()
    logger.debug('Read segmentation image into memory')
    mem_raster = None
    seg_ds = None

    # Get list of unique segments
    useg = np.unique(seg)

    # If calc is num, do only for 1 band
    out_bands = 0
    for stat in args.stat:
        if stat == 'num':
            out_bands += 1
        else:
            out_bands += len(bands)

    # Create output driver
    driver = gdal.GetDriverByName(args.format)
    out_ds = driver.Create(args.output, cols, rows, out_bands,
                           gdal.GDT_Float32)

    # Loop through image bands
    out_b = 0
    out_2d = np.empty_like(seg, dtype=np.float32)
    for i_b, b in enumerate(bands):
        img_band = img_ds.GetRasterBand(b)
        ndv = img_band.GetNoDataValue()
        band_name = img_band.GetDescription()
        if not band_name:
            band_name = 'Band {i}'.format(i=b)
        logger.info('Processing input band {i}, "{b}"'.format(
            i=b, b=band_name))

        img = img_band.ReadAsArray().astype(
            gdal_array.GDALTypeCodeToNumericTypeCode(img_band.DataType))
        logger.debug('Read image band {i}, "{b}" into memory'.format(
            i=b, b=band_name))

        for stat in args.stat:
            logger.debug('    calculating {s}'.format(s=stat))
            if stat == 'mean':
                out = ndimage.mean(img, seg, useg)
            elif stat == 'var':
                out = ndimage.variance(img, seg, useg)
            elif stat == 'num':
                # Remove from list of stats so it is only calculated once
                args.stat.remove('num')
                count = np.ones_like(seg)
                out = ndimage.sum(count, seg, useg)
            elif stat == 'sum':
                out = ndimage.sum(img, seg, useg)
            elif stat == 'min':
                out = ndimage.minimum(img, seg, useg)
            elif stat == 'max':
                out = ndimage.maximum(img, seg, useg)
            elif stat == 'mode':
                out = ndimage.labeled_comprehension(img, seg, useg,
                                                    scipy_mode,
                                                    out_2d.dtype, ndv)
            else:
                logger.error('Unknown stat. Not sure how you got here')
                sys.exit(1)

            # Transform to 2D
            out_2d = out[seg - seg.min()]

            # Fill in NDV
            if ndv is not None:
                out_2d[np.where(img == ndv)] = ndv

            # Write out the data
            out_band = out_ds.GetRasterBand(out_b + 1)
            out_band.SetDescription(band_name)
            if ndv is not None:
                out_band.SetNoDataValue(ndv)
            logger.debug('    Writing object statistic for band {b}'.format(
                    b=b + 1))
            out_band.WriteArray(out_2d, 0, 0)
            out_band.FlushCache()
            logger.debug('    Wrote out object statistic for band {b}'.format(
                    b=b + 1))
            out_b += 1

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

    parser.add_argument('-of', dest='format', default='GTiff',
                        help='GDAL format for output file (default "GTiff")')
    parser.add_argument('-b', '--bands', dest='bands', default=None,
                        type=int, nargs='*',
                        help='Bands within input image to process')
    parser.add_argument('--version', action='version',
                        version='%(prog)s v{v}'.format(v=__version__))
    parser.add_argument('--verbose', '-v', help="increase output verbosity",
                        action="store_true")
    parser.add_argument('image', action='store', type=str,
                        help='input image raster file')
    parser.add_argument('segment', action='store', type=str,
                        help='input segment raster file')
    parser.add_argument('output', action='store', type=str,
                        help='output raster file')
    parser.add_argument('stat', nargs='*', action='store',
                        help='statistic to calculate ({c})'.format(
                            c=', '.join(STATISTICS)))

    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)

    if not all([stat in STATISTICS for stat in STATISTICS]):
        logger.error('Statistic {s} is incorrect or not available.'.format(
            s=args.stat))
        parser.print_help()
        sys.exit(1)
    else:
        objstats(args)


if __name__ == '__main__':
    main()
