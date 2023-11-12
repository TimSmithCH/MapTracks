#!/Users/Tim/Code/ACTION/BigSurPy3/bin/python
# #!/usr/bin/python
#-------------------------------------------------------------------------------
#
# DESCRIPTION
#    Find and delete anryd duplicate GPX files
#
# EXAMPLES
#    python gpx_deduplicate.py tracks/3_gpx/ski tracks/3_gpx/skiclimb
#    python gpx_deduplicate.py tracks/3_gpx/bike tracks/3_gpx/commute
#
# IMPLEMENTATION
#    Author       Tim Smith
#    Copyright    Copyright (c) Tim Smith
#    Licence      GNU General Public License
#
#-------------------------------------------------------------------------------
import os
import pathlib
import fnmatch
import gpxpy
import re
import numpy as np
import pandas as pd
import argparse
import datetime

def values_in_column_equal(col):
    arr = col.to_numpy()
    return (arr[0] == arr).all()

# Parse the arguments
parser = argparse.ArgumentParser(description='Check for duplicate files downloaded with different names.')
defaults = dict(verbose=False,dryrun=False)
parser.set_defaults(**defaults)
parser.add_argument("files", help="individual gpx filenames [filenames]", nargs="+")
parser.add_argument('-d', '--dryrun', action='store_true', help='Dryrun doesnt delete files, just identifies what to do')
parser.add_argument('-v', '--verbose', dest='verbose', help='Whether to print filenames scanned')
args = parser.parse_args()
verbose = args.verbose

# Expand any directories passed on the command line into a list of files
fpaths = []
for fpath in args.files:
    if os.path.isfile(fpath):
        fpaths.append(fpath)
    elif os.path.isdir(fpath):
        mpaths = [os.path.join(dp, f) for dp, dn, fn in os.walk(os.path.expanduser(fpath)) for f in fn]
        # Retain only GPX files from the mpaths list
        #fpaths = [ file for file in mpaths if file.endswith('.gpx') ]
        fpaths = np.append(fpaths,[ file for file in mpaths if file.endswith('.gpx') ])

df = pd.DataFrame(columns=['FileName', 'FilePath', 'Type', 'Time', 'Segments', 'TrkPoints'])
for fpath in fpaths:
    modified = False
    try:
        gpx = gpxpy.parse(open(fpath,'r'))
    except:
        print("ERROR: Error trying to parse {}".format(fpath))
    dname = os.path.dirname(fpath)
    bname = os.path.basename(fpath)
    fname = os.path.splitext(bname)[0]
    if verbose :
        print(" Processing {} {} {}".format(dname,bname,fname))
    else:
        print(".", end="", flush=True)
    gtime = gpx.time
    if gtime is None:
        # Skip routes (which have no timing info)
        continue
    totpts = 0
    if len(gpx.tracks) == 0 :
        continue
    for seg in gpx.tracks[0].segments:
        totpts = totpts + len(seg.points)
    gtype = gpx.tracks[0].type
    if gtype is None:
        gtype = "UNKNOWN"
    df.loc[len(df)] = {'FileName': fname,
                       'FilePath': dname,
                       'Type': gtype,
                       'Time': gtime,
                       'Segments': len(gpx.tracks[0].segments),
                       'TrkPoints': totpts}
if not verbose :
    print(" ")

#pd.set_option('display.max_rows', None)
#print(df)

# Find duplicates
dup_df = df[df.duplicated('Time', keep=False)].groupby('Time')
for name, group in dup_df:
    group = group.sort_values(['FileName']).reset_index()
    good_gpx = os.path.join(group.iloc[0]['FilePath'], group.iloc[0]['FileName'] + ".gpx")
    bad_gpx = os.path.join(group.iloc[1]['FilePath'], group.iloc[1]['FileName'] + ".gpx")
    bad_geojson = pathlib.Path(bad_gpx.replace("3_gpx","2_geojson")).with_suffix(".geojson")
    if values_in_column_equal(group['TrkPoints']):
        print("{} identical to {}".format(bad_gpx,good_gpx))
        print(" Deleting {} and {}".format(bad_gpx,bad_geojson))
        if args.dryrun == False :
            if os.path.isfile(bad_gpx):
                os.remove(bad_gpx)
            if os.path.isfile(bad_geojson):
                os.remove(bad_geojson)
    else:
        print("WARNING: Cant delete {} ({}) as its modified from {} ({})".format(bad_gpx,group.iloc[1]['TrkPoints'],good_gpx,group.iloc[0]['TrkPoints']))

