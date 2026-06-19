# CLAUDE.md

Guidance for Claude Code when working in this repository.

## Working agreement

- **Git is mine.** I (the user) run all git commands — `add`, `commit`, `branch`,
  `push`, `pull`, `merge`, `rebase`, tags, etc. Do **not** stage, commit, or push
  on my behalf, and do not suggest doing so as part of a task unless I explicitly
  ask. You may edit files; I will handle version control.

## Project overview

Calypso Monterey Bay flight-planning engine. A sun-aware flight planner for a
fixed-wing UAV (BlackSwift S2) collecting ocean-color / SST data over the M1
mooring in Monterey Bay. It builds an M1-centered lawnmower grid oriented for
minimum sun glint (science legs held 135° off the sun) and exports the route as
`.kml` and `.png`. See [`README.md`](README.md) for the full description.

## Layout

- `flight_plan_maker.py` — terminal entry point (run this).
- `src/` — engine modules:
  - `constants.py` — V1 assumed constants (aircraft, M1, sensor, dates).
  - `objects.py` — core classes (Aircraft, Sensor, Weather, CurrentSunState,
    Waypoint, MissionRequest, CandidatePlan).
  - `sun.py` — pysolar → sun azimuth/elevation.
  - `aircraft_math.py` — endurance → distance budget, duration, battery margin.
  - `geo.py` — geodesic math + M1-centered lawnmower grid geometry.
  - `planner.py` — the hub: assembles objects, scores glint, builds the plan.
  - `outputs.py` — KML + PNG writers.
  - `validator.py` — stub reserved for V2 legality/feasibility gating.

## Design conventions

- **"Dumb unidirectionality":** each module knows only as much about the rest of
  the program as it strictly needs. `planner.py` is the hub that knows the other
  modules; the other modules do not reach back. Preserve this when adding code.
- `outputs.py` is a black box that renders whatever the plan contains — it does
  not validate correctness.

## Setup & run

Run from the repo root with the virtualenv active:

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
python flight_plan_maker.py        # optional: --name NAME --out-dir DIR
```

> The default `OUTPUT_DIRECTORY` in `src/constants.py` is an absolute path on the
> developer's machine; edit it or pass `--out-dir` so output lands somewhere that
> exists locally.

## Notes

- Target Python 3.10+ (developed/tested on 3.14.4).
- This is a V1 proof-of-engine build: fixed aircraft, clear skies, fixed mission
  date/time, assumed legal-to-fly, glint as the only ranking metric.
