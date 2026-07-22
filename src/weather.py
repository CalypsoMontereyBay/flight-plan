"""
Leaf file for the National Weather Service API data necessary for Version 2B
of the Calypso Flight Engine. weather.py retrives NWS data for a given day.
The availability of forecasting data also means that CFE plans can be generated up
to a week in advance, allowing for operational flexibility around agencies with
administrative delays such as UCSC, MBARI, and the FAA. weather.py follows the design
paradigm, no other file in the engine is aware of weather.py.
"""

# Imports:
from objects import Weather
import constants as C
import requests
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

def _value_at_time (property_block, when):
    
    covering_value = None
    
    for entry in property_block.get("values", []):
        
        start_str = entry["validTime"].split("/")[0]
        
        start = datetime.fromisoformat(start_str)
        
        if start <= when:
            
            #Since the valid times end right when another begins, we want the valid time that 'when' sits inside, not before.
            #the covering value tells us which valid time value we are looking at, we keep the one that came most
            #recently before 'when'
            covering_value = entry["value"]
            
        else:
            break
        
    return covering_value


"""
_to_ms(value, uom) Takes a kmh (or whatever unit NWS uses in the future) value and convers to m/s.
"""

def _to_ms (value, uom:str):
    
    if value is None:
        return None

    if uom == "wmoUnit:km_h-1":     # NWS wind unit (verified live) -> convert to m/s

        return value * C.KMH_TO_MS

    if uom == "wmoUnit:m_s-1":      # already m/s -> pass through unchanged
        return value

    # Unknown unit: don't feed a wrong-unit number into the wind gate; treat as missing.
    return None
    


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
        
