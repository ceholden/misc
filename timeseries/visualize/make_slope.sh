#!/bin/bash

root=/projectnb/modislc/projects/te_phenology/landsat_stacks/tc_nahanni/OVERLAP
dest=tc_nahanni/slopes

if [ ! -d $dest ]; then
    mkdir -p $dest
fi

for y in $(seq 1985 2013); do 
    echo $y
    ~/Documents/yatsm_v0.3.0/scripts/yatsm_map.py -v \
        --root $root \
        --image LT50530172011148PAC01/LT50530172011148PAC01_stack \
        --before --after \
        --ndv -9999 \
        --coef slope \
        --band 5 \
        coef $y-06-01 $dest/slope_b5_$y-06-01.gtif
done

echo "Complete"
