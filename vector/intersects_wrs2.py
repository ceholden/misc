#!/bin/env python
""" Tests if geographic data fits within WRS-2 path/row

Usage:
    intersects_wrs2.py [options] <path> <row> <data>

Options:
    --wrs2_file             Override location of WRS-2 file
    --a_srs <EPSG>          Override test data CRS with EPSG code
    -q --quiet              Surpress printing of answer
    -v --verbose            Print verbose debugging messages
    -h --help               Print help screen
    
"""

import os
import sys

from docopt import docopt

try:
    from osgeo import gdal, ogr, osr
except:
    import gdal
    import ogr
    import osr

wrs2_file = '/projectnb/landsat/datasets/WRS-2/wrs2_descending.shp'

QUIET = False
VERBOSE = False

def gdal_get_extent(ds):
    """ Uses input data's GDAL dataset to calculate extent within
    its projection

    Input:
        ds              Test data GDAL data
    
    Returns:
        extent          coordinates of each corner
        proj            projection of input data
    """
    # Get info
    rows = ds.RasterYSize
    cols = ds.RasterXSize
    gt = ds.GetGeoTransform()

    # Calculate corners
    ext = []
    px = [0, cols]
    py = [0, rows]

    for x in px:
        for y in py:
            ext.append([
                gt[0] + (x * gt[1]) + (y * gt[2]),
                gt[3] + (x * gt[4]) + (y * gt[5])
            ])
        py.reverse()

    ext_srs = osr.SpatialReference()
    ext_srs.ImportFromWkt(ds.GetProjection())
    return (ext, ext_srs)
    
def ogr_get_extent(data_ds):
    raise NotImplementedError

def reproj_coord(coord, s_srs, t_srs):
    """ Reprojects coordinates into targeted projection
    """
    transform = osr.CoordinateTransformation(s_srs, t_srs)

    t_coord = []

    for x, y in coord:
        try:
            x, y, z = transform.TransformPoint(x, y, 0)
        except:
            print 'Could not transform coordinates'
            print 'Source: ' + str(s_srs)
            print 'Dest: ' + str(t_srs)
            print 'X: ' + str(x) + ' Y: ' + str(y)
            sys.exit(-1)
        t_coord.append([x, y])
    
    return t_coord

def test_intersect(path, row, ext, ext_srs):
    """ Returns True (1) or False (0) if test extent intersects WRS-2 
    path and row footprint

    Input:
        path            WRS-2 path
        row             WRS-2 row
        ext             test extent
        ext_srs         test extent's spatial reference system
    
    Returns:
        1               True
        0               False
    """
    # Read in WRS-2 path/row
    wrs2 = ogr.Open(wrs2_file)
    if wrs2 is None:
        print 'Error: could not open WRS-2 shapefile'
        print '    Location: %s' % str(wrs2_file)
        print 'Please redefine using --wrs2_file option'
        sys.exit(-1)
    
    # Open layer
    layer = wrs2.GetLayer()
    if layer is None:
        print 'Error opening layer'
        sys.exit(-1)

    # Find correct feature
    found = False
    for feat in layer:
        if (feat.GetFieldAsInteger('PATH') == path and
            feat.GetFieldAsInteger('ROW') == row and
            feat.GetFieldAsString('MODE') == 'D'):
            found = True
            break
    if found is False:
        print 'Error: could not find path/row specified in WRS-2 shapefile'
        sys.exit(-1)

    # Grab the geometry from the chosen feature
    f_geom = feat.GetGeometryRef()

    # Identify WRS-2 file spatial ref system & reproject test extent
    t_srs = layer.GetSpatialRef()
    t_ext = reproj_coord(ext, ext_srs, t_srs)

    # Create geometry from reprojected test extent
    ring = ogr.Geometry(ogr.wkbLinearRing)
    for e in t_ext:
        ring.AddPoint(e[0], e[1])
    ring.CloseRings()

    t_geom = ogr.Geometry(ogr.wkbPolygon)
    t_geom.AddGeometryDirectly(ring)
    
    t_geom.AssignSpatialReference(t_srs)

    # Test for intersection
    return f_geom.Intersect(t_geom)


def main():
    """ Main function that processes input
    """
    path = int(args['<path>'])
    row = int(args['<row>'])
    data = args['<data>']
    print data

    ext_srs = None
    if args['--a_srs'] is not None:
        ext_srs = osr.SpatialReference()
        success = ext_srs.ImportFromEPSG(int(args['--a_srs']))
        if success != 0:
            print 'Error: could not process EPSG override into a valid CS'
            sys.exit(-1)

    # Try opening as GDAL or OGR data
    gdal.AllRegister()
    gdal.UseExceptions()
    
    try:
        data_ds = gdal.Open(data, gdal.GA_ReadOnly)
        type = 'GDAL'
    except:
        try:
            data_ds = ogr.Open(data, gdal.GA_ReadOnly)
            type = 'OGR'
        except:
            print 'Error: cannot open data with GDAL or OGR'
            sys.exit(-1)

    # Define the extent to be tested
    if type == 'GDAL':
        if ext_srs is None:
            ext, ext_srs = gdal_get_extent(data_ds)
        else:
            ext, _ignore = gdal_get_extent(data_ds)
    elif type == 'OGR':
        if ext_srs is None:
            ext, ext_srs = ogr_get_extent(data_ds)
        else:
            ext, _ignore = ogr_get_extent(data_ds)

    ans = test_intersect(path, row, ext, ext_srs)

    if not QUIET:
        print 'Intersect?: ' + str(ans)

    return ans

if __name__ == '__main__':
    args = docopt(__doc__)
    # Exit with status of main
    #   Note:   True        1
    #           False       0
    if args['--quiet']:
        QUIET = True
    sys.exit(main())
