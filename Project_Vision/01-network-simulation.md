# Network Simulation

### The social graph, the phenomena that run over it, and the engine driving them day by day. Lives in `graph.py`, `phenomena.py`, `engine.py`, `demo.py`.

## Current State

### Social graph (`graph.py`)

- **Node** — one resident: `resident_id`, `ses` (poor/rich, from the
  TownShape snapshot), `alive`, and four personal traits —
  `religiousness`, `cunning`, `skepticism`, `loyalty` (each 0..1,
  independently synthesized at import via `synthesize_traits`, flat and
  uncorrelated with `ses` for now). Not yet mutated by events. Violence
  is the first consumer: a resident's own `loyalty` dampens their own
  odds of being picked as the aggressor in `_pick_aggressor`, restraining
  them even when equally hostile. `religiousness`/`cunning`/`skepticism`
  have no consumer yet — they're in place for Priests/Criminals work.
  Also carries `gender` and `age` (whole years, computed at import
  against `town_state.year_start`; `None` if either input is missing),
  used by romance/marriage eligibility below. Also carries `occupation`
  and `is_noble` straight from TownShape, plus a derived `role` property
  (`noble` > `guard` > `priest` > `civilian`, priority in that order —
  a noble who happens to also guard isn't rank-and-file) — infra for
  Guards/Priests/Nobles, not a behavior yet.
- **Edge** — one relationship: `source_type` (TownShape's original
  label), `fiske_type`, `time`/`intimacy`/`services` (shared — how much
  contact happens is mutual), and **two independent, directed valences**
  — `valence_a_to_b` and `valence_b_to_a`. How A feels about B need not
  match how B feels about A; only synthesized independently at import,
  and only ever mutated in the direction that actually changed (see
  `grief_shock` below). `tie_strength` averages the two valences'
  magnitudes with `time`/`intimacy`/`services`.
- **Import** (`import_snapshot`) is read-only against a TownShape `.db`
  and fully deterministic per `(db_path, seed)`: loads living residents,
  loads `relationships` rows as edges with attributes synthesized from
  per-type baseline distributions, and derives `shopkeeper_customer`
  edges from `shop_relationships` (TownShape doesn't store either
  directly). Also reads `town_state.aggression` and `.year_start` into
  `SocialGraph.town_aggression` (default 0.0 if the table is absent —
  e.g. test fixtures) and the age-reference year, respectively.

### Town-wide dynamic parameters

- **Aggression**: **Implemented**, using TownShape's *own* existing
  0..1 generation dial (it already drives TownShape's own skirmish-event
  generation) rather than inventing a new one. `demo.py` scales
  `ViolencePhenomenon.base_rate` by `1.0 + 2.0 * graph.town_aggression`
  (1x at aggression 0 — TownShape's own default — up to 3x at max).
  Religiosity and loyalty as *town-wide* dials (distinct from the
  per-resident traits above) remain proposed, not implemented.

### Phenomenon engine (`phenomena.py`, `engine.py`)

- A `Phenomenon` protocol (`init_state`, `edge_probability`,
  `apply_effect`, `end_of_day`, `summarize`) any number of phenomena can
  implement independently, each keeping its own per-resident state
  separate from the graph and from every other phenomenon.
- `run_simulation` drives every phenomenon over every living-endpoint
  edge, once per day, for N days: roll each edge's probability, apply
  effects, run end-of-day upkeep, then summarize. `alive`/`dead` in the
  daily summary is computed once, graph-wide, from `Node.alive` — not
  from any single phenomenon's own bookkeeping, since more than one
  phenomenon can now cause a death.

### Contagion (SIR + death)

- States: susceptible → infected → (recovered | deceased). Transmission
  probability scales with `base_rate`, tie strength, and a per-
  relationship-type weight (household ties spread it faster than
  incidental ones).
- An infected resident can now die instead of recovering:
  `case_fatality_rate`, weighted by the same SES-vulnerability factor
  violence uses (poor residents ×2, rich ×0.5), clamped at 100%.
- All three knobs are CLI flags on `demo.py`:
  `--transmission-rate`, `--infectious-days`, `--fatality-rate` — enough
  to model, for instance, a Black Death–like scenario.
- `ContagionPhenomenon` only ever models one thing: a single, severe,
  patient-zero-driven outbreak (`init_state` seeds exactly one
  `patient_zero`, once, at day 0 — no mechanism exists for a second
  one). That's deliberate scope for *this* phenomenon (a Black
  Death–style event) — see Common ailments, below, for the everyday
  sickness that runs alongside it instead of through it.

### Common ailments (`CommonAilmentsPhenomenon`)

- **Implemented 2026-09-21** (user feedback, refined twice before
  landing on the concrete design, then rebuilt once more after the
  first version's calibration blew up — see `docs/decisions.md`'s two
  2026-09-21 entries for the full history). Models ordinary, everyday
  sickness running continuously all year, alongside the rare big
  epidemic above, not instead of it. Two named ailments (the user's own
  examples, not exhaustive — more could be added the same way):
  - **Flu is contagious** — spreads over edges the same
    staged-pending-transmission way `ContagionPhenomenon` does, plus a
    small daily spontaneous chance of catching it from outside the
    tracked social graph entirely (what lets it keep circulating all
    year without a `patient_zero` seed or ever fully dying out).
  - **Diarrhea is not contagious** — a plain per-resident daily hazard
    roll, no edges involved at all; getting it doesn't depend on who you
    know.
  - **Both scale by poverty on two independent axes**, reusing
    `SES_VULNERABILITY`: the odds of getting sick at all, and separately
    the odds of dying from it once sick (kept low — common, not
    catastrophic).
  - **Recovering grants temporary immunity** (`flu_immunity_days=90`,
    `diarrhea_immunity_days=30`) — a third per-ailment status
    (`healthy`/`sick`/`immune`) alongside the sick/healthy pair. Not
    permanent like the big epidemic (residents do get sick again later
    in the year) and not zero either.
  - **Calibration bug, found and fixed before shipping**: a first
    version used zero immunity (straight back to `healthy` on
    recovery). On the reference town's dense ~40-80-ties-per-resident
    graph, that meant a same-day-reinfectable population never ran out
    of susceptible neighbors — flu alone produced ~29,500 "cases" in a
    year and 562 deaths, more than violence, riots, and the real
    epidemic combined. Verified with a real run *before* declaring it
    done, per the lesson from this session's earlier thief-plateau
    mistake. Fixed with the temporary-immunity window above plus a
    ~75× cut to `flu_transmission_rate`. Reference town after the fix:
    flu 354 cases/year (1 death), diarrhea 1,628 cases/year (31
    deaths) — comparable to the town's other minor death sources, not
    dominating them.
  - A resident can independently have the big epidemic, flu, and/or
    diarrhea at once — no cross-phenomenon link exists to prevent that,
    matching how every other phenomenon here stays self-contained.
  - **Flu is seasonal** (added 2026-09-21, follow-up feedback): both its
    transmission rate and spontaneous rate are multiplied by
    `flu_winter_multiplier` (default 3.0) during Q4+Q1 (day-of-year <=91
    or >=274), recurring every calendar year in multi-year runs.
    Diarrhea has no seasonality — only flu was asked for it, and it's the
    airborne one. Same follow-up also clarified that recovery had always
    worked (`sick`→`immune`→`healthy`); the "diarrhea just keeps growing"
    impression came from the dashboard plotting a cumulative-cases
    counter instead of currently-sick counts.
  - Tests: `tests/test_ailments.py`.

### Violence (directed animosity)

- Fires on an edge only if at least one direction is hostile
  (`valence < 0`); the day's odds come from whichever direction is more
  hostile, not an average — a one-sided grudge is enough to make an edge
  dangerous even if the other person doesn't reciprocate it.
- The **aggressor** is chosen by weighting each side's own outgoing
  hostility against the *other* side's SES vulnerability — the angrier
  side is more likely to strike, but a more vulnerable target also makes
  that strike more likely to succeed. This replaces an earlier version
  that picked a victim by SES alone, blind to who actually wanted to
  hurt whom.
- `grief_shock`: when someone dies, their other living connections who
  also know the culprit get angrier at the culprit — but only in *that
  bystander's own* outgoing valence toward the culprit, never the
  culprit's stored feelings toward them.
- **Assassination refinement: implemented 2026-09-21** (Criminals
  section's "assassination isn't guaranteed," extended directly onto
  `ViolencePhenomenon` rather than a new phenomenon). A violent attempt
  now has a success chance instead of an automatic kill:
  `min(1.0, success_base_rate * victim_vulnerability /
  attacker_vulnerability)`, reusing `SES_VULNERABILITY` for both sides
  at once — the victim's own value (poorer victims are easier to
  actually kill) divided by the attacker's (richer attackers succeed
  more easily; poorer ones struggle). Same-class violence stays close
  to the 0.85 default base rate; a poor-attacker-vs-rich-victim attempt
  succeeds rarely (~21% at defaults), the reverse almost always. A
  *failed* attempt never kills — the surviving victim's own valence
  toward the culprit drops sharply instead (`discovery_shock`), and no
  `grief_shock` fires (nobody died for bystanders to react to). See
  "Criminals," below, for the full before/after.

### Riots (town-wide, not per-edge)

- **Implemented** (`RiotPhenomenon`). Unlike every other phenomenon,
  a riot isn't a pairwise edge event, so all the real logic runs once a
  day in `end_of_day`; `edge_probability`/`apply_effect` are always
  inert (return 0.0 / `[]`). Town-wide bookkeeping (the precomputed
  civilian↔authority adjacency list, riot/death counters) lives on
  `self`, not the per-resident `state` dict — the engine indexes
  `state[resident_id]` for every phenomenon on every edge regardless of
  what `edge_probability` does with it, so `init_state` still has to
  return a per-resident dict, just one whose values are never read.
- **A riot now persists across days as explicit state**
  (`self._active_riot`), not a single atomic `end_of_day` call. Earlier
  it fully resolved (guard deaths, retreat, noble deaths) on the
  triggering day alone, which had no real stopping condition — it
  "stopped" only because the function returned. Corrected per direct
  user feedback: a real riot lasts as long as its own logic says it
  should, not as long as one Python call happens to run.
- **Trigger** (`_start_riot`, unchanged in spirit): average hostility
  from `civilian`-role residents toward any `guard`/`noble`-role
  neighbor (precomputed adjacency, since roles are static) crossing
  `unrest_threshold`; a daily probabilistic roll (`riot_base_rate *
  excess`) decides if it actually breaks out. Civilians with a hostile
  edge join with a chance driven by their own worst grievance and
  `1 - loyalty`. Needs `min_participants` (default 3) or it fizzles.
  Once started, `self._active_riot` holds the fixed participant list,
  guard roster, and a **riot bar** (below) for the rest of its life —
  the town-wide trigger check is skipped entirely while a riot is
  already active.
- **Guard phase** (`_advance_riot`, day by day while `not guards_retreated`):
  guards and rioters now trade casualties **simultaneously** each day —
  independent rolls for every living guard and every living rioter,
  both using that day's starting counts, checked once at the end of the
  day rather than sequentially with an early exit. (An earlier version
  processed guards first and stopped the instant they retreated, which
  meant rioters were only ever rolled against on days guards *didn't*
  break — in practice guards almost always broke on day one, so
  rioters essentially never took casualties. Corrected per direct user
  feedback: "how many rioters died? that should also be taken into
  account.")
  - Guards' own death chance scales with mob-size-vs-guard-count,
    exactly as before, until enough have died to cross that riot's
    `retreat_threshold`. **Still scales with the guards' own average
    `loyalty`** at riot start:
    `effective_guard_retreat_threshold = retreat_threshold * (0.5 + avg_guard_loyalty)`
    — 0.5 is the trait's own default mean, so an average-loyalty
    garrison reproduces the plain `retreat_threshold` unchanged; a
    disloyal one breaks far sooner, a fiercely loyal one holds far
    longer.
  - Rioters' own death chance uses the same size-ratio shape, but
    `rioter_lethality` (default 0.6) is set higher than `guard_lethality`
    (default 0.3) — direct user feedback: "guards are armed and
    trained, they have a lower chance to die when fighting rioters than
    the opposite." At equal force sizes this makes a rioter roughly
    **twice** as likely to die that day as a guard.
  - **New: rioters can rout.** If the mob's own casualties cross
    `rioter_retreat_threshold` before guards retreat, the survivors
    break and scatter — a `rioters_rout` event fires, the riot ends
    right there, and **nobles are never exposed** (guards successfully
    defended). Scaled the same way as guard loyalty, but by the mob's
    own animosity instead: `effective_rioter_retreat_threshold =
    rioter_retreat_threshold * (0.5 + avg_participant_hostility)`, using
    each participant's own worst grievance at the moment they joined —
    direct user feedback: "if enough rioters die, the others should
    escape (threshold should be based on the level of animosity)." An
    enraged mob absorbs more losses before it breaks than a lukewarm one.
  - If guards retreat (or there were none to begin with), no further
    guard *or* rioter deaths occur from this combat and nobles become
    exposed. If neither side breaks that day, both phases repeat the
    next day with the survivors.
- **Noble phase** (day by day once retreated): nobles are ranked by
  **how personally hated they are** (`_hatred_toward`: summed hostile
  valence from everyone who knows them, not just this riot's
  participants) and targeted most-hated-first, each with a death chance
  proportional to their hatred relative to the average among living
  nobles — never a flat class-wide rate. Every kill decrements the
  riot's own **riot bar** (`riot_bar_per_participant * len(participants)`
  at trigger time, e.g. 8 for a 77-person mob at the default 0.1) by 1.
  **The riot ends — a `riot_ends` event fires and `self._active_riot`
  clears — the moment the bar hits zero, or if no nobles are left**,
  whichever comes first. This is the actual stopping condition;
  previously there wasn't one. All death probabilities are still capped
  (`death_cap`, default 0.9) to avoid a mass-extinction outcome.
- **Aggression tie-in**: `demo.py` scales both `unrest_threshold` (down)
  and `riot_base_rate` (up) by the same `aggression_factor` violence
  uses.
  - **Calibration bug, found and fixed (user-prompted)**: the original
    default (`unrest_threshold=0.25`) sat almost exactly *on* the
    reference town's natural baseline civilian-to-authority hostility
    (~0.25-0.26 across seeds) — the daily trigger odds scale with how
    far *above* the threshold that baseline sits, so a near-zero margin
    meant near-zero odds, and riots were effectively unreachable within
    a normal year even though they weren't technically impossible.
    Several seeds in a row showing zero riots prompted the check. Fixed
    by dropping the default to `0.15` (real margin below the baseline)
    and raising `riot_base_rate` to `0.03`. **Verified the trigger
    mechanism itself was never broken**, separately from the
    calibration: with a fresh RNG stream and no other phenomena
    running (isolating it from the full simulation's shared draw
    sequence), 20 of 30 independent year-long trials produced at least
    one riot at these corrected values.
- **Calibration bug, found and fixed 2026-09-21**: `_advance_riot`'s
  death-chance formula used to scale linearly with each side's opposing
  headcount ratio, which made *total* expected deaths on each side equal
  to `lethality * opposing_headcount` — independent of your own side's
  size. Since the mob is drawn from the whole town but the guard corps
  is small and fixed (~40 in the reference town), a merely-larger-than-
  usual mob made guard casualties (driven by mob size, effectively
  unbounded) swamp rioter casualties (capped by the guard corps' small
  fixed size), regardless of `rioter_lethality` (0.6) being set above
  `guard_lethality` (0.3 at the time). Verified with a 30-seed aggregate
  before assuming a single bad run: 649 guard deaths vs. 539 rioter
  deaths (ratio 1.204, guards dying *more*) under the old formula —
  confirming a real bug, not noise. Fixed by switching to a square-root
  size factor on both sides (`lethality * sqrt(opposing/own)`), which
  makes the guard:rioter casualty *ratio* equal to
  `guard_lethality:rioter_lethality` regardless of mob size; retuned to
  `guard_lethality=0.2` (kept `rioter_lethality=0.6`, a clean 3:1). Same
  30-seed aggregate after the fix: 381 guard deaths vs. 1,036 rioter
  deaths (ratio 0.368, close to the 0.333 target). Full writeup:
  `docs/decisions.md`'s 2026-09-21 entry. Regression test:
  `tests/test_riot.py::test_guards_die_less_often_than_rioters_regardless_of_mob_size`.
- **Not yet built**: the bottom-up trigger from Criminals' "group
  violence escalates into a riot" (Criminals doesn't exist yet); any
  resolution-phase valence shift (catharsis vs. crackdown backlash) —
  deliberately left out since the source material doesn't commit to a
  direction and either would be a guess. A new riot can still trigger
  again immediately after one ends if the underlying hostility hasn't
  cooled — not treated as a bug, but worth knowing if two riots show up
  back-to-back in a log.

### Guards: bribery (`GuardPhenomenon`)

- **Implemented**, scoped to bribery only — see "Guards" below for what's
  deferred and why. Fires per-edge, only between a `civilian` and a
  `guard`; probability scales with the civilian's own `cunning` trait
  and an SES-based wealth-affordability proxy. Effect: raises only the
  guard's own outgoing valence toward the briber (clamped at 1.0) — the
  first concrete instance of the **favor** event type.

### Criminals: thief occupation + theft (`TheftPhenomenon`)

- **Implemented**, scoped to thief occupation + theft only — assassination
  refinement and the bottom-up group-violence-into-riot trigger (see
  "Criminals" below) are deferred to a later slice, same pattern Guards
  used for bribery-only.
- Becoming a thief is a **sticky per-resident flag**, rolled once in
  `end_of_day` (like Romance's `married` flag, not a new `Node` field),
  scaled by `ses` (poor ×2, rich ×0.3) — poverty raises the daily odds of
  the roll, but once it lands a resident stays a thief permanently; there
  is no reform or removal mechanic today, so the flag only ever
  accumulates. Nobles never roll for it (vision doc: "Nobles don't
  steal").
- Theft itself fires per-edge, only between a thief and a non-thief,
  scaled by the thief's own `cunning` and the victim's wealth (reuses
  `GuardPhenomenon`'s `BRIBE_WEALTH_FACTOR` — both are "how tempting is
  this person's wealth" the same way). A flat `discovery_chance` decides
  if it's caught; a caught theft drops the victim's valence toward the
  thief, and the valence of every guard the thief personally knows,
  toward the thief.
- **Arrest, execution, and deterrence: implemented 2026-09-21, corrected
  same day.** A caught thief can be arrested (clears `is_thief`) or, in
  a low-loyalty (corrupt) town, executed instead (removed from the
  graph). Every removal raises a decaying town-wide deterrence level
  that suppresses the become-a-thief roll. **First version gated arrest
  on the thief having an actual guard neighbor** — with only ~40 guards
  among 1,911 residents, that meant only ~10% of catches ever led to a
  removal, nowhere near enough for deterrence to matter. Corrected to a
  flat, town-wide arrest chance (the execution-vs-arrest split now uses
  town-wide average guard loyalty, not a caught thief's own guard
  neighbors) — arrest rate rose to 43% of catches. See "Criminals,"
  below, and `docs/decisions.md`'s two 2026-09-21 entries (the mistake
  and the correction are both recorded, not just the fix).
- **Calibration bug, found 2026-09-21 (user feedback), fix verified
  wrong, then actually fixed**: on the reference town/seed, 511 of
  1,911 residents (27%) became thieves within a single year, with no
  way for the count to ever go back down. The *first* attempted fix
  (arrest/execution/deterrence, gated on guard-neighbor adjacency)
  looked like it worked from a 1-year trajectory (77→78, "flat") — but
  asked directly "are you sure it plateaus?", a 3-year check showed
  94→221, still climbing at the same rate, no real deceleration. The
  1-year read was short-window noise, not convergence. Corrected per
  above; a 2-year run with the corrected mechanism shows real
  fluctuation for the first time, including several genuine
  *declines* (e.g. day 550→600: 65→64→63 thieves) — only possible when
  removals outpace new thieves — though the exact equilibrium level
  (drifting somewhere in the 70s-90s by year 2, town-wide) isn't fully
  pinned down yet; a longer/more-seeded verification is the natural
  next check if the exact level matters, not run given how expensive
  multi-year full-town runs are in this environment.

### CLI & output (`demo.py`)

- `demo.py --db <snapshot> [--days] [--seed] [--transmission-rate]
  [--infectious-days] [--fatality-rate] [--out]` runs both phenomena and
  writes `summary.csv` (daily susceptible/infected/recovered/deceased/
  alive/dead) and `events.json` (full event log).
- No test framework — plain `assert`-based tests, `tests/run_all.py`
  runs everything.

## Feedback & Future Ideas

Organized by topic; sourced from
[`../Network_Population_depth.md`](../Network_Population_depth.md) (the
original brainstorm, kept as-is) and re-grouped here against what's
already built above. Everything below is **Proposed** — none of it is
implemented yet — unless marked otherwise.

### Town-wide dynamic parameters

- A set of "guardrail" dials that widen or narrow how fast animosity/
  affinity move in response to events — not new events themselves, but
  multipliers on the events above:
  - **Aggression**: **Implemented** — see "Current State" above. Reads
    TownShape's own generation dial rather than a new one.
  - **Religiosity**: shapes how strongly residents' relationships with
    priests move (see Priests, below).
  - **Loyalty**: a loyal town's guards take fewer bribes and its people
    are more deferential to nobles, so animosity toward the governing
    class grows more slowly.
- These shouldn't be fixed at generation — they should drift with
  events. Worked example from the source doc: a very religious town hit
  by a deadly disease sees animosity toward priests rise (slowly, at
  first); that erosion should itself lower the town's religiosity
  parameter, so a *second* disease event moves animosity toward priests
  faster than the first one did. A feedback loop, not a one-time roll.
- **Open question the user posed directly:** what other town-wide
  parameters make sense here, informed by whatever's already in
  TownShape's own gap log (`TownShape/docs/narrative-gaps.md`, linked
  from `TownShape/Project_Vision/02-simulation-layer.md`) so the same
  gaps aren't independently rediscovered. A few candidates worth
  weighing, not yet proposed by the user — flag if any land wrong:
  - **Corruption** (distinct from loyalty): how often bribes are
    *offered* in the first place, versus how often guards *accept* one.
  - **Wealth inequality / Gini-style skew**: TownShape already models
    per-household wealth; a town-wide inequality parameter derived from
    that distribution could directly drive how fast poor→noble animosity
    grows, rather than that rate being a flat constant.
  - **Justice fairness**: independent of loyalty, how consistently crime
    is actually punished regardless of the culprit's class — feeds the
    "nobles almost never get caught" asymmetry already implied under
    Criminals/Nobles below.
- **Taxes**: an external stressor (disease, war) prompts the governing
  body to raise taxes; taxes raise animosity toward whoever governs.
  Overlaps with the Nobles section's coup mechanic below — same
  underlying lever (tax → animosity → possible violence against the
  governing class), triggered from a different direction.

### People

- **Romance**: **Implemented** (`RomancePhenomenon`). Mutual affinity
  (`min` of both directions, so an unrequited crush never qualifies)
  crossing `love_threshold` (default 0.5) retypes an eligible edge to
  `spouse` in place. Eligible = both alive, both adults (age >= 18, the
  same threshold TownShape's own `family.py` uses), opposite gender
  (only gender values seen in TownShape data so far — a known gap, not
  a deliberate exclusion), neither already married (v1 has no
  divorce/remarriage), and not a `parent`/`sibling` edge (no incest).
  Married (`spouse`-type) edges then roll for a birth each day,
  recorded as a **log-only `Event`** — no new `Node` is created yet,
  since every other phenomenon's state dict is fixed at day 0 and
  doesn't tolerate residents added mid-run (would need a
  `Phenomenon.default_state` hook or similar to fix properly). Real
  child-Nodes, and therefore real multi-generational family ties
  derived from them, are a follow-up.
  - **Calibration finding, worth remembering**: on a real TownShape
    town, most residents are already married at import (337 spouse
    edges / 1911 residents here) and the unmarried-adult pool is small
    (143 of 1911). Of those, pairs that are *both* unmarried *and*
    already connected by some edge *and* clear the mutual-affinity
    threshold are rarer still (1 such pair in the reference town/seed).
    ~0-2 new marriages/year for this town is therefore a realistic
    result of the data, not underfiring — resist the urge to inflate
    `marriage_base_rate` to compensate. The real limiter is that two
    unconnected singles can never meet: there's no "stranger" edge-
    creation mechanic, only marriage over pre-existing ties. Worth
    revisiting once that matters more.
  - **User pushback, 2026-09-21**: this explanation hasn't actually
    resolved the concern — "I still do not understand why no one falls
    in love in these cities" was raised again after the above was
    already documented. Treat as open, not closed: either the mechanic
    itself needs rebalancing (a stranger-meeting mechanic, or a lower
    `love_threshold`) or, if the current rate genuinely is realistic,
    the dashboard needs to *show* that more legibly (e.g. surface
    near-miss courtships — pairs that clear some but not all of the
    eligibility gates) so "quiet year" reads as working-as-intended
    rather than broken.
- Opposite-gender marriages can produce children — this is additive on
  top of TownShape's existing birth/household derivation, not a
  replacement for it.
- Cross-class romance is rare but possible. Affinity between people from
  different classes grows slowly; animosity grows fast, driven by
  events. (An asymmetric growth *rate* — distinct from the directed
  animosity *values* already implemented.)
- **Multi-generational family ties** (grandparent, aunt/uncle, cousin,
  nephew...) should exist as derived relationships. This is the same
  gap TownShape's own vision doc already tracks — see
  `TownShape/Project_Vision/02-simulation-layer.md`, "No multi-
  generational relationships" (Open, 2026-08-28) — worth resolving in
  one place rather than two.
  - **Checked, not viable yet**: TownShape's `parent` edges are
    strictly household-scoped (only recorded between an adult and a
    *currently cohabiting* minor child) — a resident who's grown up and
    moved out never appears as a "child" in any `parent` edge anymore.
    Confirmed empirically on a real snapshot: 1842 `parent` edges, 1463
    `sibling` edges, **zero** cases of a parent who is themselves
    someone's recorded child (i.e. zero derivable grandparent or
    aunt/uncle chains). Deriving this now would be untestable dead
    code. Real path forward: once Romance's births create actual
    `Node`s (see People, above) and a simulation runs long enough for
    those children to grow up and have their own kids, genuine
    multi-generation chains will exist in *our* graph to derive from —
    revisit then, not before.
- **Personal traits** — religiousness, cunning, skepticism, loyalty —
  **Implemented** as static fields on `Node` (see above); only `loyalty`
  has a consumer so far (violence). Still proposed: shaping how likely a
  person is to be bribed, to succeed at a crime, to become a thief, to
  join a riot, and so on, once those phenomena exist. Traits should also
  themselves shift in response to events (e.g., being beaten by guards
  erodes loyalty in the victim and their close connections) — not yet
  built; nothing mutates a trait today. Town-wide parameters (above) should likely
  be an *aggregate* of these individual traits rather than a separately
  hand-set dial — worth deciding as one design question, not two, since
  the source doc raises both independently but they're the same idea at
  different scales.
- **Stress, a new candidate personal property (user feedback,
  2026-09-21)**: "a single-person property that represents their level
  of stress? Affected by poverty, by grief, sickness..." Not
  implemented, no consumer designed yet — this would be a *derived*,
  dynamic per-resident value (unlike the four static traits above),
  fed by sustained poverty (see "Economy & poverty," below), grief
  (Violence's `grief_shock` already tracks something adjacent — a
  hostility bump toward a specific person — stress would need to be a
  general, undirected level instead), and sickness. Individual-level
  analog of the town-wide-dials-as-aggregate-of-traits idea above:
  worth designing together rather than twice, once both exist.

### Economy & poverty (new, user feedback 2026-09-21)

No economic simulation exists today: `ses` is a static three-tier
(`poor`/`middling`/`rich`) field copied from TownShape at import,
never earned, spent, or changed by events. Several pieces of feedback
converge on the same missing layer underneath Criminals, Contagion, and
People:

- **A continuous poverty/wealth measure per resident**, not just the
  3-tier `ses` bucket — "probability should depend also on how
  effectively poor a person is." Several mechanics above already want
  to scale by *how* poor, not just *which* bucket: thief-occupation odds
  (Criminals, above), theft-victim attractiveness (already implemented,
  reuses `BRIBE_WEALTH_FACTOR`), and the two items below. Likely needs
  deciding whether this is TownShape-sourced (does TownShape track
  actual household wealth already? — the Guards bribery section above
  notes it "already models per-household wealth" for the Gini-style
  town parameter candidate) or synthesized here the way traits are.
- **Irregular income for residents without a formal `occupation`** —
  "sporadic day jobs" should give informally-employed residents some
  irregular income, rather than being economically inert. Needs the
  poverty measure above to have somewhere to feed into.
- **Beggars**: very poor residents should have a chance to become
  beggars, alongside (or instead of) becoming thieves (see Criminals,
  above) — another branch off the same poverty-severity roll.
- **Hardship/starvation death**: a resident poor for "too long" — needs
  poverty *duration* tracked as real state, which nothing currently
  does anywhere in the codebase (every existing sticky flag, like
  Theft's `is_thief` or Romance's `married`, only tracks whether
  something is true, never for how long) — should eventually die from
  it directly, independent of Contagion. A new hazard, not a Contagion
  parameter.
- ~~Continuous ambient sickness~~ — superseded by the concrete "common
  ailments" design (flu, diarrhea, contagious vs. not, poverty-scaled
  incidence *and* fatality) under Contagion, above, once the user spelled
  out exactly what they meant. Kept here only as a pointer so this
  section doesn't silently duplicate that one.

### Guards

- Guards function as something closer to a shared public relationship
  than individual people — most residents have a baseline connection to
  "the guards" as a class, shifting with events (beatings, tax
  collection, bribery, corruption). **Simplified for v1**: guards are
  modeled as the individual named residents they already are (role
  `guard`, ~40 in the reference town), and mechanics operate over real
  edges to them, consistent with every other implemented phenomenon —
  not a separate abstract "the guards" institution-wide relationship.
  Revisit if that framing turns out to matter.
- A guard's response to a given resident: arrest calmly (low animosity
  toward that person), arrest roughly (high animosity), look the other
  way (high affinity), or accept a bribe (moderate affinity). **Bribery
  and a first arrest mechanic implemented** (2026-09-21, inside
  `TheftPhenomenon` itself — see Criminals, above and below); arrest
  behavior for *violence* specifically is still blocked on the same
  cross-phenomenon event link this always needed (guards reacting to
  what violence produced), since that link still doesn't exist. Theft's
  own arrests sidestepped needing it: guards react to theft locally
  (checking their own edges), the same self-contained way the existing
  `guard_notified` valence hit already worked, not through a generic
  event bus.
- **Riots**: **Implemented** — see "Riots" under Current State, above.
- **Bribery: Implemented** (`GuardPhenomenon`). A civilian bribes a
  guard they're actually connected to (an edge, not an abstract class
  tie); the chance scales with the civilian's own `cunning` trait, their
  `ses` as a wealth-affordability proxy (no town-wide wealth aggregate
  exists yet — see the "Wealth inequality" candidate parameter), and the
  **guard's own `loyalty`** as a restraint factor (`1 - loyalty`) — a
  loyal guard refuses far more often than a corruptible one. Effect:
  raises only the guard's own outgoing valence toward the briber,
  clamped at 1.0 — the first concrete instance of the new **favor**
  event type (below): it only ever raises affinity, directionally, same
  discipline as `grief_shock`.
  - **Calibration correction (user feedback)**: the first version had no
    loyalty dependence and an unscaled base rate, producing ~471
    bribes/year on the reference town — far too high for a normal town,
    since that number should only show up in a genuinely low-loyalty,
    high-corruption one. Adding the loyalty restraint (halves the rate
    at the trait's own default mean of 0.5) and cutting the base rate
    10× together bring the reference town to ~25/year. Loyalty alone
    only gives about a 2× swing town-to-town, though — a real
    high/low-corruption *contrast* likely needs the town-wide
    **corruption** parameter already flagged as a candidate dial
    (Town-wide dynamic parameters, above) multiplying this rate too,
    not just individual guards' own loyalty. Not built yet; flagged so
    the next pass doesn't have to rediscover the gap.
  - **Integration note for whenever this feeds back into TownShape**:
    bribes are a real economic transaction and should be recorded
    there, not just as a valence nudge here. TownShape already has a
    `tax_payments` table (`resident_id`, `tax_type`, `amount`, `period`,
    `payment_date`) for exactly this shape of record — a bribe should
    likely be written the same way (a new `bribe_payments` table, or an
    extended `tax_type`/transaction table covering both), carrying an
    `amount` so the "going rate scales with town wealth" idea has
    somewhere real to live. This project never writes back to
    TownShape today (see the design doc's read-only contract) — this is
    a forward note for whenever that integration is actually built, not
    a change to make now.
- A guard bribed by a noble or priest reacts more strongly to anyone who
  later targets that patron — an attack on someone who's paid you off
  reads as more personal than an attack on an ordinary resident. Not
  implemented: needs bribery to track *who* bribed a guard beyond the
  edge's own valence, and a link to violence's culprit/victim.
- Guards start with a built-in skew: more affinity toward nobles, more
  animosity toward poor residents who act against nobles. Not
  implemented: noble/guard edges get the same neutral synthesis as
  everyone else today.
- Animosity toward a governor (if the town has one) should partly
  trickle down onto the guards and nobles associated with them. Not
  implemented — no governor concept exists yet.

### Criminals

- ~~**Thief** as an occupation; poverty raises the odds a resident becomes
  one.~~ **Implemented** (see "Criminals: thief occupation + theft" under
  Current State, above).
- ~~Crime types: manslaughter (violence already covers the mechanics) and
  theft~~ **Theft implemented** (see above). Manslaughter still just
  reuses Violence's existing mechanics, unchanged.
- ~~Every criminal event carries a discovery chance; if the culprit is
  caught, their relationships with nearby residents and the guards
  change.~~ **Implemented for theft** (discovery chance, victim + guard
  valence hit, plus arrest/execution — see below).
- ~~**Population should plateau, not grow monotonically**~~ **Arrest,
  execution, and deterrence implemented 2026-09-21, corrected same
  day** — see "Criminals: thief occupation + theft" under Current
  State, above, and `docs/decisions.md`'s two 2026-09-21 entries. A
  first version gated arrest on the thief having a guard *neighbor*,
  which a 3-year check (not just 1 year) showed didn't actually
  plateau (94→221 thieves, year 1 to year 3, no deceleration) — most
  caught thieves never had a guard neighbor given only ~40 guards among
  1,911 residents. Corrected to a flat, town-wide arrest chance. A
  2-year run with the fix shows real fluctuation, including genuine
  declines, for the first time — a qualitatively different dynamic than
  the old monotonic climb — though the exact long-run equilibrium level
  isn't fully pinned down yet (drifting somewhere in the 70s-90s by
  year 2). Two of the originally-requested pieces are still deferred,
  not yet needed to get real negative feedback:
  - **Arrest chance is a flat town-wide constant today, not scaled by
    guard density or a town-wide corruption dial** — the dial itself
    (candidate parameter under Town-wide dynamic parameters, above)
    still doesn't exist; execution-vs-arrest reuses guard loyalty as a
    corruption proxy instead (same proxy bribery already uses).
  - **The base rate still scales by the 3-tier `ses` bucket, not a
    continuous poverty-severity measure** — needs the measure proposed
    under the new "Economy & poverty" section, below.
- **Beggars, as a second poverty-driven status alongside thieves (user
  feedback, 2026-09-21)** — very poor residents should have a chance to
  become beggars instead of/in addition to thieves. See "Economy &
  poverty," below, for the mechanics this needs (a continuous poverty
  measure to branch on).
- ~~**Assassination isn't guaranteed**~~ **Implemented 2026-09-21** —
  extends `ViolencePhenomenon` directly rather than a new phenomenon
  (per the plan's own scoping). Success chance reuses `SES_VULNERABILITY`
  two ways at once: divided by the attacker's own value (a rich
  attacker's resources make success easier, a poor attacker's lack of
  them makes it harder) and multiplied by the victim's (a poor victim is
  easier to actually kill, same logic `_pick_aggressor`'s weighting
  already uses) — `min(1.0, success_base_rate * victim_vulnerability /
  attacker_vulnerability)`. Same-class violence stays close to the
  default 0.85 base rate (close to the old guaranteed-kill behavior); a
  poor-attacker-vs-rich-victim attempt succeeds rarely (~21% at
  defaults), the reverse succeeds almost always. A *failed* attempt
  never kills — the surviving victim's own valence toward the culprit
  drops sharply instead (`discovery_shock`, they now know exactly who
  came after them) — this is the "guaranteed discovery" the vision doc
  asked for, scoped to the victim's own reaction rather than a
  town-wide alert (no cross-phenomenon Guards link exists yet — see
  Guards, above). No grief_shock fires on a failure, since nobody died.
  Tests: `tests/test_violence.py`'s
  `test_poor_attacker_vs_rich_victim_succeeds_less_often_than_the_reverse`
  and `test_failed_attempt_leaves_victim_alive_and_drops_their_valence_toward_culprit`.
- **Group violence**: if enough people share high animosity toward the
  same target, and enough affinity with each other, they can attempt a
  killing together with a much higher success chance than any one of
  them alone — and if enough band together, this can escalate directly
  into a riot. (Shares the riot-model dependency flagged under Guards.)

### Priests

- In a religious town, priests get a broad affinity boost from most
  residents; a small, deliberately chosen set of heretics/skeptics get
  an animosity boost instead.
- Priests can be corrupt — accepting payment for services.
- Priests are the town's disease-curers; when a disease kills many
  people, priests are blamed and animosity toward them rises.
- In a less religious town, priests may resort to bribing guards
  themselves.
- Priests (alongside nobles) can declare a quarantine for a sufficiently
  contagious or dangerous disease — see Quarantine, below.

### Nobles

- Noble/poor animosity starts already skewed toward resentment on the
  poor side, and rises further with riots and general unrest (e.g. from
  high taxes) — disproportionately from the poor side. High enough
  animosity has the same riot risk as with guards. **Riot risk itself
  implemented** (see "Riots" above, including the guards-shield-nobles-
  until-they-break mechanic); the *skewed starting animosity* and *rises
  with taxes* parts are still proposed, not implemented — noble/civilian
  edges get the same neutral-mean valence synthesis as everyone else
  today.
- Nobles may call a quarantine if the outbreak starts near wealthy areas
  or once wealthy residents start dying; a governor, if one exists,
  absorbs most of the resulting public anger for that call.
- One or a few nobles can become the town's head figures, where the
  narrative supports it.
- Nobles (and priests) can hire mercenary protection, scaling with how
  much animosity is directed at them, with a sensible cap. More hired
  protection lowers an attacker's success chance.
- Nobles almost never personally commit manslaughter — when they want
  someone dead, they hire an assassin instead.
- Nobles don't steal (for now).
- Rising taxes raise noble animosity toward the governor; past a
  threshold, nobles may hire mercenaries to move against the governor
  and seize power themselves. The governing body's suspicion of an
  in-progress coup grows with the number of mercenaries hired.
- Nobles under heavy public animosity can bribe priests to speak well of
  them; the resulting animosity decrease (or affinity increase) among
  poor residents scales with each individual's own religiousness.

### Quarantine (cross-cutting: Priests + Nobles)

- Either priests or nobles can institute a quarantine for a dangerous or
  highly contagious disease.
- Effect: substantially raises the death rate for residents already in
  the affected area, while substantially lowering infection/death risk
  for everyone outside it.
- Also raises animosity toward whichever class — priests or nobles —
  made the call.

### Event taxonomy & personal properties (needs a decision, not just a list)

- Candidate event types so far: killing, stealing, loving, bribing,
  hiring, influencing, **favor**, **wrongdoing** — likely incomplete;
  several more are implicit above (arresting, quarantining, raising
  taxes, attempting a coup). **Open: agree the full list before
  implementing further phenomena.**
  - **favor** and **wrongdoing** (added this session, not yet
    implemented as their own phenomenon): the two generic, symmetric
    building-block events underneath most of the more specific ones
    above. A favor raises affinity (valence, in the beneficiary's
    outgoing direction toward whoever did it) — a bribe, a kindness, a
    guard looking the other way are all specific *instances* of a
    favor. A wrongdoing raises animosity the same way, directionally —
    a beating, a theft, a betrayal are specific instances of a
    wrongdoing. Once built, several already-implemented or proposed
    mechanics (bribery, guard beatings, priest corruption) could likely
    be expressed as parameterized favor/wrongdoing events rather than
    each inventing its own valence-mutation logic from scratch — worth
    deciding when Guards/Priests get built, not before.
- Once agreed, each event needs an explicit mapping to which edges and
  weights it reads and mutates — the same discipline `violence`'s
  `grief_shock` already follows (see
  `docs/2026-09-15-social-network-design.md` §8). Skipping this step is
  exactly how `valence` ended up undirected the first time around.
- Needs the personal-trait system (religiousness, cunning, skepticism,
  loyalty — see People, above) in place before most of these events can
  be implemented, since several depend on it directly (bribability,
  crime success odds, riot participation).
