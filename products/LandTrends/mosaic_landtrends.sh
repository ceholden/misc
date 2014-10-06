#!/bin/bash

dir=$1
ex_img=$2

if [ $# -lt 2 ]; then
    echo 'This script is bad - check for "$1" and "$2"'
    exit 1
fi

cd $dir

# Dates
dates='.*198[3456].* .*199[1234].* .*(199[789]|200[01]).*'
years='1986 1992 2000'

# Image stack characteristics
ul=`gdalinfo $ex_img | grep "Upper Left" | awk -F '(' '{ print $2 }' | tr -d ')' | sed 's/,//g' | sed -e 's/^ *//g' -e 's/ *$//g'`

lr=`gdalinfo $ex_img | grep "Lower Right" | awk -F '(' '{ print $2 }' | tr -d ')' | sed 's/,//g' | sed -e 's/^ *//g' -e 's/ *$//g'`

proj=`gdalinfo -proj4 $ex_img | grep '+proj' | tr -d "'"`

# Determine samples by date
if [ ! -d LandTrends/by_year ]; then
    mkdir -p LandTrends/by_year
    mkdir -p LandTrends/by_year/1986
    mkdir -p LandTrends/by_year/1992
    mkdir -p LandTrends/by_year/2000
fi

count=1
for d in $dates; do
    for img in `find LandTrends/samp* -regextype posix-extended -regex $d`; do
        # Reproject and organize by date
        name=`basename $img | awk -F '.' '{ print $1 }'`
        yr=`echo $years | cut -d ' ' -f$count`
        gdalwarp -q -overwrite -t_srs "$proj" -tr 60 60 $img LandTrends/by_year/$yr/${name}.tif
    done

    mosaic=LandTrends/by_year/LandTrends_${yr}

    # Delete old one
    if [ -e $mosaic ]; then
        rm $mosaic
        rm ${mosaic}.hdr
    fi

    gdal_merge.py -v -init 0 -n 0 -a_nodata 0 -of ENVI -ps 30 30 -ul_lr $ul $lr  -o LandTrends/by_year/LandTrends_${yr} LandTrends/by_year/$yr/*.tif

    let count+=1
done
