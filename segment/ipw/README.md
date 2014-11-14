# IPW Segmentation Helper Scripts

## About

These two scripts - `batch_segment.sh` and `apply_segment.sh` - wrap the `segment` image segmentation program from the Image Processing Workbench (IPW) toolbox.

## Performing Segmentation

### Parameters

``` {.bash}
$ cat param.txt 
-t 10 -m .1 -n 15,15,100,2500,2500
```


``` {.bash}
$ ./batch_segment.sh -h
    usage: ./batch_segment.sh options

    This script will read in text file of parameter values for
    segment program and run segmentation for -i image for all options within
    -p parameter file.

    OPTIONS:
    -i an ENVI format BSQ image
    -p parameter file
    -s produce shapefile of regions
    
```

This program "Wraps" segment program by handling IO from ENVI format. `segment` IPW program requires "IPW" format - this script handles the conversion to IPW format by rescaling the data from whatever data type to a 8-bit unsigned integer and by converting the image into a BIP format.

`segment` creates two log files and two output "IPW" image files. The "IPW" image files have the names "*.rmap.##" and "*.armap.##" (# denotes the algorithm's loop number on output). The "armap" image is the desired output.

After running "segment" on the intermediate "test.bsq.ipw" image, the script handles the conversion from the output "*armap" image to an image readable by modern software. This conversion entails adding additional bits into the image (e.g., from 18 to 32), removing the "IPW" header, and creating an ENVI readable header text file.

Example:
batch_segment.sh -i test.bsq -p param.txt

