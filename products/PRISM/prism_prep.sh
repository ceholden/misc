#!/bin/bash
# After PRISM data are downloaded and organize, preprocess the data
# to create "anomaly" (monthly/daily - normal) images.
# PRISM precipitation data will also be transformed into cumulative
# precipitation for a given 'water year' (Oct 1, YYYY - 1 to Sept 31, YYYY)

set -e

resume=1
if [ "$1" == "0" ]; then
    resume=0
fi

if [ ! -z $PRISM_ROOT ]; then
    dest=$PRISM_ROOT/data
else
    echo "'PRISM_ROOT' envvar is not defined."
    echo "Defaulting to /projectnb/landsat/datasets/PRISM" 
    dest=/projectnb/landsat/datasets/PRISM/data/
fi
if [ ! -d $dest ]; then
    echo "Destination directory doesn't exist -- have you organized the data?"
    exit 1
fi

element="ppt tmin tmax tmean"
normals="$dest/normals"

for t in monthly daily; do
    if [ ! -d $dest/$t ]; then
        echo "No $t data -- continuing"
        continue
    fi
    echo "+ Working on $(basename $t) data"
    for ele in $element; do
        if [ ! -d $dest/$t/$ele ]; then
            echo "  ==> No $ele data in $dest/$t/$ele -- continuing"
            continue
        fi
        echo "  ==> Normalizing $ele"
        
        # Normalize
        normdir=$dest/$t/${ele}_norm
        mkdir -p $normdir
        for img in $(find $dest/$t/$ele -name 'PRISM*.gtif' | sort); do
            outfn=$normdir/$(basename $img)
            [ -f "$outfn" -a "$resume" == "1" ] && continue
            # TODO: does this month extraction work for daily?
            _date=$(basename $img .gtif | awk -F '_' '{ print $5 }')
            month=${_date:4:6}

            normal=$(find $normals/$ele -name "PRISM*_${month}*")
            
            # Calculate
            rio -q calc --co "TILED=YES" --co "COMPRESS=DEFLATE" \
                "(- (read 1) (read 2))" \
                $img $normal $normdir/$(basename $img)
        done

        # Cumulative per 'water year' (Oct 1, YYYY - 1 to Sept 31, YYYY)
        if [ "$ele" == "ppt" ]; then
            echo "  ==> Cumulating ppt"
            cumdir=$dest/$t/${ele}_cum
            mkdir -p $cumdir
            
            prev_cum=""
            for img in $(find $dest/$t/$ele -name 'PRISM*.gtif' | sort); do
                outfn=$cumdir/$(basename $img)
                
                # Extract year, month, & day from date
                _date=$(basename $img .gtif | awk -F '_' '{ print $5 }')
                year=${_date:0:4}
                month=${_date:4:6}
                day=${_date:6:8}
                if [ -z "$day" ]; then
                    [ "$month" == "10" ] && day="01"
                fi

                # Begin cumulating on Oct 1st
                if [ "$month" == "10" -a "$day" == "01" ]; then
                    echo "   ::: Beginning to cumulate $((year + 1)) from ${year}-${month}-${day}"
                    echo "       * cumulating ${year}-${month}-${day}"
                    cp $img $outfn
                    prev_cum=$outfn
                else
                    if [ ! -z "$prev_cum" ]; then
                        # Try to resume before going further
                        [ -f $outfn -a "$resume" == "1" ] && continue
                        # Add this image to previously cumulated
                        echo "       * cumulating ${year}-${month}-${day}"
                        rio -q calc --co "TILED=YES" --co "COMPRESS=DEFLATE" \
                            "(+ (read 1) (read 2))" \
                            $prev_cum $img $outfn
                        prev_cum=$outfn
                    fi                    
                fi
            done
        fi
        # End element type loop
    done
    # End time frequency loop
done
