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
# 🔴 STALE AS OF 2026-09-08. The standing default launch/land site is the UCSC Coastal
# Science Campus -- TERRACE POINT, Santa Cruz (north shore):
#
#       36.94840 N,  -122.06538   <- replace BOTH pairs below with this (Step J-1)
#
# LAUNCH AND LAND ARE THE SAME POINT now; the V1 split into a beach launch and a separate
# road landing collapses to one pad. The values below are a SOUTH-shore position 14,615 m
# from M1, while planner's waypoint NAMES already say "Seymour-*" -- names and coordinates
# have disagreed since V1.
#
# Terrace Point measures 22,386 m from M1 (bearing 169.6 deg), 53% further than these
# values encode. Round-trip transit alone is ~44.8 km = ~41.5 min of a 90 min endurance,
# which is what makes the transit-budget defect binding -- see CLAUDE.md, Step J.
V1_LAUNCH_POINT_LONG = -122.06538
V1_LAUNCH_POINT_LAT = 36.94840

# Land point coordinate constants (Beach near launch point.)
# 🔴 Same staleness applies, and these become IDENTICAL to the launch point above.

V1_LAND_POINT_LONG = -122.06538
V1_LAND_POINT_LAT = 36.94840

TERRACE_POINT_AMSL_m = 16

'''
CFE VERSION 2 CONSTANTS ARE DEFINED BELOW:
ASSUMPTIONS REMANING FROM V1 ARE ALSO DEFINED BELOW
========================================================================================
'''

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

V1_DEFAULT_AIRCRAFT_ALTITUDE_m = 609.6  # Units = m. 609.6m = 2000 FT exactly when accounting for takeoff
#elevation.
# NOTE: 2000 FT AGL is ABOVE the Part 107 ceiling of 400 FT. validator.py (V2 step E)
# must gate on the ceiling this mission is actually authorized for, not on 400 by default.

V1_DEFAULT_LAND_ALTITUDE_m = 0 #Units = m. 

V1_DEFAULT_LINE_LENGTH_km = 2  # Units = km. 2 km = ~6562 FT.

V1_DEFAULT_LINE_SPACING_km = 0.15  # Units = km. 0.15 km = ~500 FT.

V1_DEFAULT_GRID_WIDTH_km = 3.2187  # Units = km. 3.2187 km = 2.00 MI -> ~10560 FT.
# NOTE: currently DECLARED BUT NEVER READ. The grid is sized from the endurance budget
# in geo._initial_total_lines_from_budget, not from this width. Changing this value has
# no effect on a plan until a width cap is actually wired into the grid builder.
# ⚠️ 2026-09-08: this and the two length/spacing constants above were removal candidates.
# They are now REINSTATED as the defaults behind user-settable grid dimensions (Step F).
# Do not delete them.

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

V1_DEFAULT_CROSSTRACK_OVERLAP_PCT = 50
V2_DEFAULT_ALONGTRACK_OVERLAP_PCT = 50# Units = %. Side-lap between adjacent science swaths.
# 50% also buys margin against crab-induced strip shear: at the 15 deg tolerance the
# imaged strip shifts ~182 m between opposite-direction legs, leaving ~131 m of true overlap.

'''
========================================================================================
'''

'''
BlackSwift specific constants are below, and should only be used when making plans for
the BlackSwift S2 as of 09/10/2026.
========================================================================================
'''

BLACKSWIFT_ENDURANCE_min = 90  # Units = minutes

BLACKSWIFT_WIND_RATING_ms = 15  # Units = m/s

BLACKSWIFT_CLIMB_RATE_ms = 3.35  # Units = m/s

BLACKSWIFT_DESCENT_RATE_ms = 1.80  # Units = m/s

BLACKSWIFT_TURN_RADIUS_m = 57  # Units = m

BLACKSWIFT_TURN_PENALTY_s = 10  # Units = seconds

BLACKSWIFT_MIN_GROUND_SPEED_ms = 12  # Units = m/s

BLACKSWIFT_CRUISE_SPEED_ms = 18  # Units = m/s

'''
========================================================================================
'''


'''
NWS SERVICE CONSTANTS:
========================================================================================
'''

NWS_BASE_URL = "https://api.weather.gov"
NWS_USER_AGENT = "Calypso Flight Engine (rwandel@ucsc.edu)"
NWS_REQUEST_TIMEOUT_s = 10 #CFE will wait for 10 seconds before bailing
NWS_MAX_RETRIES = 1 #CFE will retry the api request once before bailing
NWS_ACCEPT_HEADER = "application/geo+json" #NWS api output formatting
NWS_FORECAST_HORIZON_days = 7 #NWS forecasting horizon
WEATHER_SOURCE_NWS = "NWS" #tags a Weather object as live NWS data (vs the "STUB" fallback)
WEATHER_SOURCE = "NWS"

'''
========================================================================================
'''

'''
WEATHER OBJECT ASSUMPTIONS FOR TESTING AND IDEAL WEATHER SCENARIOS ARE DEFINED BELOW:
========================================================================================
'''

DEFAULT_ZERO_WIND = 0  # Units = m/s

CLEAR_SKY_THRESHOLD_PERCENTAGE = 95  # Units = % (When 95% or more of the sky is clear, the engine considers the sky clear)

OVERCAST_SKY_THRESHOLD_PERCENTAGE = 85  # Units = % (When 85% or more of the sky is clouded, the engine considers the sky overcast)

DEFAULT_WIND_DIRECTION_deg = None

DEFAULT_WIND_GUST_ms = 0

DEFAULT_VISIBILITY_m = 16100  # ~10 miles (METAR reports max out at +10 SM)
# ⚠️ VISIBILITY IS A SHORT-TERM FORECAST ONLY. NWS publishes visibility for roughly the
# next 8-30 HOURS -- the span is volatile and has been measured as low as 8.7 h -- while
# windSpeed / windDirection / skyCover all run ~176 h and comfortably cover the 7-day
# NWS_FORECAST_HORIZON_days below. So on any plan more than about a day out, visibility is
# NOT a forecast: weather.py marks it in Weather.stale_fields and substitutes this default.
# Never gate VLOS on visibility without first checking Weather.is_stale("visibility") --
# a defaulted 10 miles reads as perfect conditions and is the most permissive possible
# input to a legality check. The horizon stays at 7 days because it fits the WIND fields,
# which are what the RTH safety gate actually consumes.

DEFAULT_WEATHER_CONDITION = "clear"

KMH_TO_MS = 1/3.6 # conversion factor for wind speed

'''
========================================================================================

'''

'''
WAYPOINT ACTION CONSTANTS FOR TRANSLATING BETWEEN CFE LANGUAGE AND QGC JSON VALUES:
========================================================================================

'''

# WAYPOINT DEFAULTS AND ACTION CONSTANTS HERE:
#NOTE: NOT QGC ACTIONS, SIMPLE STRINGS FOR DENOTATION

WAYPOINT_ACTION_LAUNCH = "launch"
WAYPOINT_ACTION_TRANSIT = "transit"
WAYPOINT_ACTION_SCIENCE = "science"
WAYPOINT_ACTION_M1_OVERFLIGHT = "m1_overflight"
WAYPOINT_ACTION_TURN = "turn"
WAYPOINT_ACTION_LAND = "land"
WAYPOINT_ACTION_COLLECT_START = "collect_start"
WAYPOINT_ACTION_COLLECT_STOP = "collect_stop"
WAYPOINT_ACTION_LINE_LABEL = "line_label"

'''
========================================================================================

'''

'''
SENSOR MOUNTING CONSTANTS FOR V2:
========================================================================================

'''

SENSOR_MOUNT_ALONG_TRACK = "along_track"
SENSOR_MOUNT_CROSS_TRACK = "cross_track"
V2_SENSOR_MOUNTING = SENSOR_MOUNT_ALONG_TRACK
V2_SENSOR_NAME = "FLIR Boson -- PROVISIONAL"

'''
========================================================================================
'''

'''
SUN AZIMUTH AND OTHER ANGULAR CONSTANTS:
========================================================================================

'''


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
# ⚠️ 2026-09-08: that crosswind relationship is REPORTED to the RPIC as science-quality
# headroom, never enforced -- the feasibility gate C-2 was going to build is cancelled. This
# constant still gates ORIENTATION SELECTION in planner._passes_glint_gate, which is grid
# geometry vs. the sun and has nothing to do with wind. That use stays.

'''
========================================================================================
'''

'''
OUTPUT CONSTANTS FOR V2:
========================================================================================
'''


OUTPUT_DIRECTORY = "./CALYPSO_OUTPUT"

EXTENSION_KML = "kml"

EXTENSION_PNG = "png"

PNG_PLOTTING_MARGIN = 0.05 # Units = degrees. Allows for axis plotting with a 5 percent margin on each side

#FOR V2 ONLY:

EXTENSION_JSON = "json"

EXTENSION_PLAN = "plan"

'''
========================================================================================
'''

'''
CFE V2C DEPRECATED EMERGENCY AND RTH CONSTANTS:
========================================================================================
'''



# V2C-2 EMERGENCY CONSTANTS AND RTH CONSTANTS:
#
# ⚠️ 2026-09-08: the RTH safety GATE these were sized for is CANCELLED. Aircraft are now
# assumed to sense wind and compensate in flight, so the engine may not reject a plan or
# shrink a grid on wind. RTH_SEED_RESERVE_FRACTION is still read (it is the reserve the
# distance budget uses). The rest are now REPORTING inputs at best -- their fate is decided
# when C-2 resumes as a reporting step. DO NOT DELETE THEM before then: the reasoning behind
# each number is recorded here and in the 2026-08-19 log entry, and re-deriving it is
# expensive. See CLAUDE.md, "Operating constraints -- 2026-09-08".

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

'''
========================================================================================
'''

# ---------------------------------------------------------------------------------------
# V2 J-4: transit-aware grid sizing.
#
# ⚠️ This is NOT an RTH constant and must not be folded into RTH_MAX_ITERATIONS. The RTH
# loop was a WEATHER gate (cancelled 2026-09-08). This one bounds a purely GEOMETRIC
# convergence: planner seeds the grid budget with 2 x d(launch, M1), then re-measures the
# transit against the real entry/exit corners. The seed is accurate to ~0.40% at the
# Terrace Point geometry, so pass 1 almost always fits. Each retry re-seeds with the
# MEASURED transit, which is strictly larger than the estimate that just failed, so the
# budget strictly shrinks and the loop is guaranteed to terminate. 3 is headroom for a
# launch point close to the grid (a boat launch), where the seed is proportionally worse.
TRANSIT_FIT_MAX_PASSES = 3


'''
======================================================================================
QGROUNDCONTROL JSON FIELD CONSTANTS ARE LISTED BELOW.
QGC requires very precise strings and values for '.plan' files to function correctly.
Therefore, these constants are protected for proper use.
======================================================================================
'''


_QGC_FILETYPE = "Plan"

_QGC_VERSION = 1

_QGC_MISSION_VERSION = 2

_QGC_GROUNDSTATION = "QGroundControl"

#OPTIONAL GEOFENCE PARAMETER, OMITTED FOR NOW
_QGC_GEOFENCE = {
    "circles": [],
    "polygons": [],
    "version": 2
}

#OPTIONAL SAFE RETURN COORDINATE LOCATIONS, OMITTED FOR NOW, WILL INCORPORATE LATER
_QGC_RALLYPOINTS = {
    "points": [],
    "version": 2
}

#FAA height regs most often matter above "Ground Level", ie: the launch point.
#Therefore, Altitude must be relative to the launch pad.
# 1 now matches _QGC_MISSION_GLOBAL_RELATIVE_ALT_FRAME when it is set to 3.
_QGC_GLOBAL_PLAN_ALTITUDE_MODE = 0


'''
MAVLINK COMMAND & CONTROL CONSTANTS ARE LISTED BELOW
(INTEGERS REPRESENT MAV_CMD & MAV_FRAME VALUES IN THE QGC JSON FOR EACH WAYPOINT)
THESE COMMANDS WILL BE ASSIGNED AND PROPERLY TRANSLATED BETWEEN THE ENGINE AND QGC VIA
THE WAYPOINT AND CANDIDATE PLAN OBJECTS.

LISTED ORDER: [2, 3, 16, 21, 22, 84, 85, 206]

See More: https://mavlink.io/en/messages/common.html#mav_commands

EACH SECTION OF CONSTANTS BELOW FOLLOWS THE ABOVE LISTED ORDER
========================================================================================
'''

_TAKEOFF_LANDING_ALT_FRAME = 3
_TAKEOFF_LAND_ALT_MODE = 1

_CRUISING_MISSION_ALT_FRAME = 0
_CRUISING_MISSION_ALT_MODE = 2

_QGC_AMSL_ALT_ABOVE_TERRAIN = None

#.plan files do not have a field for a mission frame, just a global altitude mode??? (CLAUDE see exp2.plan)
_QGC_MAV_FRAME_MISSION = 2



'''
========================================================================================
'''

#For CMD #16: Alt, Long, Lat are filled in by CFE plan generated waypoints
HOLD_TIME_s = 0

ACCEPTANCE_RADIUS_m = 28.5 #sphere with a diamter of B.S S2 turn radius (Radius of (turn radius/2))

PASS_RADIUS_m = 0

# Yaw angle must be null or some other NaN to follow generated waypoint headings from CFE
WP_YAW_deg = None

'''
========================================================================================
'''

ABORT_REL_m = 50

ABORT_AMSL_m = 50 + TERRACE_POINT_AMSL_m

LAND_YAW_deg = None

LANDING_REL_m = 0

LANDING_AMSL_m = TERRACE_POINT_AMSL_m

'''
========================================================================================
'''

#FIXED WING TAKEOFF

TAKEOFF_PITCH_deg = 15

TAKEOFF_YAW_deg = None

TAKEOFF_REL_m = 50

TAKEOFF_AMSL_m = 50 + TERRACE_POINT_AMSL_m

# Homepoint position constant and its necessary values go with takeoff, since takeoffs will always happen at the home point
# [LAT, LONG, SEA LEVEL ALTITUDE]

_QGC_PLANNED_HOME_POSITION = [V1_LAUNCH_POINT_LAT, V1_LAUNCH_POINT_LONG, TERRACE_POINT_AMSL_m]

'''
========================================================================================
'''

#VTOL TAKEOFF

TRANSITION_HEADING_SETTING = 3

TRANSITION_YAW_deg = None

TRANSITION_REL_m = 50

TRANSITION_AMSL_m = 50 + TERRACE_POINT_AMSL_m

'''
========================================================================================
'''

LANDING_BEHAVIOR = 0

APPROACH_AMSL_m = None

LANDING_YAW_deg = None

GROUND_REL_m = 0

GROUND_AMSL_m = TERRACE_POINT_AMSL_m

'''
========================================================================================
'''

'''
**NOTE** MAY BECOME DEPRECATED DEPENDING ON BOSON INTEGRATION
WITH FCU
'''

#**CLAUDE**: Replace "stub" with actuall FLIR BOSON Shutter speed
CAM_SHUTTER_INTEGRATION_millis = 0

CAM_TRIGGER_START = 1

CAM_TRIGGER_END = 0

TARGET_CAM_ID = 0