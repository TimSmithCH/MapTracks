#!/bin/bash
set -e   # Exit with nonzero exit code if anything fails
set -x   # Debug mode to echo commands

TYPES="bike hike run ski"
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
    if [[ $fileIN -nt $fileOUT ]]; then
      printf "\n  Generating $fileOUT \n"
      ogr2ogr -nlt LINESTRING -f GeoJSON -simplify 0.0001 $fileOUT $fileIN tracks
    else
      printf "."
    fi
  done
  fileSUMM=tracks/geojson/${type}_tracks.geojson
  printf "\n Generating $fileSUMM \n"
  geojson-merge tracks/geojson/$type/*.geojson >$fileSUMM
done

tilesets list-sources --token `cat tileset_api` timsmithch
tilesets update-recipe --token `cat tileset_api` timsmithch.all_tracks ./tracks_recipe.json
tilesets publish --token `cat tileset_api` timsmithch.all_tracks

rm tileset_ap*
