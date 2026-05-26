
'''
Sun.py is used to populate the CurrentSunState object, found in objects.py.
When this file recieves input in the form of long, lat, and date_time, it returns
a populated current sun state object.

We do not need two sun states (one for launch and land), because the aircraft
return heading is not determined by sun azimuth.

'''

#module imports:
from pysolar.solar import get_azimuth, get_altitude 
import datetime
from .objects import CurrentSunState


#constants imports
from .constants import (
                        V1_LAUNCH_POINT_LAT, 
                        V1_LAUNCH_POINT_LONG, 
                        V1_DEFAULT_MISSION_YEAR,
                        V1_DEFAULT_MISSION_MONTH,
                        V1_DEFAULT_MISSION_DAY_OF_MONTH,
                        V1_DEFAULT_MISSION_HOUR)

#date constants in datetime module form are below:
TIME_ZONE_INFO = datetime.timezone.utc

#The datetime library is used in conunction with pysolar for my helper functions
mission_date = datetime.datetime(V1_DEFAULT_MISSION_YEAR, V1_DEFAULT_MISSION_MONTH, 
                                 V1_DEFAULT_MISSION_DAY_OF_MONTH, V1_DEFAULT_MISSION_HOUR, tzinfo=TIME_ZONE_INFO)

'''
Below are the list of helper functions used to populate the current sun state
object for the start of the mission.

The functions are written in order of their listing in the currentSunState Constructor
in order to hopefully increase readability and decrease confusion. 
'''

'''
The calc_azimuth(latitude, longitude, and date) function
calculates the azimuth angle of the sun given some coordinates
and a date. Latitude and longitude will be the launch position,
and date will be our assumed mission date for V1.
It returns the azimuth angle in degrees in decimal form.

Azimuth is reckoned with zero corresponding to north. 
Positive azimuth estimates correspond to estimates east of north; 
negative estimates, or estimates larger than 180 are west of north.
'''

def calc_azimuth(latitude, longitude, date):
    
    launch_point_sun_az_deg = get_azimuth(latitude, longitude, date)
    
    return launch_point_sun_az_deg

#===================================================================

'''
The calc_elevation (latitude, longitude, date) function
calculates the elevation of the sun given some coordinates
and a date. Latitude and longitude will alwaus be the launch positon,
and date will always be our assumed mission date for V1. It returns
the elevation angle in degrees in decimal form.
'''

def calc_elevation(latitude, longitude, date):
    
    launch_point_sun_elev_deg = get_altitude(latitude, longitude, date)
    
    return launch_point_sun_elev_deg

#===================================================================

'''
The calc_zenith function (solar_elevation_deg) returns
the zenith angle of the sun in degrees as a decimal. It only
accepts one parameter because date, time, and coordinates have already
been taken into account when calculating the solar elevation, which
is required to be completed beforehand (pysolar does not have a zenith
function).
'''

def calc_zenith(solar_elevation_deg):

    launch_point_solar_zenith_deg = (90.0 - solar_elevation_deg)
    
    return launch_point_solar_zenith_deg

#===================================================================

'''
The create_launch_sun_state function puts it all together by populating
the constructor of a currentSunState obejct and returning it. It uses
the helper functions above and calculates the values needed for the rest
of the engine to have proper sun data.
'''

#Creator function is getting defaults for now
def create_sun_state(latitude=V1_LAUNCH_POINT_LAT, longitude=V1_LAUNCH_POINT_LONG, date=mission_date):
    
    #calculating launch point azimuth for object
    current_launch_point_az_deg = calc_azimuth(latitude, longitude, date)
    
    #calculating launch point elevation for object
    current_launch_point_elev_deg = calc_elevation(latitude, longitude, date)
    
    #calculating launch point zenith for object
    current_launch_point_zen_deg = calc_zenith(current_launch_point_elev_deg)
    
    launch_sun_state = CurrentSunState(current_launch_point_az_deg, current_launch_point_elev_deg, 
                            current_launch_point_zen_deg, V1_DEFAULT_MISSION_DAY_OF_MONTH,
                            V1_DEFAULT_MISSION_HOUR,0)
    
    return launch_sun_state
    
    