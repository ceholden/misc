#!/bin/bash

set -e

resume=1
if [ "$1" == "0" ]; then
    resume=0
fi

# Download destination
from=/projectnb/landsat/datasets/PRISM/download/
dest=/projectnb/landsat/datasets/PRISM/data/
if [ ! -d $dest ]; then
    mkdir -p $dest
fi

element="ppt tmin tmax tmean"
monthly="$from/monthly"
normals="$from/normals"

for ele in $element; do
    to=$dest/monthly/$ele
    if [ ! -d $to ]; then
        mkdir -p $to
    fi
    for z in $monthly/$ele/*zip; do
        unzip -q -u -d $to/ $z
    done

    to=$dest/normals/$ele
    if [ ! -d $to ]; then
        mkdir -p $to
    fi
    for z in $normals/$ele/*zip; do
        unzip -q -u -d $to/ $z
    done

done
