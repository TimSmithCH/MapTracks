#!/bin/bash
set -e   # Exit with nonzero exit code if anything fails
#set -x   # Debug mode to echo commands

TOKEN=$tileset_api

TYPES=( bike hike run ski commute )
FORCE="false"
FRESHNESS=720

# Catch-up with latest changes from first job
git pull --rebase=false

# Update tileset sources when the summary GEOJsons have changed
for type in "${TYPES[@]}"
do
  MODIFIED="false"
  fileSUMM=tracks/1_display/${type}_tracks.geojson
  timeNOW="$(git log --pretty=format:%cd -n 1 --date=format:%s)"
  echo "Processing $fileSUMM"
  if [ $FORCE -eq "true" ] ; then
    timeLAST=$timeNOW
  else
    timeLAST="$(git log --pretty=format:%cd -n 1 --date=format:%s -- $fileSUMM)"
  fi
  timeEL=$(($timeNOW-$timeLAST))
  if [[ "$timeEL" -le "$FRESHNESS" ]]; then
    printf "\n  Generating $type tileset\n"
    MODIFIED="true"
    #tilesets delete-source --token $TOKEN --force timsmithch ${type}_tracks
    #tilesets add-source --token $TOKEN timsmithch ${type}_tracks tracks/1_display/${type}_tracks.geojson
    tilesets upload-source --token $TOKEN timsmithch ${type}_tracks tracks/1_display/${type}_tracks.geojson --replace
  else
    printf "\n  ."
  fi
done
printf "\n+++ Sources +++\n"
tilesets list-sources --token $TOKEN timsmithch

# Generate the new tileset
if [ $MODIFIED -eq "true" ; then
  # Create the initial tileset, only necessary first time, afterwards update is all
  #tilesets create timsmithch.all_tracks --token $TOKEN --recipe scripts/all_tracks_recipe.json --name "All track types"
  # Update the recipe to generate the tilesets, only if it changes
  tilesets update-recipe --token $TOKEN timsmithch.all_tracks scripts/all_tracks_recipe.json
  # Launch the tilset generation and wait for completion
  tilesets publish --token $TOKEN timsmithch.all_tracks
  JOBRUN=true
  n=1
  while $JOBRUN && [ $n -lt 21 ]; do
    sleep 7
    JOBRUN=$(tilesets status --token $TOKEN timsmithch.all_tracks | jq '.status == "processing"')
    n=$(( n+1 ))
  done
  tilesets status --token $TOKEN --indent 2 timsmithch.all_tracks
fi
