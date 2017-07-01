#!/usr/bin/env bash

if [ -z $1 ]; then
    echo "Error: must specify <N_workers> as first argument"
    exit 1
fi

N=$1
JOBNAME="dask-exec"


echo "Launching scheduler job..."
qsub_msg=$(
    qsub \
    -V -j y -b y -l h_rt=24:00:00 -l eth_speed=10 \
    -N $JOBNAME \
    dask-scheduler 2>&1
)

scheduler_jid=$(echo $qsub_msg | awk '{ print $3 }')
scheduler_log=$JOBNAME.o${scheduler_jid}

echo "$scheduler_log"

echo "Waiting on scheduler (job ID $scheduler_jid) to start..."
while true; do
    if [ -f $scheduler_log ]; then
        scheduler_ip=$(grep "Scheduler at" $scheduler_log | awk '{ print $NF }')
        if [ ! -z "$scheduler_ip" ]; then
            scheduler_host=$(qstat -u $USER | \
                             grep $scheduler_jid | \
                             awk '{ print $8 }' | \
                             awk -F '@' '{ print $2 }')
            echo "Found scheduler at: $scheduler_ip"
            echo "Scheduler running on hostname: ${scheduler_host}"
            break
        fi
    fi
    sleep 5
done

echo "Launching $N workers..."
qsub -V -j y -b y -l h_rt=24:00:00 \
    -N "dask-worker" -t 1-$N \
    dask-worker --nthreads 1 --nprocs 1 $scheduler_ip
