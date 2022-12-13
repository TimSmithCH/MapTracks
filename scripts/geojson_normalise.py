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

    # If the track is split into segments, then make segment styles alternate
    if len(gj['features']) > 1:
        opacity_toggle = "0.0"   # Initialise
        for f in gj['features'][1:]:
            # Dont touch the waypoints, only the tracks!
            if f['geometry']['type'] == "LineString":
                if opacity_toggle == "0.0":   # First one found
                    opacity_toggle = f['properties']['desc']
                else:
                    if opacity_toggle == "1.0":
                        opacity_toggle = "0.5"
                    else:
                        opacity_toggle = "1.0"
                    f['properties']['desc'] = opacity_toggle
        print("Set alternating opacity (100%/50%) in filename {0:48s}".format(fname))
        modified = True

    # Write out any changes
    if modified:
        #outfile = mpath + ".new"
        outfile = mpath
        with open(outfile, "w") as f:
            json.dump(gj,f)
            #json.dump(gj,f,indent=0)
            f.write('\n')
