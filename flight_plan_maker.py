"""
flight_plan_maker.py is the terminal based entry point for the flight planning engine in V2.

The file follows the engine design paradigm of "dumb unidirectionality", meaning that flight_plan_maker is only
as knowledgeable of the files in src/ as it needs to be. It also only serves one role, ask the planner for a plan, then
hand-off to outputs.py. This is the user-friendly entry point that allows for the manual production of output
from the engine.
"""

import argparse
import os
import sys
from zoneinfo import ZoneInfo

# src/ must be on the path BEFORE the engine modules below are imported.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

import constants as CONST
import outputs
import planner
from sun import resolve_mission_datetime


def _design_wind_ms(text):
    """
    argparse type for --design-wind: a wind speed in m/s that cannot be negative.
    """

    try:
        wind_ms = float(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"the design wind must be a number in m/s, not {text!r}")

    if wind_ms < 0:
        raise argparse.ArgumentTypeError("the design wind cannot be negative")

    return wind_ms


def _parse_args():
    """
    Optional overrides for on-command generation: plan name, output directory, the
    mission's local date and time, and the design wind.
    """

    parser = argparse.ArgumentParser(description="Generate a Calypso V2 flight plan.")

    parser.add_argument("--name", default="V2 Plan")
    parser.add_argument("--out-dir", default=CONST.OUTPUT_DIRECTORY)
    parser.add_argument("--date", default=None)
    parser.add_argument("--time", default=None)
    parser.add_argument(
        "--design-wind",
        type=_design_wind_ms,
        default=CONST.DEFAULT_DESIGN_WIND_ALOFT_ms,
        help="wind the plan is sized for, in m/s at flight altitude (not the 10 m forecast)",
    )

    return parser.parse_args()


def _forecast_wind_text(weather):
    """
    The forecast wind as NWS gives it, at its own height. It is never converted to flight
    altitude: over M1 the morning wind aloft is ~1.15x the 10 m wind, not the 1/7 law's 1.79x.
    """

    if not weather.wind_is_measured:
        return "none for this date and time (reported only, never applied)"

    return (
        f"{round(weather.wind_speed, 1)} m/s from {round(weather.wind_direction)} deg at "
        f"{CONST.NWS_WIND_HEIGHT_m} m ({weather.source}; reported only, never applied)"
    )


def _climb_orbit_text(plan):
    """
    Where the aircraft climbs and between which heights: from its transition height above
    home, or from the pad for a vehicle that never transitions.
    """

    climb_wp = plan.climb_waypoint
    if plan.transition_height_agl_m is None:
        climb_from = "the pad"
    else:
        climb_from = f"its {plan.transition_height_agl_m:g} m transition above home"

    return (
        f"{plan.climb_orbit_radius_m:g} m radius around {climb_wp.latitude:.5f}, "
        f"{climb_wp.longitude:.5f}, from {climb_from} to {plan.mission_request.altitude} m"
    )


def _print_summary(plan, kml_path, png_path, json_path, mission_datetime):
    """
    User-friendly terminal recap of what was produced, without force-opening files.
    Extended in V2 to echo the selected mission datetime (local + UTC), and since the
    camera rollout fix to show the design wind, the geometry it produced, and the
    forecast wind beside them. The forecast is reported only: it never shapes the plan.
    Since K-6 it also shows the climb orbit and the takeoff and landing phases, and ends
    with every pilot note the planner attached to the plan.
    """

    # mission_datetime is a UTC-aware datetime; show both the Monterey-local wall
    # clock the user thinks in and the UTC instant the engine actually computed with.
    local_dt = mission_datetime.astimezone(ZoneInfo(CONST.V2_MISSION_INPUT_TIMEZONE))

    print(f"Mission : {plan.name}")
    print(f"When    : {local_dt:%Y-%m-%d %H:%M} local  ({mission_datetime:%Y-%m-%d %H:%M} UTC)")
    print(f"Lines   : {plan.total_lines}  |  Glint Score: {plan.score}")
    print(f"Total Flight Duration: {round(plan.duration, 1)} min")
    print(f"Transit Flight: {round(plan.transit_duration_min, 2)} min, {round(plan.transit_distance_m, 2)} meters")
    print(f"Grid Flight: {round(plan.grid_duration_min, 2)} min, {round(plan.total_grid_distance_m, 2)} meters")
    print(
        f"Phases: climb {plan.climb_duration_min:.2f} min | descent overrun "
        f"{plan.descent_overrun_min:.2f} min | hand-offs {plan.handoff_reserve_min:.2f} min "
        f"(all inside Transit Flight's time)"
    )
    print(f"Margin: {round(plan.margin, 1)} min")
    print(f"Departure Bearing: {round(plan.departure_bearing_deg, 2)} deg | Approach Bearing: {round(plan.approach_bearing_deg, 2)} deg")
    print(f"Climb Orbit: {_climb_orbit_text(plan)}")
    print(f"Design Wind: {plan.mission_request.design_wind_aloft_ms:.1f} m/s at flight altitude (planning input) | Collection Inset: {round(plan.collection_inset_m, 2)} m")
    print(f"Line 1 Lead-in: {round(plan.entry_pushback_m, 2)} m, for a {round(plan.entry_arrival_angle_deg, 2)} deg turn in from the transit")
    print(f"Forecast Wind: {_forecast_wind_text(plan.weather)}")
    print(f"KML -> {kml_path}")
    print(f"PNG -> {png_path}")
    print(f"PLAN -> {json_path}")
    for note in plan.pilot_notes:
        print(f"RPIC NOTE: {note}")


def main():

    args = _parse_args()

    mission_datetime = resolve_mission_datetime(args.date, args.time)

    plan = planner.plan_default_mission(
        args.name, mission_datetime=mission_datetime, design_wind_aloft_ms=args.design_wind
    )

    kml_path = outputs.write_kml(plan, args.out_dir)

    png_path = outputs.write_png(plan, args.out_dir)

    json_path = outputs.write_qgc_plan(plan, args.out_dir)

    _print_summary(plan, kml_path, png_path, json_path, mission_datetime)


if __name__ == "__main__":
    main()
