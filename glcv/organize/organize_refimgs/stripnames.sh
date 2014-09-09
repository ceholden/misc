#!/bin/sh
# ceholden 8/3/2012

# Function to rename files
function renamestuff {

	for file in ${fid}*; 
	do
		# Check what kind of file
		ext=${file#*.}
		if [[ "$ext" == "bsq" || "$ext" == "bsq.hdr" ]]; then
			id=`echo $file | awk 'BEGIN { FS = "_" }; { print $1 }'`
			id=`echo $id | tr -d ' '`

			date=`echo $file | awk 'BEGIN { FS = "_" }; { print $NF }'`
			date=`echo $date | tr -d ' '`

			name=`echo "${id}_${date}" | tr -d ' '`
		else
			id=`echo $file | awk 'BEGIN { FS = "_" }; { print $1 }'`
			id=`echo $id | tr -d ' '`

			date=`echo $file | awk 'BEGIN { FS = "_" }; { print $(NF-1)}'`
			date=`echo $date | tr -d ' '`

			utm=`echo $file | awk 'BEGIN { FS = "_" }; { print $NF }'`
			utm=`echo $utm | tr -d ' '`
		
			name=`echo "${id}_${date}_${utm}" | tr -d ' '`
		fi

		echo $name

		if [ $bRename -eq 1 ]; then
			mv $file $name
		fi
	done
}

# Rename or just test?
bRename=$1
if [ "$bRename" == "" ]; then
	bRename=0
fi
echo Move stuff? ${bRename}

# START
# change directory

rootdir='/net/casrs1/volumes/cas/landsat25/reference_images/catalog'
cd $rootdir

# get list of dirs to change
dirs=`ls | grep _`

for d in $dirs;
do
	echo "<-------------------->"
	echo "Entering: ${d}"
	# get scene id
	fid=`echo $d | awk 'BEGIN { FS = "_" }; { print $1 }' | tr -d ' '`
	# change to scene dir
	cd $d
	# get dates
	dates=`ls`
	for dat in $dates;
	do
		echo "Date: ${dat}"
		cd $dat
		# change directory to 2-Preprocess
		cd 2-Preprocess
		# rename files
		renamestuff
		# go back to date dir
		cd ..
		# go back to scene dir
		cd ..
	done
	# change back to root dir
	cd $rootdir
	# rename folder
	if [ $bRename -eq 1 ]; then
		echo "Moved ${d} to ${fid}"
		mv $d $fid
	else
		echo "Would move ${d} to ${fid}"
	fi
done
	
	













