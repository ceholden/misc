#!/bin/sh

set +e 

usage () {
    cat << EOF

    usage: $0 <input_dir> <output_dir>

    Author: Chris Holden (ceholden@gmail.com)

    Purpose: Compress a Landsat stack directory to archival directoy

    Options:
        -r          Resume - don't overwrite existing archives (default: 1)
        -n          Number of CPUs to use (default: '$NSLOTS' or 4)
        -h          Show help
EOF
    exit 1
}

resume=1
ncpu=4
if [ ! -z $NSLOTS ]; then
    ncpu=$NSLOTS
fi

# Parse opts and args
while getopts ":r:n:h" o; do
    case "${o}" in
        r)
            resume=${OPTARG}
            ((s != 1 || s != 0) || usage)
            ;;
        n)
            ncpu=${OPTARG}
            ;;
        *)
            usage
            ;;
    esac
done
shift $((OPTIND-1))

if [ -z $1 ] || [ -z $2 ]; then
    usage
fi

input=$1
output=$2

if [ ! -d $input ]; then
    echo "Error: <input_dir> $input is not a directory"
    usage
fi
if [ ! -d $output ]; then
    echo "Error: <output_dir> $output is not a directory"
    usage
fi

echo "Backing up $input with $ncpu processors"

# If path/row folder exists, create folder for it in archive space
backup=$output/$(basename $input)
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
	
cd $input
# Go into stack folder 'images'
if [ ! -d images/ ]; then
	echo "Could not find stack folder 'images' within $input"
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
	tar -c $files | pbzip2 -c -q -p${ncpu} > archive_tmp/$stack.tar.bz2
	if [ `echo $?` != 0 ]; then
		echo "Error compressing archive for $stack"
		exit 1
	fi

	# Rsync to backup location
	echo "Copying to backup location"
	rsync -a --remove-source-files archive_tmp/$stack.tar.bz2 $backup
	if [ `echo $?` != 0 ]; then
		echo "Error rsyncing $stack"
		exit 1
	fi
    
    rm archive_tmp/$stack.tar.bz2
	let count+=1
done

# Remove temporary stuff
rmdir archive_tmp

echo "Done with backup!"
