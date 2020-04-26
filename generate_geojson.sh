#!/bin/bash
set -e   # Exit with nonzero exit code if anything fails
#set -x   # Debug mode to echo commands

#ls -lR tracks/

mkdir -pv tracks/geojson/bike
mkdir -pv tracks/geojson/hike
mkdir -pv tracks/geojson/run
mkdir -pv tracks/geojson/ski

TYPES="bike hike run ski"
FORCE=true

for type in $TYPES
do
  echo "Processing $type"
  FILES=tracks/gpx/$type/*.gpx
  for f in $FILES
  do
    file=${f##*/}
    base=${file%.gpx}
    fileIN=tracks/gpx/$type/$base.gpx
    fileOUT=tracks/geojson/$type/$base.geojson
    if $FORCE ; then
      timeIN="$(date +%s)"
    else
      timeIN="$(git log --pretty=format:%cd -n 1 --date=format:%s -- $fileIN)"
    fi
    timeOUT="$(git log --pretty=format:%cd -n 1 --date=format:%s -- $fileOUT)"
    if [[ $timeIN -ge $timeOUT ]]; then
      printf "\n  Generating $fileOUT \n"
      ogr2ogr -nlt LINESTRING -f GeoJSON -simplify 0.000025 $fileOUT $fileIN tracks
    else
      printf "."
    fi
  done
  fileSUMM=tracks/geojson/${type}_tracks.geojson
  printf "\n Generating $fileSUMM \n"
  node_modules/\@mapbox/geojson-merge/geojson-merge tracks/geojson/$type/*.geojson >$fileSUMM
done
