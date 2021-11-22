#!/bin/bash
#set -e   # Exit with nonzero exit code if anything fails
#set -x   # Debug mode to echo commands

# Update MapBox tileset?
if ! git diff --quiet --exit-code tracks/1_display; then
  echo "generate"
  echo "=== Signalling to generate TileSet ===" 1>&2
  ##echo "generate"
  #echo "=== NOT Signalling to generate TileSet ===" 1>&2
else
  echo "stop"
fi

# Push the modified GeoJSON files
git add tracks/1_display 1>&2
git add tracks/2_geojson 1>&2
git status -s 1>&2
MESS="${commit_mess} (GeoJSONs)"
git commit -m "$MESS" 1>&2
git push 1>&2
