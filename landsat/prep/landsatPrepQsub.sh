#!/bin/bash

###
# 
# Name:     landsatPrepQsub.sh
# Version:  3.0
# Date:     10/27/2012
#
# Author:   Chris Holden (ceholden@bu.edu)
#
# Purpose:  For input Landsat tar.gz, extract and organize  each image by
#			path/row and year-day of year (year-doy). Then, atmospherically 
#			correct using LEDAPS and screen for clouds using Fmask.
#
###

line_num=''

function usage {
    cat << EOF
    
    usage: $0 [options] image_tarfile

    This script organizes and extracts Landsat .tar.gz scene archives into
    folders based on WRS-1 path-row and date. Next, it automates LEDAPS
    atmospheric correction and Fmask cloud and cloud shadow detection.

    Options:
        -h  help
        -c  cloud dilation parameter for FMASK
        -s  shadow dilation parameter for FMASK
		-p	cloud probability parameter for FMASK
		-d	delete TIF files?
        -l  do LEDAPS? 1 - yes, 0 - no (default $do_ledaps)
		-f  do FMask? 1 - yes, 0 - no (default $do_fmask)
		-x	do directory structure organization?	
		-g	check for L1G images and exit if found? (default $do_L1G)
        -u  unzip tar.gz? useful if not doing dir structure (default $do_unzip)
        -2  Use Fmask 2.1 instead of 3.2 (default $FMASK2)
EOF
}

function addSources {
    # Source for commands and ancillary data
	###
	# Changelog:
	#	12/08/2012 - change to Yang's compiled version
    #   06/02/2013 - new cluster. now use module system for LEDAPS
    #   12/19/2013 - option to use Qingsong's LC8 version of LEDAPS
	#   08/01/2014 - use Eric Vermote's LDCM SR
	###
    if [ -f /usr/local/Modules/default/init/bash ]; then
        . /usr/local/Modules/default/init/bash
    fi

    module load LDCM-SR/v1.3
    module load ledaps/20120925
    module load gdal/1.10.0
}

# Custom exit failure setup
function prepFail {
	echo "Error: failure for id " $tarfile " at line " $line_num >> fail.log
	echo "Directory: `pwd`" >> fail.log
	exit 1
}

function extract {
    if [ $do_unzip -eq 1 ]; then
	    ### Handle tar.gz and tar.bz
        # Get last file extension (i.e. compression type)
	    ext=`echo $tarfile | awk -F '.' ' { print $NF } '`
	    # Case - tar.gz
	    if [ "$ext" == "gz" ]; then
	    	# Extract tar.gz file
	    	tar -xvf $tarfile
	    elif [ "$ext" == "bz" ]; then
	    	# Extract tar.bz file
	    	bzip2 -cd $tarfile | tar xvf -
	    fi
	    # Check if success
	    if [ `echo $?` != 0 ]; then
	    	echo "Could not extract $tarfile"
	    	line_num=$LINENO
	    	prepFail
	    else
	    	echo "Exporting from archive completed"
	    fi
    else
        tifs=`find . -name '*.TIF'`
        mtl=`find . -name '*MTL.txt'`
        if [ "$tifs" == "" ]; then
            echo "Could not find TIF files. Please resubmit and unzip (-u 1)"
        fi
        if [ "$mtl" == "" ]; then
            echo "Could not find MTL file. Please resubmit and unzip (-u 1)"
        fi
    fi

	### CEHOLDEN: I don't think this does anything... test & delete
    # Go into extracted directory, if exists
    tardir=`echo $tarfile | tr -d .tar.gz`
    if [ -d $tardir ]; then
        cd $tardir
    fi

    # Find metadata file and scene id
    # Check for MTL format
	metadata=`find . -maxdepth 1 -name '*MTL.txt' -exec basename {} \;`
	# Did we find anything?
	if [ -z $metadata ]; then
		# If not, then try for NLAPS format
		metadata=`find . -maxdepth 1 -name 'L*_WO.txt' -exec basename {} \;`
		# Did this find anything?
		if [ -z $metadata ]; then
			echo "Error: Could not find either MTL or NLAPS metadata"
			exit 1
		else
			# If we did, parse into meta
			echo $metadata
			meta=`echo $metadata | tr -d .txt`
			echo $meta
		fi
	else 
		echo $metadata
		meta=`echo $metadata | sed -e 's/.txt//' -e 's/_MTL//' -e 's/.met//'`
		echo $meta
	fi
}

function checkMTLold {
    # Check if there's a file called "*MTLold.txt"
    if [ -e L*MTLold.txt ]; then
        # Rename "new" MTL file
        mtl_new=${meta}_MTLnew.txt
        mv $metadata $mtl_new
        # Rename "old" MTL file
        mtl_old=`ls L*MTLold.txt`
        cp $mtl_old $metadata
    # Print message
    echo 'Using "old" MTL file. "New" MTL file moved to: ' $mtl_new
    fi        
}

function checkL1G {
	# Check if image is L1G and not L1T
	l1g=$(grep -a 'DATA_TYPE.*"L1G"' $metadata)
	if [ ! -z "$l1g" ]; then
		echo "This image is L1G. Exiting"
		echo "Image $metadata is L1G" > L1G_fail.log
		# Removing TIF files
		removeExtra=1
		cleanUp
		exit
	fi
	echo "This image is not L1G. Proceeding."
}

function checkLC8 {
   
    spacecraft=$(grep "SPACECRAFT_ID" $metadata | \
        awk '{ print $3 }' | \
        tr -d '"')
    if [ "$spacecraft" == "LANDSAT_8" ]; then
        LC8=1
    else
        LC8=0
    fi
}

function get_sds() {
    if [ -z "$1" ] || [ -z "$2" ]; then
        echo "Missing arguments. Usage:"
        echo "    get_sds <raster> <bands>"
        return
    fi

    sds_names=""
    for b in $2; do
        sds=$(gdalinfo $1 | grep "SUBDATASET_${b}_NAME" | awk -F '=' '{ print $2 }')
        sds_names="$sds_names $sds"
    done
    echo "$sds_names"
}

function gdal_extent() {
    if [ -z "$1" ]; then 
        echo "Missing arguments. Syntax:"
        echo "  gdal_extent <input_raster>"
        return
    fi
    EXTENT=$(gdalinfo $1 |\
        grep "Upper Left\|Lower Right" |\
        sed "s/Upper Left  //g;s/Lower Right //g;s/).*//g" |\
        tr "\n" " " |\
        sed 's/ *$//g' |\
        tr -d "[(]" | tr "," " ")
    echo -n "$EXTENT"
}

function doLDCMSR {
    set -e

    echo "Running LDCM-SR located here: $(which LDCMSR)"

    processldcm_bu.sh $(readlink -f ./)

    echo "Converting LDCM-SR HDF output to referenced GTiff"

    sr=$(ls LC8*-sr.hdf)
    id=$(grep "LANDSAT_SCENE_ID" $metadata | awk '{ print $3 }' | tr -d '"')

    # Get geotransform and projection from a TIF
    b5=$(ls LC8*_B5.TIF)
    ext=$(gdal_extent $b5)
    proj=$(gdalinfo -proj4 $b5 | grep "+proj" | tr -d "'")

    # Find all subdatasets and make into VRT
    vrts=""
    for b in $(gdalinfo $sr | grep "SUBDATASET_.*_NAME" | awk -F '_' '{ print $2 }'); do
        temp_vrt=temp_${b}.vrt
        sds=$(get_sds $sr $b)

        gdal_translate -q -of VRT -ot Int16 $sds $temp_vrt
        
        gdal_edit.py -tr 30 30 $temp_vrt
        gdal_edit.py -a_srs "$proj" $temp_vrt
        gdal_edit.py -a_ullr $ext $temp_vrt

        vrts="$vrts $temp_vrt"
    done

    gdal_merge.py -o ${id}-sr.gtif -of GTiff -ot Int16 -separate $vrts

    cat <<-EOF | python - 
from osgeo import gdal
bands = ['Band 1 - Coastal',
         'Band 2 - Blue',
         'Band 3 - Green',
         'Band 4 - Red',
         'Band 5 - NIR',
         'Band 6 - SWIR1',
         'Band 7 - SWIR2',
         'Band 9 - Cirrus',
         'Band 10 - TIRS1',
         'Band 11 - TIRS2',
         'Band QA',
         'Cloud mask']
ds = gdal.Open('${id}-sr.gtif', gdal.GA_Update)
hdf = gdal.Open('$sr', gdal.GA_ReadOnly)

for i, (name, desc) in enumerate(hdf.GetSubDatasets()):
    sds = gdal.Open(name, gdal.GA_ReadOnly)
    ds.GetRasterBand(i + 1).SetMetadata(sds.GetMetadata())
    ds.GetRasterBand(i + 1).SetDescription(bands[i])
sds = None
hdf = None
ds = None
EOF

    rm temp_*.vrt

    set +e
}

function doLEDAPS { 
	ledapsDir=`which lndsr`
	echo "lndsr location: $ledapsDir"

    # Starting LEDAPS functions
    lndpm $metadata > ledaps.log
	if [ `echo $?` != 0 ]; then # if not success, then
		line_num=$LINENO
		prepFail
	fi
    echo "lndpm started"
    lndcal lndcal.$meta.txt >> ledaps.log
	if [ `echo $?` != 0 ]; then
		line_num=$LINENO
		prepFail
	fi
    echo "lndcal started"
    lndcsm lndcsm.$meta.txt >> ledaps.log
	if [ `echo $?` != 0 ]; then
		line_num=$LINENO
		prepFail
	fi
    echo "lndcsm started"
    lndsr lndsr.$meta.txt >> ledaps.log
	if [ `echo $?` != 0 ]; then
		line_num=$LINENO
		prepFail
	fi
    lndsrbm.ksh lndsr.$meta.txt >> ledaps.log
    
    # Changing directory back to original directory
    echo "LEDAPs ran correctly for "$metadata
}

function doFmask {
    # 1/23/2013:	unset license manager locations for MATLAB due to bug checking out license
	#				for mapping toolbox
	unset IDL_LMGRD_LICENSE_FILE
	unset LM_LICENSE_FILE	

	# Setup MATLAB execute command
    ML="/usr/local/bin/matlab -nodisplay -nojvm -singleCompThread -r "
    # Setup fmask commands
	# 10/23/2012: update for Fmask 2.1sav
    if [ "$FMASK2" -eq 0 ]; then
        fmask="addpath('/usr3/graduate/ceholden/tools/Fmask/');"
        fmask=$fmask"clr_pct=autoFmask(${c_dilate},${s_dilate},3,${c_prob});disp(clr_pct);"
    else
        fmask="addpath('/usr3/graduate/ceholden/tools/Fmask_2_1sav/');"
	    fmask=$fmask"autoFmask_2_1sav(${c_dilate},${s_dilate},${c_prob});"
    fi
    fmask=$fmask"exit;"

	# Print out
	echo "Starting FMASK: "
	echo $fmask

    # Run MATLAB & fmask
    $ML $fmask
}

function cleanUp {
    # Removes extracted images if specified
    if [ $removeExtra -eq 1 ]; then
        # Remove TIF and tif
		echo "Removing extracted single-band Landsat .TIF files"
		find . -maxdepth 1 -name "*.TIF" -exec rm {} \;

		# Remove other LEDAPS files
		# echo "Removing non-lndsr LEDAPS files"
		# find . -maxdepth 1 -iname "*lndcal*" -exec rm {} \;
		# find . -maxdepth 1 -iname "*lndcsm*" -exec rm {} \;
		# find . -maxdepth 1 -iname "*lndth*" -exec rm {} \;
		
		# echo "Removing other..."
		# b6cloud file
		# find . -maxdepth 1 -iname "*b6cloud*" -exec rm {} \;
    fi
}

# Main function
function doit {
	echo "<---------------------------------------->"
    echo "Starting process on "$tarfile
    # Make directory for path-row
    pathrow=`echo P${tarfile:3:3}-R${tarfile:6:3}`
	if [ $do_dir -eq 1 ]; then
		if [ ! -d $pathrow ]; then
			mkdir $pathrow
		fi
		mv $tarfile $pathrow
		cd $pathrow
    
		tarname=`echo $tarfile | awk -F '.' ' { print $1 } '`
		if [ ! -d $tarname ]; then
			mkdir $tarname
		fi
		mv $tarfile $tarname
		cd $tarname
	else
		echo "Not doing directory structuring..."
		echo "Working on: $tarfile"
		# tarname=`echo $tarfile | tr -d .tar.gbz`
		tarname=`find ./ -name $tarfile -exec dirname {} \;`
		if [ ! -d $tarname ]; then
			echo "Error: no directory named $tarname"
			echo "Error: fail for $tarfile"
			prepFail
		fi
		cd $tarname
		tarfile=`basename $tarfile`
	fi

	# Extract files 
	extract
	# 09-06-2012 ceholden: edit
	#   Add in check for "new" MTL file format
	#   Current version of LEDAPS doesn't support new tags
	# 02/03/2013 ceholden: edit
	#	New versions of Fmask & LEDAPS support new MTL file
	#	Commenting out this step	
	# checkMTLold
	# CEHOLDEN (11/23/2012): Check if image is L1G - quit if true
	if [ $do_L1G -eq 1 ]; then
		checkL1G
	fi
	
	# CEHOLDEN (10/23/2012): Fmask_2_1sav gets confused if LEDAPS is done first
	# Perform FMASK
	if [ $do_fmask -eq 1 ]; then
		doFmask
	fi
	# Perform LEDAPS
	if [ $do_ledaps -eq 1 ]; then
        checkLC8
        if [ "$LC8" -ne 1 ]; then
    		echo "Running SR correction on Landsat 4-7 - LEDAPS"
            doLEDAPS
        else
            echo "Running SR correction on Landsat 8 - LDCMSR"
            doLDCMSR
        fi
	fi
	# Clean up files?
	cleanUp
}

tarfile=''
metadata=''
removeExtra=0
c_dilate=3
s_dilate=3
c_prob=22.5
do_ledaps=1
do_fmask=1
do_dir=1
do_L1G=0
do_unzip=1
LC8=0
FMASK2=0

# Parse arguments
while getopts "hc:s:p:dl:f:x:g:u:2:" opt
do
        case $opt in
        h)
            usage
            exit 0
            ;;
        c)
            c_dilate=$OPTARG
            ;;
        s)
            s_dilate=$OPTARG
            ;;
		p)
			c_prob=$OPTARG
			;;
        d)
            removeExtra=1
            ;;
		l)
			do_ledaps=$OPTARG
			;;
		f)
			do_fmask=$OPTARG
			;;
		x)
			do_dir=$OPTARG
			;;
		g)
			do_L1G=$OPTARG
			;;
        u)
            do_unzip=$OPTARG
            ;;
        2)
            FMASK2=$OPTARG
            ;;
        esac
done

shift $(($OPTIND - 1 ))

# Parse positional entry
if [ -n "$1" ]; then
    tarfile=$1
else
	echo "Error: no tar.gz input"
	line_num=$LINENO
	prepFail
fi

echo 'Image: ' $tarfile
echo "Parameters: "
echo "Cloud dilate: " $c_dilate
echo "Shadow dilate: " $s_dilate
echo "Cloud probability: " $c_prob
echo "Remove TIF: " $removeExtra
echo "Do LEDAPS?: " $do_ledaps
echo "Do Fmask?: " $do_fmask
echo "Check for L1G?: " $do_L1G
echo "Unzip tarfile?: " $do_unzip
echo "Use FMASK 2.1: " $FMASK2

# Add sources for LEDAPS
addSources
# Run main method
doit
