#!/bin/bash
set -e   # Exit with nonzero exit code if anything fails
#set -x   # Debug mode to echo commands

git status
git add tracks/2_geojson
git add tracks/1_display
git status
echo "$commit_mess"
MESS="GeoJsons for: ${commit_mess}"
echo "$MESS"
#git commit -m "Uploaded more GeoJSON files"
#git push
