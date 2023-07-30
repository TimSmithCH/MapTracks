#!/usr/bin/python
import requests
import json
import time
import os

activitiesFile = "features/LastStravaIDRead.json"

def init():
    global tokens
    global stravaData
    # Construct an expired token, so the access and refresh tokens wont be used so arent valid
    tokens = {
        "token_type": "Bearer",
        "access_token": "4444444444444444444444444444444444444444",
        "expires_at": 1690747915,
        "expires_in": 0,
        "refresh_token": "6666666666666666666666666666666666666666"
    stravaData = json.load(open(config["activitiesFile"]))

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

def getAccessToken():
    global tokens
    if tokens.get("expires_at") < (time.time()):
        # REFRESH TOKENS
        print("Token Expired. Requesting new Token.")
        tokenResponse = refreshTokens()
        if("access_token" not in tokenResponse):
            print("ERROR: Could not refresh tokens")
            return None
        print("New Token: " + tokenResponse["access_token"])
        tokens = tokenResponse
        return tokens["access_token"]
    else:
        print("Using Token: " + tokens["access_token"])
        return tokens["access_token"]

def fetchActivities(page, per_page=100):
    accessToken = getAccessToken()
    headers = {
        'accept': 'application/json',
        'authorization': "Bearer " + accessToken
    }
    resp = requests.get("https://www.strava.com/api/v3/athlete/activities?page="+str(page)+"&per_page="+str(per_page), headers=headers)
    fetched = json.loads(resp.text)
    return fetched

def updateLocalActivities():
    init()
    lastLocalID = stravaData.get("last_read")
    activitiesToAdd = []
    page = 1
    finished = False
    while not finished:
        batch = fetchActivities(page)
        if len(batch) <= 0:
            break
        for b in batch:
            if b["id"] == lastLocalID:
                finished = True
                break
            else:
                activitiesToAdd.insert(0,b)
        page = page + 1
        if page > 2:
            break
    print("ADDING:")
    for i in activitiesToAdd:
        print(" -"+str(i["id"])+" : "+str(i["type"])+" : "+str(i["name"]))
    return activitiesToAdd


if __name__ == "__main__":

    activities = updateLocalActivities()
    currentSport = list(filter(lambda obj: obj['type'] == "Ride", activities))
    dates = list(map(lambda obj: obj['start_date'], currentSport))
    dates_conv = dt.date2num(dates)
