#!/bin/sh
# script to rename completed 'browse' image directories since the bands
# are wrong for wv-2

cd /net/casrs1/volumes/cas/modisk/moscratch/dsm/viirs_preprocess/test_in

prep=`find . -type d -name '2-Preprocess'`

for p in $prep; 
do 
		scene=`echo $p | awk -F '/' '{ print $2 }'`; 
		date=`echo $p | awk -F '/' '{ print $3 }'`; 
		img=`find $p -name ${scene}_${date}.bsq`; 
		if [ "$img" != "" ]; then 
				b8=`gdalinfo -norat -nomd $img | grep 'Band 8'`; 
				if [ "$b8" != "" ]; then 
						browse=`find $p -name 'browse' -type d`; 
						if [ "$browse" != "" ]; then 
								echo $browse; 
								mv $browse $p/wrong_browse; 
						fi; 
				fi; 
		fi; 
done
