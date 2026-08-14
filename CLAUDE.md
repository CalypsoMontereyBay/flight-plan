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

**V1 (proof-of-engine) is complete and tested. V2 Steps A (selectable date/time) and B
(live NWS weather) are complete and tested; Step C is being scoped.** See
[V2 roadmap](#v2-roadmap-what-comes-next).

## Layout

- `flight_plan_maker.py` — terminal entry point (run this). CLI flags: `--name`, `--out-dir`, `--date`, `--time`.
- `src/` — engine modules:
  - `constants.py` — engine constants (aircraft, M1, sensor, date/time defaults + timezone, weather, actions).
  - `objects.py` — core classes (Aircraft, Sensor, Weather, CurrentSunState,
    Waypoint, MissionRequest, CandidatePlan).
  - `sun.py` — local→UTC datetime resolver (`resolve_mission_datetime`, `mission_datetime`) + pysolar sun azimuth/elevation (`create_sun_state`).
  - `aircraft_math.py` — endurance → distance budget, duration, battery margin.
  - `geo.py` — geodesic math + M1-centered lawnmower grid geometry.
  - `weather.py` — **leaf**: live NWS weather for a lat/lon/datetime → populated `Weather`, or `None` (planner falls back to the stub).
  - `planner.py` — the hub: assembles objects, scores glint, builds the plan.
  - `outputs.py` — KML + PNG writers.
  - `validator.py` — **empty**, reserved for V2 legality/feasibility gating.
- `tests/` — tiered pytest harness (`test_0_*` … `test_5_*`); see [Setup & run](#setup--run).
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
pytest tests/test_2_derived_math.py -o addopts=""   # one tier, no fail-fast
```

## Current state — what the engine actually does (context for future work)

Read this before touching the grid, classification, or output code.

- **Selectable date/time (V2 Step A, done).** `flight_plan_maker` takes `--date`/`--time`
  as **Monterey-local** strings; `sun.resolve_mission_datetime` converts them to a tz-aware
  UTC instant (DST-aware via `zoneinfo`), defaulting to the V2 constants when omitted, and
  is lenient (bad input → defaults). `planner._build_dated_objects` builds the sun state /
  mission request / weather **per run** from that instant, so the sun azimuth (and thus
  glint) track the chosen time. `plan_default_mission(name, mission_datetime=None)` falls
  back to the module default. The summary echoes local + UTC.

- **Live weather (V2 Step B, done).** `weather.py` is a **leaf**: `get_weather(lat, lon, when)`
  returns a `Weather` populated from live NWS data, or `None` (outside the ~7-day forecast
  horizon, or any network/parse failure). `planner._build_dated_objects` uses it and falls
  back to the clear-sky / zero-wind stub on `None`, so a plan is always produced. Wind arrives
  in km/h (`_to_ms` → m/s); `condition` from `skyCover` thresholds; absent fields (often
  `visibility`) fall to `DEFAULT_*`. Offline tests monkeypatch the fetch (`tests/test_1_weather.py`).

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
- **Tests.** Tier 0 (primitives) and Tier 2 (derived math) are pure closed-form math
  (must never fail); Tier 1 pins the date/time resolver, sun-state, and weather-leaf wiring; Tiers 3–5 drive
  the real mission and assert structural invariants as *indicators* that the math is sound.
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

### A. Selectable mission date/time ✅ DONE
`flight_plan_maker` exposes `--date YYYY-MM-DD` / `--time HH:MM` (**Monterey local**, each
optional). `sun.resolve_mission_datetime` fills missing halves from the V2 defaults
(`V2_DEFAULT_MISSION_LOCAL_HOUR/MINUTE`, `V1_DEFAULT_MISSION_{YEAR,MONTH,DAY_OF_MONTH}`),
attaches `V2_MISSION_INPUT_TIMEZONE` (`America/Los_Angeles`, DST-aware) and converts to a
tz-aware UTC instant; module-level `sun.mission_datetime` is the default when no flags are
given. `planner.plan_default_mission(name, mission_datetime=None)` → `_build_dated_objects`
builds the sun state / mission request / weather per run, so sun azimuth (and glint)
track the chosen time.
- The old latent bug is fixed: `create_sun_state` now stores `CurrentSunState`'s
  day/hour/minute from the passed `date`, not the constants.
- Input handling is **lenient**: unparseable `--date`/`--time` silently falls back to the
  defaults (the try/except catches both `ValueError` and `TypeError` — `TypeError` is what
  `date.fromisoformat(None)` raises when a flag is omitted). Switch to hard-reject later if
  strict validation is wanted.

### B. Weather integration ✅ DONE
`weather.py` is a **leaf** the hub orchestrates: `weather.get_weather(lat, lon, when)` returns
a `Weather` populated from live NWS data, or `None` (out of forecast horizon, or any
network/parse failure); `planner._build_dated_objects` falls back to the clear-sky /
zero-wind stub on `None`, so a plan is always produced. The leaf never reaches back into the hub.
- **NWS (no API key; `User-Agent` required — `constants.NWS_USER_AGENT`).** Two-call flow:
  `GET /points/{lat},{lon}` → `properties.forecastGridData` URL (launch point = office **MTR**,
  grid **91,52**), then `GET` that gridpoint doc. Fields are time-series with a `uom`:
  `skyCover` (percent), `windSpeed`/`windGust` (**km/h — `_to_ms` ÷3.6 → m/s**),
  `windDirection` (deg). `visibility` (metres) is **sometimes absent** → `get_weather` fills
  `DEFAULT_VISIBILITY_m`. `_value_at_time` picks the latest interval whose `validTime` start ≤ T
  (no duration parsing).
- `_within_forecast_horizon` short-circuits any datetime outside `[now, now+7d]` to the stub
  **with no network call** (forecasts cover ~7 days from *now*).
- `_condition_from_skycover` maps `skyCover` → `"clear"` / `"partly cloudy"` / `"overcast"`
  via `CLEAR_SKY_THRESHOLD_PERCENTAGE` / `OVERCAST_SKY_THRESHOLD_PERCENTAGE`.
- Tests: `tests/test_1_weather.py` (offline; fetch monkeypatched) + a Tier 3 check that the
  planner uses the leaf's populated result.

### C. (V2C — in planning)
Reserved. This slot was opened by shifting the former ranking and legality items down one
letter (old C → D, old D → E); the V2C spec is being written. Fill in when it lands.

### D. Fold date/time + weather into glint scoring
Today `planner._score_glint` is the **only** ranking metric and uses the fixed sun
azimuth (`_score_candidate` / `_passes_glint_gate`, gate = `V1_GLINT_TOLERANCE_DEG`).
- Date/time (A) already varies the sun azimuth feeding glint.
- Add weather (B) as a factor: e.g. overcast diffuses sunlight so glint matters less;
  wind above `BLACKSWIFT_WIND_RATING_ms` (15 m/s) should gate feasibility; low visibility
  bears on VLOS. Extend scoring into a composite metric and/or add parallel gates
  alongside the glint gate rather than overloading `_score_glint`.

### E. `validator.py` — Part 107 legality/feasibility gating (later in V2)
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
- V1 was a proof-of-engine build (fixed aircraft, clear skies, fixed date/time, assumed
  legal-to-fly, glint-only ranking). V2 replaces those one at a time: **Steps A (date/time)
  and B (live NWS weather) are done**; the new **C** (in planning), weather-aware ranking
  (**D**), and legality gating (**E**) remain.