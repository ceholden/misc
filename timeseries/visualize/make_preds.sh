#!/bin/bash

root=/projectnb/modislc/projects/te_phenology/landsat_stacks/tc_nahanni/OVERLAP

for y in $(seq 1985 2013); do 
    for m in 03 06 09; do 
        echo "$y - $m"
        ~/Documents/yatsm_v0.3.0/scripts/yatsm_map.py -v \
            --root $root \
            --image LT50530172011148PAC01/LT50530172011148PAC01_stack \
            --before --after \
            --ndv -9999 \
            predict $y-$m-01 tc_nahanni/preds/nahanni_predict_$y-$m-01.gtif
    done
done

echo "Complete"
