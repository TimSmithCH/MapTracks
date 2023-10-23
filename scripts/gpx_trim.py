#!/usr/bin/python
# -*- coding: utf-8 -*-
#-------------------------------------------------------------------------------
#
# DESCRIPTION
#    Ensure GPX files have tracks not routes, no unnecessary timing info on
#    tracks, and no unnecessary precision on elevation or track points
#
# EXAMPLES
#    python gpx_trim.py tracks/3_gpx/vehicle/CAR_Istria_Day*
#
# IMPLEMENTATION
#    Author       Tim Smith
#    Copyright    Copyright (c) Tim Smith
#    Licence      GNU General Public License
#
#-------------------------------------------------------------------------------
import os
import fnmatch
import gpxpy
import re
import numpy as np
import argparse
import datetime
import base64, json


# Instantiate the parser
parser = argparse.ArgumentParser(description='Trim the GPX track in points and precision.')
# Set up the argument defaults
defaults = dict(simplify=True,time=True,elevation=True,output=True)
parser.set_defaults(**defaults)
# Parse the command line
parser.add_argument("files", help="individual gpx filenames [filenames]", nargs="+")
parser.add_argument('-s', '--simplify', dest='simplify', help='Apply simplification (or not)')
parser.add_argument('-t', '--time', dest='time', help='Drop timing info from tracks')
parser.add_argument('-e', '--elevation', dest='elevation', help='Round elevation info in tracks')
parser.add_argument('-o', '--output', dest='output', help='Alterntive file for output in avoiding overwrite')
args = parser.parse_args()
print(">>> Cmd line: process files ({})".format(args.files))
print(">>> Cmd line: rename output ({}), apply simplify ({}), drop timing ({}), round elevations ({})".format(args.output,args.simplify,args.time,args.elevation))

VERBOSE = True

# Expand any directories passed on the command line into a list of files
fpaths = []
for fpath in args.files:
    if os.path.isfile(fpath):
        fpaths.append(fpath)
    elif os.path.isdir(fpath):
        mpaths = [os.path.join(dp, f) for dp, dn, fn in os.walk(os.path.expanduser(fpath)) for f in fn]
        # Retain only GPX files from the mpaths list
        fpaths = [ file for file in mpaths if file.endswith('.gpx') ]

for fpath in fpaths:
    modified = False
    try:
        gpx = gpxpy.parse(open(fpath,'r'))
    except:
        print("ERROR: Error trying to parse {}".format(fpath))
    bname = os.path.basename(fpath)
    fname = os.path.splitext(bname)[0]
    if VERBOSE : print("INFO: Processing {0:48s}".format(fname))
    if VERBOSE : print("INFO:  (START) GPX file contains {} tracks, {} waypoints, {} routes".format(len(gpx.tracks),len(gpx.waypoints),len(gpx.routes)))

    if len(gpx.routes) > 0:
        # Convert routes into tracks
        for r,route in enumerate(gpx.routes):
            gpx.tracks.append(gpxpy.gpx.GPXTrack())
            gpx.tracks[r].segments.append(gpxpy.gpx.GPXTrackSegment())
            gpx.tracks[r].segments[0].points.extend(route.points)
        # Drop the original routes
        gpx.routes = []
        modified = True

    if len(gpx.tracks) > 0:
        if VERBOSE : print("INFO:  File initially contains {} points".format(gpx.get_track_points_no()))
        #print(gpx.get_elevation_extremes())
        # Simplify tracks by removing unnecessary points
        if args.simplify == True:
            print("INFO:  > Simplify tracks")
            gpx.simplify(max_distance=10)
            modified = True
        for track in gpx.tracks:
            #track.remove_elevation()
            # Drop the point timing information
            if track.has_times():
                if args.time == True:
                    print("INFO:  > Drop timing info from tracks")
                    track.remove_time()
                    modified = True
            if VERBOSE : print("INFO:  Track contains {} segments".format(len(track.segments)))
            if args.elevation == True:
                print("INFO:  > Round elevation info in tracks")
                for segment in track.segments:
                    for point in segment.points:
                        # Drop precision on elevation
                        point.elevation = int(point.elevation)
                modified = True
        if VERBOSE : print("INFO:  File finally contains {} points".format(gpx.get_track_points_no()))

    # Check the file metadata block
    if gpx.name is None:
        gpx.name = fname
        print("INFO:  > Adding file name field {}".format(fname))
        modified = True
    if gpx.bounds is None:
        bounds = gpx.get_bounds()
        gpx.bounds = bounds
        bounds_str = str(bounds.min_latitude)+"/"+str(bounds.min_longitude)+"/"+str(bounds.max_latitude)+"/"+str(bounds.max_longitude)
        print("INFO:  > Adding file bounds {}".format(bounds_str))
        modified = True

    # Check the track metadata block
    tname = gpx.tracks[0].name
    # Check for name differences and reset tag if necessary
    if tname != fname:
        print("INFO:  >> Updating (file {}) NAME from ({}) to ({})".format(bname,tname,fname))
        gpx.tracks[0].name = fname
        modified = True
    if gpx.tracks[0].comment is None:
        print("INFO:  >> Adding track comment field")
        gpx.tracks[0].comment = "1970-01-01"
        modified = True
    if gpx.tracks[0].description is None:
        print("INFO:  >> Adding track description field")
        gpx.tracks[0].description = "1.0"
        modified = True
    if gpx.tracks[0].type is None:
        print("INFO:  >> Adding track type field")
        gpx.tracks[0].type = "Velomobile"
        modified = True
    if gpx.tracks[0].source is None:
        print("INFO:  >> Adding track source field")
        gpx.tracks[0].source = bounds_str
        modified = True
    if VERBOSE : print("INFO:  (END) GPX file contains {} tracks, {} waypoints, {} routes".format(len(gpx.tracks),len(gpx.waypoints),len(gpx.routes)))

    # Write out any changes
    if modified:
        if args.output:
            outfile = fpath + ".new"
        else:
            outfile = fpath
        # Default indentation for PP is 2 spaces, no extra action required
        newtree = gpx.to_xml(prettyprint=True)
        print("INFO: Writing out new content to {}".format(outfile))
        with open(outfile, "w") as f:
            f.write(newtree)
