#!/bin/bash

# Chris Holden
# 02-15-2012

set -e

function usage() {
    cat << EOF
    usage: $0 options

    This script will overlay segments onto a pixel based classified image to 
    produce an object based classification. The input pixel based classified 
    image will be used to determine the output class of each segment as 
    determined by a plurality rule.    

    OPTIONS:
    -c input pixel based classified image in ENVI format
    -s input segmentation in IPW format (*.armap.* or *.rmap.*)
    
EOF
}

function overlay_segment {

	# Get full directory names
	CLASSDIR="$( cd "$( dirname $CLASS )" && pwd )"
	echo $CLASSDIR
	CLASSDIR=`echo $CLASSDIR | tr -d ' '`
	SEGMENTDIR="$( cd "$( dirname $SEGMENT )" && pwd )"
	SEGMENTDIR=`echo $SEGMENTDIR | tr -d ' '`
	echo $SEGMENTDIR
	# Get name of classification
	CLASSFILE=`basename $CLASS`
	SEGMENTFILE=`basename $SEGMENT`
	echo $CLASSFILE
	echo $SEGMENTFILE
	# Create output classification name
	OUTPUTFILE=`echo ${CLASSFILE}.${SEGMENTFILE%.*}.segclass`
	
	# Change directory to classification's directory
	cd $CLASSDIR

	# Find image header
	if [ ${CLASSFILE#*.} = $CLASSFILE ];
	then 
		# image has no extension (i.e. *.bsq or *.envi)
		CLASSHDR=`ls | grep -i ${CLASSFILE}.hdr`
	elif [ ${CLASSFILE#*.} != $CLASSFILE ];
	then
		# image has extension
		# check if noextension.hdr exists
		if [ -e ${CLASSFILE%.*}.hdr ];
		then
			CLASSHDR=`echo ${CLASSFILE%.*}.hdr`
		# check if file.extension.hdr exists
		elif [ -e ${CLASSFILE}.hdr ];
		then
			CLASSHDR=`echo ${CLASSFILE}.hdr`
		else
			echo 'Could not find classification header file'
			exit
		fi
	fi
		
    # Convert image to IPW
    samples=`grep 'samples' $CLASSHDR | awk '{print $3}'`
    lines=`grep 'lines' $CLASSHDR | awk '{print $3}'`
    bands=`grep 'bands' $CLASSHDR | awk '{print $3}'`
    samples=`echo ${samples//[^0-9]/}`
    lines=`echo ${lines//[^0-9]/}`
    bands=`echo ${bands//[^0-9]/}`
    echo  Samples: $samples
    echo Lines: $lines
    echo Bands: $bands
    
    # IPW command mkbih: make IPW image from input image
    echo 'Converting classification to IPW image'
    mkbih -l $lines -s $samples -b $bands $CLASSFILE > ${CLASSFILE}.ipw

	# Remove old 8-bit BIP intermediate
	echo 'Created IPW image'

	# Ok finally doing stuff...
	# rmap2lut - create regionmap LUT based on plurality of classification
	rmap2lut -r ${SEGMENTDIR}/$SEGMENTFILE -i ${CLASSFILE}.ipw -c p > class.lut
	
    # Remove header from regionmap (for lutx2 from Mutlu)
    rmhdr ${SEGMENTDIR}/$SEGMENTFILE > myseg.bin
    
    # Get bytes in segment image
    NBYTES=`prhdr ${SEGMENTDIR}/$SEGMENTFILE | grep 'bytes =' | tr -d 'bytes = '`
	
	# Apply LUT 
    lutx2 -i myseg.bin -l class.lut -o $OUTPUTFILE -b $NBYTES -p 1
    
    # Copying classification header over to new classified image
    cp $CLASSHDR ${OUTPUTFILE}.hdr
    
    # Remove intermediate files
    rm class.lut
    rm myseg.bin
    rm ${CLASSFILE}.ipw
    
    echo 'COMPLETE: segmented classification filename: ' $OUTPUTFILE
}


CLASS=''
SEGMENT=''

while getopts "hc:s:" OPTION
    do
        case $OPTION in
        h)
            usage
            exit
            ;;
       	c)
            CLASS=$OPTARG
            ;;
        s)
            SEGMENT=$OPTARG
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

if [ "$CLASS" == '' ];
then
	echo "Must input a classification image file (\-c)"
	usage
        exit
elif [ "$SEGMENT" == '' ];
then
	echo "Must input a segmentation image file (\-s)"
	usage
        exit
else
	overlay_segment
fi
