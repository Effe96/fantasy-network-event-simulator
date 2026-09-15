# Social Interaction Network — Concepts & Design

## 1. Purpose

A standalone prototype, sibling to the `TownShape` repo, exploring one question:
**can a generic engine, given a social graph, simulate very different
"things that spread" — a disease and a wave of violence — using the same
mechanism?**

It reads a one-time, read-only snapshot of residents and relationships out
of a real TownShape town database, enriches that graph with attributes
TownShape doesn't store today, and runs day-by-day simulations over it.
Nothing here writes back to TownShape, and TownShape's own database schema
is untouched — this project only *reads* `residents` and `relationships`
from one `.db` file.

The output (a plain event log: "on day 40, a violent event happened between
resident 12 and resident 88") is deliberately shaped to be a good input for
narrative generation later, though wiring that up is out of scope here.

## 2. Where the data comes from

TownShape already derives relationships between residents — family,
coworker, neighbor, military unit-mate, and classmate ties — into a
`relationships` table (see `town_relationships/` in the TownShape repo).
It also has a separate `shop_relationships` table, but that links a
resident to a *shop building*, not to another resident, so it can't become
an edge in a person-to-person graph and isn't used here. This project
imports one snapshot of `residents` + `relationships` from a chosen `.db`
file (`demo_svg_overlay_town.db` — 832 residents, ~17,000 relationship
rows spanning coworker/neighbor/parent/sibling/spouse/unit_mate — is the
sample used during development). The import is one-time and read-only:
this project never opens that file for writing.

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

**Technical:** a signed score, `valence ∈ [-1, +1]`, where -1 is pure
animosity and +1 is pure affection. This is the one attribute this
prototype's violence mechanic actually depends on.

Because `intensity` (above) is magnitude-only, `tie_strength` is
recomputed using `|valence|` in place of `intensity`:

`tie_strength = mean(time, |valence|, intimacy, services)`

**Plain language:** a screaming rivalry and a tight friendship can both be
"intense" — same magnitude, opposite direction. `valence` is that
direction. Using `|valence|` in `tie_strength` means an intense rivalry
counts as just as much "contact opportunity" for a disease to spread as an
intense friendship does — it's the *sign* of valence, not its size, that
decides whether that contact helps or harms.

**Worked example:** a married couple has `time=0.9, intimacy=0.9,
services=0.9`. If `valence=+0.8` (a loving marriage), `tie_strength =
mean(0.9, 0.8, 0.9, 0.9) = 0.875` — high contact, positive relationship.
If instead `valence=-0.8` (a marriage in the middle of a bitter feud),
`tie_strength` is *unchanged* at `0.875` — they still see each other
constantly — but this edge is now a live candidate for the violence
phenomenon (§8), while the first one isn't.

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

| TownShape `relationship_type` | Fiske tag |
|---|---|
| `parent`, `sibling`, `spouse` | Communal Sharing |
| `unit_mate` | Equality Matching |
| `coworker` | Authority Ranking |
| `neighbor` | Equality Matching |
| `classmate` | Communal Sharing |

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
  vs. who-you'd-confide-in vs. who-you-actually-talk-to; both current
  phenomena treat a coworker tie as one thing.
- **House's 4-part support taxonomy** — a finer breakdown of `services`;
  not needed until a phenomenon cares about *what kind* of favor is
  exchanged.
- **Full multilayer graph formalism** (De Domenico et al.) — the doc's own
  guidance is to adopt this once more than ~2 relationship types must be
  modeled simultaneously without collapsing to one score. Two phenomena,
  one score per edge, is comfortably under that bar.
- **Cognitive Social Structures** (perceived-vs-actual graph, Krackhardt
  1987) — nobody's *perception* of the graph matters yet, only the graph
  itself.

Revisit any of these the moment a specific phenomenon needs the extra
resolution — not before.

## 4. The graph data structure

- **Node** = one resident: `id`, plus the raw fields carried over from
  TownShape (`age`, `occupation`, `home_building_id`, ...), plus `alive:
  bool`. Phenomenon-specific state (e.g. SIR status) is stored separately
  from the base node, keyed by resident id, so multiple phenomena can run
  over the same graph without stepping on each other's state.
- **Edge** = `(resident_a, resident_b) -> attributes`, undirected, at most
  one edge per pair. Attributes: `source_type` (TownShape's original
  label), `fiske_type`, `time`, `intimacy`, `services`, `valence`,
  `tie_strength`.
- If TownShape's `relationships` table has more than one row for the same
  pair (e.g. coworkers who are also neighbors), the importer keeps the row
  with the highest synthesized `tie_strength` and drops the rest.
  <!-- ponytail: single dominant edge per pair, real multiplexity (De Domenico, §3.5)
       if a phenomenon ever needs to reason about *both* ties at once -->

## 5. Synthesizing edge attributes

TownShape's `relationships` rows carry a type and nothing else — no
numeric intensity, no valence. This prototype fills that gap with
deterministic, seeded synthesis: each edge's `time` / `intimacy` /
`services` / `valence` are drawn from a per-`relationship_type` baseline
distribution.

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
edge. The same `(db_path, seed)` pair always produces the same graph.

## 6. The phenomenon engine

### 6.1 The generic interface

A `Phenomenon` is anything providing:

- `init_state(graph) -> {resident_id: state}` — starting per-node state.
- `edge_probability(edge, state_a, state_b, day) -> float` — daily chance
  of the phenomenon "firing" across this edge, given both endpoints'
  current state.
- `apply_effect(graph, state, a, b, day, rng) -> list[Event]` — what
  happens when it fires: mutate `state`, optionally mutate *other* edges'
  attributes (this is how the violence phenomenon's grief/blame feedback
  works, §8), and return a record of what happened.

Disease and violence are both just implementations of this interface —
the engine itself knows nothing about either.

### 6.2 The daily loop

```
for day in range(days):
    for phenomenon in phenomena:
        for edge in graph.edges:
            a, b = edge.endpoints
            if not (graph.nodes[a].alive and graph.nodes[b].alive):
                continue
            p = phenomenon.edge_probability(edge, state[a], state[b], day)
            if rng.random() < p:
                events += phenomenon.apply_effect(graph, state, a, b, day, rng)
    record_daily_summary(day, phenomena, state)
```

Every day, every phenomenon, every edge gets one probability roll. This is
the "generic phenomenon interface, event-driven daily rolls" approach
(Approach A) chosen over a single shared diffusion equation, specifically
because the violence phenomenon needs a structural effect (a node dying,
neighboring edges' `valence` shifting) that doesn't fit a compartment-style
equation.

### 6.3 Why the graph doesn't change shape mid-run

Scope decision: the graph's *topology* (who is connected to whom) and each
edge's *base* attributes are fixed for the duration of one simulated year,
matching how TownShape itself re-derives `relationships` once per year.
Only *state* — SIR status, alive/dead, and edge `valence` (which the
violence phenomenon does update as feedback) — changes day-to-day. New
ties forming from repeated contact, or old ties fading, is out of scope
for this prototype (see §11).

## 7. Phenomenon 1: Contagion (disease-like)

- **State:** `susceptible`, `infected` (with a remaining-days counter),
  `recovered`.
- **`edge_probability`:** if exactly one endpoint is `infected` and the
  other `susceptible`: `base_rate * tie_strength * type_weight`, else `0`.
  `type_weight` is higher for household-equivalent ties (`spouse`,
  `parent`, `sibling`) than for incidental ones (`classmate`, `neighbor`).
- **`apply_effect`:** `susceptible -> infected`; separately, each `infected`
  node's counter ticks down each day and flips to `recovered` (immune) at
  zero, independent of any edge roll.

**Worked example:** two coworkers, `tie_strength = 0.4`,
`type_weight[coworker] = 0.3`, `base_rate = 0.5`. One is infected on day
12. Daily transmission chance to the other: `0.5 * 0.4 * 0.3 = 0.06`
(6%/day). Over the following 7 days, cumulative chance of transmission is
`1 - (1 - 0.06)^7 ≈ 34%`.

## 8. Phenomenon 2: Violence (animosity-driven)

- **State:** `alive` / `dead`.
- **`edge_probability`:** if both endpoints `alive`:
  `base_rate * max(0, -valence) * tie_strength`, else `0`. Positive-valence
  edges (`valence >= 0`) never fire this phenomenon at all.
- **`apply_effect`:** one endpoint is chosen as the victim (weighted, e.g.
  toward lower `ses` — a placeholder rule, easy to swap), the other is the
  "culprit" for this event. The victim's `alive` flips to `False`. Then,
  for every *other* edge the victim had, if the person on the far end of
  that edge also has an existing edge to the culprit, that edge's
  `valence` is nudged further negative — grief and suspicion spreading
  toward the culprit through people who were close to the victim, without
  inventing new edges that didn't already exist (per §6.3).

**Worked example:** two neighbors, A and B, `valence = -0.7`, `tie_strength
= 0.5`, `base_rate = 0.01`. Daily probability: `0.01 * 0.7 * 0.5 =
0.0035` (0.35%/day; ~72% cumulative it never fires in a year). Say it
fires on day 200 and B is chosen as the victim, A as the culprit. B had a
separate edge to C (a mutual friend) with `valence = +0.6`. Since C also
has an existing edge to A, C's `valence` toward A drops by a
`grief_shock` amount proportional to C's `tie_strength` with B — C didn't
witness anything, but their friend is dead and the culprit is someone they
already knew, so their feelings toward A sour. If C had *no* existing edge
to A, nothing changes for C — this prototype doesn't create new edges (a
real "a stranger becomes a suspect" mechanic is future work, §11).

## 9. Output

- **Daily summary** (`output/summary.csv`): one row per simulated day per
  phenomenon, with counts per state (e.g.
  `day,susceptible,infected,recovered,alive,dead`).
- **Event log** (`output/events.json`): one entry per fired event —
  `{day, phenomenon, kind, resident_a, resident_b, detail}` — the intended
  hook for narrative generation later.
- A short printed summary at the end of a run (totals, peak simultaneous
  infected, total deaths).

## 10. File layout

```
social-sim-demo/
  graph.py       # SocialGraph, import_snapshot()
  phenomena.py   # Phenomenon protocol, ContagionPhenomenon, ViolencePhenomenon
  engine.py      # run_simulation()
  demo.py        # CLI: import a snapshot, run both phenomena, write output/
  tests/
    test_engine.py   # assert-based self-check, no framework
  docs/
    2026-09-15-social-network-design.md   # this file
  README.md
```

## 11. Explicitly out of scope for this prototype

- Writing back to TownShape's database, or changing its schema in any way.
- The graph's topology changing mid-run (new edges forming, old ones
  disappearing) — attributes on *existing* edges can change (§6.3, §8),
  the set of edges cannot.
- Per-resident agent decision-making (mood/personality driving individual
  choices rather than fixed per-edge probabilities) — a future direction
  the user explicitly wants to keep open. The interfaces already support
  it without a rewrite: `edge_probability` and `apply_effect` receive the
  full node `state` objects, not bare numbers, so a future `state` could
  carry a personality/mood field these functions read, with no change to
  the engine's daily loop.
- ABI trust, advice/trust/communication layering, House's support
  taxonomy, full multilayer graphs, cognitive social structures — see
  §3.5 for why each is deferred and what would trigger revisiting it.
- Narrative-mode integration itself — only the event log shape is
  designed with it in mind.
