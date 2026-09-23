# TownShape integration: residents added mid-run, and how the two could merge

> Written 2026-09-23 with pipeline step 3 ("adding residents mid-run").
> Part 1 is what changed in this repo and why it was shaped this way. Part 2
> is how TownShape creates and advances its population today. Part 3 maps
> the two data models. Part 4 lays out the integration options, with a
> recommendation. Part 5 lists the gaps any option has to close.

## 1. What changed in social-sim-demo (step 3)

Before this step every phenomenon built its per-resident state once, on day
1, and the engine assumed the set of ties never changed. A resident added
later had no state anywhere. The change makes a newcomer possible **through
the same code path as import**, fed data shaped like TownShape's own tables,
so a TownShape birth (or a future sim-created resident) enters identically.

- **One construction path.** `graph.node_from_resident_row(graph, row, rng)`
  builds a resident from a TownShape `residents`-shaped row (`id, ses,
  gender, birth_date, occupation, is_noble, household_id, home_building_id,
  workplace_building_id`); `graph.edge_from_relationship(graph, a, b, type,
  rng)` builds a tie of a TownShape `relationships` type (`spouse, parent,
  sibling, unit_mate, coworker, neighbor, classmate`). Import now uses both,
  so a newcomer gets exactly the same treatment as a day-1 resident: family-
  correlated faith and skepticism, the ex-soldier roll, synthesized tie
  strength and feelings, the noble/poor resentment skew.
- **What the graph keeps after import** so a newcomer can be built later:
  `graph.family_root` / `graph.family_baselines` (each family's shared trait
  centre, so a newborn inherits their family's tendency), `graph.
  building_districts` (home building -> district, for quarantine),
  `graph.reference_year` (for age).
- **TownShape identity on every resident.** `Node` gained `household_id`,
  `home_building_id`, `workplace_building_id` and `birth_date`, read from
  the `residents` table at import (no randomness, so every seed's import is
  unchanged). `resident_id` already *is* `residents.id`.
- **`graph.add_resident(row, relationships, rng)`**: add a person plus
  TownShape-typed ties to residents already in town, e.g. `[(mother, "parent"),
  (father, "parent")]`; the id defaults to `graph.next_resident_id()`
  (max + 1, the same rule TownShape's AUTOINCREMENT follows). The newcomer
  is queued in `graph.newcomers`.
- **The engine registers newcomers** at the end of the phenomenon that
  created them: every phenomenon's new `add_resident(graph, state, id)`
  builds the newcomer's state with the same helper its `init_state` uses and
  updates any cache built from ties (riot's authority links, religion's
  priest ties and baseline religiousness, quarantine's authority ties, the
  guard-tie list, contagion's districts, romance's married flags, theft's
  guard loyalty average). Their new ties join the fixed tie order the
  speed-up relies on. A phenomenon without `add_resident` fails loudly.
- **Nothing creates residents yet.** Deciding *who* creates them is step 4,
  and it's the main decision below.
- **Verified:** with nobody added, seeds 3 and 1 reproduce a full year byte
  for byte; `tests/test_newcomers.py` covers the construction path, id
  rules, every phenomenon taking on a mid-run newcomer, and a newborn
  catching the disease from a parent.

## 2. How TownShape creates and advances its population

**Initial generation** (`scripts/generate_town.py` ->
`town_narrative.generate.generate_town_from_parameters`, then
`town_relationships.generate.derive_relationships`):
1. `town_shaper` builds the map (settlemaker districts and buildings) and
   `assign_residents` draws households' SES and places them in homes and
   job vacancies (rich households first since `f348561`).
2. `town_db.households.build_households_and_residents` turns those slots
   into `households` and `residents` rows: names, race, gender, birth date
   by age bracket, SES, home, workplace, occupation; then tags nobles (from
   rich adults in the rich district first) and magical talent.
3. `town_db.persistence` inserts everything; the year's vital records,
   purchases, taxes, school and military service are generated too.
4. `derive_relationships` derives `relationships` (family from households
   and births, coworkers, neighbours, military unit-mates, classmates) and
   `shop_relationships` from purchases.

**Advancing a year** (`town_db.simulation.advance_town(db_path, seed,
years)`), one 365-day year at a time from `town_state.current_date`:
income; disease events; **births and deaths** (`vital_records`: a birth is
a child row in a household with a fertile mother, inheriting her SES, home
and race, plus a `births` row; deaths by age bracket, raised during disease
events, recorded in `deaths` with a cause and the temple as reporter);
skirmish casualties; **household formation** (adults leaving home, couples
forming new households in vacant homes); **job market** (vacancies filled,
apprentices promoted on a master's death); purchases; taxes; school and
military enrolment; then `derive_relationships` **deletes and re-derives
every relationship** from the new state.

**External edits** (`town_db.edits`): `kill_resident(db_path, resident_id,
death_date, cause, ..., promote_replacement)` records a death exactly the
way the sim would need to write one back: `residents.death_date`, a
`deaths` row with cause and reporting temple (guard post for skirmishes),
optional apprentice promotion, and cleanup of purchases, taxes, military and
school spans.

**Conventions a change to TownShape must respect** (`TownShape/CONTRACTS.md`):
raw SQL via `sqlite3`, no new dependencies, every random draw through
`town_shaper.seeding.rng_for(seed, *parts)`, a year is exactly 365 days,
`"current_date"` must be quoted when read, shared interfaces are listed in
CONTRACTS.md before they change.

## 3. Mapping the two data models

| Social sim | TownShape | Notes |
|---|---|---|
| `Node.resident_id` | `residents.id` | identical |
| `Node.ses, gender, occupation, is_noble` | same columns | identical values |
| `Node.age` | from `residents.birth_date` and `town_state.year_start` | recomputed, whole years |
| `Node.household_id, home_building_id, workplace_building_id, birth_date` | same columns | new in step 3 |
| `Node.district_id / district_zone` | `buildings.district_id` -> `districts.zone_type` | via the home building |
| `Node.religiousness, skepticism, cunning, loyalty, is_ex_soldier` | *none* | sim-only, synthesized; lost unless persisted |
| `Edge` (a, b, `source_type`) | `relationships` (a, b, `relationship_type`) | same types; `shopkeeper_customer` from `shop_relationships` |
| `Edge` time / intimacy / services / feelings | *none* | sim-only, synthesized; evolve daily |
| `graph.deaths` (id, day, cause, killed_by) | `deaths` (resident_id, death_date, cause, reported_by_building_id) | day -> `current_date + day`; `killed_by` has no column |
| `graph.recoveries` | `illnesses` (not yet read) | worth reconciling |
| sim epidemic outbreaks | `disease_events` | two separate disease models today |
| `graph.params.aggression` | `town_state.aggression` | read at import; other params sim-only |
| day index | `town_state."current_date"` | sim days are relative; need the start date |

**Death causes.** TownShape uses `illness`, `accident`, `childbirth`,
`old age`, `plague` and skirmish deaths; the sim uses `plague`, `flu`,
`diarrhea`, `violence`, `riot`, `execution`, `coup`. A write-back needs a
mapping (e.g. flu/diarrhea -> `illness`, riot -> a skirmish, violence and
coup kept as new causes) or TownShape accepting the sim's vocabulary.

## 4. Integration options

**A. Coupled yearly loop (recommended).** Each system owns what it models
best: **TownShape owns demography and the economy** (births, ageing,
households, jobs, school, military, income, purchases, taxes) at yearly
resolution; **the social sim owns daily social life** (feelings, violence,
riots, crime, religion, epidemics, quarantine, coups). Per simulated year:
1. The sim runs 365 days on the graph.
2. Write back: each sim death via `kill_resident` (or `insert_deaths`),
   dated `current_date + day`, cause mapped; optionally new state TownShape
   has columns for (none yet besides deaths).
3. `advance_town(years=1)` produces births, new households, job changes
   and re-derived relationships. **Its own overlapping causes of death must
   be switched off or split by ownership** (e.g. TownShape keeps old age,
   childbirth, accidents; the sim owns epidemics, violence, riots,
   executions), or people die twice over.
4. Merge back into the graph: new `residents` rows -> `graph.add_resident`
   (row as-is, ties from the new `relationships` rows touching them);
   changed residents (moved, married, new job) -> an `update_resident` hook
   (not built yet); relationship delta -> new pairs become new ties, pairs
   that vanished (moved away, changed job) keep their feelings but lose or
   change type; **existing ties keep their feelings** (re-derivation is
   destructive in TownShape, so this must be a merge, never a re-import).

*Pros:* no duplicated demography; TownShape's names, households and jobs
stay authoritative; each side keeps its resolution. *Cons:* needs the
update hook, the relationship merge, the cause ownership split, and a
place to persist sim-only state between sessions.

**B. Sim-native turnover, written back later.** The sim creates births and
arrivals itself, daily, through `graph.add_resident` with TownShape-shaped
rows, and a later write-back inserts them via `insert_residents` /
`insert_births` (ids line up by the max + 1 rule, but map them
defensively). *Pros:* quickest path to a stationary population and to
multi-year runs; no dependency on TownShape changes. *Cons:* duplicates
TownShape's birth, naming and household logic, and the two drift apart.

**C. Full merge into TownShape** (a `town_social` package driven from
`advance_town` at daily resolution). *Pros:* one system, one database, one
RNG convention. *Cons:* the largest change, across a shared repo with a
collaborator and a contracts process; the sim's daily loop would dominate
`advance_town`'s runtime.

**Recommendation:** A as the target. Because it depends on TownShape-side
changes (cause ownership, maybe new tables) that touch a shared repo, it's
worth deciding with the user whether step 4 builds A directly or starts
with B's births inside the sim as a stopgap that A later replaces. Step 3
was built so that either works: both feed the same `add_resident`.

## 5. Gaps any option has to close

- **Sim-only state isn't persisted.** Traits, tie feelings and phenomenon
  state live in memory. Crossing a year boundary through TownShape (A), or
  resuming a session, needs either new TownShape tables (e.g. per-resident
  traits and per-tie social state) or a sim-side save file.
- **An `update_resident` hook** for residents whose TownShape fields change
  (moved home, new job, married), mirroring `add_resident`.
- **Relationship merge** rather than re-import, keeping feelings.
- **Two disease models** (sim epidemics vs TownShape `disease_events` and
  `illnesses`) and **two sources of violent death** (sim violence and riots
  vs TownShape skirmishes) need one owner each.
- **Dates:** the sim counts days from 1; TownShape keeps
  `town_state."current_date"`. Write-backs need the run's start date.
- **Randomness:** TownShape derives every draw via `rng_for(seed, *parts)`;
  the sim uses one `random.Random(seed)` stream. A coupled loop should pass
  a derived seed per year to each side so both stay reproducible.
- **Town parameters:** only `aggression` exists on both sides; loyalty,
  religiosity and strictness are sim-only for now and could become
  `town_state` columns if TownShape should know them.
