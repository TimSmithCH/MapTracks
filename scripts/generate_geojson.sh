#!/bin/bash
# -*- coding: utf-8 -*-
#-------------------------------------------------------------------------------
#
# DESCRIPTION
#    Generate GeoJSON when GPX file is new, modified or newer that GEOJSON file
#
# EXAMPLES
#    ./generate_geojson.sh -s hike   ## Limit to only one sport directory to scan
#    ./generate_geojson.sh -f true   ## Force the regeneration if if not new
#
# IMPLEMENTATION
#    Author       Tim Smith
#    Copyright    Copyright (c) Tim Smith
#    Licence      GNU General Public License
#
#-------------------------------------------------------------------------------
set -e   # Exit with nonzero exit code if anything fails
#set -x   # Debug mode to echo commands

while getopts :s:f:d: opt
do
    case "${opt}" in
        s ) SPORTS=${OPTARG};;
        f ) FORCE=${OPTARG};;
        d ) DRYRUN=${OPTARG};;
        \? ) echo "Usage: cmd [-s sports] [-f force] [-d dryrun]"
    esac
done

# Defaults set if arguments aren't passed
if [ -z "$SPORTS" ]; then
  SPORTS=( bike hike run ski skiclimb swim wip commute vehicle )
fi
if [ -z "$FORCE" ]; then
  FORCE="false"
fi
if [ -z "$DRYRUN" ]; then
  DRYRUN="false"
fi


# WIP directory disappears when empty in GitHub, so continually check it is there
mkdir -pv tracks/2_geojson/wip
mkdir -pv tracks/2_geojson/vehicle
#mkdir -pv tracks/2_geojson/commute

for type in $SPORTS
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
      # simplify 0.000025 tolerance = resolution of 2m
      # GPX_ELE_AS_25D allows GPX elevation data to be read in and passed out to GeoJSON as 2.5D (ie 3D where elevation unused in rendering)
      # explodecollections creates a feature per track segment
      if [[ "$DRYRUN" == "false" ]] ; then
        ogr2ogr --config GPX_ELE_AS_25D YES -nlt LINESTRING -simplify 0.00002 -nln LayerName -lco COORDINATE_PRECISION=7 -explodecollections -f GeoJSON $fileOUT $fileIN tracks
      else
        echo "ogr2ogr (options) -f GeoJSON $fileOUT $fileIN tracks"
      fi
      # Avoid grep stopping script on null match with "pipe true" ||: trick
      # grep has exit code 1 for null match and this is usually an error status, but the pipe ensures the last command is asuccessful true
      waypts=$(grep -c "<wpt" $fileIN||:)
      if [[ $waypts -gt 0 ]]
      then
        printf "\n  Appending waypoints to GEOJSON: $fileOUT \n  "
        if [[ "$DRYRUN" == "false" ]] ; then
          ogr2ogr --config GPX_ELE_AS_25D YES -nln LayerName -lco COORDINATE_PRECISION=7 -f GeoJSON -append -update $fileOUT $fileIN waypoints
        else
          echo "ogr2ogr (options) -f GeoJSON -append -update $fileOUT $fileIN waypoints"
        fi
      fi
      if [[ "$DRYRUN" == "false" ]] ; then
        python scripts/geojson_normalise.py -file $fileOUT
      else
        echo "python scripts/geojson_normalise.py -file $fileOUT"
      fi
    else
      printf "."
    fi
  done
  # Generate the summary file when necessary
  fileSUMM=tracks/1_display/${type}_tracks.geojson
  release=www/$fileSUMM
  if [[ "$MODIFIED" == "true" || ! -f $fileSUMM ]] ; then
    printf "\n+++ Generating aggregate: $fileSUMM +++\n"
    if [[ "$DRYRUN" == "false" ]] ; then
      python scripts/geojsons_merge.py -d tracks/2_geojson/$type -o $fileSUMM
      cp $fileSUMM $release
    else
      echo "python scripts/geojsons_merge.py -d tracks/2_geojson/$type -o $fileSUMM"
      echo "cp $fileSUMM $release"
    fi
  fi
done
