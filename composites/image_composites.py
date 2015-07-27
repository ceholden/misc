#!/usr/bin/env python2
""" Image compositing script

TODO:
    - use mask bands/values in input images in masked arrays
    - make some system where vegetation indices can be inserted into expression
        + '(max {NDVI})' and {NDVI} = '(/ (- nir red) (+ nir red))'
    - allow images to not be stacked (see read's boundless option)
    - specify <projwin> for output composite

"""
from __future__ import division, print_function

import logging

import click
import numpy as np
try:
    import progressbar
except:
    _has_progressbar = False
else:
    _has_progressbar = True
import rasterio
from rasterio.rio.options import _cb_key_val, creation_options
import snuggs

__author__ = 'Chris Holden (ceholden@gmail.com)'
__version__ = '0.99.1'

logging.basicConfig(format='%(asctime)s.%(levelname)s: %(message)s',
                    level=logging.INFO,
                    datefmt='%H:%M:%S')
logger = logging.getLogger(__name__)

# Predefined algorithms -- name: snuggs expression
_ALGO = {
    'maxNDVI': '(max (/ (- nir red) (+ nir red)))',
    'medianNDVI': '(median (/ (- nir red) (+ nir red)))',
    'ZheZhu': '(max (/ nir blue))',
    'minBlue': '(min blue)',
    'maxNIR': '(max nir)'
}

_context = dict(
    token_normalize_func=lambda x: x.lower(),
    help_option_names=['--help', '-h']
)


def _valid_band(ctx, param, value):
    try:
        band = int(value)
        assert band >= 1
    except:
        raise click.BadParameter('Band must be integer above 1')
    return band


@click.command(context_settings=_context)
@click.argument('inputs', nargs=-1,
                type=click.Path(dir_okay=False, readable=True,
                                resolve_path=True))
@click.argument('output', nargs=1,
                type=click.Path(dir_okay=False, writable=True,
                                resolve_path=True))
@click.option('--algo', help='Create composite based on specific algorithm',
              type=click.Choice(_ALGO.keys()))
@click.option('--expr', help='Create composite based on an expression',
              type=str, metavar='SNUGGS')
@click.option('-of', '--format', 'oformat', help='Output image format',
              default='GTiff')
@creation_options
@click.option('--blue', callback=_valid_band, default=1, type=int,
              help='Band number for blue band in INPUTS (default: 1)')
@click.option('--green', callback=_valid_band, default=2, type=int,
              help='Band number for green band in INPUTS (default: 2)')
@click.option('--red', callback=_valid_band, default=3, type=int,
              help='Band number for red band in INPUTS (default: 3)')
@click.option('--nir', callback=_valid_band, default=4, type=int,
              help='Band number for near IR band in INPUTS (default: 4)')
@click.option('--fswir', callback=_valid_band, default=5, type=int,
              help='Band number for first SWIR band in INPUTS (default: 5)')
@click.option('--sswir', callback=_valid_band, default=6, type=int,
              help='Band number for second SWIR band in INPUTS (default: 6)')
@click.option('--band', callback=_cb_key_val, multiple=True,
              metavar='NAME=INDEX',
              help='Name and band number in INPUTS for additional bands')
@click.option('-v', '--verbose', is_flag=True, help='Show verbose messages')
@click.option('-q', '--quiet', is_flag=True,
              help='Do not show progress or messages')
@click.version_option(__version__)
def image_composite(inputs, algo, expr, output, oformat, creation_options,
                    blue, green, red, nir, fswir, sswir, band,
                    verbose, quiet):
    """ Create image composites based on some criteria

    Output image composites retain original values from input images that meet
    a certain criteria. For example, in a maximum NDVI composite with 10 input
    images, all bands for a given pixel will contain the band values from the
    input raster that had the highest NDVI value.

    Users can choose from a set of predefined compositing algorithms or may
    specify an Snuggs S-expression that defines the compositing criteria.
    Normalized Differenced indexes can be computed using "(normdiff a b)" for
    the Normalized Difference between "a" and "b" (or "nir" and "red").
    See https://github.com/mapbox/snuggs for more information on Snuggs
    expressions.

    The indexes for common optical bands (e.g., red, nir, blue) within the
    input rasters are included as optional arguments and are indexed in
    wavelength sequential order. You may need to overwrite the default indexes
    of bands used in a given S-expression with the correct band index.
    Additional bands may be identified and indexed using the
    '--band NAME=INDEX' option.

    Currently, input images must be "stacked", meaning that they contain the
    same bands and are the same shape and extent.

    Example:

    1. Create a composite based on maximum NDVI

        Use the built-in maxNDVI algorithm:

        \b
        $ image_composite.py --algo maxNDVI image1.gtif image2.gtif image3.gtif
            composite_maxNDVI.gtif

        or with S-expression:

        \b
        $ image_composite.py --expr '(max (/ (- nir red) (+ nir red)))'
            image1.gtif image2.gtif image3.gtif composite_maxNDVI.gtif

        or with S-expressions using the normdiff shortcut:

        \b
        $ image_composite.py --expr '(max (normdiff nir red))'
            image1.gtif image2.gtif image3.gtif composite_maxNDVI.gtif

    2. Create a composite based on median EVI (not recommended)

        With S-expression:

        \b
        $ evi='(median (/ (- nir red) (+ (- (+ nir (* 6 red)) (* 7.5 blue)) 1)))'
        $ image_composite.py --expr "$evi"  image1.gtif image2.gtif image3.gtif
            composite_medianEVI.gtif

    3. Create a composite based on median NBR

        With S-expression:

        \b
        $ image_composite.py --expr '(median (normdiff nir sswir))'
            image1.gtif image2.gtif image3.gtif composite_maxNBR.gtif

    """
    if verbose:
        logger.setLevel(logging.DEBUG)
    elif quiet:
        logger.setLevel(logging.ERROR)

    # Prefer built-in algorithms to expressions if both are specified
    if not algo and not expr:
        raise click.UsageError('Error: must specify either --algo or --expr')
    elif algo is not None and expr is not None:
        logger.warning('Predefined algorithm and expression both defined. '
                       'Composite will be generated with predefined algorithm')
        expr = _ALGO[algo]
    elif algo is not None:
        logger.debug('Using predefined algorithm: {}'.format(algo))
        expr = _ALGO[algo]

    if not quiet:
        click.echo('Compositing criteria S-expression: "{}"'.format(expr))

    # Setup band keywords
    _bands = {'blue': blue, 'green': green, 'red': red,
              'nir': nir, 'fswir': fswir, 'sswir': sswir}
    # Parse any additional, user specified bands
    if band:
        for k, v in band.iteritems():
            try:
                _bands.update({k: int(v)})
            except ValueError:
                raise click.BadParameter(
                    'Value specified as KEY=VAL pair in --band must be an int')

    # Find only the band names and indexes required for the composite criteria
    crit_indices = {k: v - 1 for k, v in _bands.iteritems() if k in expr}

    # Enhance snuggs expressions to return index of value matching function
    snuggs.func_map['max'] = lambda a: np.argmax(a, axis=0)
    snuggs.func_map['min'] = lambda a: np.argmin(a, axis=0)
    snuggs.func_map['median'] = lambda a: np.argmin(
        np.abs(a - np.median(a, axis=0)), axis=0)
    snuggs.func_map['normdiff'] = lambda a, b: snuggs.eval(
        '(/ (- a b) (+ a b))', **{'a':a, 'b':b})

    with rasterio.drivers():

        # Read in the first image to fetch metadata
        with rasterio.open(inputs[0]) as first:
            meta = first.meta
            if 'transform' in meta:
                meta.pop('transform')  # remove transform since deprecated
            meta.update(driver=oformat)
            meta.update(**creation_options)
            if len(set(first.block_shapes)) != 1:
                click.echo('Cannot process input files - '
                           'All bands must have same block shapes')
                raise click.Abort()
            block_nrow, block_ncol = first.block_shapes[0]
            windows = first.block_windows(1)
            n_windows = (meta['height'] / block_nrow *
                         meta['width'] / block_ncol)

        # Initialize output data and create composite
        with rasterio.open(output, 'w', **meta) as dst:
            # Process by block
            dat = np.ma.empty((len(inputs), meta['count'],
                               block_nrow, block_ncol),
                              dtype=np.dtype(meta['dtype']))
            mi, mj = np.meshgrid(np.arange(block_nrow), np.arange(block_ncol),
                                 indexing='ij')
            # Open all source files one time
            srcs = [rasterio.open(fname) for fname in inputs]

            logger.debug('Processing blocks')
            if _has_progressbar and not quiet:
                widgets = [
                    progressbar.Percentage(),
                    progressbar.BouncingBar(marker=progressbar.RotatingMarker())
                ]
                pbar = progressbar.ProgressBar(widgets=widgets).start()

            for i, (idx, window) in enumerate(windows):
                for j, src in enumerate(srcs):
                    dat[j, ...] = src.read(masked=True, window=window)

                # Find indices of files for composite
                crit = {k: dat[:, v, ...] for k, v in crit_indices.iteritems()}
                crit_idx = snuggs.eval(expr, **crit)

                # Create output composite
                # Use np.rollaxis to get (nimage, nrow, ncol, nband) shape
                composite = np.rollaxis(dat, 1, 4)[crit_idx, mi, mj]

                # Write out
                for i_b in range(composite.shape[-1]):
                    dst.write(composite[:, :, i_b], indexes=i_b + 1,
                              window=window)
                if not quiet and _has_progressbar:
                    pbar.update(int((i + 1) / n_windows * 100))

if __name__ == '__main__':
    image_composite()
