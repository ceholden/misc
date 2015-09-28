#!/bin/bash

set -e

resume=1
if [ "$1" == "0" ]; then
    resume=0
fi

# Download destination
dest=/projectnb/landsat/datasets/PRISM/data/
if [ ! -d $dest ]; then
    mkdir -p $dest
fi


# Definitions for URL
base="http://services.nacse.org/prism/data/public/"
element="ppt tmin tmax tmean"

monthly_url="${base}/4km/"
normals_url="${base}/normals/4km"

for ele in $element; do
    for mm in 0{1..9} {10..12}; do
        # Normals
        d=$dest/normals/$ele
        if [ ! -d $d ]; then
            mkdir -p $d
        fi

        f=$d/PRISM_${ele}_30yr_normal_4kmM2_${mm}_bip.zip
        if [ ! -f $f -o "$resume" == "0" ]; then
            echo "Downloading $ele normals for month $mm"
            wget -q --content-disposition $normals_url/$ele/$mm -O $f
            sleep 2
        fi
        
        # Monthly
        for yy in {1981..2015}; do
            d=$dest/monthly/$ele
            if [ ! -d $d ]; then
                mkdir -p $d
            fi
            
            f=$d/PRISM_${ele}_stable_4kmM2_${yy}${mm}_bil.zip
            if [ ! -f $f -o "$resume" == "0" ]; then
                echo "Downloading monthly $ele data for year-month $yy-$mm"
                wget -q --content-disposition $monthly_url/$ele/$yy$mm -O $f
                sleep 2
            fi
        done
        # Done with month $mm
    done
    # Done with product $ele
done
