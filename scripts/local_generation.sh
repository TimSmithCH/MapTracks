#!/bin/bash
set -e   # Exit with nonzero exit code if anything fails
#set -x   # Debug mode to echo commands

python scripts/geojson_sync_check.py -f -r -a alison -t all
python scripts/geojson_sync_check.py -f -r -a tim -t all
python scripts/geojson_sync_check.py -f -r -a tim -t commute

python scripts/geojsons_merge.py -o tracks/tim/1_display/bike_tracks.geojson tracks/tim/2_geojson/bike
python scripts/geojsons_merge.py -o tracks/tim/1_display/hike_tracks.geojson tracks/tim/2_geojson/hike
python scripts/geojsons_merge.py -o tracks/tim/1_display/commute_tracks.geojson tracks/tim/2_geojson/commute

python scripts/geojson_validate.py -f tracks/tim/1_display/
python scripts/geojson_validate.py -f tracks/alison/1_display/

rsync -avu "tracks/tim/1_display/" "www/tracks/tim/1_display/"
rsync -avu "tracks/alison/1_display/" "www/tracks/alison/1_display/"
