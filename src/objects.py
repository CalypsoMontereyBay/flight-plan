'''
    -This file contains classes and objects that will be used in the project. They are defined below

    - Each object in this file is meant to be used elsewhere in the project.

    - This file contains the following list of objects:
        - Mission Request (A mission candidate with times, launch and landing points, polygon boundary, etc)
        - Aircraft (Copter and wing supported, aircraft stats kept here to use in math)
        - Sensor (What kind of sensor is being used, also contains viewing geometry constants)
        - Weather (An object whose attributes describe the current weather according to an API)
        - SunState (This object describes important factors about the sun, most importantly, zenith and azimuth angles are stored/calculated here)
        - Candidate Plan (Bringing it all together, attributes include the list of waypoints, flight lines, aircraft battery stats, and a score used to rank candidates)

'''

#imports:

#import datetime

class Aircraft:
    
    # Global vars used for both a fixed wing and copter to standardize:
    
    #Units = minutes of flight time at cruise speed (SUBJECT TO CHANGE)
    required_battery_reserve_mins = 10 
    
    #Default constructor for an aircraft, global parameters remain above,
    #but the following parameters will differ between wing and hex/quad/oct
    def __init__(self, endurance_min, wind_rating_ms, climb_rate_ms, descent_rate_ms, turn_radius_m, 
                 turn_penalty_s, min_ground_speed_ms, cruise_speed_ms):

        self.vehicle_endurance = endurance_min
        self.vehicle_max_wind_rating = wind_rating_ms
        self.vehicle_median_climb_rate = climb_rate_ms
        self.vehicle_median_descent_rate = descent_rate_ms
        self.turn_radius = turn_radius_m
        self.turn_penalty = turn_penalty_s
        self.stall_speed = min_ground_speed_ms
        self.max_ground_speed = (1.5 * cruise_speed_ms)
        self.cruising_speed = cruise_speed_ms
        
    '''
    Below is a section that defines getters for each aircraft constructor parameter.
    Required for passing values into mathematical functions or as parameters to other
    functions.
    '''
    
    @property
    def get_vehicle_endurance(self):
        return self.vehicle_endurance
    
    @property
    def get_vehicle_wind_rating(self):
        return self.vehicle_max_wind_rating
    
    @property
    def get_vehicle_climb_rate(self):
        return self.vehicle_median_climb_rate
    
    @property
    def get_vehicle_descent_rate(self):
        return self.vehicle_median_descent_rate
    
    @property
    def get_vehicle_turn_radius(self):
        return self.turn_radius
    
    @property
    def get_vehicle_turn_penalty(self):
        return self.turn_penalty
    
    @property
    def get_vehicle_stall_speed(self):
        return self.stall_speed
    
    @property
    def get_vehicle_max_speed(self):
        return self.max_ground_speed
    
    @property
    def get_vehicle_cruise_speed(self):
        return self.cruising_speed
    
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
        
    
'''    
class Sensor:
    
    #defines ϴ for viewing geometry purposes
    #Units = degrees (CONSTANT)
    _off_nadir = 40 
    
    #Sensor paramters
    
    #Units = degress
    #_sensor_horiz_FOV (NOT KNOWN YET)
    
    #Units = degrees
    #_sensor_vert_FOV (NOT KNOWN YET) 
    
'''

class CurrentSunState:
    
    def __int__(self, azimuth_deg, elevation_ft, zenith_deg, day_of_year):#, currennt_hour, current_minute):
        
        self.azimuth_angle = azimuth_deg
        self.elevation = elevation_ft
        self.zenith_angle = zenith_deg
        self.current_day = day_of_year #1-365