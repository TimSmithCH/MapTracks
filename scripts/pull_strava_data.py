#!/usr/bin/python
# -*- coding: utf-8 -*-
#-------------------------------------------------------------------------------
#
# DESCRIPTION
#    Download Strava data to create GPX files per activity. Use the Strava API
#    to construct an activity list since last download, then for each activity
#    download Strava's actvity streams and reconstruct a GPX file from the data
#
# EXAMPLES
#    python pull_strava_data.py -o "tracks/3_gpx/" -p 20
#    python pull_strava_data.py -c True -o "tracks/3_gpx/" -p 100 -b 20220201
#
# IMPLEMENTATION
#    Author       Tim Smith
#    Copyright    Copyright (c) Tim Smith
#    Licence      GNU General Public License
#
#-------------------------------------------------------------------------------
import requests
import json
import time
import datetime
import os
import re
import gpxpy
import string
from argparse import ArgumentParser

#-------------------------------------------------------------------------------
# Initialise command line options and their defaults
def parseCommandLine():
    global orders
    # If run in Github ACTION then set defaults without parsing!
    if os.getenv("GITHUB_ACTIONS") == "true":
        orders = {
                "tokenFile": "token.json",
                "trackDir": "tracks/3_gpx/",
                "idFile": "www/features/LastStravaIDRead.json",
                "pagesize": 40,
                "numpages": 3,
                "commute": True,
                "light": False,
                "zero": False
        }
    # Parse command line arguments if not run in a Github ACTION
    else:
        # Instantiate the parser
        parser = ArgumentParser(description="Download latest activities via Strava API.")
        # Set up the argument defaults
        defaults = dict(outdir="./",iddir="./",tokendir="./",pagesize=10,numpages=3,commute=True,light=False,zero=False)
        parser.set_defaults(**defaults)
        # Parse the command line
        parser.add_argument('-t', '--tokendir', help='Directory to store generated access token file')
        parser.add_argument('-o', '--outdir',   help='Directory to store downloaded Strava activity files')
        parser.add_argument('-i', '--iddir',    help='Directory to store Strava ID file')
        parser.add_argument('-b', '--before',   help='Upper date bound to search back from')
        parser.add_argument('-s', '--specdate', help='Specific date to search for')
        parser.add_argument('-p', '--pagesize', help='Number of activities per page for Strava API download')
        parser.add_argument('-n', '--numpages', help='Number of pages of activities for Strava API download')
        parser.add_argument('-c', '--commute',  action='store_false', help='Ignore commutes')
        parser.add_argument('-l', '--light',    action='store_true', help='Light mode: Dont download data if file already exists')
        parser.add_argument('-z', '--zero',     action='store_true', help='Zero downloads: only store activity list')
        args = parser.parse_args()
        orders = {
                "tokenFile": args.tokendir+"token.json",
                "trackDir": args.outdir,
                "idFile": args.iddir+"LastStravaIDRead.json",
                "listfile": "ActivitiesList.json"
        }
        if args.before:
            orders["before"] = args.before
        if args.pagesize:
            orders["pagesize"] = args.pagesize
        if args.numpages:
            orders["numpages"] = args.numpages
        if int(args.numpages) * int(args.pagesize) > 200 :
            print("WARNING: Dont spam Strava API: {} pages x {} pagesize too large setting to 3x20".format(args.numpages,args.pagesize))
            #orders["pagesize"] = 20
            #orders["numpages"] = 3
        if args.specdate :
            orders["pagesize"] = 7
            orders["numpages"] = 1
            orders["specdate"] = args.specdate
            orders["before"] = str(int(args.specdate)+1)
        orders["commute"] = args.commute
        orders["light"] = args.light
        orders["zero"] = args.zero

#-------------------------------------------------------------------------------
def init():
    global orders
    global tokens
    global stravaData
    if os.path.isfile(orders.get("tokenFile")):
        tokens = json.load(open(orders.get("tokenFile")))
    else:
        # Construct an expired token, to force immediate refresh (hence tokens dont need to be valid)
        tokens = {
            "token_type": "Bearer",
            "access_token": "987654321",
            "expires_at": 1690747915,
            "expires_in": 0,
            "refresh_token": "123456789"
        }
    stravaData = json.load(open(orders.get('idFile')))

def refreshTokens():
    body = {
        "client_id": os.environ.get('CONF_CLIENT_ID'),
        "client_secret": os.environ.get('CONF_CLIENT_SECRET'),
        "grant_type": "refresh_token",
        "refresh_token": os.environ.get('CONF_REFRESH_TOKEN')
    }
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    resp = requests.post("https://www.strava.com/oauth/token", data=json.dumps(body), headers=headers)
    new_tokens = json.loads(resp.text)
    return new_tokens

#-------------------------------------------------------------------------------
def getAccessToken(quietly,page):
    global orders
    global tokens
    if tokens.get("expires_at") < (time.time()):
        # REFRESH TOKENS
        print(" Token Expired. Requesting new Token.")
        tokenResponse = refreshTokens()
        if("access_token" not in tokenResponse):
            print("ERROR: Could not refresh tokens")
            return None
        print(" New Token: {}".format(tokenResponse["access_token"]))
        json.dump(tokenResponse, open(orders.get("tokenFile"), mode="w"))
        tokens = tokenResponse
        return tokens["access_token"]
    else:
        if not quietly:
            print(" Page {}: Using Token: {}".format(page,tokens["access_token"]))
        return tokens["access_token"]

#-------------------------------------------------------------------------------
def fetchActivities(page):
    global orders
    accessToken = getAccessToken(False,page)
    if(not accessToken):
        print("ERROR: No access token - cant request activities")
        return {}
    headers = {
        'accept': 'application/json',
        'authorization': "Bearer " + accessToken
    }
    per_page = orders.get("pagesize")
    # Always returns activities in reverse time order from today, unless give explicit date to read back from
    if "before" in orders:
        epoch = datetime.datetime.strptime(orders["before"],'%Y%m%d').strftime('%s')
        before_string = "&before="+epoch
    else:
        before_string = ""
    resp = requests.get("https://www.strava.com/api/v3/athlete/activities?page="+str(page)+"&per_page="+str(per_page)+before_string, headers=headers)
    if resp.status_code == 200 :
        fetched = json.loads(resp.text)
        errno = 0
    else :
        fetched = {}
        errno = resp.status_code
        print(" WARNING: http response {} with string ({})".format(resp.status_code,resp.reason))
    return fetched, errno

#-------------------------------------------------------------------------------
def fetchActivityStream(actid):
    accessToken = getAccessToken(True,0)
    if(not accessToken):
        print("ERROR: No access token - cant request activity stream")
        return {}
    headers = {
        'accept': 'application/json',
        'authorization': "Bearer " + accessToken
    }
    keys = "time,latlng,altitude"
    resp = requests.get("https://www.strava.com/api/v3/activities/"+str(actid)+"/streams?keys="+keys+"&key_by_type=True", headers=headers)
    if resp.status_code == 200 :
        fetched = json.loads(resp.text)
        errno = 0
    else :
        fetched = {}
        errno = resp.status_code
        print(" WARNING: http response {} with string ({})".format(resp.status_code,resp.reason))
    return fetched, errno

#-------------------------------------------------------------------------------
def loadActivitiesList():
    global orders
    global stravaData
    init()
    if "specdate" in orders :
        lastSeenID = 1
        highestSeenID = 2
    else :
        lastSeenID = int(stravaData.get("last_read"))
        print(" Last Strava ID uploaded (to stop at when found again) {}".format(str(lastSeenID)))
        highestSeenID = lastSeenID
    activitiesToAdd = []
    page = 1
    finished = False
    while not finished:
        batch, errno = fetchActivities(page)
        if errno != 0 :
            break
        if len(batch) <= 0 :
            break
        for b in batch :
            if b["id"] > lastSeenID :
                if b["id"] > highestSeenID :
                    highestSeenID = b["id"]
                activitiesToAdd.insert(0,b)
            elif b["id"] == lastSeenID :
                finished = True
                print(" Found lastSeenID ({}) so stopping search".format(lastSeenID))
                break
            elif b["id"] < lastSeenID :   # Sanity check: cant get here unless "below" makes loop start too low (or overflow pages)
                if "before" in orders :
                    print("WARNING: before ({}) activity ({}) must be later than lastSeenID ({})".format(orders["before"],b["id"],lastSeenID))
                break
        # Spamming check: dont read more than 3 pages (unless explicitly allow)
        page = page + 1
        if page > int(orders["numpages"]) :
            print("INFO: Maximum number ({}) of pages reached".format(orders["numpages"]))
            break
    print(" Activities since last upload:")
    for i in activitiesToAdd :
        print(" - {} : {} : {}".format(str(i["id"]),str(i["type"]),str(i["name"])))
    stravaData["last_read"] = highestSeenID
    json.dump(stravaData, open(orders.get('idFile'), "w"))
    return activitiesToAdd

#-------------------------------------------------------------------------------
def createGPXFile(activity_name,activity_id,activity_start,activity_sport,stream):
    gpx = gpxpy.gpx.GPX()
    dt = datetime.datetime.fromisoformat(activity_start.replace('Z', '+00:00'))
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
    for i,p in enumerate(stream['latlng']['data']):
        trkpt_dt = dt + datetime.timedelta(seconds=int(stream['time']['data'][i]))
        gpx_segment.points.append(gpxpy.gpx.GPXTrackPoint(p[0], p[1], elevation=stream['altitude']['data'][i], time=trkpt_dt))
    return gpx

#-------------------------------------------------------------------------------
def construct_filenames(i):
    global orders
    # Construct a sanitized activity/file name from the strava id and activity name
    #  with dashes and spaces converted to underscores
    #  and punctuation marks removed
    s = str(i["id"])+"."+str(i["name"])
    s = re.sub(r"-", ' ', s)
    s = re.sub(r"/", ' ', s)
    s = re.sub(r"\s+", '_', s)
    remove = string.punctuation
    remove = remove.replace("_", "") # don't remove underscores
    remove = remove.replace(".", "") # don't remove dots
    activity_name = s.translate(str.maketrans('', '', remove))
    activity_name = re.sub(r"_$", '', activity_name) # dont leave an underscore as last letter
    # Prepare output file location
    if i['commute']:
        t = "commute"
    elif i["type"] in track_dir:
        t = track_dir[i["type"]]
    else:
        t = "wip"
    # Default of localdir unless ordered otherwise on the command line
    if str(orders.get("trackDir")) == "./":
        outfile = activity_name+".gpx"
    else:
        outfile = str(orders.get("trackDir"))+t+"/"+activity_name+".gpx"
    return activity_name,outfile

#-------------------------------------------------------------------------------
if __name__ == "__main__":

    args = parseCommandLine()
    track_dir = dict(Ride="bike",     # Ride/Ride and Ride/MountainBikeRide in bike
                     Hike="hike",     # Hike/Hike in hike
                     Walk="hike",     # Walk/Walk in hike
                     AlpineSki="ski", # AlpineSki/AlpineSki in ski
                     BackcountrySki="skiclimb", # BackcountrySki/BackcountrySki in skiclimb
                     Run="run",       # Run/Run in run
                     VirtualRun="run",# VirtualRun/VirtualRun in run
                     Swim="swim",     # Swim/Swim in swim
                     Velomobile="vehicle", # Strava has no vehicles so labelled velomobile
                     Sail="vehicle")  # Boats of various types!
    activities = loadActivitiesList()
    if orders["zero"] == True :
        # Write out the GPX file to disk
        lfile = str(orders.get("listfile"))
        with open(lfile, "w") as f:
            print("INFO: writing list file {}".format(lfile))
            json.dump(activities, f)
            #f.write(str(activities))
        exit(0)
    # Selectively download activities: by default include commutes
    if orders["commute"] == False :
        filteredActivities = list(filter(lambda obj: not obj['commute'], activities))
        print(" Non-commutes retained:")
    else:
        filteredActivities = activities
        #filteredActivities = list(filter(lambda obj: obj['type'] == "Hike", activities))
        print(" All retained:")
    # Download activities
    for i in filteredActivities:
        activity_name,outfile = construct_filenames(i)
        if orders["light"]:
            # Only if file doesnt exist at all then download
            if os.path.exists(outfile):
                print("INFO: Skipping existing {}".format(i["name"]))
                continue
        print(" - ID: {}   Type {}/{} ({})   Name: {}".format(i["id"],i["type"],i["sport_type"],i["commute"],i["name"],i["start_date"],i["name"]))
        stream, errno = fetchActivityStream(i["id"])
        if errno == 0 :
            if "latlng" in stream :
                if not stream['latlng']['resolution'] == "high":
                    print("WARNING: Stream truncated ({}) from {} to {}".format(stream['latlng']['resolution'],stream['latlng']['original_size'],len(stream['latlng']['data'])))
                # Create a GPX file in memory from the activity streams
                gpx = createGPXFile(activity_name,i["id"],i["start_date"],i["sport_type"],stream)

                # Write out the GPX file to disk
                with open(outfile, "w") as f:
                    print("INFO: writing file {}".format(outfile))
                    f.write(gpx.to_xml())
            else :
                print("INFO: stream was empty for {}".format(i["name"]))
        else :
            if errno == 429 :
                print("ERROR: {} downloading activity {} aborting".format(errno,i["id"]))
                exit(1)
            else :
                print("WARNING: {} downloading activity {} skipping".format(errno,i["id"]))

#####################################################################################
