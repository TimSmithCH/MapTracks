#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
-------------------------------------------------------------------------------

 DESCRIPTION
    Download Strava data to create GPX files per activity. Use the Strava API
    to construct an activity list since last download, then for each activity
    download Strava's actvity streams and reconstruct a GPX file from the data
 ACTIONS
     - Add metadata block containing: time, name, keywords (strava activity id)
     - Add track block containing: name, comment (date), type
     - Add 1 track with 1 segment of points consisting of: lat, long, elevation, time
     - Filename contains {Strava activity id}.{activity name}

 EXAMPLES
    python pull_strava_data.py -o "tracks/" -a tim -p 20 -n 1            # Basic, last 20 activities in one page
    python pull_strava_data.py -c False -o "tracks/" -p 100 -b 20220201  # Exclude commutes, work back from 1st Feb 2022
    python scripts/pull_strava_data.py -l -o "tracks/" -p 10 -b 20230402 # Light mode, only new files

 IMPLEMENTATION
    Author       Tim Smith
    Copyright    Copyright (c) Tim Smith
    Licence      GNU General Public License

-------------------------------------------------------------------------------
"""

import json
import time
import datetime
import os
import re
import string
from argparse import ArgumentParser
from pathlib import Path
from typing import Any

import requests
import gpxpy

# Define global variables
# orders = {}


# -------------------------------------------------------------------------------
# Initialise command line options and their defaults
def parse_command_line():
    global orders
    # If run in Github ACTION then set defaults without parsing!
    if os.getenv("GITHUB_ACTIONS") == "true":
        athlete = os.environ.get("STRAVA_ATHLETE")
        orders = {
            "athlete": athlete,
            "tokenFile": "tracks/" + athlete + "/token.json",
            "trackDir": "tracks/" + athlete + "/3_gpx/",
            "idFile": "tracks/" + athlete + "/LastStravaIDRead.json",
            "pagesize": 40,
            "numpages": 3,
            "commute": True,
            "light": False,
            "zero": False,
            "verbose": True,
            "work": False,
        }
    # Parse command line arguments if not run in a Github ACTION
    else:
        # Instantiate the parser
        parser = ArgumentParser(
            description="Download latest activities via Strava API."
        )
        # Set up the argument defaults
        defaults = dict(
            athlete="tim",
            outdir="./",
            pagesize=10,
            numpages=3,
            commute=True,
            light=False,
            zero=False,
            verbose=False,
            work=False,
        )
        parser.set_defaults(**defaults)
        # Parse the command line
        parser.add_argument("-a", "--athlete", help="Athlete name")
        parser.add_argument(
            "-o", "--outdir", help="Directory to store downloaded Strava activity files"
        )
        parser.add_argument(
            "-b", "--before", help="Upper date bound to search back from"
        )
        parser.add_argument("-s", "--specdate", help="Specific date to search for")
        parser.add_argument(
            "-p",
            "--pagesize",
            help="Number of activities per page for Strava API download",
        )
        parser.add_argument(
            "-n",
            "--numpages",
            help="Number of pages of activities for Strava API download",
        )
        parser.add_argument(
            "-c", "--commute", action="store_false", help="Ignore commutes"
        )
        parser.add_argument(
            "-w", "--work", action="store_true", help="Only commutes"
        )
        parser.add_argument(
            "-l",
            "--light",
            action="store_true",
            help="Light mode: Dont download data if file already exists",
        )
        parser.add_argument(
            "-z",
            "--zero",
            action="store_true",
            help="Zero downloads: only store activity list",
        )
        parser.add_argument(
            "-v", 
            "--verbose", 
            action="store_true",
            help="Print verbose output"
        )
        args = parser.parse_args()
        athlete = args.athlete.lower()
        orders = {
            "athlete": athlete,
            "tokenFile": args.outdir + athlete + "/" + "token.json",
            "trackDir": args.outdir + athlete + "/3_gpx/",
            "idFile": args.outdir + athlete + "/" + "LastStravaIDRead.json",
            "listfile": args.outdir + athlete + "/" + "ActivitiesList.json",
            "verbose": args.verbose,
        }
        if args.before:
            orders["before"] = args.before
        if args.pagesize:
            orders["pagesize"] = args.pagesize
        if args.numpages:
            orders["numpages"] = args.numpages
        # Strava overall rate limits: 200 requests every 15 minutes, 2,000 daily
        # Strava read rate limits: 100 requests every 15 minutes, 1,000 daily
        if int(args.numpages) * int(args.pagesize) > 200:
            print(
                f"WARNING: Dont spam Strava API: {args.numpages} pages x {args.pagesize} "
                f"pagesize too large setting to 3x20"
            )
            # orders["pagesize"] = 20
            # orders["numpages"] = 3
        if args.specdate:
            orders["pagesize"] = 7
            orders["numpages"] = 1
            orders["specdate"] = args.specdate
            orders["before"] = str(int(args.specdate) + 1)
        orders["commute"] = args.commute
        orders["light"] = args.light
        orders["zero"] = args.zero
        orders["work"] = args.work


# -------------------------------------------------------------------------------
def init():
    global orders
    global tokens
    global stravaData
    # New pythonic way to check and create directory tree
    Path(orders.get("trackDir")).mkdir(parents=True, exist_ok=True)
    for key, value in track_dir.items():
        tdir = orders.get("trackDir") + value
        Path(tdir).mkdir(parents=False, exist_ok=True)
    # Old way to check file exists
    if os.path.isfile(orders.get("tokenFile")):
        tokens = json.load(open(orders.get("tokenFile")))
    else:
        # Construct an expired token, to force immediate refresh (hence tokens dont need to be valid)
        tokens = {
            "token_type": "Bearer",
            "access_token": "987654321",
            "expires_at": 1690747915,
            "expires_in": 0,
            "refresh_token": "123456789",
        }
    if os.path.isfile(orders.get("idFile")):
        stravaData = json.load(open(orders.get("idFile")))
    else:
        stravaData = {"last_read": 10101}


def refreshTokens(person):
    athlete = person.upper()
    if "STRAVA_" + athlete + "_ID" not in os.environ:
        return {}
    body = {
        "client_id": os.environ.get("STRAVA_" + athlete + "_ID"),
        "client_secret": os.environ.get("STRAVA_" + athlete + "_SECRET"),
        "grant_type": "refresh_token",
        "refresh_token": os.environ.get("STRAVA_" + athlete + "_REFTOKEN"),
    }
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    resp = requests.post(
        "https://www.strava.com/oauth/token", data=json.dumps(body), headers=headers
    )
    new_tokens = json.loads(resp.text)
    return new_tokens


# -------------------------------------------------------------------------------
def getAccessToken(quietly, page):
    global orders
    global tokens
    if tokens.get("expires_at") < (time.time()):
        # REFRESH TOKENS
        print(" Token Expired. Requesting new Token for {}".format(orders.get("athlete")))
        tokenResponse = refreshTokens(orders.get("athlete"))
        if "access_token" not in tokenResponse:
            print("ERROR: Could not refresh tokens")
            return None
        print(" New Token: {}".format(tokenResponse["access_token"]))
        json.dump(tokenResponse, open(orders.get("tokenFile"), mode="w"))
        tokens = tokenResponse
        return tokens["access_token"]
    else:
        if not quietly:
            print(" Page {}: Using Token: {}".format(page, tokens["access_token"]))
        return tokens["access_token"]


# -------------------------------------------------------------------------------
def fetch_activities(page: int) -> tuple[dict[str, Any], int]:
    global orders
    accessToken = getAccessToken(False, page)
    if not accessToken:
        print("ERROR: No access token - cant request activities")
        return {}, 999
    headers = {"accept": "application/json", "authorization": "Bearer " + accessToken}
    per_page = orders.get("pagesize")
    # Always returns activities in reverse time order from today, unless give explicit date to read back from
    if "before" in orders:
        epoch = datetime.datetime.strptime(orders["before"], "%Y%m%d").strftime("%s")
        before_string = "&before=" + epoch
    else:
        before_string = ""
    resp = requests.get(
        "https://www.strava.com/api/v3/athlete/activities?page="
        + str(page)
        + "&per_page="
        + str(per_page)
        + before_string,
        headers=headers,
    )
    if resp.status_code == 200:
        fetched = json.loads(resp.text)
        errno = 0
    else:
        fetched = {}
        errno = resp.status_code
        print(
            " WARNING: http response {} with string ({})".format(
                resp.status_code, resp.reason
            )
        )
    return fetched, errno


# -------------------------------------------------------------------------------
def fetchActivityStream(actid):
    accessToken = getAccessToken(True, 0)
    if not accessToken:
        print("ERROR: No access token - cant request activity stream")
        return {}
    headers = {"accept": "application/json", "authorization": "Bearer " + accessToken}
    keys = "time,latlng,altitude"
    resp = requests.get(
        "https://www.strava.com/api/v3/activities/"
        + str(actid)
        + "/streams?keys="
        + keys
        + "&key_by_type=True",
        headers=headers,
    )
    if resp.status_code == 200:
        fetched = json.loads(resp.text)
        errno = 0
    else:
        fetched = {}
        errno = resp.status_code
        print(
            " WARNING: http response {} with string ({})".format(
                resp.status_code, resp.reason
            )
        )
    return fetched, errno


# -------------------------------------------------------------------------------
def loadActivitiesList():
    global orders
    global stravaData
    init()
    if "specdate" in orders:
        lastSeenID = 1
        highestSeenID = 2
    else:
        lastSeenID = int(stravaData.get("last_read"))
        print(
            " Last Strava ID uploaded (to stop at when found again) {}".format(
                str(lastSeenID)
            )
        )
        highestSeenID = lastSeenID
    activitiesToAdd = []
    page = 1
    finished = False
    while not finished:
        batch, errno = fetch_activities(page)
        if errno != 0:
            break
        if len(batch) <= 0:
            break
        for b in batch:
            if b["id"] > lastSeenID:
                if b["id"] > highestSeenID:
                    highestSeenID = b["id"]
                activitiesToAdd.insert(0, b)
            elif b["id"] == lastSeenID:
                finished = True
                print(" Found lastSeenID ({}) so stopping search".format(lastSeenID))
                break
            elif (
                b["id"] < lastSeenID
            ):  # Sanity check: cant get here unless "below" makes loop start too low (or overflow pages)
                if "before" in orders:
                    print(
                        "WARNING: before ({}) activity ({}) must be later than lastSeenID ({})".format(
                            orders["before"], b["id"], lastSeenID
                        )
                    )
                break
        # Spamming check: dont read more than 3 pages (unless explicitly allow)
        page = page + 1
        if page > int(orders["numpages"]):
            print(
                "INFO: Maximum number ({}) of pages reached".format(orders["numpages"])
            )
            break
    print(" Activities since last upload [{}]:".format(len(activitiesToAdd)))
    if orders["verbose"] == True:
        for i in activitiesToAdd:
            print(" - {} : {} : {}".format(str(i["id"]), str(i["type"]), str(i["name"])))
    stravaData["last_read"] = highestSeenID
    if orders["specdate"] == False:
        json.dump(stravaData, open(orders.get("idFile"), "w"))
    return activitiesToAdd


# -------------------------------------------------------------------------------
def createGPXFile(activity_name, activity_id, activity_start, activity_sport, stream):
    gpx = gpxpy.gpx.GPX()
    dt = datetime.datetime.fromisoformat(activity_start.replace("Z", "+00:00"))
    gpx.time = dt
    gpx.name = str(activity_name)
    gpx.keywords = str(activity_id)
    # Create track in GPX:
    gpx_track = gpxpy.gpx.GPXTrack()
    gpx_track.name = activity_name
    gpx_track.comment = str(dt.date())
    gpx_track.type = activity_sport
    ##gpx_track.description = '1.0'
    gpx.tracks.append(gpx_track)
    # Create segment in GPX track:
    gpx_segment = gpxpy.gpx.GPXTrackSegment()
    gpx_track.segments.append(gpx_segment)
    # Create points:
    for i, p in enumerate(stream["latlng"]["data"]):
        trkpt_dt = dt + datetime.timedelta(seconds=int(stream["time"]["data"][i]))
        gpx_segment.points.append(
            gpxpy.gpx.GPXTrackPoint(
                p[0], p[1], elevation=stream["altitude"]["data"][i], time=trkpt_dt
            )
        )
    return gpx


# -------------------------------------------------------------------------------
def construct_filenames(i):
    global orders
    # Construct a sanitized activity/file name from the strava id and activity name
    #  with dashes and spaces converted to underscores
    #  and punctuation marks removed
    s = str(i["id"]) + "." + str(i["name"])
    s = re.sub(r"-", " ", s)
    s = re.sub(r"/", " ", s)
    s = re.sub(r"\s+", "_", s)
    remove = string.punctuation
    remove = remove.replace("_", "")  # don't remove underscores
    remove = remove.replace(".", "")  # don't remove dots
    activity_name = s.translate(str.maketrans("", "", remove))
    activity_name = re.sub(
        r"_$", "", activity_name
    )  # dont leave an underscore as last letter
    # Prepare output file location
    if i["commute"]:
        t = "commute"
    elif i["type"] in track_dir:
        t = track_dir[i["type"]]
    else:
        t = "wip"
    outfile = str(orders.get("trackDir")) + t + "/" + activity_name + ".gpx"
    return activity_name, outfile


# -------------------------------------------------------------------------------
if __name__ == "__main__":

    args = parse_command_line()
    track_dir = dict(
        Ride="bike",  # Ride/Ride and Ride/MountainBikeRide in bike
        Hike="hike",  # Hike/Hike in hike
        Walk="hike",  # Walk/Walk in hike
        AlpineSki="ski",  # AlpineSki/AlpineSki in ski
        BackcountrySki="skiclimb",  # BackcountrySki/BackcountrySki in skiclimb
        Run="run",  # Run/Run in run
        Commute="commute",  # Ride/Commute in commute
        VirtualRun="run",  # VirtualRun/VirtualRun in run
        Swim="swim",  # Swim/Swim in swim
        Velomobile="vehicle",  # Strava has no vehicles so labelled velomobile
        Sail="vehicle",  # Boats of various types!
    )
    # Download activity list
    activities = loadActivitiesList()
    if orders["zero"] == True:
        # Write out the list of activities to disk
        lfile = str(orders.get("listfile"))
        with open(lfile, "w") as f:
            print("INFO: writing list file {}".format(lfile))
            json.dump(activities, f)
            # f.write(str(activities))
        exit(0)
    # Filter activity list: by default include commutes
    if orders["commute"] == False:
        filteredActivities = list(filter(lambda obj: not obj["commute"], activities))
        print(" Non-commutes retained [{}]:".format(len(filteredActivities)))
    elif orders["work"] == True:
        filteredActivities = list(filter(lambda obj: obj["commute"], activities))
        print(" Only commutes retained [{}]:".format(len(filteredActivities)))
    else:
        filteredActivities = activities
        # filteredActivities = list(filter(lambda obj: obj['type'] == "Hike", activities))
        print(" All retained [{}]:".format(len(filteredActivities)))
    # Download activities
    for i in filteredActivities:
        activity_name, outfile = construct_filenames(i)
        if orders["light"]:
            # Only if file doesnt exist at all then download
            if os.path.exists(outfile):
                if orders["verbose"] == True:
                    print("INFO: Skipping existing {}".format(i["name"]))
                continue
        if orders["verbose"] == True:
            print(
                " - ID: {}   Date: {}   Type {}/{} ({})   Name: {}".format(
                    i["id"],
                    i["start_date"],
                    i["type"],
                    i["sport_type"],
                    i["commute"],
                    i["name"],
                )
            )
        if not i["external_id"]:
            print("WARN: no activity file to download {}".format(i["name"]))
            continue
        if i["map"]["summary_polyline"] == "":
            print("WARN: no activity map in download {}".format(i["name"]))
            continue
        stream, errno = fetchActivityStream(i["id"])
        if errno == 0:
            if "latlng" in stream:
                if not stream["latlng"]["resolution"] == "high":
                    print(
                        "WARNING: Stream truncated ({}) from {} to {}".format(
                            stream["latlng"]["resolution"],
                            stream["latlng"]["original_size"],
                            len(stream["latlng"]["data"]),
                        )
                    )
                # Create a GPX file in memory from the activity streams
                gpx = createGPXFile(
                    activity_name, i["id"], i["start_date"], i["sport_type"], stream
                )

                # Write out the GPX file to disk
                with open(outfile, "w") as f:
                    print("INFO: writing file {}".format(outfile))
                    f.write(gpx.to_xml())
            else:
                print("INFO: stream was empty for {}".format(i["name"]))
        else:
            if errno == 429:
                print(
                    "ERROR: {} downloading activity {} aborting".format(errno, i["id"])
                )
                exit(1)
            else:
                print(
                    "WARNING: {} downloading activity {} skipping".format(
                        errno, i["id"]
                    )
                )

#####################################################################################
