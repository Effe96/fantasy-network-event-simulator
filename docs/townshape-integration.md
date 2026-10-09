# TownShape integration: what each side needs to implement

> Rewritten 2026-10-09 around the user's picture of the two tools (first
> version 2026-09-23). Grouped by priority; each item says what exists today,
> what is needed, and on which side. Checked against TownShape at `7e1d02a`
> and `demo_riverport_town.db`.

## 0. The picture (user, 2026-10-09)

1. **Starting a town creates everything it needs:** the physical town (map,
   districts, buildings), households and people with names and every
   feature, their ties, jobs, money and the town's parameters.
2. **From then on this simulator drives every interaction and every
   development of the town:** births, deaths, marriages, newcomers, jobs,
   trade, crime, faith, building. TownShape's own yearly advance
   (`advance_town`) is retired for these towns: it would re-derive every
   relationship and add a second set of births and deaths.
3. **What the sim builds appears in the physical town:** new houses, shops
   and workshops get a place on the map.

**Decided (user, 2026-10-09): one creation pipeline, both tools.** "Create
town" runs TownShape's generator, then the sim's setup (traits, tie strength
and feelings, the jobs TownShape doesn't make, money, property, houses, class
lines), and saves everything into the town's database. Each tool keeps the
code it already has; nothing is written twice.

**The town database is the single source of truth.** Everything the sim
knows lives there, so one file is the whole town at any point in its history,
and the sim can stop and resume from it.

## 1. Priority 1: creating a complete town

**1.1 Tables for the sim's state (TownShape schema; the sim writes them).**
New tables, keyed by TownShape ids:
- per resident: religiousness, skepticism, cunning, loyalty, ex-soldier,
  stress, beggar, thief (`resident_traits`);
- per tie: time, intimacy, services, both feelings, former type (columns on
  `relationships`, or a `relationship_state` table);
- per household: cash, land outside the walls, debts, rent arrears, usual
  income (`households.wealth` can hold cash plus property in florins);
- per house: owner, value, room, building in progress (`house_tenure`);
- the town: the commune's and the Church's money, class lines, granary, the
  rich's grain hoards, workshop stocks and accounts, merchants' warehouses
  and cargoes at sea, new farms and who works them, the sim's clock and its
  parameters (loyalty, religiosity, strictness, beside `aggression` in
  `town_state`).

A few tables with JSON columns for the town-level state are enough to start;
they can be split later if TownShape needs to query them.

**1.2 The pipeline (both sides).** A `create_town(parameters, path)` entry
point: TownShape's `generate_town_from_parameters` and
`derive_relationships`, then the sim's import and setup, then the sim writes
1.1. TownShape's generator needs nothing new for this: the sim's setup
already fills the gaps (staff for the workshops TownShape leaves empty, 28 in
Riverport; merchants; outworkers; day labour; working teens; wealth in
florins).

**1.3 House capacity (both sides).** The sim takes a house's room to be who
lived there at import. TownShape's `buildings.capacity` already holds it:
Riverport's residences have 1,624 places for 1,646 people, 39 of 203 houses
over. TownShape keeps every house within capacity at generation; the sim
reads `capacity`.

## 2. Priority 2: the sim running a stored town

**2.1 Load and save (sim side).** The sim loads a town from the database,
including 1.1, and saves back the clock (`town_state."current_date"`), every
changed table and the events below. Dates are `year_start` plus days run, in
365-day years.

**2.2 Names for new people (TownShape function, called by the sim).** The
sim creates people daily (births, newcomers and their families). TownShape
provides a function that names one: gender, race and household in (a
newborn takes the family name, a newcomer gets a new one); first and last
name out, from TownShape's name lists and `rng_for`. `first_name`,
`last_name` and `race` are `NOT NULL`.

**2.3 Deaths and departures (TownShape schema).**
- The sim's causes: `old age`, `plague`, `flu`, `diarrhea`, `famine`,
  `hardship`, `violence`, `riot`, `execution`, `coup`. TownShape's today:
  `illness`, `accident`, `childbirth`, `old age`, `plague`, skirmishes.
  Since the sim drives everything, the simplest is for `deaths.cause` to
  accept the sim's causes. *Open: confirm.*
- `moved away` and `banished` are recorded by the sim as deaths, but the
  person left alive: a `departures` table (resident, date, reason).
- `deaths.reported_by_building_id`: the sim has no reporter; TownShape picks
  the temple, or the column stays empty.

**2.4 Households and residents that change (the sim writes; TownShape
accepts).** New households (a couple at marriage, a newcomer family,
homeless people pooling to rent a room) and merged ones (the evicted taken
in by kin, a widow joining a child): `households` rows with `family_name`,
`race` and `wealth`. Residents' `household_id`, `home_building_id` (`NULL`
for the homeless, which the schema allows), `occupation`,
`workplace_building_id` and `ses` (re-judged yearly).

**2.5 The sim's occupations (TownShape's viewer and narrative).** Beside
TownShape's own (`acolyte, barkeep, blacksmith, farmer, farmhand, guard,
laborer, noble, priest, servant, shop_staff, shopkeep, smith_apprentice,
tavern_staff, warehouse_clerk`): `merchant`, `outworker`, `day_labourer`,
`rentier`, `sharecropper`, and craft masters and hands (seen in runs:
`dyer`, `fuller`, `weaver_hand`, `tailor_hand`, `tanner_hand`,
`carpenter_hand`, `cooper_hand`, `mason_hand`, `shoemaker_hand`).

**2.6 Relationships, changed row by row (TownShape accepts).** The sim adds
`friend` ties, lets acquaintances fade and retires the ties of the dead. So
`friend` becomes a `relationship_type`, rows are inserted and deleted one at
a time, and `derive_relationships` never runs again after creation.

## 3. Priority 3: what the sim builds appears in the town

**3.1 Placing a building (TownShape function, called by the sim).** When the
sim starts a house (today: while the town has more people than room, 8
people each) or, later, a workshop or shop, it asks TownShape for a plot:
type, capacity and preferred district in; id, position, footprint and
district out, inserted into `buildings`. TownShape knows the map
(settlemaker's geometry: free ground inside the walls, roads, districts); the
sim doesn't. Today the sim makes up ids (`max + 1`) and has no position.

**3.2 Showing it (TownShape viewer).** The viewer draws settlemaker's SVG,
made once at generation, with building outlines from `buildings` on top. A
placed building appears as an outline at once; the map underneath won't show
it unless the SVG is re-rendered or new buildings are drawn in the same
style.

**3.3 Farms outside the walls.** New farms (poderi) are land in the
countryside. They need no plot inside the town, but could be shown as
farmsteads at the edge if wanted.

## 4. Priority 4: large towns

Measured 2026-10-09 on a 21,220-person town generated with Riverport's
settings (target 29,000): one simulated year takes 8 minutes and peaks at
about 2 GB in PyPy, nearly all of it ties. TownShape generates 26
relationships per person at Riverport's size and 36 at 21,000, because
neighbour ties grow with how densely the town is built; the sim then adds
shop ties, for about 86 a person. A 100,000-person town would take about
50-60 minutes and 9-10 GB a year. *Possible change (the user's call, not
decided):* cap neighbour ties per person in big towns.

## 5. Order of work

1. Agree the Priority 1-2 interfaces in TownShape's `CONTRACTS.md` (its
   rule: shared interfaces are written down before anyone builds on them).
2. TownShape: tables (1.1), capacity (1.3), names (2.2), deaths and
   departures (2.3), occupations (2.5), `friend` and row-level writes (2.6).
3. Sim: the pipeline (1.2), load and save (2.1, 2.4).
4. TownShape: placing buildings (3.1) and showing them (3.2); the sim calls
   it when it builds.

## Reference: how TownShape creates and advances its population

**Initial generation** (`scripts/generate_town.py` ->
`town_narrative.generate.generate_town_from_parameters`, then
`town_relationships.generate.derive_relationships`):
1. `town_shaper` builds the map (settlemaker districts and buildings) and
   `assign_residents` draws households' SES and places them in homes and
   job vacancies (rich households first since `f348561`).
2. `town_db.households.build_households_and_residents` turns those slots
   into `households` and `residents` rows: names, race, gender, birth date
   by age bracket, SES, home, workplace, occupation; then tags nobles and
   magical talent.
3. `town_db.persistence` inserts everything; the year's vital records,
   purchases, taxes, school and military service are generated too.
4. `derive_relationships` derives `relationships` (family, coworkers,
   neighbours, military unit-mates, classmates) and `shop_relationships`
   from purchases.

**Advancing a year** (`town_db.simulation.advance_town`): income, disease,
births and deaths, skirmishes, household formation, job market, purchases,
taxes, school and military, then **every relationship is deleted and
re-derived**. This is why it is retired for sim-run towns (section 0).

**External edits** (`town_db.edits.kill_resident`) record a death the way a
write-back needs: `death_date`, a `deaths` row with cause and reporter, and
cleanup of purchases, taxes, military and school spans.

**Conventions a TownShape change must respect** (`TownShape/CONTRACTS.md`):
raw SQL via `sqlite3`, no new dependencies, every random draw through
`rng_for`, a year is exactly 365 days, `"current_date"` quoted when read,
and shared interfaces listed in CONTRACTS.md before they change.

## Reference: how a resident enters the sim

One path for import and for anyone added later:
`graph.node_from_resident_row(graph, row, rng)` builds a resident from a
`residents`-shaped row, and `graph.edge_from_relationship(graph, a, b, type,
rng)` builds a tie of a TownShape relationship type. `graph.add_resident(row,
relationships, rng)` adds a person mid-run with ties to people already there,
and every phenomenon registers them. A TownShape row, a birth in the sim or a
newcomer all enter the same way, so a write-back can go the other way using
the same fields.
