#!/usr/bin/env python
""" Crosstabulate reference samples

Usage:
    crosstab.py [options] <raster_map> <vector_reference> <output_csv>

Options:
    -l --layer=<layer>          Layer in shapefile (index or name) [default: 0]
    -a --attribute=<attribute>  Attribute to compare with map [default: truth]
    -v --verbose                Show verbose debugging messages
    -h --help                   Show help

Example:

    Crosstabulate reference data from vector file "sample.shp" using field
        named "Ref_label" with map named "UCA_val_period.tif":

    > crosstab.py -v -a Ref_label CA_val_period.tif sample.shp crosstab.txt

    Outputs:
        ,Map-Class_1,Map-Class_2,Map-Class_3,Map-Class_255
        Ref-Class_1,12,4,1,5
        Ref-Class_2,3,4,5,0
        Ref-Class_3,1,3,1,5
        Ref-Class_255,4,9,3,0

"""

from __future__ import print_function

import logging
import os
import sys

from docopt import docopt
import numpy as np
try:
    from osgeo import gdal
    from osgeo import ogr
except:
    import gdal
    import ogr

__version__ = '0.1.0'

VERBOSE = False

gdal.UseExceptions()
gdal.AllRegister()

ogr.UseExceptions()
ogr.RegisterAll()

logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s',
                    level=logging.INFO,
                    datefmt='%H:%M:%S')
logger = logging.getLogger(__name__)


def rasterize_map(raster_file, vector_file, attribute, layer=1):
    """ Rasterizes vector file to extent/size of raster """
    # Open raster file
    try:
        raster_ds = gdal.Open(raster_file, gdal.GA_ReadOnly)
    except:
        logger.error('Cannot open input raster')
        sys.exit(1)
    raster = raster_ds.GetRasterBand(1).ReadAsArray()
    logger.debug('Read in raster file')

    # Get raster NoDataValue
    ndv = raster_ds.GetRasterBand(1).GetNoDataValue()
    if not ndv:
        logger.warning('Could not find NoDataValue for raster')
        logger.warning('Setting NoDataValue to 0')
        ndv = 0

    # Open vector file
    try:
        vector = ogr.Open(vector_file)
    except:
        logger.error('Cannot open input vector')
        sys.exit(1)
    logger.debug('Opened vector file')

    # Try getting layer - try by index if layer is int, or string if not
    try:
        layer = int(layer)
    except:
        pass

    if isinstance(layer, int):
        logger.debug('Trying to open layer by index')

        layer = vector.GetLayerByIndex(layer)
        if layer is None:
            logger.debug('Could not open layer by index... trying by name')
            layer = str(layer)
        else:
            logger.debug('Opened layer by index')

    if isinstance(layer, str):
        # GetLayerByName
        logger.debug('Trying to open layer by name {n}'.format(n=layer))
        layer = vector.GetLayerByName(layer)

        if layer is None:
            logger.error('Could not open layer by name or index')
            sys.exit(1)

        logger.debug('Opened layer by name')

    # Try to get attribute by name
    layer_defn = layer.GetLayerDefn()
    field_names = []
    for i in range(layer_defn.GetFieldCount()):
        field_defn = layer_defn.GetFieldDefn(i)
        field_names.append(field_defn.GetName())

    if attribute not in field_names:
        logger.error(
            'Cannot find attribute {a} in vector file'.format(a=attribute))
        logger.error('Available attributes are: {f}'.format(f=field_names))
        sys.exit(1)
    logger.debug('Found attribute {a} in vector file'.format(a=attribute))

    # If we've passed checks so far, setup memory raster
    logger.debug('Setting up memory raster for rasterization')
    mem_driver = gdal.GetDriverByName('MEM')

    mem_ds = mem_driver.Create('',
                               raster_ds.RasterXSize,
                               raster_ds.RasterYSize,
                               1,
                               raster_ds.GetRasterBand(1).DataType)
    mem_ds.SetProjection(raster_ds.GetProjection())
    mem_ds.SetGeoTransform(raster_ds.GetGeoTransform())
    logger.debug('Set up memory dataset for rasterization')

    # Fill with NDV
    mem_ds.GetRasterBand(1).Fill(ndv)

    # Rasterize
    status = gdal.RasterizeLayer(mem_ds,
                                 [1],
                                 layer,
                                 None, None,
                                 burn_values=[ndv],
                                 options=['ALL_TOUCHED=FALSE',
                                          'ATTRIBUTE={a}'.format(a=attribute)]
                                 )

    if status != 0:
        logger.error('Could not rasterize vector')
        sys.exit(1)
    else:
        logger.debug('Rasterized vector file')

    # Get raster from dataset and return
    print(np.unique(mem_ds.GetRasterBand(1).ReadAsArray()))
    return (mem_ds.GetRasterBand(1).ReadAsArray(), raster, ndv)


def crosstabulate(rasterized, raster, ndv=0):
    """ Crosstabulate raster against rasterized vector file """
    # Find all values in either dataset
    uniqs = np.unique(np.concatenate([
        np.unique(rasterized[rasterized != ndv]),
        np.unique(raster[raster != ndv])]))

    # Crosstabulate
    tab = np.zeros((uniqs.size, uniqs.size))

    for i, uv_row in enumerate(uniqs):
        for j, uv_col in enumerate(uniqs):
            tab[i, j] = (raster[rasterized == uv_row] == uv_col).sum()
    logger.debug('Crosstabulated map with reference data')

    # Setup array headers
    rownames = np.array(['Ref-Class_' + str(u)
                        for u in uniqs])[:, np.newaxis]
    colnames = ['']
    colnames.extend(['Map-Class_' + str(u) for u in uniqs])

    pretty_tab = np.hstack((rownames, np.char.mod('%i', tab)))
    pretty_tab = np.vstack((colnames, pretty_tab))

    # Return with reference across & map labels going down
    return pretty_tab.T


def main():
    """ Read input arguments, check them, then run script """
    # Raster map
    raster = args['<raster_map>']
    if not os.path.isfile(raster):
        logging.error('Input raster map {r} does not exist'.format(r=raster))
        sys.exit(1)

    # Vector file
    vector = args['<vector_reference>']
    if not os.path.isfile(vector):
        logging.error('Input vector file {r} does not exist'.format(r=vector))
        sys.exit(1)

    # Output file
    output = args['<output_csv>']

    # Layer in shapefile
    layer = args['--layer']

    # Attribute in vector layer
    attribute = args['--attribute']

    # Rasterize vector file
    rasterized, raster_image, ndv = rasterize_map(
        raster, vector, attribute, layer=layer)

    # Crosstabulate
    crosstab = crosstabulate(rasterized, raster_image, ndv=ndv)

    print(crosstab)
    with open(output, 'w') as f:
        np.savetxt(f, crosstab, fmt='%s', delimiter=',')

if __name__ == '__main__':
    args = docopt(__doc__,
                  version=__version__)
    if args['--verbose']:
        VERBOSE = True
        logger.setLevel(logging.DEBUG)

    main()
