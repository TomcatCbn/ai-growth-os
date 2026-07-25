# ADR-006: Core Loop — Mission-Centric Runtime

- Status: Accepted
- Date: 2026-07-24

## Context

The growth loop (observe → update → plan → mission → evidence) needs a
"clock": what triggers re-planning. Daily cadence is mechanical; fully
event-driven re-planning over-reacts to single evidence items at ages 4-6.

## Decision

1. **Mission-centric loop.** The system holds exactly **one `active_mission`**
   per child at any time. `active_mission` is the system's cursor — the
   answer to "where are we now" for both the UI and the Planner.
2. **Re-planning triggers (only three):**
   - Evidence submitted on the active mission (main loop)
   - Mission stalled beyond threshold (e.g., 3 days, configurable)
   - Parent explicitly requests a change
3. **Mission lifecycle replaces the curriculum timetable.** Multi-day
   immersion in one adventure is success, not schedule slip.
4. **Daily cadence is display-layer only** ("today's recommendation", daily
   reminder copy). Planning logic never binds to the calendar.
5. **Evidence stream does not trigger re-planning** (option C demoted):
   free observations update state via EMA and accumulate; they influence the
   *next* planning cycle, they don't interrupt the current mission.
6. **Component split:** Growth Planner owns the long term (frontier, growth
   goals); a **Mission Manager** owns the present (active mission lifecycle,
   stall detection, handoff to Planner on mission close).
7. The Parent Agent weekly report is the only calendar-driven component.

## Consequences

- `active_mission` becomes a first-class field of the runtime child record
  (runtime state, distinct from the two raw World-Model pockets of ADR-004).
- Next design artifact: Mission Runtime Schema + state machine.
