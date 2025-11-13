#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
-------------------------------------------------------------------------------

 DESCRIPTION
    Convert Strava JSON files into GPX files

 EXAMPLES
    python json_to_gpx.py -p -t -o generatedGPX FitFiles

 IMPLEMENTATION
    Author       Tim Smith
    Copyright    Copyright (c) Tim Smith
    Licence      GNU General Public License

-------------------------------------------------------------------------------
"""

import os
import pathlib
import argparse
import gpxpy
import json
import re
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, Tuple, Union
from math import isnan
import pandas as pd


# -------------------------------------------------------------------------------
# Initialise command line options and their defaults
def parse_command_line():
    global VERBOSE
    # Instantiate the parser
    parser = argparse.ArgumentParser(
        description="Convert Strava JSON files into GPX files"
    )
    # Set up the argument defaults
    defaults = dict(
        activities=None,
        dryrun=False,
        extensions=False,
        pretty=False,
        trim=False,
        verbose=False,
    )
    parser.set_defaults(**defaults)
    # Parse the command line
    parser.add_argument("files", help="individual json filename [filenames]", nargs="+")
    parser.add_argument(
        "-a", "--activities", dest="activities", help="Activites file name with extra metadata for JSON files"
    )
    parser.add_argument(
        "-d", "--dryrun", action="store_true", help="Dont actually create new files"
    )
    parser.add_argument(
        "-e", "--extensions", action="store_true", help="Also add extension metadata (heartrate, cadence) to gpx file"
    )
    parser.add_argument(
        "-o",
        "--outdir",
        dest="outdir",
        help="Directory to store converted gpx files",
    )
    parser.add_argument(
        "-p", "--pretty", action="store_true", help="Format the output with indentations"
    )
    parser.add_argument(
        "-t", "--trim", action="store_true", help="Trim the GPX, making elevations integer and lat/lon 6 digit max"
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Turn on verbose output"
    )
    args = parser.parse_args()
    VERBOSE = True if args.verbose == True else False
    return args


# -------------------------------------------------------------------------------
# Process metadata fields to produce sanitised/standardised expected fields
def process_activities(activities: pd.DataFrame, activity_column: str, ts: datetime.timestamp) -> [str,str,str]:
    web_types = {"AlpineSki":"ski",
                 "BackcountrySki":"skiclimb",
                 "Hike":"hike",
                 "Ride":"bike",
                 "RockClimbing":"wip",
                 "Rowing":"vehicle",
                 "Run":"run",
                 "Sail":"vehicle",
                 "StandUpPaddling":"vehicle",
                 "Swim":"swim",
                 "Velomobile":"vehicle",
                 "VirtualRun":"run",
                 "Walk":"hike",
                 "Workout":"wip",
            }
    title = None
    act_id = None
    ty = None

    if len(activities) != 0:
        rows = activities.loc[activities[activity_column] == ts]
        # No exact match so find a nearest neighbour search, in case started slightly before activity
        if len(rows.index) == 0:
            row_series = activities.iloc[(activities[activity_column]-ts).abs().idxmin()]
            # iLoc returns a series not a dataframe (unlike Loc) so convert back to dataframe
            rows = row_series.to_frame().T
            cts = rows[activity_column].iloc[0]
            seconds_diff = abs(cts-ts)/1000
            if int(seconds_diff) <= 180:
                print("INFO: no exact match for {} but found start timestamp {} only {} seconds away".format(ts, cts, seconds_diff))
            else:
                print("WARN: no activity exact match found for timestamp {} (closest was {} secs away)".format(ts, seconds_diff))
                print("WARN:            event_start {} ({})".format(int(ts/1000), datetime.fromtimestamp(ts/1000)))
                print("WARN: nearest activity start {} ({})".format(int(cts/1000), datetime.fromtimestamp(cts/1000)))
                #print("WARN:           file created {} ({})".format(int(datetime.timestamp(header.get("time_created"))),header.get("time_created")))
                rows = pd.DataFrame()
        elif len(rows.index) > 1:
            print("WARN: Bizzarely found too many matches ({}) for timestamp {}".format(len(rows.index),ts))
            if rows['duration'].iloc[0] == rows['duration'].iloc[1]:
                print("INFO: But they seem to be duplicates so can use first one anyway")
            else:
                print("WARN: and since they are different, stop processing")
                rows = pd.DataFrame()
                seconds_diff = -1

        # Correctly found activity from start time
        if len(rows.index) != 0:
            # Get activityID from activity metadata
            act_id = rows['id'].iloc[0]
            # Get title from activity metadata
            s = rows['name'].iloc[0]
            s = re.sub(r"[^\w\s]", ' ', s)
            title = re.sub(r"\s+", '_', s)
            # Get activity type from activity metadata
            act_ty = rows['type'].iloc[0]
            if act_ty not in web_types:
                print("WARN: unmapped activity type {}".format(act_ty))
            ty = web_types.get(act_ty,None)
            # Override type for commutes
            comm = rows['commute'].iloc[0]
            if comm and ty == 'bike':
                ty = 'commute'

        if args.verbose:
            print("Found activity {} with title {} and type {}".format(act_id,title,ty))

    return [act_id, title, ty]


# -------------------------------------------------------------------------------
# Process metadata fields to produce sanitised/standardised expected fields
def prepare_header(md: Dict, activities: pd.DataFrame) -> Dict:
    app_types = {"ride":"bike",
                 "run":"run",
            }
    header = {}
    key_dict = {}

    # Establish the timestamp and find associated metadata from Activities file
    dt = datetime.fromisoformat(md['start_date'])
    header.update({"timestamp": dt.astimezone(timezone.utc)})
    ts = int(datetime.timestamp(dt))
    act_id, title, ty = process_activities(activities, 'start_date', ts)

    # Establish the activity type
    if not ty:
        if "activity_type" in md:
            act_ty = md.get("activity_type")
            if act_ty not in app_types:
                print("WARN: unmapped activity type {}".format(act_ty))
            ty = app_types.get(act_ty,"wip")
        else:
            ty = "wip"
    header.update({"type": ty})

    # Establish the activity title
    if title:
        header.update({"title": title})
    else:
        if "activity_name" in md:
            header.update({"title": md.get("activity_name")})
        else:
            header.update({"title": ty})

    # Establish the manufacturer and product
    if "http_user_agent" in md:
        products = (md.get("http_user_agent")).split("|")
        key_dict.update({"ma": products[0]})
        key_dict.update({"pr": re.sub(r",",'_',products[2])})
        if act_id:
            key_dict.update({"sid": str(act_id)})
        header.update({"keywords": key_dict})

    return header


# -------------------------------------------------------------------------------
# Convert a Pandas DataFrame to GPX
# Method adapted from: https://github.com/nidhaloff/gpx-converter/blob/master/gpx_converter/base.py
def dataframe_to_gpx(trim, header, df_points, col_lat='latitude', col_long='longitude', col_time=None, col_alt=None,
                     gpx_name=None, gpx_time=None, gpx_type=None, gpx_keywords=None):

    # Step 0: Check that the input dataframe has all required columns
    cols_to_check = [col_lat, col_long]
    if col_alt:
        cols_to_check.append(col_alt)
    if col_time:
        cols_to_check.append(col_time)

    if any(elem not in df_points.columns for elem in cols_to_check):
        raise KeyError("The input dataframe must consist of point coordinates in longitude and latitude. "
                       "Ideally, it should be the df_points output from the fit_to_dataframes() method.")

    # Step 1: Initiate GPX object
    gpx = gpxpy.gpx.GPX()
    #dt = pd.Timestamp(df_points.loc[1, col_time]) if col_time else None
    gpx.time = gpx_time
    gpx.name = gpx_name
    gpx.keywords = json.dumps(gpx_keywords,separators=(",",":"))
    # -- create first track in our GPX:
    gpx_track = gpxpy.gpx.GPXTrack()
    gpx.tracks.append(gpx_track)
    # -- create first segment in our GPX track:
    gpx_segment = gpxpy.gpx.GPXTrackSegment()
    gpx_track.segments.append(gpx_segment)

    # Step 2: Assign GPX track metadata
    gpx.tracks[0].name = gpx_name
    gpx.tracks[0].comment = str(gpx_time.date())
    gpx.tracks[0].type = gpx_type

    # Step 3: Add points from dataframe to GPX track:
    for idx in df_points.index:
        # Create trackpoint:
        if isnan(df_points.loc[idx, col_alt]):
            track_point = gpxpy.gpx.GPXTrackPoint(
                latitude=df_points.loc[idx, col_lat],
                longitude=df_points.loc[idx, col_long],
                time=datetime.fromtimestamp(int(df_points.loc[idx, col_time]),timezone.utc) if col_time else None,
                # Do not include elevation if nan
            )
        else:
            track_point = gpxpy.gpx.GPXTrackPoint(
                latitude=df_points.loc[idx, col_lat],
                longitude=df_points.loc[idx, col_long],
                time=datetime.fromtimestamp(int(df_points.loc[idx, col_time]),timezone.utc) if col_time else None,
                elevation=df_points.loc[idx, col_alt] if col_alt else None,
            )
        if trim:
            # Keep 6 decimal places in position
            track_point.latitude = round(track_point.latitude,6)
            track_point.longitude = round(track_point.longitude,6)
            if track_point.elevation != None:
                # Keep 1 decimal place in elevation
                track_point.elevation = int(10*track_point.elevation)/10

        # Append GPX_TrackPoint to segment:
        gpx_segment.points.append(track_point)

    return gpx


# -------------------------------------------------------------------------------
# Standardise ouput filename if required
def clean_filename(fname:str, outdir:str, header:Dict) -> str:

    orig_name = pathlib.Path(fname).stem
    orig_path = pathlib.Path(fname).parent
    ts = int(datetime.timestamp(header.get("timestamp")))
    kw = header.get("keywords")
    pr = kw.get("pr")
    ti = header.get("title")

    # If filename specified, simply use it
    if outdir and not pathlib.Path(str(outdir)).is_dir():
        outfile = outdir
    # Otherwise standardise the name to date/id/title
    else:
        #of = str(ts) + "." + str(pr) + "." + str(ti) + ".gpx"
        of = str(ts) + "." + str(ti) + ".gpx"
        if outdir:
            outfile = outdir + "/" + of
        else:
            outfile = str(orig_path) + "/" + of

    return outfile


# -------------------------------------------------------------------------------
# Convert from ISO format date to TimeStamp
def convert_to_timestamp(isodate):
    dt = datetime.fromisoformat(isodate.replace("Z", "+00:00"))
    ctimestamp = int(datetime.timestamp(dt))
    return ctimestamp


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
            # Retain only JSON files from the mpaths list
            fpaths = [file for file in mpaths if file.endswith(".json")]
            fpaths.sort()

    # Digest an associated activities file for extra metadata
    if args.activities != None:
        with open(args.activities) as f:
            #d = json.load(f)
            activities = pd.DataFrame(json.load(f))
            activities['start_date'] = activities['start_date'].apply(convert_to_timestamp)
            if args.verbose:
                print(activities)
    else:
        activities = pd.DataFrame()

    # Loop over all files in list
    for fpath in fpaths:
        # Step 1: Convert JSON to pd.DataFrame
        with open(fpath) as f:
            d = json.load(f)
            # Load the track data into a dataframe
            track_df = pd.DataFrame(d['data'][0]['values'])
            track_df.columns = d['data'][0]['fields']
            # Split the LatLon array column into two seperate columns
            track_df['latitude'],track_df['longitude'] = zip(*list(track_df['latlng'].values))
            if args.verbose:
                print(track_df)
            # Load the metadata into a dict
            md = d['metadata']
            if args.verbose:
                print(md)

        header = prepare_header(md, activities)
        if args.verbose:
            print(fpath, " : ", header)
            print("Number of GPX points: {}".format(len(track_df.index)))

        # Step 2: Convert pd.DataFrame to GPX
        gpx = dataframe_to_gpx(
            trim=args.trim,
            header=header,
            df_points=track_df,
            col_lat='latitude',
            col_long='longitude',
            col_time='time',
            col_alt='elevation',
            gpx_name=header["title"],
            gpx_time=header["timestamp"],
            gpx_type=header["type"],
            gpx_keywords=header["keywords"],
        )

        # Step 3: Save GPX file to disk
        outfile = clean_filename(fpath, args.outdir, header)
        xml = gpx.to_xml(prettyprint=args.pretty)
        print("INFO: Converted {} and writing gpx content to {}".format(fpath, outfile))
        if args.dryrun == False :
            with open(outfile, "w") as f:
                f.write(xml)
