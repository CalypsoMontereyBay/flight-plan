"""
validator.py -- STILL EMPTY. NOTHING IS VALIDATED TODAY.

    ⚠️ 2026-09-08 -- MOST OF THE SPEC BELOW IS CANCELLED. READ THIS FIRST.

Operational constraints changed: every aircraft is now assumed to carry wind sensing and to
compensate in flight for heading and speed. The engine therefore MUST NOT reject a plan or
alter a grid because of wind. The RTH / crosswind / boresight gate specified below is
CANCELLED, not deferred -- that math moves to a pilot-notes report instead. See CLAUDE.md,
"Operating constraints -- 2026-09-08" and Step E.

What survives for this file, whenever it is finally written:
  * legality (Part 107 and friends: authorized ceiling, daylight, VLOS, airspace, over-water)
  * an OPEN QUESTION -- does battery/endurance feasibility stay a gate? A route longer than
    the battery is not a weather problem and no onboard sensor fixes it. Undecided.
  * the RE-DERIVE rule at the bottom, which is good practice regardless of what is checked.

Everything from here down is preserved as HISTORY: it records what was scoped, what was
built, and why. Do not implement it as written.

--------------------------------------------------------------------------------------

This file is reserved for the gate that decides whether a CandidatePlan is safe and legal
BEFORE outputs.py writes anything. It has no code yet, and that absence is load-bearing
information: every plan the engine currently produces is UNGATED.

    ⚠️ The engine cannot presently tell you whether the aircraft can get home.

V2C-2 built the entire return-to-home apparatus and then stopped before wiring it:

    aircraft_math   wind triangle, ground speed, return_time_min, required_reserve_time_min
    geo             furthest_point_distance_m -- the worst-case return distance
    objects         Weather.wind_is_measured, Weather.stale_fields -- data provenance
    objects         CandidatePlan.set_rth_assessment / set_viewing_geometry /
                    set_aircraft_feasible, and the aircraft_feasibility / legality /
                    validation_messages getters

All of it is tested. NONE of it has a caller. Measured on the default mission, the
furthest grid point is 17,323 m from the landing site against a 14,580 m emergency
reserve -- the plan fails its own safety criterion by 2,743 m and nothing reports it.

WHAT THIS FILE IS SUPPOSED TO DO (V2C-2 step 6)
-----------------------------------------------
Take a finished CandidatePlan and decide feasibility, then legality:

  RTH        return_time_min(worst point -> land) * RTH_SAFETY_FACTOR
             + RTH_TERMINAL_ALLOWANCE_min  <=  the reserve the plan was sized against
  crosswind  homeward-leg crosswind <= MANUAL_RTH_MAX_CROSSWIND_ms (7.5), so a human can
             hand-fly the return
  boresight  axis error + |crab| <= V1_GLINT_TOLERANCE_DEG, or the science is invalid
  battery    battery_margin_min > 0
  legality   Part 107 and friends -- deferred to step E

THE RULE THAT MAKES IT A GATE RATHER THAN A RUBBER STAMP
--------------------------------------------------------
RE-DERIVE every quantity from the plan's own waypoints, weather, and aircraft. Do NOT read
the values planner stored via set_rth_assessment() -- those exist for REPORTING. Reading
them would check the builder's arithmetic against itself, and a bug in _rth_safe_budget
would sail straight through.

Second rule: "no wind data" is not "no wind". Weather.wind_is_measured is False for the
stub and for any field whose forecast does not cover the mission time, and
DEFAULT_ZERO_WIND makes that absence look like a dead-calm day -- the most permissive
possible input to a safety gate. When wind is unmeasured or stale, the verdict is
"cannot verify", never "safe".

Keep this module a LEAF: planner calls validate(plan); this file never reaches back.
"""
