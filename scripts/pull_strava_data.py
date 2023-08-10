#!/usr/bin/python
import requests
import json
import time
import datetime
import os
import re
import gpxpy
from argparse import ArgumentParser


def parseCommandLine():
    global orders
    # Parse command line arguments if not run in a Github ACTION
    if os.getenv("GITHUB_ACTIONS") == "true":
        orders = {
                "tokenFile": "token.json",
                "trackDir": "tracks/3_gpx/",
                "idFile": "features/LastStravaIDRead.json"
        }
    else:
        # Instantiate the parser
        parser = ArgumentParser(description="Download latest activities via Strava API.")
        # Set up the argument defaults
        defaults = dict(outdir="./",iddir="./",tokendir="./")
        parser.set_defaults(**defaults)
        # Parse the command line
        parser.add_argument('-t', '--tokendir', dest='tokendir', help='Directory to store generated access token file')
        parser.add_argument('-o', '--outdir', dest='outdir', help='Directory to store downloaded Strava activity files')
        parser.add_argument('-i', '--iddir', dest='iddir', help='Directory to store Strava ID file')
        parser.add_argument('-b', '--before', dest='before', help='Upper date bound to search back from')
        args = parser.parse_args()
        orders = {
                "tokenFile": args.tokendir+"token.json",
                "trackDir": args.outdir,
                "idFile": args.iddir+"LastStravaIDRead.json"
        }
        if args.before:
            orders["before"] = args.before

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

def getAccessToken(quietly):
    global orders
    global tokens
    if tokens.get("expires_at") < (time.time()):
        # REFRESH TOKENS
        print("Token Expired. Requesting new Token.")
        tokenResponse = refreshTokens()
        if("access_token" not in tokenResponse):
            print("ERROR: Could not refresh tokens")
            return None
        print("New Token: " + tokenResponse["access_token"])
        json.dump(tokenResponse, open(orders.get("tokenFile"), mode="w"))
        tokens = tokenResponse
        return tokens["access_token"]
    else:
        if not quietly:
            print("Using Token: " + tokens["access_token"])
        return tokens["access_token"]

def fetchActivities(page, per_page=10):
    global orders
    accessToken = getAccessToken(False)
    if(not accessToken):
        print("ERROR: No access token - cant request activities")
        return {}
    headers = {
        'accept': 'application/json',
        'authorization': "Bearer " + accessToken
    }
    # Always returns activities in reverse time order from today, unless give explicit date to read back from
    if "before" in orders:
        before_string = "&before="+orders["before"]
    else:
        before_string = ""
    resp = requests.get("https://www.strava.com/api/v3/athlete/activities?page="+str(page)+"&per_page="+str(per_page)+before_string, headers=headers)
    fetched = json.loads(resp.text)
    return fetched

def fetchActivityStream(actid):
    accessToken = getAccessToken(True)
    if(not accessToken):
        print("ERROR: No access token - cant request activity stream")
        return {}
    headers = {
        'accept': 'application/json',
        'authorization': "Bearer " + accessToken
    }
    keys = "time,latlng,altitude"
    resp = requests.get("https://www.strava.com/api/v3/activities/"+str(actid)+"/streams?keys="+keys+"&key_by_type=True", headers=headers)
    fetched = json.loads(resp.text)
    return fetched

def loadActivitiesList():
    global orders
    global stravaData
    init()
    if "before" in orders:
        lastSeenID = 1
    else:
        lastSeenID = int(stravaData.get("last_read"))
    print("Last Strava ID uploaded (to find) "+str(lastSeenID))
    activitiesToAdd = []
    page = 1
    finished = False
    highestSeenID = lastSeenID
    while not finished:
        batch = fetchActivities(page)
        if len(batch) <= 0:
            break
        for b in batch:
            if b["id"] > lastSeenID:
                if b["id"] > highestSeenID:
                    highestSeenID = b["id"]
                activitiesToAdd.insert(0,b)
            elif b["id"] == lastSeenID:
                finished = True
                break
        page = page + 1
        if page > 2:
            break
    print("Activities since last upload:")
    for i in activitiesToAdd:
        print(" - "+str(i["id"])+" : "+str(i["type"])+" : "+str(i["name"]))
    stravaData["last_read"] = highestSeenID
    json.dump(stravaData, open(orders.get('idFile'), "w"))
    return activitiesToAdd

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
    gpx_track.description = '1.0'
    gpx.tracks.append(gpx_track)
    # Create segment in GPX track:
    gpx_segment = gpxpy.gpx.GPXTrackSegment()
    gpx_track.segments.append(gpx_segment)
    # Create points:
    for i,p in enumerate(stream['latlng']['data']):
        trkpt_dt = dt + datetime.timedelta(seconds=int(stream['time']['data'][i]))
        gpx_segment.points.append(gpxpy.gpx.GPXTrackPoint(p[0], p[1], elevation=stream['altitude']['data'][i], time=trkpt_dt))
    return gpx



if __name__ == "__main__":

    args = parseCommandLine()
    track_dir = dict(Ride="bike", Hike="hike", Ski="ski", Run="run", Swim="wip")
    activities = loadActivitiesList()
    filteredActivities = list(filter(lambda obj: not obj['commute'], activities))
    #filteredActivities = list(filter(lambda obj: obj['type'] == "Hike", activities))
    print("Non-commutes retained:")
    for i in filteredActivities:
        print("ID: {}   Type {} ({})   Name: {}".format(i["id"],i["type"],i["sport_type"],i["name"],i["start_date"],i["name"]))
        stream = fetchActivityStream(i["id"])
        if "latlng" in stream:
            if not stream['latlng']['resolution'] == "high":
                print("WARNING: Stream truncated ({}) from {} to {}".format(stream['latlng']['resolution'],stream['latlng']['original_size'],len(stream['latlng']['data'])))
            # Construct a sanitized activity/file name from the strava id and the strava activity name with dashes and spaces converted to underscores
            s = str(i["id"])+"."+str(i["name"])
            s = re.sub(r"-", ' ', s)
            activity_name = re.sub(r"\s+", '_', s)
            # Create a GPX file from the activity streams
            gpx = createGPXFile(activity_name,i["id"],i["start_date"],i["sport_type"],stream)
            # Prepare output file location
            if i["type"] in track_dir:
                t = track_dir[i["type"]]
            else:
                t = "wip"
            # Default of localdir unless ordered otherwise on the command line
            if str(orders.get("trackDir")) == "./":
                outfile = activity_name+".gpx"
            else:
                outfile = str(orders.get("trackDir"))+t+"/"+activity_name+".gpx"
            with open(outfile, "w") as f:
                f.write(gpx.to_xml())
        else:
            print("NOTE: stream was empty for {}".format(i["name"]))
