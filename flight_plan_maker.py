"""
flight_plan_maker.py is the terminal based entry point for the flight planning engine in V1.

The file follows the engine design paradigm of "dumb unidirectionality", meaning that flight_plan_maker is only
as knowledgable of the files in src/ as it needs to be. It also only serves one role, ask the planner for a plan, then
hand-off to outputs.py. This is the user-friendly entry point that allows for the manual production of output
from the engine.
"""

# imports:
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

import argparse
import constants as CONST
import planner
import outputs

# optional overriding functionality for "On Command Generatation", also relevant for V2.
def _parse_args():

    parser = argparse.ArgumentParser(description="Generate a Calypso V1 flight plan.")

    parser.add_argument("--name", default=CONST.V1_DEFAULT_MISSION_NAME)
    parser.add_argument("--out-dir", default=CONST.OUTPUT_DIRECTORY)

    return parser.parse_args()


#User-Friendly terminal recap function for telling the user what was produced without
#force-opening files.
#WILL BE ADDED TO FOR V2

def _print_summary(plan, kml_path, png_path):
    
    print (f"Mission : {plan.name}")
    print(f"Lines   : {plan.total_lines}  |  Glint Score: {plan.score}")
    print(f"Duration: {round(plan.duration, 1)} min | Margin: {round(plan.margin,1)} min")
    print(f"KML -> {kml_path}")
    print(f"PNG -> {png_path}")
    
    
    
def main():
    
    args = _parse_args()
    
    plan = planner.plan_default_mission(args.name)
    
    kml_path = outputs.write_kml(plan, args.out_dir)

    png_path = outputs.write_png(plan, args.out_dir)
    
    _print_summary(plan, kml_path, png_path)
    
    
if __name__ == "__main__": main()