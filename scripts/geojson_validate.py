#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
-------------------------------------------------------------------------------

 DESCRIPTION
    Validate GeoJSON files generated in MapTracks processing have sensible
    track coordinate arrays. Issue summary information
    Add DATE metadata if file doesnt contain it (since only added to individual
    geojsons July 2025  and not backdated yet so only new ones have it)


 EXAMPLES
    python geojson_validate.py -f tracks/tim/1_display/vehicle_tracks.geojson

 IMPLEMENTATION
    Author       Tim Smith
    Copyright    Copyright (c) Tim Smith
    Licence      GNU General Public License

-------------------------------------------------------------------------------
"""
from json import load, dump
from argparse import ArgumentParser
from re import compile
import datetime
import sys
import os
import numpy as np


parser = ArgumentParser(description="Quick GeoJSON structure validation.")

defaults = dict(outfile=sys.stdout)

parser.set_defaults(**defaults)

# Can be passed a list of files
parser.add_argument('-d', '--dryrun',  action='store_true', help='Dont actually update files')
parser.add_argument('-f', '--files',   nargs='*', help='Files to be validated')
parser.add_argument('-s', '--stats',   action='store_true', help='Brief statistics output')
parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')

if __name__ == '__main__':
    infiles = []
    args = parser.parse_args()
    for fpath in args.files:
        if os.path.isfile(fpath):
            infiles.append(fpath)
        elif os.path.isdir(fpath):
            mpaths = [os.path.join(dp, f) for dp, dn, fn in os.walk(os.path.expanduser(fpath)) for f in fn]
            # Retain only GEOJSON files from the mpaths list
            infiles = np.append(infiles,[ file for file in mpaths if file.endswith('.geojson') ])

    for infile in infiles:
        modified = False
        if args.verbose:
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

        if args.verbose:
            print(" Number of features: {}".format(len(injson['features'])))
        for f in injson['features']:
            if f['geometry']['type'] == "LineString":
                if args.verbose:
                    print(" Number of coordinates: {} in {}".format(len(f['geometry']['coordinates']), f['properties']['name']))
                elif len(f['geometry']['coordinates']) < 2:
                    print(" Number of coordinates: {} in {}".format(len(f['geometry']['coordinates']), f['properties']['name']))
                elif args.stats:
                    print(" {:5} coords {}".format(len(f['geometry']['coordinates']), f['properties']['name']))
            elif f['geometry']['type'] == "Point":
                if args.verbose:
                    print(" Number of points: {} in {}".format(len(f['geometry']['coordinates']), f['properties']['name']))
                if args.stats:
                    print(" {:5} points {}".format(len(f['geometry']['coordinates']), f['properties']['name']))
            else:
                raise Exception('Sorry, {} feature isnt a LineString or Waypoint'.format(f['properties']['name']))
            if 'cmt' in f['properties']:
                try:
                    yy,mm,dd = f['properties']['cmt'].split('-')
                except (ValueError, AttributeError):
                    tstamp = 0
                    if args.verbose:
                        print(" Comment doesnt contain date")
                else:
                    tstamp = int(datetime.datetime.fromisoformat(f['properties']['cmt']).timestamp())
                    if args.verbose:
                        print(" Comment contains date: {} {} {}".format(yy,mm,dd))
                        print("  equates to timestamp {}".format(tstamp))
                    if not 'tstamp' in f['properties'] or f['properties']['tstamp'] != tstamp:
                        f['properties']['tstamp'] = tstamp
                        modified = True
        if modified:
            if args.dryrun == False:
                print(" Writing modified contents {}".format(infile))
                with open(infile, "w") as g:
                    dump(injson, g, ensure_ascii=False)
            else:
                if args.verbose:
                    print(" NOT writing modified contents {}".format(infile))

