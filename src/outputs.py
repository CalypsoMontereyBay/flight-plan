"""
The outputs.py file takes the data from our candidate plan and produces
human readable output. V1 produces two artifacts: a KML file and a PNG file.

⚠️ 2026-09-08 -- THE QGC ".plan" (JSON) WRITER IS THE ENGINE'S TOP PRIORITY (Step J), and
it belongs in this file alongside write_kml / write_png. EXTENSION_JSON already exists.
Everything else on the V2 roadmap is sidelined until it ships, because a KML is
visualization-only in QGC: today this engine cannot emit anything that can be uploaded and
flown. A fourth artifact -- a PILOT-NOTES document carrying the wind / crab / return-time
reporting -- is planned alongside it, deliberately kept OUT of the machine-readable outputs.

KML's can be uploaded to QGroundControl, BlackSwift's FMS, or Google Earth.

PNG's simply exist as a visual reference for the RPIC and do not serve any other
purpose.

This file does not check if output is "correct", it is simply a black box
that takes the data the engine produces and produces output.

This follows my design of "dumb unidirectionality", meaning that files
are only as knowledgeable of the rest of the program as they have to be
and the engine's pipeline follows a linear, unidirectional computational flow.

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
import json

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
==      SECTION 0: SHARED HELPERS (used by BOTH the KML and PNG writers)  ==
============================================================================
"""


# Walks the candidate plan's route into (lon, lat, alt, action) tuples.
# Shared spine consumed by BOTH write_kml and write_png.
def _route_coords(plan: CandidatePlan):

    # One (lon, lat, alt, action) tuple per waypoint, in flight order.
    kml_wp_list = []
    for point in plan.waypoints:

        # Each element in the list is a tuple containing a given waypoint's coordinates, altitude,
        # and action.
        kml_wp = (point.longitude, point.latitude, point.altitude, point.action)
        kml_wp_list.append(kml_wp)

    return kml_wp_list


def _segment_builder(route: list):

    collecting = False
    current_category = CONST.WAYPOINT_ACTION_TRANSIT
    current_pts = []
    segments = []

    for lon, lat, alt, action in route:

        point = (lon, lat)

        if action == CONST.WAYPOINT_ACTION_COLLECT_START and not collecting:

            current_pts.append(point)   #append the last gray point
            segments.append((current_category, current_pts))

            collecting = True   #starting collection
            current_category = CONST.WAYPOINT_ACTION_SCIENCE

            current_pts = [point]   #The first green point

        elif action == CONST.WAYPOINT_ACTION_COLLECT_STOP and collecting:

            current_pts.append(point)   #append the last green point
            segments.append((current_category, current_pts))

            collecting = False  #stopping collection
            current_category = CONST.WAYPOINT_ACTION_TRANSIT

            current_pts = [point]   #The first gray point
            
        else:
            current_pts.append(point) #add everything else
            
    #flush final run:
    #Do not put inside the loop: will append the list to itself, balooning the number of line segments incorrectly
    if current_pts:
        segments.append((current_category,current_pts))

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

    return f"{plan.chosen_orientation:.2f}, {plan.score:.2f}, {plan.grid_area_m2:.4f}, {plan.total_lines}, {plan.duration:.2f}, {plan.margin:.2f}"


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
    # has occurred and the helper receives an empty route list.
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


# Maps a segment category to a matplotlib color for the PNG route.
# NOTE: write_kml does NOT call this -- it applies simplekml.Color directly.
# Keeping the science=green / transit=gray choice here documents the shared
# color convention in one place so the two outputs stay visually consistent.
def _png_color(category: str):

    if category == CONST.WAYPOINT_ACTION_SCIENCE:

        return "green"

    else:

        return "gray"


# converts azimuth to a (dx, dy) for PNG arrow denoting sun position/angle
def _sun_vector(sun_az_deg, length, latitude_deg):

    # math.sin/cos expect RADIANS; azimuth comes in as degrees (0 = north,
    # clockwise), so convert first. dx uses sin, dy uses cos so the arrow
    # points along the compass bearing with north = +y.
    sun_az_rad = math.radians(sun_az_deg)

    # LATITUDE CORRECTION: dx/dy are DEGREES of lon/lat, and a degree of longitude
    # is shorter on the ground than a degree of latitude by cos(lat). The axes carry
    # the matching aspect (1/cos(lat)), so without dividing dx by cos(lat) the arrow
    # renders ~5.5 deg off true at Monterey -- it drew the sun-to-track angle as 84.5
    # deg when the plan actually holds 90.0. The flight lines are unaffected because
    # they are real geodesic points; only this synthetic vector needed the correction.
    dx = (length * math.sin(sun_az_rad)) / math.cos(math.radians(latitude_deg))

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

    # _segment_builder expects the (lon, lat, alt, action) tuples from
    # _route_coords -- NOT raw Waypoint objects (those aren't subscriptable).
    segments = _segment_builder(route)

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

    # J-6 WARNING GATE: kml.save() opens its file with codecs.open(), which Python 3.14
    # deprecates, so every write_kml run printed a DeprecationWarning. kml.kml() returns the
    # exact string save() writes, so we write it ourselves instead: UTF-8, and newline="" so
    # line endings stay "\n" on Windows too, exactly as save()'s binary-mode write left them.
    with open(path, "w", encoding="utf-8", newline="") as kml_file:
        kml_file.write(kml.kml())

    return path


def write_png(plan: CandidatePlan, out_dir: str = "EMPTY"):

    # The png writer has the same spine as the kml writer, only differences
    # are output type dependent.

    # Step 0, establish the png infrastructure by calling the helpers

    route = _route_coords(plan)

    segments = _segment_builder(route)

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

    dx, dy = _sun_vector(
        sun_az,
        length=(0.15 * span),
        latitude_deg=plan.mission_request.m1_wp.latitude,
    )

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

    axes.set_title(
        f"{plan.name}\nCaption Values in Order (L -> R): Chosen Orientation, Plan Score, Grid Area (m^2), Total Line Number, Plan Duration (minutes), Battery Margin Remaining (mins)\n{_metrics_caption(plan)}"
    )

    axes.legend(loc="best")

    axes.grid(True, alpha=0.3)

    # Save the figure and return the path

    figures.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(figures)

    return path


"""
============================================================================
==                   SECTION 2: JSON HELPERS + WRITER                     ==
============================================================================
"""

# Maps out the "items" of the flight to then
# be translated using the QGC constants and turned into JSON.

# Since many waypoints in a QGC plan are just navigational waypoints,
# this helper makes the loop quicker and easier to read.

"""
ITEM SHAPE:

1. ALL ITEMS CONTAIN AT LEAST THE FOLLOWING: {Keyword, Alt_Frame_Ref, Source_Action}

2. POSITIONAL ITEMS ALSO CONTAIN {..., Latitude, Longitude, Altitude (meters)}

3. CAMERA ITEMS CONTAIN {..., Trigger Distance (meters)} INSTEAD

**NOTE** MAVLINK protocol does not require position info for camera commands.
"""


# Helper function to define the most standard waypoint a CFE plan
# can have in a vehicle neutral fassion 
def _nav(wp: Waypoint):
    
    return {
        "Keyword": "nav",
        "Alt_Frame_Ref": "AMSL",
        "Latitude": wp.latitude,
        "Longitude": wp.longitude,
        "Altitude_m": wp.altitude        
    }

# Walks the waypoints and builds a vehicle neutral "translation layer"
# dict that is used to build the parameter arrays for each MAVLINK command
# in the function below, once a vehicle is identified.
def _plan_items(plan: CandidatePlan):
    
    planned_items = []

    for wp in plan.waypoints:
        
        if wp.action == CONST.WAYPOINT_ACTION_LAUNCH:
            items = [{"Keyword": "takeoff", "Alt_Frame_Ref": "RELATIVE",
                     "Latitude": wp.latitude, "Longitude": wp.longitude,
                     "Altitude_m": CONST.TAKEOFF_REL_m}]
            
        elif wp.action == CONST.WAYPOINT_ACTION_LAND:
            items = [{"Keyword": "land", "Alt_Frame_Ref": "RELATIVE",
                    "Latitude": wp.latitude, "Longitude": wp.longitude,
                    "Altitude_m": CONST.LANDING_REL_m}]
            
        elif wp.action == CONST.WAYPOINT_ACTION_COLLECT_START:
            items = [_nav(wp), 
                     {"Keyword": "cam_on", "Alt_Frame_Ref": "MISSION",
                      "Trigger_Distance_m": plan.camera_trigger_distance_m}]
        
        elif wp.action == CONST.WAYPOINT_ACTION_COLLECT_STOP:
            items = [_nav(wp), 
                    {"Keyword": "cam_off", "Alt_Frame_Ref": "MISSION",
                    "Trigger_Distance_m": 0}]
        
        else:
            items = [_nav(wp)]
            
        for item in items:
            item["Source_Action"] = wp.action
            
        planned_items.extend(items)
        
    return planned_items



# Builds the parameter array for a QGC command when called, depending on the vehicle type:

def _qgc_params(item, is_vtol):
    
    keyword = item["Keyword"]
    
    if keyword == "takeoff":
        if is_vtol:
            return [0, CONST.TRANSITION_HEADING_SETTING, 0, CONST.TRANSITION_YAW_deg, 
                    item["Latitude"], item["Longitude"], item["Altitude_m"]]

        else:
            return [CONST.TAKEOFF_PITCH_deg, 0, 0, CONST.TAKEOFF_YAW_deg,
                    item["Latitude"], item["Longitude"], item["Altitude_m"]]
            
    if keyword == "land":
        if is_vtol:
            return [CONST.LANDING_BEHAVIOR, 0, CONST.APPROACH_AMSL_m, CONST.VTOL_LANDING_YAW_deg,
                    item["Latitude"], item["Longitude"], item["Altitude_m"]]
            
        else:
            return [CONST.ABORT_REL_m, 0, 0, CONST.LAND_YAW_deg,
                    item["Latitude"], item["Longitude"], item["Altitude_m"]]
            
    if keyword in ("cam_on", "cam_off"):
        
        on_off_toggle = (CONST.CAM_TRIGGER_START if keyword == "cam_on" else CONST.CAM_TRIGGER_END)
        
        return [item["Trigger_Distance_m"], CONST.CAM_SHUTTER_INTEGRATION_millis, on_off_toggle, CONST.TARGET_CAM_ID,
                0, 0, 0]
        
    if keyword == "nav":
        return [CONST.HOLD_TIME_s, CONST.ACCEPTANCE_RADIUS_m, CONST.PASS_RADIUS_m, CONST.WP_YAW_deg,
                item["Latitude"], item["Longitude"], item["Altitude_m"]]
        
    
    raise ValueError(f"Invalid Keyword detected: {keyword}.")
        
        
'''
========================================================================================
'''

# Below are QGC Lookup Tables to link CFE Waypoint Keywords 

# TABLE #1: Keyword -> Command:

# Order: "Keyword" : (Non_VTOL, VTOL)

_QGC_COMMAND = {
    
    "nav": (CONST._QGC_CMD_NAV_WAYPOINT, CONST._QGC_CMD_NAV_WAYPOINT),
    
    "takeoff": (CONST._QGC_CMD_NAV_TAKEOFF, CONST._QGC_CMD_VTOL_TAKEOFF),
    
    "land": (CONST._QGC_CMD_NAV_LAND, CONST._QGC_CMD_VTOL_LAND),
    
    "cam_on": (CONST._QGC_CMD_DO_SET_CAM_TRIGGER_DIST, CONST._QGC_CMD_DO_SET_CAM_TRIGGER_DIST),
    
    "cam_off": (CONST._QGC_CMD_DO_SET_CAM_TRIGGER_DIST, CONST._QGC_CMD_DO_SET_CAM_TRIGGER_DIST)
    
}

# TABLE #2: Alt_Frame_Ref -> (MAV_FRAME, QGC AltitudeMode):

# Two different enums that both use small integers -- this table is the one place they meet.
# None = omit the AltitudeMode key entirely (camera items have no altitude to describe).

# **NOTE** "AMSL" is the CRUISE row. _CRUISING_MISSION_ALT_FRAME is named for the cruise leg of
# the mission, and is NOT MAV_FRAME_MISSION -- that one is _QGC_MAV_FRAME_MISSION, used only by
# the camera items.

_QGC_ALT_FRAME = {

    "RELATIVE": (CONST._TAKEOFF_LANDING_ALT_FRAME, CONST._TAKEOFF_LAND_ALT_MODE),

    "AMSL": (CONST._CRUISING_MISSION_ALT_FRAME, CONST._CRUISING_MISSION_ALT_MODE),

    "MISSION": (CONST._QGC_MAV_FRAME_MISSION, None)
}

'''
========================================================================================
'''

# Builds a QGC SimpleItem for plugging into the JSON.
# Built field by field into a NEW dict, so nothing of ours (Source_Action) can reach the file.

def _qgc_item(item, jump_id, is_vtol):

    alt_frame, alt_mode = _QGC_ALT_FRAME[item["Alt_Frame_Ref"]]

    qgc_item = {
        "AMSLAltAboveTerrain": CONST._QGC_AMSL_ALT_ABOVE_TERRAIN,
        "Altitude": item.get("Altitude_m", 0),  # camera items carry no altitude -> 0
        "autoContinue": CONST._QGC_AUTOCONTINUE,
        "command": _QGC_COMMAND[item["Keyword"]][1 if is_vtol else 0],
        "doJumpId": jump_id,
        "frame": alt_frame,
        "params": _qgc_params(item, is_vtol),
        "type": CONST._QGC_SIMPLE_ITEM
    }

    # Omit the key rather than writing null: camera items have no altitude to give a mode to.
    if alt_mode is not None:
        qgc_item["AltitudeMode"] = alt_mode

    return qgc_item

# Home is wherever THIS plan takes off -- never a fixed site, so a boat launch gets its own home.
# The altitude is the pad's AMSL; Step F makes launch elevation part of the launch point.

def _qgc_home(items):

    takeoff = next((i for i in items if i["Keyword"] == "takeoff"), None)

    if takeoff is None:
        raise ValueError("No takeoff item, therefore no home position")

    return [takeoff["Latitude"], takeoff["Longitude"], CONST.TERRACE_POINT_AMSL_m]

# Returns the entire plan to be written to a .plan file.
# Reads the neutral item list and calls the _qgc_item helper to build
# waypoints.

def _serialize_qgc(plan: CandidatePlan, items):
    
    is_vtol = plan.aircraft.is_VTOL

    return {
        "fileType": CONST._QGC_FILETYPE,
        "geoFence": CONST._QGC_GEOFENCE,
        "groundStation": CONST._QGC_GROUNDSTATION,
        "mission": {
            "cruiseSpeed": plan.aircraft.vehicle_cruise_speed,
            "firmwareType": plan.aircraft.firmware_type,
            "globalPlanAltitudeMode": CONST._QGC_GLOBAL_PLAN_ALTITUDE_MODE,
            "hoverSpeed": plan.aircraft.hover_speed_ms,
            # doJumpId is position in THIS file: 1-based, contiguous
            "items": [_qgc_item(item, n, is_vtol) for n, item in enumerate(items, start=1)],
            "plannedHomePosition": _qgc_home(items),
            "vehicleType": plan.aircraft.vehicle_type,
            "version": CONST._QGC_MISSION_VERSION
        },
        "rallyPoints": CONST._QGC_RALLYPOINTS,
        "version": CONST._QGC_VERSION
    }
    
# Writes a QGC plan to disk:

def write_qgc_plan(plan: CandidatePlan, out_dir: str = "EMPTY"):

    path = _output_path(plan.name, CONST.EXTENSION_PLAN, out_dir)

    flight_plan = _serialize_qgc(plan, _plan_items(plan))

    # QGC's own formatting (sorted keys, 4-space indent) keeps a diff against a QGC
    # re-export readable. allow_nan=False: a stray NaN is not valid JSON.
    with open(path, "w", encoding="utf-8") as plan_file:
        json.dump(flight_plan, plan_file, indent=4, sort_keys=True, allow_nan=False)
        
        
    return path