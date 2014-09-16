#!/usr/bin/env python
""" Stack image frequency and clear percentage visualization 

Usage:
    plot_stack_nobs.py [options] <location> <title>

Options:
    --to=<dir>          Output directory [default: pwd]
    --calc_clear        Calculate clear %
    -h                  Show help

Example:
    plot_stack_nobs.py --calc_clear images/ p008r056

This will create the following output:
    - "p008r056_df.df": a Pandas dataframe with the Landsat ID, the clear %, 
        and the date
    - "p008r056_nobs_plot.png": a PNG image of the plot

NOTE:
    - Assumes you have 8 bands stacks where the 8th band is Fmask
    - Assumes "clear" to be land (0) or water (1)
    - Pandas needs X windows forwarded to save the plot. You may need to re-run
        the script on an interactive session if you "qsub" the plot the first 
        time. When you re-run the script, it will find the Pandas dataframe
        result and only make the plot.

"""
from __future__ import print_function, division

from datetime import datetime as dt
import fnmatch
import logging
import os
import sys

from docopt import docopt

import numpy as np
import pandas as pd
from ggplot import *

from osgeo import gdal

# root = '/projectnb/landsat/projects/CMS/stacks/'
# pattern = 'p*r*'
# countries = ['Colombia', 'Mexico', 'Peru']

gdal.AllRegister()
gdal.UseExceptions()

logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s',
                    level=logging.DEBUG,
                    datefmt='%I:%M:%S')
logger = logging.getLogger(__name__)


def plot_year_doy(df, title, palette='RdYlGn'):
    """ Plot year / doy with clear percent as color if available"""

    if 'clear' in df.columns:
        pct_clear = ((df['clear'] // 20) * 20).astype(np.uint8)
        df['Percent Clear'] = [' ' * (3 - len(str(v))) + str(v) 
                               if v < 100 else str(v) 
                               for v in pct_clear]

        # HACK to get all values shown
        need = ['  0', ' 20', ' 40', ' 60', ' 80', '100']
        to_add = [v for v in need if v not in np.unique(df['Percent Clear'])]
        for v in to_add:
            df = pd.concat([df, df[:1]])
            df['year'][-1:] = np.nan
            df['doy'][-1:] = np.nan
            df['Percent Clear'][-1:] = v

        plot = ggplot(aes('year', 'doy', color='Percent Clear'), df)
        plot = plot + scale_color_brewer(type='diverging', palette=palette)

    else:
        plot = ggplot(aes('year', 'doy'), df)

    return(plot + geom_point(size=50) +
           xlim(df.year.min() - 1, df.year.max() + 1) +
           ylim(0, 366) +
           xlab('Year') +
           ylab('Day of Year') +
           ggtitle(title))


def get_clear_pct(stack_img, mask_band=8, ndv=255):
    """ Returns clear percent of image """
    # Open dataset and read in mask band
    ds = gdal.Open(stack_img)
    mask = ds.GetRasterBand(mask_band).ReadAsArray().astype(np.uint8)
    # Return clear percent of non NODATA
    clear = np.where(mask <= 1)[0].size
    data = np.where(mask != 255)[0].size
    return clear / data * 100.0


def get_year_doy(location, image_pattern='L*', stack_pattern='L*stack',
                 calc_clear=False):
    """ Returns dataframe of Landsat ID, year, DOY, and clear percent """
    logger.debug('Finding images')
    # File path to directories
    images = [os.path.join(location, d) for d in
              fnmatch.filter(os.listdir(location), image_pattern)]

    logger.debug('Found {n} images - getting attributes'.format(n=len(images)))
    # Landsat IDs
    ids = [os.path.basename(d) for d in images]

    # Dates of image
    dates = [dt.strptime(d[9:16], '%Y%j') for d in ids]

    logger.debug('Finding stack images')
    # Stack filenames
    stacks = [os.path.join(i, fnmatch.filter(os.listdir(i),
                                             stack_pattern)[0]) for i in images]

    # Clear percent of each image
    logger.debug('Found stack images')

    if calc_clear:
        logger.debug('Calculating clear percentage')
        clear = np.zeros(len(images))
        for i, stack in enumerate(stacks):
            logger.debug('    {i} / {n}'.format(i=i, n=len(images)))
            clear[i] = get_clear_pct(stack)

        logger.debug('Calculated cloud cover')

    logger.debug('Returning Pandas DataFrame')
    if calc_clear:
        # Dataframe
        df = pd.DataFrame({
            'ID': ids,
            'date': dates,
            'clear': clear
        })
    else:
        # Dataframe
        df = pd.DataFrame({
            'ID': ids,
            'date': dates
        })

    df['doy'] = pd.DatetimeIndex(dates).dayofyear
    df['year'] = pd.DatetimeIndex(dates).year

    return df

if __name__ == '__main__':
    args = docopt(__doc__)
    location = args['<location>']
    name = args['<title>']
    to = args['--to']
    if to == 'pwd':
        to = os.getcwd()
    calc_clear = args['--calc_clear']

    out_plot = os.path.join(to, name + '_nobs_plot.png')
    out_df = os.path.join(to, name + '_df.df')
    out_csv = os.path.join(to, name + '_nobs.csv')
    logger.info('Writing output to {f}'.format(f=out_plot))

    if not os.path.isfile(out_df):
        df = get_year_doy(location, calc_clear=calc_clear)
        try:
            df.to_pickle(out_df)
            df.to_csv(out_csv)
        except:
            logger.warn('Could not pickle DataFrame')
    else:
        df = pd.read_pickle(out_df)

    plot = plot_year_doy(df, name)
    ggsave(out_plot, plot)

    logger.debug('Done!')
