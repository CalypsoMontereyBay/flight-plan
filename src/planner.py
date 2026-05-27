'''
Planner.py is the "Hub" for the engine. This program puts all of the pieces together.

It is knowledgable of the other files while each module is not. 

Planner.py pulls the sun state (sun.py) and grid geometry (geo.py), then converts waypoints from
their geometric form into Waypoint objects so they can be placed into a Mission
Request object. The best corner is picked for the start of the mission route within the grid.
Then, this file returns a candidate plan that is scored.

Planner.py stitches the engine's calculations together and presents a candidate.
'''

#File Imports:

from objects import *
from constants import *
from geo import *
from sun import *
from aircraft_math import *


# Main Functions and logic:
#Step 1: Build the components of a candidate plan by assembling the
#objects I need.

#Step 1.1: Assemble the aircraft and get its constraints from aircraft math.

_Black_Swift = Aircraft(BLACKSWIFT_ENDURANCE_min, BLACKSWIFT_WIND_RATING_ms,
                                BLACKSWIFT_CLIMB_RATE_ms, BLACKSWIFT_DESCENT_RATE_ms,
                                BLACKSWIFT_TURN_RADIUS_m, BLACKSWIFT_TURN_PENALTY_s,
                                BLACKSWIFT_MIN_GROUND_SPEED_ms, BLACKSWIFT_CRUISE_SPEED_ms)

#Amount of distance the aircraft can use for its mission (Using the alias function, further docs in aircraft_math.py)
_Black_Swift_usable_endurance_m = max_planned_distance_m(_Black_Swift, V1_EMERGENCY_RESERVE_FRACTION)

#Step 1.2: Assemble the Sensor object

_Calypso_payload = Sensor(V1_DEFAULT_SENSOR_CROSS_TRACK_FOV_deg, V1_DEFAULT_SENSOR_ALONG_TRACK_FOV_DEG, 
                          V1_DEFAULT_OVERLAP_PCT, V1_DEFAULT_SENSOR_OFF_NADIR_deg, "Micasense from Grey Paper")

#Step 1.3: Mission Request object for launch, land, and M1, then route assembly:

_V1_Launch_Waypoint = Waypoint("WP000", V1_LAUNCH_POINT_LAT, V1_LAUNCH_POINT_LONG, V1_DEFAULT_AIRCRAFT_ALTITUDE_m,
                               BLACKSWIFT_CRUISE_SPEED_ms, WAYPOINT_ACTION_LAUNCH, "Launch point", "Seymour-Beach-Launch")

_V1_Land_Waypoint = Waypoint("WP_END", V1_LAND_POINT_LAT, V1_LAND_POINT_LONG, V1_DEFAULT_AIRCRAFT_ALTITUDE_m, BLACKSWIFT_CRUISE_SPEED_ms,
                             WAYPOINT_ACTION_LAND, "land waypoint", "Seymour-Road-Land")

_V1_M1_Waypoint = Waypoint("WP_M1", M1_MOORING_LAT, M1_MOORING_LONG, V1_DEFAULT_AIRCRAFT_ALTITUDE_m,
                           BLACKSWIFT_CRUISE_SPEED_ms, WAYPOINT_ACTION_M1_OVERFLIGHT, "M1 waypoint for overflight req",
                           "M1-Mooring-Station")

_V1_Mission_Request = MissionRequest("V1 First example Mission", _V1_Launch_Waypoint, _V1_Land_Waypoint,
                                     V1_DEFAULT_AIRCRAFT_ALTITUDE_m, mission_date,
                                     True, 0, "First mission")


#Step 1.4: Weather Stub, no API source yet, using conditions at launch point:

_V1_assumed_weather = Weather(V1_LAUNCH_POINT_LAT, V1_LAUNCH_POINT_LONG, mission_date,
                              V1_DEFAULT_MISSION_CLOUD_COVER, DEFAULT_ZERO_WIND, DEFAULT_WIND_DIRECTION_deg,
                              DEFAULT_WIND_GUST_ms, DEFAULT_VISIBILITY_m, DEFAULT_WEATHER_CONDITION)


#Step 2: Assemble the current sun state and grab the azimuth.

_V1_mission_sun_state = create_sun_state(V1_LAUNCH_POINT_LAT, V1_LAUNCH_POINT_LONG, mission_date)

_V1_mission_sun_azmimuth = _V1_mission_sun_state.azimuth

#Using geo.py functions to actually build the grid, make points, populate a route...


'''
HELPER FUNCTIONS FOR POPULATING THE CANDIDATE PLAN BELOW
In Order:

1. _candidate_orientation(sun_az): takes an azimuth angle and returns two heading "tracks"
Both tracks are valid for "science" lines, but depending on all the other factors, one will score
better than the other. returns both in a tuple for passing around and proper security.

2. _score_glint(track_heading_deg, sun_az_deg): Returns how far off a candidate orientation is
off from the 135 standard. Scores follow a golf paradigm (lower = better). A score of 0 means
135 degrees exactly. No candidate orientation can earn lower than zero. If scores are equal, including for
two candidates that earn a score of zero, a tiebreaker (which orientation's corner is closest to the launch),
is used. This is the tiebreaker because if the corner is closer, it is more likely that the grid is also larger.
'''


def _candidate_orientation(sun_az):
    
    #Two possible heading orientations for minimizing glint, they will
    #be used as "paths" and then the score for V1 is based off of glint minimization.
    #A second candidate will be considered for V2.
    
    az_candidate_one = (sun_az + AZIMUTH_ONE_THIRTY_FIVE) % AZIMUTH_THREE_SIXTY
    
    az_candidate_two = (sun_az - AZIMUTH_ONE_THIRTY_FIVE) % AZIMUTH_THREE_SIXTY
    
    return (az_candidate_one, az_candidate_two)


#Glint scoring function used to rank plans for V1.
#THE ONLY RANKING FUNCTION FOR V1, OTHERS WILL FOLLOW
#def _score_glint()