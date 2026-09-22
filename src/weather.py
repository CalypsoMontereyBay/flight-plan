"""
Leaf file for the National Weather Service API data necessary for Version 2B
of the Calypso Flight Engine. weather.py retrives NWS data for a given day.
The availability of forecasting data also means that CFE plans can be generated up
to a week in advance, allowing for operational flexibility around agencies with
administrative delays such as UCSC, MBARI, and the FAA. weather.py follows the design
paradigm, no other file in the engine is aware of weather.py.

COVERAGE IS PER FIELD, NOT PER REQUEST. Every gridpoint field carries its own series with
its own span, and they differ enormously:

    windSpeed / windDirection / windGust   ~176 h   covers the full 7-day horizon
    skyCover                               ~179 h   covers the full 7-day horizon
    visibility                             8-30 h   SHORT TERM ONLY, and volatile

So a single mission datetime can be well inside the forecast for wind and long past the
end of it for visibility. That is why _value_at_time honours the interval DURATION and
returns None outside coverage, and why every field records itself in
Weather.stale_fields when its answer is a DEFAULT_* rather than a forecast. Consumers must
ask before trusting: a defaulted 10-mile visibility looks like a perfect day.
"""

# Imports:
from objects import Weather
import constants as C
import requests
import re
from datetime import datetime, timedelta, timezone
#from zoneinfo import ZoneInfo

"""
Private Helpers for weather.py's main function are below:
"""

"""
_within_forecast checks if a date/time request by the user is within
the maximum forecast period offered by the NWS.
"""


def _within_forecast_horizon(when):

    curr_datetime = datetime.now(timezone.utc)

    forecast_horizon_dt = curr_datetime + timedelta(C.NWS_FORECAST_HORIZON_days)

    if curr_datetime.date() <= when.date() <= forecast_horizon_dt.date():
        return True
    else:
        return False


"""
The _http_get_json(url) function takes a url and sets the User-Agent & Accept for the NWS API.
It also applies the timeout, retries once on a code 429 or 5xx, and raises an error on non-200 codes. 
NWS is changing to an API key format soon, this is where it will need to go.
"""


def _http_get_json(url: str):

    headers = {"User-Agent": C.NWS_USER_AGENT, "Accept": C.NWS_ACCEPT_HEADER}
    
    for attempt in range (C.NWS_MAX_RETRIES + 1):
        
        response = requests.get(url, headers=headers, timeout=C.NWS_REQUEST_TIMEOUT_s)
        
        if response.status_code == 429 or response.status_code >= 500:
            if attempt < C.NWS_MAX_RETRIES:
                continue
            
        response.raise_for_status()
        return response.json()

    # Reached only if the loop never ran (NWS_MAX_RETRIES < 0). Without this the function
    # returned None, the caller's subscript raised a TypeError that get_weather does not
    # catch, and a bad retry count crashed the planner instead of falling back to the stub.
    raise requests.exceptions.RequestException(
        f"No NWS request was attempted for {url} (NWS_MAX_RETRIES = {C.NWS_MAX_RETRIES})"
    )

"""
_grid_data_url(lat, lon) uses /points endpoint from the NWS website. 
returns forecasting data as grid data
"""

def _grid_data_url(lat, lon):
    
    points = _http_get_json(f"{C.NWS_BASE_URL}/points/{lat},{lon}")
    
    grid_data_url = points["properties"]["forecastGridData"]
    
    return _http_get_json(grid_data_url)

"""
_value_at_time returns the current weather values at the specified time,
**NOTE** _value_at_time is unit-agnostic, unit conversion is built into separate helpers.
This helper handles data as it comes. Data is converted to CFE usable units as needed later.
"""

def _parse_iso_duration (text: str):
    """
    Parse the duration half of an NWS validTime ("PT1H", "PT6H", "P1DT6H", "PT30M").

    Returns a timedelta, or None when it cannot be parsed. Callers treat None as
    "coverage unknown" and decline to use the value rather than guessing at it.
    """

    match = re.fullmatch(r"P(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?)?", text or "")

    if match is None or not any(match.groups()):
        return None

    days, hours, minutes, seconds = (int(g) if g else 0 for g in match.groups())

    return timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)


def _value_at_time (property_block, when):
    """
    Value of the interval that CONTAINS `when`, or None if no interval does.

    The duration matters. Each NWS field has its OWN coverage span -- wind runs ~172 h
    while visibility runs ~29 h -- so past the end of a field's series there is simply
    no forecast for the requested time. Ignoring the duration and returning the final
    entry (the pre-V2C-2 behaviour) handed callers a days-old reading dressed up as a
    forecast, which for the RTH gate means a confident verdict from expired data.
    Returning None instead lets get_weather substitute the honest DEFAULT_* and record
    the field as stale.
    """

    for entry in property_block.get("values", []):

        start_str, _, duration_str = entry["validTime"].partition("/")

        start = datetime.fromisoformat(start_str)

        # The series is ordered, so once an interval STARTS after `when`, no later
        # interval can contain it either.
        if start > when:
            break

        duration = _parse_iso_duration(duration_str)

        if duration is None:
            continue

        if when < (start + duration):
            return entry["value"]

    return None


"""
_to_ms(value, uom) Takes a kmh (or whatever unit NWS uses in the future) value and convers to m/s.
"""

def _to_ms (value, uom: str | None):
    
    if value is None:
        return None

    if uom == "wmoUnit:km_h-1":     # NWS wind unit (verified live) -> convert to m/s

        return value * C.KMH_TO_MS

    if uom == "wmoUnit:m_s-1":      # already m/s -> pass through unchanged
        return value

    # Unknown unit: don't feed a wrong-unit number into the wind gate; treat as missing.
    return None
    


"""
_degrees_or_none mirrors _to_ms for angles. Wind DIRECTION previously had no unit check at
all while wind SPEED did, so an unexpected unit would have flowed straight into the crab
and RTH math unchallenged. Safety math does not get unvalidated inputs.
"""


def _degrees_or_none (value, uom: str | None):

    if value is None:
        return None

    if uom == "wmoUnit:degree_(angle)":     # NWS wind direction unit (verified live)
        return value

    return None


"""
_field_at_time reads one gridpoint field and records whether the answer is real.

A field is STALE when the block is missing entirely, when no interval covers the requested
time, or when the unit is not one we recognise. All three end in the same DEFAULT_*, and
all three mean the same thing to a safety gate: the number being held is not a forecast
for this mission. validator reads the set to decline certification rather than certify on
a default that happens to look like fair weather.
"""


def _field_at_time (props, field_name: str, when, stale_fields: set):

    block = props.get(field_name)

    if block is None:
        stale_fields.add(field_name)
        return None, None

    value = _value_at_time(block, when)

    if value is None:
        stale_fields.add(field_name)

    return value, block.get("uom")


"""
_conditon_from_skycover uses the sky threshold percentage constant and returns the proper
string to relay to the user what the cloud conditions are.
"""


def _condition_from_skycover (pct):
    
    if (pct >= C.OVERCAST_SKY_THRESHOLD_PERCENTAGE):
        return "overcast"
    
    elif ((100 - pct) >= C.CLEAR_SKY_THRESHOLD_PERCENTAGE):
        
        return C.DEFAULT_WEATHER_CONDITION
    
    else:

        return "partly cloudy"


"""
get_weather(latitude, longitude, when) is weather.py's ONLY public function. It runs the
helpers above in order and returns a populated Weather object, or None when live weather
cannot be produced (out of forecast horizon, or any network / parse failure). planner.py
calls this and falls back to its clear-sky stub whenever it receives None, so Step B can
never stop a plan from being produced.
"""


def get_weather(latitude, longitude, when):

    # NWS only forecasts ~7 days out (and not the past) -> skip the network entirely otherwise.
    if not _within_forecast_horizon(when):
        return None

    # Any failure in the fetch / parse / build collapses to None so the hub uses the stub.
    try:
        grid = _grid_data_url(latitude, longitude)
        if grid is None:
            return None
        props = grid["properties"]

        # Every field records its own provenance. Coverage spans differ per field -- wind
        # runs ~172 h while visibility runs ~29 h -- so one mission datetime can be well
        # inside the forecast for wind and past the end of it for visibility.
        stale = set()

        cloud_pct, _uom = _field_at_time(props, "skyCover", when, stale)

        wind_raw, wind_uom = _field_at_time(props, "windSpeed", when, stale)
        wind_ms = _to_ms(wind_raw, wind_uom)

        gust_raw, gust_uom = _field_at_time(props, "windGust", when, stale)
        gust_ms = _to_ms(gust_raw, gust_uom)

        dir_raw, dir_uom = _field_at_time(props, "windDirection", when, stale)
        wind_dir = _degrees_or_none(dir_raw, dir_uom)

        vis_raw, _uom = _field_at_time(props, "visibility", when, stale)
        visibility_m = vis_raw

        # A recognised value that failed UNIT conversion is just as unusable as a missing
        # one, so it joins the stale set too. _field_at_time cannot see this -- it hands
        # back the raw value and leaves conversion to the caller.
        if wind_raw is not None and wind_ms is None:
            stale.add("windSpeed")
        if dir_raw is not None and wind_dir is None:
            stale.add("windDirection")

        # Wind counts as MEASURED only when BOTH halves of the vector are real. Captured
        # BEFORE the DEFAULT_* fill below, because that fill is exactly what erases the
        # distinction -- a missing wind field becomes DEFAULT_ZERO_WIND, i.e. assumed dead
        # calm, which is the most permissive possible input to an RTH gate. validator must
        # not certify a return against assumed conditions.
        wind_measured = wind_ms is not None and wind_dir is not None

        # Fill any missing field with the same DEFAULT_* the stub uses.
        cloud_pct = cloud_pct if cloud_pct is not None else C.V1_DEFAULT_MISSION_CLOUD_COVER
        wind_ms = wind_ms if wind_ms is not None else C.DEFAULT_ZERO_WIND
        gust_ms = gust_ms if gust_ms is not None else C.DEFAULT_WIND_GUST_ms
        wind_dir = wind_dir if wind_dir is not None else C.DEFAULT_WIND_DIRECTION_deg
        visibility_m = visibility_m if visibility_m is not None else C.DEFAULT_VISIBILITY_m

        condition = _condition_from_skycover(cloud_pct)

        return Weather(
            latitude,
            longitude,
            when,
            cloud_pct,
            wind_ms,
            wind_dir,
            gust_ms,
            visibility_m,
            condition,
            wind_is_measured=wind_measured,
            stale_fields=stale,
            source=C.WEATHER_SOURCE_NWS,
        )

    except (requests.exceptions.RequestException, KeyError, ValueError):
        return None
        

