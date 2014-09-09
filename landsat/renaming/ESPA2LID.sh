#!/bin/bash
###
#
# Renames ESPA IDs (e.g., LT50080562000235-SC20140904152740) to Landsat IDs
#   (e.g., LT50080561998213XXX00)
#
###

# Verbose
verbose=0
if [ "$1" == "1" ]; then
    verbose=1
fi

for d in $(find ./ -maxdepth 1 -type d -name 'L*-SC*'); do
    mtl=$(find $d -name 'L*MTL.txt');
    id=$(basename $mtl "_MTL.txt")

    if [ $verbose -eq 1 ]; then
        echo "$d -> $id"
    fi

    mv $d $id

done
