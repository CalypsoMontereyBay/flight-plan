'''
    -This file contains classes and objects that will be used in the project. They are defined below

    - Each object in this file is meant to be used elsewhere in the project.

    - This file contains the following list of objects:
        - Mission Request (A mission candidate with times, launch and landing points, polygon boundary, etc) **
        - Aircraft (Copter and wing supported, aircraft stats kept here to use in math)
        - Sensor (What kind of sensor is being used, also contains viewing geometry constants)
        - Weather (An object whose attributes describe the current weather according to an API) **
        - SunState (This object describes important factors about the sun, most importantly, zenith and azimuth angles are stored/calculated here)
        - Candidate Plan (Bringing it all together, attributes include the list of waypoints, flight lines, aircraft battery stats, and a score used to rank candidates) **
        - GeoPoint (DESCRIPTION TO BE ADDED SOON) **
        - WayPoint (DESCRIPTION TO BE ADDED SOON) **
        

'''

#imports:
from shapely.geometry import Point
#from typing import Optional

#import datetime

class Aircraft:
    
    # Global vars used for both a fixed wing and copter to standardize:
    
    #Units = minutes of flight time at cruise speed (SUBJECT TO CHANGE)
    required_battery_reserve_mins = 10 
    
    #Default constructor for an aircraft, global parameters remain above,
    #but the following parameters will differ between wing and hex/quad/oct
    def __init__(self, endurance_min, wind_rating_ms, climb_rate_ms, descent_rate_ms, turn_radius_m, 
                 turn_penalty_s, min_ground_speed_ms, cruise_speed_ms):

        self._vehicle_endurance = endurance_min
        self._vehicle_max_wind_rating = wind_rating_ms
        self._vehicle_median_climb_rate = climb_rate_ms
        self._vehicle_median_descent_rate = descent_rate_ms
        self._turn_radius = turn_radius_m
        self._turn_penalty = turn_penalty_s
        self._stall_speed = min_ground_speed_ms
        self._max_ground_speed = (1.5 * cruise_speed_ms)
        self._cruising_speed = cruise_speed_ms
        
    '''
    Below is a section that defines getters for each aircraft constructor parameter.
    Required for passing values into mathematical functions or as parameters to other
    functions.
    '''
    
    @property
    def vehicle_endurance(self):
        return self._vehicle_endurance
    
    @property
    def vehicle_wind_rating(self):
        return self._vehicle_max_wind_rating
    
    @property
    def vehicle_climb_rate(self):
        return self._vehicle_median_climb_rate
    
    @property
    def vehicle_descent_rate(self):
        return self._vehicle_median_descent_rate
    
    @property
    def vehicle_turn_radius(self):
        return self._turn_radius
    
    @property
    def vehicle_turn_penalty(self):
        return self._turn_penalty
    
    @property
    def vehicle_stall_speed(self):
        return self._stall_speed
    
    @property
    def vehicle_max_speed(self):
        return self._max_ground_speed
    
    @property
    def vehicle_cruise_speed(self):
        return self._cruising_speed
    
    '''
    Below is a section that defines setters for each aircraft constructor parameter.
    Meant only to be used in the event of a user input error.
    '''
    
    
    def set_vehicle_endurance(self, new_endurance):
        self.vehicle_endurance = new_endurance
        return
    
    def set_vehicle_wind_rating(self, new_wind_rating):
        self.vehicle_max_wind_rating = new_wind_rating
        return
    
    def set_vehicle_climb_speed(self, new_climb_ms):
        self.vehicle_median_climb_rate = new_climb_ms
        return
    
    def set_vehicle_descent_speed(self, new_descent_ms):
        self.vehicle_median_descent_rate = new_descent_ms
        return
    
    def set_vehicle_turn_radius(self, new_radius):
        self.turn_radius = new_radius
        return
    
    def set_vehicle_turn_penalty(self, new_penalty_s):
        self.turn_penalty = new_penalty_s
        return
    
    def set_vehicle_stall_speed(self, new_stall_speed_ms):
        self.stall_speed = new_stall_speed_ms
        return
    
    def set_vehicle_cruise_speed(self, new_cruise_speed_ms):
        self.cruising_speed = new_cruise_speed_ms
        return
    
    def set_vehicle_max_ground_speed(self, new_cruise_speed_ms):
        self.max_ground_speed = 1.5 * new_cruise_speed_ms
        self.set_vehicle_cruise_speed(new_cruise_speed_ms)
        return
        

class CurrentSunState:
    
    # Constructor for the Sun object
    # Parameters important for V1 in order to establish the very limited
    # ranking capabilities are below
    
    def __init__(self, azimuth_deg, elevation_deg, zenith_deg, day_of_year, current_hour, current_minute):
        
        self._azimuth_angle = azimuth_deg
        self._elevation = elevation_deg
        self._zenith_angle = zenith_deg
        self._current_day = day_of_year #1-365
        self._current_time_of_day = [current_hour, current_minute] #hours are 00 - 24, mins are 00 - 59
        
    
    # Defining getters for each of the sun state params:
    
    @property
    def azimuth(self):
        return self._azimuth_angle
    
    @property
    def elevation(self):
        return self._elevation
    
    @property
    def zenith(self):
        return self._zenith_angle
    
    @property
    def current_day(self):
        return self._current_day
    
    @property
    def current_hour(self):
        return self._current_time_of_day[0]
    
    @property
    def current_minute(self):
        return self._current_time_of_day[1]
    
    # Defining setters for each sun state parameter:
    
    def set_azimuth_angle(self, new_azimuth_angle):
        self.azimuth_angle = new_azimuth_angle
        return
    
    def set_elevation(self, new_elevation):
        self.elevation = new_elevation
        return
    
    def set_zenith_angle(self, new_zenith_angle):
        self.zenith_angle = new_zenith_angle
        return
    
    def set_current_day(self, new_day):
        self.current_day = new_day
        return
    
    def set_current_hour(self, new_hour):
        self.current_time_of_day[0] = new_hour
        return
    def set_current_minute(self, new_minute):
        self.current_time_of_day[1] = new_minute
        return
    
    
class Weather:
    
    '''
    This class will later make calls to the NWS API for forecasting
    and live weather updates as the mission candidate is being made.
    This API call, due to forecasting, also allows mission candidates
    that are in the future to still be created and ranked just like any 
    other candidate.
    '''
    
    '''
    API calls to the NWS forecasting service are made in weather.py.
    This class simply serves as a definition to a weather object to efficiently
    pass around data as described in the documentation for this file up above.
    '''
    
    def __init__(self, latitude_decimal, longitude_decimal, valid_time, 
                 cloud_cover_pct, wind_speed_ms, wind_direction_deg,
                 wind_gusting_ms, visibility_m, condition_str, source = "STUB"):
        
        self.latitude = latitude_decimal
        self.longitude = longitude_decimal
        self.valid_time = valid_time #TURN INTO LIST WITH VALID HOURS AND MINUTES (MAY REQUIRE STRING PARSER)
        self.cloud_cover_pct = cloud_cover_pct
        self.wind_speed_ms = wind_speed_ms
        self.wind_direction_deg = wind_direction_deg
        self.wind_gust_speed_ms = wind_gusting_ms
        self.visibility_m = visibility_m
        self.condition = condition_str
        self.data_source = source
    
    
    #The necessary getters for this object (since most is based on api), are listed below:
    
    @property
    def cloud_cover(self):
        return self.cloud_cover
    
    @property
    def wind_speed(self):
        return self.wind_speed
    
    @property
    def wind_gusts(self):
        return self.wind_gusts
    
    @property
    def condition(self):
        return self.condition
    

class Waypoint:
    
    '''
    Mission candidates consist of useful data regarding the aircraft,
    weather, legality, glint, etc, all culminating to a final score.
    However, at its score, a mission candidate requires a list of way-
    points in order to command the UAV to the proper places along
    the route.
    The waypoint class as needed for V1 is defined here
    '''
    
    '''
    The constructor contains important but basic parameters for V1,
    basically what you would find as settings for a waypoint in QGC,
    you'll find in this constructor.
    '''
    
    def __init__(self, waypoint_id, latitude_decimal, longitude_decimal, altitude_m, speed_ms, heading_deg, action, notes=None, target_name=None):
        
        self._waypoint_id = waypoint_id
        self._latitude_decimal = latitude_decimal
        self._longitude_decimal = longitude_decimal
        self._altitude_m = altitude_m
        self._speed_ms = speed_ms
        self._heading_deg = heading_deg
        self.action = action
        self.notes = notes
        self.target_name = target_name
        
        '''
        Parameters for the way point explained:
        1. Waypoint ID: Formatted as WPXXX, gives a numerical id to each WP
        2. latitude: Waypoint's latitude coordinates in decimal form
        3. longitude: Waypoint's longitude coordinate in decimal form
        4. altitude: aircraft altitude at that waypoint
        5. speed: aircraft speed at that waypoint
        6. heading: aircraft heading at that waypoint
        7. action: Most important param, a string used to pass to other functions so the engine can make decisions on a per-point basis
        8. notes: human readable notes about a waypoint, OPTIONAL
        9. target_name, an optional but more human readable name for a waypoint besides its ID
        '''
        
        #Allowance to referral to each point as a Shapely point
        @property
        def point(self):
            return Point(self._longitude_decimal, self._latitude_decimal)
        

        def to_CSV_row(self):
            return [self._waypoint_id, self._longitude_decimal, self._latitude_decimal, 
                    self._altitude_m, self._speed_ms, self._heading_deg,
                    self.action, self.notes, self.target_name]
    
        def is_m1_overflight(self):
            return self.action == "m1_overflight" or self.target_name == "M1"

    