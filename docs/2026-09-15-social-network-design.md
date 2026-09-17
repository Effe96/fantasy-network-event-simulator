# Social Interaction Network — Concepts & Design

> **Living document.** Every mechanic in this project gets a section here,
> in the same shape: a **Technical** subsection (the exact formula/rule),
> a **Plain language** subsection (the same idea without jargon), and a
> **Worked example** with real numbers. This is a standing convention for
> the project, not a one-time write-up — when a new phenomenon or
> parameter is added, it gets a section here in the same style before the
> work is considered done. See `docs/decisions.md` for the *why* behind
> choices; this file is the *what* and *how*.

## 1. Purpose

A standalone prototype, sibling to the `TownShape` repo, exploring one
question: **can a generic engine, given a social graph, simulate very
different "things that spread" — a disease, a wave of violence, romance,
riots, corruption — using the same mechanism?**

It reads a one-time, read-only snapshot of residents and relationships out
of a real TownShape town database, enriches that graph with attributes
TownShape doesn't store today, and runs day-by-day simulations over it.
Nothing here writes back to TownShape, and TownShape's own database schema
is untouched — this project only *reads* `residents`, `relationships`,
`shop_relationships`, and `town_state` from one `.db` file.

The output (a plain event log: "on day 40, a violent event happened between
resident 12 and resident 88") is deliberately shaped to be a good input for
narrative generation later, though wiring that up is out of scope here.

Five phenomena exist today: **Contagion** (§7), **Violence** (§8),
**Romance & Marriage** (§11), **Riots** (§12), and **Guards' bribery**
(§13). §9–10 cover two pieces of shared infrastructure — personal traits/
roles and the town-wide aggression dial — that several phenomena above
read from.

## 2. Where the data comes from

TownShape already derives relationships between residents — family,
coworker, neighbor, military unit-mate, and classmate ties — into a
`relationships` table (see `town_relationships/` in the TownShape repo).
`derive_coworker_relationships` groups residents by
`workplace_building_id` regardless of building type, so two people who
both work at the same shop are already tagged `coworker` — no extra work
needed there.

TownShape also has a separate `shop_relationships` table, linking a
resident to a *shop building* (purchase history, distance, a
`customer_score`) rather than to another resident, so it isn't a
person-to-person edge as stored. This project derives one anyway: joining
`shop_relationships` against `residents.workplace_building_id` pairs each
customer with that shop's staff, producing a `shopkeeper_customer` edge.

Beyond `relationships` and `shop_relationships`, this project also reads:

- **`residents.gender`, `.birth_date`, `.occupation`, `.is_noble`** — used
  by traits/roles (§9) and Romance (§11).
- **`town_state.aggression`, `.year_start`** — used by the aggression dial
  (§10) and to compute each resident's age (§9) against an in-universe
  reference year, since `town_state.current_date` has been observed to
  hold a real-world placeholder date rather than an in-universe one on
  some sample snapshots and isn't trustworthy for this.

All of this import is one-time and read-only: this project never opens a
TownShape `.db` file for writing.

## 3. Core concept: an edge needs to be more than a label

### 3.1 The problem

TownShape tags a tie between two residents with a single word: `coworker`,
`sibling`, `neighbor`. That tells you the *kind* of relationship, but
nothing about how strong, warm, or hostile it actually is. Two people
tagged `coworker` could be work-best-friends or two people who can't stand
each other — the label can't tell the difference. Anything that depends on
*how people feel* about each other — a disease spreading faster through
close contacts, a grudge escalating into violence — needs more than a
label per edge.

### 3.2 Tie strength (Granovetter, 1973) — "how close is this?"

**Technical:** Granovetter's "The Strength of Weak Ties" scores a tie on
four independent 0–1 dimensions:

| Dimension | What it measures |
|---|---|
| `time` | how much substantive contact happens |
| `intensity` | how emotionally charged the tie is (magnitude only — not direction) |
| `intimacy` | how much personal/vulnerable information is shared |
| `services` | how much reciprocal favor/support is exchanged |

`tie_strength = mean(time, intensity, intimacy, services)`

**Plain language:** Picture two people who see each other daily, tell each
other everything, and help each other move house — high on all four,
a strong tie. Compare a shopkeeper you nod at twice a year — low on all
four, a weak tie. `tie_strength` is just the average of those four scores.

**Worked example** (numbers from the reference doc this design is based
on, `relational_network_frameworks.md` in the TownShape repo):

| Relationship | time | intensity | intimacy | services | tie_strength |
|---|---|---|---|---|---|
| Brother | 0.7 | 1.0 | 1.0 | 1.0 | 0.92 |
| Best friend | 0.7 | 1.0 | 1.0 | 1.0 | 0.92 |
| Distant friend | 0.1 | 0.5 | 0.5 | 1.0 | 0.52 |

Note that "Brother" and "Best friend" score identically here — tie
strength alone can't distinguish a beloved sibling from a beloved friend,
and it *also* can't distinguish a beloved sibling from a sibling you
despise, because `intensity` is deliberately direction-free. That gap is
what the next concept fixes.

### 3.3 Valence — "how do they feel about it?"

> **Amendment (2026-09-16):** valence is directional. Each edge stores
> `valence_a_to_b` and `valence_b_to_a` independently — A's feelings about
> B need not equal B's feelings about A, and each direction only ever
> changes when something specifically affects *that* person's feelings
> (e.g. `grief_shock`, §8, or a bribe, §13). The rest of this section still
> describes the underlying score correctly; read `valence` below as "one
> direction of it," and see `Edge.valence_from(resident_id)` in `graph.py`
> for how code asks "how does *this* person feel about the other end?"
> without needing to know which of `resident_a`/`resident_b` they are.

**Technical:** a signed score, `valence ∈ [-1, +1]`, where -1 is pure
animosity and +1 is pure affection. Several phenomena depend on it:
violence fires on negative valence (§8), romance on mutual positive
valence (§11), riots on aggregate negative valence toward guards/nobles
(§12), and bribery raises it (§13).

Because `intensity` (above) is magnitude-only, `tie_strength` is
recomputed using the mean of `|valence_a_to_b|` and `|valence_b_to_a|` in
place of `intensity`:

`tie_strength = mean(time, mean(|valence_a_to_b|, |valence_b_to_a|), intimacy, services)`

**Plain language:** a screaming rivalry and a tight friendship can both be
"intense" — same magnitude, opposite direction. `valence` is that
direction. Using its magnitude in `tie_strength` means an intense rivalry
counts as just as much "contact opportunity" for a disease to spread as an
intense friendship does — it's the *sign* of valence, not its size, that
decides whether that contact helps or harms. And because each direction
is independent, one person can be furious at another who barely notices
them.

**Worked example:** a married couple has `time=0.9, intimacy=0.9,
services=0.9`. If both directions of `valence=+0.8` (a loving marriage),
`tie_strength = mean(0.9, 0.8, 0.9, 0.9) = 0.875` — high contact, positive
relationship. If instead `valence_a_to_b=-0.9` but `valence_b_to_a=-0.1`
(A resents B far more than B resents A — two independent random draws at
import, not a shared number), `tie_strength = mean(0.9, mean(0.9,0.1), 0.9,
0.9) = mean(0.9, 0.5, 0.9, 0.9) = 0.8` — still a live candidate for
violence (§8), and the day's odds come from A's side (the more hostile
one), not an average that would water the grudge down.

### 3.4 Relational model type (Fiske, 1991) — "what kind of exchange is this?"

**Technical:** Fiske's Relational Models Theory names four categorical
"exchange logics": Communal Sharing (undifferentiated in-group, no
accounting), Authority Ranking (asymmetric/hierarchical), Equality
Matching (turn-based reciprocity), Market Pricing (explicit cost-benefit).

**Plain language:** this is the unwritten rule two people use to decide
who owes what to whom. Family shares without keeping score (Communal
Sharing); a guard captain and a soldier follow rank (Authority Ranking);
two neighbors trade favors tit-for-tat (Equality Matching); a shopkeeper
and a customer settle in coin (Market Pricing).

**In this prototype:** derived mechanically from TownShape's existing
`relationship_type` as an informational tag only —

| `relationship_type` | Fiske tag |
|---|---|
| `parent`, `sibling`, `spouse` | Communal Sharing |
| `unit_mate` | Equality Matching |
| `coworker` | Authority Ranking |
| `neighbor` | Equality Matching |
| `classmate` | Communal Sharing |
| `shopkeeper_customer` (derived, see §2) | Market Pricing |

Nothing in this prototype's probability math reads this tag yet — it's
recorded on every edge so it's available the moment a phenomenon needs it
(e.g. a future phenomenon where Authority Ranking ties behave differently
from Communal Sharing ones).

### 3.5 What's deliberately not built here

The reference doc (`relational_network_frameworks.md`) describes several
deeper layers, each skipped for this prototype with the reason why:

- **ABI trust model** (Ability/Benevolence/Integrity) — no phenomenon here
  reasons about trust yet.
- **Advice / trust / communication layering** (Krackhardt; Podolny &
  Baron) — needed when workplace ties must be split into who-you'd-ask
  vs. who-you'd-confide-in vs. who-you-actually-talk-to; every current
  phenomenon treats a coworker tie as one thing.
- **House's 4-part support taxonomy** — a finer breakdown of `services`;
  not needed until a phenomenon cares about *what kind* of favor is
  exchanged.
- **Full multilayer graph formalism** (De Domenico et al.) — the doc's own
  guidance is to adopt this once more than ~2 relationship types must be
  modeled simultaneously without collapsing to one score. Five
  phenomena, one score per edge, is comfortably under that bar so far.
- **Cognitive Social Structures** (perceived-vs-actual graph, Krackhardt
  1987) — nobody's *perception* of the graph matters yet, only the graph
  itself.

Revisit any of these the moment a specific phenomenon needs the extra
resolution — not before.

## 4. The graph data structure

- **Node** = one resident: `resident_id`, `ses`, `alive`, plus everything
  in §9 (traits, role, gender, age, occupation, is_noble). Phenomenon-
  specific state (e.g. SIR status) is stored separately from the base
  node, keyed by resident id, so multiple phenomena can run over the same
  graph without stepping on each other's state.
- **Edge** = `(resident_a, resident_b) -> attributes`, undirected in
  identity (at most one edge per pair) but directional in feeling.
  Attributes: `source_type` (TownShape's original label, or `spouse` once
  Romance retypes it — §11), `fiske_type`, `time`, `intimacy`, `services`
  (all shared — how much contact happens is mutual), and
  `valence_a_to_b`/`valence_b_to_a` (independent, §3.3).
- If TownShape's `relationships` table has more than one row for the same
  pair (e.g. coworkers who are also neighbors), the importer keeps the row
  with the highest synthesized `tie_strength` and drops the rest.
  <!-- ponytail: single dominant edge per pair, real multiplexity (De Domenico, §3.5)
       if a phenomenon ever needs to reason about *both* ties at once -->

## 5. Synthesizing edge attributes

TownShape's `relationships` rows carry a type and nothing else — no
numeric intensity, no valence. This prototype fills that gap with
deterministic, seeded synthesis: each edge's `time` / `intimacy` /
`services` / `valence_a_to_b` / `valence_b_to_a` are drawn from a
per-`relationship_type` baseline distribution (mean, spread), with the two
valence directions drawn as two *independent* `rng.gauss()` calls.

| `relationship_type` | time | intimacy | services | valence |
|---|---|---|---|---|
| `spouse` | high | high | high | skewed positive, wide spread |
| `parent`, `sibling` | high | high | high | skewed positive, wide spread |
| `unit_mate` | mid-high | mid | high | skewed positive (camaraderie) |
| `coworker` | mid | low | mid | centered on 0, moderate spread |
| `neighbor` | low | low | low | centered on 0, moderate spread |
| `classmate` | mid | low | low | centered on 0, wide spread |

"Wide spread" is what makes some siblings loving and others estranged, and
some coworkers friends and others rivals, without hand-authoring every
edge. The same `(db_path, seed)` pair always produces the same graph —
**but only for a given version of this code**: adding a new synthesized
field (a trait, an edge attribute) changes how many `rng` draws happen
during import and in what order, which shifts every draw downstream. Two
runs at the same seed only match byte-for-byte within the same commit.

**`shopkeeper_customer` is the one exception** — it isn't purely
synthesized, because real per-pair data already exists in
`shop_relationships`:

- `time` = the customer's `customer_score` for that shop, rescaled to
  0–1 across all shopkeeper-customer pairs (a regular at their primary
  shop scores high; someone who bought one thing once scores near 0).
- `services` = `purchase_count` for that pair, rescaled to 0–1 the same
  way (more transactions = more reciprocal exchange).
- `intimacy` and both valence directions are still synthesized (low
  `intimacy`, valence centered near 0 with a mild positive skew for
  `is_primary` pairs — you're more likely to be on decent terms with the
  shop you actually chose as your regular one).

## 6. The phenomenon engine

### 6.1 The generic interface

A `Phenomenon` is anything providing:

- `init_state(graph) -> {resident_id: state}` — starting per-node state.
  Since `edge_probability` below has no direct graph access, any static
  `Node` field a phenomenon needs (gender, role, a trait...) gets copied
  into this per-resident state at setup, rather than looked up live.
- `edge_probability(edge, state_a, state_b, day) -> float` — daily chance
  of the phenomenon "firing" across this edge, given both endpoints'
  current state.
- `apply_effect(graph, state, a, b, day, rng) -> list[Event]` — what
  happens when it fires: mutate `state`, optionally mutate *other* edges'
  attributes (this is how violence's grief/blame feedback works, §8), and
  return a record of what happened.
- `end_of_day(graph, state, day, rng) -> list[Event]` — runs once per
  phenomenon per day, after all edges have been rolled. Contagion uses it
  for recovery/fatality ticks (§7); Riots (§12) does *all* of its real
  work here instead, since a riot is a town-wide event, not a per-edge
  one — its `edge_probability`/`apply_effect` are always inert, which is
  cheaper than adding a second, town-wide hook to this interface for the
  one phenomenon that needs it.
- `summarize(state) -> {label: count}` — one line of the daily CSV.

Every phenomenon here is just an implementation of this interface — the
engine itself knows nothing about disease, violence, romance, riots, or
bribery specifically.

### 6.2 The daily loop

```
for day in range(days):
    for phenomenon in phenomena:
        for edge in graph.edges:
            a, b = edge.endpoints
            if not (graph.nodes[a].alive and graph.nodes[b].alive):
                continue
            p = phenomenon.edge_probability(edge, state[a], state[b], day)
            if p > 0 and rng.random() < p:
                events += phenomenon.apply_effect(graph, state, a, b, day, rng)
        events += phenomenon.end_of_day(graph, state, day, rng)
    record_daily_summary(day, phenomena, state)
```

Every day, every phenomenon, every edge gets one probability roll (the
random draw itself is only spent when `p > 0`, so a phenomenon that never
applies to an edge — e.g. Romance on two same-gender civilians — doesn't
consume a draw for it). This is the "generic phenomenon interface,
event-driven daily rolls" approach (Approach A) chosen over a single
shared diffusion equation, specifically because violence and riots need
structural effects (a node dying, neighboring edges' valence shifting)
that don't fit a compartment-style equation.

A structural consequence worth knowing: `state[resident_id]` is indexed
for *every* phenomenon on *every* edge regardless of what that
phenomenon's `edge_probability` does with it — so even a phenomenon whose
edges are always inert (Riots) still has to return a real per-resident
dict from `init_state`, one whose values just happen to never be read.

### 6.3 Why the graph doesn't change shape mid-run

Scope decision: the graph's *topology* (who is connected to whom) is fixed
for the duration of one simulated year, matching how TownShape itself
re-derives `relationships` once per year. Two kinds of things *do* change
day-to-day: node/edge **state** (SIR status, alive/dead, edge valence —
via grief_shock or a bribe), and, as of Romance (§11), an existing edge's
own **`source_type`** (retyped to `spouse` in place, rather than a new
edge being created). No phenomenon creates a *new* edge between two
residents who didn't already have one — a marriage can only happen between
people already connected some other way, and a newborn from Romance isn't
added as a graph node at all yet (§11) specifically to avoid this
constraint being violated by construction.

## 7. Phenomenon 1: Contagion (disease-like)

- **State:** `susceptible`, `infected` (with a remaining-days counter),
  `recovered`, or `deceased`.
- **`edge_probability`:** if exactly one endpoint is `infected` and the
  other `susceptible`: `base_rate * tie_strength * type_weight`, else `0`.
  `type_weight` is higher for household-equivalent ties (`spouse`,
  `parent`, `sibling`: 1.0) than for incidental ones (`shopkeeper_customer`:
  0.15).
- **`apply_effect`:** `susceptible -> infected`, staged so a transmission
  this morning can't also transmit onward this afternoon (see §6.3's
  note on same-day ordering).
- **`end_of_day`:** each `infected` node's counter ticks down; at zero, a
  fatality roll decides `recovered` vs. `deceased`:
  `fatality_p = min(1.0, case_fatality_rate * SES_VULNERABILITY[ses])`,
  where `SES_VULNERABILITY = {poor: 2.0, middling: 1.0, rich: 0.5}` — the
  same per-SES weighting Violence (§8) uses, for consistency, on the
  theory that poverty means worse access to care either way.

**Worked example (transmission):** two coworkers, `tie_strength = 0.4`,
`type_weight[coworker] = 0.3`, `base_rate = 0.5`. One is infected on day
12. Daily transmission chance to the other: `0.5 * 0.4 * 0.3 = 0.06`
(6%/day). Over the following 7 days, cumulative chance of transmission is
`1 - (1 - 0.06)^7 ≈ 34%`.

**Worked example (fatality, "calibrate the effective rate, not the
input" — a real lesson from tuning this):** trying to model the Black
Death with the historically-cited ~60% case-fatality rate directly as
`case_fatality_rate=0.6` produced ~97% town-wide mortality on a
96%-poor reference town, because `0.6 * 2.0 = 1.2`, clamped to 100% —
poor residents were already at the ceiling before the rate meant to
represent "60% overall" was even halfway applied. Using
`case_fatality_rate=0.25` instead gives poor residents an effective ~50%
(`0.25 * 2.0`), landing the *town-wide* mortality in the historically-cited
30–50% range once the population's actual SES mix is accounted for.
Always check the effective rate *per SES bracket*, not just the input
number, when tuning anything this weighting touches.

## 8. Phenomenon 2: Violence (animosity-driven)

- **State:** `alive` / `dead` (a phenomenon-local copy; the graph-wide
  truth is always `Node.alive`, since more than one phenomenon can now
  cause a death — see the engine's `alive`/`dead` daily-summary note).
- **`edge_probability`:** if both endpoints `alive`:
  `base_rate * max(-valence_a_to_b, -valence_b_to_a, 0.0) * tie_strength`,
  else `0`. The day's odds come from **whichever direction is more
  hostile**, not an average — a one-sided grudge is enough to make an
  edge dangerous even if the other person doesn't reciprocate it. Edges
  where *neither* direction is negative never fire this phenomenon.
- **`apply_effect` (`_pick_aggressor`):** the aggressor isn't picked by a
  coin flip or by SES alone. Each side's weight to be the one who snaps is
  `hostility_toward_other * vulnerability_of_other * (1 - own_loyalty)`:
  the angrier side is more likely to strike, a more vulnerable target
  (`SES_VULNERABILITY`, §7) makes that strike more likely to succeed, and
  a resident's own `loyalty` (§9) restrains them from acting on their
  hostility even when it's real. Whoever isn't the aggressor is the
  victim; their `alive` flips to `False`.
- **`grief_shock`:** for every *other* edge the victim had, if that
  neighbor also has an existing edge to the culprit, the neighbor's own
  outgoing valence toward the culprit is nudged further negative by
  `grief_shock * tie_strength(victim, neighbor)` — grief and suspicion
  spreading toward the culprit through people who were close to the
  victim, without inventing new edges that didn't already exist (§6.3).
  Only the bystander's own feelings move; the culprit's stored feelings
  toward that bystander are untouched.

**Worked example:** two neighbors, A and B. A's feeling toward B is
`valence_a_to_b = -0.25`; B's feeling toward A is `valence_b_to_a =
-0.11` — two independent random draws, not a shared number, so it's
already lopsided from day one. `tie_strength = 0.5`, `base_rate = 0.01`.
Daily probability uses the more hostile side (A's): `0.01 * 0.25 * 0.5 =
0.00125` (~0.125%/day). Over the year, five of B's other violent acts
happen to involve people A also knew, and each grief_shock nudges A's
*own* feeling toward B more negative — by day 11, A has actually grown
*angrier* at B than B ever was at A. But both are poor
(`vulnerability_a = vulnerability_b = 2.0`), so vulnerability doesn't
break the tie, and loyalty is near-default for both — the fight is close,
but B (whose hostility toward A, though smaller, is aimed at a target
whose own accumulated rage keeps them more reactive) still ends up
roughly 3-to-1 favored to strike first, and does, on day 273.

## 9. Personal traits and roles

**Technical:** four traits live on every `Node`, each independently
synthesized at import via `rng.gauss(0.5, 0.2)` clamped to `[0, 1]`, flat
and uncorrelated with `ses`:

| Trait | Read by |
|---|---|
| `loyalty` | Violence (aggressor restraint, §8), Riots (retreat/rout scaling, §12), Guards (bribe refusal, §13) |
| `cunning` | Guards (bribery success, §13) |
| `religiousness` | not yet consumed — reserved for Priests |
| `skepticism` | not yet consumed — reserved for Priests |

Also on `Node`: `gender`, `age` (whole years, computed at import against
`town_state.year_start`; `None` if either input is missing), `occupation`
and `is_noble` (both straight from TownShape), and a derived `role`
property: `is_noble` → `"noble"` (checked first — a noble who happens to
also guard isn't rank-and-file), `occupation == "guard"` → `"guard"`,
`occupation in ("priest", "acolyte")` → `"priest"`, else `"civilian"`.

**Plain language:** these are the quiet personality dials TownShape never
tracked. Loyalty is how much someone's own restraint holds them back from
acting on an impulse — snapping at a rival, taking a bribe, joining a mob.
Cunning is street-smarts. Role is just "what kind of person is this, for
the purposes of town-level mechanics" — most people are ordinary
civilians; a few are guards, nobles, or priests, derived from data
TownShape already tracks rather than invented fresh.

**Worked example:** two poor residents, X (`loyalty=0.9`) and Y
(`loyalty=0.1`), each equally hostile toward the same rich neighbor. In
Violence's aggressor weighting, X's own restraint factor is `1 - 0.9 =
0.1` versus Y's `1 - 0.1 = 0.9` — with identical hostility and identical
target vulnerability otherwise, Y is nine times more likely to be the one
who actually strikes. Loyalty doesn't change *whether* the edge is
dangerous (that's `edge_probability`, driven by hostility alone) — only
*who*, between two similarly-aggrieved people, is the one who breaks.

## 10. Town-wide aggression

**Technical:** `SocialGraph.town_aggression` (float, 0–1) is read from
`town_state.aggression` at import (defaults to `0.0`, "neutral", if the
table is absent — e.g. test fixtures). This is **TownShape's own**
town-generation dial — it already drives TownShape's own skirmish-event
generation — reused here rather than inventing a second one. `demo.py`
derives `aggression_factor = 1.0 + 2.0 * town_aggression` and applies it
to two phenomena: `ViolencePhenomenon.base_rate *= aggression_factor`, and
Riots' `unrest_threshold /= aggression_factor` while
`riot_base_rate *= aggression_factor` (an aggressive town reaches unrest
sooner *and* riots more often once it's reached).

**Plain language:** one number, set when the town itself was generated,
that says how volatile the place is. A peaceful town (`aggression=0`)
gets this simulation's baseline rates unchanged; a powder keg
(`aggression=1`) gets three times the violence rate and both an easier
trigger and a faster clock on riots.

**Worked example:** the reference town has `aggression=0.0` (TownShape's
own default), so `aggression_factor=1.0` and every rate above is used
as-is. Manually setting `town_aggression=1.0` for the same town (to
preview what a violent settlement would feel like) triples the violence
base rate and roughly halves the unrest threshold riots need to clear —
calibrated against real runs to produce ~1/5/4 riots per year at
aggression 0/0.5/1.0 respectively (not perfectly monotonic at any single
seed; each riot can thin the guard/noble pool for the rest of the year).

## 11. Romance & Marriage

- **State:** per resident, `married` (bool) plus a static copy of
  `gender`/`age` (§6.1's note on why `edge_probability` needs its own
  copies of things it can't look up live).
- **`edge_probability`:** two branches, keyed off the edge's own
  `source_type`.
  - **Not yet `spouse`:** `0` unless both residents are alive, adults
    (`age >= 18`, matching TownShape's own household-derivation
    threshold), opposite gender, neither already married (v1 has no
    divorce/remarriage), and the edge isn't `parent`/`sibling` (no
    incest). If eligible: `mutual_affinity = min(valence_a_to_b,
    valence_b_to_a)` — **both** sides must feel it, an unrequited crush
    never qualifies — and if `mutual_affinity > love_threshold`:
    `marriage_base_rate * (mutual_affinity - love_threshold) * tie_strength`.
  - **Already `spouse`:** if both alive, opposite gender, and both within
    `[18, FERTILE_MAX_AGE=45]`: `birth_base_rate * tie_strength`.
- **`apply_effect`:** marriage retypes the edge (`source_type = "spouse"`)
  in place — no new edge is created (§6.3). A birth is logged as an
  `Event` only; **no new `Node` is created yet** — every other
  phenomenon's state dict is fixed at day 0 and doesn't yet tolerate a
  resident appearing mid-run, so this is a deliberate, documented gap
  (a `Phenomenon.default_state` hook would be the way to fix it properly).

**Plain language:** two people who already know each other, are both
single, both like each other enough (not just one of them), and aren't
related, might fall in love and marry — a real event that changes the
edge itself. Married couples might then have a child, which for now is
just a note in the log ("a birth happened here") rather than an actual
new person joining the simulation.

**Worked example, and a real calibration finding:** on the reference town,
337 of ~1,911 residents' spouse edges already exist at import (674
married residents). The remaining unmarried-adult pool is small — about
140 residents — and of those, finding a pair who are *both* unmarried,
already connected by some edge, *and* clear the mutual-affinity threshold
is rarer still: often just 1 such pair town-wide in a given year. **~0–2
new marriages per year is therefore the realistic result of this data,
not the mechanic underfiring** — worth remembering before reflexively
raising `marriage_base_rate` to compensate. The real limiting factor is
structural: two unconnected singles can never meet here, since marriage
only happens over a pre-existing tie, and there's no "stranger" edge-
creation mechanic (yet).

## 12. Riots (town-wide, not per-edge)

Unlike every phenomenon above, a riot isn't a pairwise edge event, so all
of its real logic runs in `end_of_day` (§6.1); `edge_probability`/
`apply_effect` are always inert. A riot also **persists across days** as
explicit state (`self._active_riot`) rather than resolving in one call —
an earlier version resolved everything (guard deaths, retreat, noble
deaths) atomically on the triggering day, which had no real stopping
condition; it "stopped" only because the function returned. This section
describes the corrected, multi-day version.

### 12.1 Trigger

**Technical:** once a day (only while no riot is already active), average
hostility from every living `civilian`-role resident toward a
`guard`/`noble`-role neighbor they have a hostile edge to (precomputed
adjacency, since roles are static) is compared against `unrest_threshold`
(default `0.15`). If it's higher, a daily roll —
`riot_base_rate * (avg_hostility - unrest_threshold)` — decides if a riot
actually breaks out. Each hostile civilian's own worst grievance then
decides whether *they* join: `min(1.0, join_rate * hostility *
(1 - loyalty))`. Fewer than `min_participants` (default 3) joiners and the
riot fizzles without effect.

**Plain language:** the town's general mood toward its authorities has to
be genuinely sour, not just slightly negative, before a riot can even be
considered — and even then, whether it actually happens that day is a
roll of the dice weighted by how sour. Once it's happening, people don't
join a riot just because they're personally furious; a loyal person holds
back even at the same anger level a disloyal person would act on (same
idea as Violence's aggressor restraint, §8/§9).

**A real calibration bug, found from this exact symptom:** the first
version's default (`unrest_threshold=0.25`) sat almost exactly *on* the
reference town's natural baseline hostility (measured at ~0.25–0.26
across several seeds) — since the trigger odds scale with how far
*above* the threshold that baseline sits, a near-zero margin meant
near-zero odds, and several seeds in a row producing zero riots is what
surfaced it. Fixed by dropping the threshold to `0.15` (real margin below
the baseline) and raising `riot_base_rate` to `0.03`. Verified the
mechanism itself was never broken by isolating it from the full
simulation's shared RNG stream (see `docs/decisions.md`): 20 of 30
independent year-long trials produced at least one riot at the corrected
values.

### 12.2 Guard phase — mutual combat

**Technical:** while `not guards_retreated`, guards and rioters trade
casualties **simultaneously** each day: independent rolls for every
living guard and every living participant, both using that day's
starting counts, applied in full before either retreat condition is
checked (not sequential with an early exit — see §12.4 for why that
distinction matters).

- `p_death_guard = min(death_cap, guard_lethality * living_participants / living_guards)`
- `p_death_rioter = min(death_cap, rioter_lethality * living_guards / living_participants)`

`guard_lethality` (default `0.3`) is lower than `rioter_lethality`
(default `0.6`) — guards are armed and trained, so at equal force sizes a
rioter is roughly twice as likely to die that day as a guard.

Two ways the fight can end that day:

- **Guards retreat** once `guard_deaths / initial_guard_count >=
  effective_guard_retreat_threshold`, or every guard has fallen. That
  threshold scales with the guards' own average `loyalty` at riot start:
  `retreat_threshold * (0.5 + avg_guard_loyalty)` — `0.5` is the trait's
  own default mean, so an average-loyalty garrison reproduces the plain
  `retreat_threshold` unchanged; a disloyal one breaks sooner, a loyal
  one holds longer. Guards retreating exposes nobles (§12.3).
- **Rioters rout** once `rioter_deaths / initial_participant_count >=
  effective_rioter_retreat_threshold` (checked only if guards *didn't*
  also just retreat this same day). That threshold scales the same way,
  but by the mob's own animosity: `rioter_retreat_threshold * (0.5 +
  avg_participant_hostility)`, using each joiner's own worst grievance at
  the moment they joined. An enraged mob absorbs more losses before it
  breaks than a lukewarm one. **Routing ends the riot outright — nobles
  are never exposed; guards successfully defended.**

If neither side breaks, both phases repeat the next day with the
survivors.

**Plain language:** think of it as one running battle, not a single dice
roll. Every day the fight continues, both sides can lose people, but the
guards (better equipped) lose people more slowly than the mob does. The
fight only really ends one of two ways: either the guards take enough
losses that the survivors panic and run (letting the mob through to the
nobles), or the mob takes enough losses first that *they're* the ones who
break and scatter, and the guards hold the town.

**Worked example:** 71 rioters vs. ~40 guards (reference town, day 89–90).
`p_death_guard = min(0.9, 0.3*71/40) = 0.53` per guard per day —
guards took ~11 casualties before an average-loyalty garrison's threshold
(`0.3 * 1.0 = 0.3`, i.e. 30% of ~40 ≈ 12) was crossed and they broke.
`p_death_rioter = min(0.9, 0.6*40/71) = 0.34` per rioter that same day —
18 rioters also fell in the same exchange, since both sides are now
rolled simultaneously rather than the mob only being shot at on days
guards *didn't* already retreat.

> **Calibration target, flagged for a future pass (user, 2026-09-17):**
> ~11 guards to ~18 rioters here is nowhere near "guards are armed and
> trained" — the user's own read is that the ratio should land closer to
> **1 guard dead for every ~3 rioters dead**, i.e. `rioter_lethality`
> should end up several times `guard_lethality`, not the current 2×
> (`0.6` vs `0.3`). Recorded here deliberately rather than changed
> immediately — the constants are correct in *shape* (guards safer per
> capita) but not yet in *magnitude*. Next time this mechanic is touched,
> retune `guard_lethality`/`rioter_lethality` (or their ratio) against
> real runs until the emergent guard:rioter death ratio lands near 1:3,
> and update this worked example's numbers to match.

### 12.3 Noble phase — personal hatred, not a flat rate

**Technical:** once guards have retreated, nobles are ranked by
`_hatred_toward` — the **sum** of hostile valence directed at them from
*everyone* who knows them, not just this riot's participants — and
targeted most-hated-first. Each living noble's death chance is
proportional to their hatred *relative to the average* among living
nobles: `min(death_cap, noble_lethality * participants / nobles *
(hatred[n] / avg_hatred))`. Every kill decrements a **riot bar** —
`max(1, round(riot_bar_per_participant * initial_participant_count))`,
e.g. 8 for a 77-person mob at the default `0.1` — by exactly 1. **The
riot ends the moment the bar hits zero or no nobles are left**,
whichever comes first; a `riot_ends` event fires and the riot's state
clears.

**Plain language:** once the town's defenders are gone, the mob doesn't
attack nobles at random or in proportion to how rich they are — they go
after whoever the town *specifically* despises most, working down the
list, until their collective bloodlust (sized off how big and furious the
original mob was) is spent.

**Worked example:** in a real run, the two most-hated nobles in the
entire town (hatred scores ~70, versus a distant third-place noble at
~17 and a town-wide average around 10) were the first two killed once
guards broke — not because they were richest or most exposed, but because
`_hatred_toward` ranked them so far above everyone else that their
relative-hatred multiplier alone put their death chance near the cap. The
riot's bar (7, for a 71-person mob) wasn't spent by day one alone;
it continued into a second day, working down to the next few most-hated
nobles until exactly 7 kills emptied it.

### 12.4 Why "simultaneous, not sequential" matters

An earlier version processed guards first in a loop with an early exit
the instant they retreated, then only rolled against rioters *if that
loop finished without a guard retreat*. Since guards almost always broke
within the very first day at default lethality (many independent rolls,
each with a real chance of hitting, all processed in the one call before
retreat was even checked), rioters were essentially never exposed to
risk — the mob could riot indefinitely at zero personal cost. Restructured
per direct user feedback ("how many rioters died? that should also be
taken into account") so both sides always take their day's rolls before
either retreat condition is evaluated. This is also what makes a rout
possible at all: with the old early-exit ordering, rioters could never
accumulate enough of their *own* casualties to break, since the loop
would already have moved past them the moment guards happened to retreat
first.

## 13. Guards: bribery

The vision doc's fuller Guards mechanics (arrest behavior, patron
protection) depend on things that don't exist yet — Criminals, and a
cross-phenomenon link so Guards could observe what Violence produced —
so this is deliberately scoped to bribery alone, which is self-contained.

- **`edge_probability`:** only between a `civilian` and a `guard` they're
  actually connected to (a real edge, not an abstract class-wide tie —
  see the note in §9 about `role` being individual residents, not an
  institution): `bribe_base_rate * civilian.cunning *
  wealth_factor[civilian.ses] * (1 - guard.loyalty) * tie_strength`,
  where `wealth_factor = {poor: 0.5, middling: 1.0, rich: 2.0}` (a
  bribe-affordability proxy — there's no town-wide wealth aggregate yet).
- **`apply_effect`:** raises only the guard's own outgoing valence toward
  the briber, clamped at `1.0`. Nothing else changes.

**Plain language:** a resident who's clever and can afford it might bribe
a guard they know. Whether the guard *accepts* depends on the guard's own
integrity — a loyal guard turns down far more bribes than a corruptible
one, at the same offer.

**Worked example, and a real calibration correction:** the first version
(no loyalty dependence, `bribe_base_rate=0.01`) produced ~471 bribes/year
on the reference town — corruption-city numbers for what should be an
ordinary settlement. Per direct user feedback ("that number should exist
only in a low loyalty, high corruption city... make acceptance lower, far
lower"), adding the `(1 - loyalty)` restraint (which alone halves the
rate at the trait's own default mean of 0.5) and cutting the base rate
10× together brought it to ~8–25/year across several runs — roughly one
bribe per guard every year or two, not one every couple of weeks. Loyalty
alone only gives about a 2× town-to-town swing, though (since it's
bounded to `[0, 1]`); a real high/low-corruption *contrast* between towns
likely needs the town-wide **corruption** parameter already flagged as a
candidate dial in the roadmap, multiplying this rate too — not built yet.

## 14. Output

- **Daily summary** (`output/summary.csv`): one row per simulated day,
  with every phenomenon's `summarize()` counts merged together (e.g.
  `day,susceptible,infected,...,married_residents,births,riots,...,bribes`).
- **Event log** (`output/events.json`): one entry per fired event —
  `{day, phenomenon, kind, resident_a, resident_b, detail}` — the intended
  hook for narrative generation later.
- A short printed summary at the end of a run (totals, peak simultaneous
  infected, total deaths broken down by cause).

## 15. File layout

```
social-sim-demo/
  graph.py       # SocialGraph, Node, Edge, import_snapshot()
  phenomena.py   # Phenomenon protocol + Contagion/Violence/Romance/Riot/Guard
  engine.py      # run_simulation()
  demo.py        # CLI: import a snapshot, run every phenomenon, write output/
  tests/
    run_all.py           # aggregate test runner, no framework
    test_*.py             # one file per module/phenomenon, assert-based
  docs/
    2026-09-15-social-network-design.md   # this file
    decisions.md                          # why, not what/how -- see there
  Project_Vision/
    01-network-simulation.md   # current-state + roadmap, topic-organized
  Project-Memory/
    *.md   # dated session narratives -- read before touching code you weren't there for
  README.md
```

## 16. Explicitly out of scope for this prototype

- Writing back to TownShape's database, or changing its schema in any way.
- The graph's topology changing mid-run in the sense of *new edges being
  created* between previously-unconnected residents (§6.3) — an existing
  edge's `source_type` can be retyped (Romance, §11) and attributes can
  change (valence via grief_shock/bribery), but no phenomenon invents a
  connection that wasn't already there. This is also why a Romance-born
  child isn't a real graph `Node` yet (§11) and why two unconnected
  singles can never meet (§11's worked example).
  <!-- ponytail: personal-trait system now exists (§9); the deferred item
       below narrows to *decision-making driven by* traits, not the traits
       themselves -->
- Per-resident agent decision-making beyond what traits (§9) already
  drive (mood/personality-weighted probabilities are now real, e.g.
  loyalty throughout §8/§12/§13 — but nothing here reasons or plans, it
  only weights a roll).
- ABI trust, advice/trust/communication layering, House's support
  taxonomy, full multilayer graphs, cognitive social structures — see
  §3.5 for why each is deferred and what would trigger revisiting it.
- Narrative-mode integration itself — only the event log shape is
  designed with it in mind.
