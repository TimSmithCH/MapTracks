#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
-------------------------------------------------------------------------------

 DESCRIPTION
    Compare GPX directories generated from RAW originals to those generated
    via Strava

 EXAMPLES
    python compare_gpx_dirs.py -s 3_gpx GPXfiles

 IMPLEMENTATION
    Author       Tim Smith
    Copyright    Copyright (c) Tim Smith
    Licence      GNU General Public License

-------------------------------------------------------------------------------
"""

import os
import pathlib
import argparse
import json
import re
import string
from datetime import datetime, timedelta
import pandas as pd


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
        force=False,
        verbose=False,
    )
    parser.set_defaults(**defaults)
    # Parse the command line
    parser.add_argument("files", help="GPX filename or dirname [filenames]", nargs="+")
    parser.add_argument(
        "-d", "--dryrun", action="store_true", help="Dont actually create new files"
    )
    parser.add_argument(
        "-f", "--force", action="store_true", help="Force creation of file even if processed already"
    )
    parser.add_argument(
        "-s", "--strava", dest="strava", action="append", help="Directory containing strava derived gpx files",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Turn on verbose output"
    )
    args = parser.parse_args()
    VERBOSE = True if args.verbose == True else False
    return args


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

    # Expand any directories passed on the command line into a list of raw files
    rpaths = []
    for rpath in args.files:
        print("Scanning raw files in {}".format(rpath))
        if os.path.isfile(rpath):
            rpaths.append(rpath)
        elif os.path.isdir(rpath):
            mpaths = [
                os.path.join(dp, f)
                for dp, dn, fn in os.walk(os.path.expanduser(rpath))
                for f in fn
            ]
            # Retain only GPX files from the mpaths list
            rpaths = [file for file in mpaths if file.endswith(".gpx")]
    rpaths.sort()

    # Expand strava directories passed as arguement into a list of strava files
    spaths = []
    for spath in args.strava:
        print("Scanning strava files in {}".format(spath))
        if os.path.isfile(spath):
            spaths.append(spath)
        elif os.path.isdir(spath):
            npaths = [
                os.path.join(dp, f)
                for dp, dn, fn in os.walk(os.path.expanduser(spath))
                for f in fn
            ]
            # Retain only GPX files from the npaths list
            spaths = [file for file in npaths if file.endswith(".gpx")]
    spaths.sort()

    # Loop over all raw files in list
    df_raw = pd.DataFrame(columns=['FileName', 'FilePath', 'Type', 'TimeStamp'])
    for rpath in rpaths:
        dname = pathlib.Path(rpath).parent
        fname = pathlib.Path(rpath).stem
        tstamp = fname.split('.',1)[0]
        trktype = pathlib.Path(dname).parts[-1]
        df_raw.loc[len(df_raw)] = {'FileName': fname,
                                   'FilePath': dname,
                                   'Type': trktype,
                                   'TimeStamp': tstamp}

    # Loop over all strava files in list
    df_strava = pd.DataFrame(columns=['FileName', 'FilePath', 'Type', 'TimeStamp'])
    for spath in spaths:
        dname = pathlib.Path(spath).parent
        fname = pathlib.Path(spath).stem
        tstamp = fname.split('.',1)[0]
        trktype = pathlib.Path(dname).parts[-1]
        df_strava.loc[len(df_strava)] = {'FileName': fname,
                                   'FilePath': dname,
                                   'Type': trktype,
                                   'TimeStamp': tstamp}

    dfrc = df_raw.groupby("Type").size().rename('RawSum')
    dfsc = df_strava.groupby("Type").size().rename('StravaSum')
    df = pd.concat([dfrc, dfsc], axis=1)
    print(df)

    # Loop over dataframes looking for matches
    print("Raw files: {}".format(len(df_raw)))
    df_raw = df_raw.assign(Matched=df_raw["TimeStamp"].isin(df_strava["TimeStamp"]))
    dfrg = df_raw.groupby(['Type', 'Matched']).size().unstack(fill_value=0)
    print(dfrg)

    print("Strava files: {}".format(len(df_strava)))
    df_strava = df_strava.assign(Matched=df_strava["TimeStamp"].isin(df_raw["TimeStamp"]))
    dfsg = df_strava.groupby(['Type', 'Matched']).size().unstack(fill_value=0)
    print(dfsg)

    print(df_raw.loc[df_raw['Matched'] == False])
