#!/bin/bash
#$ -V
#$ -l h_rt=24:00:00
#$ -j y

set -e

function usage {
    cat << EOF
    usage: $0 <example_img> <vector_file> <vector_layer> <output_dir>

    This script finds the extent of <vector_file> that aligns with
    <example_img> and clips all images within ./images to that extent. Clipped
    images are reproduced with the same naming structure and MTL files within
    <output_dir>
EOF
}

img=$1
shp=$2
shp_lyr=$3
outdir=$4

if [ ! -d ./images ]; then
    echo "Cannot find hard-coded 'images' folder within pwd"
    echo "    Either improve this code or `cd` to correct location first"
    exit 1
fi

if [ $# -ne 4 ]; then
    echo "Error - must specify all 4 inputs"
    usage
    exit 1
fi

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
        tr -d "[(,]")
    echo -n "$EXTENT"
}

function ogr_extent() {
    if [ -z "$1" ]; then 
        echo "Missing arguments. Syntax:"
        echo "  ogr_extent <input_vector>"
        return
    fi
    EXTENT=$(ogrinfo -al -so $1 |\
        grep Extent |\
        sed 's/Extent: //g' |\
        sed 's/(//g' |\
        sed 's/)//g' |\
        sed 's/ - /, /g')
    EXTENT=`echo $EXTENT | awk -F ',' '{print $1 " " $4 " " $3 " " $2}'`
    echo -n "$EXTENT"
}

img_ext=$(gdal_extent $img)
shp_ext=$(ogr_extent $shp)

pix=$(gdalinfo $img | grep "Pixel Size" | sed "s/Pixel.*(//g;s/,/ /g;s/)//g")
pix_sz="$pix $pix"

echo "Extent of stacked images and extent of shapefile:"
echo $img_ext
echo $shp_ext

new_ext=""

for i in 1 2 3 4; do
    # Get the ith coordinate from sequence
    r=$(echo $img_ext | awk -v i=$i '{ print $i }')
    v=$(echo $shp_ext | awk -v i=$i '{ print $i }')
    pix=$(echo $pix_sz | awk -v i=$i '{ print $i }')
    
    # Quick snippit of Python
    ext=$(python -c "\\
        offset=int(($r - $v) / $pix); \
        print $r - offset * $pix\
        ")
    new_ext="$new_ext $ext"
done

# Now, unfortunately, gdalwarp wants us to specify xmin ymin xmax ymax
# In this case, this corresponds to the upper left X, lower right Y, lower right X, and upper left Y
warp_ext=$(echo $new_ext | awk '{ print $1 " " $4 " " $3 " " $2 }')
echo "gdalwarp extent:"
echo $warp_ext

# Perform the clip:
i=0
for stack in $(find images/ -name '*stack'); do
    dir=$(basename $(dirname $stack))
    echo "Clipping $dir (#$i)"
    
    mkdir -p $outdir/$dir
    
    cp images/$dir/*MTL.txt $outdir/$dir/

    output=$outdir/$dir/$(basename $stack)
    
    gdalwarp -of ENVI -co "INTERLEAVE=BIP" -te $warp_ext -tr 30 30 \
        -cutline $shp -cl $shp_lyr  \
        -dstnodata -9999 -wm 2000 \
        $stack $output
    let i+=1
done

echo "Done!"

