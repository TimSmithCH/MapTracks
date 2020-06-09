#!/bin/bash
set -e   # Exit with nonzero exit code if anything fails
#set -x   # Debug mode to echo commands

#ls -lR tracks/

mkdir -pv tracks/2_geojson/bike
mkdir -pv tracks/2_geojson/hike
mkdir -pv tracks/2_geojson/run
mkdir -pv tracks/2_geojson/ski

TYPES="bike hike run ski"
FORCE=false

for type in $TYPES
do
  echo "Processing $type"
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
      printf "\n  Generating $fileOUT \n"
      # 0.000025 tolerance = resolution of 2m
      ogr2ogr -nlt LINESTRING -f GeoJSON -simplify 0.00002 $fileOUT $fileIN tracks
    else
      printf "."
    fi
  done
  fileSUMM=tracks/1_display/${type}_tracks.geojson
  printf "\n Generating $fileSUMM \n"
  node_modules/\@mapbox/geojson-merge/geojson-merge tracks/2_geojson/$type/*.geojson >$fileSUMM
done
