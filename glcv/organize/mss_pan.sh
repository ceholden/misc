#!/bin/sh

###
#
# Author:		Chris Holden
# Date:			12/14/2012
# Purpose:		Counts number of pan/mss pairs from USGS
#
###

# Counter for mss/pan pairs
pair_count=0
# Counter for only pan
pan_count=0
# Counter for only mss
mss_count=0

#start=/net/casrs1/volumes/cas/glcv/reference_images/catalog/USGS_UPLOAD/98_sites_high_res_imagery

start=$1
# Check if not specified, default to `pwd`
if [ "$1" == "" ]; then
		start=`pwd`
fi
# Check if directory exists
if [ -d $start ]; then
		echo "Looking in: $start"
		cd $start
else
		echo "Error: $1 is not a directory."
fi

echo "<------------------------->"
echo "<         Start           >"
echo "<------------------------->"

sites=`find . -maxdepth 1 -name 'site_*'`
for site in $sites
do
		echo "Site: $site"
		cd $site
		pan=`find . -type f -name '*pan_ortho*'`
		echo "Pan: $pan"
		mss=`find . -type f -name '*mss_ortho*'`
		echo "MSS: $mss"
		if [[ "$pan" != "" && "$mss" != "" ]]; then
				let pair_count=pair_count+1
				echo "Found pair"
		fi
		if [[ "$pan" != "" && "$mss" == "" ]]; then
				let pan_count=pan_count+1
		fi
		if [[ "$mss" != "" && "$pan" == "" ]]; then
				let mss_count=mss_count+1
		fi

		echo "<-------------------->"
		cd $start
done

echo "Found $pair_count pairs."
echo "Found $mss_count sites with only MSS"
echo "Found $pan_count sites with only PAN"
