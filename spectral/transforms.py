#!/usr/bin/env python
from __future__ import division, print_function

from collections import OrderedDict
import inspect
import logging
import sys

import click
import numexpr as ne
import numpy as np
from osgeo import gdal, gdal_array

__version__ = '0.1.0'

FORMAT = '%(asctime)s:%(levelname)s:%(module)s.%(funcName)s:%(message)s'
logging.basicConfig(format=FORMAT, level=logging.INFO, datefmt='%H:%M:%S')
logger = logging.getLogger('transforms')

gdal.UseExceptions()
gdal.AllRegister()

_np_dtypes = ['uint8', 'uint16', 'int16', 'uint32', 'int32',
             'float32', 'float64']
_transforms = ['evi', 'ndvi', 'ndmi', 'nbr',
               'brightness', 'greenness', 'wetness']

# Crist 1985
_lt5_bgw = [
    np.array([0.2043, 0.4158, 0.5524, 0.5741, 0.3124, 0.2330]),
    np.array([-0.1603, -0.2189, -0.4934, 0.7940, -0.0002, -0.1446]),
    np.array([0.0315, 0.2021, 0.3102, 0.1954, -0.6806, -0.6109])
]
# Huang et al 2002
_le7_bgw = [
    np.array([0.3561, 0.3972, 0.3904, 0.6966, 0.2286, 0.1596]),
    np.array([-0.3344, -0.3544, -0.4556,  0.6966, -0.0242,-0.2630]),
    np.array([0.2626, 0.2141, 0.0926, 0.0656, -0.7629, -0.5388])
]


def transform(transform_name, required_bands):
    """ Decorator that adds name and requirement info to a transform function

    Args:
      transform_name (str): name of transform
      required_bands (list): list of bands used in the transform

    """
    def decorator(func):
        func.transform_name = transform_name
        func.required_bands = required_bands
        return func
    return decorator


@transform('EVI', ['red', 'nir', 'blue'])
def _evi(red, nir, blue, scaling=1.0, **kwargs):
    """ Return the Enhanced Vegetation Index (EVI)

    EVI is calculated as:

    .. math::
        EVI = 2.5 * \\frac{(NIR - RED)}{(NIR + C_1 * RED - C_2 * BLUE + L)}

    where:
        - :math:`RED` is the red band
        - :math:`NIR` is the near infrared band
        - :math:`BLUE` is the blue band
        - :math:`C_1 = 6`
        - :math:`C_2 = 7.5`
        - :math:`L = 1`

    Args:
      red (np.ndarray): red band
      nir (np.ndarray): NIR band
      blue (np.ndarray): blue band
      scaling (float): scaling factor for red, nir, and blue reflectance to
        convert into [0, 1] range (default: 1.0)

    Returns:
      np.ndarray: EVI

    """
    dtype = red.dtype
    expr = '2.5 * (nir - red) / (nir + 6 * red - 7.5 * blue + scaling)'
    evi = ne.evaluate(expr)

    if scaling != 1.0:
        evi *= scaling
    return evi.astype(dtype)


@transform('NDVI', ['red', 'nir',])
def _ndvi(red, nir, **kwargs):
    """ Return the Normalized Difference Vegetation Index (NDVI)

    NDVI is calculated as:

    .. math::
        NDVI = \\frac{(NIR - RED)}{(NIR + RED)}

    where:
        - :math:`RED` is the red band
        - :math:`NIR` is the near infrared band

    Args:
      red (np.ndarray): red band
      nir (np.ndarray): NIR band

    Returns:
      np.ndarray: NDVI

    """
    expr = '(nir - red) / (nir + red)'
    return ne.evaluate(expr)


@transform('NDMI', ['swir1', 'nir'])
def _ndmi(swir1, nir, **kwargs):
    """ Return the Normalized Difference Moisture Index (NDMI)

    NDMI is calculated as:

    .. math::
        NDMI = \\frac{(NIR - SWIR1)}{(NIR + SWIR1)}

    where:
        - :math:`SWIR1` is the shortwave infrared band
        - :math:`NIR` is the near infrared band

    Args:
      swir1 (np.ndarray): SWIR1 band
      nir (np.ndarray): NIR band

    Returns:
      np.ndarray: NDMI

    """
    expr = '(nir - swir1) / (nir + swir1)'
    return ne.evaluate(expr)


@transform('NBR', ['swir2', 'nir'])
def _nbr(swir2, nir, **kwargs):
    """ Return the Normalized Burn Ratio (NBR)

    NBR is calculated as:

    .. math::
        NBR = \\frac{(NIR - SWIR2)}{(NIR + SWIR2)}

    where:
        - :math:`SWIR2` is the shortwave infrared band
        - :math:`NIR` is the near infrared band

    Args:
      swir2 (np.ndarray): SWIR2 band
      nir (np.ndarray): NIR band

    Returns:
      np.ndarray: NBR

    """
    expr = '(nir - swir2) / (nir + swir2)'
    return ne.evaluate(expr)


@transform('Brightness', ['blue', 'green', 'red', 'nir', 'swir1', 'swir2'])
def _brightness(blue, green, red, nir, swir1, swir2, sensor, **kwargs):
    if sensor[0:2].lower() == 'le':
        coef = _le7_bgw[0]
    else:
        coef = _lt5_bgw[0]
    c1, c2, c3, c4, c5, c6 = coef

    expr = ('blue * c1 + green * c2 + red * c3'
            ' + nir * c4 + swir1 * c5 + swir2 * c6')

    return ne.evaluate(expr)


@transform('Greenness', ['blue', 'green', 'red', 'nir', 'swir1', 'swir2'])
def _greenness(blue, green, red, nir, swir1, swir2, sensor, **kwargs):
    if sensor[0:2].lower() == 'le':
        coef = _le7_bgw[1]
    else:
        coef = _lt5_bgw[1]
    c1, c2, c3, c4, c5, c6 = coef

    expr = ('blue * c1 + green * c2 + red * c3'
            ' + nir * c4 + swir1 * c5 + swir2 * c6')

    return ne.evaluate(expr)


@transform('Wetness', ['blue', 'green', 'red', 'nir', 'swir1', 'swir2'])
def _wetness(blue, green, red, nir, swir1, swir2, sensor, **kwargs):
    if sensor[0:2].lower() == 'le':
        coef = _le7_bgw[2]
    else:
        coef = _lt5_bgw[2]
    c1, c2, c3, c4, c5, c6 = coef

    expr = ('blue * c1 + green * c2 + red * c3'
            ' + nir * c4 + swir1 * c5 + swir2 * c6')

    return ne.evaluate(expr)


# Main script
def _valid_band(ctx, param, value):
    try:
        band = int(value)
        assert band >= 1
    except:
        raise click.BadParameter('Band must be integer above 1')
    return band

_context = dict(
    token_normalize_func=lambda x: x.lower(),
    help_option_names=['--help', '-h']
)


@click.command(context_settings=_context)
@click.option('-f', '--format', default='GTiff', metavar='<str>',
              help='Output file format (default: GTiff)')
@click.option('-ot', '--dtype',
              type=click.Choice(_np_dtypes),
              default=None, metavar='<dtype>',
              help='Output data type (default: None)')
@click.option('--scaling', default=10000, type=float, metavar='<scaling>',
              help='Scaling factor for reflectance (default: 10,000)')
@click.option('--sensor', default='LT5', type=str, metavar='<sensor>',
              help='Landsat sensor type (for Tasseled Cap) (default: LT5)')
@click.option('--blue', callback=_valid_band, default=1, metavar='<int>',
              help='Band number for blue band in <src> (default: 1)')
@click.option('--green', callback=_valid_band, default=2, metavar='<int>',
              help='Band number for green band in <src> (default: 2)')
@click.option('--red', callback=_valid_band, default=3, metavar='<int>',
              help='Band number for red band in <src> (default: 3)')
@click.option('--nir', callback=_valid_band, default=4, metavar='<int>',
              help='Band number for near IR band in <src> (default: 4)')
@click.option('--swir1', callback=_valid_band, default=5, metavar='<int>',
              help='Band number for first SWIR band in <src> (default: 5)')
@click.option('--swir2', callback=_valid_band, default=6, metavar='<int>',
              help='Band number for second SWIR band in <src> (default: 6)')
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
@click.argument('transforms', nargs=-1,
                type=click.Choice(_transforms),
                metavar='<transform>')
def create_transform(src, dst, transforms,
                     format, dtype, scaling, sensor,
                     blue, green, red, nir, swir1, swir2,
                     verbose):
    if not transforms:
        raise click.BadParameter(
            'No transforms specified', param_hint='<transform>...')

    if verbose:
        logger.setLevel(logging.DEBUG)

    # Pair transforms requested with functions that calculate each transform
    transform_funcs = [obj for name, obj in
                       inspect.getmembers(sys.modules[__name__],
                                          inspect.isfunction)
                       if hasattr(obj, 'transform_name')]

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

    # Only read in the bands that are required for the transforms
    required_bands = set()
    for t in transform_funcs:
        required_bands.update(t.required_bands)

    func_args = inspect.getargvalues(inspect.currentframe())[-1]
    transform_args = dict.fromkeys(required_bands)
    for b in transform_args.keys():
        idx = func_args[b]
        transform_args[b] = ds.GetRasterBand(idx).ReadAsArray()
    logger.debug('Opened input file')

    transform_args['scaling'] = scaling
    transform_args['sensor'] = sensor

    # Create transforms
    transforms = OrderedDict([
        [t.transform_name, t(**transform_args)] for t in transform_funcs
        if t.transform_name.lower() in transforms
    ])
    logger.debug('Calculated transforms')

    # Write output
    nbands = len(transforms.keys())
    out_ds = driver.Create(dst,
                           ds.RasterXSize, ds.RasterYSize, nbands, gdal_dtype)
    metadata = {}
    for i_b, (name, array) in enumerate(transforms.iteritems()):
        r_band = out_ds.GetRasterBand(i_b + 1)
        r_band.WriteArray(array)
        r_band.SetDescription(name)
        metadata['Band_' + str(i_b + 1)] = name

    out_ds.SetMetadata(metadata)
    out_ds.SetProjection(ds.GetProjection())
    out_ds.SetGeoTransform(ds.GetGeoTransform())
    logger.debug('Complete')

if __name__ == '__main__':
    create_transform()
