#!/bin/bash

root=/projectnb/modislc/projects/te_phenology/landsat_stacks/tc_nahanni/OVERLAP
dest=tc_nahanni/changes

if [ ! -d $dest ]; then
    mkdir -p $dest
fi

for y in $(seq 1986 2014); do
    echo $y
    ~/Documents/yatsm_v0.3.0/scripts/yatsm_changemap.py -v \
        --root $root \
        --image LT50530172011148PAC01/LT50530172011148PAC01_stack \
        --ndv 0 \
        num $((y - 1))-06-01 $y-06-01 $dest/change_num_$((y - 1))_$y.gtif
done

echo "Complete"
