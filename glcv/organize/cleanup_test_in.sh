#!/bin/sh

here=/net/casrs1/volumes/cas/modisk/moscratch/dsm/viirs_preprocess/test_in

cd $here

scenes=`find . -maxdepth 1 -regex '.*[0-9]' -type d -exec basename {} \;`

for scene in $scenes;
do
	cd $scene
	dates=`find . -maxdepth 1 -type d -regex '.*[0-9]'`
	for date in $dates;
	do
		cd $date
		echo "$scene"
		find 1-Order -maxdepth 1 -name "${scene}_*mul*" -delete
		find 1-Order -maxdepth 1 -name "${scene}_*mss*" -delete
		find 1-Order -maxdepth 1 -name "${scene}_*bsq*" -delete
		find 1-Order -maxdepth 1 -name "${scene}_*pan*" -delete
		cd ..
	done
	cd $here
done
