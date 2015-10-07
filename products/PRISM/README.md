# PRISM Climate Data

 prism.oregonstate.edu

## Usage

`prism_organize.sh`, `prism_download.sh`, and `prism_prep.sh` default
to a "resume" mode unless "0" is specified as the first input argument, $1.
The "resume" mode will not download, organize, or preprocess any files
that already exist in the destination directories.

These scripts are written with the Boston University GEO/SCC cluster in mind.
As such, the "root" directory for the PRISM datasets is:

    /projectnb/landsat/datasets/PRISM/

This "root" directory may be overriden by defining the environment variable,
"PRISM_ROOT".
