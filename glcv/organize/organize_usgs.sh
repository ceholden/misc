#!/bin/sh
###
#
# Author:	Chris Holden
# Date:		1/8/2013
# Purpose:	To organize images from USGS into standardized BU folder structure
#
###

start=/net/casrs1/volumes/cas/glcv/scratch/usgs
cd $start

site_dirs=`find . -maxdepth 1 -name 'site*' -type d`

for site_dir in $site_dirs
do
	# First, make normal BU index (i.e. strip site_)	
	s=`echo $site_dir | tr -d 'site_'`
	# Make directory for each site
	mkdir $s
	# Move contents of original USGS name into new folder
	mv $site_dir/* $s
	# Remove old USGS name
	rmdir $site_dir
	site_dir=$s
	# Go to new directory
	cd $site_dir
	# Try stripping any spaces in file name
	rename ' ' '' *	
	# Loop over each file in root directory for organization
	files=`find . -maxdepth 1 -name 'site*'`
	for f in $files
	do
		# Fetch the year, month, date of each file
		year=`echo $f | awk -F '_' ' { print $3 } '`
		month=`echo $f | awk -F '_' ' { print $4 } '`
		day=`echo $f | awk -F '_' ' { print $5 } '`
		# Format into YEAR-DOY
		yeardoy=`date -d $year-$month-$day +%Y-%j`
		# Try making directory and moving file into it
		if [ -d $yeardoy ]; then
			mv $f $yeardoy
			echo "Moved $f into $yeardoy"
		else
			mkdir $yeardoy
			mv $f $yeardoy
			echo "Moved $f into $yeardoy"
		fi
	done
	# Now that we have organized into dates, let's setup structure in each
	years=`find . -maxdepth 1 -name '2*' -type d`
	for y in $years
	do
		# Standard structure
		mkdir $y/1-Order
		mkdir $y/2-Preprocess
		mkdir $y/3-Segment
		mkdir $y/4-Classify
		mkdir $y/5-Classify_Edits
		# Move USGS date into "1-Order"
		mv $y/site* $y/1-Order/
	done
	echo "Done with $site_dir"
	cd $start
	sleep 10
done
