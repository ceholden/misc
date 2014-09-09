#!/bin/bash
#$ -l h_rt=48:00:00
#$ -V
#$ -j y

here=$1

if [ ! -d $here ]; then
    echo "Error: $here is not a directory"
    exit 1
fi

echo "Adding overviews for: $here"

cd $here

n=`find ./ -maxdepth 2 -name '*stack' -type f | wc -l`
i=1
for stk in `find ./ -maxdepth 2 -name '*stack' -type f | sort`; do
    echo "Working on: $i / $n"
    gdaladdo -ro -r nearest \
        --config INTERLEAVE_OVERVIEW PIXEL \
        --config COMPRESS_OVERVIEW JPEG \
        -b 1 -b 2 -b 3 -b 4 -b 5 -b 6 -b 7 \
        $stk 2 4 8 16
    let i+=1
done
