#!/usr/bin/env python
import os

import click
from cligj import format_opt
import pandas as pd
from pathlib import Path
import rasterio
from rasterio.rio import options as rio_opts
from rasterio.windows import Window


@click.command(short_help='Clip out ROIs')
@click.argument('indir',
                type=click.Path(exists=True, file_okay=False,
                                readable=True, resolve_path=True))
@click.argument('chip_csv',
                type=click.Path(exists=True, dir_okay=False,
                                readable=True, resolve_path=True))
@click.argument('outdir',
                type=click.Path(dir_okay=True, resolve_path=True))
@click.option('--image_pattern', type=str,
              default='*.tif', show_default=True,
              help='Image file pattern in INDIR')
@click.option('--chip_pattern', type=str, show_default=True,
              default='{Index}_{name}/{Index}_{name}_{input}',
              help='Output chip filename pattern')
@click.option('--shape', multiple=True, default=(100, ), type=int,
              help='Shape of chips (cols/rows)', show_default=True)
@format_opt
def clip(indir, chip_csv, outdir,
         image_pattern, chip_pattern, shape, driver):
    """ Output image chips listed in a CSV file

    \b
    CSV file expects the following columns:
        * idx (int): index of the chip
        * name (str): name of chip land cover
        * x (float): upper left X coordinate of chip
        * y (float): upper left Y coordinate of chip

    """
    # Handle 1 or 2 inputs
    if not len(shape):
        shape = None
    else:
        shape = (shape[0], shape[0]) if len(shape) == 1 else shape

    indir, chip_csv, outdir = Path(indir), Path(chip_csv), Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    # Chip info
    chips = pd.read_csv(chip_csv)

    # Input images
    images = list(indir.glob(image_pattern))

    for chip in chips.itertuples():
        _chip = dict(zip(chip._fields, chip))
        _chip['Index'] += 1  # index on 1
        for image in images:
            # Format output filename
            _chip['input'] = image.name
            out_image = outdir.joinpath(chip_pattern.format(**_chip))
            # Make sure output directory exists
            out_image.parent.mkdir(parents=True, exist_ok=True)

            with rasterio.open(str(image)) as src:
                # Formulate chip bounds
                col, row = map(int, ~src.transform * (chip.x, chip.y))
                window = Window.from_offlen(col, row, shape[0], shape[1])

                # Form output kwargs
                out_kwargs = src.meta.copy()
                out_kwargs['driver'] = driver
                out_kwargs['width'] = shape[0]
                out_kwargs['height'] = shape[1]
                out_kwargs['transform'] = src.window_transform(window)

                click.echo('Writing output for image: {}'
                           .format(out_image.name))
                with rasterio.open(str(out_image), 'w', **out_kwargs) as dst:
                    dst.write(src.read(window=window))


if __name__ == '__main__':
    clip()
