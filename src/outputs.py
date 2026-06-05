"""
The outputs.py file takes the data from our candidate plan and produces
human readable output in the form of a KML file and a PNG file.

KML's can be uploaded to QGroundControl, BlackSwift's FMS, or Google Earth.

PNG's simply exist as a visual reference for the RPIC and do not serve any other
purpose.

This file does not check if output is "correct", it is simply a black box
that takes the data the engine produces and produces output.

This follows my design of "dumb unidirectionality", meaning that files
are only as knowledgeable of the rest of the program as they have to be
and the engine's pipline follows a linear, unidirectional computational flow.

**NOTE**: Outputs.py may not always be the last link in the chain, once legal
and other sources of validation are needed, its position may change to only produce
output from validated data.
"""

# Calypso engine file imports:
from objects import CandidatePlan, Waypoint
import constants as CONST

# Package imports
import simplekml
import matplotlib

# Setting png backend
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path
import math
from datetime import datetime
from typing import Optional, Iterable

# Outputs.py helpers are defined below:


# Walks the candidate plan's route and fills a list with the actions needed to generate kml
def _route_coords(plan: CandidatePlan):

    # KML list for holding the necessary items to make points using
    # simplekml.
    kml_wp_list = []
    for point in plan.waypoints:

        # Each element in the list is a tuple containing a given waypoint's coordinates, altitude,
        # and action.
        kml_wp = (point.longitude, point.latitude, point.altitude, point.action)
        kml_wp_list.append(kml_wp)

    return kml_wp_list


def categorize(action: str):

    if action == "science":

        return "science"

    else:
        return "transit"


def _segments_by_action(route: list):

    # Each segment (science, transit) will be categorized so
    # the two can be represented in distinct colors

    # Finished runs
    segments = []

    # will be set to the current category of the run being built
    current_category = None

    # the points on the line of the run being built
    current_pts = []

    # last point seen
    prev_pt = None

    for route_point in route:

        # according to my loop structure, the last index of the tuple is always the action
        cat = categorize(route_point[-1])

        # according to my loop structure, the first two indices are long and lat, respectively
        long, lat = route_point[0], route_point[1]

        if current_category == None:

            current_category = cat

            current_pts.append((long, lat))

        elif cat == current_category:

            # same run just extends the current list
            current_pts.append((long, lat))

        else:

            segments.append((current_category, current_pts))

            current_category = cat

            current_pts = [prev_pt, (long, lat)]

        prev_pt = (long, lat)

    # flush the final open run AFTER the loop ends
    if current_pts:
        segments.append((current_category, current_pts))

    return segments


# converts azimuth to a (dx, dy) for PNG arrow denoting sun position/angle
def _sun_vector(sun_az_deg, length):

    # math.sin/cos expect RADIANS; azimuth comes in as degrees (0 = north,
    # clockwise), so convert first. dx uses sin, dy uses cos so the arrow
    # points along the compass bearing with north = +y.
    sun_az_rad = math.radians(sun_az_deg)

    dx = (length * math.sin(sun_az_rad))

    dy = (length * math.cos(sun_az_rad))

    return (dx, dy)


def _output_path(plan_name: str, extension: str, out_dir: str = "EMPTY"):

    # "EMPTY" is the sentinel for "caller gave no directory" -> fall back to the
    # configured default output directory from constants.
    if out_dir == "EMPTY":
        out_dir = CONST.OUTPUT_DIRECTORY

    # Always make sure the resolved directory exists (idempotent).
    Path(out_dir).mkdir(parents=True, exist_ok=True)

    # gets the current date and time after establishing it
    curr_datetime = datetime.now()

    curr_date_str = curr_datetime.strftime("%Y%m%d-%H%M")

    output_path = f"{out_dir}/{plan_name}_{curr_date_str}.{extension}"

    return output_path