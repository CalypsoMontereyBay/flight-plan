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


#Constants Imports:

#Constant Declarations:


# Main Functions and logic:
#Step 1: Build the components of a candidate plan by assembling the
#objects I need.

#Step 1.1: Assemble the aircraft and get its constraints from aircraft math.

_Black_Swift = Aircraft(BLACKSWIFT_ENDURANCE_min, BLACKSWIFT_WIND_RATING_ms,
                                BLACKSWIFT_CLIMB_RATE_ms, BLACKSWIFT_DESCENT_RATE_ms,
                                BLACKSWIFT_TURN_RADIUS_m, BLACKSWIFT_TURN_PENALTY_s,
                                BLACKSWIFT_MIN_GROUND_SPEED_ms, BLACKSWIFT_CRUISE_SPEED_ms)

#Get the aircraft's total endurance as a unit of distance
_Black_Swift_total_endurance_m = total_endurance_distance_m(_Black_Swift)

#Get the aircraft's reserve endurance as a unit of distance
_Black_Swift_reserve_endurance_m = reserve_distance_m(_Black_Swift, V1_EMERGENCY_RESERVE_FRACTION)

#Amount of distance the aircraft can use for its mission (Using the alias function, further docs in aircraft_math.py)
_Black_Swift_usable_endurance_m = max_planned_distance_m(_Black_Swift, V1_EMERGENCY_RESERVE_FRACTION)

#Step 2.2: Assemble the Sensor object

_Calypso_payload = Sensor(V1_DEFAULT_SENSOR_CROSS_TRACK_FOV_deg, V1_DEFAULT_SENSOR_ALONG_TRACK_FOV_DEG, V1_DEFAULT_OVERLAP_PCT,
                          V1_DEFAULT_SENSOR_OFF_NADIR_deg, "Micasense from Grey Paper")

#Step 2.3: Mission Request object (Route Assembly):


#Step 2.4: Weather Stub, no API source yet, using conditions at launch point:

_V1_assumed_weather = Weather(V1_LAUNCH_POINT_LAT, V1_LAUNCH_POINT_LONG, mission_date,
                              V1_DEFAULT_MISSION_CLOUD_COVER, DEFAULT_ZERO_WIND, DEFAULT_WIND_DIRECTION_deg,
                              DEFAULT_WIND_GUST_ms, DEFAULT_VISIBILITY_m, DEFAULT_WEATHER_CONDITION)
