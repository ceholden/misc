#!/usr/bin/env python
from __future__ import division, print_function

import logging
import sys

import click
import numexpr as ne
import numpy as np
from osgeo import gdal, gdal_array

__version__ = '0.1.0'

FORMAT = '%(asctime)s:%(levelname)s:%(module)s.%(funcName)s:%(message)s'
logging.basicConfig(format=FORMAT, level=logging.INFO, datefmt='%H:%M:%S')
logger = logging.getLogger('stretches')

gdal.UseExceptions()
gdal.AllRegister()

_np_dtypes = ['uint8', 'uint16', 'int16', 'uint32', 'int32',
             'float32', 'float64']
_stretches = ['linear', 'percent', 'histeq']


# Scaling functions
def _linear(arr, minmax=(0, 255), ndv=None, dtype=np.uint8, **kwargs):
    """ Performs linear min/max scaling on an array

    Args:
      arr (np.ndarray): array to scale
      minmax (tuple, optional): minimum and maximum values to scale into
        (default: 0, 255)
      ndv (int, float, or iterable, optional): one or more NoDataValue(s)
        (default: None)
      dtype (np.dtype, optional): NumPy datatype to return (default: np.uint8)

    Returns:
      np.ndarray: scaled NumPy array

    """
    if isinstance(ndv, (int, float)):
        ndv = [ndv]

    if ndv:
        mask = ~np.in1d(arr, ndv).reshape(arr.shape)
        _min, _max = arr[mask].min(), arr[mask].max()
    else:
        _min, _max = arr.min(), arr.max()

    arr[arr >= _max] = _max
    arr[arr <= _min] = _min

    scale = (_max - _min) / (minmax[1] - minmax[0])
    offset = _max - (scale * minmax[1])

    return ne.evaluate('arr * scale + offset').astype(dtype)


def _linear_pct(arr, percent=2, minmax=(0, 255), ndv=None, dtype=np.uint8,
                **kwargs):
    """ Performs linear percent scaling on an array

    Args:
      arr (np.ndarray): array to scale
      percent (float, optional): percent to scale (default: 2)
      minmax (tuple): minimum and maximum values to scale into
        (default: 0, 255)
      ndv (int, float, or iterable): one or more NoDataValue(s) (default: None)
      dtype (np.dtype, optional): NumPy datatype to return (default: np.uint8)

    Returns:
      np.ndarray: scaled NumPy array

    """
    if isinstance(ndv, (int, float)):
        ndv = [ndv]

    if ndv:
        mask = ~np.in1d(arr, ndv).reshape(arr.shape)
        _min, _max = (np.percentile(arr[mask], percent),
                      np.percentile(arr[mask], 100 - percent))
    else:
        _min, _max = (np.percentile(arr, percent),
                      np.percentile(arr, 100 - percent))

    arr[arr >= _max] = _max
    arr[arr <= _min] = _min

    scale = (minmax[1] - minmax[0]) / (_max - _min)
    offset = minmax[1] - (scale * _max)

    return ne.evaluate('arr * scale + offset').astype(dtype)


def _histeq(arr, minmax=(0, 255), ndv=None, dtype=np.uint8, **kwargs):
    """ Performs histogram equalization scaling on an array

    Reference:
        http://www.janeriksolem.net/2009/06/histogram-equalization-with-python-and.html

    Args:
      arr (np.ndarray): array to scale
      minmax (tuple): minimum and maximum values to scale into
        (default: 0, 255)
      ndv (int, float, or iterable): one or more NoDataValue(s) (default: None)
      dtype (np.dtype, optional): NumPy datatype to return (default: np.uint8)

    Returns:
      np.ndarray: scaled NumPy array

    """
    raise NotImplementedError


_stretch_dict = dict(linear=_linear, percent=_linear_pct, histeq=_histeq)

_context = dict(
    token_normalize_func=lambda x: x.lower(),
    help_option_names=['--help', '-h']
)


@click.command(context_settings=_context)
@click.option('--ndv', default=-9999, type=float, metavar='<ndv>',
              multiple=True,
              help='Image NoDataValue(s) (default: -9999)')
@click.option('-mm', '--minmax', default=(0, 255), metavar='<min, max>',
              nargs=2, type=click.FLOAT,
              help='Stretch minimum and maximum (default: 0, 255)')
@click.option('--pct', default=2, type=click.FLOAT, metavar='<pct>',
              help='Linear percent stretch percent (default: 2)')
@click.option('-f', '--format', default='GTiff', metavar='<str>',
              help='Output file format (default: GTiff)')
@click.option('-ot', '--dtype',
              type=click.Choice(_np_dtypes),
              default=None, metavar='<dtype>',
              help='Output data type (default: None)')
@click.option('-v', '--verbose', is_flag=True,
              help='Show verbose messages')
@click.version_option(__version__)
@click.argument('src', nargs=1,
                type=click.Path(exists=True, readable=True,
                                dir_okay=False, resolve_path=True),
                metavar='<src>')
@click.argument('dst', nargs=1,
                type=click.Path(writable=True, dir_okay=False,
                                resolve_path=True),
                metavar='<dst>')
@click.argument('stretch', nargs=1, type=click.Choice(_stretches),
                metavar='<stretch>')
def stretch(src, dst, stretch,
            ndv, minmax, pct, format, dtype, verbose):
    if verbose:
        logger.setLevel(logging.DEBUG)

    kwargs = dict(ndv=ndv, minmax=minmax, percent=pct)

    # Read input image
    try:
        ds = gdal.Open(src, gdal.GA_ReadOnly)
    except:
        logger.error("Could not open source dataset {0}".format(src))
        raise
    driver = gdal.GetDriverByName(str(format))

    # If no output dtype selected, default to input image dtype
    if not dtype:
        dtype = gdal_array.GDALTypeCodeToNumericTypeCode(
            ds.GetRasterBand(1).DataType)
    dtype = np.dtype(dtype)
    gdal_dtype = gdal_array.NumericTypeCodeToGDALTypeCode(dtype)

    # Create output
    out_ds = driver.Create(dst, ds.RasterXSize, ds.RasterYSize,
                           ds.RasterCount, gdal_dtype)
    for b in range(ds.RasterCount):
        in_band = ds.GetRasterBand(b + 1)
        arr = in_band.ReadAsArray()
        arr = _stretch_dict[stretch](arr, **kwargs)
        out_band = out_ds.GetRasterBand(b + 1)
        out_band.WriteArray(arr)
        out_band.SetDescription(in_band.GetDescription())

    out_ds.SetMetadata(ds.GetMetadata())
    out_ds.SetProjection(ds.GetProjection())
    out_ds.SetGeoTransform(ds.GetGeoTransform())

    ds = None
    out_ds = None

    logger.debug('Complete')


if __name__ == '__main__':
    stretch()
