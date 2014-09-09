#!/bin/sh
# ceholden 8/10/2012
# Purpose: get dates of refimgs, output to csv formatted as:
#	fid, date

# Image directory
rootdir='/net/casrs1/volumes/cas/landsat25/reference_images/catalog'
cd $rootdir

# Output csv file
outfile='/net/casrs1/volumes/cas/landsat22/validation/database/fid_dates.csv'

# Init csv file
echo 'fid, date' > $outfile

# get list of dirs to change
dirs=`ls`

for fid in $dirs;
do
	echo "<-------------------->"
	echo "Entering: ${fid}"
	# change to scene dir
	cd $fid
	# get dates
	dates=`ls`
	for date in $dates;
	do
		echo "${fid}, ${date}" >> $outfile
	done
	cd ..
done
