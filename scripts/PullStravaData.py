#!/usr/bin/python
import requests
import json
import time
import os


def init():
    global tokens
    global credentials
    global localActivities
    global config
    config = json.load(open("config.json"))
    tokens = json.load(open(config["tokenFile"]))
    credentials = json.load(open(config["credentialsFile"]))
    localActivities =  []
    if os.path.isfile(config["activitiesFile"]):
        localActivities = json.load(open(config["activitiesFile"]))

def refreshTokens():
    body = {
        "client_id": credentials.get("client_id"),
        "client_secret": credentials.get("client_secret"),
        "grant_type": "refresh_token",
        "refresh_token": tokens.get("refresh_token")
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
        json.dump(tokenResponse, open(config["tokenFile"], mode="w"))
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
    lastLocalID = 0
    if len(localActivities) > 0:
        lastLocalID = localActivities[0]["id"]
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
        print(" -"+str(i["id"]))
        localActivities.insert(0, i)

    json.dump(localActivities, open(config["activitiesFile"], "w"))
    print("DONE")
    return localActivities

def removeLocalActivities(num):
    init()
    for i in range(num):
        rem = localActivities.pop(0)
        print(rem["id"])
    json.dump(localActivities, open(config["activitiesFile"], "w"))


if __name__ == "__main__":

    activities = fetch.updateLocalActivities()
    #activities = json.load(open(config["activitiesFile"]))
    currentSport = list(filter(lambda obj: obj['type'] == "Ride", activities))
    dates = list(map(lambda obj: obj['start_date'], currentSport))
    dates_conv = dt.date2num(dates)
