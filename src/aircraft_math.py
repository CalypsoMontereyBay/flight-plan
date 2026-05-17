'''
Aircraft-level math helpers for Engine V1.

This file converts aircraft endurance from minutes into distance budgets.
Route geometry stays in geo.py; this file only answers how far the aircraft
can fly while preserving the required emergency reserve.
'''

try:
    from .constants import V1_EMERGENCY_RESERVE_FRACTION
except ImportError:
    from constants import V1_EMERGENCY_RESERVE_FRACTION


SECONDS_PER_MINUTE = 60


def total_endurance_distance_m(aircraft):
    '''
    Convert aircraft endurance at cruise speed into meters.
    '''
    return aircraft.vehicle_endurance * SECONDS_PER_MINUTE * aircraft.vehicle_cruise_speed


def reserve_distance_m(aircraft, reserve_fraction=V1_EMERGENCY_RESERVE_FRACTION):
    '''
    Calculate the distance held back for emergency reserve.
    '''
    return total_endurance_distance_m(aircraft) * reserve_fraction


def usable_endurance_distance_m(aircraft, reserve_fraction=V1_EMERGENCY_RESERVE_FRACTION):
    '''
    Calculate the maximum planned route distance while preserving reserve.
    '''
    return total_endurance_distance_m(aircraft) - reserve_distance_m(aircraft, reserve_fraction)


def max_planned_distance_m(aircraft, reserve_fraction=V1_EMERGENCY_RESERVE_FRACTION):
    '''
    Alias for usable_endurance_distance_m; kept for readability in planner.py.
    '''
    return usable_endurance_distance_m(aircraft, reserve_fraction)
