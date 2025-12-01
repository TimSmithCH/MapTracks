#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
-------------------------------------------------------------------------------

 DESCRIPTION
    Convert FIT files into GPX files

 EXAMPLES
    python fit_to_gpx.py -g MetaData/Activities.json -p -t -o generatedGPX FitFiles
    python fit_to_gpx.py -a MetaData/ActivitiesList.json -p -t -o generatedGPX RawFiles

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
import string
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple, Union
from math import isnan
import xml.etree.ElementTree as mod_etree
import pandas as pd
import fitdecode


# The names of the columns we will use in our points DataFrame. For the data we will be getting
# from the FIT data, we use the same name as the field names to make it easier to parse the data.
POINTS_COLUMN_NAMES = ['latitude', 'longitude', 'lap', 'altitude', 'timestamp', 'heart_rate', 'cadence', 'speed']

# The names of the columns we will use in our laps DataFrame.
LAPS_COLUMN_NAMES = ['number', 'start_time', 'total_distance', 'total_elapsed_time', 'max_speed', 'max_heart_rate', 'avg_heart_rate']

# The names of the columns we will use in our header DataFrame.
FILE_COLUMN_NAMES = ['serial_number', 'manufacturer', 'garmin_product', 'product_name', 'product', 'device_model', 'descriptor', 'time_created']
DEVICE_COLUMN_NAMES = ['serial_number', 'manufacturer', 'garmin_product', 'product_name', 'product', 'device_model', 'descriptor', 'time_created']
HEADER_COLUMN_NAMES = ['time_created']
SPORT_COLUMN_NAMES = ['name', 'sport', 'total_elapsed_time']
EVENT_COLUMN_NAMES = ['timestamp','event_type']

# -------------------------------------------------------------------------------
# Initialise command line options and their defaults
def parse_command_line():
    global VERBOSE
    # Instantiate the parser
    parser = argparse.ArgumentParser(
        description="Convert FIT files into GPX files"
    )
    # Set up the argument defaults
    defaults = dict(
        activities=None,
        dryrun=False,
        garmin=None,
        extensions=False,
        pretty=False,
        trim=False,
        verbose=False,
    )
    parser.set_defaults(**defaults)
    # Parse the command line
    parser.add_argument("files", help="individual fit filename [filenames]", nargs="+")
    parser.add_argument(
        "-a", "--activities", dest="activities", help="Strava activites file name with extra metadata for FIT files"
    )
    parser.add_argument(
        "-d", "--dryrun", action="store_true", help="Dont actually create new files"
    )
    parser.add_argument(
        "-e", "--extensions", action="store_true", help="Also add extension metadata (heartrate, cadence) to gpx file"
    )
    parser.add_argument(
        "-g", "--garmin", dest="garmin", help="Garmin activites file name with extra metadata for FIT files"
    )
    parser.add_argument(
        "-o", "--outdir", dest="outdir", help="Directory to store converted gpx files",
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


# Note: get_fit_laps(), get_fit_points(), get_dataframes() are shamelessly copied (and adapted) from:
# https://github.com/bunburya/fitness_tracker_data_parsing/blob/main/parse_fit.py
# -------------------------------------------------------------------------------
# Parse Frame to extract Lap data
def get_fit_lap_data(frame: fitdecode.records.FitDataMessage) -> Dict[str, Union[float, datetime, timedelta, int]]:
    """Extract some data from a FIT frame representing a lap and return
    it as a dict.
    """

    data: Dict[str, Union[float, datetime, timedelta, int]] = {}

    for field in LAPS_COLUMN_NAMES[1:]:  # Exclude 'number' (lap number) because we don't get that
                                        # from the data but rather count it ourselves
        if frame.has_field(field):
            data[field] = frame.get_value(field)

    return data


# -------------------------------------------------------------------------------
# Parse Frame to extract Point data
def get_fit_point_data(frame: fitdecode.records.FitDataMessage) -> Optional[Dict[str, Union[float, int, str, datetime]]]:
    """Extract some data from an FIT frame representing a track point
    and return it as a dict.
    """

    data: Dict[str, Union[float, int, str, datetime]] = {}

    if not (frame.has_field('position_lat') and frame.has_field('position_long')):
        # Frame does not have any latitude or longitude data. We will ignore these frames in order to keep things
        # simple, as we did when parsing the TCX file.
        return None
    elif frame.get_value('position_lat') is None and frame.get_value('position_long') is None:
        # Frame lat or long is None. Ignore frame
        return None
    else:
        data['latitude'] = frame.get_value('position_lat') / ((2**32) / 360)
        data['longitude'] = frame.get_value('position_long') / ((2**32) / 360)

    for field in POINTS_COLUMN_NAMES[3:]:
        if frame.has_field(field):
            data[field] = frame.get_value(field)

    return data


# -------------------------------------------------------------------------------
# Parse Frame to extract Header data
def get_fit_header_data(frame: fitdecode.records.FitDataMessage,frame_type) -> Dict[str, str]:
    """Extract some data from an FIT frame representing a device, sport or session
    """

    data: Dict[str] = {}

    if frame_type == "sport":
        COLUMNS = SPORT_COLUMN_NAMES
    elif frame_type == "event":
        COLUMNS = EVENT_COLUMN_NAMES
    elif frame_type == "file":
        COLUMNS = FILE_COLUMN_NAMES
    elif frame_type == "device":
        COLUMNS = DEVICE_COLUMN_NAMES
    else:
        COLUMNS = HEADER_COLUMN_NAMES

    for field in COLUMNS:
        if frame.has_field(field):
            value = frame.get_value(field)
            if value != None and value != 0:
                data[field] = value

    return data


# -------------------------------------------------------------------------------
# Process Strava metadata fields to produce sanitised/standardised expected fields
def process_activities(activities: pd.DataFrame, source: str, ts: datetime.timestamp, elapsed: int, file_created_ts: datetime.timestamp, verbose: str) -> [str,str,str]:
    strava_web_types = {"AlpineSki":"ski",
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
    garmin_web_types = {"cycling":"bike",
                "hiking":"hike",
                "indoor_cardio":"wip",
                "indoor_cycling":"bike",
                "lap_swimming":"swim",
                "mountain_biking":"bike",
                "mountaineering":"hike",
                "multi_sport":"wip",
                "open_water_swimming":"swim",
                "resort_skiing_snowboarding_ws":"ski",
                "running":"run",
                "transition_v2":"wip",
            }

    title = None
    act_id = None
    ty = None
    if source == "garmin":
        col_activity = "beginTimestamp"
        col_id = "activityId"
        col_type = "activityType"
        act_types = garmin_web_types
    elif source == "strava":
        col_activity = "start_date"
        col_id = "id"
        col_type = "type"
        act_types = strava_web_types

    if len(activities) != 0:
        rows = activities.loc[activities[col_activity] == ts]
        # No exact match so find a nearest neighbour search, in case started slightly before activity
        if len(rows.index) == 0:
            row_series = activities.iloc[(activities[col_activity]-ts).abs().idxmin()]
            # iLoc returns a series not a dataframe (unlike Loc) so convert back to dataframe
            rows = row_series.to_frame().T
            nnts = int(rows[col_activity].iloc[0])
            seconds_diff = int(nnts-ts)
            if abs(seconds_diff) <= 300:
                print(" INFO: no exact match for {} but found start timestamp {} only {} seconds away".format(ts, nnts, seconds_diff))
            else:
                percentage = round(100*(seconds_diff)/elapsed)
                # For a file cropped in Strava the start timestamp is within elapsed time (first half-ish)
                if percentage > 0 and percentage < 42:
                    print(" INFO: no exact match for {} but found start timestamp {} at {} percent into workout (cropped?)".format(ts, nnts, percentage))
                # For a file cropped in Garmin the start timestamp is between file created and Strava start
                elif nnts > file_created_ts:
                    print(" INFO: no exact match for {} but found start timestamp {} after file created {} (delayed start?)".format(ts, nnts, file_created_ts))
                else:
                    print(" WARN: no exact match for {} (closest was {} secs, {} % through)".format(ts, seconds_diff, percentage))
                    print(" WARN:        event_start {} ({})".format(ts, datetime.fromtimestamp(ts)))
                    print(" WARN:      nearest start {} ({})".format(nnts, datetime.fromtimestamp(nnts)))
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
            act_id = rows[col_id].iloc[0]
            # Get title from activity metadata
            s = rows['name'].iloc[0]
            #s = re.sub(r"[^\w\s]", ' ', s)
            #title = re.sub(r"\s+", '_', s)
            s = re.sub(r"-", " ", s)
            s = re.sub(r"/", " ", s)
            s = re.sub(r"\s+", "_", s)
            remove = string.punctuation
            remove = remove.replace("_", "")  # don't remove underscores
            remove = remove.replace(".", "")  # don't remove dots
            title = s.translate(str.maketrans("", "", remove))
            title = re.sub(
                r"_$", "", title
            )  # dont leave an underscore as last letter
            # Get activity type from activity metadata
            act_ty = rows[col_type].iloc[0]
            if act_ty not in act_types:
                print("WARN: unmapped activity type {}".format(act_ty))
            ty = act_types.get(act_ty,None)
            # Override type for commutes
            comm = rows.iloc[0].get('commute',None)
            #comm = rows['commute'].iloc[0]
            if comm and ty == 'bike':
                ty = 'commute'

        if verbose:
            print("Found activity {} with title {} and type {}".format(act_id,title,ty))

    return [act_id, title, ty]


# -------------------------------------------------------------------------------
# Process found header fields to produce sanitised/standardised expected fields
def tidy_header(header: Dict, activities: pd.DataFrame, source: str, verbose: str) -> Dict:
    """
     List of Watch codes from https://everymac.com/systems/apple/apple-watch/index-apple-watch-specs.html
     List of Phone codes from https://everymac.com/systems/apple/iphone/index-iphone-specs.html
    """
    types = {"Bike":"bike",
             "Cardio":"wip",
             "Climb":"hike",
             "Cycling":"bike",
             "Hike":"hike",
             "Hiking":"hike",
             "Indoor Cycling":"bike",
             "Mountain Biking":"bike",
             "Mountaineering":"hike",
             "Multisport":"wip",
             "Open Water":"swim",
             "Open Water Swimming":"swim",
             "Pool Swim":"swim",
             "Resort Skiing/Snowboarding":"ski",
             "Run":"run",
             "Running":"run",
             "cycling":"bike",
             "training":"wip",
             "mountaineering":"hike",
             "hiking":"hike",
             "swimming":"swim",
             "running":"run",
             "alpine_skiing":"ski",
            }
    product_lookup = {101:"iPhone", 162:"iWatch9", 163:"iWatchUltra2",1163:"iWatchWorkout"}
    device_lookup = {"iPhone12,1":"iPhone11",
                     "iPhone13,2":"iPhone12",
                     "iPhone14,5":"iPhone13",
                     "Watch7,1":"iWatch9_41mm"}
    manufacturer_lookup = {1:"Garmin", 265:"Strava"}
    key_dict = {}
    title = None
    act_id = None

    # Establish the timestamp and find associated metadata from Activities file
    if "timestamp" in header:
        ts_length = len(str(int(datetime.timestamp(header.get("timestamp")))))
        if ts_length > 10:
            print(" WARN: timestamp in header has {} digits, expected 10 for seconds resolution".format(ts_length))
        header.update({"time": header.get("timestamp").strftime('%Y/%m/%d')})
        ts = int(datetime.timestamp(header.get("timestamp")))
        et = header.get("total_elapsed_time")
        tc = int(datetime.timestamp(header.get("time_created")))
        act_id, title, ty = process_activities(activities, source, ts, et, tc, verbose)
    else:
        print("WARN: No timestamp in header, skipping")
        return header


    # Establish the activity type: first use Activities file then fall back on FIT file
    if not ty:
        if "name" in header:
            ty = types.get(header.get("name"),"wip")
        elif "sport" in header:
            ty = types.get(header.get("sport"),"wip")
        else:
            ty = "wip"
    header.update({"type": ty})

    # Establish the activity title
    if title:
        header.update({"title": title})
    else:
        header.update({"title": ty})

    # Establish the device and application which recorded the activity
    # Garmin devices
    if "garmin_product" in header:
        app = header.get("manufacturer")
        dev = header.get("garmin_product")
    # Strava app on iPhone and iWatch
    elif "device_model" in header:
        app = header.get("manufacturer")
        mod = header.get("device_model")
        dev = device_lookup.get(mod,mod)
    # Coros devices and WordkOutDoors/NikeRunClub/AsicsRunkeeper apps on iWatch
    elif "product_name" in header:
        prd = header.get("product_name")
        dev = device_lookup.get(prd,prd)
        # Override with descriptor for NikeRunClub/AsicsRunkeeper apps
        if "descriptor" in header:
            app = header.get("descriptor")
        # Swap fields for WorkOutDoors app
        elif prd == "WorkOutDoors":
            app = "WorkOutDoors"
            dev = "iWatch"
        else:
            app = header.get("manufacturer")
    # Catch-all
    else:
        app = header.get("manufacturer")
        prd = header.get("product",None)
        dev = product_lookup.get(prd,prd)
    if app:
        key_dict.update({"dv": dev.split(",",1)[0]})
        key_dict.update({"ap": app})

    # Establish the activity ID
    if act_id:
        if source == "garmin":
            key_dict.update({"gid": str(act_id)})
        elif source == "strava":
            key_dict.update({"sid": str(act_id)})

    # Add the keywords string
    header.update({"keywords": key_dict})

    return header


# -------------------------------------------------------------------------------
# Parse FIT file and load intermediate Pandas DataFrames
def get_dataframes(fname: str) -> Tuple[pd.DataFrame, pd.DataFrame, Dict]:
    """Takes the path to a FIT file (as a string) and returns two Pandas
    DataFrames: one containing data about the laps, and one containing
    data about the individual points, and a header dictionary
    """

    points_data = []
    laps_data = []
    lap_no = 1
    file_found = False
    device_found = False
    event_start_found = False
    header = {}

    try:
        # Possible handling directives: IGNORE / WARN / RAISE
        fit_file = fitdecode.FitReader(fname, error_handling=fitdecode.reader.ErrorHandling.WARN)
        for frame in fit_file:
            if isinstance(frame, fitdecode.FitDataMessage):
                if frame.name == 'record':
                    single_point_data = get_fit_point_data(frame)
                    if single_point_data is not None:
                        single_point_data['lap'] = lap_no
                        points_data.append(single_point_data)
                elif frame.name == 'lap':
                    single_lap_data = get_fit_lap_data(frame)
                    single_lap_data['number'] = lap_no
                    laps_data.append(single_lap_data)
                    lap_no += 1
                # For Garmin devices and Strava apps FILE_ID records contain a product string, otherwise need DEVICE_INFO record
                elif file_found == False and frame.name == 'file_id':
                    header_data = get_fit_header_data(frame, "file")
                    header.update(header_data)
                    file_found = True
                    print(" DEBUG: frame {}: found {}".format(frame.name, header_data))
                elif device_found == False and frame.name == 'device_info':
                    header_data = get_fit_header_data(frame, "device")
                    # Only add new keys, dont overwrite already found ones
                    for key in header_data:
                        if key not in header:
                            header[key] = header_data[key]
                    device_found = True
                    print(" DEBUG: frame {}: found {}".format(frame.name, header_data))
                elif frame.name == 'sport' or frame.name == 'session':
                    header_data = get_fit_header_data(frame, "sport")
                    header.update(header_data)
                # event records are written at various times, but only after event_start is the timing info relevant
                elif frame.name == 'event' and event_start_found == False:
                    header_data = get_fit_header_data(frame, "event")
                    if "event_type" in header_data:
                        if header_data.get("event_type") == "start":
                            header.update(header_data)
                            event_start_found = True
                            print(" DEBUG: frame {}: found {}".format(frame.name, header_data))
    except:
        print("ERROR while parsing {} so dropping stream".format(fname))
        print(points_df)
        points_df = pd.DataFrame()
        laps_df = pd.DataFrame()
    else:
        # Create DataFrames from the data we have collected. If any information is missing from a particular lap or track
        # point, it will show up as a null value or "NaN" in the DataFrame.
        laps_df = pd.DataFrame(laps_data, columns=LAPS_COLUMN_NAMES)
        laps_df.set_index('number', inplace=True)
        points_df = pd.DataFrame(points_data, columns=POINTS_COLUMN_NAMES)
    
    # Tidy up
    fit_file.close()

    return laps_df, points_df, header


# -------------------------------------------------------------------------------
# Convert a Pandas DataFrame to GPX
# Method adapted from: https://github.com/nidhaloff/gpx-converter/blob/master/gpx_converter/base.py
def dataframe_to_gpx(trim, header, df_points, col_lat='latitude', col_long='longitude', col_time=None, col_alt=None,
                     col_hr=None, col_cad=None, gpx_name=None, gpx_time=None, gpx_desc=None, gpx_link=None,
                     gpx_type=None, gpx_keywords=None):

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

    # add extension to be able to add heartrate and cadence
    if col_hr or col_cad:
        gpx.nsmap = {'gpxtpx': 'http://www.garmin.com/xmlschemas/TrackPointExtension/v1'}

    # Step 2: Assign GPX track metadata
    gpx.tracks[0].name = gpx_name
    gpx.tracks[0].comment = str(gpx_time.date())
    gpx.tracks[0].type = gpx_type
    #gpx.tracks[0].description = gpx_desc if not pd.isna(gpx_desc) else None
    #gpx.tracks[0].link = gpx_link

    # Step 3: Add points from dataframe to GPX track:
    for idx in df_points.index:
        # Create trackpoint:
        if isnan(df_points.loc[idx, col_alt]):
            track_point = gpxpy.gpx.GPXTrackPoint(
                latitude=df_points.loc[idx, col_lat],
                longitude=df_points.loc[idx, col_long],
                time=pd.Timestamp(df_points.loc[idx, col_time]) if col_time else None,
                # Do not include elevation if nan
            )
        else:
            track_point = gpxpy.gpx.GPXTrackPoint(
                latitude=df_points.loc[idx, col_lat],
                longitude=df_points.loc[idx, col_long],
                time=pd.to_datetime(df_points.loc[idx, col_time],unit='ms') if col_time else None,
                elevation=df_points.loc[idx, col_alt] if col_alt else None,
            )
        if trim:
            # Keep 6 decimal places in position
            track_point.latitude = round(track_point.latitude,6)
            track_point.longitude = round(track_point.longitude,6)
            if track_point.elevation != None:
                # Keep 1 decimal place in elevation
                track_point.elevation = int(10*track_point.elevation)/10

        # add GPX extensions for heartrate and cadence
        if col_hr or col_cad:
            namespace = '{gpxtpx}'
            root = mod_etree.Element(f'{namespace}TrackPointExtension')
            if col_hr:
                sub_hr = mod_etree.SubElement(root, f'{namespace}hr')
                sub_hr.text = str(df_points.loc[idx, col_hr]) if col_hr else '0'

            if col_cad:
                sub_cad = mod_etree.SubElement(root, f'{namespace}cad')
                sub_cad.text = str(df_points.loc[idx, col_cad]) if col_cad else '0'
            track_point.extensions.append(root)

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
            # Retain only FIT files from the mpaths list
            fpaths = [file for file in mpaths if file.endswith(".fit")]
            fpaths.sort()

    # Digest an associated Garmin activities file for extra metadata
    if args.garmin != None:
        source = "garmin"
        print("INFO: Reading GARMIN activities file {}".format(args.garmin))
        with open(args.garmin) as f:
            d = json.load(f)
            activities = pd.DataFrame(d[0]['summarizedActivitiesExport'])
            # Convert 13 digit timestamps (milliseconds) to 10 digit (seconds)
            activities['beginTimestamp'] = activities['beginTimestamp'].floordiv(1000)
            ##if args.verbose:
            ##    print(activities)
    # Digest an associated Strava activities file for extra metadata
    elif args.activities != None:
        source = "strava"
        print("INFO: Reading STRAVA activities file {}".format(args.activities))
        with open(args.activities) as f:
            activities = pd.DataFrame(json.load(f))
            # Convert datetime string to timestamp 10 digit (seconds)
            activities['start_date'] = activities['start_date'].apply(convert_to_timestamp)
            ##if args.verbose:
            ##    print(activities)
    else:
        activities = pd.DataFrame()

    # Loop over all files in list
    outcount = 0
    outtotal = len(fpaths)
    for fpath in fpaths:
        outcount += 1
        # Step 1: Convert FIT to pd.DataFrame
        df_laps, df_points, header = get_dataframes(fpath)
        if df_points.empty:
            print("INFO: no data points in {} so skipping file writing".format(fpath))
            continue
        else:
            header = tidy_header(header, activities, source, args.verbose)
        if args.verbose:
            print(fpath, " : ", header)
            print("Number of GPX points: {}".format(len(df_points.index)))
        #print(df_points)

        # Step 2: Fill gaps in data if FIT file recorded data only in enhanced altitude/speed columns:
#        enhanced_fields = ['altitude', 'speed']
#        for field in enhanced_fields:
#            if df_points[field].count() == 0 and df_points[f'enhanced_{field}'].count() > 0:
#                df_points[field] = df_points[field].fillna(df_points[f'enhanced_{field}'])

        # Step 3: Convert pd.DataFrame to GPX
        gpx = dataframe_to_gpx(
            trim=args.trim,
            header=header,
            df_points=df_points,
            col_lat='latitude',
            col_long='longitude',
            col_time='timestamp',
            col_alt='altitude',
            col_hr='heart_rate' if args.extensions else None,
            col_cad='cadence' if args.extensions else None,
            gpx_name=header["title"],
            gpx_time=header["timestamp"],
            #gpx_desc=header["description"],
            gpx_type=header["type"],
            #gpx_link=header["link"],
            gpx_keywords=header["keywords"],
        )

        # Step 3: Save GPX file to disk
        outfile = clean_filename(fpath, args.outdir, header)
        xml = gpx.to_xml(prettyprint=args.pretty)
        device = header.get("keywords").get("dv")
        print("INFO: [{}/{}] Converted {} from {} and writing gpx content to {}".format(outcount,outtotal,fpath, device, outfile))
        if args.dryrun == False :
            with open(outfile, "w") as f:
                f.write(xml)
