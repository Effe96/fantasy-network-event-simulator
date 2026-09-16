# Fantasy Network Event Simulator: Project Vision

Same convention as `TownShape/Project_Vision`, scaled down: this project
is one cohesive layer (a phenomenon-propagation engine over a social
graph), not several, so there's a single content file instead of a
per-layer split.

## Core concept

A standalone prototype exploring a generic "phenomenon propagation"
engine over a social graph imported (read-only) from a TownShape town
snapshot. Residents are nodes; relationships (spouse, coworker, neighbor,
shopkeeper-customer...) are directed edges carrying tie strength and
independent per-direction animosity/affection. A handful of
"phenomena" (disease-like contagion, animosity-driven violence, and
whatever's proposed below) run day-by-day over that graph through one
shared engine, each free to read the graph's structure and mutate its
own state and the edges it's entitled to touch. Deterministic: the same
`(db_path, seed)` always produces the same run. Never writes back to the
TownShape snapshot it reads from.

## How this folder is organized

[`01-network-simulation.md`](01-network-simulation.md) has the same two
sections as TownShape's layer files:

- **Current State** — what's actually implemented today. Comment here
  if a description has drifted from what the code does.
- **Feedback & Future Ideas** — organized by the social role/topic it's
  about (People, Guards, Criminals, Priests, Nobles, town-wide dynamic
  parameters, event taxonomy). Sourced from
  [`../Network_Population_depth.md`](../Network_Population_depth.md) —
  the user's original brainstorm, kept as-is for its own record; this
  file re-organizes that same content by topic and against what's
  already built, rather than replacing it.

## Status key

Same vocabulary as `TownShape/Project_Vision`:

- **Open** — not addressed, no decision made yet
- **Proposed** — a new idea/feature request, not yet triaged
- **Deferred** — considered, deliberately not doing now, reason given
- **Planned** — agreed direction, not yet implemented
- **Addressed** — resolved, with a pointer to where/when
- **Rejected** — considered and deliberately not doing, reason given

## How to give feedback

- **On something in Current State:** add a line right under the
  relevant bullet, e.g. `> Feedback: ...`.
- **A new idea:** add it under the relevant topic heading in
  `01-network-simulation.md`, or drop it straight into
  `Network_Population_depth.md` if it's easier to write freeform first —
  it'll get folded in and organized on the next pass.
- **Reacting to an existing entry:** add a line under it rather than
  editing the original, so the back-and-forth stays visible.
