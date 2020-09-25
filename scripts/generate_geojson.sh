#!/bin/bash
set -e   # Exit with nonzero exit code if anything fails
set -x   # Debug mode to echo commands

mkdir -pv tracks/2_geojson/commute
#mkdir -pv tracks/2_geojson/wip

TYPES="bike hike run ski wip commute"
FORCE="false"

for type in $TYPES
do
  printf "\n=== Processing $type files ===\n  "
  MODIFIED="false"
  FILES=tracks/3_gpx/$type/*.gpx
  for f in $FILES
  do
    file=${f##*/}
    base=${file%.gpx}
    fileIN=tracks/3_gpx/$type/$base.gpx
    fileOUT=tracks/2_geojson/$type/$base.geojson
    if [[ "$FORCE" == "true" ]] ; then
      timeIN="$(git log --pretty=format:%cd -n 1 --date=format:%s)"
    else
      timeIN="$(git log --pretty=format:%cd -n 1 --date=format:%s -- $fileIN)"
    fi
    timeOUT="$(git log --pretty=format:%cd -n 1 --date=format:%s -- $fileOUT)"
    if [[ $timeIN -gt $timeOUT ]]; then
      printf "\n  Generating GEOJSON: $fileOUT \n  "
      MODIFIED="true"
      ls -l $fileOUT $fileIN
      # 0.000025 tolerance = resolution of 2m
      ogr2ogr -nlt LINESTRING -f GeoJSON -simplify 0.00002 $fileOUT $fileIN tracks
      ls -l $fileOUT $fileIN
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
