"""
Tier 1 -- weather leaf (V2 Step B).

Foundational, deterministic, and fully OFFLINE: the NWS fetch is monkeypatched, so the
suite never touches the network. Covers the leaf helpers (unit conversion, condition,
value-at-time, horizon) and the get_weather wrapper's assembly plus its safety net
(any failure -> None). The planner-level fallback (None -> stub) is pinned in Tier 3.
"""

import datetime
from datetime import timezone, timedelta

import pytest

import constants as C
import weather as W


def _utc(*args):
    return datetime.datetime(*args, tzinfo=timezone.utc)


# ---- pure helpers --------------------------------------------------------------

def test_to_ms_conversions():
    assert W._to_ms(18, "wmoUnit:km_h-1") == pytest.approx(5.0)    # 18 / 3.6
    assert W._to_ms(9.0, "wmoUnit:m_s-1") == pytest.approx(9.0)    # already m/s
    assert W._to_ms(None, "wmoUnit:km_h-1") is None               # null hour
    assert W._to_ms(5, "wmoUnit:mi_h-1") is None                  # unknown unit -> missing


def test_condition_from_skycover_bands():
    assert W._condition_from_skycover(90) == "overcast"                     # >= 85
    assert W._condition_from_skycover(85) == "overcast"                     # boundary
    assert W._condition_from_skycover(3) == C.DEFAULT_WEATHER_CONDITION     # <= 5% cloud -> clear
    assert W._condition_from_skycover(50) == "partly cloudy"                # between


def test_value_at_time_picks_covering_entry():
    block = {"uom": "wmoUnit:percent", "values": [
        {"validTime": "2026-07-20T14:00:00+00:00/PT3H", "value": 20},
        {"validTime": "2026-07-20T17:00:00+00:00/PT2H", "value": 45},
        {"validTime": "2026-07-20T19:00:00+00:00/PT6H", "value": 70},
    ]}
    # 18:00Z sits inside the 17:00-19:00 block -> 45
    assert W._value_at_time(block, _utc(2026, 7, 20, 18)) == 45
    # before the first start -> None
    assert W._value_at_time(block, _utc(2026, 7, 20, 13)) is None
    # empty series -> None
    assert W._value_at_time({"values": []}, _utc(2026, 7, 20, 18)) is None


def test_parse_iso_duration():
    assert W._parse_iso_duration("PT1H") == timedelta(hours=1)
    assert W._parse_iso_duration("PT6H") == timedelta(hours=6)
    assert W._parse_iso_duration("P1DT6H") == timedelta(days=1, hours=6)
    assert W._parse_iso_duration("PT30M") == timedelta(minutes=30)
    assert W._parse_iso_duration("PT1H30M") == timedelta(hours=1, minutes=30)
    # unparseable -> None, so callers decline the value instead of guessing coverage
    assert W._parse_iso_duration("") is None
    assert W._parse_iso_duration("P") is None
    assert W._parse_iso_duration("garbage") is None


def test_value_at_time_returns_none_past_coverage():
    # REGRESSION. Before V2C-2 this helper ignored the interval DURATION and returned the
    # last entry whose start was <= `when` -- forever. A mission days past the end of a
    # field's series therefore received that field's final reading dressed up as a
    # forecast. For visibility (~29 h of coverage against a 7-day horizon) that was the
    # normal case, not an edge case, and for the RTH gate it means a confident safety
    # verdict computed from expired data.
    block = {"uom": "wmoUnit:percent", "values": [
        {"validTime": "2026-07-20T14:00:00+00:00/PT3H", "value": 20},
        {"validTime": "2026-07-20T17:00:00+00:00/PT2H", "value": 45},
    ]}

    assert W._value_at_time(block, _utc(2026, 7, 20, 15)) == 20     # inside the first
    assert W._value_at_time(block, _utc(2026, 7, 20, 18)) == 45     # inside the second

    # coverage ends at 19:00Z. The interval is half-open, so 19:00 itself is already out.
    assert W._value_at_time(block, _utc(2026, 7, 20, 19)) is None
    assert W._value_at_time(block, _utc(2026, 7, 20, 23)) is None
    assert W._value_at_time(block, _utc(2026, 7, 24, 12)) is None   # days past -> still None

    # a gap between intervals is also "no forecast", not "reuse the earlier one"
    gapped = {"values": [
        {"validTime": "2026-07-20T14:00:00+00:00/PT1H", "value": 10},
        {"validTime": "2026-07-20T20:00:00+00:00/PT1H", "value": 90},
    ]}
    assert W._value_at_time(gapped, _utc(2026, 7, 20, 17)) is None


def test_degrees_or_none_guards_the_unit():
    # Wind SPEED has always been unit-checked; wind DIRECTION was not, so an unexpected
    # unit would have flowed straight into the crab and RTH math unchallenged.
    assert W._degrees_or_none(270, "wmoUnit:degree_(angle)") == 270
    assert W._degrees_or_none(270, "wmoUnit:radian") is None
    assert W._degrees_or_none(270, None) is None
    assert W._degrees_or_none(None, "wmoUnit:degree_(angle)") is None


def test_within_forecast_horizon():
    now = datetime.datetime.now(timezone.utc)
    assert W._within_forecast_horizon(now) is True
    assert W._within_forecast_horizon(now + timedelta(days=2)) is True
    assert W._within_forecast_horizon(now - timedelta(days=2)) is False     # past
    assert W._within_forecast_horizon(now + timedelta(days=30)) is False    # beyond ~7d


# ---- get_weather wrapper (NWS fetch monkeypatched) -----------------------------

def _canned_grid(when):
    # start one hour before `when` so the single interval covers it
    start = (when - timedelta(hours=1)).isoformat()
    return {"properties": {
        "skyCover":      {"uom": "wmoUnit:percent",        "values": [{"validTime": f"{start}/PT6H", "value": 90}]},
        "windSpeed":     {"uom": "wmoUnit:km_h-1",         "values": [{"validTime": f"{start}/PT6H", "value": 18}]},
        "windGust":      {"uom": "wmoUnit:km_h-1",         "values": [{"validTime": f"{start}/PT6H", "value": 36}]},
        "windDirection": {"uom": "wmoUnit:degree_(angle)", "values": [{"validTime": f"{start}/PT6H", "value": 270}]},
        # NOTE: no "visibility" key -- mirrors the real MTR grid, which omits it
    }}


def test_get_weather_happy_path(monkeypatch):
    when = datetime.datetime.now(timezone.utc)
    grid = _canned_grid(when)

    def fake_http_get_json(url):
        if "/points/" in url:
            return {"properties": {"forecastGridData": "https://api.weather.gov/gridpoints/MTR/91,52"}}
        return grid

    monkeypatch.setattr(W, "_http_get_json", fake_http_get_json)

    wx = W.get_weather(C.V1_LAUNCH_POINT_LAT, C.V1_LAUNCH_POINT_LONG, when)

    assert wx is not None
    assert wx.wind_speed == pytest.approx(5.0)          # 18 km/h -> m/s
    assert wx.wind_gusts == pytest.approx(10.0)         # 36 km/h -> m/s
    assert wx.cloud_cover == 90
    assert wx.condition == "overcast"                   # 90% >= overcast threshold
    assert wx._data_source == C.WEATHER_SOURCE_NWS
    assert wx._visibility_m == C.DEFAULT_VISIBILITY_m   # absent in grid -> default
    assert wx._wind_direction_deg == 270


def _patch_grid(monkeypatch, grid):
    def fake_http_get_json(url):
        if "/points/" in url:
            return {"properties": {"forecastGridData": "https://api.weather.gov/gridpoints/MTR/91,52"}}
        return grid
    monkeypatch.setattr(W, "_http_get_json", fake_http_get_json)


def test_get_weather_records_provenance(monkeypatch):
    # The canned grid omits visibility (mirroring the real MTR response), so wind is real
    # but visibility is not. The Weather object must be able to say which is which.
    when = datetime.datetime.now(timezone.utc)
    _patch_grid(monkeypatch, _canned_grid(when))

    wx = W.get_weather(C.V1_LAUNCH_POINT_LAT, C.V1_LAUNCH_POINT_LONG, when)
    assert wx is not None

    assert wx.wind_is_measured is True              # both halves of the vector are real
    assert wx.is_stale("visibility") is True        # absent from the grid entirely
    assert wx.is_stale("windSpeed") is False
    assert wx.is_stale("windDirection") is False
    assert wx.visibility == C.DEFAULT_VISIBILITY_m  # defaulted, and flagged as such


def test_get_weather_out_of_coverage_is_not_measured_wind(monkeypatch):
    # SAFETY-CRITICAL. Wind present in the document but with no interval covering the
    # requested time must NOT read as measured. DEFAULT_ZERO_WIND makes an absent wind
    # field look like a dead-calm day, which is the most permissive possible input to an
    # RTH gate -- so "unknown" has to stay distinguishable from "calm".
    when = datetime.datetime.now(timezone.utc)
    stale_start = (when - timedelta(hours=12)).isoformat()      # ends 6 h before `when`
    grid = {"properties": {
        "skyCover":      {"uom": "wmoUnit:percent",        "values": [{"validTime": f"{stale_start}/PT6H", "value": 90}]},
        "windSpeed":     {"uom": "wmoUnit:km_h-1",         "values": [{"validTime": f"{stale_start}/PT6H", "value": 18}]},
        "windDirection": {"uom": "wmoUnit:degree_(angle)", "values": [{"validTime": f"{stale_start}/PT6H", "value": 270}]},
    }}
    _patch_grid(monkeypatch, grid)

    wx = W.get_weather(C.V1_LAUNCH_POINT_LAT, C.V1_LAUNCH_POINT_LONG, when)
    assert wx is not None

    assert wx.wind_is_measured is False             # <-- the whole point
    assert wx.is_stale("windSpeed") is True
    assert wx.is_stale("windDirection") is True
    assert wx.wind_speed == C.DEFAULT_ZERO_WIND     # defaulted to calm...
    assert wx.wind_direction == C.DEFAULT_WIND_DIRECTION_deg
    # ...but the plan can tell that calm was ASSUMED, not observed
    assert wx.wind_is_measured is not True


def test_get_weather_bad_unit_is_stale(monkeypatch):
    when = datetime.datetime.now(timezone.utc)
    start = (when - timedelta(hours=1)).isoformat()
    grid = {"properties": {
        "windSpeed":     {"uom": "wmoUnit:furlong_fortnight-1", "values": [{"validTime": f"{start}/PT6H", "value": 18}]},
        "windDirection": {"uom": "wmoUnit:radian",              "values": [{"validTime": f"{start}/PT6H", "value": 4.7}]},
    }}
    _patch_grid(monkeypatch, grid)

    wx = W.get_weather(C.V1_LAUNCH_POINT_LAT, C.V1_LAUNCH_POINT_LONG, when)
    assert wx is not None
    # a value that arrives in an unrecognised unit is as unusable as a missing one
    assert wx.is_stale("windSpeed") is True
    assert wx.is_stale("windDirection") is True
    assert wx.wind_is_measured is False


def test_get_weather_out_of_horizon_makes_no_call(monkeypatch):
    def boom(url):
        raise AssertionError("the network must not be touched when out of horizon")
    monkeypatch.setattr(W, "_http_get_json", boom)

    past = datetime.datetime.now(timezone.utc) - timedelta(days=10)
    assert W.get_weather(C.V1_LAUNCH_POINT_LAT, C.V1_LAUNCH_POINT_LONG, past) is None


def test_get_weather_network_failure_returns_none(monkeypatch):
    import requests

    def raise_req(url):
        raise requests.exceptions.ConnectTimeout("simulated timeout")
    monkeypatch.setattr(W, "_http_get_json", raise_req)

    when = datetime.datetime.now(timezone.utc)
    assert W.get_weather(C.V1_LAUNCH_POINT_LAT, C.V1_LAUNCH_POINT_LONG, when) is None
