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
minimum sun glint (science legs held **90° off the sun**) and exports the route as
`.kml` and `.png`. See [`README.md`](README.md) for the full description.

**V1 (proof-of-engine) is complete and tested. V2 Steps A (selectable date/time), B
(live NWS weather) and C-1 (along-track payload mount) are complete and tested;
C-2 (boresight/crab) is next.** See [V2 roadmap](#v2-roadmap-what-comes-next).

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

- **Along-track payload mount (V2 Step C-1, done).** ⚠️ **Read the MOUNTING NOTE at the top
  of `geo.py` before touching any FOV math.** The SST camera is now pitched **along-track**
  (forward, under the nose, 30° off-nadir); it used to be rolled **cross-track** at 40°.
  Only one axis is ever tilted, and the tilt decides which formula each axis uses:
  tilted → `h·(tan(θ+fov/2) − tan(θ−fov/2))`, untilted → `2·(h/cos θ)·tan(fov/2)`.
  When the mount rotated, `ground_swath_width_m` and `ground_footprint_along_m`
  **swapped formula bodies** — that swap looks like a bug in `git blame` and is not.
  Three consequences drive everything else below:
  1. Science legs are held **90° off the sun** (was 135°), gated at `V1_GLINT_TOLERANCE_DEG`
     (held at 15°, not tightened — see the note on that constant).
  2. The cross-track swath is now **centered on the ground track**. Under the old roll it
     sat 33.8–241.9 m off to *one side*, so the "free M1 overflight" imaged nothing at M1.
  3. **Both leg directions collect science**, because `sun ± 90` describes one grid axis
     flown both ways. This is why `_candidate_orientation`'s two candidates come out 180°
     apart — documented, not a bug.
  `Sensor.mounting` records the assumption; `planner._build_grid_for_orientation` raises if
  a `Sensor` declares anything other than along-track. `geo.sensor_parallax_m` reports the
  **352 m** offset between nadir and the boresight ground point — reporting only, **not
  corrected for**; see step C-2.
- **5-point flight lines.** `geo.make_line_through_point` emits
  `[turn, collect_start, line_label (center), collect_stop, turn]`
  (`V1_POINTS_PER_LINE = 5`, the single source of truth — do not re-hardcode `5`).
  The center is the M1 overflight if it's the center line; the
  `collect_start`/`collect_stop` inset points sit one `V1_COLLECTION_INSET_m` in from
  each turn (camera on/off after roll-out). **Every** leg collects, so the serpentine no
  longer alternates science/transit.
- **Classification.** `planner._classify_waypoints` tags purely by position within the
  5-point leg — there is no science-vs-transit decision left to make. The old
  reversal-safety hazard (that `_reorient_to_launch` flips every leg's heading) is
  **designed out** rather than guarded: reversal cannot change which legs collect when
  all of them do. The invariant now lives in the Tier 4 "heading-safety" test, which pins
  the physical requirement — every leg's flown bearing is within tolerance of 90° relative
  azimuth to the sun. Don't regress to index/parity tagging, and don't reintroduce a
  heading branch here.
- **Delimiter rendering.** `outputs._segment_builder` walks the route with a
  `collecting` flag: `collect_start` opens a green (science) run, `collect_stop`
  closes it, everything between (incl. `line_label`) is green. Science legs render as
  full lines with small symmetric gray gaps at the turns.
- **Metrics.** `science_lines = N`, `traverse_lines = 0`, `offset_lines = N-1`
  where `N = total_lines` (odd, so the center line passes through M1 → free overflight).
  `cross_track_swath_m` and `sensor_parallax_m` ride the same metrics dict and reach the
  plan via `set_grid_metrics`.
- **Tests.** Tier 0 (primitives) and Tier 2 (derived math) are pure closed-form math
  (must never fail); Tier 1 pins the date/time resolver, sun-state, and weather-leaf wiring; Tiers 3–5 drive
  the real mission and assert structural invariants as *indicators* that the math is sound.
- **Known deferred items (V2 candidates):**
  - **Parallax is reported, not corrected.** The imaged strip sits 352 m forward of the
    collection window, so ~8% of each line goes un-imaged at the near end and the strip
    overruns the far turn. Deferred to C-2 so it lands together with crab shear — both are
    along-track displacements and should be handled by the same code.
  - `V1_DEFAULT_GRID_WIDTH_km`, `V1_DEFAULT_LINE_LENGTH_km` and `V1_DEFAULT_LINE_SPACING_km`
    are **declared but never read** — the grid is sized from the endurance budget in
    `geo._initial_total_lines_from_budget`. Removal candidates.

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

### C-1. Along-track payload mount ✅ DONE
The SST camera was remounted: **yawed to face forward under the nose and pitched to 30°
off-nadir**, replacing the cross-track roll at 40°. See the C-1 bullet in
[Current state](#current-state--what-the-engine-actually-does-context-for-future-work)
for what that changed and why the two FOV formulas traded places.
- Target relative azimuth moved 135° → **90°** (`SCIENCE_RELATIVE_AZIMUTH_deg`), tolerance
  **held at 15°**. Also raised in the same pass: altitude → 609.6 m (2000 ft), overlap → 50%.
- Both leg directions now collect, which made the old **SCIENCE/TRANSIT OFFSET CORRECTION**
  block in `geo.py` obsolete — its premise (only alternate lines collect) is dead, so
  `offset_m` as computed is already correct. It was **deleted**, not deferred.
- `geo.sensor_parallax_m` added; `Sensor.mounting` added and guarded in `planner`.

### C-2. Boresight referencing — crosswind crab (next)
Q4 of the C-scoping decided the 90° ± 15 is measured on the **camera boresight**, i.e. the
fuselage heading — not the ground track. The camera points where the nose points, so
crosswind crab spends the tolerance budget before the grid geometry gets any of it.
- **The closed form:** flying ground track χ, the outbound heading is χ+δ and the return is
  χ−δ (**not** reciprocal — they differ from reciprocal by 2δ). Putting the grid axis exactly
  on the target lands the two directions at **+δ and −δ**, so worst-case error is exactly δ.
  Rotating the axis within the tolerance window to chase a smaller δ **provably never helps**
  (|dδ/dα| ≤ w/V < 1), so α = 0 is always optimal.
- Therefore the tolerance is a **pure feasibility gate on crosswind**: `|δ| ≤ 15°` ⟺ crosswind
  across the science axis ≤ `V·sin(15°)` ≈ **4.66 m/s**. Compute and report in C-2; *enforce*
  in step E.
- Wind-triangle helpers (`wind_correction_angle_deg`, `max_crosswind_for_tolerance_ms`,
  `ground_speed_ms`) belong in `aircraft_math.py` — it already owns aircraft performance and
  is a leaf. `Weather` still needs `wind_direction` / `visibility` getters.
- Fold in the **parallax correction** deferred from C-1 (extend the collection window) and
  `cross_track_strip_offset_m = parallax · sin(crab)`; both are along-track displacements and
  should be solved together.

### D. Fold weather into scoring
Today `planner._score_glint` is the **only** ranking metric. C-2 takes the wind half of this
step (crab is a feasibility gate, not a preference), so D inherits the rest:
- Date/time (A) already varies the sun azimuth feeding glint.
- Add the remaining weather (B) factors: overcast diffuses sunlight so glint matters less;
  wind above `BLACKSWIFT_WIND_RATING_ms` (15 m/s) gates feasibility; low visibility bears on
  VLOS. Extend into a composite metric and/or parallel gates rather than overloading
  `_score_glint`.
- `aircraft_math.route_duration_min` still uses cruise **airspeed** for the whole route. With
  wind modelled it should use per-leg **ground** speed — deliberately left for D because
  changing it shifts every duration and every Tier 2 expectation.

### E. `validator.py` — Part 107 legality/feasibility gating (later in V2)
`validator.py` is empty. Build it to take a `CandidatePlan` and decide legal + feasible
**before** `outputs.py` writes anything. `CandidatePlan` already carries the result
fields: `_is_legal`, `_is_aircraft_feasible`, `_validation_messages`, `_passes_over_m1`.
- Part 107 checks to consider: **≤ 400 ft AGL** — ⚠️ **the current default altitude is
  609.6 m (2000 ft), 5× the Part 107 ceiling.** Whether E gates at 400 ft or at a
  waiver/COA ceiling is an **open decision**, deliberately deferred to step E; until it is
  made, the default plan should not be treated as flyable-as-is. Also: **daylight /
  civil-twilight** operation (use `CurrentSunState.elevation`);
  **VLOS** (the grid spans several km from launch — a genuine concern); **airspace
  authorization** for Monterey Bay; **wind/weather feasibility** (from B + the aircraft's
  wind rating); over-water operations.
- Wiring: `planner` builds a candidate → `validator` gates it → only valid plans reach
  `outputs`. Keep `validator` a leaf; `planner` orchestrates the gate.

## Notes

- Target Python 3.12+ (developed/tested on 3.14.4). `itertools.batched` (used in
  `planner._classify_waypoints`) requires 3.12.
- V1 was a proof-of-engine build (fixed aircraft, clear skies, fixed date/time, assumed
  legal-to-fly, glint-only ranking). V2 replaces those one at a time: **Steps A (date/time),
  B (live NWS weather) and C-1 (along-track mount) are done**; boresight/crab (**C-2**),
  weather-aware ranking (**D**), and legality gating (**E**) remain.
- Many constants still carry `V1_` prefixes but hold V2 values (e.g.
  `V1_DEFAULT_SENSOR_OFF_NADIR_deg` is 30, the V2C angle). The prefix records where the
  constant was introduced, not which version's value it holds — don't infer currency from it.