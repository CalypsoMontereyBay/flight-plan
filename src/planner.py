"""
Planner.py is the "Hub" for the engine. This program puts all of the pieces together.

It is knowledgable of the other files while each module is not.

Planner.py pulls the sun state (sun.py) and grid geometry (geo.py), then converts waypoints from
their geometric form into Waypoint objects so they can be placed into a Mission
Request object. The best corner is picked for the start of the mission route within the grid.
Then, this file returns a candidate plan that is scored.

Planner.py stitches the engine's calculations together and presents a candidate.
"""

# File Imports:

from objects import Aircraft, Sensor, Waypoint, MissionRequest, Weather, CandidatePlan
import constants as CONST
from geo import make_lawnmower_grid_through_m1, distance_between, bearing_between
from sun import create_sun_state, mission_date
from aircraft_math import max_planned_distance_m

# Main Functions and logic:
# Step 1: Build the components of a candidate plan by assembling the
# objects I need.

# Step 1.1: Assemble the aircraft and get its constraints from aircraft math.

_Black_Swift = Aircraft(
    CONST.BLACKSWIFT_ENDURANCE_min,
    CONST.BLACKSWIFT_WIND_RATING_ms,
    CONST.BLACKSWIFT_CLIMB_RATE_ms,
    CONST.BLACKSWIFT_DESCENT_RATE_ms,
    CONST.BLACKSWIFT_TURN_RADIUS_m,
    CONST.BLACKSWIFT_TURN_PENALTY_s,
    CONST.BLACKSWIFT_MIN_GROUND_SPEED_ms,
    CONST.BLACKSWIFT_CRUISE_SPEED_ms,
)

# Amount of distance the aircraft can use for its mission (Using the alias function, further docs in aircraft_math.py)
_Black_Swift_usable_endurance_m = max_planned_distance_m(
    _Black_Swift, CONST.V1_EMERGENCY_RESERVE_FRACTION
)

# Step 1.2: Assemble the Sensor object

_Calypso_payload = Sensor(
    CONST.V1_DEFAULT_SENSOR_CROSS_TRACK_FOV_deg,
    CONST.V1_DEFAULT_SENSOR_ALONG_TRACK_FOV_DEG,
    CONST.V1_DEFAULT_OVERLAP_PCT,
    CONST.V1_DEFAULT_SENSOR_OFF_NADIR_deg,
    "Micasense from Grey Paper",
)

# Step 1.3: Mission Request object for launch, land, and M1, then route assembly:

_V1_Launch_Waypoint = Waypoint(
    "WP000",
    CONST.V1_LAUNCH_POINT_LAT,
    CONST.V1_LAUNCH_POINT_LONG,
    CONST.V1_DEFAULT_AIRCRAFT_ALTITUDE_m,
    CONST.BLACKSWIFT_CRUISE_SPEED_ms,
    CONST.WAYPOINT_ACTION_LAUNCH,
    "Launch point",
    "Seymour-Beach-Launch",
)

_V1_Land_Waypoint = Waypoint(
    "WP_END",
    CONST.V1_LAND_POINT_LAT,
    CONST.V1_LAND_POINT_LONG,
    CONST.V1_DEFAULT_AIRCRAFT_ALTITUDE_m,
    CONST.BLACKSWIFT_CRUISE_SPEED_ms,
    CONST.WAYPOINT_ACTION_LAND,
    "land waypoint",
    "Seymour-Road-Land",
)

_V1_M1_Waypoint = Waypoint(
    "WP_M1",
    CONST.M1_MOORING_LAT,
    CONST.M1_MOORING_LONG,
    CONST.V1_DEFAULT_AIRCRAFT_ALTITUDE_m,
    CONST.BLACKSWIFT_CRUISE_SPEED_ms,
    CONST.WAYPOINT_ACTION_M1_OVERFLIGHT,
    "M1 waypoint for overflight req",
    "M1-Mooring-Station",
)

_V1_Mission_Request = MissionRequest(
    mission_name="V1 First Example Mission",
    launch_waypoint=_V1_Launch_Waypoint,
    land_waypoint=_V1_Land_Waypoint,
    altitude_m=CONST.V1_DEFAULT_AIRCRAFT_ALTITUDE_m,
    valid_date=mission_date,
    require_m1_overflight=True,
    grid_orientation_deg=None,
    notes="First Mission",
    included_target_waypoints=[_V1_M1_Waypoint],
)


# Step 1.4: Weather Stub, no API source yet, using conditions at launch point:

_V1_assumed_weather = Weather(
    CONST.V1_LAUNCH_POINT_LAT,
    CONST.V1_LAUNCH_POINT_LONG,
    mission_date,
    CONST.V1_DEFAULT_MISSION_CLOUD_COVER,
    CONST.DEFAULT_ZERO_WIND,
    CONST.DEFAULT_WIND_DIRECTION_deg,
    CONST.DEFAULT_WIND_GUST_ms,
    CONST.DEFAULT_VISIBILITY_m,
    CONST.DEFAULT_WEATHER_CONDITION,
)


# Step 2: Assemble the current sun state and grab the azimuth.

_V1_mission_sun_state = create_sun_state(
    CONST.V1_LAUNCH_POINT_LAT, CONST.V1_LAUNCH_POINT_LONG, mission_date
)

_V1_mission_sun_azmimuth = _V1_mission_sun_state.azimuth

"""
HELPER FUNCTIONS FOR POPULATING THE CANDIDATE PLAN BELOW
In Order:

1. _candidate_orientation(sun_az): takes an azimuth angle and returns two heading "orientations"
Both orientations are valid for "science" lines, but depending on all the other factors, one will score
better than the other. returns both in a tuple for passing around and proper security.
These values are then passed as potential_orientation_deg params in other helpers.

2. _score_glint(potential_orientation_deg, sun_az_deg): Returns how far off one leg of a candidate orientation is
off from the 135 standard. Scores follow a golf paradigm (lower = better). A score of 0 means
135 degrees exactly. No candidate orientation can earn lower than zero. If scores are equal, including for
two candidates that earn a score of zero, a tiebreaker (which orientation's corner is closest to the launch),
is used. This is the tiebreaker because if the corner is closer, it is more likely that the grid is also larger.

3. _score_candidate(orientation_track_heading_deg, sun_az_deg): scores an entire candidate
by scoring both a leg in heading orientation_track_heading_deg, and orientation_track_heading_deg + 180.
A candidate is only good in V1 if both directions are tolerable.

CONTROL FLOW FOR THESE THREE FUNCTIONS:

1. _candidate_orientation() produces two "potential orientations" for the final grid.

2. Each potential orientation needs to be flow in in its original heading and + 180 degrees (lawnmower pattern)

3. _score_glint() evaluates one potential orientation in one direction, therefore running twice per potential orientation.

4. _score_candidate() combines the two legs into one candidate and ranks them. 
"""


def _candidate_orientation(sun_az):

    # Two possible heading orientations for minimizing glint, they will
    # be used as "paths" and then the score for V1 is based off of glint minimization.

    potential_orientation_one = (sun_az + CONST.AZIMUTH_ONE_THIRTY_FIVE) % CONST.AZIMUTH_THREE_SIXTY

    potential_orientation_two = (sun_az - CONST.AZIMUTH_ONE_THIRTY_FIVE) % CONST.AZIMUTH_THREE_SIXTY

    return (potential_orientation_one, potential_orientation_two)


# Glint scoring function used to rank plans for V1.
# THE ONLY RANKING FUNCTION FOR V1, OTHERS WILL FOLLOW
#track heading is an az candidate from the function above
def _score_glint(potential_orientation_deg, sun_az_deg):
    """
    Golf-style glint penalty: 0 = perfect (track is exactly 135 off sun-azimuth),
    higher = worse. Symmetric is +- 135 since the camera does not care which way it is tilted.
    (The aircraft is what maintins the azimuth, not the cam).

    track_heading: heading flown on the leg: (0..360)
    sun_az: sun azimuth at the mission time: (0..360)
    """

    # finds how far off each azimuth candidate heading is from the desired 0 score.
    azimuth_delta = (potential_orientation_deg - sun_az_deg) % CONST.AZIMUTH_THREE_SIXTY

    # the lower of the values is the winner and is returned
    return min(
        (abs(azimuth_delta - CONST.AZIMUTH_ONE_THIRTY_FIVE)),
        (abs(azimuth_delta - CONST.AZIMUTH_TWO_TWENTY_FIVE))
    )