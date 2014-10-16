landsat_stack.py
================

This program is basically a wrapper for `gdal_merge.py` specific to Landsat imagery which makes working with large numbers of images processed to standard products (LEDAPS and Fmask) easier.

## Syntax

This program is used to create layer stacks from various data sources, including the ability to use subsets of bands from different image sources. To accomplish this, several of the command line options, such as `--files` and `--ndv`, employ semi-colons `;` to separate options across different image file inputs. For specifying options within an image file input, you can use spaces or commas `,`. 

If only one value is used for an option, the one value is used for all bands for all image inputs. For example, the default value for `--ndv` is `--ndv=0`. Using this default with the default for `--files` would mean that all bands within images matching that patterns `lndsr.*.hdf` and `*Fmask` would be assigned 0 as the NoDataValue.

If we wanted to use different NoDataValues for files matching `lndsr.*.hdf` and `*Fmask`, we could denote this difference across image file inputs using a semi-colon `;` as such:

``` bash

landsat_stack.py --files "lndsr.*.hdf; *Fmask" \
    --ndv "-9999; 255" \
    --min_extent ./

```

This usage would gather all bands within the `lndsr.*.hdf` file and apply -9999 as the NoDataValue, but would use 255 as the NoDataValue for the `*Fmask` image.

A more common usage scenario when handling Landsat data atmospherically corrected using LEDAPS would be to exclude many of the QA/QC bands from the image stack. By default, however, the `--bands` argument will use `all` bands or subdatasets within an input image. We can change this specification to use some subset as follows:

``` bash

landsat_stack.py --files "lndsr.*.hdf; *Fmask" \
    --bands "1 2 3 4 5 6 15; 1" \
    --ndv "-9999; 255" \
    --min_extent ./

```

This example usage would create image layer stacks with only 8 bands - 7 bands from the LEDAPS HDF image and 1 from the Fmask image. Note that one could also specify the subdatasets to use from the first input image file (`lndsr.*.hdf`) by using a comma separated list (`"1, 2, 3, 4, 5, 6, 15; 1"` instead of `"1 2 3 4 5 6 15; 1"`).

## Extent Specification

You may specify the output extent of your timeseries of imagery in the following ways:

+ `--max_extent` sets the output extent to the union of all images, or an area which would cover 100% of all images
+ `--min_extent` sets the output extent to the intersect of all images, or the smallest region containing 100% of the images
+ `--percentile=<pct>` sets the output extent to an area representing a percentile of the maximum extent. If `--percentile=0`, then it operates as `--max_extent`. In practice this option is a more useful alternative to `--max_extent` because it results in an output extent that covers all of most of the images while being robust to images that are unusually sized or geolocated
+ `--extent=<extent>` sets the output extent of the stack to a predefined extent specified by the upper left and lower right X/Y pairs (use quotes around the 4 numbers when specifying)
+ `--image=<image>` sets the output extent to the extent of a pre-existing image

## Full Usage:

    Stack Landsat Data
    
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

## Source code

The full source code is contained within this repository [here](../landsat/landsat_stack.py).
