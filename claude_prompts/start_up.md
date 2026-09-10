# Getting started 

## Goals

This repository will be used to design code for Calypso Monterey Bay flight plans.

## Prompts

> **Note (2026-08-13):** both bootstrap prompts below are already complete — `CLAUDE.md`
> and the base Python-repo files exist. A fresh session should **not** re-run them; read
> `CLAUDE.md` and `README.md` for current project context instead.

1. Read this file.  Execute the 1st task under "Claude/CLAUDE.md file"
2. Read this file.  Execute the 1st task under "Basic start up"

## Claude

### CLAUDE.md file  ✅ DONE

1. Please generate a basic CLAUDE.md file for this project.  Have it indicate:

    - I will perform git commands

> **Done** — `CLAUDE.md` exists and is actively maintained (V1 + V2 A/B). Do not regenerate it.

### Skills

### Settings

## Basic start up  ✅ DONE

1. Generate the basic files that one needs for a Python GitHub repository, e.g. a file for dependencies.  Examine the other Repositories in Oceanography/python to see how I tend to organize things.

> **Done** — `requirements.txt`, `requirements-dev.txt`, `README.md`, `conftest.py`,
> `pytest.ini`, `pyrightconfig.json`, and the `src/` + `tests/` layout all exist. Do not regenerate them.

### Report

## Logging

The "Logs" section will record Claude's work.  Please use the following format:

### <Date> (Short summary of the work)

<Detailed description of the work and what you learned>

### <Date> (Short summary of the work)

<Detailed description of the work and what you learned>

...

## Logs

### 2026-09-08 (Operational-constraints pivot — JSON first, configurability, wind demoted to reporting)

Returned to the project after the V2C-2 pause. Audited the whole codebase against the
handoff notes, then took a scope change from the user that redirects the roadmap. **No code
changed today — documentation only.**

**The audit confirmed every number in the 2026-08-19 handoff** (66 tests green; N=15;
grid 82,320 m vs. 82,620 m budget; furthest point 17,323 m vs. 14,580 m reserve; parallax
352 m; 4.659 m/s crosswind headroom at 15°). It also found the derived-reserve fixed point
converges in two passes to 22.62 min, costing N=15 → 13 — cheaper than the notes implied.

**It also found something the docs had never recorded, and it is bigger than the RTH gap.**
`metrics["total_route_distance_m"]` is measured over **grid points only**. Launch and land
are prepended/appended afterwards in `_classify_waypoints`, and `route_duration_min` is
handed the grid-only figure. So the budget, the duration, and the margin have *all* been
excluding the transit legs since V1: 82,320 m of grid + 29,867 m of transit = 112,187 m
flown, 106.2 min against a 90 min endurance. The engine prints **+11.4 min of margin on a
flight 16.2 min over the battery**. It survived this long because it is not a wrong formula
— every function is correct — it is a wrong *argument*, which is the same interface-level
failure mode the C-2 audits kept turning up. It went unnoticed because M1 sits 14.8 km
offshore; on a mission centered near the launch site the transit would have been noise.

**The scope change.** Four items, in the user's stated priority order:

1. **JSON output is now the exclusive priority** — a QGC-uploadable `.plan`. Everything
   else on the V2 roadmap, C-2 included, is sidelined until it exists. The KML has always
   been visualization-only in QGC, so today the engine cannot produce anything flyable.
2. **The mission must become configurable** — line length, grid width, center point, launch
   and land points, requested grid area, along- *and* cross-track overlap, camera angle.
   This dissolves three standing invariants (M1-centered, M1-overflight-required,
   size-derived-from-budget) and introduces a genuinely new quantity: along-track overlap
   governs image *trigger spacing*, which this engine has never computed.
3. **The aircraft must become configurable** — fixed wing with every constant settable,
   plus quad/hexacopter. Multirotor is not just different numbers: `aircraft_math` assumes
   forward flight throughout.
4. **Wind is compensated onboard.** Assume every aircraft senses wind and adjusts heading
   and speed in flight. The engine must therefore never reject a plan or rotate a grid on
   wind — compute and report only, into a separate pilot-notes document.

**Consequence: C-2's gate is cancelled, not deferred.** Steps 5 and 6 as scoped
(`_rth_safe_budget`, `_evaluate_boresight`-as-gate, the validator RTH/crosswind checks)
are dead. The math built in steps 1–4 is *not* wasted — it keeps its correctness and loses
its authority. It was built to decide; it now exists to inform the RPIC. The lesson worth
keeping is that **compute and permit are separable**, which `aircraft_math`'s own docstring
had already argued before the constraint arrived.

**Also settled today.** Default launch/land moves to **UCSC Coastal Science Campus,
Terrace Point** — **36.94840 N, 122.06538 W**, one pad serving as both launch and land, which
collapses V1's beach-launch / road-landing split. Measured: **22,386 m to M1** on bearing
169.6°, versus 14,615 m for the stale constants — 53% further. Round-trip transit is
**44.8 km ≈ 41.5 min of a 90 min battery**, and it barely moves with grid size (45,239 m at
N=15 vs. 44,800 m at N=3) because M1 dominates. Combined with defect #1, the honest ceiling
from Terrace Point is **N=9** (77,296 m, 72.9 min); the engine emits N=15, which is 120.4 min
— thirty minutes past the battery. Altitude stays 2000 ft (COA in progress, possibly higher
later); endurance stays 90 min. No science-set minimum coverage — legality and safety still
outrank grid size.

**Step J scoped the same day.** Two consumers: QGC/PX4 for custom rotorcraft, BlackSwift's
FMS for BlackSwift vehicles as-is. Decisions worth not re-litigating:

- **Plain waypoint list, never a survey item.** A survey block lets the GCS regenerate the
  lawnmower from its own parameters, which would discard the sun-oriented geometry that is
  the entire point of this engine. This is the most important format decision in J.
- **Camera automated via distance-based triggering.** Chosen partly to cut RPIC workload and
  partly because distance triggering is *wind-immune*: ground spacing holds no matter what
  wind does to ground speed, so the along-track overlap survives conditions the engine
  deliberately stopped modelling under constraint 4. Time-based triggering would silently
  stretch and compress overlap leg by leg.
- **Build once, serialize per dialect** — a vehicle-neutral item list, then a QGC renderer,
  with a BlackSwift renderer as a later sibling rather than a fork.
- **Waypoints expand 1→N.** Camera control is a separate mission item, not a waypoint
  attribute, so `collect_start`/`collect_stop` each emit two items. `doJumpId` must therefore
  be assigned while building items — the existing `WP001`/`WP000`/`WP_END` scheme will not
  line up. This is the structural fact of J and the easiest thing to get wrong.
- **Two slices of later steps come forward** because J cannot emit a correct file without
  them: vehicle *class* from G (takeoff/land commands differ), and along-track overlap from F
  (distance triggering needs a spacing). `geo.ground_footprint_along_m` already computes the
  input — 561.5 m — and had no callers; at 50% overlap that is a frame every 280.7 m / 15.6 s.
- Trigger distance follows the **existing metrics path** (`sensor_parallax_m` and
  `cross_track_swath_m` already ride the metrics dict into `set_grid_metrics`), so `outputs`
  stays a black box and no new plumbing is invented.

**Vehicle facts corrected during scoping:** the **S2 is a pure fixed wing** — no VTOL, no
transition altitude. The tri-motor VTOL was the S3, destroyed. Custom partner vehicles are
essentially always rotorcraft. `VTOL_TRANSITION_ALTITUDE_m = 50` is defined provisionally for
a vehicle class that currently has no instance. **Nothing is ever hand-launched** — every
launch is from land or a **stationary boat**, and that last clause is the most operationally
valuable sentence in the whole scoping: a launch point near M1 collapses the 45 km transit
and hands nearly the entire battery to science, which reframes Step F from partner
convenience into the thing that makes this mission efficient.

**Both open questions closed the same day.**

*The transit fix is in scope for J.* Rationale accepted: a `.plan` is machine-consumed while
a KML is only eyeballed, so the engine's first flyable artifact may not ship on a budget
that omits a third of the flight. The mechanics turned out to be easy — seeding the transit
with `2 × distance(launch, M1)` is accurate to **0.40%** (44,773 m seed vs. 44,953 m actual),
so one pass suffices and no fixed-point loop is needed. Result: **N=9, grid 32,343 m, total
77,296 m, 72.9 min, 17.1 min margin.**

The design constraint worth remembering is *where* the subtraction goes.
`make_lawnmower_grid_through_m1` takes the M1 center, an orientation and a distance — **it
does not know where launch is, and must not learn.** The naive fix is to pass launch/land
into `geo`, which breaks unidirectionality. `planner` knows both the mission request and
`geo`, so `planner` subtracts and hands `geo` a reduced budget. The defect also gets a naming
fix: `total_route_distance_m` has always been the *grid* figure despite its name, and that
mismatch **is** the bug. Split it the way `geo` already splits `line_length_m` (science
coverage) from `physical_line_length_m` (flown) — the precedent was already in the file.

*Launch and recovery need no approach geometry.* The S2 launches from a stand and belly-lands
at a very low stall speed with steep descent capability, which is exactly why Terrace Point
works as a single pad. J-5 emits a plain land item; nothing new goes into `geo`. The approach
**direction** becomes a recommendation to the RPIC from the wind math, delivered in the
pilot-notes PDF, never baked into the `.plan` — constraint 4 applied to landing. The pilot
retains manual takeover as with any QGC plan.

One consequence to carry forward: **the `.plan` still encodes an approach direction
implicitly.** The aircraft arrives on the bearing from the last grid waypoint to the pad,
measured at **344.6°** and effectively fixed, being the M1→Terrace Point transit reciprocal.
That is geometry, not a wind decision, and the RPIC has to be told it. It hands the
pilot-notes document its first genuinely operational job: compare 344.6° against the
into-wind heading and state the component the pilot will actually meet on approach. A
belly-landing airframe arriving downwind is precisely the case worth warning about — and it
is the first time any of C-2's wind math will have done real work for anyone.

### 2026-08-19 (V2C-2 — wind, RTH safety gate; steps 1–4 of 9, PAUSED)

Work stopped mid-step for an operational-constraints change. **This entry is the handoff
state — read it before assuming anything about what the engine enforces.**

**Why C-2 exists.** C-1 put the grid 90° off the sun, but the spec is measured on the
camera **boresight**, which follows the fuselage, not the ground track. In any wind the
aircraft crabs, so C-1's perfect 0.00 glint score is only true in still air. Scoping that
turned up something larger: the emergency reserve (a flat 15%) had never been checked
against the mission's actual geometry. It does not hold. The furthest grid point is
**17,323 m** from the landing site against a **14,580 m** reserve — and *even a zero-size
grid fails*, because M1 alone is 14,813 m out. The engine had been planning missions it
could not guarantee a return from since V1. The RTH gate was pulled forward from step E on
that basis, with safety declared the absolute priority.

**Design decisions worth not re-litigating.** The reserve is **derived, not fixed** — a
fixed point that converges in 2–3 passes because ~87% of the worst-case return is the
shore-to-M1 transit, which no amount of grid shrinking touches. Both leg directions sit
exactly |δ| off target, so the tolerance is a **pure crosswind feasibility gate**, not an
optimisation window; rotating the axis provably never helps. The RTH check is stated in
**time**, not distance, because battery is time and distance is not conserved in wind.
`RTH_SAFETY_FACTOR = 1.25` is a decomposed stack (navigation 1.10 × off-best-range speed
1.08 × reaction 1.064 = 1.264), not a guess. Manual crosswind limit is 7.5 m/s, half the
airframe rating, and it binds at roughly 8 m/s of wind.

**Built and tested (steps 1–4).** Six RTH constants; `V1_EMERGENCY_RESERVE_FRACTION`
retired to an iteration seed. Weather provenance — `wind_is_measured` and `stale_fields` —
because `DEFAULT_ZERO_WIND` makes missing wind look like a dead-calm day, the most
permissive possible input to a safety gate. The full wind triangle in `aircraft_math.py`.
`_value_at_time` now honours the interval duration, fixing a silent staleness bug: it used
to return a field's last entry forever past coverage, and NWS visibility covers only 8–30 h
against a 7-day horizon. Parallax extension and `furthest_point_distance_m` in `geo.py`.
Suite went 52 → **66 passing**; test files were renamed to a seven-tier layout (0–6).

**⚠️ NOT BUILT — and this is the important part.** Steps 5–9 are untouched. `planner.py`
has no `_rth_safe_budget` and no `_evaluate_boresight`; `validator.py` is still **0 bytes**.
Every wind function has **zero callers**. `Weather.wind_is_measured` and `.stale_fields` are
populated and read by nobody. `route_duration_min` accepts `weather`/`axis_deg` but the hub
still calls it with three arguments. **The safety machinery is complete, correct, tested,
and connected to nothing.** The engine today produces plans that fail the RTH criterion
without reporting it.

The one C-2 change that IS live is the parallax extension, because it sits inside
`make_lawnmower_grid_through_m1`: every line grew 808 m, route is 82,320 m against an
82,620 m budget, and the margin fell 22.7 → **11.4 min** — against the placeholder reserve,
so optimistic.

**Bugs the audits caught, worth knowing as a pattern.** Interfaces, not algorithms, were
where things broke. The wind components omitted the track entirely, silently hard-coding a
due-north track (correct only for track 000). `return_time_min` returned seconds while
named `_min`, which would have made the reserve loop diverge to 1,311%. `ground_speed_ms`
could return a negative speed, yielding a *negative return time* that reads as a fast, safe
trip home. `furthest_point_distance_m` ignored its own reference-point argument and measured
from `points[-1]`, understating the worst-case return by **61%**. Every one of these was a
confidently-wrong number rather than a crash — which is the failure mode this engine keeps
producing, and why the audit-then-implement rhythm is earning its keep.

### 2026-08-15 (V2C-1 — along-track payload mount)

The SST camera was remounted: yawed to face forward under the nose and pitched to 30°
off-nadir, replacing a cross-track roll at 40°. Scoped as V2C and split into C-1 (viewing
geometry, done) and C-2 (boresight/crab, next). Also raised in the same pass: altitude to
609.6 m (2000 ft), overlap to 50%, grid-width constant to 2 mi.

**What the change actually was.** It presented as "a few constants" and wasn't. The formula
`h·(tan(θ+fov/2) − tan(θ−fov/2))` never computed "swath width" — it computes ground extent
along whichever axis is *tilted*, and that was cross-track only because the camera was rolled.
Moving the tilt to along-track meant `ground_swath_width_m` and `ground_footprint_along_m`
had to **swap formula bodies**. Changing only the angle would have reported 775 m against a
true 627 m — a +23.6% over-estimate feeding straight into line spacing, with no crash and no
failing test. A `MOUNTING NOTE` now sits at the top of `geo.py` so the swap doesn't read as a
bug in `git blame`.

**Two things fell out that we didn't go looking for.** First, the old roll imaged a strip
33.8–241.9 m off to *one side* of the ground track, so the "free M1 overflight" — the
mission's one hard science requirement — was collecting nothing at M1. The new mount centres
the swath on the track and fixes it. Second, `sun ± 90` describes a single grid axis flown
both ways, so **both leg directions now collect**. That made the long-deferred SCIENCE/TRANSIT
OFFSET CORRECTION block obsolete rather than pending — its premise was dead, so it was
deleted. Net effect: bounding-box area fell 10.3 → 6.5 km² at the old altitude, but *true*
science coverage rose, because half the flight stopped being wasted transit.

**What the process caught.** Auditing the implementation turned up an inverted guard that
raised on valid input, `math.cos` fed degrees, `math.radians()` applied to a length, a
`total_lines -= 1` that silently broke the odd-parity invariant the M1 overflight depends on,
and a `metrics["sensor_parralax"]` typo that `.get()` would have swallowed into `None`
forever. The tiered harness also flagged a half-applied refactor on its own: Tier 5 went red
because `geo` was reporting 15 science lines while `planner` still tagged 8. That was a true
positive across a module boundary, and it cleared itself once the planner caught up.

**A rendering bug the new geometry exposed.** Eyeballing the first 90° plan raised "these
lines look perpendicular to the sun, not parallel" — perpendicular is correct (that *is* what
90° relative azimuth means; the old 135° target sat obliquely, which is what the eye was
calibrated to). But checking it surfaced a real defect: `outputs._sun_vector` built the arrow
from degrees of lon/lat without dividing Δlon by cos(latitude), so it drew the sun 5.49° off
true and rendered the sun-to-track angle as 84.5° on a plan holding exactly 90.0°. Plan
unaffected — flight lines are real geodesic points and plot true — but the one instrument
available for eyeballing a plan was itself lying. Fixed, with a Tier 5 regression test that
pins the property (the arrow points where the sun is) rather than the formula.

**Deliberately not done.** Parallax (352 m at 2000 ft) is reported, not corrected — it pairs
with crab shear in C-2 since both are along-track displacements. Tolerance stayed at 15°
rather than tightening to 10°, because the boresight follows the fuselage and crosswind crab
spends that budget first. Two constants were dropped from the plan for being born unread.

Suite: **51 passing**. Engine: N=15, 67.3 min, 22.7 min margin.
