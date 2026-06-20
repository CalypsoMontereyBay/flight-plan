"""
Aircraft-level math helpers for Engine V1.

This file converts aircraft endurance from minutes into distance budgets.
Route geometry stays in geo.py; this file only answers how far the aircraft
can fly while preserving the required emergency reserve.
"""


from constants import V1_EMERGENCY_RESERVE_FRACTION
from objects import Aircraft


SECONDS_PER_MINUTE = 60


def total_endurance_distance_m(aircraft):
    """
    Convert aircraft endurance at cruise speed into meters.
    """
    return (
        aircraft.vehicle_endurance * SECONDS_PER_MINUTE * aircraft.vehicle_cruise_speed
    )


def reserve_distance_m(aircraft, reserve_fraction=V1_EMERGENCY_RESERVE_FRACTION):
    """
    Calculate the distance held back for emergency reserve.
    """
    return total_endurance_distance_m(aircraft) * reserve_fraction


def usable_endurance_distance_m(aircraft, reserve_fraction=V1_EMERGENCY_RESERVE_FRACTION):
    """
    Calculate the maximum planned route distance while preserving reserve.
    """
    return total_endurance_distance_m(aircraft) - reserve_distance_m(aircraft, reserve_fraction)


def max_planned_distance_m(aircraft, reserve_fraction=V1_EMERGENCY_RESERVE_FRACTION):
    """
    Alias for usable_endurance_distance_m; kept for readability in planner.py.
    """
    return usable_endurance_distance_m(aircraft, reserve_fraction)

# route duration minute is used to understand how long the finished route is going
# to take in real life minutes.

def route_duration_min(total_route_distance_m: float, total_lines, aircraft: Aircraft):
    
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

