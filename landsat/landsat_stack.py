#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: set expandtab:ts=4
###
#
# Author:               Chris Holden
# Date:                 5/21/2013
#
###
"""Stack Landsat Data

Usage: landsat_stack.py [options] (--max_extent | --min_extent |
    --extent=<extent> | --percentile=<pct> | --image=<image>) <location>

Options:
    -f --files=<files>...       Files to stack [default: lndsr.*.hdf *Fmask]
    -b --bands=<bands>...       Bands from files to stack [default: all]
    -d --dirs=<pattern>         Directory name pattern to search [default: L*]
    -o --output=<pattern>       Output filename pattern [default: *stack]
    -p --pickup                 Pickup / resume where left off
    -n --ndv=<ndv>              No data value [default: 0]
    -u --utm=<zone>             Force a UTM zone (in WGS84)
    -e --exit-on-warn           Exit on warning messages
    --format=<format>           GDAL format [default: ENVI]
    --co=<creation options>     GDAL creation options [default: None]
    -v --verbose                Show verbose debugging messages
    -q --quiet                  Be quiet by not showing warnings
    --dry-run                   Dry run - don't actually stack
    -h --help                   Show help

Examples:
    landsat_stack.py -vq -n "-9999; 255" -b "1 2 3 4 5 6 15; 1" --min_extent ./

"""
from __future__ import print_function

import copy
import fnmatch
import os
import sys

from docopt import docopt

import numpy as np

try:
    from osgeo import gdal
    from osgeo import osr
    from osgeo.gdalconst import GA_ReadOnly
except ImportError:
    import gdal
    from gdalconst import GA_ReadOnly


QUIET = False
VERBOSE = False
EXIT_ON_WARN = False
DRY_RUN = False

gdal.UseExceptions()
gdal.AllRegister()


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


def xy2geo(geo_transform, x, y):
    """ Returns the geo-referenced cooridnate of x, y pixel """
    geo_x = geo_transform[0] + geo_transform[1] * x + geo_transform[2] * y
    geo_y = geo_transform[3] + geo_transform[4] * x + geo_transform[5] * y

    return (geo_x, geo_y)


class LandsatImage():
    """
    A class for each Landsat image. Handles and stores information for
    stacking of Landsat images.
    """

    def __init__(self, directory, patterns, bands, no_data, out_pattern,
                 fformat='ENVI', dtype=gdal.GDT_Int16, co=['INTERLEAVE=BIP']):
        """
        Find images to be stacked

        Arguments:
            directory       Input image directory
            patterns        List of file name patterns
        """
        # Directory
        self.directory = directory
        # Folder name
        self.id = os.path.split(self.directory)[-1]
        # Images to stack
        self.images = []
        # Bands to stack for each image
        self.bands = []
        # Output filename for stack
        self.output_name = self.set_output_name(out_pattern)
        # Extent of images
        self.extent = { }
        # Size of image
        self.size = { }
        # Pixel size
        self.pixel_size = [None, None]
        # Projection
        self.projection = None
        # Geo-transfor
        self.geo_transform = { }
        # No data value
        self.no_data = no_data
        # File format
        self.format = fformat
        # Data type
        self.dtype = dtype
        # Creation options
        self.create_options = co
        if self.create_options and not isinstance(self.create_options, list):
            self.create_options = [self.create_options]

        if not os.path.isdir(self.directory):
            print('Error: {d} is not a directory.'.format(d=self.directory))
            sys.exit(1)
        if VERBOSE and not QUIET:
            print('<----------------------------------------')
            print('Directory: {d}'.format(d=self.directory))
            print('  Files:')

        files = os.listdir(self.directory)

        # Find image files according to patterns
        for num, pattern in enumerate(patterns):
            # Filter files by pattern
            matches = fnmatch.filter(files, pattern)
            # No matches
            if len(matches) == 0:
                print('Directory {d} has no files matching pattern: "{p}"'.
                      format(d=self.directory, p=pattern))
                sys.exit(1)
            else:
                if VERBOSE and not QUIET:
                    print('\t{i}'.format(i=matches[0]))
                # If we found match, add full path
                self.images.append(os.path.join(self.directory, matches[0]))

                # If we found image, add corresponding bands
                if bands[0] == ['all']:
                    self.bands.append(['all'])
                else:
                    self.bands.append(map(str2num, bands[num]))

        # Check for subdatasets; we want to add those instead
        self.check_sds(self.images, self.bands, self.no_data)
        # Initialize extent
        self.init_attributes()

    def __repr__(self):
        return 'Landsat ID: {id}'.format(id=self.id)

    def set_output_name(self, pattern):
        """ Assign an output name according to the image ID """
        if '*' in pattern:
            pattern = pattern.strip('*')
        return (os.path.join(self.directory, self.id + pattern))

    def check_completed(self, t_extent):
        """ Check if we've already produced a stacked image """
        if os.path.exists(self.output_name):
            # Try opening
            ds = gdal.Open(self.output_name)
            if ds is not None:
                gt = ds.GetGeoTransform()

                ul_x, ul_y = xy2geo(gt, 0, 0)
                lr_x, lr_y = xy2geo(gt, ds.RasterXSize, ds.RasterYSize)

                if t_extent == [ul_x, ul_y, lr_x, lr_y]:
                    return True
                else:
                    print('Already stacked {n}, but to different extent'.
                        format(n=self.output_name))
                    print('\tTarget: {t}'.format(t=t_extent))
                    print('\tPrevious: {p}'.format(p=[ul_x, ul_y, lr_x, lr_y]))
                    print('\n')
        return False

    def check_sds(self, images, bands, ndv):
        """
        Substitutes image, bands, & ndv for sub-datasets (useful for HDFs)

        Arguments:
            images          List of image filenames
            bands           List of lists containing bands for each filename
            ndv             List of lists containing ndv for each filename
        """
        ndv = copy.deepcopy(ndv)
        _images = []
        _bands = []
        _ndv = []

        for num, image in enumerate(images):
            # Open image
            ds = gdal.Open(image, GA_ReadOnly)
            if ds == None:
                print('Cannot open {i}'.format(i=image))
                sys.exit(1)

            sds = ds.GetSubDatasets()
            # Handle sub-datasets, if any
            if len(sds) > 0:
                # Add into _images and _bands each sub-dataset separately
                if bands[num] == ['all']:
                    # Add in all band numbers
                    bands[num] = range(1, len(sds) + 1)
                    ndv[num] = ndv[num] * len(sds)
                for b in bands[num]:
                    # Note: [b - 1] because GDAL starts on 1
                    _images.append(sds[b - 1][0])
                    _bands.append([1])
                for n in ndv[num]:
                    _ndv.append([n])
            else:
                # Just add image
                _images.append(image)
                if bands[num] == ['all']:
                    _bands.append(range(1, ds.RasterCount + 1))
                else:
                    _bands.append(bands[num])
                _ndv.append(ndv[num])
            # Close
            ds = None

        self.images = list(_images)
        self.bands = list(_bands)
        self.no_data = list(_ndv)

    def init_attributes(self):
        """
        Initalize image size, projection, geo-transform, and extent.

        Will allow for different geo-transforms and image sizes among the
        datasets. Will only warn user if projections are different among files,
        unless user specifies the --exit-on-warn flag.
        """

        for n, image in enumerate(self.images):
            # Open image dataset
            ds = gdal.Open(image, GA_ReadOnly)
            if ds == None:
                print('Cannot open {i}'.format(i=image))
                sys.exit(1)

            # Set size
            size = [ds.RasterXSize, ds.RasterYSize]
            if size[0] == 0 or size[1] == 0:
                print('Error: Image {i} has 0 rows or columns'.format(i=image))
                sys.exit(1)
            self.size[image] = size

            # Check projection
            projection = ds.GetProjection()
            if projection == '':
                if not QUIET:
                    print('Warning: Image {i} has no projection'.
                          format(i=image))
                if EXIT_ON_WARN:
                    sys.exit(1)
                else:
                    continue
            if self.projection == None and projection != '':
                self.projection = projection
            else:
                if projection != self.projection:
                    # Only raise warning because proj string could be slightly
                    # different but still mean the same thing
                    if not QUIET and not EXIT_ON_WARN:
                        print('Warning: Image {i} and image {b} have ' \
                              'different projections'.
                              format(i=image, b=self.images[0]))
                    if EXIT_ON_WARN:
                        print('Warning: Image {i} and image {b} have ' \
                              'different projections'.
                              format(i=image, b=self.images[0]))
                        sys.exit(1)

            # Get geo-transform
            geo_transform = ds.GetGeoTransform()
            if geo_transform == '':
                if n == 0:
                    print('Error: Image {i} has no geotransform and is first ' \
                          'image so we cannot assume same geotransform as ' \
                          'previous image'.format(i=image))
                elif not QUIET and not EXIT_ON_WARN:
                    print('Warning: Image {i} has no geotransform. Using' \
                          'geotransform from image{b}'.
                          format(i=image, b=self.images[n - 1]))
                if EXIT_ON_WARN:
                    print('Warning: Image {i} has no geotransform.'.
                          format(i=image))
                    sys.exit(1)
                else:
                    self.geo_transform[image] = None
            else:
                self.geo_transform[image] = geo_transform
                # Check pixel size
                if self.pixel_size == [None, None]:
                    self.pixel_size = [geo_transform[1], geo_transform[5]]
                if self.pixel_size != [geo_transform[1], geo_transform[5]]:
                    print('Error: pixel sizes of all images must be the same.')
                    sys.exit(1)
                # Check for rotation
                if geo_transform[2] != 0 or geo_transform[4] != 0:
                    print('Error: the geotransform of image {i} is rotated.' \
                          'This configuration is not supported'.
                          format(i=image))
                    sys.exit(1)

            # Find extent
            if geo_transform == '':
                # Assume extent from previous image if none exists
                self.extent[image] = self.extent[self.images[n - 1]]
                if not QUIET and not EXIT_ON_WARN:
                    print('Warning: Image {i} has no extent. Using' \
                          'extent from image {b}'.
                          format(i=image, b=self.images[n - 1]))
                else:
                    print('Warning: Image {i} has no extent'.format(i=image))
            else:
                ul_x, ul_y = xy2geo(geo_transform, 0, 0)
                lr_x, lr_y = xy2geo(geo_transform, ds.RasterXSize,
                                    ds.RasterYSize)
                self.extent[image] = [ul_x, ul_y, lr_x, lr_y]

            # Close
            ds = None

        # Check that all images have geo-transform and extent
        if not all(self.geo_transform) or not all(self.extent):
            print('Error: could not find or assume a geotransform or extent' \
                'for all images for {id}'.format(id=self.id))

    def stack_image(self, t_extent, utm=None):
        """
        Take self and output a 'stacked' image defined by the target extent
        (t_extent), named according to output_pattern.

        Notice: much of this code is graciously taken from gdal_merge.py
        """
        if VERBOSE:
            print('Target extent: {0}'.format(t_extent))
        # Parse target extent
        t_ul_x = t_extent[0]
        t_ul_y = t_extent[1]
        t_lr_x = t_extent[2]
        t_lr_y = t_extent[3]

        # Calculate the output image size
        x_size = int((t_lr_x - t_ul_x) / self.pixel_size[0] + 0.5)
        y_size = int((t_lr_y - t_ul_y) / self.pixel_size[1] + 0.5)
        if VERBOSE:
            print('Output size: x={x}, y={y}'.format(x=x_size, y=y_size))

        # Create driver
        driver = gdal.GetDriverByName(self.format)
        if driver is None:
            print('Could not create driver with format {f}.'.
                  format(f=self.format))
            return False

        # Create output dataset
        if self.create_options:
            out_ds = driver.Create(self.output_name, x_size, y_size,
                                   sum([len(_bands) for _bands in self.bands]),
                                   self.dtype, self.create_options)
        else:
            out_ds = driver.Create(self.output_name, x_size, y_size,
                                   sum([len(_bands) for _bands in self.bands]),
                                   self.dtype)
        if out_ds is None:
            print('Could not create file {f}'.format(f=self.output_name))
            return False

        # Define and set output geo transform
        out_geo_transform = [t_extent[0], self.pixel_size[0], 0,
                             t_extent[1], 0, self.pixel_size[1]]
        out_ds.SetGeoTransform(out_geo_transform)

        # Set projection from input, unless forced to a UTM zone
        if utm is None:
            out_ds.SetProjection(self.projection)
        else:
            sr = osr.SpatialReference()
            sr.SetUTM(utm)
            sr.SetWellKnownGeogCS('WGS84')
            out_ds.SetProjection(sr.ExportToWkt())

        if VERBOSE:
            print('Output projection: \n '\
                '\t\t{proj}'.format(proj=out_ds.GetProjection()))

        # Loop through list of images and stack
        out_band = 1
        for num, image in enumerate(self.images):
            # Find intersect region target window in geographic coordinates
            tw_ul_x = max(t_ul_x, self.extent[image][0])
            tw_lr_x = min(t_lr_x, self.extent[image][2])
            if self.geo_transform[image][5] < 0:
                # North
                tw_ul_y = min(t_ul_y, self.extent[image][1])
                tw_lr_y = max(t_lr_y, self.extent[image][3])
            elif self.geo_transform[image][5] > 0:
                # South
                tw_ul_y = max(t_ul_y, self.extent[image][1])
                tw_lr_y = min(t_lr_y, self.extent[image][3])
            else:
                print('Image has 0 y-pixel size')
                return False

            # Check for overlap
            if tw_ul_x >= tw_lr_x:
                print('Target and image extent do not overlap')
                return False
            if self.geo_transform[image][5] < 0 and tw_ul_y <= tw_lr_y:
                print('Target and image extent do not overlap')
                return False
            if self.geo_transform[image][5] > 0 and tw_ul_y >= tw_lr_y:
                print('Target and image extent do not overlap')
                return False

            # Calculate target window in pixel coordinates
            tw_xoff = int((tw_ul_x - t_extent[0]) /
                          self.geo_transform[image][1] + 0.1)
            tw_yoff = int((tw_ul_y - t_extent[1]) /
                          self.geo_transform[image][5] + 0.1)
            tw_xsize = int((tw_lr_x - t_extent[0]) /
                           self.geo_transform[image][1] + 0.5) - tw_xoff
            tw_ysize = int((tw_lr_y - t_extent[1]) /
                           self.geo_transform[image][5] + 0.5) - tw_yoff

            # Calculate source window in pixel coordinates
            sw_xoff = int((tw_ul_x - self.geo_transform[image][0]) /
                          self.geo_transform[image][1])
            sw_yoff = int((tw_ul_y - self.geo_transform[image][3]) /
                          self.geo_transform[image][5])
            sw_xsize = int((tw_lr_x - self.geo_transform[image][0]) /
                           self.geo_transform[image][1] + 0.5) - sw_xoff
            sw_ysize = int((tw_lr_y - self.geo_transform[image][3]) /
                           self.geo_transform[image][5] + 0.5) - sw_yoff

            if sw_xsize < 1 or sw_ysize < 1:
                print('Error: source window size less than 1 pixel')
                return False

            # Open image
            ds = gdal.Open(image, GA_ReadOnly)

            if ds is None:
                print('Could not open image {i}'.format(image))
                return False

            for nband, b in enumerate(self.bands[num]):
                # Open bands in input/output
                s_band = ds.GetRasterBand(b)
                t_band = out_ds.GetRasterBand(out_band)
                # Set no data value
                t_band.SetNoDataValue(self.no_data[num][nband])
                # Set description
                t_band.SetDescription(s_band.GetDescription())
                # Read in data
                data = s_band.ReadRaster(sw_xoff, sw_yoff, sw_xsize, sw_ysize,
                                         tw_xsize, tw_ysize, self.dtype)

                # Initialize the output target band with no_data
                t_band.Fill(self.no_data[num][nband])
                # Write data
                t_band.WriteRaster(tw_xoff, tw_yoff, tw_xsize, tw_ysize,
                                   data, tw_xsize, tw_ysize, self.dtype)
                out_band = out_band + 1

        print()

        # Close input and output datasets
        ds = None
        out_ds = None
        # Return successful
        return True


def get_directories(location, dir_pattern):
    """
    Search location for directories according to name pattern
    """
    stack_dirs = [os.path.join(location, d) for d in
                    fnmatch.filter(os.listdir(location), dir_pattern)
                    if os.path.isdir(os.path.join(location, d))]

    return stack_dirs


def get_max_extent(images):
    """
    Loop through LandsatImages finding the maximum extent of images
    """
    if VERBOSE:
        print('Finding maximum extent')

    # Extent - UL_x, UL_y, LR_x, LR_y
    extent = [None, None, None, None]
    for image in images:
        if VERBOSE:
            # Store last extent for update reporting purposes
            _extent = list(extent)

        # Collect max extent from all images for this LandsatImage
        image_extent = [
            min([e[0] for e in image.extent.values()]),
            max([e[1] for e in image.extent.values()]),
            max([e[2] for e in image.extent.values()]),
            min([e[3] for e in image.extent.values()])
        ]

       # Update extent as needed
        if extent[0] is None or image_extent[0] < extent[0]:
            extent[0] = image_extent[0]
        if extent[1] is None or image_extent[1] > extent[1]:
            extent[1] = image_extent[1]
        if extent[2] is None or image_extent[2] > extent[2]:
            extent[2] = image_extent[2]
        if extent[3] is None or image_extent[3] < extent[3]:
            extent[3] = image_extent[3]

        if VERBOSE:
            if _extent != extent:
                print('{img} updated maximum extent'.format(img=image))

    return copy.deepcopy(extent)


def get_min_extent(images):
    """
    Loop through LandsatImages finding the minimum extent of images
    """
    if VERBOSE:
        print('Finding minimum extent')

    # Extent - UL_x, UL_y, LR_x, LR_y
    extent = [None, None, None, None]
    for image in images:
        if VERBOSE:
            # Store last extent for update reporting purposes
            _extent = list(extent)

        # Collect min extent from all images for this LandsatImage
        image_extent = [
            max([e[0] for e in image.extent.values()]),
            min([e[1] for e in image.extent.values()]),
            min([e[2] for e in image.extent.values()]),
            max([e[3] for e in image.extent.values()])
        ]

        # Update extent as needed
        if extent[0] is None or image_extent[0] > extent[0]:
            extent[0] = image_extent[0]
        if extent[1] is None or image_extent[1] < extent[1]:
            extent[1] = image_extent[1]
        if extent[2] is None or image_extent[2] < extent[2]:
            extent[2] = image_extent[2]
        if extent[3] is None or image_extent[3] > extent[3]:
            extent[3] = image_extent[3]

        if VERBOSE:
            if _extent != extent:
                print('{img} updated minimum extent'.format(img=image))

    return copy.deepcopy(extent)


def get_percentile_extent(images, pct):
    """
    Loop through LandsatImages to find the <pct> percentile of min/max
    """
    if VERBOSE:
        print('Finding {0:.2f}% percentile extent'.format(pct))

    # TODO
    out_extent = [None, None, None, None]

    # Extent - UL_x, UL_y, LR_x, LR_y
    extent = np.array(images[0].extent.values())
    for image in images[1:]:
        extent = np.vstack((extent,
                            np.array(image.extent.values())))

    ### Now that we have all extents as np.array, find percentiles
    # Upper left X - (100 - pct) percentile
    i = np.abs(extent[:, 0] - np.percentile(extent[:, 0], 100 - pct)).argmin()
    out_extent[0] = extent[i, 0]

    # Upper left Y - pct percentile
    i = np.abs(extent[:, 1] - np.percentile(extent[:, 1], pct)).argmin()
    out_extent[1] = extent[i, 1]

    # Lower right X - pct percentile
    i = np.abs(extent[:, 2] - np.percentile(extent[:, 2], pct)).argmin()
    out_extent[2] = extent[i, 2]

    # Lower right Y - (100 - pct) percentile
    i = np.abs(extent[:, 3] - np.percentile(extent[:, 3], 100 - pct)).argmin()
    out_extent[3] = extent[i, 3]

    return copy.deepcopy(list(out_extent))


def get_extent_from_image(image):
    """ Returns extent coordinates from an image

    Args:
      image (str): filename of image to use

    Returns:
      extent (list): extent specified by upper left and lower right X/Y pairs

    """
    ds = gdal.Open(image, gdal.GA_ReadOnly)
    gt = ds.GetGeoTransform()
    ncol = ds.RasterXSize
    nrow = ds.RasterYSize

    ulx = gt[0]
    uly = gt[3]
    lrx = gt[0] + (ncol * gt[1]) + (nrow * gt[2])
    lry = gt[3] + (ncol * gt[4]) + (nrow * gt[5])

    return [ulx, uly, lrx, lry]


def landsat_stack(location, dir_pattern, image_pattern, out_pattern,
                  bands, ndv,
                  extent=None, max_extent=None, min_extent=None,
                  percentile=None, extent_image=None,
                  utm=None, resume=False,
                  fformat='ENVI', co='INTERLEAVE=BIP'):
    """ Performs stacking of Landsat data

    Arguments:
        location            Folder location of imagery
        dir_pattern         Pattern for folders containing each image
        image_pattern       Pattern for images. Patterns separated by ";"
        out_pattern         Pattern for output stack name
        bands               List of list of bands for each image
        ndv                 List of list of no data values for each image
        extent              [ULx, ULy, LRx, LRy] output extent
        max_extent          Option to calculate extent as maximum of all images
        min_extent          Option to calculate extent as minimum of all images
        percentile          Option to calculate extent as percentile of
                                maximum extent of all images
        extent_image        Option to use the extent of a specified image as
                                the extent of all images
        utm                 UTM zone (WGS84) to assign to output image
        resume              Option to resume by skipping already stacked images
        fformat             GDAL file format
        co                  GDAL format creation options

    Example:
        landsat_stack('./', 'L*', 'lndsr*hdf; L*Fmask', '*_stack',
            [[1, 2, 3, 4, 5, 15], ['all']], [[-9999], [255]],
            min_extent=True, resume=True)
    """
    ### Check that we provided at least 1 extent option
    extent_opt = 0
    for opt in [extent, max_extent, min_extent, percentile, extent_image]:
        if opt is not None and opt is not False:
            extent_opt = extent_opt + 1
    if extent_opt == 0:
        print('Must specifiy at least one extent option.')
        return 1
    elif extent_opt > 1:
        print('Must specify only one extent option')
        return 1
    if extent is not None:
        if len(extent) != 4:
            print('Error: extent option must have 4 values (UL XY, LR XY)')
            return 1

    ### Process stacks
    gdal.AllRegister()
    # Locate folders
    dirs = get_directories(location, dir_pattern)
    if len(dirs) == 0:
        print('Could not find any Landsat images to stack')
    else:
        print('Found {num} Landsat images to stack.'.format(num=len(dirs)))

    # For each folder, initialize a LandsatImage object
    images = []
    for d in dirs:
        images.append(LandsatImage(d, image_pattern, bands, ndv, out_pattern,
                                   fformat=fformat, co=co))
        sys.stdout.flush()
    if len(images) != len(dirs) or any([i == False for i in images]):
        print('Could not find Landsat data for all image directories')
        return 1

    # If 'max_extent' option, loop through directories getting maximum extent
    if max_extent:
        extent = get_max_extent(images)
    elif min_extent:
        extent = get_min_extent(images)
    elif percentile:
        extent = get_percentile_extent(images, percentile)
    elif extent_image:
        extent = get_extent_from_image(extent_image)

    print('\nStacking to extent:')
    print('\tUpper Left: {ulx},{uly}'.format(ulx=extent[0], uly=extent[1]))
    print('\tLower Right: {lrx},{lry}'.format(lrx=extent[2], lry=extent[3]))

    # Go through images, apply some attribute and stack
    print('\nStacking images:')
    stack_status = []
    sys.stdout.flush()
    for num, image in enumerate(images):
        print('<--------------- {i} / {t} '.format(i=num + 1, t=len(images)))
        print('Stacking:\n {n}\n'.format(n=image.output_name))

        if resume and image.check_completed(extent):
            if VERBOSE and not QUIET:
                print('Already stacked...')
        else:
            if not DRY_RUN:
                stack_status.append(image.stack_image(extent, utm))
            else:
                stack_status.append(True)
        sys.stdout.flush()

    print('\n\n --------------- REPORT --------------- \n\n')
    # Check for errors and report
    if not all(stack_status):
        failures = [num for num, s in enumerate(stack_status) if s == False]
        print('Could not stack {f} images:'.format(f=len(failures)))
        for f in failures:
            print('\t{i}'.format(i=images[f]))
        return 1
    else:
        # Check to make sure geo-transform was applied & extent is correct
        success = [image.check_completed(extent) for image in images]
        if all(success):
            print('Stacking completed successfully')
            return 0
        else:
            print('Not all stacks have same extent:')
            for n, s in enumerate(success):
                if s != True:
                    print('\t{i}'.format(i=images[n].id))
            return 1


def main():
    """ Handle input arugments and pass to landsat_stack function """
    # Extent
    max_extent = arguments['--max_extent']
    min_extent = arguments['--min_extent']
    extent = arguments['--extent']
    if extent is not None:
        # Test 4 coordinates given
        extent = extent.replace(',', ' ').split(' ')
        extent = [_e for _e in extent if _e != '']
        if len(extent) != 4:
            print('Error: must specify 4 coordinates (ULx, ULy, LRx, LRy)')
            return 1
        try:
            extent = map(float, extent)
        except ValueError:
            print('Error: could not convert extent coordinates to float')
            return 1

    percentile = arguments['--percentile']
    if percentile is not None:
        try:
            percentile = float(arguments['--percentile'])
        except:
            print('Error: percentile must be a number')
            sys.exit(1)
        if percentile < 0 or percentile > 100:
            print('Error: percentile must be between 0 - 100')
            sys.exit(1)

    extent_image = arguments['--image']
    if extent_image:
        try:
            gdal.Open(extent_image)
        except:
            print('Error: cannot open image specifid in --image')
            return 1

    # Input image directory
    location = arguments['<location>']
    if os.path.islink(location):
        location = os.readlink(location)
    if not os.path.exists(location):
        print('Error: stack directory does not exist')
        return 1
    elif not os.path.isdir(location):
        print('Error: stack directory arugment is not a directory')
        return 1
    elif not os.access(location, os.R_OK):
        print('Error: cannot read from input stack directory')
        return 1

    # File name pattern
    image_pattern = arguments['--files'].replace(';', ' ').split(' ')
    image_pattern = [p for p in image_pattern if p != '']

    # Bands to stack - images split by ";". bands within image by "," or " "
    bands = arguments['--bands'].split(';')
    bands = [b.replace(',', ' ').split(' ') for b in bands]
    if len(bands) != len(image_pattern):
        if bands[0] == ['all']:
            bands = bands * len(image_pattern)
        else:
            print('Error: must specify bands for all image patterns')
            return 1
    if bands[0] != ['all']:
        bands = parse_nested_input(bands)

    # Directory pattern
    dir_pattern = arguments['--dirs']
    # Output pattern
    out_pattern = arguments['--output']

    # No data value
    ndv = arguments['--ndv'].split(';')
    ndv = [[_n for _n in n.replace(',', ' ').split(' ') if _n != '']
            for n in ndv]
    if len(ndv) != len(image_pattern):
        if not QUIET:
            print('Warning: using same NoDataValue for all images')
        ndv = ndv * len(image_pattern)
    for i in range(len(ndv)):
        if len(ndv[i]) != len(bands[i]):
            # If only 1 NDV specified we can try just using same value
            if len(ndv[i]) == 1:
                if not QUIET:
                    print('Warning: using the same NoDataValue for all bands')
                ndv = [n * len(bands[i]) for i, n in enumerate(ndv)]
            else:
                print(ndv[i])
                print('Error: must specify NoDataValue for each band')
                return 1
    ndv = parse_nested_input(ndv)

    # Force a UTM zone
    utm = arguments['--utm']
    if utm is not None:
        utm = str2num(utm)

    # Pickup/resume feature
    resume = arguments['--pickup']

    # GDAL format
    fformat = arguments['--format']
    try:
        driver = gdal.GetDriverByName(fformat)
    except:
        print('Error - unknown GDAL format')
        raise

    # Creation options
    creation_opts = arguments['--co']
    if creation_opts == 'None':
        creation_opts = None

    # Now that we've parsed input, perform stacking
    return(landsat_stack(location, dir_pattern, image_pattern, out_pattern,
                         bands, ndv,
                         extent, max_extent, min_extent, percentile,
                         extent_image,
                         utm, resume, fformat, creation_opts))

if __name__ == '__main__':
    arguments = docopt(__doc__)

    if arguments['--verbose']:
        VERBOSE = True
    if arguments['--quiet']:
        QUIET = True
    if arguments['--exit-on-warn']:
        EXIT_ON_WARN = True
    if arguments['--dry-run']:
        DRY_RUN = True

    sys.exit(main())
