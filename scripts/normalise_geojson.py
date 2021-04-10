#!/usr/bin/python
import os
import fnmatch
import argparse
import json

# Parse the arguments
parser = argparse.ArgumentParser(description='Ensure the second feature (if any) in GEOJSON file is styled differently.')
parser.add_argument("-file", help="individual filename [filename]", nargs="+")
args = parser.parse_args()
filename = args.file

for mpath in filename:
    modified = False
    # Name from filename
    bname = os.path.basename(mpath)
    fname = os.path.splitext(bname)[0]
    try:
        gj = json.load(open(mpath,'r'))
    except:
        print("Error trying to parse {}".format(mpath))

    # If there are 2 features (hence a track split into up and down) then change style of second one
    if len(gj['features']) == 2:
        gj['features'][1]['properties']['desc'] = "0.5"
        print("Set opacity to 50% in second feature in filename {0:48s}".format(fname))
        modified = True

    # Write out any changes
    if modified:
        #outfile = mpath + ".new"
        outfile = mpath
        with open(outfile, "w") as f:
            json.dump(gj,f,indent=0)
            f.write('\n')
