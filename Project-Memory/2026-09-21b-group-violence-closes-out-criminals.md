# Resumed after a crash: committed the prior session's work, then built group violence — Criminals is now fully closed out

### Continuation of the same day's work described in `2026-09-21-criminals-slice-and-feedback-loop.md` (read that first for the full history leading up to this). That session ended with a large batch of completed, tested work sitting uncommitted, and Criminals' queue down to one item: group violence. This session's computer turned off mid-work; on resume, verified nothing was lost (tests still `ALL OK`, working tree unchanged), committed the prior batch (two commits: code+tests, then docs — see `183c6ac` and `894fc7c`), then built and shipped group violence.

## What this session did

### 1. Verified and committed the prior session's work

Before touching anything new: re-ran `tests/run_all.py` (`ALL OK`, 12
modules), re-read the live dashboard artifact directly (not trusted from
a note) to confirm it was actually current, and confirmed
`docs/feedback.md` had no truly-open entries left. Asked the user
whether to commit the pending batch before starting new work — they said
yes. Split into two commits: `183c6ac` (phenomena.py, demo.py, all test
files — theft, thief deterrence, riot lethality fix, assassination
refinement, common ailments) and `894fc7c` (docs/decisions.md,
docs/plans.md, docs/feedback.md, Project_Vision, Project-Memory). Also
added `output_*/` to `.gitignore` (the untracked `output_riverport/` run
directory).

### 2. Group violence (`ViolencePhenomenon`) — the bottom-up riot trigger

Per `docs/plans.md`'s scoping note ("plug into `RiotPhenomenon`'s
existing `_active_riot` state machine... rather than inventing a second
riot concept"): added a town-wide `end_of_day` check to
`ViolencePhenomenon`, alongside its existing per-edge solo path. Once a
day, scans every live edge for anyone hated above `group_hate_threshold`
by two or more people, then union-finds those haters into `band`s using
`group_affinity_threshold` mutual ties between them — sharing a grudge
alone isn't enough, they also have to know and like each other. The
single largest qualifying band per day gets one `group_action_rate` roll
to see whether it acts. If it does: a band below
`riot_phenomenon.min_participants` attempts a joint killing (success
chance boosted by `sqrt(len(band))` over the same solo-assassination
formula); a band at or above that size skips the kill roll entirely and
becomes a riot instead.

The riot side needed a real refactor: extracted `RiotPhenomenon.
_begin_riot` from `_start_riot`'s own tail (guard lookup, retreat
thresholds, `self._active_riot` assignment) so a pre-formed participant
list from group violence can start a riot directly, reusing the same
state machine. `avg_participant_hostility` (needed for the mob's own
retreat threshold) is now an explicit parameter to `_begin_riot` rather
than something only `_start_riot` knew how to compute, since a
group-violence band's "how angry was it" measure (hostility toward the
shared target) differs from an organic riot's (worst grievance toward an
authority figure). `ViolencePhenomenon` takes an optional
`riot_phenomenon` reference, wired in `demo.py` (which now constructs
`riot` before `violence`) — the first time in this project one
phenomenon reaches directly into another's state, a capability
previously flagged as missing (Guards' patron protection was blocked on
the same gap).

### 3. A real runaway, caught before shipping — same discipline as the thief-plateau and riot-lethality incidents

Tested on the reference town before trusting the first version
(`group_hate_threshold=0.4`, `group_affinity_threshold=0.15`, picked as
"sounds like real hostility/affinity" guesses, no probabilistic gate at
all): **345 riots in one year**, organic baseline is ~1/year. Root
cause, found via `_find_band`'s own instrumentation: on this graph's
baseline relationship-valence noise alone, with zero simulated events
ever having fired, 15,248 directed edges already exceed 0.4 hostility,
and some resulting bands reached 65 people. Unlike solo violence (which
has a degree-normalized `base_rate` roll dampening whether a hostile
edge erupts *today*), the first group-violence version was a hard
deterministic trigger — a qualifying band existed on nearly every day
and always acted.

Fixed two ways together, found by sweeping parameters against the real
graph (isolated to just `ViolencePhenomenon` + `RiotPhenomenon`, not the
full 7-phenomenon engine — the standing practice from
[[feedback-isolate-phenomena-for-diagnostics]]): raised both thresholds
to 0.7/0.3 (where the same day-1 scan caps out at band size 3, not 65),
and added `group_action_rate=0.1` as an explicit "does this actually
boil over today" roll, the same shape `RiotPhenomenon.riot_base_rate`
already uses. Re-verified on the full 7-phenomenon engine: 6 riots (3
organic — 36 to 100 participants, able to push guards back and expose
nobles — and 3 group-escalated — exactly 3 people each, crushed the same
day they formed against the full ~40-strong guard corps) and 27 group
kills alongside 95 solo kills, a believable secondary channel, not a
dominant one.

This is the fourth time in this project a hand-picked threshold has been
wrong in the same way (violence's `base_rate`, flu's transmission rate,
riots' `unrest_threshold`, now this) — wrote it up as a standing memory,
[[feedback-check-thresholds-against-real-graph-density]], since it will
keep recurring for Priests/Nobles' animosity triggers next.

### 4. Tests, docs, dashboard

`tests/test_violence.py` gained 9 new tests: band formation requires
both hate *and* mutual affinity (two separate negative cases — no tie at
all, and mutual dislike), a forced-success kill, the size-boosted
success-chance scaling (statistical, 200 trials each at two band sizes),
the failed-attempt valence hit to every band member, the riot-escalation
handoff (and its absence below the size threshold, and with no
`riot_phenomenon` wired in), and the action-rate gate itself.
`docs/decisions.md`, `docs/plans.md`, and `Project_Vision`'s Criminals
and Riots sections all updated — Criminals' scope from the vision doc is
now fully implemented, Priests is next per the build order.

Refreshed the living dashboard artifact (version 14,
`https://claude.ai/artifact/1xczPUnjNSfKa5DfasTcDQ`) against the same
reference town/seed: new DATA/EVENTS from a fresh `demo.py` run,
updated KPIs, a new case-study card (with a log-scale before/after riots
chart for the 345→6 fix), and a rewritten Riots section describing the
actual 6-riot year instead of the stale "this run's one riot" text.

## Current repo state

Two new commits on top of the prior session's two (`183c6ac`,
`894fc7c`), same discipline — ask before committing further. Not yet
committed as of this writing (see "What's next").

```
 M Project_Vision/01-network-simulation.md
 M demo.py
 M docs/decisions.md
 M docs/plans.md
 M phenomena.py
 M tests/test_violence.py
?? Project-Memory/2026-09-21b-group-violence-closes-out-criminals.md
```

(`.gitignore`'s `output_*/` addition landed in the prior batch's first
commit, `183c6ac` — already committed, not part of this diff.)

`tests/run_all.py` → `ALL OK` (12 modules, `test_violence` now has 19
tests). `output_riverport/` regenerated but gitignored.

## What's next

Criminals is fully closed out. `docs/plans.md`'s build order says
**Priests** next: religious town → broad affinity boost, with a small
deliberately-chosen heretic/skeptic minority getting animosity instead
(`religiousness`/`skepticism` traits exist on `Node`, unconsumed so
far); priest corruption (bribery pattern reuse); priests as
disease-curers tied to Contagion's death toll. Also still open,
documentation-only: the Economy & poverty backlog (income, beggars,
hardship death, ambient sickness) and the Romance rebalance question —
neither has code yet, not blocking Priests.
