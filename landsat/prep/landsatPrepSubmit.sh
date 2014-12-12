#!/bin/bash

###
#
# Name:     landsatPrepSubmit.sh
# Version:  3.0
# Date:     10/27/2012
#
# Author:   Chris Holden (ceholden@bu.edu)
#           Modified from code for MCD12Q2 processing from Koen Hufkens
#
# Purpose:  Finds Landsat tar.gz and sets up qsub jobs to run
#           landsatPrepQsub.sh on all tar.gz, thereby pre-processing them.
#           Takes input of maximum simulataneous qsub jobs and directory
#           containing image archives.
#
# Updates:
#   3.0:    Added option to skip either LEDAPS or FMASK.
#   4.0:    Use Eric Vermote's LDCM SR correction
#
###

###
# Variables
###

# User-id
USERID=`id -un`
# Job basename
JOBNAME=`id -gn`
# Maximum jobs to submit at once
NJobsMax=2
# Jobs submitted
NJobsSub=''
# Jobs running/queue
NJobsRun=''
# Jobs running
NJobsRunning=''
# Jobs waiting
NJobsWaiting=''
# Sleep time between checks (seconds)
SleepTime=60

# Defaults
removeExtra=0
cloud_dilate=3
shadow_dilate=3
c_prob=22.5

# Text file containing output of `find ...` for tar.gz
tarlist='landsat_scenes.txt'
# Number of tar.gz files found in $tarlist
Nscene=''
# Directory given at startup
startdir=''
# Directory for scripts
scriptdir='qsub_scripts'
# Current scene and script
scene=''
scriptfile=''
createdScripts=0

# Boolean switches for LEDAPS/Fmask
do_ledaps=1
do_fmask=1
# Organize by directory?
do_dir=1
# Check for L1G images?
do_L1G=0
# Send email for each job?
doMail=1
# Unzip tar.gz?
do_unzip=1
# Use Fmask 2.1
FMASK2=0

###
# Usage
###
function usage {
    cat << EOF
    
    usage: $0 [options] image_directory

    Author: Chris Holden (ceholden@bu.edu)

    Purpose:
    This script generates and manages the submissions of Landsat
    pre-processing (LEDAPS/Fmask) jobs to the Sun Grid Engine on BU's
    Katana cluster. 

    Note: requires script "landsatPrepQsub.sh" to also be in your path

    Options:
        -h  help
        -m  maximum SGE jobs at one time (default ${NJobsMax})
        -n  base for job names (default - ${JOBNAME}; cannot begin with a #)
        -w  wait between qstat checks (default ${SleepTime}s)
        -d  delete TIF files?
        -c  cloud dilation parameter for FMASK (default ${cloud_dilate})
        -s  shadow dilation parameter for FMASK (default ${shadow_dilate})
        -p  cloud probability parameter for FMASK (default ${c_prob})
        -l  do LEDAPS? 1 - yes, 0 - no (default $do_ledaps)
        -f  do FMask? 1 - yes, 0 - no (default $do_fmask)
        -x  do directory structure organization? (default $do_dir)
            0 - no, just find tar.gz and move to their locations
            1 - yes, creates directory structure
        -g  check for L1G images and exit if found? (default $do_L1G)
        -e  send email? (default $doMail)
        -u  do unzipping? useful if data already extracted (default $do_unzip)
        -2  Use Fmask 2.1 (default $FMASK2)

    Examples:
        Run LEDAPS and Fmask (3.2) using 10 jobs maximum and use custom Fmask 
        options on the folder "images":
        > landsatPrepSubmit.sh -m 10 -n myjob -w 60 -d -c 5 -s 4 -p 12.5 images/

        Run ONLY Fmask (3.2) on the files processed above, but this time with a 
        different Fmask cloud probability. Note the "-x" option:
        > landsatPrepSubmit.sh -m 10 -n myjob -c 5 -s 4 -p 22.5 images/P012-R031

        Run ONLY Fmask (3.2) on the files processed above, but with a different
        set of Fmask dilation values. Note that because we did not ask for the 
        TIF files to be deleted in the last run, they still exist and we will 
        not extract them ("-u 0").
        > landsatPrepSubmit.sh -m 10 -n myjob -c 3 -s 3 -p 22.5 images/P012-R031

EOF
}

###
# Search in current directory for *.tar.gz. Write to file
###
function find_tars {
    # Remove old list if exists
    if [ -f $tarlist ]; then
        rm $tarlist
        # Check exit status
        if [ `echo $?` != 0 ]; then
            echo "Error: could not delete old list of tar.gz"
            exit 1
        fi
    fi

    if [ "$do_dir" -eq "1" ]; then
        # Check if we can find Landsat archives
        Nscene=`find . -maxdepth 1 -name 'L*.tar.*z' | wc -l`
        # Check if we found anything
        if [ ! "$Nscene" -gt "0" ]; then
            echo "Error: no *.tar.gz found in $startdir"
            exit 1
        else
            echo "Found ${Nscene} Landsat archives"
        fi
    
        # Find all tar.gz in current directory and write to file
        find . -noleaf -maxdepth 1 -name 'L*.tar.*z' -exec basename {} \; > $tarlist
        # Ensure we could write out list
        if [ `echo $?` != 0 ]; then
            echo "Error: could not write list of *.tar.gz to file"
            exit 1
        fi
    else
        echo "Not doing directory structure..."
        # Check if we can find Landsat archives
        echo `pwd`
        Nscene=`find L* -name 'L*.tar.*z' | wc -l`
        echo $Nscene
        # Check if we found anything
        if [ ! "$Nscene" -gt "0" ]; then
            echo "Error no *.tar.gz found in $startdir"
            exit 1
        else
            echo "Found ${Nscene} Landsat archives"
        fi

        # Find all tar.gz in current directory and write to file
        find . -name 'L*.tar.*z' -exec basename {} \; > $tarlist
        # Ensure we could write out list
        #if [ `echo $?` != 0 ]; then
        #    echo "Error: could not write list of *.tar.gz to file"
        #    exit 1
        #fi
    fi
}


###
# Write job to script file
# Depends on: $scene, $scneid, $scriptfile, $scriptdir, $startdir
###
function write_job {
    # If old $scriptdir exists, delete it
    if [ -d $scriptdir -a "$createdScripts" -eq 0 ]; then
        rm -r $scriptdir
    fi
    if [ "$createdScripts" -eq 0 ]; then
        mkdir $scriptdir
    fi

    # Begin echo statmenets for qsub job file
    echo "#!/bin/sh" > $scriptdir/$scriptfile
    # SGE options
    echo "#$ -V" >> $scriptdir/$scriptfile
    echo "#$ -l h_rt=2:00:00" >> $scriptdir/$scriptfile
    echo "#$ -N $JOBNAME.$sceneid" >> $scriptdir/$scriptfile
    echo "" >> $scriptdir/$scriptfile
    # Make sure we change directory to $startdir
    echo "cd $startdir" >> $scriptdir/$scriptfile
    echo "" >> $scriptdir/$scriptfile
    
    # Command
    command="landsatPrepQsub.sh"
    # Options
    # Remove TIF?
    if [ $removeExtra == 1 ]; then
        command=`echo "$command -d"`
    fi
    # Add in dilation & tar.gz name
    command=`echo "$command -c $cloud_dilate -s $shadow_dilate"`
    # Add in cloud probability
    command=`echo "$command -p $c_prob"`
    # Add in do_ledaps, do_fmask
    command=`echo "$command -l $do_ledaps -f $do_fmask -x $do_dir"`
    command=`echo "$command -g $do_L1G -u $do_unzip -2 $FMASK2 $scene"`
    echo $command >> $scriptdir/$scriptfile
    echo "" >> $scriptdir/$scriptfile
    # Wait
    echo "wait" >> $scriptdir/$scriptfile
    
    # Mod permissions
    chmod a+rwx $scriptdir/$scriptfile
}

###
# Create qsub job files
# Some code modified from Koen's script
###
function create_jobs {
    ### Initialize text files for each tar.gz
    # Case found by Josh Gray when n=1
    if [ $Nscene -eq 1 ]; then
        i=1
        # Get archive name
        scene=`awk "NR==$i" $tarlist`
        # Remove trailing .tar.gz
        sceneid=`echo $scene | awk 'BEGIN { FS = "." }; { print $1 }'`
        # Script file name
        scriptfile=`echo $sceneid.$i.sh`
        # Write out scripts
        write_job
        createdScripts=1
    else
        for i in `seq 1 $Nscene`;
        do
            # Get archive name
            scene=`awk "NR==$i" $tarlist`
            # Remove trailing .tar.gz
            sceneid=`echo $scene | awk 'BEGIN { FS = "." }; { print $1 }'`
            # Script file name
            scriptfile=`echo $sceneid.$i.sh`
            # Write out scripts
            write_job
            createdScripts=1
        done
    fi

    echo "Wrote jobs out..."

    ### Submit jobs
    # Set counters
    NJobsRun=`qstat -u $USERID | grep ${JOBNAME:0:9} | awk '{print $5}' | wc -l`
    # NOTE: NJobsSub set to 0 for reporting
    #       scene_num=(NJobsSub + 1) used for line numbers and scriptID
    NJobsSub=0
   
    echo "Jobs running: $NJobsRun"

    # While we have jobs to submit
    while [ "$NJobsSub" -lt $Nscene ];
    do
        # Get jobs in SGE queue
        NJobsRun=`qstat -u $USERID | grep ${JOBNAME:0:9} | awk '{print $5}' | wc -l`
        # Get jobs running in SGE queue
        NJobsRunning=`qstat -u $USERID | grep ${JOBNAME:0:9} | awk '{print $5}' | 
            grep r | wc -l`
        NJobsWaiting=`qstat -u $USERID | grep ${JOBNAME:0:9} | awk '{print $5}' | 
            grep qw | wc -l`

        # Check if NJobsRun < NJobsMax
        if [ "$NJobsRun" -lt "$NJobsMax" ]; then 
            # If so, submit a job
            scene_num=`expr $NJobsSub + 1`
            scene=`awk "NR==$scene_num" $tarlist`
            sceneid=`echo $scene | awk 'BEGIN { FS = "." }; { print $1 }'`
            scriptfile=`echo $sceneid.$scene_num.sh`
            
            # Submit
            echo "<------------------------->"
            if [ $doMail == 0 ]; then
                qsub -m n $scriptdir/$scriptfile
            else
                qsub $scriptdir/$scriptfile
            fi
            # Message
            echo "Submitted job #${scene_num}"

            # Change counter
            NJobsSub=`expr $NJobsSub + 1`
            # Sleep a little to allow SGE to register job
            sleep 2
        else
            # We have max jobs running; update and wait
            sleep $SleepTime
        fi
        
        # Print out some status
        echo "<------------------------->"
        echo "Jobs submitted: " $NJobsSub
        echo "Jobs on SGE: " $NJobsRun
        echo "Jobs running: " $NJobsRunning
        echo "Jobs waiting: " $NJobsWaiting
    done

    # Done!
    echo "All jobs submitted to SGE. Exiting."
    exit 0
}

##### STARTS HERE
# Parse arguments
while getopts "hdc:s:p:m:w:n:l:f:x:g:e:u:2:" opt
do
    case $opt in
    h)
        usage
        exit 0 
        ;;
    m)
        NJobsMax=$OPTARG
        ;;
    w)
        SleepTime=$OPTARG
        ;;
    n)
        JOBNAME=$OPTARG
        ;;
    c)
        cloud_dilate=$OPTARG
        ;;
    s)
        shadow_dilate=$OPTARG
        ;;
    p)
        c_prob=$OPTARG
        ;;
    d)
        removeExtra=1
        ;;
    l)
        do_ledaps=$OPTARG
        ;;
    f)
        do_fmask=$OPTARG
        ;;
    x)
        do_dir=$OPTARG
        ;;
    g)
        do_L1G=$OPTARG
        ;;
    e)
        doMail=$OPTARG
        ;;
    u)
        do_unzip=$OPTARG
        ;;
    2)
        FMASK2=$OPTARG
        ;;
    ?)
        echo "Error: unknown option -$opt"
        exit
    esac
done

# Shift
shift $(($OPTIND - 1 ))

# Check for image archive directory at $1
if [ -n "$1" ]; then
    startdir=$1
else
    startdir=`pwd`
fi
# Get full path of startdir
startdir=`readlink -f $startdir`
# Check if startdir exists
if [ ! -d $startdir ]; then
    echo "Error: directory '$startdir' does not exist"
    exit 1
fi

# Check that JOBNAME doesn't start with a number
if [[ $JOBNAME == [0-9]* ]]; then 
    echo "Error: job basename cannot start with a number"
    exit 1
fi

# Check that dilation parameters are integers
if ! [[ "$cloud_dilate" =~ ^[0-9]+$ ]]; then
    echo "Error: cloud dilation parameter must be an integer"
    exit 1
fi
if ! [[ "$shadow_dilate" =~ ^[0-9]+$ ]]; then
    echo "Error: shadow dilation parameter must be an integer"
    exit 1
fi

# Check input for do_ledaps / do_fmask
if [[ $do_ledaps -ne 1 && $do_ledaps -ne 0 ]]; then
    echo "Error: -l option must be boolean 0 or 1"
    exit 1
fi
if [[ $do_fmask -ne 1 && $do_fmask -ne 0 ]]; then
    echo "Error: -f option must be boolean 0 or 1"
    exit 1
fi

if [[ $do_dir -ne 1 && $do_dir -ne 0 ]]; then
    echo "Error: -x option must be boolean 0 or 1"
    exit 1
fi

if [[ $do_L1G -ne 1 && $do_L1G -ne 0 ]]; then
    echo "Error: -g option must be boolean 0 or 1"
    exit 1
fi
if [[ $doMail -ne 1 && $doMail -ne 0 ]]; then
    echo "Error: -e option must be boolean 0 or 1"
    exit 1
fi
if [[ $do_unzip -ne 1 && $do_unzip -ne 0 ]]; then
    echo "Error: -e option must be boolean 0 or 1"
    exit 1
fi
if [[ $FMASK2 -ne 1 && $FMASK2 -ne 0 ]]; then
    echo "Error: -2 option must be boolean 0 or 1"
    exit 1
fi

# Echo starting parameters
echo "Scene directory: " $startdir
echo "Maximum jobs: " $NJobsMax
echo "Job basename: " $JOBNAME
echo "Time between qstat checks: " $SleepTime
echo "Cloud dilation: " $cloud_dilate
echo "Shadow dilation: " $shadow_dilate
echo "Cloud probability: " $c_prob
echo "Remove unneccessary files?: " $removeExtra
echo "Do LEDAPS?: " $do_ledaps
echo "Do Fmask?: " $do_fmask
echo "Check for L1G?: " $do_L1G
echo "Send email?: " $doMail
echo "Do unzip?: " $do_unzip
echo "Use FMask 2.1sav: " $FMASK2

# Check for companion script in PATH
command -v landsatPrepQsub.sh >/dev/null 2>&1 || { 
    echo >&2 "Error: 'landsatPrepQsub.sh' not found. Check your PATH"
    exit 1
}

# Start process
cd $startdir
find_tars
# Write jobs and submit them
create_jobs
