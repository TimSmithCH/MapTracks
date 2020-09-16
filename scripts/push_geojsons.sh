#!/bin/bash
set -e   # Exit with nonzero exit code if anything fails
set -x   # Debug mode to echo commands

git status -s
if ! git diff --quiet --exit-code tracks/1_display; then
  echo "Must update MapBox tileset"
  tile_run="Yes"
else
  echo "Tiles are good"
  tile_run="No"
fi

git add tracks/1_display
git add tracks/2_geojson
git status -s

MESS="${commit_mess} (GeoJSONs)"
echo "$MESS"
git commit -m "$MESS"
git push

#########################
#if [[ -z $(git status --untracked-files=no --porcelain tracks/1_display) ]]; then
