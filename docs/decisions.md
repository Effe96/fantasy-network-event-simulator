# Decisions Log

> **What this file is for.** `docs/2026-09-15-social-network-design.md`
> describes *what* each mechanic does and *how* — formulas, plain-language
> explanations, worked examples. This file records *why* a choice was
> made the way it was: the constraint that forced it, the alternative
> that was rejected and why, the calibration number that turned out wrong
> and what fixed it. Read this before re-litigating a decision or
> "fixing" something that was already deliberately chosen. Newest first.

## 2026-09-22 — Priests' corruption, reusing bribery's shape on the same edge/roll as devotion and friction

**Decision:** `ReligionPhenomenon` gains a `corruption` event alongside
`devotion`/`friction`, scoped exactly as `docs/plans.md` specified —
"reuses the bribery *pattern*... rather than reinventing it." A
civilian pays a priest for favorable treatment, scaled by the
civilian's own `cunning` and wealth (`BRIBE_WEALTH_FACTOR`, the same
constant `GuardPhenomenon` and `TheftPhenomenon` already reuse) and
restrained by the priest's own `loyalty` — exactly `GuardPhenomenon`'s
"a more loyal [authority figure] refuses more often" formula, no new
"integrity" trait needed despite the plan's wording suggesting one.
Only the priest's own outgoing valence toward the payer moves, same
one-directional favor shape bribery and devotion both use.

**Why it shares a roll with devotion/friction, not a separate one:**
corruption fires on the exact same civilian-priest edge devotion/
friction already use. Rather than running two independent per-edge
probability checks on one edge (which the `Phenomenon` protocol doesn't
support — `edge_probability` returns one float), `edge_probability`
returns the *sum* of the faith probability (devotion or friction,
whichever applies) and the corruption probability, and `apply_effect`
draws which one actually fired via a weighted coin flip
(`corruption_p / total`) — the same pattern `ViolencePhenomenon`'s
`_pick_aggressor` already uses to resolve which of two outcomes wins a
shared roll, reused rather than invented fresh.

**Verified on a real run:** 67 devotions / 7 frictions / 4 corruptions
(down from 98/11/0 before corruption existed, since corruption now
claims a share of the same probability budget rather than adding on
top) — a modest, real number, not a runaway, consistent with
corruption being deliberately set rarer than devotion
(`corruption_base_rate=0.005` vs `devotion_base_rate=0.01`).

## 2026-09-22 — Priests' first slice: religious devotion + skepticism (`ReligionPhenomenon`)

**Decision:** scoped to the vision doc's first Priests bullet only —
"religious town → broad affinity boost from most residents; a small,
deliberately-chosen set of heretics/skeptics get an animosity boost
instead" — same pattern Guards (bribery-only) and Criminals (thief
occupation + theft only) used for their own first slices. Corruption
(priests accepting payment, likely reusing bribery's shape) and priests
as disease-curers (needs a cross-phenomenon link to Contagion's death
toll that doesn't exist yet) are deferred.

Fires per edge, only between a civilian and a priest (`Node.role`
already returns `"priest"` for the `priest`/`acolyte` occupations — no
new field needed). Most civilians' own affinity toward priests they know
grows slowly, scaled by their own `religiousness` — a `devotion` event,
the second concrete instance of the "favor" event type after bribery,
same one-directional shape (only the civilian's own outgoing valence
moves, not the priest's). A small minority — `skepticism >
heretic_skepticism_threshold` (0.8, ~7.7% of civilians at the trait's
default Gaussian(0.5, 0.2) distribution, confirmed by counting on the
real reference town rather than assuming) — feel the opposite: their own
affinity erodes instead, scaled by their own skepticism (a `friction`
event). Which bucket a civilian falls into is decided once in
`init_state`, not re-rolled daily, same "sticky, not recomputed" shape
`TheftPhenomenon`'s `is_thief` flag uses.

**Why checked against the real graph before picking defaults:** per
[[feedback-check-thresholds-against-real-graph-density]] — the reference
town has only 4 priests and 313 civilian-priest edges total (guards, by
contrast, have 40 guards and 3,166 civilian-guard edges), so this
mechanic's raw event volume was never going to be large regardless of
rate tuning; picked `devotion_base_rate`/`friction_base_rate` an order
of magnitude above bribery's (0.01 vs 0.001) to compensate for the much
smaller edge pool, then verified on a real run rather than assuming the
guess was right. Result: 98 devotions / 11 frictions in a year — a
modest, believable trickle across ~288 devotee-eligible and ~24
heretic-eligible edges, not a runaway (no repeat of common ailments' or
group violence's first-version bugs) and not silent either.

**Noted, not a bug:** riot counts shifted from the last reference run (6
→ 9, group-escalated/organic split 3/3 → 8/1) purely because
`ReligionPhenomenon` was inserted into `demo.py`'s phenomena list —
every phenomenon shares one `random.Random` instance threaded
sequentially through the whole day loop (`engine.run_simulation`), so
adding any new phenomenon's `rng.random()` calls reshuffles every
downstream draw for the rest of the run, same property that's shifted
calibration numbers between sessions before. The total (9) stays in the
same believable order of magnitude as the prior run (6), so this reads
as ordinary single-seed variance, not a regression in the group-violence
fix — a multi-seed check would be the way to confirm that rigorously if
it becomes a live question.

## 2026-09-21 — Group violence: the bottom-up riot trigger, and a runaway first version caught before shipping

**Decision:** `ViolencePhenomenon` gained a town-wide `end_of_day` check
(`_check_group_violence`) alongside its existing per-edge solo path.
Once a day, it scans every live edge for anyone hated above
`group_hate_threshold` (0.7) by more than one person, then union-finds
those haters into `band`s using `group_affinity_threshold` (0.3) mutual
ties between them — sharing a grudge alone isn't enough, they also have
to actually know and like each other. The single largest qualifying band
that day gets one `group_action_rate` (0.1) roll to see whether it
actually acts. If it does: a band below `riot_phenomenon.min_participants`
attempts a joint killing, success chance boosted by `sqrt(len(band))`
over the same solo-assassination formula (reusing `SES_VULNERABILITY`
both ways, `success_base_rate`); a band *at or above* that size skips the
kill roll entirely and becomes a riot instead, via a new
`RiotPhenomenon._begin_riot` factored out of `_start_riot`'s own tail —
this is the bottom-up riot trigger flagged "not yet built" in the design
doc, reusing the existing riot state machine directly rather than
inventing a second one (per `docs/plans.md`'s explicit instruction).
`ViolencePhenomenon` is constructed with an optional `riot_phenomenon`
reference (wired in `demo.py`, which now builds `riot` before `violence`)
— the first deliberate case of one phenomenon reaching directly into
another's state, previously flagged as a missing capability (Guards'
patron protection was blocked on the same gap).

**Why a two-stage gate, not just tuned thresholds:** a first version had
neither `group_action_rate` nor thresholds this strict
(`group_hate_threshold=0.4`, `group_affinity_threshold=0.15` — both
picked as "sounds like real hostility/affinity" guesses, never checked
against the actual graph). Tested on the reference town before trusting
it, per the standing "verify with a real run" habit from the thief-
plateau and riot-lethality incidents: **345 riots in one year**, almost
all (`group_escalates_to_riot` events) traced straight back to this
mechanic — the organic baseline is ~1/year. Root cause: on this graph's
baseline relationship-valence noise alone, with zero simulated events
ever having fired, 15,248 directed edges already cross a 0.4 hostility
threshold, and some of those haters happened to be mutually tied into
bands as large as 65 people. Unlike solo violence (which has a
degree-normalized `base_rate` roll gating whether a hostile edge
actually erupts *today*), the first group-violence version was a hard
deterministic trigger: once a qualifying band existed, it always acted,
and a qualifying band existed on nearly every single day. Fixed two
ways together: (1) raised both thresholds to 0.7/0.3, where the same
day-1 scan caps out at band size 3 instead of 65; (2) added
`group_action_rate` as an explicit "does this actually boil over today"
roll, the same shape `RiotPhenomenon.riot_base_rate` already uses on top
of its own unrest threshold. Re-verified on the same town/seed: **6
riots** (3 organic, 3 group-escalated — close to doubling the organic
rate, not swamping it) and 27 group-violence kills alongside 95 solo
kills, a believable secondary channel. `tests/test_violence.py` covers
band formation (requires both hate *and* mutual affinity, not just a
shared grudge), the size-based success boost, the riot-escalation
handoff (and its absence below the size threshold or with no
`riot_phenomenon` wired in), and the action-rate gate itself.

## 2026-09-21 — Flu seasonality added; diarrhea's "indefinite growth" was a chart problem, not a model problem

**Decision:** `CommonAilmentsPhenomenon` gained a `flu_winter_multiplier`
(default 3.0) applied to both the per-edge transmission rate and the
spontaneous rate during Q4+Q1 (day-of-year <=91 or >=274, recurring every
calendar year in multi-year runs via `_flu_season_factor`). Diarrhea gets
no seasonality — the user's own framing only asked for it on flu, since
flu is airborne/contagious and diarrhea here is a plain per-resident
hazard roll.

**Why raised:** user asked "are you considering that people can recover?
It seems strange to me that the diarrhea people are just growing,
seemingly indefinitely," plus a request that flu get "higher chance and
higher contagion factor in the last quarter and first quarter of the
year."

**What was actually true before this fix:** recovery already worked —
`_resolve_ailment` has always taken `sick` → `immune` → `healthy` on a
duration/immunity timer (see the entry below), and each ailment's
*currently-sick* count already fluctuated all year (roughly 12-27 people
sick with diarrhea at once, in the seed-5/365-day reference run, not a
monotonic climb). What actually grew indefinitely was the **dashboard's**
"cumulative cases" chart line, which is a running total by definition —
plotting it made a fluctuating, recovering population look like it never
recovered. Fixed by switching that chart to show *currently sick* instead
of the cumulative counter, so the real up-and-down is visible. Full
seasonality is a genuinely new feature, not a bug fix — flu had no
calendar concept at all before this.

## 2026-09-21 — Common ailments: temporary (not permanent, not zero) immunity was the fix a runaway first version needed

**Decision:** new `CommonAilmentsPhenomenon` models flu (contagious,
edge-based transmission like `ContagionPhenomenon`, plus a small daily
spontaneous "caught it outside the tracked graph" rate) and diarrhea
(non-contagious, pure per-resident daily hazard roll, no edges at all).
Both scale by poverty on two independent axes reusing
`SES_VULNERABILITY`: the odds of getting sick, and separately the odds
of dying once sick. Recovering grants **temporary** immunity
(`flu_immunity_days=90`, `diarrhea_immunity_days=30`) — a third
per-ailment status (`healthy` / `sick` / `immune`) alongside the
existing two.

**Why:** the first version had *zero* immunity (straight back to
`healthy` on recovery, reinfectable the same day), on the theory that
"common ailments" shouldn't behave like the big epidemic's one-time
wave. Tested on the reference town before trusting it: flu alone
produced ~29,500 "cases" in a year and 562 deaths — on a ~1,900-person
town with ~40-80 ties per resident, a same-day-reinfectable population
never runs out of susceptible neighbors, unlike the big epidemic whose
*permanent* immunity eventually exhausts the susceptible pool and lets
a wave burn out. It wasn't 29,500 different people getting sick once;
it was a few hundred people cycling sick→healthy→sick every few days,
all year. Total ailment deaths (693) exceeded violence, riots, and the
real disease combined — nowhere near "common but not catastrophic."

**Fix and verification:** added a temporary immunity window (long
enough that a local wave has room to burn out before the same people
are reinfected, short enough that genuine reinfection later in the
year is still possible — unlike the epidemic model). Also cut
`flu_transmission_rate` by ~75× (0.03 → 0.0004) since the original
value was calibrated with zero regard for how densely-tied the
reference town is, the same category of mistake violence's own
`base_rate` needed degree-normalization for. Re-ran the reference
town: flu settled to 354 cases/year (1 death), diarrhea to 1,628
cases/year (31 deaths) — comparable in scale to the town's other minor
death sources, not dominating them.

**How to apply:** `demo.py`'s violence-death accounting was extended
to subtract `flu_deaths + diarrhea_deaths` from the start this time
(not discovered as a bug afterward, unlike the riot/execution gaps
earlier this session) — see the `ailment_deaths` variable. If either
ailment's total case count needs retuning later, the immunity-window
knobs (`*_immunity_days`) are now the primary lever for *how often* a
given resident can get sick again, separate from `*_spontaneous_rate`
(how easily a wave gets started) and `*_transmission_rate` (how fast it
spreads once started) — conflating these was part of what made the
first version hard to reason about.

## 2026-09-21 — Assassination refinement: reused SES_VULNERABILITY for both attacker and victim

**Decision:** `ViolencePhenomenon.apply_effect` now rolls a success
chance before killing anyone: `min(1.0, success_base_rate *
victim_vulnerability / attacker_vulnerability)`, using the existing
`SES_VULNERABILITY` dict for both — victim's value in the numerator
(poorer victims easier to actually kill, same direction
`_pick_aggressor`'s weighting already uses), attacker's value in the
denominator, inverted (a rich attacker's resources make success easier,
a poor attacker's lack of them makes it harder). A failed attempt never
kills; the surviving victim's own valence toward the culprit drops by
`discovery_shock` instead, and no `grief_shock` fires (nobody died).

**Why:** next item in `docs/plans.md`'s Criminals queue, scoped exactly
as written there: "extends `ViolencePhenomenon`, not a new phenomenon
... reuses `SES_VULNERABILITY` machinery already in place." Defaults
(`success_base_rate=0.85`, `discovery_shock=0.5`) were chosen so
same-class violence (the common case) stays close to the old
guaranteed-kill behavior, while a poor-attacker-vs-rich-victim attempt
succeeds only ~21% of the time and the reverse very nearly always
succeeds (formula would exceed 1.0 there, clamped). Verified on a real
run: 24 failed attempts out of 109 total violence attempts (~22%), no
crashes, `demo.py`'s existing violence-death accounting needed no
changes since a failed attempt never touches `alive`/`dead`.

**How to apply:** "discovery" was scoped to the surviving victim's own
reaction only, not a town-wide alert or a guard notification — the
vision doc's fuller version of this (tying into guards, or triggering
consequences beyond the victim) still needs the same cross-phenomenon
event link Guards' patron-protection has been blocked on all along, not
built here. Tests: `tests/test_violence.py`'s
`test_poor_attacker_vs_rich_victim_succeeds_less_often_than_the_reverse`
and `test_failed_attempt_leaves_victim_alive_and_drops_their_valence_toward_culprit`.

## 2026-09-21 — Riot lethality: linear size-ratio formula replaced with sqrt, guard:rioter ratio fixed

**Decision:** `_advance_riot`'s per-day death-chance formula changed from
`lethality * (opposing_count / own_count)` to
`lethality * sqrt(opposing_count / own_count)` on both sides.
`guard_lethality` dropped from 0.3 to 0.2 (kept `rioter_lethality` at
0.6, i.e. still a 3:1 ratio). Under the new formula, total expected
guard deaths and total expected rioter deaths both reduce to
`lethality * sqrt(guards * rioters)` — the same size factor for both —
so the guard:rioter **casualty ratio** comes out to exactly
`guard_lethality:rioter_lethality`, independent of how the mob's size
compares to the guard corps.

**Why:** the 2026-09-17 entry below already flagged the ratio as
miscalibrated in *magnitude* and deferred a fix. 2026-09-21 user
feedback re-raised it with a concrete example (24 guards died vs. 22
rioters on a real run — guards dying *more*). Before touching constants,
verified with real data rather than trusting a single sample: a 30-seed
aggregate under the **old** formula came back 649 guard deaths vs. 539
rioter deaths (ratio 1.204, guards dying more) — confirming a real,
systematic bug, not noise from one unlucky run. Root cause: the old
linear formula makes each side's *total* expected daily deaths equal to
`lethality * (opposing side's raw headcount)`, completely independent of
your own side's headcount. Since rioters are drawn from the whole town
but the guard corps is small and fixed (~40 in the reference town), a
merely-somewhat-larger-than-usual mob was enough to make guard casualties
(driven by the *mob's* size, effectively unbounded) swamp rioter
casualties (capped by the guard corps' small fixed size) — regardless of
the 2x/3x lethality edge the constants were meant to express. The sqrt
formula decouples "who wins per casualty" (purely the lethality
constants) from "how large is the mob" (which now only paces the
absolute magnitude of casualties, via `sqrt(guards*rioters)`, not the
ratio between the two sides).

**Verification:** re-ran the same 30-seed aggregate under the new
formula: 381 guard deaths vs. 1,036 rioter deaths (ratio 0.368) — close
to the 0.333 (1:3) target, across 36 riots. Added
`tests/test_riot.py::test_guards_die_less_often_than_rioters_regardless_of_mob_size`,
which runs the same "matched vs. lopsided mob size" comparison as a
permanent regression test (replaces the old
`test_guards_die_less_often_than_rioters_at_equal_force_size`, which
only checked the equal-counts case and manually reimplemented the
formula rather than exercising the real code path — it would have kept
passing even with the old bug in place, since equal counts made both
formulas coincide).

**How to apply:** the retreat-threshold and riot-bar mechanics are
unaffected (they're still fractions of initial headcounts, unrelated to
this formula). Guards may now hold slightly longer before retreating
than they used to, since per-day guard casualties are lower — a
plausible, not-yet-separately-verified side effect. If lethality
constants are touched again, remember the *ratio* between
`guard_lethality`/`rioter_lethality` is now what directly sets the
casualty ratio — no need to also account for typical mob:guard size
mismatches the way the old formula required.

## 2026-09-21 — Thief occupation is a sticky per-resident flag, not a Node field or a daily recompute

**Decision:** `TheftPhenomenon` tracks `is_thief` in its own per-resident
state dict, flipped once by a poverty-scaled roll in `end_of_day` (same
shape as `RomancePhenomenon`'s `married` flag) and never re-evaluated
afterward. Not a new `Node` field, and not a status derived fresh from
current circumstances each day.

**Why:** `docs/plans.md` flagged this as an open question to resolve
before coding, leaning toward the sticky-flag option to match the
project's established pattern (state a phenomenon tracks) over adding
graph schema. No new information changed that lean, so it's now decided
rather than re-litigated.

**How to apply:** if a later slice needs thieves to "reform" or stop
being thieves, that's a new transition to add explicitly (like Romance
has no divorce yet) — don't assume the flag re-evaluates on its own.
Scope for this slice was thief occupation + theft only; assassination
refinement and group-violence-as-riot-trigger (`docs/plans.md`'s other
two Criminals items) are still queued next.

## 2026-09-21 — Thief population plateau, take two: arrest had to stop depending on local guard adjacency

**Decision:** `TheftPhenomenon.arrest_chance` is now a flat, town-wide
probability applied to every caught thief, no longer scaled by (or
gated on) whether the thief happens to have a guard *neighbor* in the
social graph. The execution-vs-arrest split now reads a precomputed
town-wide average guard loyalty (`self._avg_guard_loyalty`, set once in
`init_state`), not the loyalty of whichever guards happen to be
adjacent. The local guard-neighbor valence hit (guards *you know*
getting angrier at you) is unchanged — only whether an arrest actually
happens stopped depending on it.

**Why — this corrects the same day's earlier decision, below.** That
first version gated arrest on having a guard neighbor at all. Asked
directly "are you sure it plateaus?", a 3-year run was checked (not
just the 1-year trajectory the first version was verified against) and
the population had gone 94 → 221 thieves from year 1 to year 3 — still
climbing at essentially the same ~0.2/day rate as year 1, no
deceleration at all. Digging in: only 20 of 195 caught thieves (10%)
in year 1 actually got arrested or executed, because with only ~40
guards among 1,911 residents, most caught thieves simply never had a
guard neighbor to trigger the old mechanism — the removal pipeline was
too weak for deterrence to ever meaningfully suppress inflow. The
original "77→78, looks flat" read from a 1-year single-seed trajectory
was real but misleading: short-window noise, not convergence. Worth
recording plainly: **the first fix was verified on too short a horizon
and the claim of success was wrong** — see `docs/plans.md` for how this
was caught.

**Verification, this time on a 2-year run:** removal rate rose from
10% to 43% of catches (68 arrests + 27 executions out of 221 catches
by day 730). The day-by-day trajectory now shows genuine fluctuation,
including several real *declines* (day 90→120: 28→27 thieves; 150→180:
36→34; 240→270: 41→40; 500→550: 65→64; 550→600: 64→63) — mathematically
only possible when removals outpace new thieves in that window, which
never happened even once under the old mechanism. Year-1 average ≈36,
year-2 average ≈66 — still trending up overall but far more slowly, and
not yet confirmed fully converged by day 730 (a further, more expensive
long run would be needed to nail down the exact equilibrium level;
not run, given how costly runs are in this environment — see the
isolate-phenomena-for-diagnostics note in Claude's own memory for why
full multi-year full-engine runs are expensive here).

**How to apply:** don't trust a 1-year (or shorter) single-seed
trajectory as proof of convergence for any similar negative-feedback
mechanic in this codebase again — check a multi-year run, and ideally
multiple seeds, before claiming a rate "settles." If the equilibrium
level (currently drifting somewhere in the 70s-90s by year 2) needs to
be pinned down further or brought down, `arrest_chance` and
`deterrence_weight` are the two most direct knobs — `become_thief_rate`
mostly just shifts how fast the climb starts, not where it settles.

## 2026-09-17 — Push scope: Project_Vision stays out of what gets pushed going forward

**Decision:** `Project_Vision/01-network-simulation.md` (the roadmap/
"ideas" file) shouldn't be included in future commits that get pushed to
the remote, on the user's explicit request. Existing history that already
contains it is left alone — rewriting 12+ already-local commits to strip
it out would be a destructive history rewrite, not requested and not
worth the risk for a working-notes file.

**Why:** the user's own words: "commit and push. Do not push the ideas
files (product vision) please." Confirmed via a direct question that this
applies going forward, not retroactively to already-committed history.

**How to apply:** when staging a commit that's about to be pushed, check
whether `Project_Vision/` changes are part of it and hold them back
(commit separately, don't push that commit, or just don't stage them)
unless told otherwise. `docs/` (this file and the design doc) and code
changes are fine to push.

## 2026-09-17 — Riot mutual-combat calibration is right in shape, wrong in magnitude

**Decision:** keep `guard_lethality=0.3` / `rioter_lethality=0.6` for now
(guards safer per capita, as intended) even though the emergent
guard:rioter death ratio on a real run (~11:18) doesn't match the user's
stated target of roughly **1 guard dead per 3 rioters dead**. Recorded as
a known gap rather than fixed immediately.

**Why:** the user flagged the target ratio directly but said "we can
change it in a future iteration, but I want it remembered" — explicitly
deferring the retune rather than asking for it now.

**How to apply:** next time riot combat is touched, retune the lethality
constants (or their ratio) against real runs until guard:rioter deaths
land near 1:3, and update the worked example in the design doc §12.2 to
match the new numbers.

## 2026-09-17 — Riot combat: simultaneous rolls, not sequential-with-early-exit

**Decision:** guards and rioters both roll for casualties every day using
that day's *starting* counts, with retreat/rout checked once at the end
of the day — replacing an earlier version that processed guards first in
a loop with an early exit the moment they retreated.

**Why:** the sequential version meant rioters were only ever exposed to
risk on days guards *didn't* break — and guards almost always broke
within the first day at default lethality (many independent rolls, real
chance to hit, all resolved in one call before retreat was even
checked). In practice this meant rioters took zero casualties, ever. User
feedback directly named the symptom: "how many of the rioters died? that
should also be taken into account."

**Alternative considered and rejected:** keep sequential processing but
give rioters their own separate loop that always runs regardless of
guard outcome. Rejected because it would double-process the "did guards
retreat" check awkwardly and doesn't fix the deeper issue — the point is
both sides should face the *same day's* fight, not staggered ones.

## 2026-09-17 — Riot retreat/rout thresholds scale by trait, not a flat constant

**Decision:** guards' retreat threshold scales with their own average
`loyalty` (`retreat_threshold * (0.5 + avg_guard_loyalty)`); rioters' rout
threshold scales the same way but by their own average worst-grievance
hostility at the moment they joined. `0.5` (the loyalty trait's own
default mean) is the pivot, so an average-loyalty garrison reproduces the
plain constant unchanged.

**Why:** two rounds of direct user feedback. First: "how likely it is
that guards are going to retreat... should depend on loyalty." Then,
extending the same idea to the other side: "if enough rioters die, the
others should escape (threshold should be based on the level of
animosity)."

**Alternative considered and rejected:** a single shared "morale" stat
covering both sides. Rejected — guards' willingness to hold and rioters'
willingness to keep fighting are driven by different things (professional
loyalty vs. personal grievance) and the existing personal traits already
model exactly this distinction; reusing `loyalty` and rederiving
`hostility` from data already on the graph is more honest than inventing
a new unified stat.

## 2026-09-17 — Riots persist as multi-day state, not an atomic one-shot

**Decision:** a riot is `self._active_riot`, live across as many days as
it takes to resolve, rather than one `end_of_day` call doing everything
(guard deaths, retreat, noble deaths) atomically.

**Why:** the atomic version had no real *stopping condition* — it
"stopped" only because the Python function returned that day. User asked
directly: "why did the riot stop?" — and pointed out nobles' deaths
should deplete a real, observable quota ("when this riot bar reaches
zero then the riot is stopped"), which requires state that survives
across days.

**How to apply:** any future riot-adjacent mechanic (Criminals' "group
violence escalates into a riot," a resolution-phase valence shift) needs
to either plug into this existing state machine or justify why it needs
its own.

## 2026-09-17 — Guard bribery recalibrated: loyalty restraint + 10× lower base rate

**Decision:** `GuardPhenomenon.edge_probability` now multiplies by
`(1 - guard.loyalty)`, and `bribe_base_rate` dropped from `0.01` to
`0.001`.

**Why:** the first version produced ~471 bribes/year on the reference
town. User: "that number is very, very high... that number should exist
only in a low loyalty, high corruption city. Make acceptance of bribes
lower, far lower." Combined, the two changes bring the reference town to
~8–25/year depending on seed.

**Known limitation, not yet addressed:** loyalty alone only gives about a
2× town-to-town swing (it's bounded to `[0,1]`), which isn't enough to
make a *genuinely* corrupt town look dramatically different from an
ordinary one. A real contrast likely needs the town-wide **corruption**
parameter already on the roadmap (distinct from personal loyalty) to
multiply this rate too. Flagged in the design doc §13, not built.

## 2026-09-16 — Riot's unrest threshold sat on the town's natural baseline

**Decision:** `unrest_threshold` dropped from `0.25` to `0.15`;
`riot_base_rate` raised from `0.02` to `0.03`.

**Why:** the reference town's actual baseline civilian-to-authority
hostility measured ~0.25–0.26 across several seeds — almost exactly on
top of the old threshold. Since the daily trigger probability scales with
how far hostility sits *above* the threshold, a near-zero margin gave
near-zero odds; riots were technically possible but unreachable within a
normal year. Several seeds in a row showing zero riots is what surfaced
this — the user asked directly whether triggering was actually broken.

**How it was actually diagnosed** (worth remembering as a method, not
just a result): isolated the trigger roll from the full simulation using
a fresh RNG stream with no other phenomena consuming draws first, and ran
30 independent year-long trials. 20 of 30 fired — confirming the
*mechanism* was fine and the problem was purely calibration (the
threshold's margin against the measured baseline), not a logic bug. Don't
skip this isolation step when debugging "an event never seems to fire" —
the shared RNG stream across phenomena makes a single full-simulation
run a poor way to tell "broken" from "just unlucky."

## 2026-09-16 — Guards and Nobles are individual named residents, not a class-wide relationship

**Decision:** `GuardPhenomenon`/`RiotPhenomenon` mechanics operate over
real edges to actual `role == "guard"`/`"noble"` residents (~40 each on
the reference town), not an abstract "the guards as an institution" tie
that every resident has one of.

**Why:** the vision doc's original framing describes guards as "something
closer to a shared public relationship than individual people." But every
other implemented phenomenon (violence, romance) operates over real
edges between real residents — introducing a parallel abstract-institution
data model just for Guards would be a second, inconsistent way of
representing "how a civilian feels about authority" alongside the
edge-based hostility Riots already needed to compute its trigger. Riots'
defense side still treats *all* living guards as town-wide defenders
(guards are public figures) even without a personal connection — that's
the concession to "shared public relationship" that was actually needed;
a full separate data model wasn't.

**Revisit if:** a future mechanic genuinely needs "how does resident X
feel about guards as an institution" as a single scalar independent of
which specific guards they happen to know (e.g. a townwide loyalty-to-
authorities metric feeding into the town-wide parameters section).

## 2026-09-16 — Guards scoped to bribery only

**Decision:** `GuardPhenomenon` v1 implements bribery and nothing else
from the vision doc's Guards section (arrest behavior, patron protection,
built-in noble/poor skew).

**Why:** arrest behavior needs a crime to react to (Criminals doesn't
exist), and patron protection needs Guards to observe what Violence
produced (no cross-phenomenon event bus exists — phenomena don't see each
other's output today). Building either as a half-measure would mean
inventing a fake trigger just to have *something*. Bribery is fully
self-contained: it only needs an edge, a civilian's traits, and a guard's
loyalty, all of which already exist.

## 2026-09-16 — Births are log-only; no new Node yet

**Decision:** `RomancePhenomenon` records a birth as an `Event` only. No
child `Node` is added to the graph.

**Why:** every other phenomenon's per-resident state dict is built once
at `init_state` (day 0) and indexed directly by resident id for the rest
of the run. A resident appearing mid-simulation would `KeyError` the
first time the engine tried `state[new_id]` for any *other* phenomenon's
edges touching that child. Fixing this properly means adding a
`Phenomenon.default_state(resident_id)` hook (or similar) so every
phenomenon can produce a sane starting state for someone who joined after
day 0 — a real interface change across every phenomenon, not a one-file
tweak. Deliberately deferred rather than half-built (the user was asked
directly and chose "log-only births now" over the fuller version).

**Revisit when:** family-tie derivation (grandparent/aunt-uncle/cousin)
actually needs real multi-generation chains to work with — see the next
entry.

## 2026-09-16 — Multi-generational family ties: checked, not viable yet

**Decision:** did not implement grandparent/aunt-uncle/cousin derivation,
despite it being on the roadmap.

**Why:** checked empirically against a real snapshot before writing any
code — TownShape's own `parent` edges are strictly household-scoped
(recorded only between an adult and a *currently cohabiting* minor
child); an adult who's grown up and moved out never appears as anyone's
"child" in the `relationships` table anymore. Real count on the reference
town: 1842 `parent` edges, 1463 `sibling` edges, **zero** cases of a
parent who is themselves someone's recorded child. Building derivation
logic against zero real chains would be untestable dead code.

**How to apply:** revisit once Romance's births produce real `Node`s
(see above) and a long-enough simulation lets those children grow up and
have kids of their own — at that point genuine multi-generation chains
will exist in *this project's own* graph to derive from, independent of
TownShape's data gap.

## 2026-09-16 — Romance is edge-based; two unconnected singles can never meet

**Decision:** marriage only fires on an existing edge between two
eligible residents. No "stranger meets stranger" mechanic creates a new
tie.

**Why:** consistent with the project-wide rule that no phenomenon invents
a graph edge that wasn't already there (§6.3 of the design doc). Also
just simpler for a v1.

**Known consequence, documented so it isn't mistaken for a bug:** on the
reference town, 337 of ~1,911 residents are already married at import,
leaving only ~140 unmarried adults, and pairs among those who are *both*
unmarried, already connected, *and* mutually smitten are rare — often
just 1 such pair town-wide per year. **~0–2 new marriages/year is the
correct result of this data, not underfiring.** Resist the urge to raise
`marriage_base_rate` to compensate; the actual bottleneck is structural
(no way for strangers to meet), not the rate.

## 2026-09-16 — Town aggression reuses TownShape's own parameter

**Decision:** `SocialGraph.town_aggression` reads `town_state.aggression`
directly from the TownShape snapshot rather than inventing a new
town-wide dial.

**Why:** checked TownShape's own source (`town_db/unrest.py`,
`town_narrative/parameters.py`) before proposing anything new —
`aggression` (0–1, default 0.0) already exists and already drives
TownShape's own skirmish-event generation. Inventing a parallel parameter
here would fork what should be one town-wide fact into two, and TownShape
generation runs would have no way to set the one this project actually
reads.

## 2026-09-16 — Personal traits: flat synthesis, one consumer to start

**Decision:** `religiousness`/`cunning`/`skepticism`/`loyalty` are all
drawn independently (`gauss(0.5, 0.2)`, uncorrelated with `ses` or each
other) at import, and only `loyalty` was wired into a real mechanic
(violence's aggressor restraint) when the traits were first added.

**Why:** the user was asked directly whether to add all four traits now
(most with no consumer yet) or add them one at a time as each gets a real
use. Chose "all four now" — matches the vision doc's framing of them as
one coherent system — but explicitly kept the *consumer* scope to one
trait, one mechanic, avoiding speculative behavior for traits with no
phenomenon to drive yet.

**Revisit when:** Priests exists (consumes `religiousness`/`skepticism`);
Criminals exists (consumes `cunning` for crime-success odds, alongside
Guards' existing use of it for bribery).

## Earlier decisions (pre-dating this log; see Project-Memory for full narrative)

- **Valence is directional** (`valence_a_to_b`/`valence_b_to_a`, not one
  shared number) — a real bug fix, not a stylistic choice: the user
  pointed out that a specific violence event's victim/aggressor pick
  couldn't be explained by a single shared valence, since "how A feels
  about B" and "how B feels about A" were structurally the same number
  before this fix. See design doc §3.3 and
  `Project-Memory/2026-09-16-v1-build-and-directed-animosity.md`.
- **`SES_VULNERABILITY = {poor: 2.0, middling: 1.0, rich: 0.5}`** is a
  deliberately simple placeholder (`ponytail:` comment in `phenomena.py`)
  for how a resident's class affects their odds in violence and disease
  fatality alike — swap for a real model if "good enough" stops being
  good enough. Already burned once by not checking the *effective* rate
  it produces (see design doc §7's Black Death worked example) — always
  check the per-SES-bracket effective rate when tuning anything this
  weighting touches, not just the raw input number.
- **This project never writes back to TownShape.** Read-only from day
  one, enforced at the SQL connection level (`?mode=ro`). Any future
  integration (e.g. recording bribes as real economic transactions — see
  design doc §13) is a deliberately separate, not-yet-built concern.
