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

V1_DEFAULT_AIRCRAFT_ALTITUDE_m = 118  # Units = m. 118m = ~385 FT.

V1_DEFAULT_LAND_ALTITUDE_m = 0 #Units = m. 

V1_DEFAULT_LINE_LENGTH_km = 2  # Units = km. 2 km = ~6562 FT.

V1_DEFAULT_LINE_SPACING_km = 0.15  # Units = km. 0.15 km = ~500 FT.

V1_DEFAULT_GRID_WIDTH_km = 2.5  # Units = km. 2.5 km = ~1.55 MI -> ~8202 FT.

V1_EMERGENCY_RESERVE_FRACTION = (
    0.15  # 15% battery/distance reserve held as a hard limit.
)

V1_DEFAULT_SENSOR_CROSS_TRACK_FOV_deg = 48  # Units = degrees. USING PAYLOAD FROM GREY PAPER

V1_COLLECTION_INSET_m = 52 #Units = meters. Rollout-of-turn and settle distance after a turn before data collection starts.

V1_DEFAULT_SENSOR_ALONG_TRACK_FOV_DEG = 36.8  # Units = degrees. USING PAYLOAD FROM GREY PAPER

V1_DEFAULT_SENSOR_OFF_NADIR_deg = 40  # Units = degrees.

V1_DEFAULT_OVERLAP_PCT = 30  # Units = %. Placeholder until science overlap requirement is known.

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


# WEATHER OBJECT AND API CONSTANTS FOR V1 ARE LISTED BELOW:

NWS_BASE_URL = "https://api.weather.gov"
# NWS_USER_AGENT =

DEFAULT_ZERO_WIND = 0  # Units = m/s

CLEAR_SKY_THRESHOLD_PERCENTAGE = 95  # Units = % (When 95% or more of the sky is clear, the engine considers the sky clear)

OVERCAST_SKY_THRESHOLD_PERCENTAGE = 85  # Units = % (When 85% or more of the sky is clouded, the engine considers the sky overcast)

DEFAULT_WIND_DIRECTION_deg = None

DEFAULT_WIND_GUST_ms = 0

DEFAULT_VISIBILITY_m = 16100  # ~10 miles (METAR reports max out at +10 SM)

DEFAULT_WEATHER_CONDITION = "clear"

DEFAULT_WEATHER_SOURCE = "V1Stub"

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



# Azimuth Constant for planner.py:

AZIMUTH_ONE_THIRTY_FIVE = 135  # Units = degrees.

AZIMUTH_THREE_SIXTY = 360  # Units = degrees.

AZIMUTH_TWO_TWENTY_FIVE = 225  # Units = degrees. 360 - 135, mirror of the ideal offset.

DEGREE_ONE_EIGHTY = 180 # Units = degrees

DEGREE_NINETY = 90 #Units = degrees

FULL_CIRCLE_DEG = 360 #Units = degrees, second 360 for readability when not dealing with azimuth


#Glint "Gate threshold" for proper ranking purposes

V1_GLINT_TOLERANCE_DEG = 15 # Units = degrees. Max allowed deviation of the science line from the ideal 135 before a plan is rejected

OUTPUT_DIRECTORY = "./CALYPSO_OUTPUT"

EXTENSION_KML = "kml"

EXTENSION_PNG = "png"

#FOR V2 ONLY:

EXTENSION_JSON = "json"