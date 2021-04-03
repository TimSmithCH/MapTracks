#!/bin/bash
set -e   # Exit with nonzero exit code if anything fails
#set -x   # Debug mode to echo commands

# WIP directory disappears when empty in GitHub, so continually check it is there
mkdir -pv tracks/2_geojson/wip
#mkdir -pv tracks/2_geojson/commute

TYPES="bike hike run ski wip commute"
FORCE="false"

for type in $TYPES
do
  printf "\n=== Processing $type files ===\n  "
  MODIFIED="false"
  FILES=tracks/3_gpx/$type/*.gpx
  for f in $FILES
  do
    GENERATE=false
    file=${f##*/}
    base=${file%.gpx}
    fileIN=tracks/3_gpx/$type/$base.gpx
    fileOUT=tracks/2_geojson/$type/$base.geojson
    # If the geojson file does not exist yet, generate it
    if [[ ! -f $fileOUT ]] ; then
      GENERATE=true
    else
      # If the geojson file exists, but the GPX file has been updated, generate it
      if [[ "$FORCE" == "true" ]] ; then
        timeIN="$(git log --pretty=format:%cd -n 1 --date=unix)"
      else
        timeIN="$(git log --pretty=format:%cd -n 1 --date=unix -- $fileIN)"
      fi
      timeOUT="$(git log --pretty=format:%cd -n 1 --date=unix -- $fileOUT)"
      if [[ $timeIN -gt $timeOUT ]]; then
        GENERATE=true
      fi
    fi
    if [[ "$GENERATE" == "true" ]] ; then
      printf "\n  Generating GEOJSON: $fileOUT \n  "
      MODIFIED="true"
      # 0.000025 tolerance = resolution of 2m
      ogr2ogr -nlt LINESTRING -f GeoJSON -simplify 0.00002 -lco COORDINATE_PRECISION=7 $fileOUT $fileIN tracks
      #if [[ -z $(git status --untracked-files=no --porcelain $fileOUT) ]]; then
      #  # Git sees no change, so need to remove the file to avoid continuous regeneration, then it will be regenrated successfully next round
      #  printf "\n  Git sees no change in $fileOUT so remove it, and force regenration next round \n  "
      #  rm $fileOUT
      #fi
    else
      printf "."
    fi
  done
  if [[ "$MODIFIED" == "true" ]] ; then
    fileSUMM=tracks/1_display/${type}_tracks.geojson
    printf "\n+++ Generating aggregate: $fileSUMM +++\n"
    python scripts/geojsons_merge.py -i tracks/2_geojson/$type -o $fileSUMM
  fi
done
