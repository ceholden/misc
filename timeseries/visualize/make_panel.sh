#!/bin/bash

set -e

dest=stretches/panel
if [ ! -d $dest ]; then
    mkdir -p $dest
fi

for y in $(seq 1985 2012); do
    echo $y
    convert \
        stretches/changes/change_$((y + 1)).png \
        stretches/preds/pred_$y-06.png \
        stretches/slopes/slope_b5_$y.png \
        +append \
        $dest/panel_$y.png

    convert \
        $dest/panel_$y.png \
        -gravity South \
        -pointsize 48 \
        -fill white \
        -annotate 0 "$y" \
        $dest/panel_annotate_$y.png
done

convert -delay 100 -loop 0 $dest/panel_annotate_*png tc_nahanni.gif
