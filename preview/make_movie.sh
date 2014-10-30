#!/bin/bash
#$ -V
#$ -l h_rt=24:00:00
#$ -N make_movie
#$ -j y

stackname="stack"
min_max="0 8000"
srcwin="Full"
resize=100
format="PNG"
ptsize=128
overwrite=0

function usage {
    cat << EOF

    usage: $0 <input> <output> <stackname> <srcwin> <min_max> <resize> <format>

    Arguments:
        <input>             The input directory containing stacked images
        <output>            Output directory for movies
        <stackname>         Name pattern for stacks [default: $stackname]
        <min_max>           Minimum and max for color stretch [default: $min_max]
        <srcwin>            Source window of images [default: $srcwin]
        <resize>            Resize percentage 1-100 [default: $resize]
        <format>            Format for output images [default: $format]

    Options:
        -s                  Point size for YEAR-DOY [default: $ptsize]
        -o                  Overwrite [default: $overwrite]
        -h                  Show help

    Example:
        $0 images/ movies/ stack "0 5000"

EOF
}

while getopts "ho:s:" opt; do
    case $opt in
    h)
        usage
        exit 0
        ;;
    o)
        overwrite=$OPTARG
        ;;
    s)
        ptsize=$OPTARG
        ;;
    *)
        echo "Error - unknown option $opt"
        usage
        exit 1
        ;;
    esac
done

shift $(($OPTIND - 1))

# Test existence of 'ffmpeg'
command -v ffmpeg >/dev/null 2>&1 || {
    # Try loading module
    set -e
    module load ffmpeg
    set +e
    command -v ffmpeg >/dev/null 2>&1 || {
        echo >&2 "I require 'ffmpeg' but it's not installed.  Aborting."
        exit 1
    }
}


# gen_preview.py script should be located right next to this script
script=$(dirname $0)/gen_preview.py
if [ ! -f $script ]; then
    echo >&2 "Error - cannot find 'gen_preview.py' script."
    exit 1
fi

################################################################################
if [ $# -lt 2 ]; then
    echo >&2 "Error - must specify <input> and <output>"
    usage
    exit 1
fi
# Parse required arguments
there=$(readlink -f $1)
if [ ! -d $there ]; then
    echo >&2 "Error: <input> is not a directory"
    exit 1
fi

here=$(readlink -f $2)
if [ ! -d $here ]; then
    echo >&2 "Error: <output> is not a directory"
    exit 1
fi

# Parse arguments with defaults
if [ $# -lt 3 ]; then
    stackname="stack"
else
    stackname=$3
fi

if [ $# -lt 4 ]; then
    min_max="0 8000"
else
    min_max=$4
fi
n=$(echo $min_max | awk '{n=split($0, a, " ")} END { print n }')
if [ $n -ne 2 ]; then
    echo >&2 "Must specify min and max separated by space"
    exit 1
fi

if [ $# -lt 5 ]; then
    srcwin="Full"
else
    srcwin=$5
fi
if [ "$srcwin" != "Full" ]; then
    n=$(echo $srcwin | awk '{n=split($0, a, " ")} END { print n }')
    if [ $n -ne 4 ]; then
        echo >&2 "Must specify 4 values in srcwin separated by spaces"
        exit 1
    fi
fi

if [ $# -lt 6 ]; then
    resize=100
else
    resize=$6
fi

if [ $# -lt 7 ]; then
    format="PNG"
else
    format=$7
    if [ "$format" != "PNG" ] && [ "$format" != "JPEG" ]; then
        echo >&2 "Error: unknown format - must be PNG or JPEG"
        exit 1
    fi
fi

# File extension
if [ "$format" == "PNG" ]; then
    ext=".png"
elif [ "$format" == "JPEG" ]; then
    ext=".jpg"
else
    echo >&2 "Error: Unknown format. Must be PNG or JPEG"
    exit 1
fi

set -e
################################################################################
# Find an example image for extent
ex=$(find $there -name "*$stackname" | head -1)
if [ "$ex" == "" ]; then
    echo "Error: could not find a stack image"
    exit 1
fi
temp=$(gdalinfo $ex | grep "Size is" | tr -d "Size is")
col=$(echo $temp | awk -F ',' '{print $1}')
row=$(echo $temp | awk -F ',' '{print $2}')

if [ "$srcwin" == "Full" ]; then
    srcwin="0 0 $col $row"
fi

# Sort all Landsat by date, regardless of sensor
dirs=$(find $there -maxdepth 1 -type d -name 'L*' | \
    awk -F '/' '{ print $NF, substr($NF, 10, 7) }' | \
    sort -k 2,2 | \
    cut -d ' ' -f 1)
ndirs=$(find $there -maxdepth 1 -type d -name 'L*' | wc -l)

if [ $ndirs -eq 0 ]; then
    echo "Error: could not find image directories"
    exit 1
fi

touch $here/srcwin-${srcwin//\ /_}

count=1
num=1
for d in $dirs; do
    # Add back in the full relative path
    d=${there}/$d

    # Get Landsat ID
    id=$(basename $d)
    echo "<---------- $id - $count / $ndirs"

    # Parse out year & doy
    yr=${id:9:4}
    doy=${id:13:3}

    # Outputname
    outname="$(printf %04d ${num})_${yr}-${doy}${ext}"

    # Find stack
    stack=$(find $d -name "*$stackname" -exec readlink -f {} \;)

    if [[ $overwrite -eq 0 && -f $here/$outname ]]; then
        echo "Not overwriting $here/$outname"
        let count+=1
        let num+=1
        continue
    else
        echo "Outputting to: $here/$outname"
    fi

    # Make preview
    if [ $resize -ne 100 ]; then
        $script --bands '5 4 3' --mask 8 --maskval '2 3 4 5' --ndv '-9999' \
            --srcwin "$srcwin" --format "$format" \
            --resize_pct $resize --manual "$min_max" \
            $stack $here/$outname
    else
        $script --bands '5 4 3' --mask 8 --maskval '2 3 4 5' --ndv '-9999' \
            --srcwin "$srcwin" --format "$format" --manual "$min_max" \
            $stack $here/$outname
    fi

    if [ $? -ne 0 ]; then
        echo "Error processing browse image for $id"
        exit 1
    fi

    if [ $? -eq 0 ]; then
	    let num+=1
    fi
    let count+=1
done

# Use ImageMagick to burn YEAR-DOY into bottom of image
echo "Burning YEAR-DOY into image"

mkdir -p $here/processed/
mkdir -p $here/to_mpeg/
for img in $(find $here/*${ext}); do
    # Parse info
    name=$(basename $img)
    yeardoy=$(echo $name | tr -d "${ext}" | awk -F '_' '{ print $2 }')
    id=$(echo $name | awk -F '_' '{ print $1 }')
    # Convert
    convert $img -pointsize $ptsize -gravity South -fill red -annotate 0 "$yeardoy" $here/to_mpeg/${id}${ext}
    # Move old image
   mv $img $here/processed/
done

cd $here/to_mpeg

# find height/width to test if even
w=$(gdalinfo 0001${ext} | grep "Size is" | tr -d "Size is" | awk -F ',' '{ print $1 }')
h=$(gdalinfo 0001${ext} | grep "Size is" | tr -d "Size is" | awk -F ',' '{ print $2 }')

# ffmpeg
echo "Making movie with FFMPEG"

if [[ $((w%2)) -eq 0 || $((h%2)) -eq 0 ]]; then
    ffmpeg -y -r 2 -i "%04d${ext}" -c:v libx264 -vf "scale=trunc(iw/2)*2:trunc(ih/2)*2" -pix_fmt yuv420p ../movie.mp4
else
    ffmpeg -y -r 2 -i "%04d${ext}" -c:v libx264 -pix_fmt yuv420p ../movie.mp4
fi

find $here -name '*xml' -delete

echo "Done!"
