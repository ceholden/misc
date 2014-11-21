#!/usr/bin/env python
# -*- coding: utf-8 -*
# vim: set expandtab:ts=4
"""Number of Observations in Stacks

Usage:
    stack_nobs.py [options] <location> <output> [<maskvalues>...]

Options:
    -n --name <name>        Pattern of each stack file [default: *stack]
    -d --dname <dname>      Pattern for each stack directory [default: L*]
    -m --mask <band>        Mask band [default: 8]
    -n --ndv <ndv>          No data value [default: 255]
    -f --format <format>    Output file format [default: GTiff]
    -v --debug              Show (verbose) debugging messages
    -h --help               Show help
"""
from docopt import docopt

try:
    from osgeo import gdal
    from osgeo import gdal_array
except ImportError:
    import gdal
    import gdal_array
    
import fnmatch
import os
import sys 
    
import numpy as np

DEBUG = False
QUIET = False


def stack_nobs(location, output, mask_val, mask_band, stkname, stkdir, format):
    """
    Loops through stacks within location building image that stores number of
    valid observations in each pixel.
    """
    # Find the stacks
    stacks = []
    for root, dirs, files in os.walk(location, topdown=True):
        dirs[:] = fnmatch.filter(dirs, stkdir)
        for f in fnmatch.filter(files, stkname):
            stacks.append(os.path.join(root, f))
    if len(stacks) == 0:
        print 'Error: could not find any stacks in {0}'.format(location)

    # Determine output data type
    if len(stacks) < 255:
        dtype = np.uint8
    elif len(stacks) < 65535:
        dtype = np.uint16
    else:
        print 'Do you really have {0} stacks?'.format(str(len(stacks)))
        sys.exit(1)
    
    # Open first stack to get size; create output Nobs image
    ex_ds = gdal.Open(stacks[0], gdal.GA_ReadOnly)
    if ex_ds is None:
        print 'Error: could not open {img}'.format(stacks[0])
        sys.exit(1)
    nobs = np.zeros((ex_ds.RasterYSize, ex_ds.RasterXSize), dtype=dtype)
    

    # Loop through remainder of stacks adding to nobs
    for stack in stacks:
        src_ds = gdal.Open(stack, gdal.GA_ReadOnly)
        if src_ds is None:
            print 'Error: could not open {img}'.format(img=stack)
            sys.exit(1)
        if (src_ds.RasterYSize, src_ds.RasterXSize) != nobs.shape:
            print 'Error: {img} is not a consistent size'.format(img=stack)
        if mask_band > src_ds.RasterCount:
            print 'Error: {img} does not have band {band}'.format(
                img=stack, band=mask_band)
            sys.exit(1)
        # Read in
        data = src_ds.GetRasterBand(mask_band).ReadAsArray()
        # Mask
        mask = np.logical_and.reduce([data != val for val in mask_val])
        # Add non-zero to nobs
        nobs = nobs + mask
        # Close dataset
        src_ds = None
        if not QUIET:
            print 'Finished image {num}/{total}'.format(
                num=stacks.index(stack) + 1, total=len(stacks))

    # Write out nobs
    driver = gdal.GetDriverByName(format)
    dst_ds = driver.Create(output,
                         ex_ds.RasterXSize, ex_ds.RasterYSize, 1,
                         gdal_array.NumericTypeCodeToGDALTypeCode(dtype))
    if dst_ds is None:
        print 'Error: could not write to output file {f}'.format(f=output)
        sys.exit(1)
    dst_ds.GetRasterBand(1).WriteArray(nobs)
    dst_ds.SetProjection(ex_ds.GetProjection())
    dst_ds.SetGeoTransform(ex_ds.GetGeoTransform())

    # Close example and destination datasets
    ex_ds = None
    dst_ds = None


def main():
    """ 
    Handle input arguments and options before calling stack_nobs 
    """
    # Input image directory
    location = arguments['<location>']
    if not os.path.exists(location):
        print 'Error: stack directory does not exist'
        sys.exit(1)
    elif not os.path.isdir(location):
        print 'Error: stack directory arugment is not a directory'
        sys.exit(1)
    elif not os.access(location, os.R_OK):
        print 'Error: cannot read from input stack directory'
        sys.exit(1)
    
    # Output image
    output = arguments['<output>']
    if os.path.dirname(output) == '':
        output = './' + output
    if not os.access(os.path.dirname(output), os.W_OK):
        print 'Cannot write to output image {0}'.format(output)
        sys.exit(1)
    
    # Mask values
    mask_val = arguments['<maskvalues>']
    if len(mask_val) > 0:
        try:
            mask_val = map(int, mask_val)
        except ValueError:
            try:
                mask_val = map(float, mask_val)
            except ValueError:
                print 'Error: mask values must be numeric int or float'
                sys.exit(1)
    else:
        print "Warning: no mask values specified; only using NDV"

    # Image stack name pattern
    stkname = arguments['--name']
    if '*' not in stkname:
        print 'Warning: stack name pattern should have a wildcard.' \
                'Prepending one:'
        stkname = '*' + stkname
        print stkname
    
    # Image stack directory name pattern
    stkdir = arguments['--dname']
    if '*' not in stkdir:
        print 'Warning: stack directory name pattern should have a wildcard.' \
                'Appending one:'
        stkdir = stkdir + '*'
        print stkdir
    
    # Mask band
    mask_band = arguments['--mask']
    try:
        mask_band = int(mask_band)
    except ValueError:
        print 'Error: mask band number must be an integer'
        sys.exit(1)
    
    # Image no data value
    ndv = arguments['--ndv']
    try:
        ndv = int(ndv)
    except ValueError:
        try:
            ndv = float(ndv)
        except ValueError:
            print 'Error: no data value must be numeric int or float'
            sys.exit(1)
    mask_val.append(ndv)

    # File format
    format = arguments['--format']
    test_driver = gdal.GetDriverByName(format)
    if test_driver is None:
        print 'Error: could not create file with driver {0}'.format(format)
    test_driver = None

    gdal.AllRegister()

    stack_nobs(location, output, mask_val, mask_band, stkname, stkdir, format)

if __name__ == '__main__':
    arguments = docopt(__doc__)
    if arguments['--debug']:
        DEBUG = True
    if DEBUG:
        print arguments.keys()
        print arguments.values()
    main()
