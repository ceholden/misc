#!/usr/bin/env python
#$ -V
#$ -l h_rt=24:00:00
#$ -N create_BGW
#$ -j y

import fnmatch
import os
import re
import sys

from osgeo import gdal
from osgeo import gdal_array
import numpy as np

gdal.AllRegister()
gdal.UseExceptions()

unbuffered = os.fdopen(sys.stdout.fileno(), 'w', 0)
sys.stdout = unbuffered

def find_stacks(location, dirpattern='L*', stackpattern='L*stack', ignore=['TSFitMap']):

    if type(ignore) == str:
        ignore = [ignore]

    assert type(ignore) == list, 'Ignore list must be a list'

    dirs = []
    stacks = []

    # Populate - only checking one directory down
    location = location.rstrip(os.path.sep)
    num_sep = location.count(os.path.sep)
    for root, dnames, fnames in os.walk(location, followlinks=True):

        # Ignore result folder
        dnames[:] = [d for d in dnames for ig in ignore if ig not in d]

        # Force only 1 level
        num_sep_this = root.count(os.path.sep)
        if num_sep + 1 <= num_sep_this:
            del dnames[:]

        for dname in fnmatch.filter(dnames, dirpattern):
            dirs.append(dname)
        for fname in fnmatch.filter(fnames, stackpattern):
            stacks.append(os.path.join(root, fname))

    assert len(dirs) == len(stacks), \
        'Number of stacks and folders found differ ({s} vs {f})'.format(
            s=len(stacks), f=len(dirs))

    dirs, stacks = (list(t) for t in zip(*sorted(zip(dirs, stacks))))

    return (dirs, stacks)

def calc_BGW(image_fn, output, fformat='GTiff', 
        bands=np.arange(6) + 1, ndv=-9999):
    
    assert min(bands) > 0, 'Bands specified must be above 0 (1 indexed)'

    # TM reflectance tasseled cap coefficients
    refW = np.array([0.0315, 0.2021, 0.3102, 0.1954, -0.6806, -0.6109])
    refG = np.array([-0.1603, -0.2189, -0.4934, 0.7940, -0.0002, -0.1446])
    refB = np.array([0.2043, 0.4158, 0.5524, 0.5741, 0.3124, 0.2330])

    bgw = ['TC brightness', 'TC greenness', 'TC wetness']
    
    # Open input image
    image_ds = gdal.Open(image_fn, gdal.GA_ReadOnly)

    n_band = bands.size + 3

    image = np.zeros((image_ds.RasterYSize, image_ds.RasterXSize, n_band),
                    dtype=gdal_array.GDALTypeCodeToNumericTypeCode(
                        image_ds.GetRasterBand(1).DataType))

    for i, b in enumerate(bands):
        image[:, :, i] = image_ds.GetRasterBand(b).ReadAsArray()

    test = image[2500:3000, 2500:3000, :]

    from IPython.core.debugger import Pdb
    Pdb().set_trace()

    image[:, :, bands.size] = np.tensordot(image, refB, axis=(2, 0))
    image[:, :, bands.size + 1] = np.tensordot(image, refG, axis=(2, 0))
    image[:, :, bands.size + 2] = np.tensordot(image, refW, axis=(2, 0))

    from IPython.core.debugger import Pdb
    Pdb().set_trace()

    # Init BGW
#     BGW = np.zeros((image_ds.RasterYSize, image_ds.RasterXSize, 3), 
#         dtype=gdal_array.GDALTypeCodeToNumericTypeCode(
#             image_ds.GetRasterBand(1).DataType))
# 
#     # Init mask
#     mask = np.ones((image_ds.RasterYSize, image_ds.RasterXSize), dtype=np.uint8)
# 
#     # Loop through bands calculating BGW
#     for i, b in enumerate(bands):
#         # Open band
#         band = image_ds.GetRasterBand(b).ReadAsArray()
# 
#         # Calculate BGW
#         BGW[:, :, 0] = BGW[:, :, 0] + band * refB[i]
#         BGW[:, :, 1] = BGW[:, :, 1] + band * refG[i]
#         BGW[:, :, 2] = BGW[:, :, 2] + band * refW[i]
# 
#         # Update mask
#         mask = np.logical_and(mask == 1, band != ndv).astype(np.uint8)

    # Apply mask
    masked = (mask == 0)
    for b in range(BGW.shape[2]):
        BGW[mask == 0, b] = ndv

    # Setup for output
    driver = gdal.GetDriverByName(fformat)

    out_ds = driver.Create(output, 
        image_ds.RasterXSize, image_ds.RasterYSize, 3,
        image_ds.GetRasterBand(1).DataType)

    for b in range(BGW.shape[2]):
        out_ds.GetRasterBand(b + 1).WriteArray(BGW[:, :, b])
        out_ds.GetRasterBand(b + 1).SetNoDataValue(ndv)
        out_ds.GetRasterBand(b + 1).SetDescription(bgw[b])

    out_ds.SetProjection(image_ds.GetProjection())
    out_ds.SetGeoTransform(image_ds.GetGeoTransform())

    out_ds = None

here = '/projectnb/landsat/projects/CMS/stacks/Mexico/p022r049/images'

dirs, stacks = find_stacks(here)

n = len(dirs)

print 'Creating BGW images'
for i, (d, s) in enumerate(zip(dirs, stacks)):
    
    if 'LC8' in s:
        continue

    dirname = os.path.dirname(s)

    out_fn = os.path.join(dirname, d + '_BGW.bsq')

    print '{i} / {n} - {name}'.format(i=i, n=n, name=d)
    print '    writing to {f}'.format(f=out_fn)

    calc_BGW(s, out_fn, fformat='ENVI')
