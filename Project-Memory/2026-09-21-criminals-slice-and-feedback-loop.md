# Criminals' first slice, a real dashboard-driven bug fix, a standing feedback loop, and two real fixes from it

### History of the session that added thief occupation + theft, refreshed the results dashboard, set up `docs/feedback.md` as a durable channel for the user's own notes, and then fixed two real bugs the first round of feedback surfaced (thief population growing unboundedly, and a riot-lethality formula that let guards die more than rioters despite the constants saying otherwise). Read this before touching `TheftPhenomenon`, `RiotPhenomenon._advance_riot`, `demo.py`'s summary math, or the dashboard artifact if you weren't there for it.

## What this session did

Six threads, in order:

### 1. Criminals: thief occupation + theft (`TheftPhenomenon`)

Per the agreed build order (Guards → **Criminals** → Priests → Nobles →
...), scoped to a first thin slice — thief occupation + theft only,
deferring assassination refinement and the group-violence-into-riot
trigger, same pattern `GuardPhenomenon` used for bribery-only.

Design decision made and recorded (`docs/decisions.md`'s 2026-09-21
entry): becoming a thief is a **sticky per-resident flag**, rolled once
in `end_of_day` and scaled by `ses` (poor ×2, rich ×0.3), the same shape
as Romance's `married` flag — not a new `Node` field, and not a status
recomputed from circumstances every day. `docs/plans.md` had flagged
this as an open question to resolve before coding; no new information
changed the existing lean, so it was decided rather than re-litigated.

Theft itself reuses the per-edge `Phenomenon` shape: fires on an edge
with exactly one thief endpoint, scaled by the thief's `cunning` and the
victim's wealth (reused `GuardPhenomenon`'s `BRIBE_WEALTH_FACTOR`). A
flat discovery chance drops the victim's valence toward the thief, and
the valence of every guard the thief personally knows, toward the
thief. Covered by `tests/test_theft.py` (8 tests); wired into `demo.py`.

**Landed uncommitted, pending confirmation** — see repo state, below.

### 2. `demo.py` rioter-death bug, found while refreshing the dashboard

Rerunning the reference town (`demo_riverport_town.db`, seed 5) to
refresh the results dashboard surfaced a real accuracy bug, unrelated to
Theft: `c30bfda` (an earlier session) added `riot_rioter_deaths` to
`RiotPhenomenon`'s summary, but `demo.py`'s own `_print_summary` never
picked up the new key — rioter deaths were silently folded into the
"violence" tally instead of the "riot" one. Fixed by including
`riot_rioter_deaths` in both the riot-deaths sum and the printed riot
line. This is why this run's violence-deaths KPI (124) differs from what
a stale pre-fix run would have shown (146) for the same seed.

### 3. Results dashboard, refreshed

Same artifact (`https://claude.ai/artifact/1xczPUnjNSfKa5DfasTcDQ`),
republished against the same reference town/seed so old sections stayed
comparable: added a Theft card + chart, corrected the riot case study
with this run's actual event log (day 347 trigger, day 348 two-sided
guard/rioter combat, days 349-351 noble-hatred-weighted kills — including
an honest note that the mob's last kill landed on the *least*-hated
noble in town, since hatred sets odds, not a strict queue), and
regenerated the Black Death scenario on the *same* town/seed as the main
run (previously mismatched: the old scenario secretly used a different,
809-resident snapshot despite claiming "same town and seed").

### 4. `docs/feedback.md` created, then used for the first time

The user asked directly: "I want some level of visualization to check
what the model now does" (saved as a standing preference in Claude's own
memory — see `[[feedback-visualize-every-change]]` if using that
system) and then, separately: "Where can I write my feedback... We need
a reliable system." Presented three options (a plain repo file, comments
on the dashboard artifact, GitHub issues); the user picked the plain
file. Created `docs/feedback.md` with a stated contract: the user writes
dated notes on what the simulation *does*, Claude reads every entry each
session and triages it into a fix, a calibration tweak, or new work.

The user then immediately populated it with 9 real notes on this run's
dashboard, and asked for them to be folded into `Project_Vision` and
`Project-Memory` specifically (not `docs/plans.md`/`docs/decisions.md`
this time, though the file's own header describes those as its usual
destination — followed the more specific instruction given). Triage
(each entry in `docs/feedback.md` now carries a status tag pointing
here):

- **Thief population should plateau, not grow unboundedly** — real gap:
  the flag only ever turns on, nothing ever removes it. Needs arrests
  (Guards' long-deferred arrest behavior, now unblocked since theft is
  a real crime to react to), a deterrence feedback loop off recent
  arrest rate, corruption-scaled execution-instead-of-arrest, and a
  continuous poverty-severity measure instead of the 3-tier `ses`
  bucket. Folded into `Project_Vision`'s Criminals section.
- **Irregular income for informally-employed residents, beggars, a
  hardship/starvation death from sustained poverty, and continuous
  ambient sickness scaled by poverty** — none of these have a home in
  the existing topic structure, since there's no economic model at all
  today (`ses` is a static, never-earned/spent import). Added a new
  **"Economy & poverty"** section to `Project_Vision` consolidating all
  four, since they share the same missing continuous-poverty-measure
  foundation.
- **Riot lethality ratio (guards dying more than rioters)** — not new;
  this is the same gap `docs/decisions.md`'s 2026-09-17 entry already
  flagged and deliberately deferred. Worked out *why* it happens despite
  `rioter_lethality > guard_lethality`: the death-count formula also
  scales inversely with each side's own headcount, and with the mob
  only ~1.4× the guard count this run, that size-ratio term nearly
  cancelled the lethality edge out (both sides landed near a 0.43
  per-capita death chance). Recorded as a concrete calibration data
  point in `Project_Vision`'s Riots section for whenever it's retuned.
- **"I still don't understand why no one falls in love"** — the
  existing Romance section already has a detailed "not underfiring,
  small-numbers effect" explanation from an earlier session; the user's
  renewed confusion means that explanation didn't actually land. Flagged
  as open in `Project_Vision`, not closed — either the mechanic needs
  rebalancing or the dashboard needs to show near-miss courtships so
  "quiet year" reads as intended rather than broken.
- **A "stress" personal property** (poverty/grief/sickness-driven) —
  added as a new candidate under `Project_Vision`'s People/traits
  section, explicitly framed as the individual-level analog of the
  existing town-wide-dials-as-aggregate-of-traits open question.
- **"What does grief shock affect?"** — answered directly in chat
  (`ViolencePhenomenon.grief_shock`: when someone dies, their other
  living connections who also know the culprit get *more hostile
  toward the culprit*, in their own outgoing valence only). No doc
  change needed — the existing Violence section already describes this
  correctly; the gap was the user reading the dashboard's raw event
  count, not the docs.

### 5. Thief population plateau (`TheftPhenomenon`)

The user asked to "proceed with the next steps in the plan," which
meant the two highest-priority items from the triage above, not the
original `docs/plans.md` order (assassination refinement, group
violence) — those stay queued after this.

Added arrest + execution + decaying deterrence to `TheftPhenomenon`. A
caught thief with a guard neighbor can be arrested (clears `is_thief`)
or, if those guards are on average low-loyalty, executed (removed from
the graph) instead — reusing `GuardPhenomenon`'s existing loyalty-as-
corruption-proxy rather than building a new town-wide corruption dial.
Every removal raises a decaying `_deterrence` level that divides down
the become-a-thief probability. Swept a few parameter combinations
against the reference town/seed and picked the one whose late-year
trajectory actually flattened (77→78 thieves from day 330 to 365), not
just "produced a smaller number" — landed on `become_thief_rate=0.00015`
(was 0.0005), `deterrence_weight=0.25`, `deterrence_decay=0.985`,
`arrest_chance_per_guard=0.45`. Reference town: 511→78 thieves (27%→
4.1%). Three new tests in `tests/test_theft.py` cover arrest, execution,
and the deterrence suppression effect. Decision recorded in
`docs/decisions.md`.

### 6. Riot lethality: a real bug, verified before being fixed

The second priority item. Before touching any constants, checked
whether the single bad run flagged in feedback (24 guards died vs. 22
rioters) was a real structural bug or just an unlucky draw — the
in-chat "root cause" reasoning written into `Project_Vision` during
triage turned out to be wrong on reflection (it analyzed one specific
matchup's expected value and concluded the formula was probably fine).
Ran a 30-seed aggregate in isolation (`RiotPhenomenon` alone, not the
full 6-phenomenon engine — the first attempt at this used the full
engine and effectively stalled for 20+ minutes on this environment's
slow single-threaded Python before being killed and redone) and got 649
guard deaths vs. 539 rioter deaths — confirming a real, systematic bug.

**Root cause**: the old formula (`lethality * opposing_count /
own_count`) makes each side's *total* expected daily deaths equal to
`lethality * the_other_side's_raw_headcount`, completely independent of
your own side's headcount. Since rioters are drawn from the whole town
but the guard corps is small and fixed (~40), a merely-larger-than-usual
mob made guard casualties (driven by unbounded mob size) swamp rioter
casualties (capped by the guard corps' small fixed size) regardless of
the lethality constants' intended 2x/3x guard-favoring ratio.

**Fix**: switched to a square-root size factor
(`lethality * sqrt(opposing_count / own_count)`) on both sides, which
makes total expected deaths on each side reduce to
`lethality * sqrt(guards * rioters)` — the same size factor for both —
so the guard:rioter casualty *ratio* becomes exactly
`guard_lethality:rioter_lethality`, independent of mob size entirely.
Retuned to a clean 3:1 (`guard_lethality=0.2`, `rioter_lethality=0.6`,
unchanged). Re-ran the same 30-seed aggregate: 381 guard deaths vs.
1,036 rioter deaths (ratio 0.368, close to the 0.333 target).

Replaced `tests/test_riot.py`'s old
`test_guards_die_less_often_than_rioters_at_equal_force_size` — it
manually reimplemented the formula inline rather than exercising the
real code path, so it would have kept passing even with the bug in
place (equal counts happen to make the old and new formulas coincide)
— with `test_guards_die_less_often_than_rioters_regardless_of_mob_size`,
which runs real riots at two very different mob:guard ratios and checks
the casualty ratio stays stable between them. Full writeup in
`docs/decisions.md`.

### 7. The thief plateau claim was wrong — caught and corrected the same day

After presenting threads 5-6 as done, the user asked directly: "Are you
sure it plateaus?" Good question — the "77→78, looks flat" read that
closed out thread 5 was from a single 1-year trajectory, and re-checking
the actual per-30-day growth rate (0.2, 0.2, 0.23, 0.2 thieves/day for
the last four windows) showed it was **not** decelerating at all, just
noisy. A 3-year run confirmed it: 94 → 221 thieves, year 1 to year 3,
same ~0.2/day rate the whole way. No plateau — the earlier claim was
simply wrong, made without checking a long-enough horizon.

Root cause, once found: arrest was gated on the thief having an actual
guard *neighbor* in the social graph. With only ~40 guards among 1,911
residents, most caught thieves never had one — only 20 of 195 catches
(10%) led to any removal in year 1, far too weak for deterrence to
matter at town scale. Fixed by decoupling arrest from local adjacency:
`arrest_chance` is now a flat, town-wide probability on every caught
theft, and the execution-vs-arrest split reads a precomputed town-wide
average guard loyalty (`self._avg_guard_loyalty`, set once in
`init_state`) instead of a caught thief's own guard neighbors. The
local guard-neighbor valence hit (guards *you know* getting angrier)
stayed unchanged — only whether an arrest actually happens stopped
depending on it. `tests/test_theft.py` gained
`test_thief_can_be_arrested_with_no_guard_neighbor_at_all`, which
exercises exactly the case the old version silently failed on (a graph
with no guard node at all).

Re-verified properly this time: a 2-year run (removal rate rose from
10% to 43% of catches) shows real fluctuation in the trajectory,
including several genuine *declines* (day 90→120: 28→27; 150→180:
36→34; 240→270: 41→40; 500→550/550→600: 65→64→63) — only mathematically
possible once removals start outpacing new thieves in a given window,
which never happened even once under the old mechanism. Year-1 average
≈36, year-2 average ≈66 — still trending up overall but far more slowly
and with real negative feedback now visibly present, not yet confirmed
fully converged (a longer/more-seeded run would pin down the exact
equilibrium level, not run given the cost of multi-year full-town runs
here — one 3-year attempt was killed mid-run by the host's own memory
pressure while this session was otherwise idle, unrelated to anything
in the simulation itself).

**The general lesson, not just this one fix**: a short-window
"looks flat" read on a single seed is not evidence of convergence for
a negative-feedback mechanic — check growth-rate trend explicitly
(differences between windows, not just two endpoints), and verify over
a horizon long enough that the mechanism has room to actually reach
equilibrium before claiming it does. Both `docs/decisions.md` entries
for this (the mistake and the correction) are kept, not just the fixed
one — the log is meant to show what was tried and found wrong, not
just the final answer.

### 8. Assassination refinement (`ViolencePhenomenon`)

Next item in `docs/plans.md`'s Criminals queue after the two feedback
fixes above, scoped exactly as the plan already specified: extend
`ViolencePhenomenon` directly (not a new phenomenon), reuse
`SES_VULNERABILITY`. A violent attempt now rolls a success chance —
`min(1.0, success_base_rate * victim_vulnerability /
attacker_vulnerability)` — before killing anyone, using the existing
`SES_VULNERABILITY` dict for both sides at once: victim's value in the
numerator (poorer victims easier to actually kill), attacker's in the
denominator, inverted (richer attackers succeed more easily). A failed
attempt never kills; the surviving victim's own valence toward the
culprit drops sharply instead (`discovery_shock`), and no `grief_shock`
fires since nobody died. Defaults (`success_base_rate=0.85`,
`discovery_shock=0.5`) keep same-class violence close to the old
guaranteed-kill behavior while a poor-attacker-vs-rich-victim attempt
succeeds only ~21% of the time.

Verified on a real run before moving on (habit from thread 7): 24
failed attempts out of 109 total violence attempts (~22%), no crashes,
and `demo.py`'s violence-death accounting needed no changes since a
failed attempt never touches `alive`/`dead` (unlike the riot/execution
gaps found earlier this session). Two new tests in
`tests/test_violence.py`; all existing tests passed unchanged (the one
that forces a rich-attacker-vs-poor-victim pairing happens to land
exactly on the formula's guaranteed-success case, so its assertions
still hold). `docs/decisions.md`'s 2026-09-21 entry has the full
reasoning behind the formula choice.

### 9. Common ailments: two named diseases, and a second real bug caught before shipping

The user had raised disease-frequency feedback twice already this
session (captured in the previous conversation's docs work, vaguely at
first, then precisely once they spelled out flu/diarrhea,
contagious-vs-not, poverty-scaled incidence *and* fatality). This
thread is where they asked to actually build it, "to maybe close the
diseases section."

Added `CommonAilmentsPhenomenon`: flu (contagious, edge transmission
reusing `ContagionPhenomenon`'s staged-pending discipline, plus a small
spontaneous "outside" rate so it never needs a `patient_zero` seed) and
diarrhea (non-contagious, pure per-resident daily hazard roll). Both
poverty-scaled via `SES_VULNERABILITY` on two independent axes:
incidence and fatality.

**First version shipped with zero post-recovery immunity** — the
reasoning at the time was that "common" ailments shouldn't behave like
the big epidemic's one-time wave, so recovery went straight back to
`healthy`. Tested on the reference town before moving on (the habit
from thread 7's assassination refinement, and more pointedly from the
"are you sure it plateaus?" lesson two threads earlier): flu alone
produced ~29,500 cases in a year and 562 deaths, more than violence +
riots + the real epidemic combined. Root cause: on a dense
~40-80-ties-per-resident graph, a same-day-reinfectable population
never runs out of susceptible neighbors the way the big epidemic's
*permanent* immunity eventually does — it wasn't 29,500 different
people, it was a few hundred cycling sick→healthy→sick all year.

Fixed with **temporary** immunity (a third per-ailment status,
`healthy`/`sick`/`immune`, with `flu_immunity_days=90` /
`diarrhea_immunity_days=30`) plus a ~75× cut to
`flu_transmission_rate` (the original number was picked with no regard
for how densely-tied the reference town is — the same category of
mistake violence's own `base_rate` needed degree-normalization for,
years earlier in this project). Re-verified: flu settled to 354
cases/year (1 death), diarrhea to 1,628 cases/year (31 deaths) —
comparable to the town's other minor death sources now, not dominating
them. `demo.py`'s violence-death accounting subtracted
`flu_deaths + diarrhea_deaths` from the start this time, not
discovered as a gap afterward.

Twelve new tests in `tests/test_ailments.py` (including one
specifically for the immune-status edge case: an immune resident can't
be reinfected through a contagious edge). `docs/decisions.md` records
both the zero-immunity mistake and the fix, same discipline as the
thief-plateau incident — the log shows what was tried and found wrong,
not just the final answer.

## Current repo state

**Uncommitted, deliberately** — not asked for yet. `git status
--porcelain`, last checked:

```
 M Project_Vision/01-network-simulation.md
 M demo.py
 M docs/decisions.md
 M docs/plans.md
 M phenomena.py
 M tests/run_all.py
 M tests/test_riot.py
 M tests/test_violence.py
?? Project-Memory/2026-09-21-criminals-slice-and-feedback-loop.md
?? docs/feedback.md
?? tests/test_ailments.py
?? tests/test_theft.py
```

`tests/run_all.py` → `ALL OK` as of this writing (12 modules, new
`test_ailments`). Ask before committing. Dashboard has gone through
several refreshes this session (currently version 13, which adds
the common-ailments card/chart from thread 9 and drops the Black
Death scenario per direct request) — up to date as of this writing.

Earlier in the session (while pulling data for an intermediate
dashboard refresh), found and fixed one more instance of the same bug
class as the rioter-death miscount: `demo.py`'s violence-death count
didn't subtract `thefts_executed` either (executed thieves die but
weren't counted anywhere) — a 9-death discrepancy between the printed
"violence: 116" and the actual 107 `violence: violence` events gave it
away. Fixed the same way, and added an `executed:` field to the theft
print line so this stays visible.

## What's next

`docs/plans.md`'s resume checklist includes reading `docs/feedback.md`'s
open entries first thing. Criminals' queue is down to one item: **group
violence** (the bottom-up riot trigger — enough people sharing high
animosity toward the same target, with enough affinity among
themselves, can attempt a killing together, escalating directly into a
riot if enough band together). This is a bigger, more architecturally
significant piece than the last few — `docs/plans.md` itself flags it as
needing deliberate design (plugging into `RiotPhenomenon._active_riot`'s
existing state machine rather than inventing a second riot concept)
rather than bolting on after the fact, so it deserves its own scoping
pass, not a rushed extension. Also still open: the documentation-only
backlog from the first feedback round (Economy & poverty section:
income, beggars, hardship death, ambient sickness; Romance rebalance;
Stress trait). The Economy & poverty section doesn't have an owner topic
yet — worth deciding whether it becomes its own phenomenon or extends
existing ones (Criminals, Contagion) before writing code. Also worth a
second look: whether the
30-seed-aggregate verification pattern used here (isolate the one
phenomenon being checked, not the full 6-phenomenon engine) should be
written down as a standing practice, given the full-engine version
stalled badly on this environment's slow single-threaded Python.
