#!/bin/bash
# Helper script to install "sen2cor"
#
# Repo: https://github.com/umwilm/SEN2COR
# Download: http://s2tbx.telespazio-vega.de/sen2cor/
#
# Issues:
# 1. Assumes Anaconda package base so it doesn't explicity define dependencies
# 2. "Updates" instead of installs pytables
# 3. No separation between:
#   * 'you should have these deps' (setup.py)
#   * 'here is where to get them' (requirements.txt/environment.yaml)
#   * a platform specific installer
# 4. There is no "you should have this version of dep <dependency>"
#
# This wrapper script around the installer tries to fix some of these issues.

set -e

# Ensure conda exists
hash conda 2>/dev/null || {
    echo >&2 "Requires 'conda' be installed and available. Exiting."; exit 1;
}

CONDA_BIN_DIR=$(dirname $(readlink -f $(which conda)))
CONDA_DIR=$(dirname $CONDA_BIN_DIR)

# Download latest "sen2cor-*.tar.gz"
echo "Downloading 'sen2cor' from 'http://s2tbx.telespazio-vega.de/sen2cor'..."
set +e  # ignore wget errors
wget -q -r -nd --no-parent -l 1 -A 'sen2cor-*.tar.gz' http://s2tbx.telespazio-vega.de/sen2cor
set -e

if [ ! -f ./sen2cor-*.tar.gz ]; then
    echo "Failed to download 'sen2cor' source code archive... "
    exit 1
fi
download=sen2cor-*.tar.gz
tar -xzf $download
cd $(basename $download .tar.gz)

# Create an encapsulated conda environment
echo "Creating 'sen2cor' conda environment to house installation..."
if [ -d $CONDA_DIR/envs/sen2cor ]; then
    echo "Deleting existing conda environment 'sen2cor'"
    rm -rf $CONDA_DIR/envs/sen2cor
fi
conda create --yes -n sen2cor python=2.7
# Activate conda env
source $CONDA_BIN_DIR/activate sen2cor

# The package installer (setup.py) has a few flaws for easy deployment
## It assumes full Anaconda (#1)
## It 'updates' pytables without having it installed, leading to runtime error (#2)

# Counteract by using custom 'environment.yaml' file
echo "Updating conda environment..."
conda env update -q -f ../environment.yaml

# Patch: Remove all calls to 'conda' from 'setup.py'
echo "Modifying 'sen2cor' setup.py installer..."
sed -e '/^os.system.*[cmdstr|conda].*/ s/^#*/#/' setup.py > setup_modified.py

# Give it a whirl -- follow the prompts!
echo "Installing 'sen2cor' package -- remember to follow the prompts!"
python setup_modified.py install
