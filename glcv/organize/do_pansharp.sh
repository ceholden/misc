#!/bin/sh
#$ -V
#$ -l h_rt=24:00:00

# Pansharpening script
batch_psh=/net/casfsb/vol/ssrchome/active_users/ceholden/batch_pansharp.sh

# Base directory
start=/net/casrs1/volumes/cas/glcv/scratch/usgs
# Go to it
cd $start

# Loop through all sites
sites=`find . -maxdepth 1 -type d -regex '.*/[0-9].*'`
echo "Sites: $sites"
for site in $sites
do
	echo "<------------------------->"
	# Go to each site
	site=`echo $site | tr -d ./`
	cd $site
	echo "Site: $site"
	# Find all dates within site
	dates=`find . -maxdepth 1 -type d -regex '.*/[0-9].*'`
	# Loop through dates
	for date in $dates
	do
		echo "<---------->"
		date=`echo $date | tr -d ./`
		cd $date
		echo "Date: $date"
		# Setup output name
		psh_out=""
		if [ -d 2-Preprocess ]; then
			# Get full name of directory
			psh_out=`readlink -f 2-Preprocess`
			psh_out=$psh_out/${site}_${date}.bsq
		else
			echo "ERROR: Site $site for $date does not have 2-Preprocess setup"
		fi
		# Find multispectral and panchromatic images for sharpening
		mss_in=""
		pan_in=""
		# Boolean for north/south pair
		north_south=0
		# Search 1-Order for images
		if [ -d 1-Order ]; then
			n=`find 1-Order/ -maxdepth 1 -name 'site*north*mss_ortho*.img'`
			# Check if multiple results
			if [ "$n" != "" ]; then
				echo "Site $site for $date has north/south pair"
				north_south=1
			fi
			mss_in=`find 1-Order/ -maxdepth 1 -name 'site*mss_ortho*.img'`
			pan_in=`find 1-Order/ -maxdepth 1 -name 'site*pan_ortho*.img'`
		else
			echo "ERROR: Site $site for $date does not have 1-Order setup"
		fi
		# Check if we found anything...
		if [[ "$mss_in" != "" && "$pan_in" != "" ]]; then
			# Modification for north/south pair
			if [ "$north_south" == "1" ]; then
				## Do north
				mss_in=`find 1-Order/ -maxdepth 1 -name 'site*north*mss_ortho*.img'`
				pan_in=`find 1-Order/ -maxdepth 1 -name 'site*north*pan_ortho*.img'`
				psh_out=`readlink -f 2-Preprocess`
				psh_out=$psh_out/${site}_N_${date}.bsq
				echo "MSS: $mss_in"
	            echo "PAN: $pan_in"
	            mss_in=`readlink -f $mss_in`
	            pan_in=`readlink -f $pan_in`
	            # Setup command
				call="$batch_psh $mss_in $pan_in $psh_out N"
				echo "CALL: $call"
				$call
				## Do south
				mss_in=`find 1-Order/ -maxdepth 1 -name 'site*south*mss_ortho*.img'`
                pan_in=`find 1-Order/ -maxdepth 1 -name 'site*south*pan_ortho*.img'`
				psh_out=`readlink -f 2-Preprocess`
				psh_out=$psh_out/${site}_S_${date}.bsq
				echo "MSS: $mss_in"
				echo "PAN: $pan_in"
				mss_in=`readlink -f $mss_in`
				pan_in=`readlink -f $pan_in`
				# Setup command
				call="$batch_psh $mss_in $pan_in $psh_out S"
				echo "CALL: $call"
				$call
			else
				# Otherwise just do once
				echo "MSS: $mss_in"
				echo "PAN: $pan_in"
				mss_in=`readlink -f $mss_in`
				pan_in=`readlink -f $pan_in`
				echo "CALL:"
				echo "$batch_psh $mss_in $pan_in $psh_out"
				$batch_psh $mss_in $pan_in $psh_out
			fi
		else
			echo "For site $site date $date - could not find both MSS and PAN"
			echo "MSS: $mss_in" > 2-Preprocess/no_pair.log
			echo "PAN: $pan_in" >> 2-Preprocess/no_pair.log
		fi

		cd ..
	done
	cd $start
	mv $site /net/casrs1/volumes/cas/glcv/scratch/usgs/complete/
done
