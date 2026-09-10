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
- **QGroundControl Constants** shall only be modified by the user. Do **not** modify these constants
unless given express permission from the user.

## Project overview

Calypso Monterey Bay flight-planning engine. A sun-aware flight planner for uncrewed
aircraft collecting ocean-color / SST data over Monterey Bay. It builds a lawnmower grid
oriented for minimum sun glint (science legs held **90° off the sun**) and exports the
route as `.kml` and `.png`. See [`README.md`](README.md) for the full description.

**V1 (proof-of-engine) is complete and tested. V2 Steps A (selectable date/time), B
(live NWS weather) and C-1 (along-track payload mount) are complete and tested. C-2 is
HALF BUILT and has been RE-SCOPED — it is no longer a gate. Everything on the V2 roadmap
is SIDELINED behind Step J (JSON output).** See
[Operating constraints](#operating-constraints--2026-09-08-supersedes-earlier-scoping) and
the [V2 roadmap](#v2-roadmap--what-comes-next).

## Operating constraints — 2026-09-08 (SUPERSEDES EARLIER SCOPING)

The engine is no longer a single-mission tool for one aircraft flying one site. It is
becoming a planner other partners run, and that changes the design. **These four items
override anything written before this date.** Where an older section conflicts, this
section wins.

1. **JSON output is the exclusive active priority.** A QGC-compatible `.plan` (JSON)
   writer must exist before *any* other V2 work resumes. Everything else on the roadmap —
   C-2, D, E, and the new configurability work — is **sidelined** until it lands. See
   [Step J](#j-json-plan-output--current-and-exclusive-priority).
2. **The mission must become configurable.** Users set line length, grid width, center
   point, launch point, landing point, desired grid area (honoured when mathematically
   feasible), overlap percentage in **both** the along- and cross-track directions, and
   the camera viewing angle. See [Step F](#f-mission-configurability-sidelined).
   MAVLINK PROTOCOL MUST BE ACCOUNTED FOR (SEE LINK): https://docs.qgroundcontrol.com/master/en/qgc-dev-guide/file_formats/plan.html
3. **The aircraft must become configurable.** Fixed-wing, quadcopter, or hexacopter. For
   a fixed wing every performance constant currently hard-coded to the BlackSwift S2 must
   be user-settable. Multirotor constraints get scoped once the fixed-wing config lands.
   See [Step G](#g-aircraft-configurability-sidelined).
   MAVLINK PROTOCOL MUST BE ACCOUNTED FOR (SEE LINK): https://docs.qgroundcontrol.com/master/en/qgc-dev-guide/file_formats/plan.html
4. **Wind is compensated onboard — the engine must not gate or steer on it.** Assume all
   aircraft carry wind sensing and adjust heading and speed in flight for best
   performance. Therefore:
   - **No plan may be rejected** because of crab angle or any live weather parameter.
   - **The grid never rotates in response to wind.** Orientation is decided by the sun and
     by data quality, full stop.
   - Wind math is still **computed and reported** — into a separate pilot-notes document,
     not into the `.kml` / `.png` / `.json`.
   - Net effect: **V2C is stripped to math + reporting.** Its gating and
     plan-altering functionality is cancelled, not deferred. See
     [C-2 re-scoped](#c-2-boresight--wind-reporting--re-scoped-2026-09-08-sidelined).

**Default launch/land is now UCSC Coastal Science Campus — Terrace Point** (Santa Cruz,
north shore) at **36.94840 N, 122.06538 W**, and stays that way until re-specified. This is
a standing assumption, not a per-mission choice, even though item 2 also makes it
user-settable. **Launch and land are the SAME point** — the two-waypoint (beach launch /
road land) split from V1 collapses.

**Vehicle facts that follow from the constraints** (recorded here because they decide the
takeoff/land commands Step J must emit):
- **BlackSwift S2 — pure fixed wing.** This is the default aircraft and the only one
  currently available. No VTOL, therefore **no transition altitude**.
- **The S3 was the tri-motor VTOL, and the only airframe was destroyed in company
  testing.** The VTOL vehicle class is real but has no instance today.
- **Custom partner vehicles are essentially always rotorcraft**, flashed with PX4 and
  driven from QGC.
- **No vehicle is ever hand-launched.** Every launch is from land or a **stationary boat**.
  A boat launch near M1 is operationally significant — see the transit note in Step J.

> ## ⚠️ READ THIS BEFORE TRUSTING A GENERATED PLAN
>
> A generated plan is a **planning sketch for review**, never a flyable mission. Three
> separate reasons, in order of size:
>
> **1. The distance budget ignores the transit legs.** `metrics["total_route_distance_m"]`
> is `geo._route_distance_m(route_points)` over **grid points only**; launch and land are
> prepended/appended afterwards in `planner._classify_waypoints`, and
> `route_duration_min` is handed the grid-only number. Measured on the current default
> mission: grid 82,320 m + transit 29,867 m = **112,187 m actually flown → 106.2 min
> against a 90 min endurance.** The summary prints **+11.4 min of margin on a flight that
> is 16.2 min over the battery.** This is arithmetic, not weather — onboard wind
> compensation does not touch it. Fixing it is a prerequisite for any honest budget.
>
> **2. The launch point in `constants.py` is stale.** `V1_LAUNCH_POINT_*` /
> `V1_LAND_POINT_*` still hold **36.637, −121.936** (south shore, 14,615 m from M1) while
> the waypoint *names* say `Seymour-Beach-Launch` / `Seymour-Road-Land`. The real site is
> **Terrace Point, 36.94840 N / 122.06538 W** (north shore), a single pad serving as both
> launch and land, and it measures **22,386 m from M1 — 53% further**. Round-trip transit
> becomes **44.8 km ≈ 41.5 min of a 90 min battery.** Combined with defect 1, an honest
> budget from Terrace Point supports **N=9 lines, not the 15 the engine emits**
> (N=9 → 77,296 m / 72.9 min; N=15 → 127,559 m / 120.4 min).
>
> **3. Nothing validates anything.** `validator.py` holds a docstring and no code. Note
> that under the 2026-09-08 constraints this is *no longer* about wind: the RTH/crosswind
> gate C-2 was scoping is **cancelled**. What survives as a genuine open question is
> whether **battery/endurance feasibility** stays a gate or also becomes a report — see
> [Step E](#e-validatorpy--legalityfeasibility-gating-sidelined-and-narrowed).
>
> The one V2C-2 change that IS live is the parallax line extension in
> `geo.make_lawnmower_grid_through_m1` — it lengthens every line by 808 m, which is why
> grid distance is 82,320 m against an 82,620 m budget.

## Layout

- `flight_plan_maker.py` — terminal entry point (run this). CLI flags: `--name`, `--out-dir`, `--date`, `--time`.
- `src/` — engine modules:
  - `constants.py` — engine constants (aircraft, M1, sensor, date/time defaults + timezone, weather, actions).
  - `objects.py` — core classes (Aircraft, Sensor, Weather, CurrentSunState,
    Waypoint, MissionRequest, CandidatePlan).
  - `sun.py` — local→UTC datetime resolver (`resolve_mission_datetime`, `mission_datetime`) + pysolar sun azimuth/elevation (`create_sun_state`).
  - `aircraft_math.py` — endurance → distance budget, duration, battery margin, plus the
    V2C wind triangle (**reporting only** as of 2026-09-08 — see constraint 4).
  - `geo.py` — geodesic math + M1-centered lawnmower grid geometry (the M1-centering
    becomes a *default* rather than an invariant under Step F).
  - `weather.py` — **leaf**: live NWS weather for a lat/lon/datetime → populated `Weather`, or `None` (planner falls back to the stub).
  - `planner.py` — the hub: assembles objects, scores glint, builds the plan.
  - `outputs.py` — KML + PNG writers. **Step J adds the QGC `.plan` (JSON) writer here**,
    and a separate pilot-notes document is where wind/crab reporting goes (constraint 4).
  - `validator.py` — **docstring only, no code.** Its docstring still describes the
    **cancelled** C-2 RTH/crosswind gate; read it as history, not as a spec. What
    validation survives is narrowed and sidelined — see Step E.
- `tests/` — tiered pytest harness (`test_0_*` … `test_6_*`, **seven** tiers, 66 tests); see [Setup & run](#setup--run).
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
  not validate correctness. (Its docstring anticipates moving *behind* validation so it
  only renders approved plans; whether that ever happens now depends on the open
  battery-feasibility decision in Step E.)
- **Compute vs. permit are separate jobs** (constraint 4 sharpens this). A module may
  calculate any number honestly — crab, ground speed, return time — without that number
  being allowed to veto or steer a plan. Wind math *reports*; it does not decide.
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
  `visibility`) fall to `DEFAULT_*`. Offline tests monkeypatch the fetch (`tests/test_3_weather.py`).

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
  **352 m** offset between nadir and the boresight ground point. The parallax **line
  extension** in `make_lawnmower_grid_through_m1` is live (+808 m/line); the crab-shear half
  of that correction is cancelled with the rest of C-2's plan-altering work.
  ⚠️ Step F makes off-nadir angle user-settable, so none of these numbers stay constant.
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
- **Known defects and deferred items:**
  - 🔴 **The budget and the reported duration exclude the transit legs.** See reason 1 in
    the warning box above. Grid-only 82,320 m is what gets budgeted and printed; the flown
    route is 112,187 m (106.2 min vs. 90 min endurance). Every duration, margin, and
    grid-size number the engine has ever produced is optimistic by the transit. This is the
    largest known defect in the engine and it is **not** weather-related. **Fix is scheduled
    into Step J-4** — after it, the default mission is N=9 / 77,296 m / 72.9 min / 17.1 min
    margin from Terrace Point.
  - 🔴 **Launch/land constants are stale.** `V1_LAUNCH_POINT_*` / `V1_LAND_POINT_*` point at
    the south shore while their waypoint names say Seymour. The standing default is Terrace
    Point (36.94840 N, 122.06538 W), **one pad for both launch and land**, 22,386 m from M1
    — 53% further than the constants encode.
  - **Grid sizing is budget-derived, not requested.** `geo._initial_total_lines_from_budget`
    picks N from the endurance budget. `V1_DEFAULT_GRID_WIDTH_km`,
    `V1_DEFAULT_LINE_LENGTH_km` and `V1_DEFAULT_LINE_SPACING_km` are declared but never
    read. They were removal candidates; under **Step F they are reinstated** as the defaults
    behind user-settable dimensions. Do not delete them.
  - **Along-track overlap does not exist yet.** Only cross-track overlap
    (`V1_DEFAULT_OVERLAP_PCT`) is modelled, and it drives line spacing. Step F adds an
    along-track overlap, which is a different quantity: it governs image **trigger spacing**
    along a line, something the engine does not currently compute at all
    (`ground_footprint_along_m` exists and is reporting-only).
  - **Parallax is reported, and only half-corrected.** The line extension is live; the
    crab-shear term is cancelled per constraint 4.

## V2 roadmap — what comes next

**Execution order as of 2026-09-08: `J` → `F` → `G` → `C-2 (re-scoped)` → `D` → `E`.**
Nothing but **J** is active. Letters record the order steps were *scoped*, not the order
they are *built* — the same convention the `V1_` constant prefixes follow.

The original through-line was "make the mission situation-aware, fold that into ranking,
then gate for legality." Constraint 4 retires the gating half of that: the aircraft
compensates for wind in flight, so the engine's job is to **describe** conditions
accurately, not to veto or re-steer on them. The new through-line is **make the engine
configurable and its output machine-usable, and report honestly.** Preserve dumb
unidirectionality throughout.

### J. JSON `.plan` output — CURRENT AND EXCLUSIVE PRIORITY
A `.plan` (JSON) writer, so a plan can be uploaded and flown instead of merely looked at.
`constants.EXTENSION_JSON` already exists and `outputs.write_kml`'s docstring already names
the intended helper (`write_qgc_plan`). Today's KML is **visualization only** in QGC — it
does not import as a flyable mission — which is the entire reason this jumped the queue.
**No other roadmap step may start until this ships.**

**Scoping settled 2026-09-08:**
- **Two consumers.** QGroundControl driving **PX4** (custom rotorcraft), and BlackSwift's
  **FMS** taking BlackSwift vehicles as-is. Whether literal fields (`firmwareType`,
  `vehicleType`) matter to the FMS is unconfirmed — cross that bridge if reached.
- **Plain waypoint list (`SimpleItem`), never a survey/`ComplexItem`.** A survey block
  lets the GCS regenerate the lawnmower from its own parameters, which would **discard the
  sun-oriented geometry this engine exists to compute**. The waypoint list preserves
  exactly what was planned. This is the single most important format decision in J.
- **Camera control is automated into the file** — reduce RPIC workload. Use
  **distance-based triggering**, not time-based. Beyond the usual reason, distance
  triggering is **wind-immune**: ground spacing holds no matter what wind does to ground
  speed, so the along-track overlap survives conditions the engine deliberately no longer
  models (constraint 4). Time-based triggering would silently stretch and compress the
  overlap leg by leg.
- **Home position** = the Terrace Point launch/land coordinate.

**The structural fact of J — waypoints expand 1→N.** Camera control is a *separate mission
item*, not an attribute of a waypoint, so one `Waypoint` can emit two items. Consequences:
- `doJumpId` must be assigned **while building the item list**, never taken from
  `Waypoint.waypoint_ID`. The existing `WP001` / `WP000` / `WP_END` scheme is for humans
  and KML and will not line up with item indices.
- Item count is roughly `5N + 2N + 2` (nav points, camera toggles, takeoff/land).

| waypoint action | items emitted |
|---|---|
| `launch` | takeoff item for the vehicle class |
| `turn`, `transit`, `line_label`, `m1_overflight` | nav waypoint |
| `collect_start` | nav waypoint **+** set trigger distance = *d* |
| `collect_stop` | nav waypoint **+** set trigger distance = 0 |
| `land` | land item for the vehicle class |

**Build once, serialize per dialect.** `_plan_items(plan)` produces a vehicle-neutral item
list — the engine's truth — and `_serialize_qgc(items, plan)` renders it. A future
`_serialize_blackswift(...)` is then a sibling, not a rewrite. This split is what keeps the
two-consumer requirement from becoming a fork.

**Two slices of later steps are pulled forward, because J cannot emit a correct file
without them:**
- *From G:* `Aircraft` must declare its **vehicle class** — pure fixed wing / multirotor /
  VTOL fixed wing — because the takeoff and land commands differ. Same move `Sensor.mounting`
  already makes: record the assumption as data on the object instead of burying it in a
  formula. Note that **neither class in use today needs a transition altitude** (the S2 is a
  pure fixed wing; custom vehicles are pure rotorcraft). `VTOL_TRANSITION_ALTITUDE_m = 50`
  is provisional, applies to the VTOL class only, and that class currently has no instance.
- *From F:* an **along-track overlap** on `Sensor`, because distance triggering needs a
  spacing. `geo.ground_footprint_along_m` already computes the input (**561.5 m** at current
  geometry) and is otherwise unused. Cross-track overlap stays at 50%; along-track default
  stays as-is for now. Spacing = footprint × (1 − overlap): **280.7 m at 50%** = one frame
  every 15.6 s at cruise.

**Where the numbers come from — follow the existing metrics path.** `geo` already computes
`sensor_parallax_m` and `cross_track_swath_m` during grid assembly and they ride the metrics
dict into `set_grid_metrics`. Along-track footprint and trigger distance go the same way. No
new plumbing, and `outputs` stays a black box rendering what the plan carries — a third
sibling to `write_kml` / `write_png`, not a new decision layer.

**✅ THE TRANSIT FIX IS IN SCOPE FOR J** (decided 2026-09-08). A `.plan` is
machine-consumed — unlike a KML that a human eyeballs, this file gets uploaded and flown —
so the engine may not ship its first flyable artifact on a budget that omits a third of the
flight.

Measured from Terrace Point: **22,386 m to M1**, bearing 169.6°, round-trip transit
**44.8 km ≈ 41.5 min of a 90 min battery**, barely varying with grid size (45,239 m at N=15
vs. 44,800 m at N=3) because M1 dominates. Today's engine emits **N=15 = 127,559 m =
120.4 min**, thirty minutes past the battery. After the fix:

```
usable (15% reserve)      82,620 m
seed transit 2·d(L,M1)    44,773 m   ->  grid budget 37,847 m
geo picks                 N=9, grid 32,343 m
true transit (entry 21,952 + exit 23,001)  44,953 m   [seed error +180 m, +0.40%]
TOTAL FLIGHT              77,296 m  |  72.9 min  |  margin 17.1 min   FITS
```

- **The seed is accurate to 0.40%, so one pass suffices** — no fixed-point loop. Seed with
  `2 × distance(launch, M1)`, size the grid, recompute the exact transit from the real
  entry/exit corners, verify it still fits. Keep a shrink fallback for the case where it
  does not.
- **⚠️ The subtraction MUST happen in `planner`, not `geo`.** `make_lawnmower_grid_through_m1`
  receives the M1 center, an orientation and a distance — **it does not know where launch
  is, and must not learn.** Passing launch/land into `geo` would be the naive fix and it
  breaks unidirectionality. `planner` knows both the mission request and `geo`, so `planner`
  computes the transit, hands `geo` the reduced budget, and `geo` stays a leaf.
- **Two distances, two names.** `metrics["total_route_distance_m"]` has always been the
  **grid** figure despite its name — that mismatch is the whole defect. Split it the way
  `geo` already splits `line_length_m` (science coverage) from `physical_line_length_m`
  (what gets flown): a grid-route figure from `geo`, and a total-flight figure computed by
  `planner` over the classified route once launch and land are in it. Duration consumes the
  total. Blast radius is small and known: `geo.py:371–376`, `planner.py:527`,
  `objects.py:600/656/782`, `tests/test_4_grid_assembly.py:65`.
- **This shifts every Tier 2 duration expectation.** Deliberate, one-time.
- **"or a stationary boat" is the escape hatch.** A launch point near M1 collapses the
  45 km transit and hands nearly the whole battery to science. That reframes Step F from
  partner convenience to the thing that makes this mission efficient.

**✅ LAUNCH AND RECOVERY — SETTLED, AND SIMPLER THAN FEARED** (decided 2026-09-08).
The S2 **launches from a stand** and **lands on its belly at a very low stall speed with
steep descent capability**, which is precisely why Terrace Point works as a single pad. So:
- **`geo` needs no approach geometry.** J-5 emits a plain land item at the pad coordinate.
  No landing pattern, no loiter-to-alt, no new geometry anywhere.
- **The approach direction is a RECOMMENDATION to the RPIC**, derived from the wind math and
  delivered in the pilot-notes PDF — never baked into the `.plan`. This is constraint 4
  applied to landing: the engine computes and advises, the pilot decides. **The RPIC can
  always take manual control of the landing, as with any QGC plan.**
- **⚠️ Know that the `.plan` still encodes an approach direction implicitly.** The aircraft
  arrives on the bearing from the last grid waypoint to the pad — measured at **344.6°** and
  effectively fixed, since it is the M1→Terrace Point transit reciprocal. That is a *fact of
  the geometry*, not a wind decision, and the RPIC must be told it. It gives the pilot-notes
  document its **first genuinely operational customer**: compare the plan's implicit 344.6°
  approach against the into-wind heading and state the headwind/crosswind/tailwind component
  the pilot will meet, so they know before launch whether they intend to take over. A
  belly-landing airframe on a tailwind approach is exactly the case worth warning about.
- The **launch item's altitude** is a climb-out altitude, not the 609.6 m mission altitude
  the launch waypoint carries today. Set it in J-1.

**Step table:**

| Step | File | Work | State |
|---|---|---|---|
| J-0 | — | Pin schema against the user's field list; confirm takeoff/land commands per vehicle class | ❌ |
| J-1 | `constants.py` | Terrace Point coords (launch = land); along-track overlap; launch climb-out altitude; `VTOL_TRANSITION_ALTITUDE_m = 50` (provisional, no instance); vehicle-class + command constants; schema literals | ❌ |
| J-2 | `objects.py` | `Aircraft` vehicle class; `Sensor` along-track overlap; `CandidatePlan` trigger-distance + total-flight-distance fields | ❌ |
| J-3 | `geo.py` | Along-track spacing into the metrics dict; rename the grid figure so it stops claiming to be the whole route | ❌ |
| J-4 | `planner.py` | Thread the new sensor fields; **subtract the transit seed before calling `geo`**; recompute exact transit and set total flight distance; duration from the total | ❌ |
| J-5 | `outputs.py` | `_plan_items` → `_serialize_qgc` → `write_qgc_plan`; plain land item at the pad | ❌ |
| J-6 | `flight_plan_maker.py` | Emit and report the `.plan` path | ❌ |
| J-7 | `tests/test_6_outputs.py` | Item ordering, camera toggles paired, monotonic `doJumpId`, home position; **Tier 2 duration expectations rebased** | ❌ |
| J-8 | docs | Closeout | ❌ |

**No open decisions remain for J.** Both were settled 2026-09-08: the transit fix is in
scope, and launch/recovery needs no approach geometry. J-0 (pinning the schema against the
user's field list) is the only thing standing between here and J-1.

**Follows J, lower priority:** the **PDF pilot-notes document** from constraint 4 — the
wind / crab / return-time reporting, deliberately kept out of the machine-readable outputs.
Its first operational customer is already known: the **recommended landing approach**,
comparing the plan's implicit 344.6° arrival against the into-wind heading. That is also the
first time any of C-2's wind math will have done real work for anybody.

### F. Mission configurability (SIDELINED)
Per constraint 2, the user sets: line length, grid width, center point, launch point,
landing point, desired grid area (honoured **when mathematically feasible**, otherwise
reported as infeasible with the closest achievable), cross-track overlap %, along-track
overlap %, and camera off-nadir viewing angle.
- **This dissolves three current invariants.** The grid is no longer necessarily
  M1-centered; the M1 overflight is no longer necessarily required; and grid size is no
  longer necessarily derived from the endurance budget. `geo.make_lawnmower_grid_through_m1`,
  `_initial_total_lines_from_budget`, and the odd-N parity rule all assume otherwise. The
  odd-N rule exists to put the center line through M1 — with a configurable center it
  generalises to "center-point overflight" and should stay, but as a *default*.
- **Requested-vs-derived sizing is a real design fork.** Today N falls out of the budget.
  With a requested area/length/width, the budget becomes a **feasibility check** on a
  requested grid rather than the source of its dimensions. Both modes need to coexist
  ("fill my endurance" vs. "cover this box").
- The three unread constants (`V1_DEFAULT_GRID_WIDTH_km`, `V1_DEFAULT_LINE_LENGTH_km`,
  `V1_DEFAULT_LINE_SPACING_km`) become the defaults behind these inputs.
- Along-track overlap is **new physics for this engine**: cross-track overlap sets line
  spacing, along-track overlap sets image trigger spacing along a line
  (`ground_footprint_along_m` is the input, and it is currently reporting-only).
- Delivery mechanism (CLI flags vs. a mission config file) is undecided. The flag list is
  already at four and this adds ~9 more, which argues for a config file.

### G. Aircraft configurability (SIDELINED)
Per constraint 3. Fixed-wing, quadcopter, or hexacopter, with every fixed-wing performance
constant user-settable rather than hard-coded to the BlackSwift S2.
- `objects.Aircraft` is already a general constructor — the hard-coding lives in
  `planner._Black_Swift`, a module-level singleton built from `BLACKSWIFT_*` constants.
  That singleton is what has to go.
- **Step J pulls the vehicle *class* forward** (pure fixed wing / multirotor / VTOL fixed
  wing), because takeoff and land commands differ per class. G inherits the rest: the
  performance numbers.
- Multirotor is **not** just different numbers. `aircraft_math` assumes forward flight
  (cruise speed, turn penalty, turn radius); a multirotor hovers, turns in place, and has a
  materially different endurance-vs-speed curve. `geo`'s turn geometry and
  `route_duration_min`'s turn-penalty model both need a multirotor branch. Scope after the
  fixed-wing config lands, per the user.
- **Climb and descent are unmodeled.** `Aircraft` carries climb 3.35 m/s and descent
  1.80 m/s and `route_duration_min` uses neither — the whole route is flown at cruise with
  zero vertical time. A full-altitude vertical profile at 609.6 m would be ~3 min up and
  ~5.6 min down; the real fixed-wing profile climbs in forward flight so it is less, but it
  is not zero, and today it is counted as zero.
- **Vehicle facts:** the S2 is a **pure fixed wing** (no VTOL, no transition altitude); the
  tri-motor VTOL **S3 is not an option**, its only airframe having been destroyed in company
  testing; custom partner vehicles are essentially always **rotorcraft** on PX4/QGC. Nothing
  is ever hand-launched.

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
- Tests: `tests/test_3_weather.py` (offline; fetch monkeypatched) + a Tier 4 check that the
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

### C-2. Boresight + wind REPORTING ⏳ RE-SCOPED 2026-09-08 (SIDELINED)

> **What changed.** C-2 was scoped as *boresight referencing + an RTH safety gate*.
> Constraint 4 cancels the gate. Onboard wind sensing plus in-flight compensation is now
> assumed on every aircraft, so the engine must **never** reject a plan or rotate a grid
> because of wind. C-2 is reduced to **math + reporting**, and what it reports goes into a
> **separate pilot-notes document**, not into the `.kml` / `.png` / `.json`.
>
> This is a cancellation, not a deferral. Do not resurrect `_rth_safe_budget`,
> `_evaluate_boresight` as a gate, or the wind-derived reserve loop.

**Step status — steps 1–4 built, and now that is most of what C-2 needs.**

| Step | What | State |
|---|---|---|
| 1 | `constants.py` — six RTH constants; `V1_EMERGENCY_RESERVE_FRACTION` retired to a seed | ✅ done (several now unused — see below) |
| 2 | `objects.py` / `weather.py` — `wind_direction`/`visibility` getters, `wind_is_measured`, `stale_fields`, C-2 plan setters | ✅ done |
| 3 | `aircraft_math.py` — wind triangle, `return_time_min`, derived reserve | ✅ done + tested |
| 3.5 | `weather.py` — `_value_at_time` honours interval duration; per-field staleness | ✅ done + tested |
| 4 | `geo.py` — parallax line extension, `furthest_point_distance_m` | ✅ done |
| ~~5~~ | ~~`planner._rth_safe_budget`, `_evaluate_boresight`, budget wiring~~ | ❌ **CANCELLED — plan-altering** |
| ~~6~~ | ~~`validator.py` RTH / crosswind gate~~ | ❌ **CANCELLED — gating** |
| **5′** | **pilot-notes document: crab, boresight error, ground speeds, worst-case return, crosswind headroom** | ❌ not started |
| 6′ | `planner` calls the wind math for **reporting only** and populates the C-2 setters | ❌ not started |
| 7 | Tier 4+ tests that the reported numbers reach the notes document | ❌ not started |
| 8 | docs | ⏳ this section |

**What is LIVE vs INERT.** Step 4's parallax extension is inside
`make_lawnmower_grid_through_m1`, so it changes every plan today (+808 m per line; grid
distance 82,320 m). **Everything else built in C-2 has zero callers**:
`wind_correction_angle_deg`, `ground_speed_ms`, `effective_lawnmower_speed_ms`,
`return_time_min`, `required_reserve_time_min`, `wind_aware_usable_distance_m`,
`max_crosswind_tolerance_ms`, `cross_wind_component_ms`, `head_wind_component_ms`,
`furthest_point_distance_m`. `Weather.wind_is_measured` and `.stale_fields` are populated
and read by nobody. `route_duration_min` accepts `weather`/`axis_deg` but `planner` calls
it with three arguments, so duration is still-air.

**None of that math is wasted — its destination changed.** It was built to *decide*; it
now exists to *inform the RPIC*. The functions themselves are correct and stay. What dies
is the branch that would have shrunk a grid or refused a plan.

**Constants left stranded by the re-scope.** `RTH_SAFETY_FACTOR`, `RTH_TERMINAL_ALLOWANCE_min`,
`MANUAL_RTH_MAX_CROSSWIND_ms`, `RTH_INCLUDES_GLIDE`, `RTH_SEED_RESERVE_FRACTION` and
`RTH_MAX_ITERATIONS` were sized for the cancelled gate. `RTH_SEED_RESERVE_FRACTION` is
still read (it is the reserve the budget uses); the rest are now reporting inputs at best.
Decide their fate when C-2 resumes — **do not delete them before then**, the reasoning
behind each is recorded in `constants.py` and in the 2026-08-19 log entry.

**The boresight geometry still holds and is still worth reporting.** The 90° ± 15 is
measured on the camera **boresight** — the fuselage heading, not the ground track — so
crab moves the imaged geometry even though it no longer moves the plan.
- **The closed form:** flying ground track χ, the outbound heading is χ+δ and the return is
  χ−δ (**not** reciprocal — they differ from reciprocal by 2δ). Putting the grid axis exactly
  on the target lands the two directions at **+δ and −δ**, so worst-case error is exactly δ.
  Rotating the axis to chase a smaller δ **provably never helps** (|dδ/dα| ≤ w/V < 1), so
  α = 0 is always optimal. Under constraint 4 this stops being an argument for *not
  rotating* and becomes simply the *reported* error.
- `|δ| ≤ 15°` ⟺ crosswind across the science axis ≤ `V·sin(15°)` ≈ **4.66 m/s** at S2
  cruise. Report it as **science-quality headroom** for the RPIC, never as a gate.
- `cross_track_strip_offset_m = parallax · sin(crab)` — report, do not correct.

### D. Fold weather into scoring (SIDELINED, NARROWED)
`planner._score_glint` is still the **only** ranking metric. Constraint 4 removes wind from
this step entirely — wind is neither a preference nor a gate — so D narrows to
**sun-and-data-quality** factors:
- Date/time (A) already varies the sun azimuth feeding glint.
- Cloud cover is the surviving weather input: overcast diffuses sunlight, so glint matters
  less. That is a genuine data-quality signal and belongs in ranking.
- **Removed from D:** the wind-rating feasibility gate and any wind term in ranking.
  Visibility/VLOS moves to E (legality), where it always belonged.
- `aircraft_math.route_duration_min` still uses cruise **airspeed** for the whole route.
  Wind-aware duration is now a **reporting** improvement, not a planning one — the wind
  path in that function already exists and is unused.

### E. `validator.py` — legality/feasibility gating (SIDELINED AND NARROWED)
`validator.py` holds only a docstring, and that docstring describes the **cancelled** RTH
gate — read it as history. What remains for E:
- **Legality** — Part 107 and friends: **altitude ceiling** (the default is 609.6 m /
  2000 ft; COA authorization is in progress with partners and may go **higher**, so gate on
  the ceiling the mission is *authorized* for, never a hard-coded 400 ft);
  **daylight / civil twilight** (use `CurrentSunState.elevation`); **VLOS**; **airspace
  authorization**; **over-water operations**.
- **⚠️ OPEN DECISION — does battery/endurance feasibility stay a gate?** Constraint 4
  removes *weather-driven* gating, and the user's stated priority is that "legality and
  safety are still our priority." A route longer than the battery is not a weather problem
  and no onboard sensor fixes it (see warning reason 1). Until this is decided, treat
  endurance feasibility as **unresolved**, not as cancelled.
- Wiring, if E stays a gate: `planner` builds a candidate → `validator` gates it → only
  valid plans reach `outputs`. Keep `validator` a leaf. `CandidatePlan` already carries
  `_is_legal`, `_is_aircraft_feasible`, `_validation_messages`, `_passes_over_m1`.
- The **re-derive rule** in the existing docstring survives any re-scope: a validator that
  reads back what the planner stored is checking the builder's arithmetic against itself.

## Notes

- Target Python 3.12+ (developed/tested on 3.14.4). `itertools.batched` (used in
  `planner._classify_waypoints`) requires 3.12.
- V1 was a proof-of-engine build (fixed aircraft, clear skies, fixed date/time, assumed
  legal-to-fly, glint-only ranking). V2 replaces those one at a time: **Steps A (date/time),
  B (live NWS weather) and C-1 (along-track mount) are done**. Remaining, in execution
  order: **J** (JSON output — active), **F** (mission configurability), **G** (aircraft
  configurability), **C-2 re-scoped** (wind reporting), **D** (sun/cloud ranking), **E**
  (legality).
- Many constants still carry `V1_` prefixes but hold V2 values (e.g.
  `V1_DEFAULT_SENSOR_OFF_NADIR_deg` is 30, the V2C angle). The prefix records where the
  constant was introduced, not which version's value it holds — don't infer currency from it.
  **Roadmap letters work the same way** — they record scoping order, not build order.
- **When a doc and a measurement disagree, measure.** Several numbers in these docs
  (route distance, margin, N) were verified by instrumenting the engine on 2026-09-08, and
  one long-standing claim — that `total_route_distance_m` is the route — turned out to be
  false. Re-measure before trusting a figure that predates a geometry change.