#!/bin/sh
###
#
# Author:		Chris Holden
# Date:			12/20/2012
#
###

### Header information to add
# Wavelength units tag
w_units="wavelength units = Micrometers"
# Orbview-3
ov_wl="wavelength = { 0.48,0.545,0.6725,0.85 }"
ov_fwhm="fwhm = { 0.06,0.07,0.035,0.14 }"
# Quickbird
qb_wl="wavelength = { 0.485,0.56,0.66,0.83 }"
qb_fwhm="fwhm = { 0.065,0.1,0.065,0.11 }"
# Worldview-2 (8-band)
wv2_8_wl="wavelength = { 0.425,0.48,0.545,0.605,0.66,0.725,0.8325,0.95 }"
wv2_8_fwhm=""
# Worldview-2 (4-band)
wv2_4_wl="wavelength = { 0.48, 0.545, 0.6725, 0.85 }"
wv2_4_fwhm="fwhm = { 0.06, 0.07, 0.035, 0.14 }"
# Ikonos (4-band)
ik_wl="wavelength = { 0.480300, 0.550700, 0.664800, 0.805000 } "
ik_fwhm="fwhm = { 0.070000, 0.090000, 0.070000, 0.100000 }"


### Variables
# Flag for north-south
mosaic=0
# Multispectral, panchromatic and pansharpened output names
mul_in=""
mul_out=""
pan_in=""
pan_out=""
psh_out=""

function pansharpen {
	# Change directory to image location, saving old location
	orig_path=`pwd`
	# Order path
	order_path=`dirname $mul_in`
	if [ -d $order_path ]; then
		cd $order_path
	else
		echo "Error: could not find $order_path"
		exit 1
	fi

	### Get info about the input image
	# Search for site number
	site=`basename $mul_in | awk -F '_' ' { print $2 } '`
	echo "SITE: $site"
	echo "MOSAIC: $mosaic"
	# Search for sensor type
	if [ "$mosaic" == "1" ]; then
		sensor=`basename $mul_in | awk -F '_' ' { print $7 } '`
	else
		sensor=`basename $mul_in | awk -F '_' ' { print $6 } '`
	fi
	echo "SENSOR: $sensor"
	# Search for number of bands
	bands=`gdalinfo -nomd -norat -noct $mul_in | grep Band | wc -l`
	echo "BANDS: $bands"
	# Get date information
	year=`basename $mul_in | awk -F '_' ' { print $3 } '`
	month=`basename $mul_in | awk -F '_' ' { print $4 } '`
	day=`basename $mul_in | awk -F '_' ' { print $5 } '`
	# Form multispectral and panchromatic names
	if [ "$mosaic" == 1 ]; then
		mul_out=${site}_$4_${sensor}_${bands}b_${year}-${month}-${day}_mul
        pan_out=${site}_$4_${sensor}_${bands}b_${year}-${month}-${day}_pan
	else
		mul_out=${site}_${sensor}_${bands}b_${year}-${month}-${day}_mul
        pan_out=${site}_${sensor}_${bands}b_${year}-${month}-${day}_pan
	fi
	# Convert to ENVI type image (from ERDAS img)
	gdal_translate -of ENVI $mul_in $mul_out
	gdal_translate -of ENVI $pan_in $pan_out
	# Get full paths
	mul_out=`readlink -f $mul_out`
	pan_out=`readlink -f $pan_out`
	# Add information to the multispectral header about spectral bands
	# Also setup sensor ID number for PRO script
	sensor_id=-1
	echo $w_units >> ${mul_out}.hdr
	# Quickbird
	if [ "$sensor" == "qb" ]; then
		sensor_id=1
		echo $qb_wl >> ${mul_out}.hdr
		echo $qb_fwhm >> ${mul_out}.hdr
	# Orbview-3
	elif [ "$sensor" == "ov" ]; then
		sensor_id=3
		echo $ov_wl >> ${mul_out}.hdr
		echo $ov_fwhm >> ${mul_out}.hdr
	# Worldview-2 4 and 8 band
	elif [ "$sensor" == "wv2" ]; then
		sensor_id=2
		if [ "$bands" == "8" ]; then
			echo $wv2_8_wl >> ${mul_out}.hdr
		elif [ "$bands" == "4" ]; then
			echo $wv2_4_wl >> ${mul_out}.hdr
			echo $wv2_4_fwhm >> ${mul_out}.hdr
		else
			echo "Error: unknown number of bands for WV02"
			exit 1
		fi
	# Ikonos
	elif [ "$sensor" == "ik" ]; then
		sensor_id=4
		echo $ik_wl >> ${mul_out}.hdr
		echo $ik_fwhm >> ${mul_out}.hdr
	else
		echo "Unknown sensor ${sensor}."
		exit 1
	fi

	# Go to script directory
	cd /net/casfsb/vol/ssrchome/active_users/ceholden
	# Now start IDL and run the PRO script	
	cmd="idl -quiet -e pansharpen_image,'$pan_out','$mul_out','$psh_out',$sensor_id"
	$cmd

	# Change directories back to start
	cd $orig_path
}

# Inputs:       
#   $1          mss input file
#   $2          pan input file
#   $3          name of output file
mul_in=$1
pan_in=$2
psh_out=$3
if [ -z "$4" ]; then
	mosaic=0
else
	mosaic=1
fi

pansharpen
