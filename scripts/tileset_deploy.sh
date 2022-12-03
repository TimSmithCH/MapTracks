#!/bin/bash
set -e   # Exit with nonzero exit code if anything fails
#set -x   # Debug mode to echo commands

while getopts :t:j:s:f:d: opt
do
    case "${opt}" in
        t ) TOKEN=${OPTARG};;
        j ) JOBLENGTH=${OPTARG};;
        s ) SPORTS=${OPTARG};;
        f ) FORCE=${OPTARG};;
        d ) DRYRUN=${OPTARG};;
        \? ) echo "Usage: cmd [-t token] [-j joblength] [-s sports] [-f force] [-d dryrun]"
    esac
done

# Defaults set if arguements arent passed
if [ -z "$TOKEN" ]; then
  TOKEN=$tileset_api
fi
if [ -z "$SPORTS" ]; then
  SPORTS=( bike hike run ski commute )
  #SPORTS=( bike hike run ski commute vehicle )
fi
if [ -z "$FORCE" ]; then
  FORCE="false"
fi
if [ -z "$JOBLENGTH" ]; then
  JOBLENGTH=720
fi
if [ -z "$DRYRUN" ]; then
  DRYRUN="false"
fi

# Catch-up with latest changes from first job
if [[ "$FORCE" == "false" ]] ; then
  git pull --rebase=false
fi

# Update tileset sources when the summary GEOJsons have changed
printf "\n+++ Upload New Sources +++\n"
MODIFIED="false"
for sport in "${SPORTS[@]}"
do
  fileSUMM=tracks/1_display/${sport}_tracks.geojson
  timeNOW="$(git log --pretty=format:%cd -n 1 --date=format:%s)"
  echo "Processing $fileSUMM"
  if [[ "$FORCE" == "true" ]] ; then
    timeLAST=$timeNOW
  else
    timeLAST="$(git log --pretty=format:%cd -n 1 --date=format:%s -- $fileSUMM)"
  fi
  timeEL=$(($timeNOW-$timeLAST))
  if [[ "$timeEL" -le "$JOBLENGTH" ]]; then
    printf "  Generating $sport tileset\n"
    MODIFIED="true"
    #tilesets delete-source --token $TOKEN --force timsmithch ${sport}_tracks
    #tilesets add-source --token $TOKEN timsmithch ${sport}_tracks tracks/1_display/${sport}_tracks.geojson
    if [[ "$DRYRUN" == "false" ]] ; then
      tilesets upload-source --token $TOKEN timsmithch ${sport}_tracks tracks/1_display/${sport}_tracks.geojson --replace
    else
      echo "tilesets upload-source --token $TOKEN timsmithch ${sport}_tracks tracks/1_display/${sport}_tracks.geojson --replace"
    fi
  else
    printf "  .\n"
  fi
done
printf "\n+++ Full Source List +++\n"
tilesets list-sources --token $TOKEN timsmithch

# Generate the new tileset
if [[ "$MODIFIED" == "true" ]] ; then
  # Create the initial tileset, only necessary first time, afterwards update is all
  #tilesets create timsmithch.all_tracks --token $TOKEN --recipe scripts/all_tracks_recipe.json --name "All track sports"
  # Update the recipe to generate the tilesets, only if it changes
  #tilesets update-recipe --token $TOKEN timsmithch.all_tracks scripts/all_tracks_recipe.json
  # Launch the tilset generation and wait for completion
  printf "\n+++ Publish +++\n"
  if [[ "$DRYRUN" == "false" ]] ; then
    tilesets publish --token $TOKEN timsmithch.all_tracks
    JOBRUN=1
    n=1
    while [[ $JOBRUN -eq 1 && $n -lt 21 ]]; do
      sleep 7
      JOBRUN=$(tilesets status --token $TOKEN timsmithch.all_tracks | jq --exit-status '.status == "processing"' >/dev/null)
      n=$((n+1))
    done
  fi
  printf "\n+++ Finished +++\n"
  tilesets status --token $TOKEN --indent 2 timsmithch.all_tracks
fi
