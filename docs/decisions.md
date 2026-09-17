# Decisions Log

> **What this file is for.** `docs/2026-09-15-social-network-design.md`
> describes *what* each mechanic does and *how* — formulas, plain-language
> explanations, worked examples. This file records *why* a choice was
> made the way it was: the constraint that forced it, the alternative
> that was rejected and why, the calibration number that turned out wrong
> and what fixed it. Read this before re-litigating a decision or
> "fixing" something that was already deliberately chosen. Newest first.

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
