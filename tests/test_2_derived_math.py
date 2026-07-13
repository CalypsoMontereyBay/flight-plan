"""
Tier 2 -- derived sizing + aircraft math.

Builds directly on the Tier 0 primitives. These are still pure, closed-form math
(endurance/distance/duration conversions, grid sizing, orientation candidates), so
like Tier 0 they must NEVER fail. If a Tier 1 assert breaks, the -x gate stops the
run here before any grid/classification/rendering tier is even attempted.

Test vectors are hard literals (independent of production constants) so they pin the
math itself, not whatever CONST happens to hold today.
"""

# Imports:
import pytest
import constants as CONST, objects as O, aircraft_math as A, geo as G, planner as P


# One deterministic vehicle: endurance 90 min, turn penalty 10 s, cruise 18 m/s are
# the three values the aircraft-math functions actually consume.
def _test_aircraft():
    return O.Aircraft(90, 15, 3.35, 1.80, 57, 10, 12, 18)


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


# NOTE: geo.calculate_total_lines (the EVEN-forcing helper) has no callers -- the grid
# path uses _initial_total_lines_from_budget below. It is a removal candidate for V2 and
# is intentionally left untested here rather than pinning dead code.
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


def test_candidate_orientation():
    assert P._candidate_orientation(0) == (135, 225)      # sun +/- 135
    assert P._candidate_orientation(300) == (75, 165)     # wraps mod 360
    # tie-back to Tier 0: both candidates are exactly 135 off the sun -> perfect glint
    sun = 42
    first, second = P._candidate_orientation(sun)
    assert P._score_glint(first, sun) == pytest.approx(0)
    assert P._score_glint(second, sun) == pytest.approx(0)
