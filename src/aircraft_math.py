"""
Aircraft-level math helpers.

This file converts aircraft endurance into distance budgets and, as of V2C-2, owns the
wind triangle: crab angle, ground speed, and the return-to-home timing the RTH safety
gate is built on. Route geometry stays in geo.py; this file only answers what the
AIRCRAFT can do in a given wind.

LEAF: imports constants and objects, nothing else. It does not know what a grid is, where
M1 is, or what a CandidatePlan looks like. The RTH fixed-point loop needs both geometry
and performance, so it lives in planner -- the only module allowed to know both.

It also makes no POLICY decisions. Handed stub weather it reports zero crab and airspeed
ground speed, honestly, because that is what the numbers say. Whether a plan may be
CERTIFIED on those numbers is validator's call, made by reading weather.wind_is_measured.
Computation and permission are separate jobs.
"""


import constants as C
from objects import Aircraft
import math


SECONDS_PER_MINUTE = 60


def total_endurance_distance_m(aircraft):
    """
    Convert aircraft endurance at cruise speed into meters.
    """
    return (
        aircraft.vehicle_endurance * SECONDS_PER_MINUTE * aircraft.vehicle_cruise_speed
    )


def reserve_distance_m(aircraft, reserve_fraction=C.RTH_SEED_RESERVE_FRACTION):
    """
    Calculate the distance held back for emergency reserve.
    """
    return total_endurance_distance_m(aircraft) * reserve_fraction


def usable_endurance_distance_m(aircraft, reserve_fraction=C.RTH_SEED_RESERVE_FRACTION):
    """
    Calculate the maximum planned route distance while preserving reserve.
    """
    return total_endurance_distance_m(aircraft) - reserve_distance_m(aircraft, reserve_fraction)


def max_planned_distance_m(aircraft, reserve_fraction=C.RTH_SEED_RESERVE_FRACTION):
    """
    Alias for usable_endurance_distance_m; kept for readability in planner.py.
    """
    return usable_endurance_distance_m(aircraft, reserve_fraction)

# route duration minute is used to understand how long the finished route is going
# to take in real life minutes.

def route_duration_min(total_route_distance_m: float, total_lines, aircraft: Aircraft, weather=None, axis=None):
    
    # time spent flying in a straight line (cruising)
    cruise_seconds = total_route_distance_m / aircraft.vehicle_cruise_speed
    
    # time spent flying in a turn
    # total number of turns is N-lines - 1
    turn_seconds = (total_lines -1) * aircraft.vehicle_turn_penalty
    
    duration_min = (cruise_seconds + turn_seconds) / SECONDS_PER_MINUTE
    
    return duration_min


# battery_margin_min() reports how much endurance is left after completing the route

def battery_margin_min(aircraft: Aircraft, estimated_duration_min: float):
    
    # calculate how much battery time is left
    margin = (aircraft.vehicle_endurance - estimated_duration_min)
    
    # this function is returned and margin is a signed float
    # negative numbers imply an infeasible battery margin, which validator.py
    # rejects. Otherwise, margin represents what is left after flying.
    return margin

"""
V2C-2 functions related to RTH feasability, crosswing heading adjustments, flight crab angle,
and other wind aware functions are below:
=============================================================================================

*NOTE* NWS (And all aviation) list wind direction was 'coming from':
 Ex: A wind direction of 45 deg. is blowing towards 225 deg. 
 
 ALL functions below assume this will not change, as this has been aviation's convention for a long time.
 """

"""
EVERY function below is relative to a TRACK. The wind's effect on the aircraft depends
entirely on the angle BETWEEN the wind and the direction of travel, so the relative angle
(blowing_from_deg - track_deg) is the only thing that matters -- never the wind bearing
on its own. Omitting the track silently hard-codes a due-north track.

airspeed_ms is TRUE AIRSPEED, never ground speed. Keeping those two apart is the entire
point of V2C-2; the moment a variable name blurs them the module is lying.
"""


# Positive = from the RIGHT of track. Feeds the crab angle and the controllability gate.
def cross_wind_component_ms (blowing_from_deg, wind_speed_ms, track_deg):

    # No direction reported (stub weather) -> no resolvable vector, treat as calm.
    if blowing_from_deg is None or not wind_speed_ms:
        return 0.0

    relative_rads = math.radians(blowing_from_deg - track_deg)

    return (wind_speed_ms * math.sin(relative_rads))

# positive = wind opposing the aircraft, negative = tailwind. This is the RANGE term.
def head_wind_component_ms (blowing_from_deg, wind_speed_ms, track_deg):

    if blowing_from_deg is None or not wind_speed_ms:
        return 0.0

    relative_rads = math.radians(blowing_from_deg - track_deg)

    return (wind_speed_ms * math.cos(relative_rads))

#crab angle calculation, returns none if there is not a valid crab angle given the wind and vehicle speeds.
def wind_correction_angle_deg (blowing_from_deg, wind_speed_ms, track_deg, airspeed_ms):

    cross_wind_ms = cross_wind_component_ms(blowing_from_deg, wind_speed_ms, track_deg)

    # >= not >: at exactly airspeed the crab is 90 deg, the nose is square to the track
    # and the aircraft makes no headway along it. That is not a flyable track either.
    if abs(cross_wind_ms) >= airspeed_ms:
        return None
    else:
        arc_sin_divison = (cross_wind_ms/ airspeed_ms)

        return (math.degrees(math.asin(arc_sin_divison)))



#derives the aircraft's ground speed for a given airspeed, not to be confused with the stall speed constant.

def ground_speed_ms (blowing_from_deg, wind_speed_ms, track_deg, airspeed_ms):

    crab_angle = wind_correction_angle_deg(blowing_from_deg, wind_speed_ms, track_deg, airspeed_ms)

    #if there is no crab angle, (None), that means that the wind is too fast to fly and maintain heading.
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

def effective_lawnmower_speed_ms (blowing_from_deg, wind_speed_ms, axis_deg, airspeed_ms):
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
    pass

# bearing_home_deg is the TRACK flown to get home -- geo.bearing_between(worst_point, land).
# altitude_m and the aircraft come in as PARAMETERS, never read from constants: this module
# must work for any Aircraft and any mission altitude, including the Tier 2 synthetic one.
def return_time_min (blowing_from_deg, wind_speed_ms, bearing_home_deg, aircraft: Aircraft,
                     dist_from_landing_m, altitude_m):

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

    return (max(cruise_seconds, descent_seconds) / SECONDS_PER_MINUTE)

# mission's required return time accounting for manual takeover and/or go arounds above landing.
def required_reserve_time_min (return_time_min: float):

    return (return_time_min * C.RTH_SAFETY_FACTOR + C.RTH_TERMINAL_ALLOWANCE_min)


def wind_aware_usable_distance_m (blowing_from_deg, wind_speed_ms, axis_deg,
                                  aircraft: Aircraft, reserve_min):

    effective_speed = effective_lawnmower_speed_ms(
        blowing_from_deg, wind_speed_ms, axis_deg, aircraft.vehicle_cruise_speed
    )

    if effective_speed is None:
        return None

    flyable_min = aircraft.vehicle_endurance - reserve_min

    # A reserve larger than the endurance means there is no mission left to fly.
    if flyable_min <= 0:
        return 0.0

    return (flyable_min * SECONDS_PER_MINUTE * effective_speed)