"""
Tier 1 -- selectable date/time + sun-state wiring (V2 Step A).

Foundational date/time plumbing. Like the rest of Tier 1 these must NEVER fail:
if the local->UTC resolver or the sun-state's date metadata is wrong, EVERY
higher tier inherits a wrong sun azimuth. This file leans on zoneinfo (system
tzdata) and pysolar rather than pure arithmetic, but the same "trust the
foundation" contract applies, so it lives in the Tier 1 band.

Vectors use hard literals (a known winter/PST instant and a known summer/PDT
instant) so they pin the conversion itself, not whatever the defaults happen to
hold today.
"""

import datetime

import pytest

import constants as CONST
import sun as S


def _utc(year, month, day, hour, minute=0):
    return datetime.datetime(year, month, day, hour, minute, tzinfo=datetime.timezone.utc)


# ---- resolve_mission_datetime: local -> UTC ------------------------------------

def test_resolver_winter_is_pst():
    # Jan 1 is PST (UTC-8): 10:00 local -> 18:00 UTC (the exact V1 fixed instant).
    assert S.resolve_mission_datetime("2026-01-01", "10:00") == _utc(2026, 1, 1, 18)


def test_resolver_summer_is_pdt():
    # Jul 15 is PDT (UTC-7): 10:00 local -> 17:00 UTC. Pins DST handling.
    assert S.resolve_mission_datetime("2026-07-15", "10:00") == _utc(2026, 7, 15, 17)


def test_resolver_returns_utc_aware():
    got = S.resolve_mission_datetime("2026-07-15", "10:00")
    assert got.tzinfo == datetime.timezone.utc


def test_resolver_defaults_to_v2_local_defaults():
    # No input at all -> the V2 local defaults (2026-01-01 10:00 PST) -> 18:00 UTC,
    # and identical to the module-level default the engine falls back on.
    assert S.resolve_mission_datetime() == _utc(2026, 1, 1, 18)
    assert S.resolve_mission_datetime() == S.mission_datetime


def test_resolver_none_inputs_fall_back():
    # The omitted-flag case: fromisoformat(None) raises TypeError, so this pins that
    # the except arm catches TypeError (not just ValueError) and defaults cleanly.
    assert S.resolve_mission_datetime(None, None) == S.mission_datetime


def test_resolver_garbage_inputs_fall_back():
    # Lenient design: an unparseable string raises ValueError and also falls back
    # to the defaults rather than crashing. (Note: this SWALLOWS bad input instead
    # of rejecting it -- see the audit note if strict rejection is ever wanted.)
    assert S.resolve_mission_datetime("not-a-date", "nonsense") == S.mission_datetime


def test_resolver_partial_input_fills_the_other_half():
    # Only a date given -> time falls back to the 10:00 local default (17:00 UTC in July).
    assert S.resolve_mission_datetime("2026-07-15", None) == _utc(2026, 7, 15, 17)
    # Only a time given -> date falls back to the 2026-01-01 default (PST, so 20:00 UTC).
    assert S.resolve_mission_datetime(None, "12:00") == _utc(2026, 1, 1, 20)


# ---- create_sun_state: date metadata + azimuth follow the passed instant -------

def test_sun_state_metadata_matches_passed_date():
    # REGRESSION for the Step A latent bug: day/hour/minute must be derived from the
    # passed date, not from the old V1 constants. Would fail against pre-fix code.
    instant = _utc(2026, 7, 15, 17, 30)
    ss = S.create_sun_state(CONST.V1_LAUNCH_POINT_LAT, CONST.V1_LAUNCH_POINT_LONG, instant)
    assert ss.current_day == 15
    assert ss.current_hour == 17
    assert ss.current_minute == 30


def test_azimuth_varies_with_date():
    # The whole point of Step A: a different instant moves the sun, which is what
    # will drive glint ranking in Step C.
    winter = S.create_sun_state(
        CONST.V1_LAUNCH_POINT_LAT, CONST.V1_LAUNCH_POINT_LONG, _utc(2026, 1, 1, 18)
    )
    summer = S.create_sun_state(
        CONST.V1_LAUNCH_POINT_LAT, CONST.V1_LAUNCH_POINT_LONG, _utc(2026, 7, 1, 20)
    )
    assert winter.azimuth != pytest.approx(summer.azimuth, abs=1.0)
