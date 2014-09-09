#!/bin/bash

# url=ftp://ftp.glcf.umd.edu/glcf/SRTM/WRS2_Tiles
url=ftp://ftp.glcf.umd.edu/glcf/SRTM/stow/GLCF.TSM.B4-007.00.Filled_Finished_B-01sec-WRS2-United-States/WRS2_Tiles

usage() {
    echo "get_srtm.sh"
    echo ""
    echo "Downloads SRTM 'Filled Finished-B' dataset from UMD GLCF"
    echo '    $1        path'
    echo '    $2        row'
    echo '    $3        location'
    echo ""
    echo "Example:"
    echo "    get_srtm.sh p012 r031 my_directory"
    exit 1
}

[[ $# -eq 0 ]] && usage

path=$1
row=$2
location=$3

if [ "$location" == "" ]; then
    location=`pwd`
fi

echo "Path: $path"
echo "Row: $row"
echo "Download to: $location"

if [ ! -d $location ]; then
    mkdir -p $location
fi

wget -nv -nd --continue -r -np -P $location -A *${path}${row}* $url/$path


### Get files accounting for symlinks
# https://bbs.archlinux.org/viewtopic.php?pid=487014#p487014
#
# Find directory path
# dirpath=$(echo "$url/$path" | sed s-ftp://--)
# baseurl=$(echo "$dirpath" | cut -d '/' -f1)
# # Get symlinks
# wget -r -N -A *${row}* -P $location $url/$path
# # Get full names
# symlinks=$(find $dirpath -type l)
# for symlink in $symlinks; do
#     target=$(readlink $symlink)
#     if [ "${target:0:1}" == "/" ]; then
#         uri="ftp://$baseurl/$(readlink $symlink)"
#     else
#         uri="ftp://$dirpath/$(readlink $symlink)"
#     fi
#     wget -r -N $uri
# done
