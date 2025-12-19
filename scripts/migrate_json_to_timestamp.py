#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
-------------------------------------------------------------------------------

 DESCRIPTION
    Convert Pull_Strava JSON file names to timestamp convention

 EXAMPLES
    python migrate_to_timestamp.py JSONfiles

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
    parser.add_argument("files", help="individual GPX filename [filenames]", nargs="+")
    parser.add_argument(
        "-d", "--dryrun", action="store_true", help="Dont actually create new files"
    )
    parser.add_argument(
        "-f", "--force", action="store_true", help="Force creation of file even if processed already"
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
    of = str(ts) + "." + name_part + ".json"
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
            # Retain only JSON files from the mpaths list
            fpaths = [file for file in mpaths if file.endswith(".json")]
            fpaths.sort()

    # Loop over all files in list
    outcount = 0
    outtotal = len(fpaths)
    for fpath in fpaths:
        dont_delete = False
        outcount += 1
        print("INFO: Processing {}".format(fpath))
        with open(fpath) as f:
            d = json.load(f)
            # Load the track data into a dataframe
            #track_df = pd.DataFrame(d['data'][0]['values'])
            #track_df.columns = d['data'][0]['fields']
            # Load the metadata into a dict
            md = d['metadata']
            if args.verbose:
                print(md)

        dname = os.path.dirname(fpath)
        bname = os.path.basename(fpath)
        fname = os.path.splitext(bname)[0]
        sname = fname.split('.',1)[0]
        # Step 2: Establish new metadata
        dt = datetime.fromisoformat(md['start_date'])
        ts = int(datetime.timestamp(dt))
        outfile = clean_filename(fpath, ts)

        # Step 3: Rename file
        print("INFO: [{}/{}] Renaming {} to {}".format(outcount,outtotal,fpath, outfile))
        if args.dryrun == False :
            os.rename(fpath,outfile)
