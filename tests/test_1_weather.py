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
