#!/usr/bin/env python
from __future__ import division, print_function

try:
    from itertools import zip_longest
except ImportError:
    from itertools import izip_longest as zip_longest
import sys

import click
import numexpr as ne
import numpy as np
from osgeo import gdal, gdal_array

__version__ = '0.1.0'

FORMAT = '%(asctime)s:%(levelname)s:%(module)s.%(funcName)s:%(message)s'

gdal.UseExceptions()
gdal.AllRegister()

NP_DTYPES = ['uint8', 'uint16', 'int16', 'uint32', 'int32',
             'float32', 'float64']
STRETCHES = ['linear', 'percent', 'histeq']

COPY_FORMATS = ['jpeg', 'jpg', 'png']


# Scaling functions
def _linear(arr, minmax, ndv=None, dtype=np.uint8, **kwargs):
    """ Performs linear min/max scaling on an array

    Args:
        arr (np.ndarray): array to scale
        minmax (tuple): minimum and maximum values to scale into
        ndv (int, float, or iterable): one or more NoDataValue(s)
        dtype (np.dtype): NumPy datatype to return

    Returns:
        np.ndarray: scaled NumPy array

    """
    if isinstance(ndv, (int, float)):
        ndv = [ndv]
    if ndv:
        mask = ~np.in1d(arr, ndv).reshape(arr.shape)

    if minmax is None:
        if ndv:
            _min, _max = arr[mask].min(), arr[mask].max()
        else:
            _min, _max = arr.min(), arr.max()
    else:
        _min, _max = minmax

    try:
        dt_max = np.iinfo(dtype).max
        dt_min = np.iinfo(dtype).min + 1
    except:
        dt_max = np.finfo(dtype).max
        dt_min = np.finfo(dtype).min + 1.0

    arr[arr >= _max] = _max
    arr[arr <= _min] = _min

    scale = (dt_max - dt_min) / (_max - _min)
    offset = dt_max - (scale * _max)

    out_ndv = dt_min - 1.0

    if ndv is not None:
        out = np.ones(arr.shape, dtype=dtype) * out_ndv
        out[mask] = arr[mask] * scale + offset
        return out.astype(dtype), out_ndv
    else:
        return ne.evaluate('arr * scale + offset').astype(dtype), out_ndv


def _linear_pct(arr, percent=2, ndv=None, dtype=np.uint8,
                **kwargs):
    """ Performs linear percent scaling on an array

    Args:
        arr (np.ndarray): array to scale
        percent (float): percent to scale
        minmax (tuple): minimum and maximum values to scale into
        ndv (int, float, or iterable): one or more NoDataValue(s)
        dtype (np.dtype): NumPy datatype to return

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

    return _linear(arr, minmax=(_min, _max), ndv=ndv, dtype=dtype, **kwargs)


def _histeq(arr, minmax=(0, 255), ndv=None, dtype=np.uint8, **kwargs):
    """ Performs histogram equalization scaling on an array

    Reference:
        http://www.janeriksolem.net/2009/06/histogram-equalization-with-python-and.html

    Args:
        arr (np.ndarray): array to scale
        minmax (tuple): minimum and maximum values to scale into
        ndv (int, float, or iterable): one or more NoDataValue(s)
        dtype (np.dtype): NumPy datatype to return

    Returns:
      np.ndarray: scaled NumPy array

    """
    raise NotImplementedError


_STRETCH_FUNCS = dict(linear=_linear, percent=_linear_pct, histeq=_histeq)

_context = dict(
    token_normalize_func=lambda x: x.lower(),
    help_option_names=['--help', '-h']
)


@click.command(context_settings=_context)
@click.option('-b', '--bands', type=int, metavar='<bands>',
              multiple=True, show_default=True,
              help='Only operate on these bands')
@click.option('--ndv', default=(-9999, ), type=float, metavar='<ndv>',
              multiple=True, show_default=True,
              help='Image NoDataValue(s)')
@click.option('-mm', '--minmax', metavar='<min, max>',
              nargs=2, multiple=True, type=click.FLOAT, show_default=True,
              help='Stretch minimum and maximum [default: min/max of band]')
@click.option('--pct', default=2, type=click.FLOAT, metavar='<pct>',
              show_default=True,
              help='Linear percent stretch percent')
@click.option('-f', '--format', '_format', default='JPEG', metavar='<str>',
              help='Output file format')
@click.option('-ot', '--dtype',
              type=click.Choice(NP_DTYPES),
              default='uint8', metavar='<dtype>',
              help='Output data type')
@click.option('--co', multiple=True, type=str, help='GDAL Creation options')
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
@click.argument('stretch', nargs=1, type=click.Choice(STRETCHES),
                metavar='<stretch>')
def stretch(src, dst, stretch,
            bands, ndv, minmax, pct, _format, dtype, co, verbose):
    # Read input image
    try:
        ds = gdal.Open(src, gdal.GA_ReadOnly)
    except:
        click.echo("Could not open source dataset {0}".format(src))
        raise
    driver = gdal.GetDriverByName(str(_format))

    # If no output dtype selected, default to input image dtype
    if not dtype:
        dtype = gdal_array.GDALTypeCodeToNumericTypeCode(
            ds.GetRasterBand(1).DataType)
    dtype = np.dtype(dtype)
    gdal_dtype = gdal_array.NumericTypeCodeToGDALTypeCode(dtype)

    if not bands:
        nbands = ds.RasterCount
        bands = range(1, nbands + 1)
    else:
        nbands = len(bands)

    # Create output
    if _format.lower() in COPY_FORMATS:
        if nbands not in (1, 3, 4):
            raise click.BadParameter(
                'JPEG/PNG images must have 1, 3, or 4 bands')

        mem_driver = gdal.GetDriverByName('MEM')
        out_ds = mem_driver.Create('', ds.RasterXSize, ds.RasterYSize,
                                   nbands, gdal_dtype)
    else:
        out_ds = driver.Create(dst, ds.RasterXSize, ds.RasterYSize,
                               nbands, gdal_dtype)

    for idx, (b, _minmax) in enumerate(zip_longest(bands, minmax)):
        kwargs = dict(ndv=ndv, minmax=_minmax, percent=pct)

        in_band = ds.GetRasterBand(b)
        arr = in_band.ReadAsArray()
        arr, out_ndv = _STRETCH_FUNCS[stretch](arr, **kwargs)
        out_band = out_ds.GetRasterBand(idx + 1)
        out_band.WriteArray(arr)
        out_band.SetDescription(in_band.GetDescription())
        out_band.SetNoDataValue(out_ndv)

    out_ds.SetMetadata(ds.GetMetadata())
    out_ds.SetProjection(ds.GetProjection())
    out_ds.SetGeoTransform(ds.GetGeoTransform())

    if _format.lower() in COPY_FORMATS:
        _out_ds = driver.CreateCopy(dst, out_ds, 0, co)
        _out_ds = None

    ds = None
    out_ds = None

    if verbose:
        click.echo('Complete!')


if __name__ == '__main__':
    stretch()
