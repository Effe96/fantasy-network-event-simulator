# Nobles' last three items: hired assassins, mercenary protection, and the coup mechanic — paused mid-diagnostic

### Continuation of the prior day's work (`2026-09-22-priests-first-slice-religious-devotion.md`). Opened by diagnosing why seed 5 looked like a riot outlier (it isn't — the full engine runs riot-hot for every seed, a flawed isolated-sweep methodology was the real problem), then closed out all four remaining Nobles items: hired assassins, mercenary protection (with a friend-of-a-friend extension on user feedback), and the coup mechanic. Paused mid-session on an open diagnostic about the coup mechanic, at the user's request ("stop the diagnostic and we pick it back up tomorrow").

## What this session did

### 1. Seed 5 riot-outlier investigation — corrected a prior session's flawed methodology

Picked up "figure out what makes seed 5 an outlier, move to a calmer
seed" from the previous session. Real `demo.py --seed 1..10` runs (full
8-phenomenon engine, one seed driving both the import and the run — how
`--seed` is actually used) showed **every seed landing at 5–12
riots/year, mean 8.4** — seed 5 (10) is unremarkable, not a tail. The
prior session's 20-seed sweep that suggested otherwise had held the
graph import fixed and used a trimmed `[violence, riot]` phenomena list
— not a smaller sample of the real distribution, but a different
quantity (it happened to land close to the *organic-only* riot rate,
~1.7/year, missing that group-violence escalation is 80% of real
riots). **Kept seed 5** as the reference; corrected the stale claims in
`docs/plans.md`/`demo.py` comments; extended
[[feedback-isolate-phenomena-for-diagnostics]] with the lesson: an
isolated sweep must vary the graph import *and* the RNG together if the
project's own entry point does, or its aggregate shape can't be trusted
either. Committed as `fb1d9e6`, pushed.

### 2. Nobles hire assassins

Small, self-contained: when `_pick_aggressor` picks a noble as the
solo-violence culprit, success chance is unchanged (their wealth already
buys a skilled hand via the existing SES-vulnerability ratio), but
`noble_hired_assassin_shock_factor` (0.5) halves both `grief_shock`
(neighbors' reaction to a kill) and `discovery_shock` (a survivor's
reaction to a failed attempt) — insulated, not consequence-free. No new
graph edges or resident types. 3 new tests. Committed as `d000d26`,
pushed.

### 3. Mercenary protection — new `is_ex_soldier` trait, then a friend-of-a-friend extension

User asked directly: should hired mercenaries come from an `is_ex_soldier`
trait layered on existing jobs, or a dedicated "mercenary" occupation?
Checked TownShape's own data first (`town_db/military.py`, the reference
town's `military_service` table — 42 rows, all *current* guards, zero
retired-service records) — no real data either way, so it came down to
not overwriting a resident's real TownShape occupation with a fictional
one. Went with the trait: `Node.is_ex_soldier`, civilians only, ~8%
synthetic rate (sized against nobles/priests' median ~102-neighbor
degree).

`ViolencePhenomenon._check_mercenary_hiring`: a noble/priest with more
hostile neighbors than `mercenary_min_enemies` (at the same 0.7 cutoff
`group_hate_threshold` uses) rolls to hire, chance scaling with how far
past the threshold they are (same shape `RiotPhenomenon`'s own trigger
uses), capped at `mercenary_cap`. Each living mercenary multiplies an
attacker's success chance by `mercenary_protection_factor` in
`apply_effect`. Scoped to solo violence only — riot lethality doesn't
see this protection yet, flagged as a deliberate deferral. 7 new tests.
Verified: 26 mercenaries hired on the reference town in a year, no
runaway. Committed as `90d345c`, pushed.

**User feedback, same session:** "they can also be a connection of a
connection, they do not need to be connected directly." Added
`_mercenary_candidates`: tries direct neighbors first, only widens to a
neighbor-of-a-neighbor (2 hops) if none is available — still never
inventing a new edge to a stranger, just walking a real chain of
existing ties. 3 new tests. Verified: 32 mercenaries hired (up from 26).
Committed as `e96b683`, pushed.

### 4. Coup mechanic — coded and tested, **not yet committed**

Vision doc: "Rising taxes raise noble animosity toward the governor;
past a threshold, nobles may hire mercenaries to move against the
governor and seize power themselves. The governing body's suspicion of
an in-progress coup grows with the number of mercenaries hired." Two
real blockers existed (`docs/plans.md` had flagged both): no governor
concept, and Taxes doesn't exist yet.

**Governor:** checked TownShape source and the reference town's own
`town_state` table first — no governor/mayor/ruler concept anywhere, so
this is synthetic regardless. `graph.governor_id: Optional[int]`, a
single town-wide fact (same shape as `town_aggression`, not a `Node`
field almost everyone would carry as `False`). Picked lazily by
`ViolencePhenomenon._ensure_governor` — the highest-degree living noble
— the first time the coup mechanic needs one, with the same call
handling succession if the current governor ever dies (any cause, not
just a coup). Checked this against real data before committing to it:
36 of the other 39 nobles already share a direct edge with the
highest-degree noble on the reference town, so "most connected" also
maximizes who can actually reach them to plot, given the project's
no-invented-edges rule.

**Taxes deferral:** same pattern already used for Nobles' resentment
skew — built entirely on whatever noble-to-governor animosity the graph
already carries or accumulates dynamically; "rising taxes raise it
further" is deferred until Taxes exists.

**Mechanic** (`_check_coup`/`_advance_coup`, `ViolencePhenomenon`'s 5th
capability): one coup in progress at a time (`_active_coup`, same shape
`RiotPhenomenon`'s `_active_riot` uses). The most-hostile-toward-governor
living noble, once animosity over an *existing* edge crosses
`coup_animosity_threshold` (0.5 — checked real data: 0 nobles clear 0.7,
1 clears 0.5, 6 clear 0.3, so 0.5 was the only threshold with any real
day-1 signal at all), rolls `coup_start_rate` to begin plotting. Once
active, each day rolls to hire one more coup mercenary via the *same*
`_mercenary_candidates` pool mercenary protection uses (an ex-soldier
hired for one purpose is unavailable for the other, via the shared
`hired_by` field) — each hire raises `suspicion`, which is *also* that
day's detection-roll multiplier (`coup_detection_rate * suspicion`) —
never a hard threshold, so a fully-staffed plot always has *some* chance
of going undetected. Reaching `coup_mercenary_cap` triggers the attempt:
`coup_success_base_rate * (1 + mercenaries)`, reduced by the governor's
own living protection mercenaries via the *exact same*
`mercenary_protection_factor` formula `apply_effect` already uses — the
two mechanics pay off together. Failure kills the plotter either way
(detection or a repelled attempt); success kills the old governor and
hands `graph.governor_id` to the plotter — both reuse the existing
`alive=False` death mechanic rather than inventing a "deposed but alive"
status.

10 new tests (governor selection, succession, no-nobles edge case,
threshold gating, mercenary hiring/suspicion, plotter death mid-plot,
detection, success against an unprotected governor, defense reducing
success chance). Full suite green.

**Verified on real runs, not yet committed:**
- 1-year reference run (seed 5): 1 coup attempted, 0 succeeded, 3 coup
  mercenaries hired. Fires organically, doesn't runaway.
- 5-year reference run (seed 5): **identical totals to the 1-year run**
  — 36 protection mercenaries, 1 coup attempt, 3 coup mercenaries, all
  by day 153. Nothing new happens in the remaining ~1,670 days. Not a
  runaway (the opposite), but the exact freeze made it worth confirming
  this is genuine equilibrium before writing it up as such.

## Open diagnostic (paused here, at the user's request)

An instrumented script (`coup_saturation_check.py`, written to the
session's scratchpad, not the repo) replays the engine loop manually so
`ViolencePhenomenon`'s own per-resident state can be inspected at day
1825 — specifically, for every living noble/priest: are they already at
`mercenary_cap`, do they never clear `mercenary_min_enemies` at all, or
are they under-cap *and* over-threshold with genuinely zero reachable
`is_ex_soldier` candidate (real saturation) versus something else? The
script was mid-run (~5-year replay, same cost as the earlier real run)
when the user asked to stop and resume tomorrow. Both the diagnostic
process and an earlier wasted attempt at the same check were stopped
cleanly via `TaskStop`; nothing was left running.

**Prior reasoning, not yet confirmed by the script:** this session's own
earlier calibration check found the reference town's hostile-neighbor
count at the 0.7 valence cutoff has median 3 across nobles/priests — so
roughly half never clear `mercenary_min_enemies=3` at all, and the
other half likely hit their personal `mercenary_cap` fast (bounded,
early). If true, day-153 saturation is a legitimate "demand dried up"
finding, same shape as Romance's already-documented "0–2 marriages/year
is correct, not underfiring." The diagnostic script exists to confirm
this rather than assume it — rerun it, read the per-resident breakdown
it prints (`capped_out` / `never_qualified` / `still_wanting_but_uncapped`
counts, plus per-resident candidate availability for anyone in the last
bucket), and write the real answer into the coup mechanic's
`docs/decisions.md` entry before committing.

## Current repo state

**Uncommitted**, on top of `e96b683` (pushed): `demo.py`,
`docs/decisions.md`, `docs/plans.md`, `graph.py`, `phenomena.py`,
`tests/test_violence.py` — the entire coup mechanic (code, docs, tests).

`tests/run_all.py` → `ALL OK` (still 13 modules; the coup mechanic's
tests live inside the existing `tests/test_violence.py`, no new test
file).

## What's next

1. Rerun the saturation diagnostic (see above), resolve the open
   question, note the answer in the coup `docs/decisions.md` entry.
2. Commit and push the coup mechanic. That closes out **all four**
   Nobles items.
3. Per the build order (Guards → Criminals → Priests → Nobles →
   **Quarantine** → Taxes → town-wide dials): Quarantine is next, and
   needs both Priests and Nobles (done as of this session, modulo the
   commit above) — but Priests still has one open item, disease-curer
   blame, blocked on a cross-phenomenon "who died of what" link (the
   same wall Guards' patron-protection hit). Worth deciding whether to
   close that out first or start Quarantine without it.
4. Refresh the main dashboard Artifact (`v17` as of the last check,
   predates this entire session's changes — Nobles' resentment-shift
   retune, seed/outlier correction, hired assassins, mercenary
   protection, and the coup mechanic are all missing from it) and
   consider whether the Criminals/Diseases/Priests companion reports
   need it too, per [[feedback-visualize-every-change]].
