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
from geo import make_lawnmower_grid_through_m1, distance_between
from sun import create_sun_state, mission_datetime as DEFAULT_MISSION_DATETIME
from aircraft_math import max_planned_distance_m, route_duration_min, battery_margin_min
import itertools
import weather

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
    CONST.BLACKSWIFT_CRUISE_SPEED_ms
)

# Amount of distance the aircraft can use for its mission (Using the alias function, further docs in aircraft_math.py)
# V2C-2 INTERIM: the reserve is no longer a policy constant -- it is DERIVED per mission
# from the worst-case return-to-home time. This module-level budget uses the iteration
# SEED only, and is replaced by _rth_safe_budget() once that lands (step 5). Until then a
# plan is sized against an unverified reserve; do not treat it as RTH-cleared.
_Black_Swift_usable_endurance_m = max_planned_distance_m(
    _Black_Swift, CONST.RTH_SEED_RESERVE_FRACTION
)

# Step 1.2: Assemble the Sensor object

_Calypso_payload = Sensor(
    CONST.V1_DEFAULT_SENSOR_CROSS_TRACK_FOV_deg,
    CONST.V1_DEFAULT_SENSOR_ALONG_TRACK_FOV_DEG,
    CONST.V1_DEFAULT_CROSSTRACK_OVERLAP_PCT,
    CONST.V2_DEFAULT_ALONGTRACK_OVERLAP_PCT,
    CONST.V1_DEFAULT_SENSOR_OFF_NADIR_deg,
    mounting=CONST.V2_SENSOR_MOUNTING,
    sensor_name=CONST.V2_SENSOR_NAME
)

# Step 1.3: Mission Request object for launch, land, and M1, then route assembly:

_Launch_Waypoint = Waypoint(
    "WP000",
    CONST.V1_LAUNCH_POINT_LAT,
    CONST.V1_LAUNCH_POINT_LONG,
    CONST.V1_DEFAULT_AIRCRAFT_ALTITUDE_m,
    CONST.BLACKSWIFT_CRUISE_SPEED_ms,
    CONST.WAYPOINT_ACTION_LAUNCH,
    "Launch point",
    "Seymour-Beach-Launch",
)

_Land_Waypoint = Waypoint(
    "WP_END",
    CONST.V1_LAND_POINT_LAT,
    CONST.V1_LAND_POINT_LONG,
    CONST.V1_DEFAULT_LAND_ALTITUDE_m,
    CONST.BLACKSWIFT_CRUISE_SPEED_ms,
    CONST.WAYPOINT_ACTION_LAND,
    "land waypoint",
    "Seymour-Road-Land",
)

_M1_Waypoint = Waypoint(
    "WP_M1",
    CONST.M1_MOORING_LAT,
    CONST.M1_MOORING_LONG,
    CONST.V1_DEFAULT_AIRCRAFT_ALTITUDE_m,
    CONST.BLACKSWIFT_CRUISE_SPEED_ms,
    CONST.WAYPOINT_ACTION_M1_OVERFLIGHT,
    "M1 waypoint for overflight req",
    "M1-Mooring-Station",
)

#Step 1.4, consolidating the date/time dependent objects to a builder function:

def _build_dated_objects (mission_datetime):
    
    _Sun_State = create_sun_state(
        CONST.V1_LAUNCH_POINT_LAT,
        CONST.V1_LAUNCH_POINT_LONG,
        mission_datetime
        )
    
    _Mission_Request = MissionRequest(
        mission_name="V2 Generated Mission",
        launch_waypoint=_Launch_Waypoint,
        land_waypoint=_Land_Waypoint,
        m1_waypoint=_M1_Waypoint,
        altitude_m=CONST.V1_DEFAULT_AIRCRAFT_ALTITUDE_m,
        valid_time=mission_datetime,
        require_m1_overflight=True,
        grid_orientation_deg=None,
        notes="V2 Grid",
        included_target_waypoints=[_M1_Waypoint]
        )
    
    # Ask the weather leaf for live NWS data; it returns None when weather cannot be
    # produced (out of forecast horizon, or any fetch/parse failure).
    _Mission_Weather = weather.get_weather(
        CONST.V1_LAUNCH_POINT_LAT, CONST.V1_LAUNCH_POINT_LONG, mission_datetime
    )

    # Fallback: the V1-style clear-sky / zero-wind stub, so a plan is always produced.
    if _Mission_Weather is None:
        _Mission_Weather = Weather(
            CONST.V1_LAUNCH_POINT_LAT,
            CONST.V1_LAUNCH_POINT_LONG,
            mission_datetime,
            CONST.V1_DEFAULT_MISSION_CLOUD_COVER,
            CONST.DEFAULT_ZERO_WIND,
            CONST.DEFAULT_WIND_DIRECTION_deg,
            CONST.DEFAULT_WIND_GUST_ms,
            CONST.DEFAULT_VISIBILITY_m,
            CONST.DEFAULT_WEATHER_CONDITION,
        )
    
    mission_az = _Sun_State.azimuth
    
    return (_Sun_State, _Mission_Request, _Mission_Weather, mission_az)

"""
HELPER FUNCTIONS FOR POPULATING THE CANDIDATE PLAN BELOW
In Order:


1. _candidate_orientation(): takes an azimuth angle and returns two heading "orientations"
Both orientations are valid for "science" lines, but depending on all the other factors, one will score
better than the other. returns both in a tuple for passing around and proper security.
These values are then passed as potential_orientation_deg params in other helpers.

2. _score_glint(): Returns how far off one leg of a candidate orientation is
off from the SCIENCE_RELATIVE_AZIMUTH_deg standard (90 deg for the V2C along-track mount).
Scores follow a golf paradigm (lower = better). A score of 0 means the target relative azimuth
exactly. No candidate orientation can earn lower than zero. If scores are equal, including for
two candidates that earn a score of zero, a tiebreaker (which orientation's corner is closest to the launch),
is used. This is the tiebreaker because if the corner is closer, it is more likely that the grid is also larger.

3. _score_candidate(): scores a candidate based on the
deviation from the target relative azimuth based on their science leg.

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
    # be used as "paths" and then the score is based off of glint minimization.

    # NOTE (V2C): with the along-track mount the target is 90 deg of relative
    # azimuth, so these two candidates come out 180 deg apart -- the SAME grid
    # axis flown in opposite directions, not two distinct grids. The pair is kept
    # because _pick_best_orientation still uses it to resolve the entry corner,
    # and because a future target != 90 would separate them again.

    potential_orientation_one = (
        sun_az + CONST.SCIENCE_RELATIVE_AZIMUTH_deg
    ) % CONST.AZIMUTH_THREE_SIXTY

    potential_orientation_two = (
        sun_az - CONST.SCIENCE_RELATIVE_AZIMUTH_deg
    ) % CONST.AZIMUTH_THREE_SIXTY

    return (potential_orientation_one, potential_orientation_two)


# Glint scoring function used to rank plans for V1.
# THE ONLY RANKING FUNCTION FOR V1, OTHERS WILL FOLLOW
# track heading is an az candidate from the function above
def _score_glint(potential_orientation_deg, sun_az_deg):
    """
    Golf-style glint penalty: 0 = perfect (the leg sits exactly
    SCIENCE_RELATIVE_AZIMUTH_deg off the sun azimuth), higher = worse.

    Scored against the target AND its mirror (360 - target) because glint
    geometry is symmetric about the solar principal plane -- sun off the left
    shoulder is as good as sun off the right.

    potential_orientation_deg: heading flown on the leg (0..360)
    sun_az_deg: sun azimuth at the mission time (0..360)
    """

    # finds how far off each azimuth candidate heading is from the desired 0 score.
    azimuth_delta = (potential_orientation_deg - sun_az_deg) % CONST.AZIMUTH_THREE_SIXTY

    mirror_azimuth_deg = CONST.FULL_CIRCLE_DEG - CONST.SCIENCE_RELATIVE_AZIMUTH_deg

    # _angular_distance wraps correctly for ANY target; a raw abs() difference
    # only happened to work for the old 135/225 pair.
    return min(
        _angular_distance(azimuth_delta, CONST.SCIENCE_RELATIVE_AZIMUTH_deg),
        _angular_distance(azimuth_delta, mirror_azimuth_deg),
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
    
    if payload.mounting != CONST.SENSOR_MOUNT_ALONG_TRACK:
        raise ValueError (f"V2 only allows for along track payload mounting in accordance with geo.py math; Sensor declares: {payload.mounting}")
    
    return make_lawnmower_grid_through_m1(
        mission_request.m1_wp,
        orientation_deg,
        usable_distance_m,
        mission_request.altitude,
        payload.cross_track_fov,
        payload.cross_track_overlap,
        off_nadir_deg=payload.off_nadir,
        along_track_fov_deg=payload.along_track_fov,
        along_track_overlap_pct=payload.along_track_overlap,
    )


def _pick_best_orientation(
    candidates: tuple,
    sun_az_deg,
    mission_request: MissionRequest,
    payload: Sensor,
    predicted_grid_distance_m,
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
            orientation_deg, mission_request, payload, predicted_grid_distance_m
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
    cruise_speed_ms
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
                
            elif local_idx == 1:
                    action = CONST.WAYPOINT_ACTION_COLLECT_START
                    target_name = "Camera On"
                    
            elif local_idx == (CONST.V1_POINTS_PER_LINE - 2):
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
    candidate_name
):

    # Step 1, generate the potential orientation candidates
    mission_potential_orientations = _candidate_orientation(mission_azimuth)

    # Step 2, RESERVE THE TRANSIT before geo is allowed to size anything.
    #
    # geo.make_lawnmower_grid_through_m1 takes a centre, an orientation and a distance --
    # it does not know where launch is and must not learn, so this subtraction belongs to
    # the hub. The seed is 2 * d(launch, M1); measured against the real entry/exit corners
    # it comes out accurate to ~0.40% at the Terrace Point geometry, so one pass is
    # normally enough and no fixed-point loop is warranted.
    predicted_transit_budget_m = 2 * distance_between(
        mission_request.launch_wp, mission_request.m1_wp
    )

    grid_budget_m = mission_aircraft_endurance_m - predicted_transit_budget_m

    # Steps 3-6 run inside the fit loop. A pass that does not fit re-seeds the budget with
    # the transit it MEASURED rather than the one it estimated. That measured value is
    # strictly larger than the estimate which just failed, so grid_budget_m strictly
    # shrinks every pass and the loop cannot spin. If it shrinks below a 3-line grid, geo
    # raises -- the honest answer that no grid fits this launch point, which is a sizing
    # failure and not a weather veto.
    for _fit_pass in range(CONST.TRANSIT_FIT_MAX_PASSES):

        # Step 3, pick the winning orientation AND reuse the grid the picker built
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
            grid_budget_m,
        )

        # Step 4, reorient the grid so the route starts at the corner closest to launch
        route_shapely_waypoints, m1_index = _reorient_to_launch(
            route_points, metrics["m1_route_index"], mission_request.launch_point
        )

        # Step 5, walk the route and classify each waypoint and assign it an index:

        mission_route_list_classified = _classify_waypoints(
            route_shapely_waypoints,
            m1_index,
            mission_request.launch_wp,
            mission_request.land_wp,
            mission_request.altitude,
            mission_aircraft.vehicle_cruise_speed
        )

        # Step 6, measure the transit that was ACTUALLY planned, now that the route has
        # been reoriented and the pad waypoints are in it.
        # Launch Waypoint IDX = 0, Land Waypoint IDX = -1
        # First Grid Waypoint IDX = 1, Last Grid Waypoint IDX = -2
        true_outbound_non_grid_transit_m = distance_between(
            mission_request.launch_wp, mission_route_list_classified[1]
        )
        true_returning_non_grid_transit_m = distance_between(
            mission_route_list_classified[-2], mission_request.land_wp
        )

        true_non_grid_transit_m = (
            true_outbound_non_grid_transit_m + true_returning_non_grid_transit_m
        )

        total_flight_distance_m = (
            true_non_grid_transit_m + metrics["total_grid_distance_m"]
        )

        if total_flight_distance_m <= mission_aircraft_endurance_m:
            break

        grid_budget_m = mission_aircraft_endurance_m - true_non_grid_transit_m

    else:
        # Only reachable if the measured transit keeps growing faster than the budget
        # shrinks, which the geometry does not permit. Fail loudly rather than return a
        # plan the aircraft cannot fly.
        raise ValueError(
            f"Transit-aware grid sizing did not converge in "
            f"{CONST.TRANSIT_FIT_MAX_PASSES} passes against "
            f"{mission_aircraft_endurance_m:.0f} m of usable distance"
        )

    # Step 7, build the candidate plan

    candidate_plan = CandidatePlan(
        candidate_name,
        mission_request,
        mission_aircraft,
        mission_sun_state,
        mission_weather,
        mission_orientation,
        payload,
        mission_route_list_classified
    )

    # Step 8, set the plan metrics using the object's setter.
    # set_grid_metrics carries geo's grid_budget_m (endurance MINUS transit). The full
    # battery figure is a different number and only the hub knows it, so it is set here.

    candidate_plan.set_grid_metrics(metrics)

    candidate_plan.set_usable_endurance_distance_m(mission_aircraft_endurance_m)

    candidate_plan.set_total_flight_distance_m(total_flight_distance_m)

    # Step 9, calculate the duration of the flight in minutes and then send it to the
    # candidate. This consumes the TOTAL flight distance, not the grid figure -- that
    # substitution is the reporting half of the J-4 transit fix.

    candidate_plan_estimated_duration_min = route_duration_min(
        total_flight_distance_m, metrics["total_lines"], mission_aircraft
    )

    candidate_plan_estimated_battery_margin_min = battery_margin_min(
        mission_aircraft, candidate_plan_estimated_duration_min
    )

    candidate_plan.set_duration_min(candidate_plan_estimated_duration_min)

    candidate_plan.set_battery_margin_min(candidate_plan_estimated_battery_margin_min)

    # Step 9, retrieve the orientation score and send it to the candidate
    candidate_plan.set_score(mission_orientation_score)

    return candidate_plan


# Public wrapper function for flight_plan_maker.py in order to prevent reaching into internals


def plan_default_mission(candidate_name, mission_datetime=None):

    # With no datetime, fall back to the module-level V2 default so a plan can be
    # built from just a name (keeps the V1-era one-arg call sites working). The
    # sun resolver only defaults the STRING inputs; a None datetime object must be
    # caught here.
    if mission_datetime is None:
        mission_datetime = DEFAULT_MISSION_DATETIME

    #unpacking dated objects:
    _Sun_State, _Mission_Request, _Weather_State, _Sun_az = _build_dated_objects(mission_datetime)
        
    return build_candidate_plan(
        mission_aircraft= _Black_Swift,
        mission_aircraft_endurance_m= _Black_Swift_usable_endurance_m,
        payload= _Calypso_payload,
        mission_request= _Mission_Request,
        mission_weather= _Weather_State,
        mission_azimuth= _Sun_az,
        mission_sun_state= _Sun_State,
        candidate_name=candidate_name
    )
    
