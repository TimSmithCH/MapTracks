#!/bin/bash
set -e   # Exit with nonzero exit code if anything fails
#set -x   # Debug mode to echo commands

git status
git add tracks/1_display
git add tracks/2_geojson
git status
MESS="${commit_mess} (GeoJSONs)"
#MESS="Generate geoJSONs for: ${GITHUB_SHA}"
echo "$MESS"
git commit -m "$MESS"
git push
