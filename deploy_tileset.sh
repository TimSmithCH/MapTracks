#!/bin/bash
set -e   # Exit with nonzero exit code if anything fails
set -x   # Debug mode to echo commands

TOKEN=$(<tileset_api)

# Update the tileset input sources with the files just generated
tilesets delete-source --token $TOKEN --force timsmithch bike_tracks
tilesets delete-source --token $TOKEN --force timsmithch hike_tracks
tilesets delete-source --token $TOKEN --force timsmithch run_tracks
tilesets delete-source --token $TOKEN --force timsmithch ski_tracks
tilesets add-source --token $TOKEN timsmithch bike_tracks tracks/geojson/bike_tracks.geojson
tilesets add-source --token $TOKEN timsmithch hike_tracks tracks/geojson/hike_tracks.geojson
tilesets add-source --token $TOKEN timsmithch run_tracks tracks/geojson/run_tracks.geojson
tilesets add-source --token $TOKEN timsmithch ski_tracks tracks/geojson/ski_tracks.geojson

# Launch the tilset generation and wait for completion
#tilesets list-sources --token $TOKEN timsmithch
tilesets update-recipe --token $TOKEN timsmithch.all_tracks ./all_tracks_recipe.json
tilesets publish --token $TOKEN timsmithch.all_tracks
JOBRUN=true
n=1
while $JOBRUN && [ $n -lt 21 ]; do
  sleep 7
  JOBRUN=$(tilesets status --token $TOKEN timsmithch.all_tracks | jq '.status == "processing"')
  n=$(( n+1 ))
done
tilesets status --token $TOKEN --indent 2 timsmithch.all_tracks

# Clean-up, dont publish the key files
rm tileset_ap*
