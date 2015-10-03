#!/bin/bash

set -e

naip_pattern="*imagery_NAIP*.zip"

# SETUP DECODER FROM LIZARDTECH
decode=/usr3/graduate/ceholden/tools/MrSID/GeoExpressCLUtils-9.5.0.4326-linux64/bin/mrsidgeodecode
export LD_LIBRARY_PATH=$LD_LIRBARY_PATH:$(dirname $decode)

# PARSE INPUT
if [ "$1" == "" ]; then
    echo "Looking for NAIP order zips in current directory"
    dir=$(pwd)
elif [ ! -d $1 ]; then
    echo "Error: directory specified does not exist"
    exit 1
else
    echo "Looking for NAIP order zips in $1"
    dir=$1
fi

# FIND NAIP ZIPS -- ortho_imagery_NAIP*.zip
naip=$(find $dir -maxdepth 1 -name "$naip_pattern")
n_naip=$(echo $naip | wc -w)

if [ "$n_naip" == "0" ]; then
    echo "Could not find any NAIP downloads in $dir"
    echo "Search pattern is: $naip_pattern"
    exit 1
else
    echo "Found $n_naip NAIP products"
fi

for z in $naip; do
    # Extract NAIP year and state reference
    state=$(echo $(basename $z) | awk -F '_' '{ print $(NF - 2) }')
    yr=$(echo $(basename $z) | awk -F '_' '{ print $(NF - 3) }')
    echo "==> Found $yr/$state"

    # Organize
    dest=$dir/$yr/$state
    mkdir -p $dest
    mv $z $dest/
    dest_name=${yr}_${state}_imagery.gtif
    z=$(basename $z) 

    # Formulate decode & compress command
    cmd="cd $dest; unzip -j $z"
    cmd="$cmd; \
         LD_LIBRARY_PATH=$(dirname $decode) $decode -wf -i *.sid -o tmp.tif"
    cmd="$cmd;\
         gdal_translate \
            -of GTiff \
            -co BIGTIFF=YES \
            -co TILED=YES \
            -co COMPRESS=DEFLATE \
            tmp.tif $dest_name"
    cmd="$cmd; rm tmp.tif tmp.tfw"
            
    echo $cmd
    qsub -V -l eth_speed=10 -l h_rt=24:00:00 \
         -N ${yr}_${state} -j y -b y \
         "$cmd" 
    echo ""
done
