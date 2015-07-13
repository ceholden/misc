#!/bin/bash

set +e

frmt=GTiff
co="COMPRESS=LZW"
usage() {
    cat << EOF

    Usage: $0 <radar_img> <example_img> <dest>

    Author: Chris Holden (ceholden@gmail.com)
    Purpose:
        Reproject and resize imagery to meet size/extents of an example 
        image. Specific application of script at time of writing is to
        reproject and resize radar imagery to match a Landsat timeseries
        stack.

    Options:
        -f          Output format (default: $frmt)
        -o          Creation options (default: $co)
        -h          Show help

EOF
}

while getopts "f:h" opt
do
    case $opt in
        f)
            frmt=$OPTARG
            ;;
        h)
            usage
            exit 0
            ;;
        ?)
            echo "Error: unknown option -$opt"
            usage
            exit 1
            ;;
    esac
done
shift $(($OPTIND - 1))

radar=$1
example=$2
dest=$3

if [ -z $radar ] || [ ! -f $radar ]; then
    echo "Error: '$1' is not a file"
    exit 1
fi
if [ -z $example ] || [ ! -f $example ]; then
    echo "Error: '$2' is not a file"
    exit 1
fi

proj=$(gdalinfo -proj4 $example | grep '+proj'| tr -d "'")
ext=$(gdalinfo $example | grep 'Upper Left\|Lower Right' |\
      sed "s/Upper Left  //g;s/Lower Right //g;s/).*//g" |\
      tr "\n" " " |\
      sed 's/ *$//g' |\
      tr -d "[(]" | tr "," " " |\
      awk 'BEGIN {OFS=" "} { print $1, $4, $3, $2 }')
sz=$(gdalinfo $example | grep "Pixel Size" | awk '{ print $4 }' |\
     tr -d "(-)" | tr "," " ")

# Reproject and resize first to VRT
gdalwarp -q -overwrite -of VRT -t_srs "$proj" -tr $sz -te $ext \
    -r near $radar $(basename $radar).vrt
if [ $? -ne 0 ]; then
    echo "Error in gdalwarp"
    exit 1
fi

# Translate if partially inside
if [ ! -z $co ]; then
    gdal_translate -q -eco -of $frmt -co $co $(basename $radar).vrt $dest
else
    gdal_translate -q -eco -of $frmt $(basename $radar).vrt $dest
fi

rm $(basename $radar).vrt
