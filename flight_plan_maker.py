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


def _parse_args():
    """
    Optional overrides for on-command generation: plan name, output directory, and the
    mission's local date and time.
    """

    parser = argparse.ArgumentParser(description="Generate a Calypso V2 flight plan.")

    parser.add_argument("--name", default="V2 Plan")
    parser.add_argument("--out-dir", default=CONST.OUTPUT_DIRECTORY)
    parser.add_argument("--date", default=None)
    parser.add_argument("--time", default=None)

    return parser.parse_args()


def _print_summary(plan, kml_path, png_path, json_path, mission_datetime):
    """
    User-friendly terminal recap of what was produced, without force-opening files.
    Extended in V2 to echo the selected mission datetime (local + UTC).
    """

    # mission_datetime is a UTC-aware datetime; show both the Monterey-local wall
    # clock the user thinks in and the UTC instant the engine actually computed with.
    local_dt = mission_datetime.astimezone(ZoneInfo(CONST.V2_MISSION_INPUT_TIMEZONE))

    print(f"Mission : {plan.name}")
    print(f"When    : {local_dt:%Y-%m-%d %H:%M} local  ({mission_datetime:%Y-%m-%d %H:%M} UTC)")
    print(f"Lines   : {plan.total_lines}  |  Glint Score: {plan.score}")
    print(f"Total Flight Duration: {round(plan.duration, 1)} min")
    print(f"Transit Flight: {plan.transit_duration_min} min, {plan.non_grid_transit_m} meters")
    print(f"Grid Flight: {plan.grid_duration_min} min, {plan.total_grid_distance_m} meters")
    print(f"Margin: {round(plan.margin, 1)} min")
    print(f"Departure Bearing: {round(plan.departure_bearing_deg, 2)} deg | Approach Bearing: {round(plan.approach_bearing_deg, 2)} deg")
    print(f"KML -> {kml_path}")
    print(f"PNG -> {png_path}")
    print(f"PLAN -> {json_path}")


def main():

    args = _parse_args()

    mission_datetime = resolve_mission_datetime(args.date, args.time)

    plan = planner.plan_default_mission(args.name, mission_datetime=mission_datetime)

    kml_path = outputs.write_kml(plan, args.out_dir)

    png_path = outputs.write_png(plan, args.out_dir)

    json_path = outputs.write_qgc_plan(plan, args.out_dir)

    _print_summary(plan, kml_path, png_path, json_path, mission_datetime)


if __name__ == "__main__":
    main()
