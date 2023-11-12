#!/usr/bin/python
# -*- coding: utf-8 -*-
#-------------------------------------------------------------------------------
#
# DESCRIPTION
#    Check all GPXs have a corresponding GEOJSON and generate them if not,
#    and check all GEOJSONs have a corresponding GPX and delete them if not
#
# EXAMPLES
#    python geojson_sync_check.py -f -r -t bike
#
# IMPLEMENTATION
#    Author       Tim Smith
#    Copyright    Copyright (c) Tim Smith
#    Licence      GNU General Public License
#
#-------------------------------------------------------------------------------
import os
import pathlib
import argparse
import subprocess
import termcolor

#-------------------------------------------------------------------------------
# Initialise command line options and their defaults
def parseCommandLine():
    global VERBOSE
    # Instantiate the parser
    parser = argparse.ArgumentParser(description="Convert GPX track into standardised GeoJSON tracks")
    # Set up the argument defaults
    defaults = dict(trkdirs="all",dryrun=False,forward=False,reverse=False,verbose=False)
    parser.set_defaults(**defaults)
    # Parse the command line
    parser.add_argument('-d', '--dryrun',  action='store_true', help='Dont create or delete files')
    parser.add_argument('-f', '--forward', action='store_true', help='Check all GPXs have a corresponding GEOJSON')
    parser.add_argument('-r', '--reverse', action='store_true', help='Check all GEOJSONs have a corresponding GPX')
    parser.add_argument('-t', '--trkdirs', dest='trkdirs',      help='Track types to check')
    parser.add_argument('-v', '--verbose', action='store_true', help='Turn on verbose output')
    args = parser.parse_args()
    VERBOSE = True if args.verbose == True else False
    return args

#-------------------------------------------------------------------------------
if __name__ == '__main__':
    # See what the orders are from the command line
    args = parseCommandLine()

    if args.trkdirs == "all" :
        trkdirs = ["run","swim","ski","skiclimb","bike","hike","vehicle","wip"]
    else :
        trkdirs = [args.trkdirs]

    if args.forward == True :
        print("Forward: Check all GPXs have a corresponding GEOJSON")
        for trkdir in trkdirs:
            print("INFO: Processing {} files".format(trkdir))
            fpath = "tracks/3_gpx/" + trkdir
            files = pathlib.Path(fpath).glob("*.gpx")
            for gpxfile in files:
                generate_geojson = False
                if VERBOSE : print(" INFO: processing {}".format(gpxfile))
                geofile = pathlib.Path(str(gpxfile).replace("3_gpx","2_geojson")).with_suffix(".geojson")
                # Generate GeoJSON is it doesnt even exist
                if not geofile.is_file() :
                    print(" ACTION: Need to re-generate {}".format(geofile))
                    generate_geojson = True
                # Re-generate GeoJSON it exists but is older than the GPX file
                else :
                    process = subprocess.run(['git', 'log', '--pretty=format:%cd', '-n 1', '--date=unix', '--', str(gpxfile)],
                             stdout=subprocess.PIPE,
                             universal_newlines=True)
                    timeGPX = process.stdout
                    process = subprocess.run(['git', 'log', '--pretty=format:%cd', '-n 1', '--date=unix', '--', str(geofile)],
                             stdout=subprocess.PIPE,
                             universal_newlines=True)
                    timeGEO = process.stdout
                    if timeGPX > timeGEO :
                        generate_geojson = True
                if generate_geojson == True :
                    if args.dryrun == False :
                        process = subprocess.run(['python', 'scripts/gpx_to_geojson.py', '-s', '-u', str(gpxfile)],
                                 stdout=subprocess.PIPE,
                                 universal_newlines=True)
                        print(termcolor.colored(process.stdout,'green'))

    if args.reverse == True :
        print("Reverse: Check all GEOJSONs have a corresponding GPX")
        for trkdir in trkdirs:
            print("INFO: Processing {} files".format(trkdir))
            fpath = "tracks/2_geojson/" + trkdir
            files = pathlib.Path(fpath).glob("*.geojson")
            for geofile in files:
                if VERBOSE : print(" INFO: processing {}".format(geofile))
                gpxfile = pathlib.Path(str(geofile).replace("2_geojson","3_gpx")).with_suffix(".gpx")
                if not gpxfile.is_file() :
                    print(" ACTION: Need to delete {}".format(geofile))
                    if args.dryrun == False :
                        if os.path.isfile(geofile):
                            os.remove(geofile)
