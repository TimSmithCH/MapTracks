#!/usr/bin/python
# #!/Users/Tim/Code/ACTION/BigSurPy3/bin/python
# -*- coding: utf-8 -*-
# -------------------------------------------------------------------------------
#
# DESCRIPTION
#    Add an enclosing bounding box to a set of track files
#
# EXAMPLES
#    python gpx_ensemble.py -v tracks/tim/3_gpx/vehicle/*Sardinia*.gpx
#
# IMPLEMENTATION
#    Author       Tim Smith
#    Copyright    Copyright (c) Tim Smith
#    Licence      GNU General Public License
#
# -------------------------------------------------------------------------------
import os
import pathlib
import argparse
import gpxpy


# -------------------------------------------------------------------------------
# Initialise command line options and their defaults
def parse_command_line():
    global VERBOSE
    # Instantiate the parser
    parser = argparse.ArgumentParser(
        description="Add an enclosing bounding box to a set of track files"
    )
    # Set up the argument defaults
    defaults = dict(verbose=False)
    parser.set_defaults(**defaults)
    # Parse the command line
    parser.add_argument("files", help="individual gpx filename [filenames]", nargs="+")
    parser.add_argument(
        "-o",
        "--outdir",
        dest="outdir",
        help="Directory to store converted geojson files",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Turn on verbose output"
    )
    args = parser.parse_args()
    VERBOSE = True if args.verbose == True else False
    return args


# -------------------------------------------------------------------------------
# Prepare the encompassing bounding box for all files in one ensemble of files
def prepare_global_bbox(fpaths):
    llx = 180.0
    lly = 90.0
    urx = -180.0
    ury = -90.0
    for fpath in fpaths:
        try:
            gpx = gpxpy.parse(open(fpath, "r"))
        except:
            print("ERROR: Error trying to parse {}".format(fpath))
        fb = gpx.get_bounds()
        # Lower left corner
        llx = min(llx, fb.min_longitude)
        lly = min(lly, fb.min_latitude)
        # Upper right corner
        urx = max(urx, fb.max_longitude)
        ury = max(ury, fb.max_latitude)
        gbounds = gpxpy.gpx.GPXBounds(lly, ury, llx, urx)
    return gbounds


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

    # Prepare the encompassing bounding box for all files in one ensemble of files
    if VERBOSE:
        print(" ACTION: Prepare global Bounding Box")
    gbb = prepare_global_bbox(fpaths)
    gbb_str = (
        str(gbb.min_longitude)
        + "/"
        + str(gbb.min_latitude)
        + "/"
        + str(gbb.max_longitude)
        + "/"
        + str(gbb.max_latitude)
    )
    if VERBOSE:
        print("  > Global BBox {}".format(gbb_str))

    for fpath in fpaths:
        try:
            gpx = gpxpy.parse(open(fpath, "r"))
        except:
            print("ERROR: Error trying to parse {}".format(fpath))
        if VERBOSE:
            print("INFO: Processing {}".format(pathlib.Path(fpath).name))

        gpx.description = "Ensemble"
        gpx.bounds = gbb
        gbounds_str = (
            str(gbb.min_longitude)
            + "/"
            + str(gbb.min_latitude)
            + "/"
            + str(gbb.max_longitude)
            + "/"
            + str(gbb.max_latitude)
        )
        if VERBOSE:
            print("  > Bbox {}".format(gbounds_str))

        # Write out new GPX file
        if str(args.outdir) == "./":
            outfile = args.outdir + pathlib.Path(fpath).name
        else:
            outfile = fpath
        if VERBOSE:
            print("INFO: Writing out new content to {}".format(outfile))
        newtree = gpx.to_xml(prettyprint=True)
        with open(outfile, "w") as f:
            f.write(newtree)
