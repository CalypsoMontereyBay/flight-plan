"""
Tier 2 -- derived sizing + aircraft math.

Builds directly on the Tier 0 primitives. These are still pure, closed-form math
(endurance/distance/duration conversions, grid sizing, orientation candidates), so
like Tier 0 they must NEVER fail. If an assert here breaks, the -x gate stops the
run before any grid/classification/rendering tier is even attempted.

Test vectors are hard literals (independent of production constants) so they pin the
math itself, not whatever CONST happens to hold today.
"""

import pytest

import aircraft_math as A
import constants as CONST
import geo as G
import objects as OBJ
import planner as P


# One deterministic vehicle: endurance 90 min, turn penalty 10 s, cruise 18 m/s are
# the three values the aircraft-math functions actually consume.
def _test_aircraft():
    return OBJ.Aircraft(90, 15, 3.35, 1.80, 57, 10, 12, 18)


def test_total_endurance_distance():
    ac = _test_aircraft()
    # 90 min * 60 s/min * 18 m/s
    assert A.total_endurance_distance_m(ac) == pytest.approx(97_200)


def test_reserve_and_usable_distance():
    ac = _test_aircraft()
    assert A.reserve_distance_m(ac, 0.15) == pytest.approx(14_580)         # 97_200 * 0.15
    assert A.usable_endurance_distance_m(ac, 0.15) == pytest.approx(82_620)  # 97_200 - 14_580
    # max_planned_distance_m is a documented alias for usable_endurance_distance_m
    assert A.max_planned_distance_m(ac, 0.15) == pytest.approx(82_620)


def test_route_duration_min():
    ac = _test_aircraft()
    # 1800 m / 18 m/s = 100 s cruise; (11 - 1) turns * 10 s = 100 s; total 200 s -> 3.333 min
    assert A.route_duration_min(1800, 11, ac) == pytest.approx(3.3333, abs=1e-3)


def test_battery_margin_min_sign():
    ac = _test_aircraft()
    assert A.battery_margin_min(ac, 3.3333) == pytest.approx(86.6667, abs=1e-3)
    # negative margin flags an infeasible route (duration > endurance)
    assert A.battery_margin_min(ac, 100) == pytest.approx(-10)


def test_calculate_line_length():
    assert G.calculate_line_length_m(140, 11) == pytest.approx(1400)  # offset * (N - 1)
    with pytest.raises(ValueError):
        G.calculate_line_length_m(140, 1)   # N < 2
    with pytest.raises(ValueError):
        G.calculate_line_length_m(0, 11)    # offset <= 0


def test_calculate_grid_area():
    assert G.calculate_grid_area_m2(140, 11) == pytest.approx(1_960_000)  # 1400 ** 2


# NOTE: the ODD result here is load-bearing, not cosmetic. An odd total_lines is what puts
# the center line through M1, which is what makes the M1 overflight free (no detour) and
# what geo's m1_route_index assumes. An even count silently moves M1 off every flight line.
def test_initial_total_lines_from_budget():
    # 4*10000/100 = 400 -> (1 + sqrt(401)) / 2 = 10.51 -> floor 10 -> even, -1 -> 9
    assert G._initial_total_lines_from_budget(10000, 100) == 9
    # tiny budget floors at the enforced minimum of 3
    assert G._initial_total_lines_from_budget(100, 100) == 3
    # invariant: result is always odd (so the center line passes through M1)
    for budget in (500, 2500, 9000, 50_000):
        assert G._initial_total_lines_from_budget(budget, 137) % 2 == 1
    with pytest.raises(ValueError):
        G._initial_total_lines_from_budget(0, 100)
    with pytest.raises(ValueError):
        G._initial_total_lines_from_budget(10000, 0)


# ---- V2C-2 wind triangle -------------------------------------------------------------
# Every vector below is closed-form at TAS 18 m/s. NWS (and aviation) report wind by the
# direction it blows FROM, and all of these assume that: 045 means blowing toward 225.


def test_wind_components_are_relative_to_the_track():
    # THE core property. Wind's effect depends on the angle BETWEEN it and the direction
    # of travel, so the track is not optional. Dropping it silently pins the track to
    # due north, which happens to be right only for track 000.
    assert A.cross_wind_component_ms(90, 5, 0) == pytest.approx(5.0)    # from the right
    assert A.head_wind_component_ms(0, 5, 0) == pytest.approx(5.0)      # dead ahead
    assert A.head_wind_component_ms(180, 5, 0) == pytest.approx(-5.0)   # tailwind is negative

    # same wind, a real mission track -> completely different components
    assert A.cross_wind_component_ms(45, 5, 237.18) == pytest.approx(1.054918, abs=1e-5)
    assert A.head_wind_component_ms(45, 5, 237.18) == pytest.approx(-4.887448, abs=1e-5)

    # stub weather reports no direction at all -> unresolvable vector, treated as calm
    assert A.cross_wind_component_ms(None, 5, 0) == pytest.approx(0.0)
    assert A.head_wind_component_ms(None, 5, 0) == pytest.approx(0.0)
    assert A.cross_wind_component_ms(90, 0, 0) == pytest.approx(0.0)


def test_wind_correction_angle():
    V = 18
    assert A.wind_correction_angle_deg(90, 5, 0, V) == pytest.approx(16.127620, abs=1e-5)
    assert A.wind_correction_angle_deg(90, 4, 0, V) == pytest.approx(12.839588, abs=1e-5)
    assert A.wind_correction_angle_deg(0, 5, 0, V) == pytest.approx(0.0)     # pure headwind, no crab
    assert A.wind_correction_angle_deg(45, 5, 0, V) == pytest.approx(11.327603, abs=1e-5)

    # crosswind at or beyond airspeed: no heading makes that track at all
    assert A.wind_correction_angle_deg(90, 20, 0, V) is None
    assert A.wind_correction_angle_deg(90, 18, 0, V) is None   # exactly V -> nose square to track


def test_wind_correction_angle_flips_on_the_reciprocal():
    # STRUCTURAL, and the reason all of V2C-2 exists: crab reverses sign when you turn
    # around, so the outbound heading is track+d while the return is track-d. The two
    # headings are therefore NOT reciprocal, and both legs sit |d| off the target
    # relative azimuth -- which is what makes the tolerance a pure crosswind gate.
    out = A.wind_correction_angle_deg(90, 5, 0, 18)
    back = A.wind_correction_angle_deg(90, 5, 180, 18)
    assert out is not None and back is not None      # both tracks are flyable at 5 m/s
    assert out == pytest.approx(-back)
    assert out == pytest.approx(16.127620, abs=1e-5)


def test_ground_speed_ms():
    V = 18
    assert A.ground_speed_ms(90, 5, 0, V) == pytest.approx(17.291616, abs=1e-5)   # crosswind
    assert A.ground_speed_ms(0, 5, 0, V) == pytest.approx(13.0)                   # headwind
    assert A.ground_speed_ms(180, 5, 0, V) == pytest.approx(23.0)                 # tailwind
    assert A.ground_speed_ms(45, 5, 0, V) == pytest.approx(14.113829, abs=1e-5)

    # A headwind stronger than the crabbed airspeed leaves the aircraft going backwards
    # over the ground. Returning that unguarded would give callers a NEGATIVE return
    # time, which reads as an unusually fast and safe trip home.
    assert A.ground_speed_ms(0, 25, 0, V) is None


def test_effective_lawnmower_speed_is_harmonic():
    V = 18
    # 5 m/s along the axis -> legs of 13 and 23. The ARITHMETIC mean is exactly 18, which
    # would make wind look free; the harmonic mean is 16.611, because equal DISTANCES at
    # unequal speeds spend more time slow.
    assert A.effective_lawnmower_speed_ms(0, 5, 0, V) == pytest.approx(16.611111, abs=1e-5)
    assert A.effective_lawnmower_speed_ms(0, 8, 0, V) == pytest.approx(14.444444, abs=1e-5)
    assert A.effective_lawnmower_speed_ms(0, 0, 0, V) == pytest.approx(18.0)   # calm

    # A pure crosswind penalises BOTH directions equally, so harmonic == arithmetic here
    # -- but still below airspeed, because crabbing spends part of the airspeed sideways.
    assert A.effective_lawnmower_speed_ms(90, 5, 0, V) == pytest.approx(17.291616, abs=1e-5)

    # INVARIANT: wind is never free. No wind direction, at any strength, beats still air.
    for direction in range(0, 360, 15):
        for speed in (1, 3, 5, 8, 12):
            effective = A.effective_lawnmower_speed_ms(direction, speed, 42.0, V)
            if effective is not None:
                assert effective <= V + 1e-9


def test_max_crosswind_tolerance():
    # Inverts the crab formula: the largest crosswind whose crab stays inside tolerance.
    assert A.max_crosswind_tolerance_ms(18, 15) == pytest.approx(4.658743, abs=1e-5)
    assert A.max_crosswind_tolerance_ms(18, 30) == pytest.approx(9.0)
    assert A.max_crosswind_tolerance_ms(18, 0) == pytest.approx(0.0)


def test_return_time_min_and_reserve():
    ac = _test_aircraft()
    # 18 km at 18 m/s = 1000 s = 16.6667 MINUTES. The function is named _min and must
    # return minutes -- returning seconds here would inflate the derived reserve by 60x
    # and the fixed-point loop could never converge.
    assert A.return_time_min(None, 0, 0, ac, 18000.0, 609.6) == pytest.approx(16.666667, abs=1e-5)

    # DESCENT FLOOR: close in, the trip home is limited by how fast you can get down
    # (609.6 m at 1.80 m/s = 338.67 s = 5.6444 min), not by distance.
    assert A.return_time_min(None, 0, 0, ac, 1000.0, 609.6) == pytest.approx(5.644444, abs=1e-5)

    # an unflyable return propagates None rather than a nonsense number
    assert A.return_time_min(0, 25, 0, ac, 18000.0, 609.6) is None

    # reserve = return * safety factor + terminal allowance
    assert A.required_reserve_time_min(16.666667) == pytest.approx(23.833333, abs=1e-5)


def test_wind_aware_usable_distance():
    ac = _test_aircraft()
    # (90 - 20) min * 60 s * 18 m/s
    assert A.wind_aware_usable_distance_m(None, 0, 0, ac, 20) == pytest.approx(75_600)

    # ONE sentinel, None, for every "cannot fly" case -- because planner branches on it.
    # Returning 0.0 for the exhausted-reserve case would flow into geo's
    # _initial_total_lines_from_budget, which RAISES on a non-positive budget, turning a
    # legitimate "too windy today" verdict into an exception in the plan path.
    assert A.wind_aware_usable_distance_m(None, 0, 0, ac, 95) is None    # reserve > endurance
    assert A.wind_aware_usable_distance_m(0, 25, 0, ac, 20) is None      # wind unflyable


def test_candidate_orientation():
    assert P._candidate_orientation(0) == (90, 270)       # sun +/- 90
    assert P._candidate_orientation(300) == (30, 210)     # wraps mod 360
    # tie-back to Tier 0: both candidates are exactly 90 off the sun -> perfect glint
    sun = 42
    first, second = P._candidate_orientation(sun)
    assert P._score_glint(first, sun) == pytest.approx(0)
    assert P._score_glint(second, sun) == pytest.approx(0)
    # V2C: at a 90 deg target the pair comes out 180 deg apart -- the SAME grid axis
    # flown in opposite directions. This is the structural reason both leg directions
    # collect science under the along-track mount.
    assert P._angular_distance(first, second) == pytest.approx(180)
