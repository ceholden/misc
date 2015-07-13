#!/bin/bash

reproj=/usr3/graduate/ceholden/code/misc/radar/stack_radar_wrs2.sh

src=/projectnb/landsat/projects/CMS/RADAR/ALOS_PALSAR/josef_colombia/la_victoria_srtm1
here=/projectnb/landsat/projects/CMS/stacks/Colombia/p008r056/subset/RADAR
ex_img=/projectnb/landsat/projects/CMS/stacks/Colombia/p008r056/subset/example_img
pattern='*_s1_g15_mtfil_3_dB'

cd $here
for i in $(find $src -maxdepth 1 -name 'A*' -type d); do
    echo "<------------------------------------------------------------"
    id=$(basename $i)
    echo "Working on: $id"
    mkdir $id
    # Find hh/hv/ratio images
    for type in hh hv ratio; do
        img=$(find $i -name "${pattern}_${type}.vrt")
        if [ ! -z $img ]; then
            echo "    Found $type"
            $reproj $img $ex_img $id/$(basename $img .vrt).gtif
        fi
    done
done

for d in ALPSRP*; do
    hh=$(find $d/ -name '*hh.gtif')
    hv=$(find $d/ -name '*hv.gtif')
    ratio=$(find $d/ -name '*ratio.gtif')

    if [ ! -z $hh ] && [ ! -z $hv ] && [ ! -z $ratio ]; then
        echo "Making HH/HV/Ratio RGB VRT"
        gdalbuildvrt -q -separate $d/$(basename $hh _hh.gtif).vrt $hh $hv $ratio
    fi
done

