#!/bin/bash

set -e

# SETUP FOR GEO/SCC
HOST=$(hostname)
if [ "${HOST:0:3}" == "geo" ] || [ "${HOST:0:3}" == "scc" ]; then
    export PATH=/usr3/graduate/ceholden/Documents/misc/spectral:$PATH
    module load ImageMagick
fi

# TEST IF NECESSARY PROGRAMS ARE AVAILABLE
hash stretches.py || {
    echo "ERROR: Cannot find 'stretches.py' from https://github.com/ceholden/misc"
    exit 1
}
hash  convert || {
    echo "ERROR: Cannot find 'convert' from ImageMagick"
    exit 1
}
STRETCH=stretches.py

# Parse CLI
if [ -z $1 ]; then
    echo "ERROR: Must supply output directory as first argument"
    exit 1
fi
OUT=$1


# STYLE

ANNOTATE=0

# 3x 1920x1080
# BOUNDS="209565.0 4671855.0 382365.0 4704255.0"

# 3x 3840x2160
BOUNDS="228495.0 4638585.0 574095.0 4703385.0"

#FORMAT=JPEG
#EXT=jpg
FORMAT=GTiff
EXT=tif

PTSIZE=100
GRAVITY=South

# DETAILS
ROOT=/projectnb/landsat/projects/Massachusetts/p012r031/images

OUT=$OUT/$FORMAT/
TMP=${OUT}/TEMP
CLIPPED=$OUT/../clipped
B543=$OUT/B543
B432=$OUT/B432

mkdir -p $CLIPPED
mkdir -p $B543
mkdir -p $B432

pretty_date () { date -d "$1-01-01 +$2 days -1 day" "+%b %e, %Y"; }
sort_date() { date -d "$1-01-01 +$2 days -1 day" "+%Y%m%d"; }

clip_stretch() {
    echo "Working on: $2"

    img=$1
    name=$2
    prefix="$3"

    clipped=$CLIPPED/$name.gtif

    if [ ! -f $clipped ]; then
    #    rio clip --bounds $BOUNDS $img $clipped
        gdal_translate \
            -srcwin 1011 1147 11520 2160 \
            $img $clipped
    fi

    if [ ! -f $B543/$name.${EXT} ]; then
        $STRETCH \
            -b 5 -mm 500 3500 \
            -b 4 -mm 0 6000 \
            -b 3 -mm 0 2500 \
            -f $FORMAT -ot uint8 \
            --ndv -9999 --ndv 20000 \
            --co "QUALITY=95" \
            $clipped $B543/${prefix}$name.${EXT} linear
    fi

    if [ ! -f $B432/$name.${EXT} ]; then
        $STRETCH \
            -b 4 -mm 0 6000 \
            -b 3 -mm 0 2500 \
            -b 2 -mm 0 2500  \
            -f $FORMAT -ot uint8 \
            --ndv -9999 --ndv 20000 \
            --co "QUALITY=95" \
            $clipped $B432/${prefix}$name.${EXT} linear
    fi
}

annotate() {
    name=$1

    year=${name:9:4}
    doy=${name:13:3}
    _date=$(pretty_date $year $doy)
    _sort_date=$(sort_date $year $doy)

    sensor_id=${name:0:3}
    if [ "$sensor_id" == "LC8" ]; then
        sensor="Landsat 8"
    elif [ "$sensor_id" == "LE7" ]; then
        sensor="Landsat 7"
    elif [ "$sensor_id" == "LT5" ]; then
        sensor="Landsat 5"
    elif [ "$sensor_id" == "LT4" ]; then
        sensor="Landsat 4"
    fi

    for d in $B543 $B432; do
        img=$d/${name}.${EXT}
        out=$d/../${_sort_date}_${name}.${EXT}

        convert $img \
            -pointsize $PTSIZE \
            -gravity $GRAVITY \
            -stroke 'black' -strokewidth 4 -fill white \
            -annotate 0 "${sensor}\n${_date}" \
            $out
    done
}

for img in $(find $ROOT/LC8* -name 'L*_all'); do
    name=$(echo $(basename $img) | awk -F '_' '{ print $1 }')
    if [ "$ANNOTATE" == "1" ]; then
        clip_stretch $img $name
        annotate $name
    else
        year=${name:9:4}
        doy=${name:13:3}
        _sort_date=$(sort_date $year $doy)

        clip_stretch $img $name ${_sort_date}_
    fi
done

if [ "$ANNOTATE" == "1" ]; then
    for d in $B543 $B432; do
        for img in $d/*.${EXT}; do
            name=$(basename $img .${EXT})
            year=${name:9:4}
            doy=${name:13:3}
            _date=$(pretty_date $year $doy)
            _sort_date=$(sort_date $year $doy)

            out=$d/../${_sort_date}_${name}.${EXT}

            convert $img \
                -pointsize $PTSIZE \
                -gravity $GRAVITY \
                -stroke '#000C' -strokewidth 2 \
                -stroke  none   -fill white \
                -annotate 0 "$_date" \
                $out
        done
    done
fi

echo "Complete!"
