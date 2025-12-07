#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
-------------------------------------------------------------------------------

 DESCRIPTION
    Convert Pull_Strava GPX file names to timestamp convention

 EXAMPLES
    python migrate_to_timestamp.py GPXfiles

 IMPLEMENTATION
    Author       Tim Smith
    Copyright    Copyright (c) Tim Smith
    Licence      GNU General Public License

-------------------------------------------------------------------------------
"""

import os
import pathlib
import argparse
import gpxpy
import json
import re
import string
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple, Union
from math import isnan
import xml.etree.ElementTree as mod_etree
import pandas as pd
import fitdecode


# -------------------------------------------------------------------------------
# Initialise command line options and their defaults
def parse_command_line():
    global VERBOSE
    # Instantiate the parser
    parser = argparse.ArgumentParser(
        description="Convert Pull_Strava file names to timestamp convention"
    )
    # Set up the argument defaults
    defaults = dict(
        dryrun=False,
        verbose=False,
    )
    parser.set_defaults(**defaults)
    # Parse the command line
    parser.add_argument("files", help="individual fit filename [filenames]", nargs="+")
    parser.add_argument(
        "-d", "--dryrun", action="store_true", help="Dont actually create new files"
    )
    parser.add_argument(
        "-o", "--outdir", dest="outdir", help="Directory to store converted gpx files",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Turn on verbose output"
    )
    args = parser.parse_args()
    VERBOSE = True if args.verbose == True else False
    return args


# -------------------------------------------------------------------------------
# Standardise ouput filename if required
def clean_filename(fname:str, ts:int ) -> str:

    orig_name = pathlib.Path(fname).stem
    name_part = orig_name.split('.',1)[1]
    orig_path = pathlib.Path(fname).parent

    # Standardise the name to timestamp/title
    of = str(ts) + "." + name_part + ".gpx"
    outfile = str(orig_path) + "/" + of

    return outfile


# -------------------------------------------------------------------------------
# Convert from ISO format date to TimeStamp
def convert_to_timestamp(isodate):
    dt = datetime.fromisoformat(str(isodate))
    ctimestamp = int(datetime.timestamp(dt))
    return ctimestamp


# -------------------------------------------------------------------------------
if __name__ == "__main__":
    # See what the orders are from the command line
    args = parse_command_line()

    # Expand any directories passed on the command line into a list of files
    fpaths = []
    for fpath in args.files:
        if os.path.isfile(fpath):
            fpaths.append(fpath)
        elif os.path.isdir(fpath):
            mpaths = [
                os.path.join(dp, f)
                for dp, dn, fn in os.walk(os.path.expanduser(fpath))
                for f in fn
            ]
            # Retain only GPX files from the mpaths list
            fpaths = [file for file in mpaths if file.endswith(".gpx")]
            fpaths.sort()

    # Loop over all files in list
    outcount = 0
    outtotal = len(fpaths)
    for fpath in fpaths:
        outcount += 1
        try:
            gpx = gpxpy.parse(open(fpath,'r'))
        except:
            print("ERROR: Error trying to parse {}".format(fpath))
        dname = os.path.dirname(fpath)
        bname = os.path.basename(fpath)
        fname = os.path.splitext(bname)[0]
        sname = fname.split('.',1)[0]
        print("INFO: Processing {}".format(fpath))
        if gpx.keywords is None:
            print(" WARN: No keywords, doesnt seem to be a pull_strava file, skipping")
            continue
        # Step 2: Establish new metadata
        ts = convert_to_timestamp(gpx.time)
        outfile = clean_filename(fpath, ts)
        # Step 3: Validate metadata
        if sname == gpx.keywords:
            print(" INFO: Strava ID in filename - unconverted file; fname {} keyword {}".format(sname,gpx.keywords))
        # Skip writing if re-running on an already converted file
        if gpx.name == outfile:
            print(" WARN: name in file {} doesnt match filename {}".format(gpx.name,outfile))
        if outfile == fpath:
            print(" INFO: {} has already been converted, skipping".format(fpath))
            continue
        gpx.name = os.path.basename(outfile)
        gpx.keywords = json.dumps({"sid": str(sname)},separators=(",",":"))

        # Step 3: Save GPX file to disk
        xml = gpx.to_xml(prettyprint=True)
        print("INFO: [{}/{}] Converted {} to {}".format(outcount,outtotal,fpath, outfile))
        if args.dryrun == False :
            with open(outfile, "w") as f:
                f.write(xml)
            # And delete the old one
            os.remove(fpath)
