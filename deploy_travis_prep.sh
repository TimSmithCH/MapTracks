#!/bin/bash
set -e   # Exit with nonzero exit code if anything fails
set -x   # Debug mode to echo commands

#ls -lR
rm -r node_modules

git rm -rq tracks/3_gpx
git commit -q -m "Dropped raw GPX files"

git status
git add tracks/2_geojson
git commit -m "Uploaded more GeoJSON files"
