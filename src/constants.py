"""
For the first build of the engine, this file will hold all of the constants used/assumed.

    1. We use these assumed "constants" in order to prove the engine works.

    2. We will be assuming the aircraft type, and therefore, its properties.

    3. We will also be assuming permanently clear skies on January 1st 2026 for now.

    4. The coordinates of the M1 Mooring station are also found here and will be used
    even after the first eversion of the engine works.

    5. Legal status for now is assumed to be true (Legal).

    6. Flight path constants like altitude, line lengths, etc are also found her for now.

    7. We are also ignoring wind in version 1.
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

# Engine Version 1 constants are defined below:

V1_DEFAULT_MISSION_DAY_OF_MONTH = 1

V1_DEFAULT_MISSION_NAME = "v1_m1_test"

V1_DEFAULT_MISSION_YEAR = 2026

V1_DEFAULT_MISSION_MONTH = 1

V1_DEFAULT_MISSION_HOUR = 18  # Units: 24hr clock in UTC, we are assuming a mission start time of 10 am.



V1_DEFAULT_MISSION_CLOUD_COVER = 0  # Units = %

V1_DEFAULT_LEGAL_STATUS = True

V1_DEFAULT_AIRCRAFT_ALTITUDE_m = 118  # Units = m. 118m = ~385 FT.

V1_DEFAULT_LINE_LENGTH_km = 2  # Units = km. 2 km = ~6562 FT.

V1_DEFAULT_LINE_SPACING_km = 0.15  # Units = km. 0.15 km = ~500 FT.

V1_DEFAULT_GRID_WIDTH_km = 2.5  # Units = km. 2.5 km = ~1.55 MI -> ~8202 FT.

V1_EMERGENCY_RESERVE_FRACTION = (
    0.15  # 15% battery/distance reserve held as a hard limit.
)

V1_DEFAULT_SENSOR_CROSS_TRACK_FOV_deg = 48  # Units = degrees. USING PAYLOAD FROM GREY PAPER


V1_DEFAULT_SENSOR_ALONG_TRACK_FOV_DEG = 36.8  # Units = degrees. USING PAYLOAD FROM GREY PAPER

V1_DEFAULT_SENSOR_OFF_NADIR_deg = 40  # Units = degrees.

V1_DEFAULT_OVERLAP_PCT = 30  # Units = %. Placeholder until science overlap requirement is known.

# Engine Version 1 aircraft defailts are defined below:

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

DEFAULT_CLOUD_COVER = 0  # Units = %

DEFAULT_ZERO_WIND = 0  # Units = m/s

MAX_ACCEPTABLE_WIND = 15  # Units = m/s (Same as UAV wing rating)

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

# Azimuth Constant for planner.py:

AZIMUTH_ONE_THIRTY_FIVE = 135  # Units = degrees.

AZIMUTH_THREE_SIXTY = 360  # Units = degrees.

AZIMUTH_TWO_TWENTY_FIVE = 225  # Units = degrees.
