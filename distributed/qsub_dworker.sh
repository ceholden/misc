#!/bin/bash
#
# Helper script for submitting `dask-distributed` worker jobs as array tasks

function usage() {
    echo "Usage: $0 <hostname:port> <njobs> <qsub_kwargs>"
    exit 1
}
if [ -z $1 ]; then
    echo "Error: must specify hostname"
    usage
fi
if [ -z $2 ]; then
    echo "Error: must specify number of jobs"
    usage
fi

# Check if dworker is installed
hash dask-worker 2>/dev/null || {
    echo >&2 "Can't find 'dask-worker': please install dask-distributed"
}

host=$1
njobs=$2

qsub -V -b y -j y -t 1-${njobs} "${@:3}" dask-worker --nthreads 1 $host
