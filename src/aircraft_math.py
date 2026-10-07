"""
Aircraft-level math helpers.

This file converts aircraft endurance into distance budgets and, as of V2C-2, owns the
wind triangle: crab angle, ground speed, and return-to-home timing. Route geometry stays
in geo.py; this file only answers what the AIRCRAFT can do in a given wind.

LEAF: imports constants and objects, nothing else. It does not know what a grid is, where
M1 is, or what a CandidatePlan looks like. Anything that needs both geometry and
performance lives in planner -- the only module allowed to know both.

⚠️ WIRING STATUS: every wind function below still has ZERO CALLERS. They are written and
covered by Tier 2 vectors, but planner does not use them, so none of them affects a
generated plan. route_duration_min accepts weather/axis_deg and the hub still calls it with
three arguments, meaning duration is computed in still air.

⚠️ 2026-09-08 -- THEIR DESTINATION CHANGED. These functions were built to feed a
return-to-home safety GATE (planner._rth_safe_budget, a wind-derived reserve, a crosswind
veto). That gate is CANCELLED: aircraft are now assumed to sense wind and compensate in
flight, so the engine may not reject a plan or reshape a grid on wind. The math stays and
stays correct; what it loses is authority. It was built to DECIDE and now exists to INFORM
-- these numbers belong in a pilot-notes document for the RPIC. See CLAUDE.md, "Operating
constraints -- 2026-09-08".

It also makes no POLICY decisions. Handed stub weather it reports zero crab and airspeed
ground speed, honestly, because that is what the numbers say. Whether anything may be
CERTIFIED on those numbers is a question for validator (Step E, not yet written), which
would answer it by reading weather.wind_is_measured. Computation and permission are
separate jobs.

WIND CONVENTION: NWS (and all of aviation) reports wind by the direction it blows FROM --
a wind direction of 45 deg is blowing towards 225 deg. Every function below assumes this.

EVERY wind function is relative to a TRACK. The wind's effect on the aircraft depends
entirely on the angle BETWEEN the wind and the direction of travel, so the relative angle
(blowing_from_deg - track_deg) is the only thing that matters -- never the wind bearing
on its own. Omitting the track silently hard-codes a due-north track.

airspeed_ms is TRUE AIRSPEED, never ground speed. Keeping those two apart is the entire
point of V2C-2; the moment a variable name blurs them the module is lying.
"""

import math

import constants as CONST
from objects import Aircraft


SECONDS_PER_MINUTE = 60


def total_endurance_distance_m(aircraft):
    """
    Convert aircraft endurance at cruise speed into meters.
    """
    return (
        aircraft.vehicle_endurance * SECONDS_PER_MINUTE * aircraft.vehicle_cruise_speed
    )


def reserve_distance_m(aircraft, reserve_fraction=CONST.RTH_SEED_RESERVE_FRACTION):
    """
    Calculate the distance held back for emergency reserve.
    """
    return total_endurance_distance_m(aircraft) * reserve_fraction


def usable_endurance_distance_m(aircraft, reserve_fraction=CONST.RTH_SEED_RESERVE_FRACTION):
    """
    Calculate the maximum planned route distance while preserving reserve.
    """
    return total_endurance_distance_m(aircraft) - reserve_distance_m(aircraft, reserve_fraction)


def max_planned_distance_m(aircraft, reserve_fraction=CONST.RTH_SEED_RESERVE_FRACTION):
    """
    Alias for usable_endurance_distance_m; kept for readability in planner.py.
    """
    return usable_endurance_distance_m(aircraft, reserve_fraction)


def route_duration_min(total_route_distance_m: float, total_lines, aircraft: Aircraft,
                       weather=None, axis_deg=None):
    """
    How long the finished route takes to fly, in real-life minutes: cruise time over the
    route distance plus one turn penalty per turn.
    """

    # Still-air cruise is both the floor and the fallback. `speed` is a valid number from
    # here on and is only ever REPLACED by another valid number, so the division below can
    # never see None. That is what keeps this change to three lines instead of pushing
    # None-checks out to every call site.
    speed = aircraft.vehicle_cruise_speed

    # Wind-aware only when BOTH are supplied. Note what is NOT in the signature: the wind
    # direction, wind speed, and airspeed. Weather already carries the wind vector and
    # `aircraft` already carries the airspeed -- passing them separately would create two
    # sources of truth for the same numbers and is what blew up the parameter list.
    if weather is not None and axis_deg is not None:

        effective_speed = effective_lawnmower_speed_ms(
            weather.wind_direction,
            weather.wind_speed,
            axis_deg,
            aircraft.vehicle_cruise_speed,
        )

        # None means this wind cannot fly this axis at all. Fall back to still air rather
        # than propagating None: duration is a REPORTING number and every consumer
        # (_metrics_caption, battery_margin_min, the terminal summary) formats it as a
        # float. An optimistic duration here is a reporting error, not a safety hole: wind
        # feasibility is not gated at all (the aircraft compensates in flight, constraint
        # 4), and this branch is not wired yet -- planner calls without weather.
        if effective_speed is not None:
            speed = effective_speed

    # time spent flying in a straight line (cruising)
    cruise_seconds = total_route_distance_m / speed

    # time spent flying in a turn
    # total number of turns is N-lines - 1
    turn_seconds = (total_lines - 1) * aircraft.vehicle_turn_penalty

    duration_min = (cruise_seconds + turn_seconds) / SECONDS_PER_MINUTE

    return duration_min


def battery_margin_min(aircraft: Aircraft, estimated_duration_min: float):
    """
    How much endurance is left after completing the route, in minutes.
    """

    # calculate how much battery time is left
    margin = (aircraft.vehicle_endurance - estimated_duration_min)

    # margin is a signed float. A negative number means the route outlasts the battery.
    # Nothing rejects that today: whether endurance feasibility becomes a gate is the open
    # Step E question (validator.py is still empty). Otherwise, margin is what is left
    # after flying.
    return margin


"""
V2C-2 wind-aware functions -- crosswind components, crab angle, ground speed, return
timing and derived reserve -- are below. The wind convention and the track rule they all
follow are in the module docstring above.
=============================================================================================
"""


def cross_wind_component_ms(blowing_from_deg, wind_speed_ms, track_deg):
    """
    Crosswind component relative to the track. Positive = from the RIGHT of track. Feeds
    the crab angle and the controllability check.
    """

    # No direction reported (stub weather) -> no resolvable vector, treat as calm.
    if blowing_from_deg is None or not wind_speed_ms:
        return 0.0

    relative_rads = math.radians(blowing_from_deg - track_deg)

    return (wind_speed_ms * math.sin(relative_rads))


def head_wind_component_ms(blowing_from_deg, wind_speed_ms, track_deg):
    """
    Headwind component along the track. Positive = wind opposing the aircraft, negative =
    tailwind. This is the RANGE term.
    """

    if blowing_from_deg is None or not wind_speed_ms:
        return 0.0

    relative_rads = math.radians(blowing_from_deg - track_deg)

    return (wind_speed_ms * math.cos(relative_rads))


def wind_correction_angle_deg(blowing_from_deg, wind_speed_ms, track_deg, airspeed_ms):
    """
    Crab angle needed to hold the track, in degrees. Returns None when no heading can hold
    the track, given the wind and the airspeed.
    """

    cross_wind_ms = cross_wind_component_ms(blowing_from_deg, wind_speed_ms, track_deg)

    # >= not >: at exactly airspeed the crab is 90 deg, the nose is square to the track
    # and the aircraft makes no headway along it. That is not a flyable track either.
    if abs(cross_wind_ms) >= airspeed_ms:
        return None
    else:
        arc_sin_division = (cross_wind_ms / airspeed_ms)

        return (math.degrees(math.asin(arc_sin_division)))


def ground_speed_ms(blowing_from_deg, wind_speed_ms, track_deg, airspeed_ms):
    """
    The aircraft's ground speed along the track for a given airspeed. Not to be confused
    with the stall speed constant.
    """

    crab_angle = wind_correction_angle_deg(blowing_from_deg, wind_speed_ms, track_deg, airspeed_ms)

    # if there is no crab angle, (None), that means that the wind is too fast to fly and maintain heading.
    # No ground speed is sufficient -> return None
    if crab_angle is None:
        return None

    head_wind_ms = head_wind_component_ms(blowing_from_deg, wind_speed_ms, track_deg)

    ground_speed = ((airspeed_ms * math.cos(math.radians(crab_angle))) - head_wind_ms)

    # A headwind can exceed what the crabbed airspeed makes good, leaving the aircraft
    # stationary or going backwards over the ground. Returning that number unguarded
    # would hand callers a NEGATIVE return time, which reads as a fast, safe trip home.
    if ground_speed <= 0:
        return None

    return ground_speed


def effective_lawnmower_speed_ms(blowing_from_deg, wind_speed_ms, axis_deg, airspeed_ms):
    """
    Average ground speed over a lawnmower flown along axis_deg in BOTH directions.

    axis_deg is the grid orientation (plan.chosen_orientation). A lawnmower flies one
    axis two ways, so evaluate ground_speed_ms at axis_deg AND axis_deg + 180.

    Combine them with the HARMONIC mean, not the arithmetic one, because the legs are
    equal in DISTANCE, not in time -- more of the flight is spent at the slower speed:

        2 / (1/out + 1/back)

    Returns None if either direction is unflyable. The result is always <= airspeed for
    any non-zero wind, INCLUDING a pure crosswind: crabbing spends part of the airspeed
    vector sideways, so wind is never free.
    """

    out_bound_ground_speed_ms = ground_speed_ms(blowing_from_deg, wind_speed_ms, axis_deg, airspeed_ms)

    return_bound_ground_speed_ms = ground_speed_ms(blowing_from_deg, wind_speed_ms, (axis_deg + CONST.DEGREE_ONE_EIGHTY), airspeed_ms)

    if out_bound_ground_speed_ms is None or return_bound_ground_speed_ms is None:
        return None
    else:
        return (2 / ((1 / out_bound_ground_speed_ms) + (1 / return_bound_ground_speed_ms)))


def max_crosswind_tolerance_ms(airspeed_ms, tolerance_deg):
    """
    Largest crosswind that keeps the crab angle -- and therefore the boresight error --
    inside tolerance_deg. Inverts the crab formula:

        crab = asin(crosswind / V) <= tolerance   =>   crosswind <= V * sin(tolerance)

    Wind DIRECTION is irrelevant here; this is a magnitude limit. Called with
    V1_GLINT_TOLERANCE_DEG it yields 4.659 m/s, the science-axis crosswind headroom
    reported to the RPIC. Not to be confused with MANUAL_RTH_MAX_CROSSWIND_ms, which is
    a direct m/s limit on the HOMEWARD leg rather than an angle-derived one.
    """
    max_cross_wind_ms = airspeed_ms * math.sin(math.radians(tolerance_deg))

    return max_cross_wind_ms


def return_time_min(blowing_from_deg, wind_speed_ms, bearing_home_deg, aircraft: Aircraft,
                    dist_from_landing_m, altitude_m):
    """
    Minutes to fly home from a point dist_from_landing_m out, limited by the slower of the
    cruise leg and the descent.

    bearing_home_deg is the TRACK flown to get home -- geo.bearing_between(worst_point, land).
    altitude_m and the aircraft come in as PARAMETERS, never read from constants: this module
    must work for any Aircraft and any mission altitude, including the Tier 2 synthetic one.
    """

    returning_ground_speed_ms = ground_speed_ms(
        blowing_from_deg, wind_speed_ms, bearing_home_deg, aircraft.vehicle_cruise_speed
    )

    if returning_ground_speed_ms is None:
        return None

    # Both terms are SECONDS; divide once at the end so the name stays true. The max()
    # is load-bearing: you cannot get down faster than the descent rate, so a close-in
    # emergency is descent-limited rather than distance-limited.
    cruise_seconds = dist_from_landing_m / returning_ground_speed_ms
    descent_seconds = altitude_m / aircraft.vehicle_descent_rate

    return (max(cruise_seconds, descent_seconds) / (SECONDS_PER_MINUTE))


def required_reserve_time_min(return_time_min: float):
    """
    The mission's required return time, accounting for a manual takeover and/or
    go-arounds above the landing site.
    """

    return (return_time_min * CONST.RTH_SAFETY_FACTOR + CONST.RTH_TERMINAL_ALLOWANCE_min)


def wind_aware_usable_distance_m(blowing_from_deg, wind_speed_ms, axis_deg,
                                 aircraft: Aircraft, reserve_min):
    """
    Distance the aircraft can fly on the lawnmower axis in this wind once reserve_min is
    held back, or None when the wind is unflyable or the reserve exceeds the endurance.
    """

    effective_speed = effective_lawnmower_speed_ms(
        blowing_from_deg, wind_speed_ms, axis_deg, aircraft.vehicle_cruise_speed
    )

    if effective_speed is None:
        return None

    flyable_min = aircraft.vehicle_endurance - reserve_min

    # A reserve larger than the endurance means there is no mission left to fly.
    # ONE sentinel: None, matching every other wind function here, because that is what
    # planner will branch on. Returning 0.0 instead would flow into geo's
    # _initial_total_lines_from_budget, which RAISES on a non-positive budget -- turning a
    # legitimate "too windy today" verdict into an exception in the plan path.
    if flyable_min <= 0:
        return None
    else:
        return (flyable_min * SECONDS_PER_MINUTE * effective_speed)
