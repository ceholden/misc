#!/bin/sh

resume=1

# Multithreaded bzip2
zip=/net/casfsb/vol/ssrchome/active_users/ceholden/tools/pbzip2/bin/pbzip2

# Location of backup
backup=/net/archive/ifs/archive/project/modislc/archive/IDS_stacks

# Set path/row to input $1
pr=$1
if [ ! -d $pr ]; then
	echo "Error: no such directory"
	exit 1
else
	echo "Backing up $pr with $NSLOTS processors"
	cd $pr
fi

# If path/row folder exists, create folder for it in archive space
backup=$backup/$pr
if [ ! -d $backup ]; then
	mkdir $backup
	if [ `echo $?` == 0 ]; then
		echo "Backing up to $backup"
	else
		echo "Error creating $backup"
		exit 1
	fi
else
	echo "Backing up to $backup"
fi
	

# Go into stack folder 'images'
if [ ! -d images/ ]; then
	echo "Could not find stack folder 'images'"
	exit 1
else
	cd images/
fi

# Make a temp directory for archive purposes
if [ ! -d archive_tmp ]; then
	mkdir archive_tmp
fi

# Find all Landsat stack folders
stacks=`find -L . -maxdepth 1 -name 'L*' -type d -exec basename {} \;`
n_stack=`find -L . -maxdepth 1 -name 'L*' -type d | wc -l`
echo "Found $n_stack images to backup. Proceeding..."
echo ""

# Go through stacks doing tar.bz2 compression & rsync to archive
count=1
for stack in $stacks; do
	echo "--------------------------------------------------"
	echo "Starting on $stack ($count / $n_stack)"
	
	# If we want to resume, check backup location for archive
	if [ $resume -eq 1 ]; then
		check=`find $backup -name "$stack.tar.bz2" -type f`
		if [ "$check" != "" ]; then
			echo "Already backed up $stack. Continuing..."
			let count+=1
			continue
		fi
	fi

	# Select files for archiving
	met=`find $stack -name '*.txt'`
	stk=`find $stack -name '*stack*'`
	fmk=`find $stack -name '*Fmask*'`
	log=`find $stack -name '*.log'`
	files=`echo $met $stk $fmk $log`
	
	# Multithread bzip2 the archive (don't keep tar)
	echo "Zipping using pbzip2"
	tar -c $files | $zip -c -q -p${NSLOTS} > archive_tmp/$stack.tar.bz2
	if [ `echo $?` != 0 ]; then
		echo "Error compressing archive for $stack"
		exit 1
	fi

	# Rsync to backup location
	echo "Copying to backup location"
	rsync -av --remove-source-files archive_tmp/$stack.tar.bz2 $backup
	if [ `echo $?` != 0 ]; then
		echo "Error rsyncing $stack"
		exit 1
	fi

	let count+=1
done

# Remove temporary stuff
rmdir archive_tmp

echo "Done with backup!"
