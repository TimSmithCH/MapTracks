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
printf "\n+++ Upload New Sources +++\n"
MODIFIED="false"
for type in "${TYPES[@]}"
do
  fileSUMM=tracks/1_display/${type}_tracks.geojson
  timeNOW="$(git log --pretty=format:%cd -n 1 --date=format:%s)"
  echo "Processing $fileSUMM"
  if [[ "$FORCE" == "true" ]] ; then
    timeLAST=$timeNOW
  else
    timeLAST="$(git log --pretty=format:%cd -n 1 --date=format:%s -- $fileSUMM)"
  fi
  timeEL=$(($timeNOW-$timeLAST))
  if [[ "$timeEL" -le "$FRESHNESS" ]]; then
    printf "  Generating $type tileset\n"
    MODIFIED="true"
    #tilesets delete-source --token $TOKEN --force timsmithch ${type}_tracks
    #tilesets add-source --token $TOKEN timsmithch ${type}_tracks tracks/1_display/${type}_tracks.geojson
    tilesets upload-source --token $TOKEN timsmithch ${type}_tracks tracks/1_display/${type}_tracks.geojson --replace
  else
    printf "  .\n"
  fi
done
printf "\n+++ Full Source List +++\n"
tilesets list-sources --token $TOKEN timsmithch

# Generate the new tileset
if [[ "$MODIFIED" == "true" ]] ; then
  # Create the initial tileset, only necessary first time, afterwards update is all
  #tilesets create timsmithch.all_tracks --token $TOKEN --recipe scripts/all_tracks_recipe.json --name "All track types"
  # Update the recipe to generate the tilesets, only if it changes
  #tilesets update-recipe --token $TOKEN timsmithch.all_tracks scripts/all_tracks_recipe.json
  # Launch the tilset generation and wait for completion
  printf "\n+++ Publish +++\n"
  tilesets publish --token $TOKEN timsmithch.all_tracks
  JOBRUN=1
  n=1
  while [[ $JOBRUN -eq 1 ]] && [[ $n -lt 21 ]]; do
    sleep 7
    JOBRUN=$(tilesets status --token $TOKEN timsmithch.all_tracks | jq --exit-status '.status == "processing"' >/dev/null)
    n=$((n+1))
  done
  printf "\n+++ Finished +++\n"
  tilesets status --token $TOKEN --indent 2 timsmithch.all_tracks
fi
