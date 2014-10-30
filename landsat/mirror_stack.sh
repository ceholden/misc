#!/bin/bash

dname=L*
sname=*stack*
cpmtl=0

function usage() {

    cat << EOF
    
    Usage: $0 <from> <to>

    This script "clones" an existing Landsat stack directory by recreating
    the existing directory structure, copying MTL files, and symlinking to 
    the image stack file.

    Options:
      -d=<pattern>          Stack directory pattern [default: $dname]
      -s=<pattern>          Stack filename pattern [default: $sname]
      -m                    Copy MTL file
      -h                    Show help

EOF
}

function main() {
    set -e
    # Create <to> directory
    mkdir -p $to
    # Find stack directories
    stkdirs=$(find $from/ -maxdepth 1 -name "$dname" -type d)
    nstkdirs=$(echo $stkdirs | awk '{ print NF }')
    if [[ -z "$nstkdirs" || "$nstkdirs" == 0 ]]; then
        echo "Could not find any stack directories in $from"
        exit 1
    fi

    # Loop over, finding stack images and creating symlinks
    i=0
    for stkdir in $stkdirs; do
        stkname=$(basename $stkdir)

        echo "Mirroring $stkname"

        stk=$(find $stkdir -maxdepth 1 -name "$sname")
        [[ -z "$stk" ]] && {
            echo "Error - could not find stack image for $stkdir"
            exit 1
        }

        if [ $cpmtl -eq 1 ]; then
            mtl=$(find $stkdir/ -maxdepth 1 -name '*MTL.txt' -type f)
            [[ -z "$mtl" ]] && {
                echo "Error - could not find MTL file for $stkdir"
                exit 1
            }
        fi

        mkdir -p $to/$stkname

        for f in $stk; do
            fname=$(basename $f)
            ln -s $(readlink -f $f) $to/$stkname/$fname
        done
   
        if [ $cpmtl -eq 1 ]; then
            cp $mtl $to/$stkname/
        fi
        
        let i+=1
    done

    echo "Complete"
}

while getopts "hmd:s:" opt; do
    case $opt in
    h)
        usage
        exit 0
        ;;
    d)
        dir=$OPTARG
        ;;
    s)
        stk=$OPTARG
        ;;
    m)
        cpmtl=1
        ;;
    *)
        echo "Error - unknown option."
        usage
        exit 0
    esac
done

shift $(($OPTIND - 1))

[[ -z $1 || -z $2 ]] && {
    echo "Error - must specify <from> and <to> arguments"
    usage
    exit 1
}
from=$1
to=$2

[[ ! -d $1 ]] && {
    echo "Error - $from is not a directory"
    exit 1
}
[[ -d $2 ]] && {
    echo "Error - $to already exists and this script will not overwrite"
    exit 1
}

main
