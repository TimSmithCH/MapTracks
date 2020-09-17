#!/bin/bash
set -e   # Exit with nonzero exit code if anything fails
#set -x   # Debug mode to echo commands

# Update MapBox tileset?
if ! git diff --quiet --exit-code tracks/1_display; then
  tupdate=1
else
  tupdate=0
fi

# Push the modified GeoJSON files
git add tracks/1_display
git add tracks/2_geojson
git status -s
MESS="${commit_mess} (GeoJSONs)"
#git commit -m "$MESS"
#git push

#########################
#if [[ -z $(git status --untracked-files=no --porcelain tracks/1_display) ]]; then
exit $tupdate
