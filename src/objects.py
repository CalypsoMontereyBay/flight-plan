"""
-This file contains classes and objects that will be used in the project. They are defined below

- Each object in this file is meant to be used elsewhere in the project.

- This file contains the following list of objects:
    - Mission Request (A mission candidate with times, launch and landing points, polygon boundary, etc)
    - Aircraft (Copter and wing supported, aircraft stats kept here to use in math)
    - Sensor (What kind of sensor is being used, also contains viewing geometry constants)
    - Weather (An object whose attributes describe the current weather according to an API)
    - SunState (This object describes important factors about the sun, most importantly, zenith and azimuth angles are stored/calculated here)
    - Candidate Plan (Bringing it all together, attributes include the list of waypoints, flight lines, aircraft battery stats, and a score used to rank candidates) **
    - GeoPoint (DESCRIPTION TO BE ADDED SOON) **
    - WayPoint (The smallest unit of a mission request, while a candidate plan holds all other params, waypoints build the route stored in a mission request object)


"""

# imports:
from shapely.geometry import Point
from datetime import datetime


class Aircraft:

    # Global vars used for both a fixed wing and copter to standardize:

    # Units = minutes of flight time at cruise speed (SUBJECT TO CHANGE)
    # required_battery_reserve_mins = 10

    # Default constructor for an aircraft, global parameters remain above,
    # but the following parameters will differ between wing and hex/quad/oct
    def __init__(
        self,
        endurance_min,
        wind_rating_ms,
        climb_rate_ms,
        descent_rate_ms,
        turn_radius_m,
        turn_penalty_s,
        min_ground_speed_ms,
        cruise_speed_ms,
    ):

        self._vehicle_endurance = endurance_min
        self._vehicle_max_wind_rating = wind_rating_ms
        self._vehicle_median_climb_rate = climb_rate_ms
        self._vehicle_median_descent_rate = descent_rate_ms
        self._turn_radius = turn_radius_m
        self._turn_penalty = turn_penalty_s
        self._stall_speed = min_ground_speed_ms
        self._max_ground_speed = 1.5 * cruise_speed_ms
        self._cruising_speed = cruise_speed_ms

    """
    Below is a section that defines getters for each aircraft constructor parameter.
    Required for passing values into mathematical functions or as parameters to other
    functions.
    """

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

    """
    Below is a section that defines setters for each aircraft constructor parameter.
    Meant only to be used in the event of a user input error.
    """

    def set_vehicle_endurance(self, new_endurance):
        self._vehicle_endurance = new_endurance
        return

    def set_vehicle_wind_rating(self, new_wind_rating):
        self._vehicle_max_wind_rating = new_wind_rating
        return

    def set_vehicle_climb_speed(self, new_climb_ms):
        self._vehicle_median_climb_rate = new_climb_ms
        return

    def set_vehicle_descent_speed(self, new_descent_ms):
        self._vehicle_median_descent_rate = new_descent_ms
        return

    def set_vehicle_turn_radius(self, new_radius):
        self._turn_radius = new_radius
        return

    def set_vehicle_turn_penalty(self, new_penalty_s):
        self._turn_penalty = new_penalty_s
        return

    def set_vehicle_stall_speed(self, new_stall_speed_ms):
        self._stall_speed = new_stall_speed_ms
        return

    def set_vehicle_cruise_speed(self, new_cruise_speed_ms):
        self._cruising_speed = new_cruise_speed_ms
        return

    def set_vehicle_max_ground_speed(self, new_cruise_speed_ms):
        self._max_ground_speed = 1.5 * new_cruise_speed_ms
        self.set_vehicle_cruise_speed(new_cruise_speed_ms)
        return


class CurrentSunState:

    # Constructor for the Sun object
    # Parameters important for V1 in order to establish the very limited
    # ranking capabilities are below

    def __init__(
        self,
        azimuth_deg,
        elevation_deg,
        zenith_deg,
        day_of_month,
        current_hour,
        current_minute=0,
    ):

        self._azimuth_angle = azimuth_deg
        self._elevation = elevation_deg
        self._zenith_angle = zenith_deg
        self._current_day = day_of_month
        self._current_time_of_day = [
            current_hour,
            current_minute,
        ]  # hours are 00 - 24, mins are 0 - 59

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
        self._azimuth_angle = new_azimuth_angle
        return

    def set_elevation(self, new_elevation):
        self._elevation = new_elevation
        return

    def set_zenith_angle(self, new_zenith_angle):
        self._zenith_angle = new_zenith_angle
        return

    def set_current_day(self, new_day):
        self._current_day = new_day
        return

    def set_current_hour(self, new_hour):
        self._current_time_of_day[0] = new_hour
        return

    def set_current_minute(self, new_minute):
        self._current_time_of_day[1] = new_minute
        return


class Weather:
    """
    This class will later make calls to the NWS API for forecasting
    and live weather updates as the mission candidate is being made.
    This API call, due to forecasting, also allows mission candidates
    that are in the future to still be created and ranked just like any
    other candidate.
    """

    """
    API calls to the NWS forecasting service are made in weather.py.
    This class simply serves as a definition to a weather object to efficiently
    pass around data as described in the documentation for this file up above.
    """

    def __init__(
        self,
        latitude_decimal,
        longitude_decimal,
        valid_time,
        cloud_cover_pct,
        wind_speed_ms,
        wind_direction_deg,
        wind_gusting_ms,
        visibility_m,
        condition_str,
        source="STUB",
    ):

        if not isinstance(valid_time, datetime):
            raise TypeError("valid_time must be a datetime.datetime instance")

        self._latitude = latitude_decimal
        self._longitude = longitude_decimal
        self._valid_time = valid_time
        self._cloud_cover_pct = cloud_cover_pct
        self._wind_speed_ms = wind_speed_ms
        self._wind_direction_deg = wind_direction_deg
        self._wind_gust_speed_ms = wind_gusting_ms
        self._visibility_m = visibility_m
        self._condition = condition_str
        self._data_source = source

    # The necessary getters for this object (since most is based on api), are listed below:

    @property
    def cloud_cover(self):
        return self._cloud_cover_pct

    @property
    def wind_speed(self):
        return self._wind_speed_ms

    @property
    def wind_gusts(self):
        return self._wind_gust_speed_ms

    @property
    def condition(self):
        return self._condition

    # Date-awareness getters, mirroring CurrentSunState's pattern so the planner
    # can ask the same shape of questions ("what hour?", "what day-of-year?") of
    # both objects without special-casing.

    @property
    def valid_time(self):
        return self._valid_time

    @property
    def valid_day_of_year(self):
        return self._valid_time.timetuple().tm_yday

    @property
    def valid_hour(self):
        return self._valid_time.hour

    @property
    def valid_minute(self):
        return self._valid_time.minute

    @property
    def valid_date(self):
        return self._valid_time.date()


class Sensor:
    """
    Sensor stores the camera geometry values that drive grid spacing.
    The engine uses the cross-track FOV to determine line-to-line offset
    distance, while QGroundControl remains responsible for waypoint headings.
    """

    def __init__(
        self,
        cross_track_fov_deg,
        along_track_fov_deg,
        desired_overlap_pct,
        off_nadir_deg=40,
        sensor_name=None,
    ):

        self._cross_track_fov_deg = cross_track_fov_deg
        self._along_track_fov_deg = along_track_fov_deg
        self._desired_overlap_pct = desired_overlap_pct
        self._off_nadir_deg = off_nadir_deg
        self._sensor_name = sensor_name

    @property
    def cross_track_fov(self):
        return self._cross_track_fov_deg

    @property
    def along_track_fov(self):
        return self._along_track_fov_deg

    @property
    def desired_overlap(self):
        return self._desired_overlap_pct

    @property
    def off_nadir(self):
        return self._off_nadir_deg

    @property
    def sensor_name(self):
        return self._sensor_name


class Waypoint:
    """
    Mission candidates consist of useful data regarding the aircraft,
    weather, legality, glint, etc, all culminating to a final score.
    However, at its score, a mission candidate requires a list of way-
    points in order to command the UAV to the proper places along
    the route.
    The waypoint class as needed for V1 is defined here
    """

    """
    The constructor contains important but basic parameters for V1,
    basically what you would find as settings for a waypoint in QGC,
    you'll find in this constructor.
    """

    def __init__(
        self,
        waypoint_id: str,
        latitude_decimal,
        longitude_decimal,
        altitude_m,
        speed_ms,
        action,
        notes=None,
        target_name=None,
    ):

        self._waypoint_id = waypoint_id
        self._latitude_decimal = latitude_decimal
        self._longitude_decimal = longitude_decimal
        self._altitude_m = altitude_m
        self._speed_ms = speed_ms
        self.action = action
        self.notes = notes
        self.target_name = target_name

        """
        Parameters for the way point explained:
        1. Waypoint ID: Formatted as WPXXX, gives a numerical id to each WP
        2. latitude: Waypoint's latitude coordinates in decimal form
        3. longitude: Waypoint's longitude coordinate in decimal form
        4. altitude: aircraft altitude at that waypoint
        5. speed: aircraft speed at that waypoint
        6. action: Most important param, a string used to pass to other functions so the engine can make decisions on a per-point basis
        7. notes: human readable notes about a waypoint, OPTIONAL
        8. target_name, an optional but more human readable name for a waypoint besides its ID
        """

        # Allowance to referral to each point as a Shapely point

    @property
    def point(self):
        return Point(self._longitude_decimal, self._latitude_decimal)

    @property
    def latitude(self):
        return self._latitude_decimal

    @property
    def longitude(self):
        return self._longitude_decimal

    @property
    def altitude(self):
        return self._altitude_m

    @property
    def speed(self):
        return self._speed_ms

    @property
    def waypoint_ID(self):
        return self._waypoint_id

    def to_CSV_row(self):
        return [
            self._waypoint_id,
            self._longitude_decimal,
            self._latitude_decimal,
            self._altitude_m,
            self._speed_ms,
            self.action,
            self.notes,
            self.target_name,
        ]

    def is_m1_overflight(self):
        return self.action == "m1_overflight" or self.target_name == "M1"


class MissionRequest:

    # Mission Request object no longer holds line length/grid_width etc... params
    def __init__(
        self,
        mission_name,
        launch_waypoint,
        land_waypoint,
        altitude_m,
        valid_date: datetime,
        require_m1_overflight=True,
        grid_orientation_deg=None,
        notes=None,
        included_target_waypoints=None,
    ):

        if not isinstance(valid_date, datetime):
            raise TypeError("valid_time must be a datetime.datetime instance")

        self._mission_name = mission_name
        self._launch_waypoint = launch_waypoint
        self._land_waypoint = land_waypoint
        self._altitude_m = altitude_m
        self._date = valid_date
        self._require_M1_overflight = require_m1_overflight
        self._grid_orientation_deg = grid_orientation_deg
        self._notes = notes
        self._included_target_waypoints = included_target_waypoints

    @property
    def day_of_year(self):
        return self._date.timetuple().tm_yday

    @property
    def launch_point(self):
        return self._launch_waypoint.point

    @property
    def land_point(self):
        return self._land_waypoint.point

    @property
    def target_point(self):

        if self._included_target_waypoints is not None:
            return [wp.point for wp in self._included_target_waypoints]

        return []

    @property
    def altitude(self):
        return self._altitude_m

    @property
    def grid_orientation(self):
        return self._grid_orientation_deg

    @property
    def desired_heading(self):
        return self._grid_orientation_deg


class CandidatePlan:

    # For V1, these are the only objects we will need passed as parameters:
    def __init__(
        self,
        missionRequest,
        aircraft,
        currentSunState,
        weather,
        sensor=None,
        waypoints=None,
    ):

        self._mission_request = missionRequest
        self._aircraft = aircraft
        self._currentSunState = currentSunState
        self._weather = weather
        self._sensor = sensor

        if waypoints is None:
            self._waypoints = []

        else:
            self._waypoints = waypoints

        self._total_route_distance_m = None
        self._usable_endurance_distance_m = None
        self._grid_area_m2 = None
        self._offset_distance_m = None
        self._line_length_m = None
        self._total_lines = None
        self._science_lines = None
        self._traverse_lines = None
        self._offset_lines = None

        self._estimated_duration_min = None
        self._battery_margin_min = None

        self._passes_over_m1 = False
        self._is_legal = None
        self._is_aircraft_feasible = None

        self._score = None
        self._validation_messages = []

    # V1 properties for the candidate plan are listed below:

    @property
    def mission_request(self):
        return self._mission_request

    @property
    def aircraft(self):
        return self._aircraft

    @property
    def sun_state(self):
        return self._currentSunState

    @property
    def weather(self):
        return self._weather

    @property
    def sensor(self):
        return self._sensor

    @property
    def waypoints(self):
        return self._waypoints

    @property
    def total_route_distance_m(self):
        return self._total_route_distance_m

    @property
    def usable_endurance_distance_m(self):
        return self._usable_endurance_distance_m

    @property
    def grid_area_m2(self):
        return self._grid_area_m2

    @property
    def offset_distance_m(self):
        return self._offset_distance_m

    @property
    def line_length_m(self):
        return self._line_length_m

    @property
    def total_lines(self):
        return self._total_lines

    @property
    def science_lines(self):
        return self._science_lines

    @property
    def traverse_lines(self):
        return self._traverse_lines

    @property
    def offset_lines(self):
        return self._offset_lines

    """
    Below are the methods needed or that will be convenient during the 
    construction of V1
    """

    def add_waypoint(self, new_waypoint):
        self._waypoints.append(new_waypoint)
        return

    def add_validation_message(self, new_message):
        self._validation_messages.append(new_message)
        return

    def set_grid_metrics(self, metrics):
        self._total_route_distance_m = metrics.get("total_route_distance_m")
        self._usable_endurance_distance_m = metrics.get("usable_endurance_distance_m")
        self._grid_area_m2 = metrics.get("grid_area_m2")
        self._offset_distance_m = metrics.get("offset_distance_m")
        self._line_length_m = metrics.get("line_length_m")
        self._total_lines = metrics.get("total_lines")
        self._science_lines = metrics.get("science_lines")
        self._traverse_lines = metrics.get("traverse_lines")
        self._offset_lines = metrics.get("offset_lines")
        return

    def has_m1_overflight(self):
        for i in range(0, len(self._waypoints)):
            if self._waypoints[i].is_m1_overflight():
                return True

        return False
