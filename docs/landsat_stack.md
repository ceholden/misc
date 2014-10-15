landsat_stack.py
================

This program is basically a wrapper for `gdal_merge.py` specific to Landsat imagery which makes working with large numbers of images processed to standard products (LEDAPS and Fmask) easier.

## Usage:

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

### Extent specification

You may specify the output extent of your timeseries of imagery in the following ways:

+ `--max_extent` sets the output extent to the union of all images, or an area which would cover 100% of all images
+ `--min_extent` sets the output extent to the intersect of all images, or the smallest region containing 100% of the images
+ `--percentile=<pct>` sets the output extent to an area representing a percentile of the maximum extent. If `--percentile=0`, then it operates as `--max_extent`. In practice this option is a more useful alternative to `--max_extent` because it results in an output extent that covers all of most of the images while being robust to images that are unusually sized or geolocated
+ `--extent=<extent>` sets the output extent of the stack to a predefined extent specified by the upper left and lower right X/Y pairs (use quotes around the 4 numbers when specifying)
+ `--image=<image>` sets the output extent to the extent of a pre-existing image
