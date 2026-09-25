"""
The engine's core classes. Each is meant to be used elsewhere in the project; this file
imports nothing from the engine.

    - Aircraft (performance numbers the math consumes: endurance, speeds, turn penalty, etc.)
    - Vehicle (an Aircraft plus its MAVLink identity: vehicle type, firmware, VTOL, hover speed)
    - CurrentSunState (the sun at the mission time -- azimuth, elevation, zenith)
    - Weather (conditions at the mission time, from NWS or the clear-sky stub)
    - Sensor (camera viewing geometry and overlaps)
    - Waypoint (the smallest unit of a route)
    - MissionRequest (launch, land and M1 waypoints, altitude and datetime for one mission)
    - CandidatePlan (bringing it all together: the route, its metrics, and its score)
"""

import warnings
from datetime import datetime

from shapely.geometry import Point


class Aircraft:
    """
    An aircraft's performance numbers, as the engine's math consumes them. These differ
    between a fixed wing and a hex/quad/octocopter.
    """

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

    # Getters for each constructor parameter, for passing values into the math and to
    # other functions.

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

    # Setters for each constructor parameter, meant only for correcting a user input error.

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


"""
QGC JSON uses special integers to denote firmware and vehicle types. See the following
link for the tables of vehicle and firmware types recognized by the MAVLink protocol. The
sets below are the firmwares and vehicle types the CFE is designed for:
https://mavlink.io/en/messages/common.html
"""

VALID_FIRMWARE_TYPES = frozenset({0, 3, 5, 6, 7, 12})
VALID_VEHICLE_TYPES = frozenset({1, 2, 13, 14, 21, 22, 43})
MULTIROTOR_TYPES = {2, 13, 14, 43}
VTOL_TYPES = {21, 22}


VALID_FIRMWARE_TYPES_DICT = {"Generic Autopilot (Full Support)": 0,
                             "Ardupilot": 3,
                             "Autopilot w/only Waypoint Support": 5,
                             "Autopilot w/only Waypoint & Nav Support": 6,
                             "Generic Autopilot Full Cmd Set": 7,
                             "Px4": 12}

VALID_VEHICLE_TYPES_DICT = {"Fixed Wing": 1,
                            "Quadrotor": 2,
                            "Hexrotor": 13,
                            "Octorotor": 14,
                            "TiltRotor VTOL": 21,
                            "FixedRotor VTOL": 22,
                            "Generic Multirotor": 43
                            }


class Vehicle(Aircraft):
    """
    An Aircraft plus the MAVLink identity the .plan writer branches on. An invalid vehicle
    type raises; an invalid firmware type warns and defaults to PX4 (12).
    """

    def __init__(self,
                 endurance_min,
                 wind_rating_ms,
                 climb_rate_ms,
                 descent_rate_ms,
                 turn_radius_m,
                 turn_penalty_s,
                 min_ground_speed_ms,
                 cruise_speed_ms,
                 vehicle_type,
                 firmware_type,
                 hover_speed_ms=0
                 ):

        super().__init__(endurance_min,
                         wind_rating_ms,
                         climb_rate_ms,
                         descent_rate_ms,
                         turn_radius_m,
                         turn_penalty_s,
                         min_ground_speed_ms,
                         cruise_speed_ms)

        # Setting Vehicle or aborting
        if vehicle_type in VALID_VEHICLE_TYPES:
            self._vehicle_type = vehicle_type
        else:
            raise ValueError("Invalid vehicle type detected, please retry with a valid vehicle type.")

        # Setting Firmware type or defaulting
        if firmware_type in VALID_FIRMWARE_TYPES:
            self._firmware_type = firmware_type
        else:
            self._firmware_type = 12
            warnings.warn("Warning: Unknown firmware type detected, defaulting to PX4.")

        self._hover_speed_ms = hover_speed_ms

        if vehicle_type in MULTIROTOR_TYPES:
            # A multirotor takes off vertically but is not a VTOL: it never transitions.
            self._vertical_takeoff = True
            self._is_vtol = False

        elif vehicle_type in VTOL_TYPES:
            # VTOLs have both a hover speed and a cruising speed
            self._vertical_takeoff = True
            self._is_vtol = True

        else:
            self._vertical_takeoff = False
            self._is_vtol = False
            # Manually setting hover speed to zero for fixed wing aircraft in case of a user mistake.
            # Fixed wings cannot have a non-zero hover speed.
            self._hover_speed_ms = 0

    # Getters and setters for the hover speed, hover capability, and the vehicle and firmware
    # types are below.
    # NOTE: there are no setters for hover speed or hover capability, on purpose. The vehicle
    # type and hover capability directly decide the kind of plan sent to QGC, so they are set
    # once, by the constructor that validates them, and never patched afterwards.

    @property
    def hover_speed_ms(self):
        return self._hover_speed_ms

    @property
    def can_hover(self):
        return self._vertical_takeoff

    @property
    def vehicle_type(self):
        for value in VALID_VEHICLE_TYPES_DICT.values():
            if value == self._vehicle_type:
                return value

    @property
    def vehicle_type_name(self):
        for key, value in VALID_VEHICLE_TYPES_DICT.items():
            if value == self._vehicle_type:
                return key

    @property
    def firmware_type(self):
        for value in VALID_FIRMWARE_TYPES_DICT.values():
            if value == self._firmware_type:
                return value

    @property
    def firmware_type_name(self):
        for key, value in VALID_FIRMWARE_TYPES_DICT.items():
            if value == self._firmware_type:
                return key

    @property
    def is_VTOL(self):
        return self._is_vtol

    def set_firmware_type(self, firmware_type: int):
        if firmware_type in VALID_FIRMWARE_TYPES:
            self._firmware_type = firmware_type
        else:
            self._firmware_type = 12
            warnings.warn("Warning: Unknown firmware type detected, defaulting to PX4.")


class CurrentSunState:
    """
    The sun at the mission time: azimuth, elevation and zenith, plus the day and time they
    were computed for. Built by sun.create_sun_state.
    """

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
    Weather conditions at the mission time, passed around as one object. The NWS API calls
    are made in weather.py, which returns one of these; planner falls back to a clear-sky
    stub when it cannot. Because NWS forecasts about a week ahead, plans for future dates
    are built and ranked just like any other.
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
        wind_is_measured=False,
        stale_fields=None,
        source="STUB",
    ):
        # Both default FAIL-SAFE. Omitting wind_is_measured means "provenance unknown",
        # which any consumer must treat as unverified, never as measured calm. A caller
        # must positively CLAIM measured wind; it can never be acquired by forgetting an
        # argument.

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
        self._measured_wind = wind_is_measured
        # Normalized so consumers never have to null-check before asking "is X stale?"
        self._stale_fields = frozenset(stale_fields) if stale_fields else frozenset()
        self._data_source = source

    # Getters (the values mostly come from the NWS API):

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
    def wind_direction(self):
        return self._wind_direction_deg

    # PROVENANCE. Safety math must be able to tell "measured calm" from "no idea".
    # DEFAULT_ZERO_WIND makes an absent wind field look like a dead-calm day, which is
    # the most PERMISSIVE possible input to any safety check -- exactly backwards. Nothing
    # reads these yet; their consumers (the pilot-notes report, any Step E gate) must use
    # them to refuse to present assumed conditions as measured.

    @property
    def wind_is_measured(self):
        return self._measured_wind

    @property
    def stale_fields(self):
        return self._stale_fields

    def is_stale(self, field_name):
        return field_name in self._stale_fields

    @property
    def source(self):
        return self._data_source

    @property
    def visibility(self):
        return self._visibility_m

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

    `mounting` records WHICH AXIS THE CAMERA IS TILTED ON (see the mounting note in
    geo.py). It is data, not dispatch -- geo.py implements the along-track case only,
    and planner._build_grid_for_orientation raises if a Sensor declares anything else.
    It exists because the V2C refactor was caused by a mount change that no code
    recorded: the assumption lived silently inside two formula bodies.
    """

    def __init__(
        self,
        cross_track_fov_deg,
        along_track_fov_deg,
        desired_crosstrack_overlap_pct,
        desired_alongtrack_overlap_pct,
        off_nadir_deg,
        mounting=None,
        sensor_name=None,
    ):

        self._cross_track_fov_deg = cross_track_fov_deg
        self._along_track_fov_deg = along_track_fov_deg
        self._desired_cross_track_overlap_pct = desired_crosstrack_overlap_pct
        self._desired_along_track_overlap_pct = desired_alongtrack_overlap_pct
        self._off_nadir_deg = off_nadir_deg
        self._mounting = mounting
        self._sensor_name = sensor_name

    @property
    def cross_track_fov(self):
        return self._cross_track_fov_deg

    @property
    def along_track_fov(self):
        return self._along_track_fov_deg

    @property
    def cross_track_overlap(self):
        return self._desired_cross_track_overlap_pct

    @property
    def along_track_overlap(self):
        return self._desired_along_track_overlap_pct

    @property
    def off_nadir(self):
        return self._off_nadir_deg

    @property
    def mounting(self):
        return self._mounting

    @property
    def sensor_name(self):
        return self._sensor_name


class Waypoint:
    """
    A mission candidate carries data about the aircraft, weather, legality, glint, etc.,
    all culminating in a final score. At its core, though, it needs a list of waypoints to
    command the UAV to the proper places along the route.

    The constructor takes roughly what you would find as settings for a waypoint in QGC:
      1. waypoint_id: formatted as WPXXX, gives a numerical id to each WP
      2. latitude: the waypoint's latitude in decimal form
      3. longitude: the waypoint's longitude in decimal form
      4. altitude: aircraft altitude at that waypoint
      5. speed: aircraft speed at that waypoint
      6. action: the most important param -- a string the engine passes to other functions
         so it can make decisions on a per-point basis
      7. notes: human-readable notes about a waypoint, OPTIONAL
      8. target_name: an optional, more human-readable name for a waypoint than its ID
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
        self._action = action
        self.notes = notes
        self.target_name = target_name

    # The waypoint as a Shapely Point.
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

    @property
    def action(self):
        return self._action

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

    def set_action(self, new_action):
        self._action = new_action
        return


class MissionRequest:
    """
    One mission's request: launch, land and M1 waypoints, altitude and datetime. It no
    longer holds line length, grid width, etc.; the grid is sized from the budget.
    """

    def __init__(
        self,
        mission_name,
        launch_waypoint,
        land_waypoint,
        m1_waypoint,
        altitude_m,
        valid_time: datetime,
        require_m1_overflight=True,
        grid_orientation_deg=None,
        notes=None,
        included_target_waypoints=None,
    ):

        if not isinstance(valid_time, datetime):
            raise TypeError("valid_time must be a datetime.datetime instance")

        self._mission_name = mission_name
        self._launch_waypoint = launch_waypoint
        self._land_waypoint = land_waypoint
        self._m1_waypoint = m1_waypoint
        self._altitude_m = altitude_m
        self._date = valid_time
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

    @property
    def launch_wp(self):
        return self._launch_waypoint

    @property
    def land_wp(self):
        return self._land_waypoint

    @property
    def m1_wp(self):
        return self._m1_waypoint


class CandidatePlan:
    """
    Bringing it all together: one scored plan -- the route, the objects it was built from,
    and every metric the engine computed for it. planner builds it; outputs renders it.
    """

    def __init__(
        self,
        name: str,
        mission_request,
        aircraft,
        current_sun_state,
        weather,
        chosen_orientation_deg,
        sensor=None,
        waypoints=None,
    ):
        self._name = name
        self._mission_request = mission_request
        self._aircraft = aircraft
        self._current_sun_state = current_sun_state
        self._weather = weather
        self._chosen_orientation_deg = chosen_orientation_deg
        self._total_flight_distance_m = None
        self._sensor = sensor

        if waypoints is None:
            self._waypoints = []

        else:
            self._waypoints = waypoints

        self._total_grid_distance_m = None
        self._camera_trigger_distance_m = None
        self._grid_budget_m = None
        self._usable_endurance_distance_m = None
        self._grid_area_m2 = None
        self._offset_distance_m = None
        self._line_length_m = None
        self._total_lines = None
        self._science_lines = None
        self._traverse_lines = None
        self._offset_lines = None
        self._parallax_m = None
        self._cross_track_width_m = None

        self._estimated_duration_min = None
        self._estimated_transit_duration_min = None
        self._estimated_grid_duration_min = None
        self._battery_margin_min = None

        self._passes_over_m1 = False
        self._is_legal = None
        self._is_aircraft_feasible = None

        self._score = None
        self._validation_messages = []

        self._crab_deg = None
        self._boresight_error_deg = None

        self._worst_distance_m = None
        self._worst_bearing_deg = None
        self._return_min = None
        self._reserve_min = None

        self._departure_bearing_deg = None
        self._approach_bearing_deg = None

    # Properties:

    @property
    def mission_request(self):
        return self._mission_request

    @property
    def aircraft(self):
        return self._aircraft

    @property
    def sun_state(self):
        return self._current_sun_state

    @property
    def weather(self):
        return self._weather

    @property
    def total_flight_distance(self):
        return self._total_flight_distance_m

    @property
    def sensor(self):
        return self._sensor

    @property
    def waypoints(self):
        return self._waypoints

    @property
    def total_grid_distance_m(self):
        return self._total_grid_distance_m

    @property
    def usable_endurance_distance_m(self):
        """The aircraft's full usable distance -- what the BATTERY affords."""
        return self._usable_endurance_distance_m

    @property
    def grid_budget_m(self):
        """What was left for the GRID after the transit was reserved (J-4)."""
        return self._grid_budget_m

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

    @property
    def aircraft_feasibility(self):
        return self._is_aircraft_feasible

    @property
    def legality(self):
        return self._is_legal

    @property
    def validation_messages(self):
        return self._validation_messages

    # V2C viewing-geometry metrics. Both are measured by geo during grid assembly and
    # arrive in the same metrics dict as the fields above, so they are set by
    # set_grid_metrics. Reporting only in V2C-1: parallax is NOT corrected for yet.

    @property
    def parallax_m(self):
        return self._parallax_m

    @property
    def cross_track_width_m(self):
        return self._cross_track_width_m

    # V2C-2 viewing geometry + RTH assessment. STORED FOR REPORTING ONLY -- outputs and
    # the terminal summary read these. validator, when it is written, must NOT: it has to
    # re-derive every one of them from the plan's own waypoints, so a bug in the builder
    # cannot certify itself.
    #
    # ⚠️ 2026-09-08: "reporting only" is now the WHOLE story. The RTH gate that would have
    # consumed these is cancelled -- aircraft compensate for wind in flight, so the engine
    # neither vetoes nor reshapes a plan on wind. Their destination is the pilot-notes
    # document. Nothing populates them yet; every one reads None on a plan built today.

    @property
    def crab_deg(self):
        return self._crab_deg

    @property
    def boresight_error_deg(self):
        return self._boresight_error_deg

    @property
    def worst_return_distance_m(self):
        return self._worst_distance_m

    @property
    def worst_return_bearing_deg(self):
        return self._worst_bearing_deg

    @property
    def return_min(self):
        return self._return_min

    @property
    def required_reserve_min(self):
        return self._reserve_min

    # J-4.5 transit bearings. Unlike the C-2 figures above these ARE populated on every
    # plan built today, and they are pure geometry rather than weather -- the directions
    # the route already commits the aircraft to. Reporting only: they reach the terminal
    # summary and the pilot-notes document, never the .plan (writing a heading there would
    # command a yaw, which the null-yaw decision rules out).
    @property
    def departure_bearing_deg(self):
        return self._departure_bearing_deg

    @property
    def approach_bearing_deg(self):
        return self._approach_bearing_deg

    @property
    def chosen_orientation(self):
        return self._chosen_orientation_deg

    @property
    def name(self):
        return self._name

    @property
    def duration(self):
        return self._estimated_duration_min

    @property
    def margin(self):
        return self._battery_margin_min

    @property
    def score(self):
        return self._score

    @property
    def camera_trigger_distance_m(self):
        return self._camera_trigger_distance_m
    
    @property
    def estimated_transit_duration_min(self):
        return self._estimated_transit_duration_min
    
    @property
    def estimated_grid_duration_min(self):
        return self._estimated_grid_duration_min
            

    # Methods and setters:

    def add_waypoint(self, new_waypoint):
        self._waypoints.append(new_waypoint)
        return

    def add_validation_message(self, new_message):
        self._validation_messages.append(new_message)
        return

    def set_grid_metrics(self, metrics):
        self._total_grid_distance_m = metrics.get("total_grid_distance_m")
        # J-4: geo reports the budget it was GIVEN (endurance minus transit). The
        # aircraft's full usable distance is a different number and arrives from the
        # hub via set_usable_endurance_distance_m -- do not read it out of the metrics.
        self._grid_budget_m = metrics.get("grid_budget_m")
        self._grid_area_m2 = metrics.get("grid_area_m2")
        self._offset_distance_m = metrics.get("offset_distance_m")
        self._line_length_m = metrics.get("line_length_m")
        self._total_lines = metrics.get("total_lines")
        self._science_lines = metrics.get("science_lines")
        self._traverse_lines = metrics.get("traverse_lines")
        self._offset_lines = metrics.get("offset_lines")
        self._parallax_m = metrics.get("sensor_parallax_m")
        self._cross_track_width_m = metrics.get("cross_track_swath_m")
        self._camera_trigger_distance_m = metrics.get("camera_trigger_distance_m")
        return

    def has_m1_overflight(self):
        for i in range(0, len(self._waypoints)):
            if self._waypoints[i].is_m1_overflight():
                return True

        return False

    def set_duration_min(self, mission_duration_min):
        self._estimated_duration_min = mission_duration_min
        return

    def set_battery_margin_min(self, mission_battery_margin_min):
        self._battery_margin_min = mission_battery_margin_min
        return

    def set_score(self, mission_score):
        self._score = mission_score
        return

    def set_orientation(self, new_orientation):
        self._chosen_orientation_deg = new_orientation
        return

    def change_name(self, new_name):
        self._name = new_name
        return

    def set_total_flight_distance_m(self, total_flight_distance_m):
        self._total_flight_distance_m = total_flight_distance_m
        return

    def set_usable_endurance_distance_m(self, usable_endurance_distance_m):
        self._usable_endurance_distance_m = usable_endurance_distance_m
        return
    
    def set_transit_endurance_min(self, transit_endurance_min):
        self._estimated_transit_duration_min = transit_endurance_min
        return
    
    def set_grid_endurance_min(self, grid_endurance_min):
        self._estimated_grid_duration_min = grid_endurance_min
        return

    def set_transit_bearings(self, departure_bearing_deg, approach_bearing_deg):
        self._departure_bearing_deg = departure_bearing_deg
        self._approach_bearing_deg = approach_bearing_deg
        return

    # V2C-2 setters for the viewing geometry and RTH figures (reporting only):

    def set_aircraft_feasible(self, feasibility):
        self._is_aircraft_feasible = feasibility
        return

    def set_viewing_geometry(self, crab_deg, boresight_error_deg):
        self._crab_deg = crab_deg
        self._boresight_error_deg = boresight_error_deg
        return

    def set_rth_assessment(self, worst_distance, worst_bearing, return_min, reserve_min):
        self._worst_distance_m = worst_distance
        self._worst_bearing_deg = worst_bearing
        self._return_min = return_min
        self._reserve_min = reserve_min
        return
