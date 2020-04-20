#!/bin/bash
set -e   # Exit with nonzero exit code if anything fails
set -x   # Debug mode to echo commands

tilesets list-sources --token `cat tileset_api` timsmithch
#ls -lR
rm -r node_modules

git status
git add tracks/geojson
git rm -r tracks/gpx
git commit -m "Uploaded more GeoJSON files"
