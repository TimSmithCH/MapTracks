#!/bin/bash
set -e   # Exit with nonzero exit code if anything fails
#set -x   # Debug mode to echo commands

#ls -lR tracks/

mkdir -pv tracks/2_geojson/bike
mkdir -pv tracks/2_geojson/hike
mkdir -pv tracks/2_geojson/run
mkdir -pv tracks/2_geojson/ski
mkdir -pv tracks/2_geojson/wip

TYPES="bike hike run ski wip"
FORCE=false

for type in $TYPES
do
  echo "Processing $type files"
  MODIFIED=true
  #MODIFIED=false
  FILES=tracks/3_gpx/$type/*.gpx
  for f in $FILES
  do
    file=${f##*/}
    base=${file%.gpx}
    fileIN=tracks/3_gpx/$type/$base.gpx
    fileOUT=tracks/2_geojson/$type/$base.geojson
    if $FORCE ; then
      timeIN="$(date +%s)"
    else
      timeIN="$(git log --pretty=format:%cd -n 1 --date=format:%s -- $fileIN)"
    fi
    timeOUT="$(git log --pretty=format:%cd -n 1 --date=format:%s -- $fileOUT)"
    if [[ $timeIN -gt $timeOUT ]]; then
      printf "\n  Generating GEOJSON: $fileOUT \n"
      MODIFIED=true
      # 0.000025 tolerance = resolution of 2m
      ogr2ogr -nlt LINESTRING -f GeoJSON -simplify 0.00002 $fileOUT $fileIN tracks
    else
      printf "."
    fi
  done
  if $MODIFIED ; then
    fileSUMM=tracks/1_display/${type}_tracks.geojson
    printf "\n Generating aggregate: $fileSUMM \n"
    python scripts/geojsons_merge.py -i tracks/2_geojson/$type -o $fileSUMM
  fi
done