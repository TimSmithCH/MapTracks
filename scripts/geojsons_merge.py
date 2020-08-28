#!/usr/bin/python
from json import load, dump
from argparse import ArgumentParser
from re import compile
import sys
import os


parser = ArgumentParser(description="Group (merge) multiple GeoJSON files.")

defaults = dict(outfile=sys.stdout)

parser.set_defaults(**defaults)


parser.add_argument('-i', '--files', help='Files to be merged')
parser.add_argument('-o', '--outfile', dest='outfile', help='Outfile')

if __name__ == '__main__':
    args = parser.parse_args()
    infiles = sorted(os.listdir(args.files))
    outfile = args.outfile

    outjson = dict(type='FeatureCollection', features=[])

    for infile in infiles:
        jfile = os.path.join(args.files, infile)
        with open(jfile) as f:
            injson = load(f)

        if injson.get('type', None) != 'FeatureCollection':
            raise Exception('Sorry, "%s" does not look like GeoJSON' % infile)

        if type(injson.get('features', None)) != list:
            raise Exception('Sorry, "%s" does not look like GeoJSON' % infile)
        try:
            outjson['features'] += injson['features']
        except:
            outjson['features'] += injson

    with open(outfile, 'w') as wj:
        dump(outjson, wj, indent=2, ensure_ascii=False)
