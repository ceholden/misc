#!/bin/bash

types="treecover2000 loss gain lossyear datamask first last"

usage() {
    echo ""
    echo "Usage: $0 <lat> <lon>"
    echo ""
    echo "  <lat> is [0-9][0-9][NS]"
    echo "  <lon> is [0-9][0-9][0-9][EW]"
    echo ""
    echo "Example:"
    echo "  dl_hansen.sh 090N 100W"
    echo ""
    exit 1
}

if [ $# -ne 2 ]; then
    echo "Error: must specify lat and longitude"
    usage
fi

lat=$1
lon=$2

if [ "$(echo $lat | grep '[0-9][0-9][NS]')" != "$lat" ]; then
    echo "Error: latitude misspecified"
    usage
fi
if [ "$(echo $lon | grep '[0-9][0-9][0-9][EW]')" != "$lon" ]; then
    echo "Error: longitude misspecified"
    usage
fi

d=${lat}_${lon}
if [ ! -d $d ]; then
    mkdir $d
fi

cd $d

echo "Beginning download:"
for t in $types; do
    echo "  downloading $t"
    wget -q http://commondatastorage.googleapis.com/earthenginepartners-hansen/GFC2013/Hansen_GFC2013_${t}_${lat}_${lon}.tif
done

echo ""
echo "Download complete"
