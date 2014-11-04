#!/bin/sh
###
#
# Chris Holden
#
##

to_lnd=1
if [ $1 -eq "0" ]; then
	to_lnd=0
	echo "Switching from LND to LE7/LT5/LT4"
else
	echo "Switching from LE7/LT5/LT4 to LND"
fi

cd $2

repl=LND

l_dir=`find . -maxdepth 1 -name 'L*' -exec basename {} \;`
for l in $l_dir
do
	if [ $to_lnd -eq "0" ]; then
		repl=`find $l -maxdepth 1 -name 'L*.tar.*z' -exec basename {} \;`
		repl=${repl:0:3}
	fi	
	# Find first three char of each ID
	l_type=${l:0:3}
	# Replace with "LND"
	l_new=${l/$l_type/$repl}
	# Rename folder
	echo $l
	echo $l_new
	if [ ! $l == $l_new ]; then
		echo "Moving $l to $l_new"
		mv $l $l_new		
	fi
	echo "<------------------------->"
done
