#!/bin/bash

# Chris Holden
# 02-15-2012

set -e

function usage() {
    cat << EOF
    usage: $0 options

    This script will read in text file of parameter values for
    segment program and run segmentation for -i image for all options within
    -p parameter file.

    OPTIONS:
    -i an ENVI format BSQ image
    -p parameter file
    -s produce shapefile of regions
    
EOF
}

function do_seg {

	# Get full directory name
    IMAGEDIR="$( cd "$( dirname $IMAGE )" && pwd )"
    IMAGEDIR=`echo $IMAGEDIR | tr -d ' '`
    IMAGEFILE=`basename $IMAGE`

    echo $IMAGEDIR

    cd $IMAGEDIR

    # Find the image header
    if [ ${IMAGEFILE#*.} = $IMAGEFILE ];
    then
        # image has no extension (i.e. no *.bsq, *.envi)
        IMAGEHDR=`ls | grep -i ${IMAGEFILE}.hdr`
    elif [ ${IMAGEFILE#*.} != $IMAGEFILE ];
    then
        # image has extension
        # check if image.hdr exists
        if [ -e ${IMAGEFILE%.*}.hdr ];
        then
            IMAGEHDR=`echo ${IMAGEFILE%.*}.hdr`
        elif [ -e ${CLASSFILE%.*}.HDR ];
        then
            IMAGEHDR=`echo ${IMAGEFILE%.*}.HDR`
        # check if image.ext.hdr exists
        elif [ -e ${IMAGEFILE}.hdr ];
        then
            IMAGEHDR=`echo ${IMAGEFILE}.hdr`
        elif [ -e ${IMAGEFILE}.HDR ];
        then
            IMAGEHDR=`echo ${IMAGEFILE}.HDR`
        fi
    fi

    # Convert image to Byte type'd BIP image (if necessary) in ENVI format
	if [ ! -e ${IMAGEFILE}.ipw ]; then
	
		# gdal_translate will just create new file if no conversion needed
		echo 'Converting image to byte data type, BIP in ENVI format'
		gdal_translate -of ENVI -ot Byte -scale -co INTERLEAVE=BIP -co SUFFIX=ADD $IMAGEFILE temp_byte_bip
	
    	# Convert image to IPW
    	samples=`grep 'samples' temp_byte_bip.hdr | tr -d 'samples = '`
    	lines=`grep 'lines' temp_byte_bip.hdr | tr -d 'lines = '`
    	bands=`grep 'bands' temp_byte_bip.hdr | tr -d 'bands = '`
    	dtype=`grep 'data type' temp_byte_bip.hdr | tr -d 'data type = '`
    	echo  Samples: $samples
    	echo Lines: $lines
    	echo Bands: $bands
    	echo Data type: $dtype
    
    	# IPW command: make IPW image from input image
    	echo 'Converting 8-bit BIP to IPW image for segmentation'
	    mkbih -l $lines -s $samples -b $bands temp_byte_bip > ${IMAGEFILE}.ipw

		# Remove old 8-bit BIP intermediate
		if [ -e temp_byte_bip ]; then
			rm temp_byte_bip
		fi
		if [ -e temp_byte_bip.hdr ]; then
			rm temp_byte_bip.hdr
		fi
		if [ -e temp_byte_bip.aux.xml ]; then
			rm temp_byte_bip.aux.xml
		fi
		echo 'Created IPW image and removed 8-bit BIP intermediate file'
	elif [ -e ${IMAGEFILE}.ipw ]; then
		echo 'Using existing IPW format of image name provided...'
        bands=$(prhdr ${IMAGEFILE}.ipw | grep nbands | awk -F '=' '{ print $2 }' | tr -d ' ')
	fi

    # Parse parameters
    tol=`echo ${params} | awk -F'-t ' '{print $2}' | awk -F' -' '{print $1}'`
    merge=`echo ${params} | awk -F'-m ' '{print $2}' | awk -F'-' '{print $1}'`
    varN=`echo ${params} | awk -F'-n' '{print $2}' | awk -F'-' '{print $1}'`
    ns=`echo $varN | tr ',' '_'`
    echo Tolerance: $tol
    echo Merge: $merge
    echo N: $varN

    # make dir for segments
    m=`echo $merge | tr -d '.'`
    echo m: $m
    echo n: $ns
    dir=t${tol}-m${m}-n${ns}
    echo $dir
    # Check to see if directory already exists (for overwriting)
    if [ -d $dir ]; then
    	cd $dir
    elif [ ! -d $dir ]; then
        mkdir $dir
    	cd $dir
    fi
    
    # If user didn't specify filename, make one
    if [ $bOUTF -eq 0 ]; then
        OUTF=`echo ${dir}_myseg`
    fi

    # IPW command: Do the segmentation
    if [ "$bands" -eq 1 ]; then
        band_option=0
    else
        band_option=1
    fi

#    if [ $EIGHT -eq 1 ]; then
#        segment -t $tol -m $merge -n $varN -b $band_option -o $OUTF ../${IMAGEFILE}.ipw | tee myseg.log    
#    elif [ $EIGHT -eq 0 ]; then
#        segment -t $tol -m $merge -n $varN -b $band_option -o $OUTF ../${IMAGEFILE}.ipw | tee myseg.log
#    fi

    if [ $EIGHT -eq 1 ]; then
        segment -t $tol -m $merge -n $varN -o $OUTF ../${IMAGEFILE}.ipw | tee myseg.log    
    elif [ $EIGHT -eq 0 ]; then
        segment -t $tol -m $merge -n $varN -o $OUTF ../${IMAGEFILE}.ipw | tee myseg.log
    fi



    bytes=`prhdr *myseg.armap.* | grep 'bytes' | tr -d 'bytes = '`
	bits=`prhdr *myseg.armap.* | grep 'bits' | tr -d 'bits = '`
    regions=`grep 'regions remain' myseg.log | tail -1 | tr -d 'regions remain after this pass'`
    
    if [ "$bytes" -eq 3 ] | [ "$bytes" -eq 4 ]; then
        # Create interp file
        echo "1 1" > interplut
        max=`echo $((2**$bits))`
		echo $max $max >> interplut
        interp < interplut > armap.lut
        new_bytes=4
        # Change data type with lutx2
		rmhdr *myseg.armap.* > temp_armap
        lutx2 -i temp_armap -l armap.lut -o regionmap -r -b $bytes -p $new_bytes
		rm temp_armap
		# Copy image header from original image
        cp ../$IMAGEHDR regionmap.hdr
        echo 'Copied header from ' $IMGHDR ' to regionmap.hdr'
        # replace band number
        sed -i "s;bands.*;bands = 1;" regionmap.hdr
		echo 'Replaced band number in header file'
        # replace data type with 32-bit unsign int
        sed -i "s;data type.*;data type = 13;" regionmap.hdr
       	echo 'Replaced data type in header file'
        # delete band names in file, if given in file
		if [ `grep -c 'band names' regionmap.hdr` -gt 0 ]; then
		    pos1=`grep -n 'band names' regionmap.hdr | cut -f1 -d ":"`
		    pos1=`expr $pos1 + 1`
		    pos2=`expr $pos1 + $bands - 1`
		    sed -i "${pos1},${pos2}d" regionmap.hdr
		    sed -i "s;band names = {;band names = { ${dir}_armap };" regionmap.hdr
		    echo 'Replaced band names in header file'
		fi
    elif [ "$bytes" -eq 2 ]; then
        # Create ENVI binary
        rmhdr *.armap.* > regionmap
        # Copy header
        cp ../$IMAGEHDR regionmap.hdr
        echo 'Copied header from ' ../${IMAGE}.hdr ' to regionmap.hdr'
        # replace band number
        sed -i "s;bands   = $bands;bands   = 1;" regionmap.hdr
        echo 'Replaced band number in header file'
        # replace data type with 16-bit unsign int
        sed -i "s;data type = 1;data type = 12;" regionmap.hdr
        echo 'Replaced data type in header file'
        # delete band names in file, if given in file
		if [ `grep -c 'band names' regionmap.hdr` -gt 0 ]; then
		    pos1=`grep -n 'band names' regionmap.hdr | cut -f1 -d ":"`
		    pos1=`expr $pos1 + 1`
		    pos2=`expr $pos1 + $bands - 1`
		    sed -i "${pos1},${pos2}d" regionmap.hdr
		    sed -i "s;band names = {;band names = { ${dir}_armap };" regionmap.hdr
		    echo 'Replaced band names in header file'
		fi
    fi

    # Generate an ESRI shapefile of regionmap?
	if [ $POLY -eq 1 ]; then
		# Create regionmap shapefiles
		echo 'Converting to polygon...'
		gdal_polygonize.py -f "ESRI Shapefile" regionmap regionmap-poly.shp
	fi

	# Cleaning up other files
    #if [ -e ../${IMAGEFILE}.ipw ]; then
    #    rm ../${IMAGEFILE}.ipw
    #fi
	if [ -e armap.lut ]; then
		rm armap.lut
	fi
	if [ -e interplut ]; then
		rm interplut
	fi

    cd ..
    cd $CD
}

# POLY: boolean - produce shapefile?
IMAGE=''
PFILE=''
POLY=0
EIGHT=0
bOUTF=0
OUTF=''

CD=`pwd`

while getopts "hi:p:s" OPTION
    do
        case $OPTION in
        h)
            usage
            exit
            ;;
        i)
            IMAGE=$OPTARG
            ;;
        p)
            PFILE=$OPTARG
            ;;
        o)
            bOUTF=1
            OUTF=$OPTARG
            ;;
        s)
			POLY=1
			;;
        8)
            EIGHT=1
            ;;
		:)
			echo 'Error: -$OPTION requires an argument'
			usage
			exit
			;;	
		?)
			echo 'Error: unknown option -$option'
			usage
			exit
			;;
       	esac
done

if [ "$PFILE" == "" ]; then
	echo 'Must input a parameter file (-p)'
	usage
	exit
elif [ "$IMAGE" == "" ]; then
	echo 'Must input an image file (-i)'
	usage
	exit
else
	while read params
	    do
	        do_seg
	done < $PFILE
fi
