#!/bin/bash

set +e

resume=1
if [ "$1" == "0" ]; then
    resume=0
fi

srcwin="700 1000 1000 1500"
resize=50

# PREDICTIONS
dest=stretches/preds
if [ ! -d $dest ]; then
    mkdir -p $dest
fi

for y in $(seq 1985 2013); do 
    if [ "$resume" == 1 -a -f $dest/pred_$y-06.png ]; then
        echo "Already stretched prediction for $y"
        continue
    fi
    ~/Documents/misc/preview/gen_preview.py -v \
        --bands "5 4 3" \
        --srcwin "$srcwin" \
        --mask 1 --maskval -9999 \
        --manual "0 4000; 0 6000; 0 3000" \
        --resize_pct $resize --format PNG \
        tc_nahanni/preds/nahanni_predict_$y-06-01.gtif $dest/pred_$y-06.png
done
echo "Complete"

# CHANGEMAPS
dest=stretches/changes
if [ ! -d $dest ]; then
    mkdir -p $dest
fi

for y in $(seq 1986 2014); do
    if [ "$resume" == "1" -a -f $dest/change_$y.png ]; then
        echo "Already stretched changemap for $y"
        continue
    fi
    gdal_translate \
        -outsize ${resize}% ${resize}% \
        -srcwin $srcwin \
        -ot Byte \
        tc_nahanni/changes/change_num_$((y - 1))_$y.gtif \
        tmp.gtif
    gdaldem color-relief -of PNG \
        tmp.gtif \
        colormaps/change.cmap \
        $dest/change_$y.png
done
echo "Complete"
rm tmp.gtif

# SLOPES
dest=stretches/slopes
if [ ! -d $dest ]; then
    mkdir -p $dest
fi

for y in $(seq 1985 2013); do
    if [ "$resume" == "1" -a -f $dest/slope_b5_$y.png ]; then
        echo "Already stretched slope for $y"
        continue
    fi
    gdal_translate \
        -outsize ${resize}% ${resize}% \
        -srcwin $srcwin \
        tc_nahanni/slopes/slope_b5_$y-06-01.gtif \
        tmp.gtif
    gdaldem color-relief -of PNG \
        tmp.gtif \
        colormaps/slope.cmap \
        $dest/slope_b5_$y.png
done
echo "Complete"
rm tmp.gtif
