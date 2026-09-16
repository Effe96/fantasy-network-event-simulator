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
  directly).

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
  to model, for instance, a Black Death–like scenario (see the results
  dashboard's plague scenario).

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
  - **Aggression**: an aggressive town has bigger animosity swings
    (harsher guard beatings, more frequent riots); a pacific one has
    smaller swings.
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

- **Romance**: if mutual affinity between two people crosses a
  threshold, they fall in love and marry.
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

### Guards

- Guards function as something closer to a shared public relationship
  than individual people — most residents have a baseline connection to
  "the guards" as a class, shifting with events (beatings, tax
  collection, bribery, corruption).
- A guard's response to a given resident: arrest calmly (low animosity
  toward that person), arrest roughly (high animosity), look the other
  way (high affinity), or accept a bribe (moderate affinity).
- **Riots**: once town-wide animosity toward guards crosses some
  threshold, riots become possible. **No riot model exists yet** — this
  needs a concrete mechanic (who joins, what it costs, what it changes)
  before it can be implemented; flagged as a dependency for Guards,
  Criminals, and Nobles alike.
- Bribery raises the guard's affinity toward the briber; the going rate
  scales with town wealth.
- A guard bribed by a noble or priest reacts more strongly to anyone who
  later targets that patron — an attack on someone who's paid you off
  reads as more personal than an attack on an ordinary resident.
- Guards start with a built-in skew: more affinity toward nobles, more
  animosity toward poor residents who act against nobles.
- Animosity toward a governor (if the town has one) should partly
  trickle down onto the guards and nobles associated with them.

### Criminals

- **Thief** as an occupation; poverty raises the odds a resident becomes
  one.
- Crime types: manslaughter (violence already covers the mechanics) and
  theft (doesn't exist yet as a phenomenon).
- Every criminal event carries a discovery chance; if the culprit is
  caught, their relationships with nearby residents and the guards
  change.
- **Assassination isn't guaranteed**: the target has a survival chance,
  and a *failed* attempt guarantees the attacker is discovered. A poor
  attacker targeting a rich or noble victim has lower odds of success
  than the reverse.
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
  animosity has the same riot risk as with guards.
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
  hiring, influencing — likely incomplete; several more are implicit
  above (arresting, quarantining, raising taxes, attempting a coup).
  **Open: agree the full list before implementing further phenomena.**
- Once agreed, each event needs an explicit mapping to which edges and
  weights it reads and mutates — the same discipline `violence`'s
  `grief_shock` already follows (see
  `docs/2026-09-15-social-network-design.md` §8). Skipping this step is
  exactly how `valence` ended up undirected the first time around.
- Needs the personal-trait system (religiousness, cunning, skepticism,
  loyalty — see People, above) in place before most of these events can
  be implemented, since several depend on it directly (bribability,
  crime success odds, riot participation).
