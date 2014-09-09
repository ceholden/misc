#!/bin/env python
""" Converts point data to a square of a given size

Usage:
    point2square.py [options] (--topleft | --center ) <size> <input> <output>

Options:
    --overwrite             Allow overwrite of output?
    -f --format=format      Output format [default: ESRI Shapefile]
    -q --quiet              Surpress printing of answer
    -v --verbose            Print verbose debugging messages
    -h --help               Print help screen
    
"""
import os
import sys

from docopt import docopt

try:
    from osgeo import ogr
except:
    import ogr

# Make stdout unbuffered
sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)

QUIET = False
VERBOSE = False

def drawProgressBar(percent, barLen = 60):
    """ Progress bar - taken from Jacob Tsui:
http://stackoverflow.com/questions/3002085/python-to-print-out-status-bar-and-percentage
    """
    sys.stdout.write("\r")
    progress = ""
    for i in range(barLen):
        if i < int(barLen * percent):
            progress += "="
        else:
            progress += " "
    sys.stdout.write("[ %s ] %.2f%%" % (progress, percent * 100))
    sys.stdout.flush()

def point2square(size, input, output, topleft, format):
    """
    """
    # Configure corners
    if topleft is True:
        corners = [(0, 0), (size, 0), (size, -size), (0, -size), (0, 0)]
    elif topleft is False:
        hs = size / 2.0
        corners = [(-hs, hs), (hs, hs), (hs, -hs), (-hs, -hs), (-hs, hs)]

    # Open & get layer
    in_ds = ogr.Open(input)
    if in_ds is None:
        print 'Error: could not open input file'
        sys.exit(1)
    in_layer = in_ds.GetLayer()

    # Ensure the layer has points
    if ogr.GeometryTypeToName(in_layer.GetGeomType()) != 'Point':
        print 'Error: input vector file must have Point geometry'
        sys.exit(1)

    # Create output
    driver = ogr.GetDriverByName(format)
    out_ds = driver.CreateDataSource(output)
    if out_ds is None:
        print 'Error: could not create output file'
        sys.exit(1)
    out_layer = out_ds.CreateLayer(in_layer.GetName() + '_square',
                                   in_layer.GetSpatialRef(),
                                   geom_type=ogr.wkbPolygon)

    # Copy FeatureDefn from input
    featDefn = in_layer.schema
    for defn in featDefn:
        result = out_layer.CreateField(defn)
        if result != 0:
            print 'Error: cannot create field {0}'.format(defn.GetName())
            sys.exit(1)
    fields = [f.GetName() for f in featDefn]

    # Setup progress bar
    if VERBOSE:
        n_feat = in_layer.GetFeatureCount()
        i = 0.0

    # Populate fields
    for in_feat in in_layer:
        # Progress
        if VERBOSE:
            drawProgressBar(i / n_feat)
            i += 1.0

        # Setup new feature
        out_feat = ogr.Feature(in_layer.GetLayerDefn())
        out_feat.SetFID(in_feat.GetFID())
        
        # Add fields and populate
        for f in fields:
            out_feat.SetField(f, in_feat.GetField(f))

        # Setup geometry
        point = in_feat.GetGeometryRef().GetPoint_2D()
        ring = ogr.Geometry(type=ogr.wkbLinearRing)
        for corner in corners:
            ring.AddPoint(corner[0] + point[0], 
                          corner[1] + point[1])
        poly = ogr.Geometry(type=ogr.wkbPolygon)
        poly.AddGeometry(ring)

        # Set geometry for out_feat
        out_feat.SetGeometry(poly)
        
        # Add feature to layer
        out_layer.CreateFeature(out_feat)

        # Flush memory of feature
        out_feat.Destroy()

    if VERBOSE:
        print ''
        print 'Done processing all features from input layer'

    # Flush memory for layer
    out_ds = None
    in_ds = None

def main():
    """ Main function that processes input
    """
    ogr.UseExceptions()
    ### Parse arguments
    # Size
    size = arguments['<size>']
    try:
        size = int(size)
    except:
        try:
            size = float(size)
        except:
            print 'Error: cannot convert input size to a number'
            sys.exit(1)
    
    # Input vector file
    input = arguments['<input>']
    if os.path.dirname(input) == '':
        input = './' + input
    if not os.path.exists(input):
        print 'Error: could not find input file {0}'.format(input)
        sys.exit(1)
    if not os.access(input, os.R_OK):
        print 'Error: cannot read input file {0}'.format(input)
        sys.exit(1)

    # Output vector file
    output = arguments['<output>']
    if os.path.dirname(output) == '':
        output = './' + output
    if os.path.exists(output) and arguments['--overwrite']:
        print 'Output layer exists - overwriting'
        try:
            ds = ogr.Open(output)
            driver = ds.GetDriver()
            driver.DeleteDataSource(output)
        except:
            print 'Error: could not overwrite existing output file'
            sys.exit(1)
    elif os.path.exists(output) and not arguments['--overwrite']:
        print 'Error: output file already exists. Specify "--overwrite"'
        sys.exit(1)
    else:
        if not os.access(os.path.dirname(output), os.W_OK):
            print 'Error: cannot write to output location'
            sys.exit(1)

    # Topleft/Middle
    topleft = None
    if arguments['--topleft']:
        topleft = True
    elif arguments['--center']:
        topleft = False


    # Format
    format = arguments['--format']
    test = ogr.GetDriverByName(format)
    if test is None:
        print 'Error: unknown format "{0}"'.format(format)
        sys.exit(1)
    test = None

    point2square(size, input, output, topleft, format)

if __name__ == '__main__':
    arguments = docopt(__doc__)
    if arguments['--verbose']:
        VERBOSE = True
    if arguments['--quiet']:
        QUIET = True
    main()
