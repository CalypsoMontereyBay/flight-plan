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
from aircraft_math import max_planned_distance_m, route_duration_min, battery_margin_min
import itertools

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
    CONST.V1_DEFAULT_LAND_ALTITUDE_m,
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
    m1_waypoint=_V1_M1_Waypoint,
    altitude_m=CONST.V1_DEFAULT_AIRCRAFT_ALTITUDE_m,
    valid_time=mission_date,
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

# Setting the mission azimuth
_V1_mission_sun_azimuth = _V1_mission_sun_state.azimuth

"""
HELPER FUNCTIONS FOR POPULATING THE CANDIDATE PLAN BELOW
In Order:


1. _candidate_orientation(): takes an azimuth angle and returns two heading "orientations"
Both orientations are valid for "science" lines, but depending on all the other factors, one will score
better than the other. returns both in a tuple for passing around and proper security.
These values are then passed as potential_orientation_deg params in other helpers.

2. _score_glint(): Returns how far off one leg of a candidate orientation is
off from the 135 standard. Scores follow a golf paradigm (lower = better). A score of 0 means
135 degrees exactly. No candidate orientation can earn lower than zero. If scores are equal, including for
two candidates that earn a score of zero, a tiebreaker (which orientation's corner is closest to the launch),
is used. This is the tiebreaker because if the corner is closer, it is more likely that the grid is also larger.

3. _score_candidate(): scores a candidate based on the
deviation from the 135 degree ideal based on their science leg. 

4. _passes_glint_gate(): checks if the score of a candidate is within a certain margin, plans are rejected if this
function returns False, used in function #6.

5. _build_grid_for_orientation(): takes an orientation and uses the lawnmower route
building function to construct a grid

6. _pick_best_orientation(): takes the two candidates and picks the best grid for the mission, also handles
tie breaking

7. _reorient_to_launch(): checks if the normal orientation of the grid or the reverse orientation (H + 180)
is more efficient by checking the distance of the launch point to both the first and last waypoints of the grid.
The grid is then either left alone or reversed accordingly

8. _angular_distance(heading1_deg, heading2_deg): returns the angular distance between two angles

9. _classify_waypoints(): Walks the route and tags each one according to the waypoint actions found in constants.py. Does final checks (prepend & append) the launch and land waypoints in their
final positions. Returns a list of waypoint objects that is "the route."
"""


def _candidate_orientation(sun_az):

    # Two possible heading orientations for minimizing glint, they will
    # be used as "paths" and then the score for V1 is based off of glint minimization.

    potential_orientation_one = (
        sun_az + CONST.AZIMUTH_ONE_THIRTY_FIVE
    ) % CONST.AZIMUTH_THREE_SIXTY

    potential_orientation_two = (
        sun_az - CONST.AZIMUTH_ONE_THIRTY_FIVE
    ) % CONST.AZIMUTH_THREE_SIXTY

    return (potential_orientation_one, potential_orientation_two)


# Glint scoring function used to rank plans for V1.
# THE ONLY RANKING FUNCTION FOR V1, OTHERS WILL FOLLOW
# track heading is an az candidate from the function above
def _score_glint(potential_orientation_deg, sun_az_deg):
    """
    Golf-style glint penalty: 0 = perfect (track is exactly 135 off sun-azimuth),
    higher = worse. Symmetric is +- 135 since the camera does not care which way it is tilted.
    (The aircraft is what maintains the azimuth, not the cam).

    track_heading: heading flown on the leg: (0..360)
    sun_az: sun azimuth at the mission time: (0..360)
    """

    # finds how far off each azimuth candidate heading is from the desired 0 score.
    azimuth_delta = (potential_orientation_deg - sun_az_deg) % CONST.AZIMUTH_THREE_SIXTY

    # the lower of the values is the winner and is returned
    return min(
        (abs(azimuth_delta - CONST.AZIMUTH_ONE_THIRTY_FIVE)),
        (abs(azimuth_delta - CONST.AZIMUTH_TWO_TWENTY_FIVE)),
    )


def _score_candidate(potential_orientation_candidate_deg, sun_az):

    # Calculates the science leg score of an orientation
    science_leg_score = _score_glint(potential_orientation_candidate_deg, sun_az)

    return science_leg_score


def _passes_glint_gate(score):

    return score <= CONST.V1_GLINT_TOLERANCE_DEG


def _build_grid_for_orientation(
    orientation_deg, mission_request: MissionRequest, payload: Sensor, usable_distance_m
):
    """
    Thin wrapper around geo.make_lawnmower_grid_through_m1 that pulls the grid
    parameters out of the mission/payload objects for a single orientation.

    Returns geo's (flight_lines, route_points, metrics) tuple unchanged.
    """
    return make_lawnmower_grid_through_m1(
        mission_request.m1_wp,
        orientation_deg,
        usable_distance_m,
        mission_request.altitude,
        payload.cross_track_fov,
        payload.desired_overlap,
        off_nadir_deg=payload.off_nadir,
    )


def _pick_best_orientation(
    candidates: tuple,
    sun_az_deg,
    mission_request: MissionRequest,
    payload: Sensor,
    usable_distance_m,
):
    """
    Score both candidate science headings (glint, science-leg only), keep the
    ones that clear the glint gate, build each survivor's grid, and return the
    winner together with its already-built grid so build_candidate_plan never
    rebuilds.

    Tiebreak (the V1 norm, since both ideal candidates score 0): choose the
    orientation whose nearest grid endpoint is closest to the launch point,
    which minimizes the transit leg flown from launch into the grid.

    Returns:
        (winning_orientation_deg, winning_score, flight_lines, route_points, metrics)
    """
    launch_point = mission_request.launch_point

    # Collect (orientation, score) for every candidate that clears the gate.
    gate_passers = []
    for candidate_orientation in candidates:
        candidate_score = _score_candidate(candidate_orientation, sun_az_deg)
        if _passes_glint_gate(candidate_score):
            gate_passers.append((candidate_orientation, candidate_score))

    if len(gate_passers) == 0:
        raise ValueError("No candidate orientations passed the glint gate!")

    # Build each survivor's grid once and keep the one with the closest entry
    # corner. The running-best comparison covers the 1-passer and multi-passer
    # cases uniformly, so no branching is needed here or in the caller.
    best_entry = (
        None  # (corner_dist, orientation, score, flight_lines, route_points, metrics)
    )

    for orientation_deg, orientation_score in gate_passers:
        flight_lines, route_points, metrics = _build_grid_for_orientation(
            orientation_deg, mission_request, payload, usable_distance_m
        )
        nearest_corner_dist_m = min(
            distance_between(launch_point, route_points[0]),
            distance_between(launch_point, route_points[-1]),
        )

        if best_entry is None or nearest_corner_dist_m < best_entry[0]:
            best_entry = (
                nearest_corner_dist_m,
                orientation_deg,
                orientation_score,
                flight_lines,
                route_points,
                metrics,
            )

    _, winning_orientation, winning_score, flight_lines, route_points, metrics = (
        best_entry
    )

    return (winning_orientation, winning_score, flight_lines, route_points, metrics)


def _reorient_to_launch(route_points: list, m1_idx, launch_point: Waypoint):

    last_wp_dist_to_launch = distance_between(launch_point, route_points[-1])

    first_wp_dist_to_launch = distance_between(launch_point, route_points[0])

    if last_wp_dist_to_launch < first_wp_dist_to_launch:

        updated_route_list = route_points[::-1]
        updated_m1_idx = len(route_points) - 1 - m1_idx

        return (updated_route_list, updated_m1_idx)
    else:
        return (route_points, m1_idx)


def _angular_distance(heading1_deg, heading2_deg):

    return abs(
        (
            ((heading2_deg - heading1_deg) + CONST.DEGREE_ONE_EIGHTY)
            % CONST.FULL_CIRCLE_DEG
            - CONST.DEGREE_ONE_EIGHTY
        )
    )


def _classify_waypoints(
    route_points: list,
    m1_route_idx,
    launch_wp: Waypoint,
    land_wp: Waypoint,
    altitude_m,
    cruise_speed_ms,
    winning_orientation,
):

    # Establish a new route list that has each waypoint tagged, as well as a global index
    tagged_route_list = []

    # Sets the launch action then adds it to the list
    if launch_wp.action != CONST.WAYPOINT_ACTION_LAUNCH:
        launch_wp.set_action(CONST.WAYPOINT_ACTION_LAUNCH)

    tagged_route_list.append(launch_wp)

    if land_wp.action != CONST.WAYPOINT_ACTION_LAND:
        land_wp.set_action(CONST.WAYPOINT_ACTION_LAND)
        
    leg_number = 0

    for leg in itertools.batched(route_points, CONST.V1_POINTS_PER_LINE):

        leg_heading = bearing_between(leg[0], leg[-1])

        # A leg is a science leg if the current heading is the mission orientation that minimizes glint (H)

        if _angular_distance(leg_heading, winning_orientation) < CONST.DEGREE_NINETY:

            is_science = True

        else:

            is_science = False
            
        leg_start = leg_number * CONST.V1_POINTS_PER_LINE
            
        for local_idx, point in enumerate(leg):
            
            global_index = leg_start + local_idx
            
            if global_index == m1_route_idx:
                
                action = CONST.WAYPOINT_ACTION_M1_OVERFLIGHT
                target_name = "M1"
                
            elif local_idx in (0, (CONST.V1_POINTS_PER_LINE -1)):
                
                action = CONST.WAYPOINT_ACTION_TURN
                target_name = None
                
            elif local_idx == (CONST.V1_POINTS_PER_LINE // 2):
                
                action = CONST.WAYPOINT_ACTION_LINE_LABEL
                target_name = None
                
            elif is_science and local_idx == 1:
                    action = CONST.WAYPOINT_ACTION_COLLECT_START
                    target_name = "Camera On"
                    
            elif is_science and local_idx == 3:
                    action = CONST.WAYPOINT_ACTION_COLLECT_STOP
                    target_name = "Camera Off"
                    
            else:
                
                action = CONST.WAYPOINT_ACTION_TRANSIT
                target_name = None
                
        
            tagged_route_list.append(
                Waypoint(
                    f"WP{global_index + 1:03d}",
                    point.y,
                    point.x,
                    altitude_m,
                    cruise_speed_ms,
                    action,
                    target_name=target_name,
                )
            )
            
        leg_number += 1    

    tagged_route_list.append(land_wp)

    return tagged_route_list


"""
Putting it all together, build_candidate_plan() uses all of the pre-established
objects and sends their data through the helpers as needed. Below is what happens in
order:

1. Identify candidates then pick the best orientation

2. make a lawnmower grid through m1.

3. reorient to the launch to get the shortest traversal to the grid possible.

4. classify each waypoint now that proper orientation has been established.

5. construct the candidate plan object with helpers and getters/setters.

6. return a fully finished candidate plan.

"""


def build_candidate_plan(
    mission_aircraft: Aircraft,
    mission_aircraft_endurance_m,
    payload: Sensor,
    mission_request: MissionRequest,
    mission_weather: Weather,
    mission_azimuth,
    mission_sun_state,
    candidate_name,
):

    # Step 1, generate the potential orientation candidates
    mission_potential_orientations = _candidate_orientation(mission_azimuth)

    # Step 2, pick the winning orientation AND reuse the grid the picker built
    (
        mission_orientation,
        mission_orientation_score,
        flight_lines,
        route_points,
        metrics,
    ) = _pick_best_orientation(
        mission_potential_orientations,
        mission_azimuth,
        mission_request,
        payload,
        mission_aircraft_endurance_m,
    )

    # Step 3, reorient the grid so the route starts at the corner closest to launch
    route_shapely_waypoints, m1_index = _reorient_to_launch(
        route_points, metrics["m1_route_index"], mission_request.launch_point
    )

    # Step 4, walk the route and classify each waypoint and assign it an index:

    mission_route_list_classified = _classify_waypoints(
        route_shapely_waypoints,
        m1_index,
        mission_request.launch_wp,
        mission_request.land_wp,
        mission_request.altitude,
        mission_aircraft.vehicle_cruise_speed,
        mission_orientation,
    )

    # Step 5, build the candidate plan

    candidate_plan = CandidatePlan(
        candidate_name,
        mission_request,
        mission_aircraft,
        mission_sun_state,
        mission_weather,
        mission_orientation,
        payload,
        mission_route_list_classified,
    )

    # Step 6, set the plan metrics using the object's setter

    candidate_plan.set_grid_metrics(metrics)

    # Step 7, calculate the duration of the flight in minutes and then send it to the candidate

    candidate_plan_estimated_duration_min = route_duration_min(
        metrics["total_route_distance_m"], metrics["total_lines"], mission_aircraft
    )

    candidate_plan_estimated_battery_margin_min = battery_margin_min(
        mission_aircraft, candidate_plan_estimated_duration_min
    )

    candidate_plan.set_duration_min(candidate_plan_estimated_duration_min)

    candidate_plan.set_battery_margin_min(candidate_plan_estimated_battery_margin_min)

    # Step 8, retrieve the orientation score and send it to the candidate
    candidate_plan.set_score(mission_orientation_score)

    return candidate_plan


# Public wrapper function for flight_plan_maker.py in order to prevent reaching into internals


def plan_default_mission(candidate_name):

    return build_candidate_plan(
        _Black_Swift,
        _Black_Swift_usable_endurance_m,
        _Calypso_payload,
        _V1_Mission_Request,
        _V1_assumed_weather,
        _V1_mission_sun_azimuth,
        _V1_mission_sun_state,
        candidate_name=candidate_name,
    )
