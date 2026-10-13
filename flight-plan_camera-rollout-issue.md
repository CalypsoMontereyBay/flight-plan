# flight-plan: the camera starts before the BlackSwift S2 has rolled out of its turn

Found 2026-09-28 by flying flight-plan's own V2 lines in uas_sim, the Gazebo + PX4 SITL
simulator in `~/programs/Python/CMB/CLAUDE_UAS_SIM`. This note is written for an agent
working on flight-plan. It describes the problem, where it lives in the code, what the
simulator measured, and three ways to fix it. **Nothing in flight-plan has been changed;
which fix to take is the user's decision.**

## Summary

- Every science line starts with a turn at its turn waypoint:
  - a 90° turn from the 313 m offset leg on lines 2 onward
  - a 118° turn from the transit on the first line of `V2 Plan_20260922-1240.plan`
- The camera switches on just `V1_COLLECTION_INSET_m` = **52 m** after that waypoint, at
  collect_start. It uses a 206 item with param3 = 1, which takes an image immediately.
- 52 m is shorter than the S2's still-air turn radius (57 m), so the first image of a line
  is taken while the aircraft is still banked. In wind the turn is wider, and it gets worse.
- That first image cannot simply be written off. It is the **only** image covering the first
  ~54 m of the science box. The second image's footprint begins beyond the box edge (the
  numbers are in "The geometry" below).
- In SITL on flight-plan's real line geometry:
  - Every line's first image was banked 20–31°.
  - On the line entered from a downwind offset leg, the aircraft was level only 281 m past
    the turn waypoint.
  - That line's science box had only **50 %** of its first 100 m covered.

## Where it lives in flight-plan

| What | Where |
|---|---|
| The 52 m inset ("rollout-of-turn and settle distance") | `src/constants.py:110` `V1_COLLECTION_INSET_m` |
| Line points `[turn, collect_start, centre, collect_stop, turn]`, with the collect points inset from each end | `src/geo.py:243-266` `make_line_through_point` |
| Line extension per end = parallax + inset (352 + 52 = 404 m) | `src/geo.py:372` `extension_m` |
| Trigger distance = along-track footprint × (1 − overlap) = 280.74 m | `src/geo.py:370`, `src/constants.py:509` |
| 206 params `[distance, 0, CAM_TRIGGER_START (1), cam id]`; param3 = 1 means "take one image now" | `src/outputs.py:606-611`, `src/constants.py:505` |
| Waypoint acceptance radius 28.5 m (param2 of every nav item) | `src/constants.py:430` |
| S2 cruise 18 m/s, turn radius 57 m, wind rating 15 m/s | `src/constants.py:145`, `:139`, `:133` |

## The geometry (609.6 m above the sea)

**The footprint.** The FLIR Boson has a 48° × 36.8° field of view and is tilted 30° forward.
Along the track, measured forward from where the aircraft is when it takes the image:

| Part of the footprint | Formula | Distance ahead |
|---|---|---|
| Near edge | h · tan(30° − 18.4°) | **125.1 m** |
| Boresight (the parallax) | h · tan 30° | **352.0 m** |
| Far edge | h · tan(48.4°) | **686.6 m** |

That gives a footprint 561.5 m long. At 50 % overlap the trigger distance is 280.74 m.

**Where things sit along a line.** Distances are measured from the turn waypoint T:

| Point | Distance from T | Ground it images |
|---|---|---|
| collect_start (camera on) | 52 m | — |
| Science box start (T + parallax + inset) | 404 m | — |
| Image 1, at collect_start | 52 m | 177.1 → 738.6 m (boresight lands on the box edge, by design) |
| Image 2 | 332.7 m | 457.9 → 1019.3 m |

So the box's first **53.9 m** (404 → 457.9 m) are seen by image 1 alone.

**Why "setup + rollout is longer than the trigger distance" doesn't protect this.** It keeps
the box start more than one image spacing from T. But the second image's footprint starts
280.74 + 125.1 = 405.9 m after the first image. That is further than the 352 m parallax, so
it never reaches back to the box edge. Image 1 is required, and it is taken in the turn.

**The turn.** At its turn radius the S2 banks φ = atan(V² / (g·R)) = 30.1°. The ground
radius of that turn, in the worst case (tailwind), is R_g = (V + W)² / (g·tan φ):

| Wind aloft W | Ground turn radius R_g |
|---|---|
| 0 (still air) | 57 m |
| 10.8 m/s | 146 m |
| 15 m/s (the wind rating) | **191.6 m** |

A 90° fly-by turn reaches the new line no sooner than R_g past the waypoint. Rolling out and
settling onto the line come on top of that. So even in still air the aircraft reaches the
line at 57 m or more, past the 52 m collect_start. The 118° first-line entry is worse.

**The line spacing is also tight.** The 313 m line spacing is smaller than the turn diameter
at the wind rating (2 × 191.6 = 383 m). So on the downwind side the aircraft cannot finish
the turn onto the next line without overshooting it. That is what the 89 m excursion below
is.

## What the simulator showed

**Setup:**
- **Aircraft:** uas_sim flies PX4 v1.18 SITL on a Gazebo model scaled to the S2 (3.048 m span,
  9.5 kg, 18 m/s cruise, 57 m turn radius).
- **Mission:** the first three lines of `V2 Plan_20260922-1240.plan`, exactly as written
  (items 1–21: altitude, 313 m spacing, 52 m inset, 206 items at 280.74 m, 28.5 m
  acceptance). They were moved 20.5 km north so the aircraft skips the 22 km transit, with
  exp2.plan's takeoff and landing added.
- **Wind:** 6 m/s from 300° at 10 m, which is about 10.8 m/s at altitude with the 0.143 shear
  exponent.
- **Height:** the simulated ground sits at launch elevation, so the aircraft flew 594 m above
  it. Its footprints are ~2.6 % smaller than over the sea; nothing below changes.

**Results.** Distances are along the new line, past its turn waypoint:

| | Line 1 | Line 2 | Line 3 (entered from a downwind offset leg) |
|---|---|---|---|
| Bank under 5° from | 41 m | 104 m | **281 m** |
| Within 10 m of the line from | immediately | 60 m | **186 m** (worst 89 m off) |
| Image 1 (where, bank) | 15 m, 31.0° | 6 m, 19.7° | 0 m, −25.3° |
| Image 2 (where, bank) | 296 m, 0.0° | 286 m, −0.2° | 280 m, −7.4° |
| Science box coverage, first 100 m | 100 % | 100 % | **50.3 %** |
| Science box coverage, next 200 m | 100 % | 100 % | 96.7 % |

- **Overall:** 37 images against 36 predicted, 3 taken at more than 10° of bank, mission
  completed. The run's full report is at
  `~/.uas_sim/runs/run-20260928-150115-529e/report.html`, and its `inputs.json` holds the
  exact mission flown.
- **PX4 switched the camera on 0–15 m past T, about 40–50 m before collect_start.** Autopilots
  count a waypoint reached before they get to it (flight-plan asks for 28.5 m, and PX4's
  fixed-wing guidance can switch earlier). That early start moved image 2 back to
  280–296 m. On the two good lines, that happened to land image 2's footprint on the box
  edge. An autopilot that switches the camera on exactly at collect_start loses the box's
  first ~54 m whenever image 1 is banked.
- **An earlier run agrees.** It used a tighter test pattern (250 m altitude, 128 m spacing,
  the same 52 m inset). 5 of 34 images were taken at more than 10° of bank, and on 2 of 3
  lines the aircraft was still banked 239–262 m past the turn waypoint.

**Caveats:**
- The real S2 flies Black Swift's own autopilot; PX4 is a stand-in. The turn-radius
  geometry above holds for any autopilot. The exact rollout distances and the early camera
  start are PX4's.
- This is one wind direction and three lines.
- The first-line entry from the transit (118°) was not flown: in the test the first line was
  entered after the climb from home.

## The requirement any fix must meet

The first image that counts as science is the one whose footprint covers the box start. It
must be taken **wings-level and on the line.** Call the distance past T where that becomes
true D_level.

- **Measured:** 41–104 m after upwind entries; 281 m after the downwind entry at 10.8 m/s
  aloft. The 281 m is about 1.9 × R_g.
- **Sizing rule:** D_level ≈ 2 · R_g at the wind rating = 383 m, plus ~50 m for the
  autopilot reaching waypoints early, ≈ **430 m.**

Size this from the aircraft's **wind rating** (`BLACKSWIFT_WIND_RATING_ms`), not from the
forecast. The rating is a fixed aircraft constant. That keeps the grid geometry independent
of weather, in the spirit of constraint 4 (describe conditions, don't re-steer on them).

## Fix options

### A. Lengthen the rollout inset

- **The change:** set the inset to about 2·R_g(wind rating) + 50 m, which is ≈ 430 m for the
  S2. Derive it from the turn radius, cruise speed and wind rating constants rather than
  hard-coding it. Keep `extension_m` = parallax + inset, so image 1's boresight still lands
  on the box edge, and image 1 is now level.
- **Cost:** each line grows by 2 × (430 − 52) ≈ 756 m. On the 9-line V2 grid that is
  ≈ 6.8 km, or about 6.3 min at 18 m/s. The transit-aware sizing (J-4) will absorb it,
  possibly by dropping a line.
- **Pros:** one constant changes; the camera items and grid logic stay as they are.
- **Cons:** the longest lines of the three options.

### B. A slight outward turn so the aircraft lines up before the turn waypoint

- **The idea:** shape the approach so the aircraft joins the new line's axis **outside the
  grid, before T**, heading along the line, instead of turning onto it at T.
- **Between lines:** instead of two 90° turns around the 313 m offset leg, the aircraft
  swings slightly outward (away from the next line), then turns back through a little more
  than 180°. This is a bulb or teardrop turn, and its arc ends on the next line's axis.
  - For a constant-radius turn, the outward angle is β = arccos(p / 2R_g) when the line
    spacing p is smaller than 2R_g. The join point lies 2R_g · sin β beyond the line end.
  - At the wind rating (p = 313 m, R_g = 191.6 m): **β ≈ 35°, joining about 220 m outside
    the grid.** When p ≥ 2R_g (for example R_g = 146 m at 10.8 m/s: 292 m < 313 m), no
    outward swing is needed; the turn only needs a straight run-in after it.
- **In waypoints:**
  - Add a lead-in waypoint on the next line's axis, outward of T by at least the rollout and
    settle distance (~100 m).
  - Add an outward waypoint placed so the aircraft reaches the lead-in point nearly along
    the axis.
  - Autopilots cut corners, so the lead-in needs its own straight segment before T.
- **The first line needs the same treatment.** V2's transit arrives on 175° and turns 118° onto
  the first line at T. A lead-in waypoint on the first line's axis, extended outward, lets
  the transit end already aligned.
- **Pros:** the turn happens outside the line, so the inset (and the extension) can stay
  short. It also removes the overshoot when line spacing is below the turn diameter.
- **Cons:** more waypoints and turn geometry in flight-plan, and the outward swing adds some
  distance of its own. It needs checking in the simulator, because waypoint-following is not
  arc-following.

### C. Drop the first picture; the former second photo becomes the first

This only works if the new first image (the old image 2) reaches the box start and is level.

- **Coverage:** image 2's footprint starts 53.9 m inside the box. So the lines must be
  extended by one trigger distance: extension per end = parallax + inset + trigger distance
  = 352 + 52 + 280.74 ≈ 685 m. That is 280.74 m more per end, ≈ 561 m per line, and
  ≈ 5.1 km on the 9-line grid. Otherwise the box's first ~54 m of every line go unimaged.
- **Levelness:** the new first image is taken at inset + trigger = 332.7 m past T.
  - That clears the 281 m measured at 10.8 m/s aloft.
  - It does not clear the ~430 m needed at the 15 m/s rating, unless the inset also grows
    to ~150 m.
  - With early waypoint acceptance (PX4 started ~50 m early), the image lands at ~281 m,
    right at the measured limit.
- **C versus A:** sized for the same wind, C is never shorter than A. Both put the first
  science image at D_level + margin past T; C also takes one extra image and throws it away.
  Its advantage is that the inset and the camera items stay as they are; only the extension
  grows.
- **Two ways to drop the image:**
  - Keep taking it and exclude each line's first image in processing. This works on any
    autopilot and is the simplest.
  - Or write param3 = 0 in the 206 start item (today `CAM_TRIGGER_START` = 1, "take one
    image now"). ArduPilot then takes no image at the start; its first image comes one
    spacing later, where the old second image was. **PX4 ignores this**: its
    `camera_trigger` always takes an image when the camera starts (checked in the PX4
    v1.18 source, `camera_trigger.cpp` `update_distance`). Black Swift's autopilot is
    unknown and needs checking.

**Combinations work too.** For example, B's outward turn with a modest inset, or C with the
inset raised to ~150 m for the wind rating.

## How to check a change with uas_sim

```bash
cd ~/programs/Python/CMB/CLAUDE_UAS_SIM
# Pre-flight: turn_too_tight flags a leg shorter than the turn needs at the worst ground radius
.venv/bin/uas-sim analyze --mission <plan> --profile blackswift_s2 --wind 15@<direction>
# Fly it in PX4 SITL
.venv/bin/uas-sim run --mission <plan> --profile blackswift_s2 --speed 3 --wind 6@300
```

What to look at:
- The run's `report.html` has a **Sensor footprints** section. **"Taken in a turn"** (images
  at more than 10° of bank) should be 0.
- The same section shows coverage and forward and side overlap. It also has a map of
  predicted against flown footprints, with coverage gaps in red.
- A full V2 plan includes the 22 km transit each way, about 50 min of simulated flight. For
  quick checks, fly a few lines moved near the launch point, as was done here.
