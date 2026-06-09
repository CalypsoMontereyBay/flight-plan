"""
The outputs.py file takes the data from our candidate plan and produces
human readable output in the form of a KML, PNG, JSON, and Cartopy figure file.

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

"""
============================================================================
==              SECTION 0: KML HELPERS                                    ==
============================================================================
"""


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


def _metrics_caption(plan: CandidatePlan):

    return f"{plan.chosen_orientation}, {plan.score}, {plan.grid_area_m2}, {plan.total_lines}, {plan.duration}, {plan.margin}"


"""
============================================================================
==              SECTION 1: PNG HELPERS                                    ==
============================================================================
"""


# Defines the geographic bounds for png elements such as the sun arrow, etc.
def _route_extent(route: list):

    lons = []

    lats = []

    # length checking route to gracefully handle a case in which an error
    # has occured and the helper recieves an empty route list.
    if not route:

        raise ValueError("Route list is empty and it should not be!")

    else:

        for point in route:

            lons.append(point[0])
            lats.append(point[1])

        return (min(lons), max(lons), min(lats), max(lats))


def _poi_markers(plan: CandidatePlan):

    mission_req = plan.mission_request

    poi_list = []

    poi_list.append(
        (
            mission_req.launch_wp.action,
            mission_req.launch_wp.longitude,
            mission_req.launch_wp.latitude,
            mission_req.launch_wp.altitude,
        )
    )

    poi_list.append(
        (
            mission_req.land_wp.action,
            mission_req.land_wp.longitude,
            mission_req.land_wp.latitude,
            mission_req.land_wp.altitude,
        )
    )

    poi_list.append(
        (
            mission_req.m1_wp.action,
            mission_req.m1_wp.longitude,
            mission_req.m1_wp.latitude,
            mission_req.m1_wp.altitude,
        )
    )

    return poi_list


# Standardizing the coloring paradigm between the png output and the KML,
# KML function will use this to assign colors! (I think)
def _png_color(category: str):

    if category == CONST.WAYPOINT_ACTION_SCIENCE:

        return "green"

    else:

        return "gray"


# converts azimuth to a (dx, dy) for PNG arrow denoting sun position/angle
def _sun_vector(sun_az_deg, length):

    # math.sin/cos expect RADIANS; azimuth comes in as degrees (0 = north,
    # clockwise), so convert first. dx uses sin, dy uses cos so the arrow
    # points along the compass bearing with north = +y.
    sun_az_rad = math.radians(sun_az_deg)

    dx = length * math.sin(sun_az_rad)

    dy = length * math.cos(sun_az_rad)

    return (dx, dy)


def write_kml(plan: CandidatePlan, out_dir: str = "EMPTY"):
    """
    QGC REMINDER:
    A KML uploaded to QGroundControl is VISUALIZATION ONLY. QGC draws the
    LineStrings/Placemarks for review, but it does NOT turn them into a
    flyable mission with auto-generated per-waypoint headings. To actually
    upload-and-fly we will emit a QGC ".plan" file (JSON) -- which is why
    constants.py carries EXTENSION_JSON. That JSON writer is a future helper
    (write_qgc_plan); this KML is for human/Google Earth review.

    Section #1: Prep, establish the kml, get the line segments,
    get the output path, get the route list
    """

    kml = simplekml.Kml()

    route = _route_coords(plan)

    # _segments_by_action expects the (lon, lat, alt, action) tuples from
    # _route_coords -- NOT raw Waypoint objects (those aren't subscriptable).
    segments = _segments_by_action(route)

    path = _output_path(plan.name, CONST.EXTENSION_KML, out_dir)

    """
    Section #2: Set the document name and metadata 
    """

    kml.document.name = plan.name

    kml.document.description = _metrics_caption(plan)

    """
    Section #3: Draw the route
    """

    for category, pts in segments:

        ls = kml.newlinestring(name=category)

        """
        IF YOU OPEN THIS FILE IN A CODE EDITOR WITH PYLANCE:
        
        **There is not error in the lines that contain: .coords, .extrude, .altitudemode
        simplekml uses its own special syntax rules and logic that makes this syntax valid.
        Just disable the warning in pyright.**
        """

        ls.coords = pts  # type: ignore

        ls.extrude = 0  # pyright: ignore[reportAttributeAccessIssue]

        ls.altitudemode = (
            simplekml.AltitudeMode.relativetoground
        )  # pyright: ignore[reportAttributeAccessIssue]

        ls.style.linestyle.width = 3

        if category == "science":

            ls.style.linestyle.color = simplekml.Color.green

        else:

            ls.style.linestyle.color = simplekml.Color.gray

    """
    Section #4: Markers at POI's
    """

    # Establish each POI
    launch_marker = kml.newpoint(name=plan.mission_request.launch_wp.action)

    land_marker = kml.newpoint(name=plan.mission_request.land_wp.action)

    m1_marker = kml.newpoint(name=plan.mission_request.m1_wp.action)

    # Set the coordinates and altitude of each POI
    launch_marker.coords = [  # pyright: ignore[reportAttributeAccessIssue]
        (
            plan.mission_request.launch_wp.longitude,
            plan.mission_request.launch_wp.latitude,
            plan.mission_request.launch_wp.altitude,
        )
    ]

    land_marker.coords = [  # pyright: ignore[reportAttributeAccessIssue]
        (
            plan.mission_request.land_wp.longitude,
            plan.mission_request.land_wp.latitude,
            plan.mission_request.land_wp.altitude,
        )
    ]

    m1_marker.coords = [  # pyright: ignore[reportAttributeAccessIssue]
        (
            plan.mission_request.m1_wp.longitude,
            plan.mission_request.m1_wp.latitude,
            plan.mission_request.m1_wp.altitude,
        )
    ]

    # Set the altitude mode of each POI
    launch_marker.altitudemode = (
        simplekml.AltitudeMode.relativetoground
    )  # pyright: ignore[reportAttributeAccessIssue]

    land_marker.altitudemode = (
        simplekml.AltitudeMode.relativetoground
    )  # pyright: ignore[reportAttributeAccessIssue]

    m1_marker.altitudemode = (
        simplekml.AltitudeMode.relativetoground
    )  # pyright: ignore[reportAttributeAccessIssue]

    # Set the styling of each POI
    launch_marker.style.iconstyle.color = simplekml.Color.green

    land_marker.style.iconstyle.color = simplekml.Color.red

    m1_marker.style.iconstyle.color = simplekml.Color.coral

    """
    Section #5: Save and return
    """

    kml.save(path=path)

    return path


def write_png(plan: CandidatePlan, out_dir: str = "EMPTY"):

    # The png writer has the same spine as the kml writer, only differences
    # are output type dependent.

    # Step 0, establish the png infrastructure by calling the helpers

    route = _route_coords(plan)

    segments = _segments_by_action(route)

    path = _output_path(plan.name, CONST.EXTENSION_PNG, out_dir)

    pois = _poi_markers(plan)

    geo_bounds = _route_extent(route)

    # Step 1: establish the plot for the png and set its bounds and settings

    figures, axes = plt.subplots(figsize=(8, 8))

    axes.set_aspect(1 / math.cos(math.radians(CONST.M1_MOORING_LAT)))

    axes.set_xlabel("Longitude")

    axes.set_ylabel("Latitude")

    lower_lon, upper_lon, lower_lat, upper_lat = geo_bounds

    # Margin must be a fraction of the SPAN, not of the coordinate value.
    # (lon ~ -121.9, so lon * 0.05 would shove the view ~6 degrees sideways.)
    lon_margin = (upper_lon - lower_lon) * CONST.PNG_PLOTTING_MARGIN
    lat_margin = (upper_lat - lower_lat) * CONST.PNG_PLOTTING_MARGIN

    axes.set_xlim(lower_lon - lon_margin, upper_lon + lon_margin)
    axes.set_ylim(lower_lat - lat_margin, upper_lat + lat_margin)

    # Step 2: draw the route on the PNG, one polyline per segment:

    seen_cats = set()

    for category, points in segments:

        # each segment is its OWN list of (lon, lat) points -> unpack per segment
        xs = [pt[0] for pt in points]
        ys = [pt[1] for pt in points]

        color = _png_color(category)

        # label each category only once so the legend isn't flooded
        if category not in seen_cats:
            label = category
        else:
            label = None

        axes.plot(xs, ys, color=color, linewidth=1.5, label=label)

        seen_cats.add(category)

    # Step 3: Draw the markers:

    # _poi_markers labels each POI with its waypoint ACTION, so the style dict
    # must be keyed on the action strings (M1's action is "m1_overflight",
    # not "M1") or every M1 marker would KeyError.
    style = {
        CONST.WAYPOINT_ACTION_LAUNCH: ("^", "green"),
        CONST.WAYPOINT_ACTION_LAND: ("v", "red"),
        CONST.WAYPOINT_ACTION_M1_OVERFLIGHT: ("*", "coral"),
    }

    # alt has to be unpacked but it is not used
    for label, lon, lat, alt in pois:

        symbol, color = style[label]

        axes.scatter(lon, lat, marker=symbol, c=color, s=120, label=label, zorder=5)

    # Step 4: Sun Arrow visualizer:

    sun_az = plan.sun_state.azimuth

    span = max((upper_lon - lower_lon), (upper_lat - lower_lat))

    dx, dy = _sun_vector(sun_az, length=(0.15 * span))

    axes.annotate(
        "",
        xy=(
            (plan.mission_request.m1_wp.longitude + dx),
            (plan.mission_request.m1_wp.latitude + dy),
        ),
        xytext=(
            plan.mission_request.m1_wp.longitude,
            plan.mission_request.m1_wp.latitude,
        ),
        arrowprops=dict(color="orange", width=2),
    )

    # text() needs (x, y, string); anchor the label at the sun-arrow tip.
    axes.text(
        plan.mission_request.m1_wp.longitude + dx,
        plan.mission_request.m1_wp.latitude + dy,
        f"sun azimuth: {sun_az:.0f} deg",
        color="orange",
    )

    # Step 5: Put the title, Legend, and Grid

    axes.set_title(f"{plan.name}\nCaption Values in Order (L -> R): Chosen Orientation, Plan Score, Grid Area (m^2), Total Line Number, Plan Duration (minutes), Battery Margin Remaining (%)\n{_metrics_caption(plan)}")

    axes.legend(loc="best")

    axes.grid(True, alpha=0.3)

    # Save the figure and return the path

    figures.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(figures)

    return path
