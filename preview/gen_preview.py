#!/usr/bin/env python
""" Generate preview image

Usage:
    gen_preview.py [options] (--linear_pct <pct> | --histeq | --manual <minmax>) \n\t<input> <output>

Options:
    -b --bands <bands>              Bands for output image [default: 3 2 1]
    --mask <mask>                   Mask band [default: 8]
    --maskval <value>...            Mask band value [default: 2 3 4]
    --maskcol <r, g, b>             Mask color [default: 0, 0, 0]
    --ndv <value>                   No data value [default: 255]
    --threshold <percent>           Min unmasked data for output [default: 0]
    --srcwin <x y xsize ysize>      Window (in pixels) to subset
    --projwin <ulx uly lrx lry>     Window (in projected coordinates) to subset
    --resize_pct <pct>              Image resize percent [default: 100]
    --resize_method <method>        Image resize method [default: antialias]
    --format <format>               Output format [default: JPEG]
    -v --verbose                    Print (verbose) debugging messages
    -q --quiet                      Do not print except for warnings/errors
    -h --help                       Show help
"""
from __future__ import division, print_function

import os
import sys
import tempfile

from docopt import docopt

import Image
import numpy as np
import scipy.misc
import scipy.ndimage

try:
    from osgeo import gdal
    from osgeo import gdal_array
except:
    import gdal
    import gdal_array

VERBOSE = False
QUIET = False

def str2num(string):
    """ String representation of number to int/float utility function """
    try:
        num = int(string)
    except ValueError:
        num = float(string)
    return num

def parse_nested_input(t):
    """ Utility function for parsing of nested inputs (e.g. ndv, bands)"""
    if isinstance(t, list):
        return [parse_nested_input(s) for s in t if s != '']
    else:
        return str2num(t)

def proj2src_win(geotrans, projwin):
    """ 
    Utility function for converting projection window to source window
    """
    xoff = int((projwin[0] - geotrans[0]) / geotrans[1] + 0.001)
    yoff = int((projwin[1] - geotrans[3]) / geotrans[5] + 0.001)
    xsize = int((projwin[2] - projwin[0]) / geotrans[1] + 0.5)
    ysize = int((projwin[3] - projwin[1]) / geotrans[5] + 0.5)

    return [xoff, yoff, xsize, ysize]

def src2proj_win(geotrans, srcwin):
    """ 
    Utility function for converting source window to projection window
    """
    ulx = geotrans[0] + geotrans[1] * srcwin[0] + geotrans[2] * srcwin[1]
    uly = geotrans[3] + geotrans[4] * srcwin[0] + geotrans[5] * srcwin[1]
    lrx = geotrans[0] + geotrans[1] * (srcwin[0] + srcwin[2]) + \
        geotrans[2] * (srcwin[1] + srcwin[3])
    lry = geotrans[3] + geotrans[4] * (srcwin[0] + srcwin[2]) + \
        geotrans[5] * (srcwin[1] + srcwin[3])

    return [ulx, uly, lrx, lry]

def resize_img(img, resize_pct, method='NEAREST', quiet=True):
    """ Rescale image by resize_pct percent

    Note: PIL only works with np.uint8
    """
    # NOTE: For m columns and n rows:
    #   np.shape -> (n, m) -> height, width -> rows, cols
    #   Image.size  -> (m, n) -> width, height -> cols, rows
    # Calculate new sizes
    cols = int(img.shape[1] * resize_pct)
    rows = int(img.shape[0] * resize_pct)

    if VERBOSE is True and quiet is False:
        print('Output image is ' + str(rows) + 'x' + str(cols))

    if method == 'NEAREST':
        method = Image.NEAREST
    elif method == 'BILINEAR':
        method = Image.BILINEAR
    elif method == 'BICUBIC':
        method = Image.BILINEAR
    elif method == 'ANTIALIAS':
        method = Image.ANTIALIAS

    img_PIL = scipy.misc.toimage(img)
    img_PIL = img_PIL.resize((cols, rows), method)
    img = np.asarray(img_PIL)
    img_PIL = None

    return img

def linear_pct(image, pct=None, minmax=None):
    """
    #TODO 

    Linear percent stretch
    """
    raise NotImplementedError

def histeq(image, pct=None, minmax=None):
    """
    #TODO

    Histogram equalization
    Reference:
        http://www.janeriksolem.net/2009/06/histogram-equalization-with-python-and.html
    """
    nbr_bins = 256
    ### Get image histogram
    # Do differently for numpy.ndimage vs masked array
    imhist, bins = np.histogram(image.flatten(), nbr_bins, density=True)

    cdf = imhist.cumsum() # cumulative distribution function
    cdf = 255 * cdf / cdf[-1] # normalize

    # Use linear interpolation of cdf to find new pixel values
    img2 = np.interp(image.flatten(), bins[:-1], cdf)
    img2 = img2.reshape(image.shape)

    # Deal with possible mask
    return(img2)

def manual(image, pct=None, minmax=None, out_datatype='uint8'):
    """ Manual scaling of image from minmax to range of datatype specified """
    # Get output datatype as np & GDAL
    try:
        np_dt = np.dtype(out_datatype.lower())
        gdal_dt = gdal.GetDataTypeByName(out_datatype)
    except:
        print('Error: could not understand datatype {dt}'.
              format(dt=out_datatype))
        sys.exit(1)

    # Get data type min/max
    try:
        dt_max = np.iinfo(np_dt).max
        dt_min = np.iinfo(np_dt).min
    except:
        dt_max = np.finfo(np_dt).max
        dt_min = np.finfo(np.dt).min

    # Calculate scale factor & offset
    scale = (dt_max - dt_min) / (minmax[1] - minmax[0])
    offset = dt_max - (scale * minmax[1])

    return image * scale + offset


def clean_temp_file(temp):
    """ Delete temporary ENVI file """
    if os.path.isfile(temp):
        os.remove(temp)
    if os.path.isfile(temp + '.hdr'):
        os.remove(temp + '.hdr')

def gen_preview(input, output, bands, 
                maskband, maskvals, ndv, 
                maskcol, threshold,
                stretch, pct, minmax, 
                srcwin, projwin, 
                resize_pct, method,
                format):
    """
    #TODO
    """
    #### Read in image
    in_ds = gdal.Open(input, gdal.GA_ReadOnly)
    if in_ds is None:
        print('Error: Could not open input image')
        sys.exit(1)
    # Check if input bands are in image
    if max(bands) > in_ds.RasterCount:
        print('Error: Bands do not exist in image')
        sys.exit(1)
    # Check if maskband is in image
    if maskband > in_ds.RasterCount:
        print('Error: Mask band does not exist in image ({m} of {b})'.
              format(m=maskband, b=in_ds.RasterCount))
        sys.exit(1)

    # Read in input image geo_transform, nrows, ncols
    in_geotrans = in_ds.GetGeoTransform()
    in_xsize = in_ds.RasterXSize
    in_ysize = in_ds.RasterYSize

    # If in projection window, convert to window in pixels
    if projwin is not None:
        srcwin = proj2src_win(in_geotrans, projwin)
        if not QUIET:
            print('Computer --srcwin "{xoff}, {yoff}, {xsize}, {ysize}" ' \
                  'from projected window'.
                  format(xoff=srcwin[0], yoff=srcwin[1],
                         xsize=srcwin[2], ysize=srcwin[3]))
    # If user didn't provide a subset, use entire image
    if srcwin is None:
        srcwin = [0, 0, in_xsize, in_ysize]

    # Check for raster size
    if srcwin[2] <= 0 or srcwin[3] <= 0:
        print('Error: Computer --srcwin "{xoff}, {yoff}, {xsize}, {ysize}" ' \
            'has a negative width and/or height'.
                format(xoff=srcwin[0], yoff=srcwin[1], 
                       xsize=srcwin[2], ysize=srcwin[3]))
        sys.exit(1)

    # Check that source window is in image
    if srcwin[0] < 0 or srcwin[1] < 0 or \
        (srcwin[0] + srcwin[2] > in_xsize) or \
        (srcwin[1] + srcwin[3] > in_ysize):
        print('Error: Computer --srcwin "{xoff}, {yoff}, {xsize}, {ysize}" ' \
            'has a negative width and/or height'.
                format(xoff=srcwin[0], yoff=srcwin[1],
                       xsize=srcwin[2], ysize=srcwin[3]))
        sys.exit(1)

    # Calculate output image size and resolution
    out_xsize = int(srcwin[2] * resize_pct)
    out_ysize = int(srcwin[3] * resize_pct)
    out_px_size = in_geotrans[1] / (out_xsize / srcwin[2])
    out_py_size = in_geotrans[5] / (out_ysize / srcwin[3])

    # Initialize output as temp file (since create not available for JPEG)
    tf = tempfile.NamedTemporaryFile()
    
    driver = gdal.GetDriverByName('ENVI')
    out_ds = driver.Create(tf.name, out_xsize, out_ysize, 3, gdal.GDT_Byte)
    if out_ds is None:
        print('Error: could not initialize output file')
        sys.exit(1)

    # If mask exists, read it in
    if maskband is not None:
        mask = in_ds.GetRasterBand(maskband).ReadAsArray(
                    srcwin[0], srcwin[1], srcwin[2], srcwin[3])

    # Iterate through selected bands
    for n, inband in enumerate(bands):
        # Read in image
        image = in_ds.GetRasterBand(inband).ReadAsArray(
                    srcwin[0], srcwin[1], srcwin[2], srcwin[3])
        
        # Mask image for mask values and NDV
#        image_mask = np.zeros_like(image).astype(np.uint8)
        image_mask = ((image > 10000) | 
                      (image < 0) | 
                      (image == ndv[n])).astype(np.uint8)
        if maskband is not None:
            for maskval in maskvals:
                image_mask = np.logical_or(image_mask == 1, mask == maskval)
        image_mask = image_mask.astype(np.uint8)

        image = np.ma.masked_equal(image, ndv[n], copy=False)

        # If image does not have at least the threshold percent, skip output
        unmasked = ((image_mask == 0) & (image.mask == 0)).sum() / \
                image.size * 100
        if unmasked < threshold:
            print('Percent of unmasked image ({um}%) did not exceed required' \
                  ' threshold ({t}%). Exiting.'.
                  format(um=unmasked, t=threshold))
            # clean_temp_file(tempfile)
            sys.exit(2)

        # Do scaling according to function in argument
        image = stretch(image * (image_mask == 0), pct,
                        minmax[n]).astype(np.uint8)

        # Resize raster if needed
        if resize_pct != 1:
            image = resize_img(image, resize_pct, method)
            image_mask = resize_img(image_mask, resize_pct, 'NEAREST')
    
        # Apply image mask
        image = image * (image_mask == 0) + image_mask * maskcol[n]

        # Write output (n + 1 since we're using enumerate => 0 index)
        out_band = out_ds.GetRasterBand(n + 1)
        out_band.SetNoDataValue(0)
        out_band.WriteArray(image, 0, 0)
        out_band.FlushCache()

    out_geotrans = [0, 0, 0, 0, 0, 0]
    # Calculate new geotransform if we used subset
    if srcwin[0] != 0 and srcwin[1] != 0 and \
        srcwin[2] != in_ds.RasterXSize and srcwin[3] != in_ds.RasterYSize:
        projwin = src2proj_win(in_ds.GetGeoTransform(), srcwin)
        # Recalculate
        out_geotrans[0] = projwin[0]        # UL x
        out_geotrans[1] = out_px_size    # W-E pixel resolution
        out_geotrans[2] = in_geotrans[2]    # rotation
        out_geotrans[3] = projwin[1]        # UL y
        out_geotrans[4] = in_geotrans[4]    # rotation
        out_geotrans[5] = out_py_size    # N-S pixel resolution
    else:
        out_geotrans = in_ds.GetGeoTransform()

    # Set projection and geotransform
    out_ds.SetGeoTransform(out_geotrans)
    out_ds.SetProjection(in_ds.GetProjection())

    # Create copy of dataset in format
    gdal.GetDriverByName(format).CreateCopy(output, out_ds, 0)
    
#    clean_temp_file(tempfile)

    # Clear datasets
    in_ds = None
    out_ds = None

    if VERBOSE:
        print('Percent of unmasked image: {um}%'.format(um=unmasked))

def main():
    """ Handle input and pass to gen_preview function """
    # Constrast stretch and options
    stretch = None
    pct = None
    minmax = [None, None, None]
    if arguments['--linear_pct']:
        stretch = linear_pct
        pct = str2num(arguments['<pct>'])
    elif arguments['--histeq']:
        stretch = histeq
    elif arguments['--manual']:
        stretch = manual
        minmax = arguments['<minmax>'].split(';')
        minmax = [m.replace(', ', ' ').split(' ') for m in minmax]
        if len(minmax) != 3:
            if len(minmax) == 1:
                minmax = minmax * 3
            else:
                print('Error: min-max must be 2 values for all bands or 2' \
                      'values for each band')
                sys.exit(1)
        minmax = parse_nested_input(minmax)

    # Input file
    input = os.path.abspath(arguments['<input>'])
    if os.path.islink(input):
        input = os.readlink(input)
    if not os.path.exists(input):
        print('Error: input image does not exist.')
        sys.exit(1)
    elif not os.path.isfile(input):
        print('Error: input image is not a file')
        sys.exit(1)
    elif not os.access(input, os.R_OK):
        print('Error: input image is not readable')
        sys.exit(1)
    
    # Output file
    output = os.path.abspath(arguments['<output>'])
    if os.path.islink(output):
        input = os.readlink(output)
    if not os.access(os.path.dirname(output), os.W_OK):
        print('Error: output image directory is not writeable')
        sys.exit(1)

    # Input image bands
    bands = arguments['--bands']
    if bands is None:
        print('Warning: using bands 3, 2, 1 as R, G, B')
        bands = [3, 2, 1]
    else:
        bands = [str2num(b) for b in 
                    bands.replace(', ', ' ').split(' ')]
    
    # Input mask / mask value
    if arguments['--mask'] == 'None':
        maskband = None
        maskval = None
    else:
        maskband = str2num(arguments['--mask'])
        maskval = arguments['--maskval']
        if maskval is None:
            print('Warning: using default mask value of 0')
            maskval = 0
        else:
            maskval = [str2num(mv) for mv in 
                       maskval.replace(', ', ' ').split(' ')]

    # Mask color
    maskcol = arguments['--maskcol']
    try:
        maskcol = [int(c) for c in maskcol.replace(', ', ' ').split(' ')]
    except ValueError:
        print('Error: mask color choice must be integers')
        sys.exit(1)
    except:
        print('Error: cannot understand mask color choice')
        sys.exit(1)
    if len(maskcol) != 3:
        print('Error: must specify three mask colors (RGB)')
        sys.exit(1)
    if any([c > 255 or c < 0 for c in maskcol]):
        print('Error: mask colors must be 0 - 255')
        sys.exit(1)

    # NoDataValue
    ndv = arguments['--ndv']
    if ndv is None:
        print('Warning: using default NDV of 0')
        ndv = [0, 0, 0]
    else:
        ndv = [str2num(n) for n in ndv.replace(', ', ' ').split(' ')]
        if len(ndv) != 3:
            ndv = ndv * 3

    # Threshold for percent of image masked to not produce image
    threshold = str2num(arguments['--threshold'])
    
    # Source or projection window
    srcwin = arguments['--srcwin']
    projwin = arguments['--projwin']
    if srcwin is not None and projwin is not None:
        print('Error: must specify either projection or source window')
        sys.exit(1)
    if srcwin is not None:
        srcwin = [str2num(n) for n in srcwin.replace(', ', ' ').split(' ')]
        if len(srcwin) != 4:
            print('Error: --srcwin option must specify 4 values')
            print(__doc__)
            sys.exit(1)
    elif projwin is not None:
        projwin = [str2num(n) for n in projwin.replace(', ', ' ').split(' ')]
        if len(projwin) != 4:
            print('Error: --projwin option must specify 4 values')
            print(__doc__)
            sys.exit(1)

    # Resize percentage
    resize_pct = arguments['--resize_pct']
    try:
        resize_pct = float(resize_pct)
    except:
        print('Error: resize percent must be a number [0 - 100]')
        print(__doc__)
        sys.exit(1)
    if resize_pct <= 0 or resize_pct > 100:
        print('Error: resize percent must be between 0 - 100')
        print(__doc__)
        sys.exit(1)
    resize_pct = resize_pct / 100.0

    method = arguments['--resize_method']
    if method.upper() not in ['NEAREST', 'BILINEAR', 'BICUBIC', 'ANTIALIAS']:
        print('Error: unknown resize method - {m}'.format(m=method))
        print(__doc__)
        sys.exit(1)
    method = method.upper()

    # Parse output format
    format = arguments['--format']
    test_ds = gdal.GetDriverByName(format)
    if test_ds is None:
        print('Error: could not create a driver with {f} \
              format'.format(f=format))
        sys.exit(1)
    test_ds = None

    # Register all GDAL drivers
    gdal.AllRegister()

    # Exit with return code of gen_preview
    sys.exit(gen_preview(input, output, bands, 
                maskband, maskval, ndv, 
                maskcol, threshold,
                stretch, pct, minmax,
                srcwin, projwin, 
                resize_pct, method,
                format))

if __name__ == '__main__':
    arguments = docopt(__doc__)
    if arguments['--verbose']:
        VERBOSE = True
    if arguments['--quiet']:
        QUIET = True
    main()
