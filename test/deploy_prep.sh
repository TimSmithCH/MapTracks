#!/bin/bash
set -e   # Exit with nonzero exit code if anything fails
set -x   # Debug mode to echo commands

#ls -lR tracks/
rm -r test
rm -r node_modules
#rm tracks/geojson/hike/*simple*
#rm tracks/geojson/bike/*simple*
#rm tracks/geojson/ski/*simple*

git status
git add tracks/geojson
git rm -r test
git commit -m "Converted more GeoJson files"
