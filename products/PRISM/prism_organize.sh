#!/bin/bash

set -e

resume=1
if [ "$1" == "0" ]; then
    resume=0
fi

# Download destination
if [ ! -z $PRISM_ROOT ]; then
    from=$PRISM_ROOT/download
    dest=$PRISM_ROOT/data
else
    echo "'PRISM_ROOT' envvar is not defined."
    echo "Defaulting to /projectnb/landsat/datasets/PRISM" 
    from=/projectnb/landsat/datasets/PRISM/download/
    dest=/projectnb/landsat/datasets/PRISM/data/
fi
if [ ! -d $dest ]; then
    mkdir -p $dest
fi

element="ppt tmin tmax tmean"

for t in monthly normals; do
    if [ ! -d $from/$t ]; then
        echo "No data downloaded for $t -- continuing"
        continue
    fi
    echo "+ Working on $t data"

    for ele in $element; do
        to=$dest/$t/$ele
        tmp=${to}_tmp
        mkdir -p $to
        mkdir -p $tmp
    
        # Unzip
        echo "  ==> Extracting $ele $t data"
        for z in $from/$t/$ele/*zip; do
            unzip -q -n -d $tmp/ $z
        done
        
        # Convert to GTIFF
        echo "  ==> Converting $ele $t BIL files to GTiff"
        for bil in $tmp/*.bil; do
            gdal_translate -q -of GTiff \
                -co TILED=YES -co COMPRESS=DEFLATE \
                $bil $to/$(basename $bil _bil.bil).gtif
        done

        # Cleanup
        rm -rf $tmp/

    done 
done
