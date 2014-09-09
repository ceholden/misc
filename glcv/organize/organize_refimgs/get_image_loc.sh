#!/bin/sh
# ceholden
#
# Purpose: finds reference images and outputs location to csv with format:
# fid, directory to bsq

# Catalog directory
catalog='/net/casrs1/volumes/cas/glcv/reference_images/catalog'
cd $catalog

# Output csv
outcsv='/net/casrs1/volumes/cas/landsat22/validation/database/fid_imageloc.csv'

# Init csv file
echo 'fid, date, image' > $outcsv

# get dirs
dirs=`find * -maxdepth 0 -type d`

for refimg in $dirs;
do
	echo "<-------------->"
	echo "Entering: ${refimg}"
	cd $refimg
	# get dates
	dates=`ls`
	for date in $dates;
	do
		cd $date
		cd '2-Preprocess'
		image=`find * -name '*.bsq'`
		image="`pwd`/$image"
		echo "${refimg}, ${date}, ${image}" >> $outcsv
		# Go back from 2-Preprocess and date
		cd ../..
	done
	# go back to catalog
	cd $catalog
done

