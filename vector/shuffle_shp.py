#!/usr/bin/env python
"""
"""
import os
import sys
import random

from osgeo import ogr

def gen_random(l):
    in_id = range(l.GetFeatureCount())

    out_id = random.sample(range(min(in_id), max(in_id) + 1), len(in_id))
    
    assert len(in_id) == len(out_id), \
            'Error: input and output features disagree'

    return (in_id, out_id)

shp = '/projectnb/landsat/projects/IDS/ceholden/LC_MAP/Audubon/sample/prep/2014_01_23_audubon_sample_sq_attr_wrs2.shp'
out = '/projectnb/landsat/projects/IDS/ceholden/LC_MAP/Audubon/sample/2014_01_23_audubon_sample.shp'

# OPEN shp file to be shuffled
in_ds = ogr.Open(shp)
l = in_ds.GetLayer()

# Get random order of FIDs
in_id, out_id = gen_random(l)

# CREATE output shuffled shp file dataset
driver = ogr.GetDriverByName('ESRI Shapefile')
out_ds = driver.CreateDataSource(out)

# Create output layer
d_l = out_ds.CreateLayer(l.GetName(),
                     l.GetSpatialRef(),
                     l.GetLayerDefn().GetGeomType())
# Setup fields
for i in range(l.GetLayerDefn().GetFieldCount()):
    d_l.CreateField(l.GetLayerDefn().GetFieldDefn(i))

# Create output feature
dst_feat = ogr.Feature(feature_def = l.GetLayerDefn())

### SHUFFLE features
for _out_id in out_id:
    # Read feature using FID from out_id
    f = l.GetFeature(_out_id)
    dst_feat.SetFrom(f)
    d_l.CreateFeature(dst_feat)

assert l.GetFeatureCount() == d_l.GetFeatureCount(), \
        'Error: input feature count does not match output feature count'

# SAVE shapefile
in_ds = None
out_ds = None
