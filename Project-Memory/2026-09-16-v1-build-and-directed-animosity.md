# social-sim-demo: v1 build, disease death, and directed animosity

### History of the session(s) that built this prototype from scratch through its first real extension. Read this before touching `graph.py`/`phenomena.py`/`engine.py` if you weren't there for it — it explains *why* the model is shaped the way it is, not just what the code does.

## What this project is

A standalone prototype (`social-sim-demo/`, sibling to `TownShape/`, never
writes back to it) exploring a generic "phenomenon propagation" engine
over a social graph imported read-only from a TownShape town snapshot.
Full design: `docs/2026-09-15-social-network-design.md`. Current
state/roadmap: `Project_Vision/01-network-simulation.md`.

## Timeline

### 1. Initial build (plan: `docs/superpowers/plans/2026-09-15-social-network-demo-implementation.md`)

Built in a worktree (`social-network-demo` branch) via
`subagent-driven-development`/TDD, task by task: `graph.py` (`Node`,
`Edge`, `SocialGraph`, import from a TownShape `.db`), relationship-type
attribute synthesis, shopkeeper-customer edge derivation, the generic
`Phenomenon` protocol, `ContagionPhenomenon` (SIR), `ViolencePhenomenon`
(with `grief_shock` feedback), `engine.run_simulation`, and `demo.py`.
Merged to `main` via `finishing-a-development-branch` (fast-forward, tests
green). Verified against a real snapshot,
`TownShape/demo_svg_overlay_town.db` (810 residents).

### 2. Results dashboard (Artifact)

Built an interactive dashboard artifact visualizing a real run: disease
spread (SIR chart), population (alive/dead), event-log breakdown, and a
full data table. First publish had a real bug worth remembering: **the
Chart.js CDN URL was pinned to a version (`4.4.4`) that doesn't exist on
cdnjs** — it 404'd silently and the whole inline script died with it, so
nothing rendered. Confirmed the fix by hitting the CDN URL directly
(`curl -sI ...`) before trusting a version number again — cdnjs's
`api.cdnjs.com/libraries/<name>` endpoint lists what's actually there.

### 3. Disease can now kill (feature, not just a viz question)

The user asked to visualize deaths and noticed disease had none —
`ContagionPhenomenon` was SIR-only, no fatal branch, by original design
(see the design doc's now-amended §3.3 note). Added `case_fatality_rate`
(default 3%), reusing `ViolencePhenomenon`'s existing `SES_VULNERABILITY`
weighting for consistency. This required a small architectural fix: the
`Phenomenon.end_of_day` signature gained an `rng` parameter (contagion
needs randomness for the fatality roll; violence's `end_of_day` was and
still is a no-op, just updated to match), and `engine.run_simulation` now
computes `alive`/`dead` **once, graph-wide, from `Node.alive`**, applied
*after* every phenomenon's own `summarize()` — because once more than one
phenomenon can cause a death, no single phenomenon's private bookkeeping
is a trustworthy town-wide count on its own.

Also added CLI knobs (`--transmission-rate`, `--infectious-days`,
`--fatality-rate`) so parameters don't require editing code. Tried
literal Black Death case-fatality figures (~60%) and got 97% town
mortality — because `SES_VULNERABILITY`'s ×2 poor-multiplier stacks with
the input rate and clamps at 100%, and this town's population is 96%
poor. Landed on `--fatality-rate 0.25` (→ ~50% effective CFR for poor
residents once the multiplier applies) to hit the historically-cited
~30-50%-of-total-population range instead. **Worth remembering when
tuning any SES-weighted rate**: the multiplier and the input rate aren't
independent, check the effective rate per SES bracket, not just the input.

### 4. Directed animosity (the bigger fix)

The user asked why a specific violence event picked one victim over the
other, and pointed out — correctly — that `Edge.valence` was a single
value shared by both endpoints, so "how A feels about B" and "how B
feels about A" were, structurally, the same number. Real fix, not a
patch:

- `Edge.valence` → `valence_a_to_b` + `valence_b_to_a`, synthesized
  independently (two separate `rng.gauss()` draws). `tie_strength`
  averages both directions' magnitudes.
- Added `Edge.valence_from(resident_id)` / `.set_valence_from(...)` so
  callers never have to know which of `resident_a`/`resident_b` they're
  asking about.
- `ViolencePhenomenon.edge_probability`: the day's odds come from
  whichever direction is more hostile (`max`, not an average) — a
  one-sided grudge is enough.
- `ViolencePhenomenon._pick_victim` → `_pick_aggressor`: the aggressor is
  now chosen by weighting each side's own outgoing hostility against the
  *other* side's SES vulnerability (`hostility_a_to_b * vulnerability_b`
  vs. `hostility_b_to_a * vulnerability_a`), not a same-valence coin
  flip. Reduces to the old SES-only behavior when both sides are equally
  hostile.
- `grief_shock` now mutates only the bystander's own outgoing valence
  (`set_valence_from(neighbor_id, ...)`) — previously it mutated the one
  shared value the culprit's own (fictional, since untracked) feelings
  toward that bystander were also reading from.
- **This RNG change breaks byte-for-byte reproducibility of old runs at
  the same seed** — every edge now consumes two `gauss()` draws instead
  of one during import, shifting every subsequent random draw downstream.
  Same `(db_path, seed)` still reproduces deterministically *for this
  version of the code*; don't expect an old run's exact events back.
- All tests updated (new coverage added for the directed behavior
  specifically — see `tests/test_graph.py`'s `valence_from`/
  `set_valence_from` tests and `tests/test_violence.py`'s
  `test_probability_driven_by_the_more_hostile_direction` and
  `test_aggressor_is_the_more_hostile_side_when_vulnerability_is_equal`).
  `tests/run_all.py` → `ALL OK`.
- Added a short amendment note to
  `docs/2026-09-15-social-network-design.md` §3.3 rather than rewriting
  every worked example — the section's underlying explanation of what
  valence *means* is still correct, only "one shared value" needed
  correcting to "one value per direction."

Found a real, undirected-model-era bug as a side effect of this: because
`ViolencePhenomenon._pick_victim` never looked at animosity direction, a
close look at one dashboard case study (residents 511/513, seed 3) turned
out to be a **literal 50/50 coin flip** with no connection to who
actually resented whom — both were poor, so SES weights were equal, and
that was the entire deciding factor. Post-fix, the equivalent case study
(residents 61/191, seed 5) shows the mechanism actually working: 61 grew
*more* hostile than 191 over the year (from grief), but 191 still struck
first because attacking a poor victim carries much better odds under the
SES-vulnerability weighting — a real, inspectable reason instead of a
coin flip.

### 5. Results dashboard, updated

Same artifact (`https://claude.ai/artifact/1xczPUnjNSfKa5DfasTcDQ`),
republished: disease-vs-violence death breakdown, a Black Death scenario
section (`--transmission-rate 0.5 --infectious-days 6 --fatality-rate
0.25`, ~51% town mortality), and the corrected 61/191 case study with a
two-line directed-valence chart.

## Current repo state

**Uncommitted, deliberately** — the user never asked for a commit, and
was told the diff would wait for that. `git status --porcelain`, last
checked:

```
 M demo.py
 M docs/2026-09-15-social-network-design.md
 M engine.py
 M graph.py
 M phenomena.py
 M tests/test_attributes.py
 M tests/test_contagion.py
 M tests/test_engine.py
 M tests/test_graph.py
 M tests/test_import_relationships.py
 M tests/test_violence.py
?? Network_Population_depth.md
?? Project_Vision/
?? Project-Memory/
```

All of it passes `tests/run_all.py` (`ALL OK`) as of this writing. Ask
before committing or discarding any of it.

## What's next

`Network_Population_depth.md` is the user's own freeform notes on where
this goes next — town-wide dynamic parameters (aggression/religiosity/
loyalty), romance/marriage/multi-generational family, and new social
roles (Guards, Criminals, Priests, Nobles) each with their own animosity/
affinity mechanics. `Project_Vision/01-network-simulation.md` organizes
that same material by topic against the current codebase — read it
before starting implementation on any of it, since several items there
depend on infrastructure that doesn't exist yet (a personal-trait system
on `Node`, an agreed event taxonomy, a riot model) rather than being
independently implementable one at a time.
