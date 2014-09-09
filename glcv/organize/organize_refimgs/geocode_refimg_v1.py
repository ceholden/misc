#!/usr/bin/env python

###
# Author: Chris Holden
# Date: 06/18/2012
# 
# Purpose: Use Google to reverse geocode reference image locations
#
# Using: googlemaps
#   http://pypi.python.org/pypi/googlemaps/
#
####

import codecs
import glob
import os
import shutil
import sys
import time

from geopy import geocoders
from googlemaps import GoogleMaps

def main():

    output = '/net/casfsb/vol/ssrchome/active_users/ceholden/img_names.txt'
    f = codecs.open(output,'w', encoding='utf-8')

#    refimg = '/net/casrs1/volumes/cas/landsat25/reference_images/catalog'
#    os.chdir(refimg)

    # GoogleMaps API key
    apik = 'AIzaSyA2w-3WNR5joUnHa4K7WDs2eyC-nzjr3fE'
    gmaps = GoogleMaps(apik)

    

#    for scene in sorted(os.listdir('.')):
        # e.g. 491
#        os.chdir(scene)
        # e.g. 2010-058
#        yeardir = glob.glob('*-*')[0]
#        os.chdir(yeardir)
        # e.g. 1-Order
#        os.chdir('1-Order')
        # e.g. 052591267460_01
#        imgdir = glob.glob('*_01')
#        os.chdir(imgdir[0])
        # e.g. 052591267460_01_P001_PSH
#        imgdir = glob.glob('*_01_P001_*')
#        os.chdir(imgdir[0])
        # Find IMD file
#        imd = glob.glob('*.IMD')[0]
        # Read IMD file and get place name
#        sceneName = readIMD(imd, gmaps)
        # Get scene ID
#        sceneID = scene.split('_')[0]
        # Reformat name to path friendly
#        sceneName = getFriendlyName(sceneName, sceneID)

#        f.write(sceneName)
#       f.write('\n')

#        os.chdir('../../../../..')
    
#    f.close()

def readIMD(imd, gmaps):
    imd = glob.glob('*.IMD')[0]
    
    UL = [0, 0]
    UR = [0, 0]
    LL = [0, 0]
    LR = [0, 0]

    found = 0
    imdFile = open(imd)
    for line in imdFile:
        # Parse each line into key/val
        key, val = [s.strip().strip(';') for s in line.split('=')]
        # Parse longitude / latitude
        if key == 'ULLon':
            UL[0] = float(val)
            found+=1
        elif key == 'ULLat':
            UL[1] = float(val)
            found+=1
        elif key == 'URLon':
            UR[0] = float(val)
            found+=1
        elif key == 'URLat':
            UR[1] = float(val)
            found+=1
        elif key == 'LLLon':
            LL[0] = float(val)
            found+=1   
        elif key == 'LLLat':
            LL[1] = float(val)
            found+=1
        elif key == 'LRLon':
            LR[0] = float(val)
            found+=1
        elif key == 'LRLat':
            LR[1] = float(val)
            found+=1
        if found == 8:
            imdFile.close()
            break
    
    center = [0, 0]
    center[0] = (UL[0] + UR[0] + LL[0] + LR[0]) / 4
    center[1] = (UL[1] + UR[1] + LL[1] + LR[1]) / 4

    name = getPlaceName(center, gmaps)
    return(name)

def getPlaceName(center, gmaps):
    # Sleep so we don't overload Google
    time.sleep(1)
    
    ### GoogleMaps API key
    # Put in request & get back dict
    query = gmaps.reverse_geocode(center[1], center[0])
    
    # Grab address details
    reverse = query['Placemark'][0]['AddressDetails']

    # Parse reverse into what we want
    if 'Country' in reverse.keys():
        reverse = reverse['Country']
        # Try to get country
        if 'CountryCode' in reverse.keys():
            country = reverse['CountryCode']
        elif 'CountryNameCode' in reverse.keys():
            country = reverse['CountryNameCode']
        else:
            print 'No country code. Here\'s reverse.'
            country = 'UNKNOWN'
            print reverse.keys()
    # Or grab address line
    elif 'AddressLine' in reverse.keys():
        country = reverse['AddressLine'][0]
    else:
        country = 'UNKNOWN'
        print 'Country unknown. Here\'s reverse:'
        print reverse
        print reverse.keys()

    # Check if Google returned an admin area
    if 'AdministrativeArea' in reverse.keys():
        # If so, try to define city
        city = reverse['AdministrativeArea']
        if 'Locality' in city.keys():
            city = city['Locality']['LocalityName']
        elif 'DependentLocality' in city.keys():
            city = city['DependentLocality']['DependentLocalityName']
        elif 'SubAdministrativeArea' in city.keys():
            city = city['SubAdministrativeArea']['SubAdministrativeAreaName']
        else:
            print city
            print city.keys()
            city = 'UNKNOWN'
        # If so, try to define state
        state = reverse['AdministrativeArea']
        if 'AdministrativeAreaName' in state.keys():
            state = state['AdministrativeAreaName']
    # Google doesn't have the information for city or state
    else:
        city = 'UNKNOWN'
        state = 'UNKNOWN'

    # Re-format info to remove white-space / etc
    city = city.strip().replace(' ', '')
    state = state.strip().replace(' ', '')
    country = country.strip().replace(' ', '')

    # Concatenate together
    name = city + '_' + state + '_' + country

    # Make sure it's in unicode
    if isinstance(name, basestring):
        if not isinstance(name, unicode):
            name = unicode(name, 'utf-8')

    return(name)

def getFriendlyName(sceneName, sceneID):
    # Need to do some parsing to get city_state_country

    sceneName = sceneID.strip() + ': ' + sceneName
    return sceneName

if __name__ == "__main__":
    main()
