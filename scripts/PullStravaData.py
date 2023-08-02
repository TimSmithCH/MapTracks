#!/usr/bin/python
import requests
import json
import time
import datetime
import os
import re
import gpxpy

historyFile = "features/LastStravaIDRead.json"
tokenFile = "token.json"

def init():
    global tokens
    global stravaData
    if os.path.isfile(tokenFile):
        tokens = json.load(open(tokenFile))
    else:
        # Construct an expired token, to force immediate refresh (hence tokens dont need to be valid)
        tokens = {
            "token_type": "Bearer",
            "access_token": "987654321",
            "expires_at": 1690747915,
            "expires_in": 0,
            "refresh_token": "123456789"
        }
    stravaData = json.load(open(historyFile))

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
    global tokens
    if tokens.get("expires_at") < (time.time()):
        # REFRESH TOKENS
        print("Token Expired. Requesting new Token.")
        tokenResponse = refreshTokens()
        if("access_token" not in tokenResponse):
            print("ERROR: Could not refresh tokens")
            return None
        print("New Token: " + tokenResponse["access_token"])
        json.dump(tokenResponse, open(tokenFile, mode="w"))
        tokens = tokenResponse
        return tokens["access_token"]
    else:
        if not quietly:
            print("Using Token: " + tokens["access_token"])
        return tokens["access_token"]

def fetchActivities(page, per_page=100):
    accessToken = getAccessToken(False)
    if(not accessToken):
        print("ERROR: No access token - cant request activities")
        return {}
    headers = {
        'accept': 'application/json',
        'authorization': "Bearer " + accessToken
    }
    resp = requests.get("https://www.strava.com/api/v3/athlete/activities?page="+str(page)+"&per_page="+str(per_page), headers=headers)
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

def updateActivitiesList():
    init()
    lastSeenID = int(stravaData.get("last_read"))
    print("Last Strava ID uploaded (to find) "+str(lastSeenID))
    activitiesToAdd = []
    page = 1
    finished = False
    while not finished:
        batch = fetchActivities(page)
        if len(batch) <= 0:
            break
        for b in batch:
            if b["id"] == lastSeenID:
                finished = True
                break
            else:
                activitiesToAdd.insert(0,b)
        page = page + 1
        if page > 2:
            break
    print("Activities since last upload:")
    for i in activitiesToAdd:
        print(" - "+str(i["id"])+" : "+str(i["type"])+" : "+str(i["name"]))
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

    activities = updateActivitiesList()
    filteredActivities = list(filter(lambda obj: not obj['commute'], activities))
    #filteredActivities = list(filter(lambda obj: obj['type'] == "Hike", activities))
    print("Non-commutes retained:")
    for i in filteredActivities:
        print("ID: {}   Type {} ({})   Name: {}".format(i["id"],i["type"],i["sport_type"],i["name"],i["start_date"],i["name"]))
        stream = fetchActivityStream(i["id"])
        if "latlng" in stream:
            if not stream['latlng']['resolution'] == "high":
                print("WARN: Stream truncated ({}) from {} to {}".format(stream['latlng']['resolution'],stream['latlng']['original_size'],len(stream['latlng']['data'])))
            s = str(i["id"])+"."+str(i["name"])
            s = re.sub(r"-", ' ', s)
            activity_name = re.sub(r"\s+", '_', s)
            gpx = createGPXFile(activity_name,i["id"],i["start_date"],i["sport_type"],stream)
            #print('Created GPX:', gpx.to_xml())
            outfile = activity_name+".gpx"
            with open(outfile, "w") as f:
                f.write(gpx.to_xml())
        else:
            print("WARN: stream was empty for {}".format(i["name"]))
