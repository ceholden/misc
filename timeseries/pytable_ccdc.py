#!/usr/bin/env python
#$ -V
#$ -l h_rt=24:00:00
#$ -N pytable_ccdc
#$ -j y

from __future__ import print_function
import fnmatch
import logging
import os
import sys

import numpy as np
import scipy.io
import tables

class Unbuffered(object):
   def __init__(self, stream):
       self.stream = stream
   def write(self, data):
       self.stream.write(data)
       self.stream.flush()
   def __getattr__(self, attr):
       return getattr(self.stream, attr)

sys.stdout = Unbuffered(sys.stdout)

def find_mat_files(location, pattern='record_change*.mat'):
    mats = fnmatch.filter(os.listdir(location),
                          pattern)
    mats = [os.path.join(location, m) for m in mats]

    if len(mats) == 0:
        raise Exception('No files found')
    
    return mats

def get_description(mats, ignore=[]):
    """ Try to init dict description for PyTable from MATLAB files """
    # Try to find description from mat file
    description = {}
    
    for mat in mats:
        # Load MATLAB file
        try:
            m = scipy.io.loadmat(mat, squeeze_me=True, struct_as_record=True)['rec_cg']
        except:
            # TODO logging
            print('Warning: MATLAB file {m} may be corrupt'.format(m=mat))
            continue
        
        # Skip if no records found
        if m.size == 0:
            continue
        
        # Loop through fields setting up description
        i = 0
        for item, name in zip(m[0], m.dtype.names):
            if name in ignore:
                continue
            item = np.array(item)
            description[name] = tables.Col.from_dtype(
                np.dtype((item.dtype, item.shape)), pos=i)
            i+=1
            
        return description 

def create_pytable(filename, mats, description):
    """ Loop through MATLAB mat files adding to PyTable """

    # Open PyTable file
    with tables.open_file(filename, mode='w') as h5file:
        # Create group
        group = h5file.create_group(h5file.root, 'CCDCRec')
        # Create table
        table = h5file.create_table('/CCDCRec', 
                                    'rec_cg', 
                                    description, 
                                    'CCDC Records')
        # Get row
        record = table.row
        
        # Loop through MATLAB files
        for i, mat in enumerate(mats):
            if i % 10 == 0:
                print('    processing record {i} / {n}'.format(i=i,
                                                               n=len(mats)))
            # Open up .mat file
            try:
                m = scipy.io.loadmat(mat, 
                                     squeeze_me=True, 
                                     struct_as_record=True)['rec_cg']
            except:
                # TODO logging
                print('Warning: MATLAB file {m} may be corrupt'.format(m=mat))
                
            # Loop through records in .mat file
            for rec_cg in m:
                # Skip blank rows
                if all([item.size == 0 if 
                        type(item) == np.ndarray 
                        else False for item in rec_cg]):
                    continue
                # Loop through fields in record
                for name, item in zip(rec_cg.dtype.names, rec_cg):
                    # Ignore fields not in table description
                    if name not in description.keys():
                        continue
                    # Insert item
                    record[name] = item
                    
                # Append row before going to next
                record.append()
                
            # Flush output before going to new MATLAB file
            table.flush()
    
        # Create indexing on position and change date
        table.cols.pos.create_index(optlevel=9)
        table.cols.t_break.create_index(optlevel=9)
            
    # Context manager takes care of closing
    return 0

def main():
    # Setup
    root = '/projectnb/landsat/projects/CMS/stacks/Mexico/p022r049'
    location = 'images/TSFitMap'
    pattern = 'record_change*.mat'
    pytable_name = '/projectnb/landsat/projects/CMS/stacks/Mexico/p022r049/ccdc_record_change.h5'
    
    os.chdir(root)
    
    # Find record_change files
    # TODO logging
    print('Finding MATLAB files...')
    mats = find_mat_files(location, pattern)
    print('Found {n} MATLAB files'.format(n=len(mats)))
    
    # Determine our PyTable description from mat files
    print('Getting description...')
    desc = get_description(mats, ignore=['band', 'bands'])
    print('Description:')
    print(desc)
    
    # Create PyTable
    print('Creating PyTable...')
    sys.exit(create_pytable(pytable_name, mats, desc))

if __name__ == '__main__':
    main()
