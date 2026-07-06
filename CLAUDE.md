# CLAUDE.md

Guidance for Claude Code when working in this repository.

## Working agreement

- **Git is mine.** I (the user) run all git commands — `add`, `commit`, `branch`,
  `push`, `pull`, `merge`, `rebase`, tags, etc. Do **not** stage, commit, or push
  on my behalf, and do not suggest doing so as part of a task unless I explicitly
  ask. You may edit files; I will handle version control.
- **Workflow.** I usually ask you to audit/plan first and implement the code changes
  myself, then ask you to audit my work against the plan. Follow that rhythm unless I
  say otherwise.

## Project overview

Calypso Monterey Bay flight-planning engine. A sun-aware flight planner for a
fixed-wing UAV (BlackSwift S2) collecting ocean-color / SST data over the M1
mooring in Monterey Bay. It builds an M1-centered lawnmower grid oriented for
minimum sun glint (science legs held 135° off the sun) and exports the route as
`.kml` and `.png`. See [`README.md`](README.md) for the full description.

**V1 (proof-of-engine) is complete and tested.** V2 is the next phase — see
[V2 roadmap](#v2-roadmap-what-comes-next).

## Layout

- `flight_plan_maker.py` — terminal entry point (run this). CLI flags: `--name`, `--out-dir`.
- `src/` — engine modules:
  - `constants.py` — V1 assumed constants (aircraft, M1, sensor, dates, weather, actions).
  - `objects.py` — core classes (Aircraft, Sensor, Weather, CurrentSunState,
    Waypoint, MissionRequest, CandidatePlan).
  - `sun.py` — pysolar → sun azimuth/elevation (`create_sun_state`, `mission_date`).
  - `aircraft_math.py` — endurance → distance budget, duration, battery margin.
  - `geo.py` — geodesic math + M1-centered lawnmower grid geometry.
  - `planner.py` — the hub: assembles objects, scores glint, builds the plan.
  - `outputs.py` — KML + PNG writers.
  - `validator.py` — **empty**, reserved for V2 legality/feasibility gating.
- `tests/` — tiered pytest harness (`test_0_*` … `test_4_*`); see [Setup & run](#setup--run).
- `conftest.py`, `pytest.ini`, `requirements-dev.txt`, `pyrightconfig.json` — test wiring
  and editor import resolution (`pyrightconfig` sets `extraPaths: ["src"]` so Pylance
  resolves the flat `import geo` / `planner` / `constants` style).

## Design conventions

- **"Dumb unidirectionality":** each module knows only as much about the rest of
  the program as it strictly needs. `planner.py` is the hub that knows the other
  modules; the other modules do not reach back. Preserve this when adding code —
  new V2 modules (e.g. a `weather.py`, a fleshed-out `validator.py`) must be **leaves**
  that `planner.py` orchestrates, not modules that reach back into the hub.
- `outputs.py` is a black box that renders whatever the plan contains — it does
  not validate correctness. (Its docstring already anticipates moving *behind*
  validation in V2 so it only renders approved plans.)
- Modules import flat (`import constants as CONST`, `from geo import ...`); the entry
  point and `conftest.py` put `src/` on `sys.path`.

## Setup & run

Run from the repo root with the virtualenv active:

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
python flight_plan_maker.py        # optional: --name NAME --out-dir DIR
```

Output defaults to `./CALYPSO_OUTPUT` (repo-relative, created on first run); pass
`--out-dir` to write elsewhere.

**Tests** (tiered gate — pure math at the bottom, grid/classification/rendering
indicators above; `pytest.ini` runs `-x` so the run stops at the first broken tier):

```bash
pip install -r requirements-dev.txt   # one time: pytest
pytest                                 # all tiers, gated bottom-up
pytest tests/test_1_derived_math.py -o addopts=""   # one tier, no fail-fast
```

## Current state — what V1 actually does (context for future work)

Read this before touching the grid, classification, or output code.

- **5-point flight lines.** `geo.make_line_through_point` emits
  `[turn, collect_start, line_label (center), collect_stop, turn]`
  (`V1_POINTS_PER_LINE = 5`, the single source of truth — do not re-hardcode `5`).
  On a science leg the center is the M1 overflight if it's the center line; the
  `collect_start`/`collect_stop` inset points sit one `V1_COLLECTION_INSET_m` in from
  each turn (camera on/off after roll-out).
  The serpentine alternates heading **H** (science, camera on) and **H+180**
  (transit, camera off); only H legs collect valid science.
- **Heading-based classification.** `planner._classify_waypoints` tags a leg science
  vs transit by its **actual flown bearing** vs the winning orientation, measured
  *after* `_reorient_to_launch` (which may reverse the route and flip every leg's
  heading). This is deliberately reversal-safe — the Tier 3 "heading-safety" test
  pins it; don't regress to index/parity-based tagging.
- **Delimiter rendering.** `outputs._segment_builder` walks the route with a
  `collecting` flag: `collect_start` opens a green (science) run, `collect_stop`
  closes it, everything between (incl. `line_label`) is green. Science legs render as
  full lines with small symmetric gray gaps at the turns.
- **Metrics.** `science_lines = (N+1)//2`, `traverse_lines = N//2`, `offset_lines = N-1`
  where `N = total_lines` (odd, so the center line passes through M1 → free overflight).
- **Tests.** Tiers 0–1 are pure closed-form math (must never fail); Tiers 2–4 drive the
  real mission and assert structural invariants as *indicators* that the math is sound.
- **Known deferred items (V2 candidates):**
  - The **SCIENCE/TRANSIT OFFSET CORRECTION** documented in `geo.make_lawnmower_grid_through_m1`
    is written up but **not active**: science lines are spaced `2 × offset` apart, so
    the science swaths leave cross-track gaps and `grid_area_m2` is the bounding-box
    area, not true science coverage. Activate only once ranking expects true science area.
  - `geo.calculate_total_lines` (even-forcing) is **dead code** — a removal candidate.

## V2 roadmap — what comes next

The through-line: make the mission **situation-aware** (real date/time + real weather),
fold that into ranking, then gate plans for legality before output. Preserve dumb
unidirectionality throughout.

### A. Selectable mission date/time
Today the date/time is fixed by `constants.V1_DEFAULT_MISSION_{YEAR,MONTH,DAY_OF_MONTH,HOUR}`
→ `sun.mission_date` → `planner._V1_mission_sun_state`. Goal: let the user choose it.
- Add a `--date` / `--time` (or single datetime) flag in `flight_plan_maker._parse_args`
  and thread it through `planner.plan_default_mission` → `create_sun_state(date=...)`.
  `create_sun_state` already accepts a `date` param, so sun azimuth/elevation follow
  automatically — which is why this change also drives glint scoring (item C).
- ⚠️ **Latent bug to fix first:** `sun.create_sun_state` computes az/elev from the passed
  `date` but still stores `CurrentSunState`'s day/hour/minute from the **V1 constants**
  (`sun.py` ~lines 126–133). Derive those from the passed `date` or the sun-state
  metadata will disagree with its own angles once date/time is selectable.

### B. Weather integration
The `Weather` class (`objects.py`) already models cloud cover, wind speed/direction/gust,
visibility, condition, and `valid_time`; today `planner._V1_assumed_weather` is a stub
built from `DEFAULT_*` constants (clear skies, zero wind).
- Add a **leaf** module (e.g. `weather.py`) that fetches from NWS
  (`constants.NWS_BASE_URL = https://api.weather.gov`) for a given lat/lon/date and
  returns a populated `Weather` object; `planner` calls it, it does not reach back.
- NWS requires a **User-Agent** header (`constants.NWS_USER_AGENT` is present but
  commented out — fill it in).
- ⚠️ **Constraint:** NWS forecasts extend only ~7 days out. A selectable date beyond that
  (or in the past) needs a different source or a graceful fallback to the assumed stub.
  `CLEAR_SKY_THRESHOLD_PERCENTAGE` / `OVERCAST_SKY_THRESHOLD_PERCENTAGE` exist for
  classifying sky condition.

### C. Fold date/time + weather into glint scoring
Today `planner._score_glint` is the **only** ranking metric and uses the fixed sun
azimuth (`_score_candidate` / `_passes_glint_gate`, gate = `V1_GLINT_TOLERANCE_DEG`).
- Date/time (A) already varies the sun azimuth feeding glint.
- Add weather (B) as a factor: e.g. overcast diffuses sunlight so glint matters less;
  wind above `BLACKSWIFT_WIND_RATING_ms` (15 m/s) should gate feasibility; low visibility
  bears on VLOS. Extend scoring into a composite metric and/or add parallel gates
  alongside the glint gate rather than overloading `_score_glint`.

### D. `validator.py` — Part 107 legality/feasibility gating (later in V2)
`validator.py` is empty. Build it to take a `CandidatePlan` and decide legal + feasible
**before** `outputs.py` writes anything. `CandidatePlan` already carries the result
fields: `_is_legal`, `_is_aircraft_feasible`, `_validation_messages`, `_passes_over_m1`.
- Part 107 checks to consider: **≤ 400 ft AGL** (current altitude 118 m ≈ 387 ft — under,
  but validate); **daylight / civil-twilight** operation (use `CurrentSunState.elevation`);
  **VLOS** (the grid spans several km from launch — a genuine concern); **airspace
  authorization** for Monterey Bay; **wind/weather feasibility** (from B + the aircraft's
  wind rating); over-water operations.
- Wiring: `planner` builds a candidate → `validator` gates it → only valid plans reach
  `outputs`. Keep `validator` a leaf; `planner` orchestrates the gate.

## Notes

- Target Python 3.12+ (developed/tested on 3.14.4). `itertools.batched` (used in
  `planner._classify_waypoints`) requires 3.12.
- V1 is a proof-of-engine build: fixed aircraft, clear skies, fixed mission date/time,
  assumed legal-to-fly, glint as the only ranking metric. V2 replaces those assumptions
  one at a time per the roadmap above.