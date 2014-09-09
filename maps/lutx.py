#!/usr/bin/env python
# -*- coding: utf-8 -*
# vim: set expandtab:ts=4
"""Look-Up-Table Execute (lutx)

Usage:
    lutx.py [options] <lut_csv> <input> <output>

Options:
    -c --colname            Header column names
    -d --delim=<delim>      CSV delimiter [default: ,]
    -q --quote=<quote>      CSV quote character [default: "]
    --format=<format>       Output format [default: ENVI]
    -v --debug              Show (verbose) debugging messages
    -h --help               Show help
"""
from docopt import docopt

import csv
import os
import sys

try:
    from osgeo import gdal
    from osgeo import gdal_array
    from osgeo.gdalconst import GA_ReadOnly
except ImportError:
    import gdal
    from gdalconst import GA_ReadOnly

import numpy as np

# Make stdout unbuffered
sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)

DEBUG = False

def read_lut(csvfile, header, delimiter, quotechar):
    """
    Reads CSV file and records LUT as dictionary
    """
    # Read in file
    with open(csvfile, 'rb') as f:
        csvreader = csv.reader(f, delimiter=delimiter, quotechar=quotechar)
        if header:
            csvreader.next()
        lut = { int(row[0]) : int(row[1]) for row in csvreader }

    if DEBUG:
        print 'Read in LUT:\n {0}'.format(lut)

    return lut

def lutx(lut, input, output, format):
    """
    Reads in input image, applies lut and outputs image
    """
    # Read in input image
    gdal.AllRegister()
    src_ds = gdal.Open(input, GA_ReadOnly)
    if src_ds is None:
        print 'Error: could not open {0}'.format(input)
    rows = src_ds.RasterYSize
    cols = src_ds.RasterXSize
    # Read in data
    band = src_ds.GetRasterBand(1)
    dtype = band.DataType
    data = band.ReadAsArray(0, 0, cols, rows).astype(
                                gdal_array.flip_code(dtype))
    
    # Determine requiredo output datatype
    out_dt = np.byte
    if np.min(lut.values()) < 0:
        # Must be signed int
        if np.max(np.abs(lut.values())) < 2 ** 15:
            # NOTE: put np.int8 as np.int16 since GDAL has no int8
            out_dt = np.int16
        elif np.max(np.abs(lut.values())) < 2 ** 31:
            out_dt = np.int32
        elif np.max(np.abs(lut.values())) < 2 ** 63:
            out_dt = np.int64
        else:
            print 'Required output data type is unknown'
            sys.exit(1)
    else:
        # Can be unsigned
        if np.max(lut.values()) < 2 ** 8:
            out_dt = np.uint8
        elif np.max(lut.values()) < 2 ** 16:
            out_dt = np.uint16
        elif np.max(lut.values()) < 2 ** 32:
            out_dt = np.uint32
        elif np.max(lut.values()) < 2 ** 64:
            out_dt = np.uint64
        else:
            print 'Required output data type is unknown'
            sys.exit(1)

    if DEBUG:
        print 'NumPy data type:  %s' % str(out_dt)
        print 'GDAL data type:   %s' % str(
            gdal.GetDataTypeName(gdal_array.flip_code(out_dt)))

    # Copy data for output
    lutdata = data.copy().astype(out_dt)
    # Apply lut
    for key, value in lut.iteritems():
        np.place(lutdata, data == key, value)

    # Write to output
    driver = gdal.GetDriverByName(format)
    dst_ds = driver.Create(output, 
                           src_ds.RasterXSize, src_ds.RasterYSize, 1,
                           gdal_array.flip_code(out_dt))
    dst_ds.SetProjection(src_ds.GetProjection())
    dst_ds.SetGeoTransform(src_ds.GetGeoTransform())
    dst_ds.GetRasterBand(1).WriteArray(lutdata)
    # Close
    src_ds = None
    dst_ds = None
    print 'Wrote output to file {0}'.format(output)

def main():
    gdal.UseExceptions()
    ### Handle input arguments and options
    # Input CSV file
    csvfile = arguments['<lut_csv>']
    if not os.path.exists(csvfile):
        print 'Could not find input file {0}'.format(csvfile)
        sys.exit(1)
    # Input image
    input = arguments['<input>']
    if os.path.dirname(input) == '':
        input = './' + input
    if not os.path.exists(input):
        print 'Could not find input image {0}'.format(input)
        sys.exit(1)
    elif not os.access(input, os.R_OK):
        print 'Cannot read input image {0}'.format(input)
        sys.exit(1)
    # Output image
    output = arguments['<output>']
    if os.path.dirname(output) == '':
        output = './' + output
    if not os.access(os.path.dirname(output), os.W_OK):
        print 'Cannot write to output image {0}'.format(output)
        sys.exit(1)
    # Header column name
    header = arguments['--colname']
    # Delimiter
    delim = arguments['--delim']
    # Quote character
    quotechar = arguments['--quote']
   
    # Format
    format = arguments['--format']

    # Read CSV and get look-up-table
    lut = read_lut(csvfile, header, delim, quotechar)
    # Execute LUT
    lutx(lut, input, output, format)

if __name__ == '__main__':
    arguments = docopt(__doc__)
    if arguments['--debug']:
        DEBUG = True
    main()
