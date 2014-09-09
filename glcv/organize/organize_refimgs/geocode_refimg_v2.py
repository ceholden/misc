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
# Versions:
#   v1  works on existing images reading in lat/lon from *.IMD file
#   v2  opens sqlite validation db to read in lat/lon, saves as csv
#
####

import codecs
import shutil
import sqlite3
import time

from geopy import geocoders
from googlemaps import GoogleMaps

def main():

    save = '/net/casrs1/volumes/cas/landsat22/validation/database/fid_commonname.csv'
    f = codecs.open(save,'w', encoding='utf-8')

    # GoogleMaps API key
    apik = 'AIzaSyA2w-3WNR5joUnHa4K7WDs2eyC-nzjr3fE'
    gmaps = GoogleMaps(apik)

    # Open validation database
    sitedb = '/net/casrs1/volumes/cas/landsat22/validation/database/site_data.db'
    # Create backup
#    backup = sitedb + '.bkup'
#    shutil.copyfile(sitedb, backup)

    # Create connection
    conn = sqlite3.connect(sitedb)
    cursor = conn.cursor()

    # Loop through database
    count = 0
    for row in cursor.execute('SELECT * FROM site'):
        if count != 0:
            fid = getSiteFID(row)
            # Return lonlat from row
            lonlat = getLonLat(row)

            # Reverse geocode
            siteName = getPlaceName(lonlat, gmaps)
            # Get formatted as CSV
            output = formatName(siteName, fid)

            # Write output & new line
            f.write(output)
            f.write('\n')
        count += 1

    # Finish output and close
    f.close()

def getSiteFID(row):
    return(row[0])

def getLonLat(row):
    lonlat = [0, 0]
    lonlat[0] = float(row[2])
    lonlat[1] = float(row[3])

    return(lonlat)

def getPlaceName(lonlat, gmaps):
    # Sleep so we don't overload Google
    time.sleep(10)
    
    ### GoogleMaps API key
    # Put in request & get back dict
    # note: send lonlat but query needs latlon
    query = gmaps.reverse_geocode(lonlat[1], lonlat[0])
    
    # Grab address details
    reverse = query['Placemark'][0]
    
    name = reverse['address']
    
    # Make sure it's in unicode
    if isinstance(name, basestring):
        if not isinstance(name, unicode):
            name = unicode(name, 'utf-8')

    return(name)

def formatName(sceneName, sceneID):
    # Need to do some parsing to get city_state_country
    sceneName = str(sceneID).strip() + ', ' + sceneName

    return(sceneName)
if __name__ == "__main__":
    main()
