#!/bin/bash

set -e
set -u

# EQUATIONS
DN_to_dB="(- (* (- (read 1 1) 1) 0.15) 31.0)"

# INPUTS -- HARDCODED
EXAMPLE=/projectnb/landsat/projects/CMS/stacks/Colombia/p008r056/images/example_img

SRC=/projectnb/landsat/projects/CMS/RADAR/ALOS_PALSAR/new_scenes_Dec_2015/
DST=/projectnb/landsat/projects/CMS/stacks/Colombia/p008r056/RADAR/

PATTERN="*_hh.tif *_hv.tif"

P="145 146"
R="0110"

# OPTIONS - HARDCODED
RESAMPLING=bilinear


function DN_to_power() {
    img=$1 out=$2

    calc="(power 10.0 (/ ${DN_to_dB} 10.0))"
    rio calc "$calc" \
        -t float32 \
        --masked \
        --force-overwrite \
        $img $out
}


function reproj() {
    example=$1
    img=$2
    dest=$3

    # First convert to power so we can resample
    echo "        DN to power: $img -> tmp_power.tif"
    DN_to_power $img tmp_power.tif
    
    echo "        Warping"
    rio warp --like $example \
        --resampling $RESAMPLING \
        --src-nodata 0 \
        --dst-nodata 0 \
        --force-overwrite \
        --co "COMPRESS=LZW" \
        tmp_power.tif tmp_power_reproj.tif

    # Back to dB
    echo "        ... back to dB"
    rio calc "(* 10 (log10 (read 1 1)))" \
        -t float32 \
        --masked \
        --force-overwrite \
        tmp_power_reproj.tif $dest

    rm tmp_power.tif
    rm tmp_power_reproj.tif
}


for path in $P; do
    for row in $R; do
        src=$SRC/$path/$row
        echo "Working on path/row: $path/$row"
        if [ -d $src ]; then
            for pattern in $PATTERN; do
                for img in $(find $src -name $pattern); do
                    echo "    $img"
                    dname=$(basename $(dirname $(readlink -f $img)))
                    dst=$DST/$path/$row/$dname
                    mkdir -p $dst
                    
                    dstimg=$(basename $img)
                    dstimg=${dstimg/_DN_/_dB_}
                    reproj $EXAMPLE $img $dst/$dstimg
                done
            done
        fi
    done
done
