#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#-------------------------------------------------------------------------------
#
# DESCRIPTION
#    Validate GeoJSON files generated in MapTracks processing have sensible
#    track coordinate arrays. Issue summary information
#
# EXAMPLES
#    python geojson_validate.py -f tracks/tim/1_display/vehicle_tracks.geojson
#
# IMPLEMENTATION
#    Author       Tim Smith
#    Copyright    Copyright (c) Tim Smith
#    Licence      GNU General Public License
#
#-------------------------------------------------------------------------------
from json import load, dump
from argparse import ArgumentParser
from re import compile
import sys
import os


parser = ArgumentParser(description="Quick GeoJSON structure validation.")

defaults = dict(outfile=sys.stdout)

parser.set_defaults(**defaults)

# Can be passed a list of files
parser.add_argument('-f', '--files', nargs='*', help='Files to be merged')
parser.add_argument('-d', '--debug', action='store_true', help='Debug FLag')

if __name__ == '__main__':
    args = parser.parse_args()
    if isinstance(args.files, list):
        # Already supplied a list of files
        infiles = args.files
    else:
        # Expand directory into a list of files
        infiles = [os.path.join(dp, f) for dp, dn, fn in os.walk(os.path.expanduser(args.directory)) for f in fn]

    for infile in infiles:
        print("Opening {}".format(infile))
        with open(infile) as f:
            try:
                injson = load(f)
            except:
                print("Failed to load {}".format(f))

        if injson.get('type', None) != 'FeatureCollection':
            raise Exception('Sorry, "%s" does not look like GeoJSON' % infile)

        if type(injson.get('features', None)) != list:
            raise Exception('Sorry, "%s" does not look like GeoJSON' % infile)

        print("Number of features: {}".format(len(injson['features'])))
        for f in injson['features']:
            if f['geometry']['type'] == "LineString":
                if args.debug:
                    print("Number of coordinates: {} {}".format(f['properties']['name'],len(f['geometry']['coordinates'])))
                elif len(f['geometry']['coordinates']) < 2:
                    print("Number of coordinates: {} {}".format(f['properties']['name'],len(f['geometry']['coordinates'])))
            elif f['geometry']['type'] == "Point":
                if args.debug:
                    print("Number of points: {} {}".format(f['properties']['name'],len(f['geometry']['coordinates'])))
            else:
                raise Exception('Sorry, {} feature isnt a LineString or Waypoint'.format(f['properties']['name']))

