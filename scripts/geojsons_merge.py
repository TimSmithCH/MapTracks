#!/usr/bin/python
from json import load, dump
from argparse import ArgumentParser
from re import compile
import sys
import os
import pathlib


parser = ArgumentParser(description="Group (merge) multiple GeoJSON files.")

defaults = dict(outfile=sys.stdout)

parser.set_defaults(**defaults)

# Can be passed a directory or a list of files
parser.add_argument("files", help="individual fit filename [filenames]", nargs="+")
parser.add_argument('-d', "--dryrun", action="store_true", help="Dont actually create new files")
#parser.add_argument('-f', '--files', nargs='*', help='Files to be merged')
# Only one output file!
parser.add_argument('-o', '--outfile', dest='outfile', help='Outfile')

if __name__ == '__main__':
    args = parser.parse_args()

    # Expand any directories passed on the command line into a list of files
    infiles = []
    for fpath in args.files:
        if os.path.isfile(fpath):
            infiles.append(fpath)
        elif os.path.isdir(fpath):
            mpaths = [
                os.path.join(dp, f)
                for dp, dn, fn in os.walk(os.path.expanduser(fpath))
                for f in fn
            ]
            # Retain only GEOJSON files from the mpaths list
            infiles = [file for file in mpaths if file.endswith(".geojson")]
            infiles.sort()

    # If passed an output directory create standard output filename from input directory
    if os.path.isdir(args.outfile) and os.path.isdir(args.files[0]):
        dir_name = pathlib.Path(args.files[0]).stem
        outfile = args.outfile + "/" + dir_name + "_tracks.geojson"
    else:
        outfile = args.outfile
    print("GeoJSON_Merge: concatenating {} files into {}".format(len(infiles),outfile))

    outjson = dict(type='FeatureCollection', features=[])

    for infile in infiles:
        with open(infile) as f:
            try:
                injson = load(f)
            except:
                print("Failed to load {}".format(f))

        if injson.get('type', None) != 'FeatureCollection':
            raise Exception('Sorry, "%s" does not look like GeoJSON' % infile)

        if type(injson.get('features', None)) != list:
            raise Exception('Sorry, "%s" does not look like GeoJSON' % infile)
        try:
            outjson['features'] += injson['features']
        except:
            outjson['features'] += injson

    if args.dryrun == False :
        with open(outfile, 'w') as wj:
            dump(outjson, wj, ensure_ascii=False)
            #dump(outjson, wj, indent=1, ensure_ascii=False)
