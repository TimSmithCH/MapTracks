#!/usr/bin/python
# #!/Users/Tim/Code/ACTION/BigSurPy3/bin/python
import os
import fnmatch
import gpxpy
import re
import numpy as np
import argparse
import datetime

def prune_spaces(oldtree):
    newtree = ""
    for line in oldtree.splitlines():
        match = re.search(r'(\s*)(\S.*$)', line)
        if match:
            # Find current number of spaces
            num_spaces = len(match.group(1))//2
            # Half the number of spaces
            new_length = len(match.group(2))+num_spaces
            # Build the line again
            new_string = match.group(2).rjust(new_length)
            newtree = newtree + new_string + "\n"
    return newtree

def get_old_stat_points(self):
    sp = []
    pi = -1
    if not self.segments:
        return None
    sp.append(0)
    for seg in self.segments:
        pi += len(seg.points)
        sp.append(pi)
    return sp

def get_new_stat_points(self):
    sp = []
    elevations = []
    prominence_threshold = 100.0
    if not self.segments:
        return None
    # Rebuild a single array of elevations (like in recorded track file) from individual segments
    for seg in self.segments:
        for pnt in seg.points:
            if pnt.elevation is not None:
                elevations.append(pnt.elevation)
    if not elevations:
        return None
    sp.append(0)
    sp.append(1)
    spi = 1
    # Loop over elevations array and find stationary points above threshold
    for n, elevation in enumerate(elevations[2:],start=2):
        next_step = elevation - elevations[sp[spi]]
        last_step = elevations[sp[spi]] - elevations[sp[spi-1]]
        # If in same direction as last inter-stationary-point trend
        if (last_step * next_step) > 0:
            # Update last stationary-point with current
            sp[spi] = n
        # Or if the last step wasnt a proper full one (likely on first step)
        elif (abs(last_step) < (prominence_threshold/2)) and (abs(next_step) > (prominence_threshold/10)):
            # Update last stationary-point with current
            sp[spi] = n
        # If in oppostite direction to last inter-stationary-point trend
        else:
            if abs(next_step) > prominence_threshold:
                # Found new stationary-point
                sp.append(n)
                spi += 1
    lastp = len(elevations) - 1
    if sp[spi] < lastp:   # Add last point if not already there
        last_step = elevations[sp[spi]] - elevations[sp[spi-1]]
        if abs(last_step) > prominence_threshold:
            sp.append(lastp)
        else:
            sp[spi] = lastp
    # Loop over resultant stationary point array and avoid short segments
    for i in range(1,len(sp)):
        # Its too short, only 1 track point long
        if (sp[i] - sp[i-1]) < 2:
            # There are spare points in the previous track segment
            if (sp[i-1] - sp[i-2]) > 2:
                # steal one
                sp[i-1] -= 1
    return sp

# Parse the arguments
parser = argparse.ArgumentParser(description='Split the GPX track into climb and descent segments.')
parser.add_argument("files", help="individual gpx filenames [filenames]", nargs="+")
args = parser.parse_args()

VERBOSE = True
RAPID = 0

# Expand any directories passed on the command line into a list of files
fpaths = []
for fpath in args.files:
    if os.path.isfile(fpath):
        fpaths.append(fpath)
    elif os.path.isdir(fpath):
        mpaths = [os.path.join(dp, f) for dp, dn, fn in os.walk(os.path.expanduser(fpath)) for f in fn]
        # Retain only GPX files from the mpaths list
        fpaths = [ file for file in mpaths if file.endswith('.gpx') ]

for fpath in fpaths:
    modified = False
    try:
        gpx = gpxpy.parse(open(fpath,'r'))
    except:
        print("ERROR: Error trying to parse {}".format(fpath))
    bname = os.path.basename(fpath)
    fname = os.path.splitext(bname)[0]
    if VERBOSE : print(" Processing {0:48s}".format(fname))
    if len(gpx.tracks) < 1:
        if VERBOSE : print("WARNING: GPX file contains no tracks")
        if VERBOSE : print("WARNING: GPX file contains {} waypoints".format(len(gpx.waypoints)))
        exit(0)

    # Loop over point extensions and delete cadence for non-bike exercises
    gtype = gpx.tracks[0].type
    if not (gtype == 'Ride' or gtype == 'MountainBikeRide' or gtype == 'Hike' or gtype == 'BackcountrySki'):
        print("WARNING: Track type {} not for splitting".format(gtype))
        exit(0)

    # Split track at stationary points
    nseg = 0
    description = ""
    old_stat_points = get_old_stat_points(gpx.tracks[0])
    if VERBOSE : print(" Track currently has {} static points {}".format(len(old_stat_points),old_stat_points))
    stat_points = get_new_stat_points(gpx.tracks[0])
    if VERBOSE : print(" Track should have   {} static points {}".format(len(stat_points),stat_points))
    if not np.array_equal(old_stat_points,stat_points):
        # If we need to re-do splitting, start by reassembling the segments back into one
        lseg = len(gpx.tracks[0].segments)
        if lseg > 1:
            for i in reversed(range(lseg-1)):
                gpx.tracks[0].join(i)
        # Then split them in the new configuration
        seg = gpx.tracks[0].segments[0]
        if stat_points != None:
            if len(stat_points) > 2:
                for nsp,sp in enumerate(stat_points[:-2]):
                    cur,nxt = sp, stat_points[nsp+1]
                    new_seg_len = nxt - cur
                    if cur == 0:
                        new_seg_len += 1
                    ele_diff = seg.points[nxt].elevation - seg.points[cur].elevation
                    if ele_diff > 0 or abs(ele_diff) < 20:
                        if description == "":
                            description = "1.0"   # An UP segment
                    else:
                        if description == "":
                            description = "0.5"   # A DOWN segment
                    if VERBOSE : print("  [{}] Splitting segment {} at point {} (track at {}) with elevation diff {:.1f}".format(bname,nseg,new_seg_len-1,nxt,ele_diff))
                    gpx.split(0,nseg,new_seg_len-1)   # third argument is pointer to array starting at zero, so length-1
                    nseg += 1   # Splitting added a segment
                    modified = True
            else:
                # If going back to an unsplit file, just simply write out
                description = "1.0"
                modified = True
        nseg += 1   # Array starts from 0 so count needs 1 more
    else:
        print("INFO: Nothing to do!")
    # And write them  back out to the same file
    if modified:
        gpx.tracks[0].description = description
        print(" Split track into {} segments in file {}".format(nseg,bname))

    # Write out any changes
    if modified:
        #outfile = fpath + ".new"
        outfile = fpath
        xmltree = gpx.to_xml()
        newtree = prune_spaces(xmltree)
        with open(outfile, "w") as f:
            f.write(newtree)
    # Exit after a single change if RAPID flag set
    RAPID -= 1
    if RAPID == 0:
        break

