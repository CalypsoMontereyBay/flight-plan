"""
For the second build of the engine, this file will hold all of the constants used/assumed.

    1. We use these assumed "constants" in order to avoid magic numbers and assist the user.

    2. We will be assuming the aircraft type, and therefore, its properties.

    3. We will no longer be assuming constant date and time, but other constants to assist in dynamic dating will exist.

    4. The coordinates of the M1 Mooring station are also found here and will be used
    even after the first version of the engine works.

    5. Legal status is no longer assumed to be true in V2.

    6. Flight path constants like altitude, line lengths, etc are also found here for now.

    7. Wind is now a feature being accounted for in our dynamic weather, any related constants will be put here.
"""

# M1 Mooring station coordinates are defined below:

M1_MOORING_LONG = -122.020
M1_MOORING_LAT = 36.750

# Launch point coordinate constants (Closest point to M1 station.)
V1_LAUNCH_POINT_LONG = -121.936
V1_LAUNCH_POINT_LAT = 36.637

# Land point coordinate constants (Beach near launch point.)

V1_LAND_POINT_LONG = -121.938
V1_LAND_POINT_LAT = 36.634

# Engine Version 2 constants are defined below:

#Local date/time defaults if user does not specify:

V2_DEFAULT_MISSION_LOCAL_HOUR = 10 #10 AM PT

V2_DEFAULT_MISSION_LOCAL_MINUTE = 0

V1_DEFAULT_MISSION_DAY_OF_MONTH = 1

V1_DEFAULT_MISSION_YEAR = 2026

V1_DEFAULT_MISSION_MONTH = 1

V2_MISSION_INPUT_TIMEZONE = "America/Los_Angeles" #String used in ZoneInfo

#--------------------------------------------

V1_POINTS_PER_LINE = 5

V1_DEFAULT_MISSION_CLOUD_COVER = 0  # Units = %

V1_DEFAULT_LEGAL_STATUS = True

V1_DEFAULT_AIRCRAFT_ALTITUDE_m = 609.6  # Units = m. 609.6m = 2000 FT exactly.
# NOTE: 2000 FT AGL is ABOVE the Part 107 ceiling of 400 FT. validator.py (V2 step E)
# must gate on the ceiling this mission is actually authorized for, not on 400 by default.

V1_DEFAULT_LAND_ALTITUDE_m = 0 #Units = m. 

V1_DEFAULT_LINE_LENGTH_km = 2  # Units = km. 2 km = ~6562 FT.

V1_DEFAULT_LINE_SPACING_km = 0.15  # Units = km. 0.15 km = ~500 FT.

V1_DEFAULT_GRID_WIDTH_km = 3.2187  # Units = km. 3.2187 km = 2.00 MI -> ~10560 FT.
# NOTE: currently DECLARED BUT NEVER READ. The grid is sized from the endurance budget
# in geo._initial_total_lines_from_budget, not from this width. Changing this value has
# no effect on a plan until a width cap is actually wired into the grid builder.

"""
V1_EMERGENCY_RESERVE_FRACTION = (
    0.15  # 15% battery/distance reserve held as a hard limit.
)

**NOTE** RETIRED AS OF CFE V2C-2!!!! SEE RTH_SEED_RESERVE_FRACTION
"""

# FOV values are AIRFRAME-RELATIVE, not camera-relative: "cross-track" means across the
# ground track regardless of how the camera body is bolted on. Which airframe axis is
# TILTED is recorded by V2_SENSOR_MOUNTING below and decides which formula geo.py uses
# for each axis -- see the MOUNTING NOTE at the top of geo.py before changing either.
# PROVISIONAL: these are still the Grey Paper payload numbers. The SST camera is now a
# FLIR Boson (Teledyne), unconfirmed; its lens FOV will change both values.

V1_DEFAULT_SENSOR_CROSS_TRACK_FOV_deg = 48  # Units = degrees. Across the ground track.

V1_COLLECTION_INSET_m = 52 #Units = meters. Rollout-of-turn and settle distance after a turn before data collection starts.

V1_DEFAULT_SENSOR_ALONG_TRACK_FOV_DEG = 36.8  # Units = degrees. Along the ground track (the TILTED axis).

V1_DEFAULT_SENSOR_OFF_NADIR_deg = 30  # Units = degrees. Camera pitched forward under the nose.

V1_DEFAULT_OVERLAP_PCT = 50  # Units = %. Side-lap between adjacent science swaths.
# 50% also buys margin against crab-induced strip shear: at the 15 deg tolerance the
# imaged strip shifts ~182 m between opposite-direction legs, leaving ~131 m of true overlap.

PNG_PLOTTING_MARGIN = 0.05 # Units = degrees. Allows for axis plotting with a 5 percent margin on each side

# Engine Version 1 aircraft defaults are defined below:

# AIRCRAFT PARAMS ARE DEFINED WITH RESPECT TO THE BLACKSWIFT S2 FIXED-WING UAV

BLACKSWIFT_ENDURANCE_min = 90  # Units = minutes

BLACKSWIFT_WIND_RATING_ms = 15  # Units = m/s

BLACKSWIFT_CLIMB_RATE_ms = 3.35  # Units = m/s

BLACKSWIFT_DESCENT_RATE_ms = 1.80  # Units = m/s

BLACKSWIFT_TURN_RADIUS_m = 57  # Units = m

BLACKSWIFT_TURN_PENALTY_s = 10  # Units = seconds

BLACKSWIFT_MIN_GROUND_SPEED_ms = 12  # Units = m/s

BLACKSWIFT_CRUISE_SPEED_ms = 18  # Units = m/s

# NATIONAL WEATHER SERVICE API CONSTANTS BELOW:

NWS_BASE_URL = "https://api.weather.gov"
NWS_USER_AGENT = "Calypso Flight Engine (rwandel@ucsc.edu)"
NWS_REQUEST_TIMEOUT_s = 10 #CFE will wait for 10 seconds before bailing
NWS_MAX_RETRIES = 1 #CFE will retry the api request once before bailing
NWS_ACCEPT_HEADER = "application/geo+json" #NWS api output formatting
NWS_FORECAST_HORIZON_days = 7 #NWS forecasting horizon
WEATHER_SOURCE_NWS = "NWS" #tags a Weather object as live NWS data (vs the "STUB" fallback)
WEATHER_SOURCE = "NWS"


# WEATHER OBJECT AND API CONSTANTS FOR V1 ARE LISTED BELOW:

DEFAULT_ZERO_WIND = 0  # Units = m/s

CLEAR_SKY_THRESHOLD_PERCENTAGE = 95  # Units = % (When 95% or more of the sky is clear, the engine considers the sky clear)

OVERCAST_SKY_THRESHOLD_PERCENTAGE = 85  # Units = % (When 85% or more of the sky is clouded, the engine considers the sky overcast)

DEFAULT_WIND_DIRECTION_deg = None

DEFAULT_WIND_GUST_ms = 0

DEFAULT_VISIBILITY_m = 16100  # ~10 miles (METAR reports max out at +10 SM)

DEFAULT_WEATHER_CONDITION = "clear"

KMH_TO_MS = 1/3.6 # conversion factor for wind speed

# WAYPOINT DEFAULTS AND ACTION CONSTANTS HERE:

WAYPOINT_ACTION_LAUNCH = "launch"
WAYPOINT_ACTION_TRANSIT = "transit"
WAYPOINT_ACTION_SCIENCE = "science"
WAYPOINT_ACTION_M1_OVERFLIGHT = "m1_overflight"
WAYPOINT_ACTION_TURN = "turn"
WAYPOINT_ACTION_LAND = "land"
WAYPOINT_ACTION_COLLECT_START = "collect_start"
WAYPOINT_ACTION_COLLECT_STOP = "collect_stop"
WAYPOINT_ACTION_LINE_LABEL = "line_label"

# SENSOR ACTIONS AND MOUNTING CONSTANTS:

SENSOR_MOUNT_ALONG_TRACK = "along_track"
SENSOR_MOUNT_CROSS_TRACK = "cross_track"
V2_SENSOR_MOUNTING = SENSOR_MOUNT_ALONG_TRACK
V2_SENSOR_NAME = "FLIR Boson -- PROVISIONAL"



# Azimuth Constant for planner.py:

SCIENCE_RELATIVE_AZIMUTH_deg = 90 # Units = degrees.

AZIMUTH_THREE_SIXTY = 360  # Units = degrees.

DEGREE_ONE_EIGHTY = 180 # Units = degrees

DEGREE_NINETY = 90 #Units = degrees

FULL_CIRCLE_DEG = 360 #Units = degrees, second 360 for readability when not dealing with azimuth


#Glint "Gate threshold" for proper ranking purposes

V1_GLINT_TOLERANCE_DEG = 15 # Units = degrees. Max allowed deviation of the science line from the ideal 90 before a plan is rejected
# Held at 15 rather than tightened to 10 for V2C: the camera boresight follows the FUSELAGE,
# so crosswind crab spends this budget before the grid geometry gets any of it. 15 deg allows
# ~4.66 m/s of crosswind across the science axis at cruise; 10 deg would allow only 3.13 m/s.
# V2C-2 turns that relationship into a real feasibility gate.

OUTPUT_DIRECTORY = "./CALYPSO_OUTPUT"

EXTENSION_KML = "kml"

EXTENSION_PNG = "png"

#FOR V2 ONLY:

EXTENSION_JSON = "json"

# V2C-2 EMERGENCY CONSTANTS AND RTH CONSTANTS:

RTH_SAFETY_FACTOR = 1.25 # See explanation below
"""
Manual operation of a UAS vs. Autopilot is far less efficient. However,
it is paramount that a human operator has the ability to assume manual control
in the event of an emergency. That being said, humans aren't perfect. This safety factor
is multipled with the derived minimum amount of battery needed to make it safely home
from anywhere on the route, fully manually.
"""

RTH_TERMINAL_ALLOWANCE_min = 3.0 # flight time set aside for go-arounds/pattern once above landing location.

MANUAL_RTH_MAX_CROSSWIND_ms = 7.5 # Units: m/s. Half the aircraft's autopilot wind rating, but ultimately pilot dependent

RTH_INCLUDES_GLIDE = False # RTH procedures never lack thrust from the motors.

RTH_SEED_RESERVE_FRACTION = 0.15 #Fixed point iteration seed for calculating emergency flight distances and RTH feasability.

RTH_MAX_ITERATIONS = 12 #Prevents the engine from creating a grid whose derived RTH battery time blows up so high that no grid fits.
