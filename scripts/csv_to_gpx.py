#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
-------------------------------------------------------------------------------

 DESCRIPTION
    Convert CSV files ifrom FlightRadar into GPX files

 EXAMPLES
    python csv_to_gpx.py -v tracks/tim/7_csv

 IMPLEMENTATION
    Author       Tim Smith
    Copyright    Copyright (c) Tim Smith
    Licence      GNU General Public License

-------------------------------------------------------------------------------
"""

import os
import pathlib
import argparse
import csv
import gpxpy
import datetime
import xml.etree.ElementTree as mod_etree


# -------------------------------------------------------------------------------
# Initialise command line options and their defaults
def parse_command_line():
    global VERBOSE
    # Instantiate the parser
    parser = argparse.ArgumentParser(
        description="Convert CSV track into standardised GPX tracks"
    )
    # Set up the argument defaults
    defaults = dict(
        outdir="./",
        dryrun=False,
        verbose=False,
    )
    parser.set_defaults(**defaults)
    # Parse the command line
    parser.add_argument("files", help="individual csv filename [filenames]", nargs="+")
    parser.add_argument(
        "-d", "--dryrun", action="store_true", help="Dont actually create new files"
    )
    parser.add_argument(
        "-o",
        "--outdir",
        dest="outdir",
        help="Directory to store converted gpx files",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Turn on verbose output"
    )
    args = parser.parse_args()
    VERBOSE = True if args.verbose == True else False
    return args

# -------------------------------------------------------------------------------
# For a track which is already split into segments, create a list of static
def createGPXFile(activity_name, activity_start, activity_sport, csv):
    gpx = gpxpy.gpx.GPX()
    dt = datetime.datetime.fromisoformat(activity_start.replace("Z", "+00:00"))
    gpx.time = dt
    gpx.name = str(activity_name)
    # Create track in GPX:
    gpx_track = gpxpy.gpx.GPXTrack()
    gpx_track.name = activity_name
    gpx_track.comment = str(dt.date())
    gpx_track.type = activity_sport
    gpx.tracks.append(gpx_track)
    # Create segment in GPX track:
    gpx_segment = gpxpy.gpx.GPXTrackSegment()
    gpx_track.segments.append(gpx_segment)
    # Create points:
    for p in csv:
        track_point = gpxpy.gpx.GPXTrackPoint( p["Lat"], p["Lon"], elevation=p["Altitude"], time=dt)
        # add GPX extensions for speed and course
        speed = p["Speed"]
        course = p["Course"]
        namespace = '{gpxtpx}'
        root = mod_etree.Element(f'{namespace}TrackPointExtension')
        sub_sp = mod_etree.SubElement(root, f'{namespace}speed')
        sub_sp.text = str(speed) if speed else '0'
        sub_cr = mod_etree.SubElement(root, f'{namespace}course')
        sub_cr.text = str(course) if course else '0'
#        track_point.extensions.append(root)
        # Append GPX_TrackPoint to segment:
        gpx_segment.points.append(track_point)

    return gpx


# -------------------------------------------------------------------------------
if __name__ == "__main__":
    # See what the orders are from the command line
    args = parse_command_line()

    # Expand any directories passed on the command line into a list of files
    fpaths = []
    for fpath in args.files:
        if os.path.isfile(fpath):
            fpaths.append(fpath)
        elif os.path.isdir(fpath):
            mpaths = [
                os.path.join(dp, f)
                for dp, dn, fn in os.walk(os.path.expanduser(fpath))
                for f in fn
            ]
            # Retain only CSV files from the mpaths list
            fpaths = [file for file in mpaths if file.endswith(".csv")]

    for fpath in fpaths:
        csv_contents = []
        with open(fpath, mode='r') as csv_file:
            csv_reader = csv.DictReader(csv_file)
            for row in csv_reader:
                newrow = {}
                if row["UTC"]:
                    newrow["UTC"] = row["UTC"]
                if row["Altitude"]:
                    newrow["Altitude"] = float(row["Altitude"]) * 0.3048 # converts feet to meters
                if row["Speed"]:
                    newrow["Speed"] = float(row["Speed"]) * 0.514444 # converts to meters per second
                if row["Direction"]:
                    newrow["Course"] = row["Direction"]
                newrow["Lat"] = row["Position"].split(",")[0]
                newrow["Lon"] = row["Position"].split(",")[1]
                csv_contents.append(newrow)
            print("INFO: csv file {} contained {} lines".format(fpath, len(csv_contents)))

        # Create a GPX file in memory from the csv data
        activity_name = pathlib.Path(fpath).stem
        start_date = csv_contents[0]["UTC"]
        gpx = createGPXFile( activity_name, start_date, "Plane" , csv_contents)

        # Write out the GPX file to disk
        if str(args.outdir) == "./":
            outdir = pathlib.Path(fpath).parent
            outfile = pathlib.Path(fpath).with_suffix(".gpx")
        else:
            outfile = args.outdir + "/PLANE_" + pathlib.Path(fpath).stem + ".gpx"
            outdir = args.outdir
        if VERBOSE:
            print("INFO: Writing out new content to {}".format(outfile))
        if args.dryrun == False:
            pathlib.Path(outdir).mkdir(parents=True, exist_ok=True)
            with open(outfile, "w") as f:
                print("INFO: writing file {}".format(outfile))
                f.write(gpx.to_xml())
        else:
            print("WARN: didnt write file {}".format(outfile))
