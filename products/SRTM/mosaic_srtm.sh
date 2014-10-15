#!/bin/bash

module purge
module load gdal/1.10.0

location=$1
proj=$2
mosaic=$3

cd $location

if [ ! -d temp ]; then
    mkdir temp
fi

if [ ! -d temp_reproj ]; then
    mkdir temp_reproj
fi

for gz in `find . -name '*.gz'`; do
    # Unzip
    tif=`basename $gz | sed 's/.gz//g'`
    gunzip -c $gz > temp/$tif

    # Reproject
    gdalwarp -srcnodata -32701 -dstnodata -32701 -t_srs $proj -wm 2000 temp/$tif temp_reproj/$tif
done

# Mosaic
gdal_merge.py -o $mosaic -of GTiff -n -32701 -a_nodata -32701 -ps 30 30 temp_reproj/*.tif

rm temp/*.tif
rm temp_reproj/*.tif
rmdir temp
rmdir temp_reproj
