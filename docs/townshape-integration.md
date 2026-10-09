# TownShape integration: what TownShape needs to implement

> Rewritten 2026-10-09 (first version 2026-09-23). What TownShape needs so
> that a town it generates can be run in the social sim and come back,
> grouped by priority. Each item says what the sim does today, what TownShape
> would add, and why. Checked against TownShape at `7e1d02a` and
> `demo_riverport_town.db`.

## 0. Where things stand

**The sim now owns the town once it is imported.** The 2026-09-23 version
recommended a yearly loop with TownShape owning births, households, jobs and
income. The sim has since grown all of these itself, daily (in effect option
B of that version): births, newcomers coming for work, households moving
away, households formed at marriage, evictions and the homeless, jobs and
unemployment, money, land, houses and rent, debts, classes, farms (new ones
too), workshops, merchants and their cargoes, and the deaths of all of them.

So the integration is now:
1. **TownShape generates** the town: map, buildings, households, residents,
   relationships.
2. **The sim imports and runs it** for months or decades.
3. **The result goes back** to TownShape, to be viewed, edited and run again.

`advance_town` must **not** run on a town the sim has advanced. It would
re-derive every relationship (feelings lost), add a second set of births and
deaths, and re-fill jobs the sim manages. If TownShape wants to keep features
the sim doesn't model (school, military service), they need to run on their
own, without the demography and relationship steps.

**What the sim reads today** (`graph.import_snapshot`): `residents` (living),
`households.wealth` (as a ranking only), `relationships`,
`shop_relationships`, `buildings` (type, district) with `districts.zone_type`,
`town_state.aggression` and `year_start`. Everything else is invented at
import (section 3) or kept only in memory (section 2).

## 1. Priority 1: needed for a first round trip

Without these, a town the sim has run can't be written back. Each one is a
TownShape-side function or schema change that the sim's write-back calls.

**1.1 New residents: names and rows.** The sim creates people (births,
newcomers and their families) as TownShape-shaped rows, but without names or
race. `residents.first_name`, `last_name` and `race` are `NOT NULL`.
- *Needed:* a function that names a new resident: given gender, race and
  household (a newborn takes the family name; a newcomer gets a new one),
  return first and last name, using TownShape's name lists and `rng_for`.
- *Needed:* `insert_residents` / `insert_births` accepting sim-made rows with
  the ids the sim already assigned (max + 1, the same rule as TownShape's
  AUTOINCREMENT), and `births` rows with the mother and father ids.

**1.2 Deaths in the sim's vocabulary, and departures that aren't deaths.**
- The sim's causes: `old age`, `plague` and everyday ailments (`flu`,
  `diarrhea`), `famine` and `hardship` (hunger), `violence` (murder),
  `riot`, `execution`, `coup`. TownShape's are `illness`, `accident`,
  `childbirth`, `old age`, `plague` and skirmishes. *Needed:* either accept
  the sim's causes in `deaths.cause`, or agree a mapping (e.g. flu and
  diarrhea -> illness).
- `moved away` and `banished` are recorded by the sim as deaths, but the
  person left town alive. *Needed:* a place for departures that isn't
  `death_date`: a `departures` table (resident, date, reason) or a column.
- `deaths.reported_by_building_id` (a temple, or a guard post for
  skirmishes): the sim has no reporter; TownShape picks one, or the column
  stays empty.

**1.3 Households the sim forms and changes.** The sim makes new households
(a couple at marriage, a newcomer family, homeless people who pool to rent a
room) and merges others (the evicted taken in by kin, a widow joining a
child). *Needed:* insert `households` rows (`family_name`, `race`, `wealth`
are `NOT NULL`: name from the head, race from the head, wealth from the sim's
money and property), and update `residents.household_id`.

**1.4 Changed residents.** The sim changes a resident's
- `home_building_id`: moves, evictions, new houses; **`NULL` for the
  homeless**, which the schema already allows (worth saying it is valid);
- `occupation` and `workplace_building_id`: jobs found and lost;
- `ses`: class is re-judged every year from wealth and income.

*Needed:* an `update_resident` write that TownShape accepts, and agreement
that these values are legal (next item).

**1.5 The sim's occupations.** TownShape generates `acolyte, barkeep,
blacksmith, farmer, farmhand, guard, laborer, noble, priest, servant,
shop_staff, shopkeep, smith_apprentice, tavern_staff, warehouse_clerk`. The
sim adds `merchant`, `outworker` (spinning and carding for a merchant),
`day_labourer`, `rentier`, `sharecropper`, and craft masters and hands for
the workshops TownShape leaves empty (seen in runs: `dyer`, `fuller`,
`weaver_hand`, `tailor_hand`, `tanner_hand`, `carpenter_hand`, `cooper_hand`,
`mason_hand`, `shoemaker_hand`).
*Needed:* TownShape's job market, viewer and narrative accept them.

**1.6 Relationships: a merge, never a re-derivation.** The sim adds
`friend` ties (and `shopkeeper_customer` from `shop_relationships`), lets
acquaintances fade, retires the ties of the dead, and gives every tie
strength and feelings in both directions. `derive_relationships` deletes and
re-derives everything. *Needed:* accept `friend` as a `relationship_type`
and a write-back that inserts and removes individual rows; never call
`derive_relationships` on a town the sim has run. Feelings themselves can
stay sim-side (2.1).

**1.7 Dates.** The sim counts days from 1. *Needed:* the write-back sets
`town_state."current_date"` to `year_start + days run` and dates every birth,
death and departure as start + day (365-day years, as in TownShape).

## 2. Priority 2: needed to stop and resume a run

The sim keeps a lot of state only in memory. A run can be written back
(section 1), but resuming it later needs this state too.

**2.1 Recommended: a sim-side save file, keyed by TownShape ids.** The sim
owns these values, so it should store them. TownShape only has to keep ids
stable (residents, households, buildings) and not reuse them. What the file
would hold:
- per resident: religiousness, skepticism, cunning, loyalty, ex-soldier,
  stress, beggar, thief;
- per tie: time, intimacy, services, both feelings, former type;
- per household: cash, land outside the walls, debts, rent arrears, usual
  income;
- per house: owner, value, room, building in progress;
- the commune's and the Church's money, the class lines, the granary, the
  rich's grain hoards, workshop stocks and accounts, merchants' warehouses
  and cargoes at sea, new farms and who works them.

**2.2 Optional: the values TownShape can show.** If TownShape's viewer
should show the economy, a few belong in its tables: `households.wealth`
(the sim's cash plus property, in florins), and who owns each house
(a `house_tenure` table: building, owner household, value, rent). Only if
TownShape wants to use them; the save file covers the sim either way.

## 3. Priority 3: generate what the sim now invents at import

These work today because the sim's importer fills the gaps. They belong in
TownShape's generator, so a generated town is already whole.

**3.1 Jobs** (`economy.setup_economy`, user 2026-09-29 and 2026-10-01):
- **Merchants:** the head (30+, not noble) of each of the richest houses
  trades, about one per 150 residents. TownShape gives the richest houses'
  heads odd posts (guards, servants who are nobles, farmhands); employers
  and public posts keep theirs.
- **Trades for the workshops:** TownShape's 28 workshops in Riverport have no
  one working in them. The sim staffs each with a master and 3-5 hands of one
  trade.
- **Putting-out work** for merchants, **day labour**, more farmhands.
- **Teenagers (12-17) of households that aren't rich** spin and card for
  merchants.

**3.2 Wealth in florins.** The sim reads `households.wealth` only as a
ranking and sets amounts from the book (most households own little, the
richest tenth most of it). TownShape could generate florin amounts directly.

**3.3 House capacity.** The sim takes each house's room to be the number of
people living in it at import. TownShape's `buildings.capacity` already says
it: Riverport's residences hold 1,624 places for 1,646 people, with 39 of
203 over capacity. *Needed (both sides):* TownShape keeps every house within
its capacity at generation, and the sim reads `capacity` instead of
guessing.

**3.4 Randomness.** TownShape draws everything through
`rng_for(seed, *parts)`; the sim uses one `random.Random(seed)`. Only matters
if the two ever run inside one loop: pass each side a derived seed per run.

## 4. Priority 4: buildings the sim creates

The user's decision (2026-10-08): new buildings exist only in the sim for
now. When TownShape should show them:
- **New houses** (from 2026-10-09): built while the town has more people
  than room, 8 people each, ids `max(building ids) + 1`, type `residence`.
- **New farms (poderi):** land outside the walls worked by sharecroppers.
  They need no building inside the town, but could be shown as farmsteads.
- **New workshops:** planned next.

*Needed:* a function that places a building: type, capacity and preferred
district in; id, position, footprint and district out, so the map and
`building_districts` stay right. The sim would call it when it builds, or
the write-back places them all at once.

## 5. Priority 5: large towns

Measured 2026-10-09 on a 21,220-person town generated with Riverport's
settings (target 29,000): one simulated year takes 8 minutes and peaks at
about 2 GB in PyPy, nearly all of it ties. TownShape generates 26
relationships per person at Riverport's size and 36 at 21,000, because
neighbour ties grow with how densely the town is built; the sim then adds
shop ties, for about 86 ties a person. A 100,000-person town would take about
50-60 minutes and 9-10 GB a year.

*Possible change (a model choice, not decided):* cap neighbour ties per
person in big towns (own building and the nearest few), so ties grow with
the population rather than faster. This would change results, so it's the
user's call.

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
re-derived**. This is why it must not run on a sim-advanced town (section 0).

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
