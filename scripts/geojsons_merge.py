#!/usr/bin/python
from json import load, dump
from argparse import ArgumentParser
from re import compile
import sys
import os


parser = ArgumentParser(description="Group (merge) multiple GeoJSON files.")

defaults = dict(outfile=sys.stdout)

parser.set_defaults(**defaults)

# Can be passed a directory or a list of files
parser.add_argument('-d', '--directory', help='Directory containing files to be merged')
parser.add_argument('-f', '--files', nargs='*', help='Files to be merged')
# Only one output file!
parser.add_argument('-o', '--outfile', dest='outfile', help='Outfile')

if __name__ == '__main__':
    args = parser.parse_args()
    if isinstance(args.files, list):
        # Already supplied a list of files
        infiles = args.files
    else:
        # Expand directory into a list of files
        infiles = [os.path.join(dp, f) for dp, dn, fn in os.walk(os.path.expanduser(args.directory)) for f in fn]
    outfile = args.outfile

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

    with open(outfile, 'w') as wj:
        dump(outjson, wj, ensure_ascii=False)
        #dump(outjson, wj, indent=1, ensure_ascii=False)
