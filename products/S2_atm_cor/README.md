# Sentinel 2 atmospheric correction helper utility

Helper installation file for installing `sen2cor` into a `conda` environment.

## Instructions

1. Download and install the Anaconda (or, preferably the "miniconda") Python distribution:
    * For miniconda:
        * Download:
            * `wget https://repo.continuum.io/miniconda/Miniconda-latest-Linux-x86_64.sh`
        * Install into `$HOME/miniconda2`
            * `bash ./Miniconda-latest-Linux-x86_64.sh -b`
        * Enable `conda` by adding it to your `$PATH`
            * Temporarily: `export PATH=$PATH:$HOME/miniconda2/bin/`
            * Permanently: `echo 'export PATH=$PATH:$HOME/miniconda2/bin/' >> $HOME/.bashrc`
2. Download and navigate to this directory
    * Using git:
        * `git clone https://github.com/ceholden/misc.git`
    * Navigate:
        * `cd misc/products/S2_atm_cor`
3. Run wrapper around `sen2cor` installer
    * `bash ./conda_install_patch.sh`
4. Make sure to follow the prompts in the `sen2cor` installer!

## Using `sen2cor`

Once `sen2cor` is installed into the `conda` environment, you will need to activate both the `conda` environment and the `sen2cor` setup scripts

1. Activate `conda` environment
    * `source $HOME/miniconda2/bin/activate sen2cor`
2. Activate `sen2cor`
    * Assuming the default location
    * `source $HOME/sen2cor/L2A_Bashrc`
3. Run `sen2cor` using `L2A_Process`
    * Example: `L2A_Process -h`
