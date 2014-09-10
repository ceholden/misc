#!/bin/bash
#$ -V
#$ -N stack
#$ -l h_rt=96:00:00
#$ -j y

module purge
module load python/2.7.5
module load gdal/1.10.0

if [ -z $1 ]; then
    echo "Error - must specify location"
    exit 1
fi
loc=$1

if [ -z $2 ]; then
    echo "Error - must specify UTM zone overide"
    exit 1
fi
utmzone=$2

echo "Working on: $loc"

cd $loc

### Newer ESPA format
files=""
for n in 1 2 3 4 5 7; do
    files="$files L*sr_band${n}.tif;"
done
files="$files L*_toa_band6.tif; L*Fmask"

landsat_stack.py --files "$files" \
    -p --ndv "-9999; -9999; -9999; -9999; -9999; -9999; -9999; 255" \
    --utm "$utmzone" -o '_stack' \
    --co "INTERLEAVE=BIP" \
    --percentile 1 ./ 
    

### Old HDF format
# landsat_stack.py -q --files "lndsr*hdf; *Fmask" \
#     --bands "1 2 3 4 5 6 15; 1" \
#     -p --ndv "-9999 -9999 -9999 -9999 -9999 -9999 -9999; 255" \
#     --utm 18 -o '_stack' --percentile 1 \
#     images/

