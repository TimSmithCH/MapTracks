#!/usr/bin/python
# #!/Users/Tim/Code/ACTION/BigSurPy3/bin/python
# -*- coding: utf-8 -*-
# -------------------------------------------------------------------------------
#
# DESCRIPTION
#    Covert GPX files into GeoJSON files. At the same time:
#    Always enhace:
#     - add global bounding box to file metadata
#     - add track bounding box to each track metadata
#     - promote segments into tracks
#    Optionally apply various transformations to the tracks:
#     - split tracks into up-hill and down-hill segments (before promotion!)
#     - simplify the track using Douglas-Peucker algorithm to reduce # points
#
# EXAMPLES
#    python gpx_to_geojson.py -s -u tracks/tim/3_gpx/bike/9634087156.Baudichonne.gpx
#    ls tracks/tim/3_gpx/skiclimb/8* | xargs -I {} ./gpx_to_geojson.py {}
#    git status --porcelain tracks/tim/3_gpx | awk '{print $2}' | xargs -I {} ./gpx_to_geojson.py {}
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
import geojson


# -------------------------------------------------------------------------------
# Initialise command line options and their defaults
def parse_command_line():
    global VERBOSE
    # Instantiate the parser
    parser = argparse.ArgumentParser(
        description="Convert GPX track into standardised GeoJSON tracks"
    )
    # Set up the argument defaults
    defaults = dict(
        precision=6,
        tolerance=1.6,
        dryrun=False,
        simplify=False,
        updown=False,
        verbose=False,
    )
    # Precision=6 : Trim cooridnate precision to 6 decimal places which is 0.1 metre
    # Tolerance=1.6 : Simplify tracks to a tolerance of roughly 1 metre (mapping degree fraction to metre varies with latitude)
    #  old ogr2ogr max_distance of 0.00002 maps to (tolerance=1.6945)
    parser.set_defaults(**defaults)
    # Parse the command line
    parser.add_argument("files", help="individual gpx filename [filenames]", nargs="+")
    parser.add_argument(
        "-d", "--dryrun", action="store_true", help="Dont actually create new files"
    )
    parser.add_argument(
        "-o",
        "--outdir",
        dest="outdir",
        help="Directory to store converted geojson files",
    )
    parser.add_argument(
        "-p",
        "--precision",
        type=int,
        help="Round lat/lon to this number of decimal places",
    )
    parser.add_argument(
        "-s", "--simplify", action="store_true", help="Apply simplification (or not)"
    )
    parser.add_argument(
        "-t",
        "--tolerance",
        type=float,
        help="When simplifying tracks use this tolerance in meters",
    )
    parser.add_argument(
        "-u",
        "--updown",
        action="store_true",
        help="Split tracks into up/down hill segments",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Turn on verbose output"
    )
    args = parser.parse_args()
    VERBOSE = True if args.verbose == True else False
    return args


# -------------------------------------------------------------------------------
# For a track which is already split into segments, create a list of static
# points from the start/end of the segments
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


# -------------------------------------------------------------------------------
# Locate the static points (maximum/minimum) that are separated by more than the
# desired prominanece threshold. These can then be used to split the tracks into
# uphill and downhill sections
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
    for n, elevation in enumerate(elevations[2:], start=2):
        next_step = elevation - elevations[sp[spi]]
        last_step = elevations[sp[spi]] - elevations[sp[spi - 1]]
        # If individual elevation step is unfeasable, skip it
        ele_step = elevations[n] - elevations[n - 1]
        if ele_step > prominence_threshold:
            print(
                "WARNING: Unfeasable single elevation step of {} at {}".format(
                    ele_step, n
                )
            )
            break
        # If in same direction as last inter-stationary-point trend
        if (last_step * next_step) > 0:
            # Update last stationary-point with current
            sp[spi] = n
        # Or if the last step wasnt a proper full one (likely on first step)
        elif (abs(last_step) < (prominence_threshold / 2)) and (
            abs(next_step) > (prominence_threshold / 10)
        ):
            # Update last stationary-point with current
            sp[spi] = n
        # If in oppostite direction to last inter-stationary-point trend
        else:
            if abs(next_step) > prominence_threshold:
                # Found new stationary-point
                sp.append(n)
                spi += 1
    # After loop tidy up: add last point if not already there
    lastp = len(elevations) - 1
    if sp[spi] < lastp:
        last_step = elevations[sp[spi]] - elevations[sp[spi - 1]]
        if abs(last_step) > prominence_threshold:
            sp.append(lastp)
        else:
            sp[spi] = lastp
    # Loop over resultant stationary point array and avoid short segments
    for i in range(1, len(sp)):
        # Its too short, only 1 track point long
        if (sp[i] - sp[i - 1]) < 2:
            # There are spare points in the previous track segment
            if (sp[i - 1] - sp[i - 2]) > 2:
                # steal one
                sp[i - 1] -= 1
    return sp


# -------------------------------------------------------------------------------
# Split the track segments into uphill and downhill section after a static
# point analysis
def split_up_down(tracks):
    for itrk, track in enumerate(tracks):
        modified = False
        nseg = 0
        description = ""
        old_stat_points = get_old_stat_points(track)
        if VERBOSE:
            print(
                "  > Track currently has {} static points {}".format(
                    len(old_stat_points), old_stat_points
                )
            )
        stat_points = get_new_stat_points(track)
        if VERBOSE:
            print(
                "  > Track should have   {} static points {}".format(
                    len(stat_points), stat_points
                )
            )
        # if not np.array_equal(old_stat_points,stat_points):
        if old_stat_points != stat_points:
            # If we need to re-do splitting, start by reassembling the segments back into one
            lseg = len(track.segments)
            if lseg > 1:
                for i in reversed(range(lseg - 1)):
                    track.join(i)
            # Then split them in the new configuration
            seg = track.segments[0]
            if stat_points != None:
                if len(stat_points) > 2:
                    for nsp, sp in enumerate(stat_points[:-2]):
                        cur, nxt = sp, stat_points[nsp + 1]
                        new_seg_len = nxt - cur
                        if cur == 0:
                            new_seg_len += 1
                        ele_diff = seg.points[nxt].elevation - seg.points[cur].elevation
                        if ele_diff > 0 or abs(ele_diff) < 20:
                            if description == "":
                                description = "1.0"  # An UP segment
                        else:
                            if description == "":
                                description = "0.5"  # A DOWN segment
                        if VERBOSE:
                            print(
                                "  Split segment {} at point {} [{}] (track at {}) with elevation diff {:.1f}".format(
                                    nseg, new_seg_len - 1, description, nxt, ele_diff
                                )
                            )
                        track.split(
                            nseg, new_seg_len - 1
                        )  # Second argument is pointer to array starting at zero, so length-1
                        nseg += 1  # Splitting added a segment
                        modified = True
                else:
                    # If going back to an unsplit file, just simply write out
                    description = "1.0"
                    modified = True
            nseg += 1  # Array starts from 0 so count needs 1 more
        else:
            if VERBOSE:
                print("  > Track doesnt need splitting!")
        # And write them  back out to the same file
        if modified:
            track.description = description
            if VERBOSE:
                print("  > Split track {} into {} segments".format(itrk, nseg))
    return None


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

    for fpath in fpaths:
        try:
            gpx = gpxpy.parse(open(fpath, "r"))
        except:
            print("ERROR: Error trying to parse {}".format(fpath))
        print("Processing {}".format(pathlib.Path(fpath).name))

        nsegs = sum(len(t.segments) for t in gpx.tracks)
        print(
            "INFO: GPX file original: {} tracks, {} segments, {} points, {} routes, {} waypoints".format(
                len(gpx.tracks),
                nsegs,
                gpx.get_track_points_no(),
                len(gpx.routes),
                len(gpx.waypoints),
            )
        )

        # Split tracks into uphill and downhill segments
        if args.updown == True:
            if VERBOSE:
                print(" ACTION: Split tracks into Up/Down segments")
            split_up_down(gpx.tracks)

        nsegs = sum(len(t.segments) for t in gpx.tracks)
        print(
            "INFO: GPX file modified: {} tracks, {} segments, {} points, {} routes, {} waypoints".format(
                len(gpx.tracks),
                nsegs,
                gpx.get_track_points_no(),
                len(gpx.routes),
                len(gpx.waypoints),
            )
        )

        # Simplify tracks to a remove unnecessary points whilst preserving geometry
        if args.simplify == True:
            if VERBOSE:
                print(" ACTION: Simplify tracks")
            if VERBOSE:
                print(
                    "  > Using a tolerance of {} metres for simplifying".format(
                        args.tolerance
                    )
                )
            gpx.simplify(max_distance=args.tolerance)

        # Prepare the encompassing bounding box, either of all tracks in one file or all files in one ensemble of files
        if gpx.description == "Ensemble":
            # Alredy generated ensemble so just use it for reprocessing individual files later
            fbounds = gpx.bounds
            print("INFO: file part of an ensemble so use global BBox from GPX file")
        else:
            # Not an ensemble, just generate new bbox for all tracks in single file
            fbounds = gpx.get_bounds()
        if fbounds == None:
            # Some files contain only waypoints, no tracks so dont have a bbox
            fbounds = gpxpy.gpx.GPXBounds(1.0, 2.0, 3.0, 4.0)
        fbounds_str = (
            str(fbounds.min_longitude)
            + "/"
            + str(fbounds.min_latitude)
            + "/"
            + str(fbounds.max_longitude)
            + "/"
            + str(fbounds.max_latitude)
        )
        if VERBOSE:
            print("  > Bbox {}".format(fbounds_str))

        # Convert each track into a Feature
        if VERBOSE:
            print(" ACTION: Converting tracks to Feature LinesStrings")
        if VERBOSE:
            print(
                "  > Using a precision of {} decimal places for coordinate trimming".format(
                    args.precision
                )
            )
        geo_features = []
        for track in gpx.tracks:
            desc = "---"
            tbounds = track.get_bounds()
            tbounds_str = (
                str(tbounds.min_longitude)
                + "/"
                + str(tbounds.min_latitude)
                + "/"
                + str(tbounds.max_longitude)
                + "/"
                + str(tbounds.max_latitude)
            )
            # Make each segment into a LineString
            for segment in track.segments:
                if desc == "---":
                    if track.description != None:
                        desc = "DownHill" if track.description == "0.5" else "UpHill"
                else:
                    desc = "DownHill" if desc == "UpHill" else "UpHill"
                coords = [(p.longitude, p.latitude) for p in segment.points]
                geo_line = geojson.LineString(coords, precision=args.precision)
                geo_features.append(
                    geojson.Feature(
                        properties={
                            "name": track.name,
                            "cmt": track.comment,
                            "desc": desc,
                            "src": fbounds_str,
                            "bbox": tbounds_str,
                        },
                        bbox=[
                            tbounds.min_longitude,
                            tbounds.min_latitude,
                            tbounds.max_longitude,
                            tbounds.max_latitude,
                        ],
                        geometry=geo_line,
                    )
                )

        # Convert each waypoint into a Feature
        if VERBOSE:
            print(" ACTION: Converting waypoints to Feature Points")
        for wp in gpx.waypoints:
            if VERBOSE:
                print(
                    "  > WayPoint: {} -> ({},{}) type [{}]".format(
                        wp.name, wp.latitude, wp.longitude, wp.description
                    )
                )
            geo_point = geojson.Point(
                (wp.longitude, wp.latitude, wp.elevation), precision=args.precision
            )
            geo_features.append(
                geojson.Feature(
                    properties={"name": wp.name, "desc": wp.description},
                    geometry=geo_point,
                )
            )

        # Ensure there are no routes
        if len(gpx.routes) > 0:
            print(" WARNING: file contains routes which have not been dropped")

        # Construct the FeatureCollection from the set of Features
        geoj = geojson.FeatureCollection(
            geo_features,
            name="TrackSet",
            crs={
                "type": "name",
                "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"},
            },
            bbox=[
                fbounds.min_longitude,
                fbounds.min_latitude,
                fbounds.max_longitude,
                fbounds.max_latitude,
            ],
        )

        # Sanity check that it is valid GeoJSON
        if not geoj.is_valid:
            print("ERROR: Aborting as GeoJSON is invalid")
            print(geoj.errors())
            exit(1)

        # Make the json dict to write out to file
        npts = sum(len(f.geometry.coordinates) for f in geoj.features)
        print(
            "INFO: GeoJSON generated: {} tracks, {} points, {} routes, {} waypoints".format(
                len(geoj.features), npts, len(gpx.routes), len(gpx.waypoints)
            )
        )
        dumpj = geojson.dumps(geoj, sort_keys=False)

        # Write out new GeoJSON file
        if str(args.outdir) == "./":
            outfile = args.outdir + pathlib.Path(fpath).stem + ".geojson"
        else:
            outfile = pathlib.Path(fpath.replace("3_gpx", "2_geojson")).with_suffix(
                ".geojson"
            )
        if VERBOSE:
            print("INFO: Writing out new content to {}".format(outfile))
        if args.dryrun == False:
            with open(outfile, "w") as f:
                f.write(dumpj)

########################################################
# Feature could have styling information, but chose to leaving the styling choices to the map rendering
# dash = "[2,2]" if track.description == "1.0" else "[1]"
# Feature( ..., style={"dasharray": dash}, ...)
