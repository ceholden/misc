#!/bin/bash
#$ -V
#$ -l h_rt=24:00:00
#$ -j y
# Simple script to check the validity of each Landsat CDR product

NARGS=$#

if [ $NARGS -lt 1 ]; then
    here=$(pwd)
else
    here=$1
fi
if [ $NARGS -lt 2 ]; then
    VERBOSE=0
else
    VERBOSE=$2
fi

echo "Working on: $here"
cd $here

okay=1

count=1
for tgz in `find . -name '*.tar.gz' -exec basename {} \;`; do 
    if [ $VERBOSE -eq 1 ]; then
        echo "# $count"
    fi
    id=`basename $tgz | awk -F '.' '{ print $1 }'`
    check=`cat ${id}.cksum`
    test=`cksum $tgz`
    if [ "$test" != "$check" ]; then 
        echo "Found inconsistency:"
        echo "    $tgz"
        okay=0
    fi
    let count+=1
done

echo "<---------------------------------------------"
if [ $okay -eq 0 ]; then
    echo "ERROR: PROBLEM FOUND CHECK LOG"
else
    echo "All files are valid"
fi
echo "--------------------------------------------->"
