#!/bin/bash
#$ -V
#$ -l h_rt=48:00:00
#$ -j y

intersects=/usr3/graduate/ceholden/code/Vector/intersects_wrs2.py

trends=/projectnb/landsat/datasets/LandTrends/

if [ $# -eq 3 ]; then
    row=$3
    path=$2
    dir=$1
else
    echo "Please specify <location> <path> <row>"
    echo ""
    echo "Example: $0 ./ 012 031"
    echo ""
    exit 1
fi

if [ ! -d $dir ]; then
    echo "Error - $dir is not a directory"
    exit 1
fi

echo "Working on $dir"
echo "    path $path row $row"

cd $dir

if [ ! -d LandTrends ]; then
    mkdir LandTrends
fi

for eco in `find $trends -maxdepth 1 -name 'Eco[0-9][0-9]' -type d`; do 
    for d in `find $eco -maxdepth 1 -name 'samp*' -type d`; do 
            s=`find $d -name 'samp*img' -type f | head -1`
            $intersects --a_srs 42303 -q $path $row $s
            if [ $? -eq 1 ]; then 
                echo "$s matches"
                cp -R $d LandTrends/ 
            fi
    done
done

echo "Done!"
