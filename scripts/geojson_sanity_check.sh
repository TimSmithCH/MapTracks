#!/bin/bash
# -*- coding: utf-8 -*-
#-------------------------------------------------------------------------------
#
# DESCRIPTION
#    Check all GPX files have up-to-date generated GeoJSON versions and that no
#    GeoJSON files exist for deleted GPX files
#
# EXAMPLES
#    ./geojson_sanity_check.sh
#
# IMPLEMENTATION
#    Author       Tim Smith
#    Copyright    Copyright (c) Tim Smith
#    Licence      GNU General Public License
#
#-------------------------------------------------------------------------------
set -e   # Exit with nonzero exit code if anything fails
#set -x   # Debug mode to echo commands

TYPES="bike hike run ski skiclimb swim wip commute vehicle"

printf "\n=== Forward Check ===\n  "
for type in $TYPES
do
  printf "\n=== Processing $type files ===\n  "
  FILES=tracks/3_gpx/$type/*.gpx
  for f in $FILES
  do
    file=${f##*/}
    base=${file%.gpx}
    fileIN=tracks/3_gpx/$type/$base.gpx
    fileOUT=tracks/2_geojson/$type/$base.geojson
    if [[ ! -f $fileOUT ]] ; then
      printf " $fileOUT not found\n"
    else
      timeIN="$(git log --pretty=format:%cd -n 1 --date=unix -- $fileIN)"
      timeOUT="$(git log --pretty=format:%cd -n 1 --date=unix -- $fileOUT)"
      if [[ $timeIN -gt $timeOUT ]]; then
        printf " $fileOUT too old\n"
      fi
    fi
  done
done

printf "\n=== Reverse Check ===\n  "
for type in $TYPES
do
  printf "\n=== Processing $type files ===\n  "
  FILES=tracks/2_geojson/$type/*.geojson
  for f in $FILES
  do
    file=${f##*/}
    base=${file%.geojson}
    fileOUT=tracks/2_geojson/$type/$base.geojson
    fileIN=tracks/3_gpx/$type/$base.gpx
    if [[ ! -f $fileIN ]] ; then
      printf " $fileOUT is extra\n"
    fi
  done
done

printf "\n=== End of Check ===\n  "
