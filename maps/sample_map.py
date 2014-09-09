#!/usr/bin/env python
""" Generate random sample of a map

Usage:
    sample_map.py [options] (random | stratified | systematic) <map>

Options:
    --allocation <allocation>   Sample allocation [default: 'proportional']
    --size <n>                  Sample size for allocation [default: 500]
    --mask <values>             Values to be excluded from sample [default: 0]
    --order                     Order or sort output samples by strata
    --ndv <NoDataValue>         NoDataValue for output raster [default: 255]
    --raster <filename>         Raster filename [default: sample.gtif]
    --rformat <format>          Raster file format [default: GTiff]
    --vector <filename>         Vector filename [default: sample.shp]
    --vformat <format>          Vector file format [default: ESRI Shapefile]
    -v --verbose                Show verbose debugging messages
    -h --help                   Show help
    
Sample size:    
    [specified]                 Specify an integer for total number of samples
    variance                    Estimate number of samples from variance formula

Allocation options:
    proportional
    "good practices"
    equal
    [specified]
"""
from docopt import docopt

import os
import sys

import numpy as np
try:
    from osgeo import gdal
    from osgeo import ogr
    from osgeo import osr
except:
    import gdal
    import ogr
    import osr

VERBOSE = False

gdal.UseExceptions()
gdal.AllRegister()

ogr.UseExceptions()
ogr.RegisterAll()


def random_stratified(image, classes, counts):
    """ 
    Return pixel strata, row, column from within image from a random stratified 
    sample of classes specified

    :param image: input map image
    :type image: np.ndarray
    :param classes: map image classes to be sampled
    :type classes: np.ndarray
    :param counts: map image class sample counts
    :type counts: np.ndarray
    :returns: (strata, col, row) tuple of np.arrays
    :rtype: tuple
    """

    # Initialize outputs
    strata = np.array([])
    rows = np.array([])
    cols = np.array([])

    if VERBOSE:
        print 'Performing sample'

    for c, n in zip(classes, counts):
        if VERBOSE:
            print 'Sampling class {c}'.format(c=c)

        # Find pixels containing class c
        row, col = np.where(image == c)
        
        if VERBOSE:
            print '    found pixels within stratum'

        assert row.size == col.size

        # Check for sample size > population size
        if n > col.size:
            print 'WARNING: class {0} sample size larger than population'.format(c)
            print '         reducing sample count to size of population'

            n = col.size

        # Randomly sample x / y without replacement
        # NOTE: np.random.choice new to 1.7.0... check requirement and provide
        #       replacement
        samples = np.random.choice(col.size, n, replace=False)

        if VERBOSE:
            print '    collected samples'

        strata = np.append(strata, np.repeat(c, n))
        rows = np.append(rows, row[samples])
        cols = np.append(cols, col[samples])



    return (strata, cols, rows)

def sample(image, method, size=None, allocation=None, mask=None, order=False):
    """
    Make sampling decisions and perform sampling

    image -> np.ndarray of the image
    method -> sampling method
    size -> total sample size
    allocation -> str, or list/np.ndarray with sample counts
    mask -> list or np.ndarray of masked values
    order -> boolean, do we order the output by strata?

    :returns: (strata, col, rows)
    """
    # Find map classes within image
    classes = np.sort(np.unique(image))

    # Exclude masked values
    classes = classes[np.in1d(classes, mask)  == False]

    if VERBOSE:
        print 'Found {n} classes:'.format(n=classes.size)
        for c in classes:
            px = np.sum(image == c)
            print '    class {c} - {pix}px ({pct}%)'.format(c=c, pix=px,
                pct=np.round(float(px) / image.size * 100.0, decimals=2))

    # Determine allocation based on input
    if type(allocation) == str:
        # If allocationd determined by method, we must specify a size
        assert type(size) == int, \
            'Must specify sample size if allocation to calculate allocation'

        raise NotImplementedError
    # Or use specified allocation
    elif type(allocation) == list:
        counts = np.array(allocation)
    elif type(allocation) == np.ndarray:
        assert allocation.ndim == 1, 'Allocation must be 1D array'
        counts = allocation
    else:
        raise TypeError, \
            'Allocation must be a str for a method, or a list/np.ndarray'

    # Ensure we found allocation for each class
    assert classes.size == counts.size, \
        'Sample counts must be given for each unmasked class in map'

    # Perform sample using desired method
    if method == 'stratified':
        strata, cols, rows = random_stratified(image, classes, counts)
    elif method == 'random':
        raise NotImplementedError
    elif method == 'systematic':
        raise NotImplementedError

    # Randomize samples if not ordered
    if order is not True:
        sort_index = np.random.choice(strata.size, strata.size, replace=False)

        strata = strata[sort_index]
        cols = cols[sort_index]
        rows = rows[sort_index]

    return (strata, cols, rows)

def write_raster_output(strata, cols, rows, map_ds, output, 
        gdal_frmt='GTiff', ndv=255):
    """
    """
    # Init and fill output array with samples
    raster = np.ones((map_ds.RasterYSize, map_ds.RasterXSize),
        dtype=np.uint8) * ndv

    for s, c, r in zip(strata, cols, rows):
        raster[r, c] = s

    # Get output driver
    driver = gdal.GetDriverByName(gdal_frmt)

    # Create output dataset
    sample_ds = driver.Create(output,
        map_ds.RasterXSize, map_ds.RasterYSize, 1, 
        gdal.GetDataTypeByName('Byte'))

    # Write out band
    sample_ds.GetRasterBand(1).SetNoDataValue(ndv)
    sample_ds.GetRasterBand(1).WriteArray(raster)

    # Port over metadata, projection, geotransform, etc
    sample_ds.SetProjection(map_ds.GetProjection())
    sample_ds.SetGeoTransform(map_ds.GetGeoTransform())
    sample_ds.SetMetadata(map_ds.GetMetadata())

    # Close
    sample_ds = None

def write_vector_output(strata, cols, rows, map_ds, output,
    ogr_frmt='ESRI Shapefile'):
    """
    """
    # Corners of pixel in pixel coordinates
    corners = [(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)]

    # Raster geo-transform
    gt = map_ds.GetGeoTransform()
    # Get OSR spatial reference from raster to give to OGR dataset
    map_sr = osr.SpatialReference()
    map_sr.ImportFromWkt(map_ds.GetProjectionRef())

    # Get OGR driver
    driver = ogr.GetDriverByName(ogr_frmt)
    # Create OGR dataset and layer
    sample_ds = driver.CreateDataSource(output)
    layer = sample_ds.CreateLayer('sample', map_sr, geom_type=ogr.wkbPolygon)

    # Add fields for layer
    # Sample ID field
    layer.CreateField(ogr.FieldDefn('ID', ogr.OFTInteger))
    # Row/Col fields
    layer.CreateField(ogr.FieldDefn('ROW', ogr.OFTInteger))
    layer.CreateField(ogr.FieldDefn('COL', ogr.OFTInteger))
    # Strata field
    layer.CreateField(ogr.FieldDefn('STRATUM', ogr.OFTInteger))

    # Loop through samples adding to layer
    for i, (stratum, col, row) in enumerate(zip(strata, cols, rows)):
        # Feature
        feature = ogr.Feature(layer.GetLayerDefn())
        feature.SetField('ID', i)
        feature.SetField('ROW', row)
        feature.SetField('COL', col)
        feature.SetField('STRATUM', stratum)

        # Geometry
        ring = ogr.Geometry(type=ogr.wkbLinearRing)

        for corner in corners:
            ring.AddPoint(
                gt[0] + (col + corner[0]) * gt[1] + (row + corner[1]) * gt[2],
                gt[3] + (col + corner[1]) * gt[4] + (row + corner[1]) * gt[5])
        square = ogr.Geometry(type=ogr.wkbPolygon)
        square.AddGeometry(ring)

        feature.SetGeometry(square)

        layer.CreateFeature(feature)

        feature.Destroy()

    sample_ds = None


def main():
    # TODO read these in
    image_fn = 'map_mosaic_masked.bsq'
    method = 'stratified'
    allocation = np.array([150, 50, 50, 50, 150])

    mask = np.array([5])

    # output_raster = 'subset_sample.gtif'
    output_raster = 'sample_map.gtif'
    output_vector = 'sample.shp'
    gdal_frmt = 'GTiff'
    ogr_frmt = 'ESRI Shapefile'
    ndv = 255

    # Test output drivers
    gdal_driver = gdal.GetDriverByName(gdal_frmt)
    assert gdal_driver is not None, \
        'Could not create GDAL driver for format {f}'.format(f=gdal_frmt)
    
    ogr_driver = ogr.GetDriverByName(ogr_frmt)
    assert ogr_driver is not None, \
        'Could not create OGR driver for format {f}'.format(f=ogr_frmt)
    if os.path.exists(output_vector):
        try:
            ogr_driver.DeleteDataSource(output_vector)
        except:
            print 'Error - cannot overwrite existing output vector file {f}'.format(f=output_vector)
            raise

    gdal_driver = None
    ogr_driver = None
    
    # Read in image
    image_ds = gdal.Open(image_fn, gdal.GA_ReadOnly)
    image = image_ds.GetRasterBand(1).ReadAsArray()

    if VERBOSE:
        print 'Read in map image to be sampled'

    strata, cols, rows = sample(image, method, allocation=allocation, mask=mask)

    if VERBOSE:
        print 'Finished collecting samples'

    image = None

    if output_raster is not None:
        if VERBOSE:
            print 'Writing raster output to {f}'.format(f=output_raster)
        write_raster_output(strata, cols, rows, 
            image_ds, output_raster, gdal_frmt, ndv)

    if output_vector is not None:
        if VERBOSE:
            print 'Writing vector output to {f}'.format(f=output_vector)
        write_vector_output(strata, cols, rows, 
            image_ds, output_vector, ogr_frmt)

if __name__ == '__main__':
    args = docopt(__doc__)

    if args['--verbose']:
        VERBOSE = True

    main()
