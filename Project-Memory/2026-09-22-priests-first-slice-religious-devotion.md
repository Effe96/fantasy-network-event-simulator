# Priests' first slice: religious devotion + skepticism, plus a dedicated Criminals dossier and Diseases report

### Continuation of the prior day's work (`2026-09-21-criminals-slice-and-feedback-loop.md`, `2026-09-21b-group-violence-closes-out-criminals.md`). Criminals was fully closed out and pushed; this session built two dedicated single-topic report Artifacts on request (Criminals, then Diseases, restyled once after the first attempt used an off-brand "case file" aesthetic instead of the house style), extended the Criminals report to a real 2-year run on request, then moved to the next item in the build order: Priests.

## What this session did

### 1. Dedicated report Artifacts, on request

The user asked for "a dashboard and a full report showcasing the
Criminals additions," then separately for a diseases-focused one. Built
two new single-topic Artifacts (distinct from the main all-phenomena
dashboard) reusing the main dashboard's real data (theft trend, 2-year
thief-plateau checkpoints, assassination formula, group-violence
before/after fix). First attempt at the Criminals one used a themed
"case file" visual identity (parchment, typewriter font, ink stamps) —
the user said "not the strange style you decided to use," so it was
rebuilt in the dashboard's actual house style (same CSS tokens, card/
KPI/note components) and republished to the same URL. Lesson: don't
invent a bespoke visual identity for a companion piece to an existing
dashboard without asking — match the established house style unless a
distinctive look is explicitly requested.

Then asked to see the Criminals report "for a 2 years simulation" — ran
a real 730-day simulation (not just relabeled the 1-year one) and
rebuilt every chart/number from it, including replacing the
thief-plateau chart's *separate* older verification run with a
checkpoint trend pulled from *this* coherent 2-year run — a genuine
improvement, not just filling in numbers. The 2-year data was itself
informative: group-violence-triggered riots stayed at 3 total (all in
year 1, zero new ones in year 2) while organic riots and group kills
grew roughly in line with the 1-year rates — real evidence the
group-violence fix holds up past the first year, not just looks quiet
on a short window.

Diseases report: same house style, covers `ContagionPhenomenon` (SIR
curve) and `CommonAilmentsPhenomenon` (flu/diarrhea) in one place,
including the zero-immunity runaway bug and flu's winter seasonality
(quarter-by-quarter average sick count, confirmed a real ~70% winter
bump in the actual data before charting it).

Artifacts: `https://claude.ai/artifact/TWRb32eh6zeta4zFcXjbCP` (Criminals
Report) and `https://claude.ai/artifact/S8kcKTQNL7netixug5F1XE` (Diseases
Report).

### 2. Priests' first slice: `ReligionPhenomenon`

User said "let's keep implementing" — picked up the next item in
`docs/plans.md`'s build order (Guards → Criminals → **Priests** → ...)
without being asked to scope it first, following the same "first thin
slice" pattern established for Guards (bribery-only) and Criminals
(thief occupation + theft only): scoped to the vision doc's first
Priests bullet only (religious devotion + a heretic/skeptic minority),
deferring corruption and disease-curer blame.

Design: fires per edge, only civilian-priest (`Node.role` already
covers this). Most civilians' own affinity toward priests grows slowly,
scaled by their own `religiousness` (a `devotion` event — the second
instance of the "favor" event type after bribery). A minority —
`skepticism` above a threshold — feel the opposite (a `friction`
event), classification decided once in `init_state`, same "sticky" shape
`TheftPhenomenon`'s `is_thief` flag uses. Before picking
`devotion_base_rate`/`friction_base_rate`/`heretic_skepticism_threshold`,
checked the real reference town directly (per
[[feedback-check-thresholds-against-real-graph-density]], written last
session after group violence's near-miss): only 4 priests and 313
civilian-priest edges total (vs. guards' 3,166), and skepticism > 0.8
lands ~7.7% of civilians — informed the rate choice instead of guessing
blind. Verified on a real run before calling it done: 98 devotions / 11
frictions, no runaway (the fourth time this project has deliberately
checked a new threshold this way, after three near-misses that shipped
broken the first time).

8 new tests in `tests/test_religion.py`. `docs/decisions.md`,
`docs/plans.md`, and `Project_Vision`'s Priests sections all updated.
Refreshed the main dashboard (v15) with a new Religion card and two new
CSS color tokens (`--devotion`, `--friction`) added properly rather than
reusing an unrelated existing color.

**Noted while refreshing the dashboard, not a bug:** riot counts and
their organic/group-escalated split shifted a lot between the last two
main-dashboard runs (6 total, 3/3 split → 9 total, 1/8 split) purely
from `ReligionPhenomenon` being inserted into `demo.py`'s phenomena
list — every phenomenon shares one `random.Random` instance threaded
through the whole day loop, so adding any phenomenon's own `rng.random()`
calls reshuffles every downstream draw for the rest of the run. Recorded
in `docs/decisions.md` as expected behavior, not investigated further
(the totals stayed in a believable order of magnitude both times).

## Current repo state

Committed as `07bdffd` (religion slice) on top of the prior session's
commits, up through `bce2fe4`. **Not pushed** — ask before pushing
(the user explicitly said "push it" for the Criminals batch specifically
last session; that authorization doesn't automatically extend here).

`tests/run_all.py` → `ALL OK` (13 modules, `test_religion` new).

## What's next

Priests has two items left: corruption (priests accepting payment,
likely reusing bribery's shape) and disease-curer blame (needs a way to
read Contagion's death toll — the same kind of cross-phenomenon link
Guards' patron protection was blocked on, though group violence's
`riot_phenomenon` reference on `ViolencePhenomenon` is now a precedent
for how to wire one). After Priests: Nobles, then Quarantine (needs
both Priests and Nobles), then Taxes, then the town-wide dials.
