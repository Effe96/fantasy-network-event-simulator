# Brief for TownShape: what to build so the social sim can run your towns

> For the agent working on TownShape. Written 2026-10-09 from the
> social-sim-demo side. The background and reasoning are in
> `social-sim-demo/docs/townshape-integration.md`; this brief is the list of
> what to build.

## The goal

The owner wants the two tools to work as one:

1. **Starting a town creates everything it needs:** the physical town (map,
   districts, buildings), households and people with names and all their
   features, their ties, jobs, money and the town's parameters. This is one
   pipeline: TownShape generates the town as it does today, then the social
   sim's setup adds what only it uses, and everything is saved into the
   town's database.
2. **From then on the social sim drives every interaction and development:**
   births, deaths, marriages, newcomers, jobs, trade, crime, faith, building.
   `advance_town` is not run on these towns: it re-derives every relationship
   (the sim's feelings would be lost) and adds a second set of births and
   deaths.
3. **What the sim builds appears in the physical town:** new houses, shops and
   workshops get a place on the map.

The town database is the single source of truth: the sim writes its state
back into it, so one file is the whole town at any point.

Nothing below changes how TownShape generates a town today. It adds tables,
accepts some new values, and adds two functions.

## What to build, in order

### 1. Tables for the social sim's state

Create these empty for every town (`town_db/schema.py`). Only the social sim
fills them; TownShape's own code doesn't need to read them.

- `resident_traits(resident_id INTEGER PRIMARY KEY REFERENCES residents(id),
  religiousness REAL, skepticism REAL, cunning REAL, loyalty REAL,
  is_ex_soldier INTEGER, same_sex_attracted INTEGER, stress REAL,
  hungry_months INTEGER, is_beggar INTEGER)`
- New nullable columns on `relationships`: `time REAL, intimacy REAL,
  services REAL, valence_a_to_b REAL, valence_b_to_a REAL, former_type TEXT`.
  `NULL` until the sim sets them.
- `household_economy(household_id INTEGER PRIMARY KEY REFERENCES
  households(id), cash REAL, property REAL, rent_behind REAL, usual_income
  REAL)`, in florins. Once the sim has run, it also sets `households.wealth`
  to cash plus property, so TownShape's views stay meaningful.
- `house_tenure(building_id INTEGER PRIMARY KEY REFERENCES buildings(id),
  owner_household_id INTEGER REFERENCES households(id), owner_kind TEXT NOT
  NULL, value REAL NOT NULL, room INTEGER NOT NULL, cost_left REAL)`.
  `owner_kind` is `household`, `commune` or `church`; `cost_left` is set
  while a house is still being built.
- `departures(id INTEGER PRIMARY KEY AUTOINCREMENT, resident_id INTEGER NOT
  NULL UNIQUE REFERENCES residents(id), departure_date TEXT NOT NULL, reason
  TEXT NOT NULL)`, for people who left town alive (`moved away`, `banished`).
  Their `death_date` stays `NULL`. A resident is living in town when they
  have neither a `deaths` row nor a `departures` row; please make TownShape's
  queries for living residents respect that.
- `sim_state(key TEXT PRIMARY KEY, value TEXT NOT NULL)`, JSON values, for the
  sim's town-level state (the commune's and Church's money, class lines,
  granary, workshop stocks, merchants' cargoes, debts, its clock). Opaque to
  TownShape.
- New nullable columns on `town_state`: `loyalty REAL, religiosity REAL,
  strictness REAL`, the sim's town parameters beside `aggression`.

### 2. Accept the social sim's values

No schema change is needed for these; TownShape's code, viewer and narrative
just need to handle them. **Treat each list below as open:** the sim keeps
adding values (new diseases, new kinds of tie, new trades), so code should
show an unknown value as it is rather than reject or drop it.

- **Causes of death** (the owner's decision: accept them as they are, no
  mapping): `old age`, `plague`, `flu`, `diarrhea`, `famine`, `hardship`,
  `violence`, `riot`, `execution`, `coup`. Coming: one cause per epidemic
  disease (for example `typhus`, `dysentery`, `influenza`) in place of
  `plague` for all of them. `deaths.reported_by_building_id` may be `NULL`.
- **Occupations:** besides TownShape's own, `merchant`, `outworker`,
  `day_labourer`, `rentier`, `sharecropper`, and craft masters and hands, for
  example `dyer`, `fuller`, `weaver_hand`, `tailor_hand`, `tanner_hand`,
  `carpenter_hand`, `cooper_hand`, `mason_hand`, `shoemaker_hand`.
- **Relationship types:** `friend`, `acquaintance` and `shopkeeper_customer`,
  besides TownShape's own. Coming: wider family (for example `grandparent`,
  `aunt_uncle`, `cousin`); TownShape's `coworker` and `classmate` will also
  be created mid-run.
- **Homeless residents:** `residents.home_building_id` is `NULL`. The schema
  already allows it; the viewer should show them as homeless.
- **Ids:** the sim adds `residents` and `households` rows with ids it assigns
  (the current maximum plus one, the AUTOINCREMENT rule).

### 3. Keep houses within their capacity

The sim will read `buildings.capacity` as how many people a house holds. In
`demo_riverport_town.db` the residences have 1,624 places for 1,646 people,
and 39 of 203 houses are over capacity. Please make generation keep every
home within its capacity.

### 4. Name a new resident

`town_db/names.py`: `name_new_resident(seed, resident_id, race, gender,
family_name=None) -> (first_name, last_name)`.

The sim creates people during a run (births, newcomers and their families)
and needs names for them, because `first_name` and `last_name` are
`NOT NULL`. A newborn passes its household's `family_name`; a newcomer passes
`None` and gets a drawn surname. Draw through
`rng_for(seed, "name", resident_id)`, so a name depends only on the resident,
not on call order. It can wrap the existing `draw_first_name` and
`draw_surname`.

### 5. Place a new building

`place_building(db_path, seed, building_type, capacity,
preferred_district_id=None) -> building_id` (in `town_shaper` or `town_db`,
wherever fits).

When the sim builds a house (when the town has more people than room,
eight people per house) or a workshop (when a craft can't keep up with the
town, since 2026-10-10), it calls this to get a plot. It should:
- find free ground inside the walls, in the preferred district if possible;
- insert a `buildings` row with position, size, rotation and footprint, like
  a generated building;
- return the new id, or `None` if there is no room.

The viewer draws building outlines from `buildings`, so a placed building
shows at once. The settlemaker SVG underneath is made once at generation and
won't include it. Whether to re-render it or draw new buildings in the same
style is open; say what's feasible.

## What not to build

- **The creation pipeline, and loading and saving the sim's state.** The
  social sim will call `generate_town_from_parameters` and
  `derive_relationships`, then run its own setup and write the tables above.
- **Relationship updates during a run.** The sim inserts and deletes
  `relationships` rows itself with plain SQL. TownShape only has to never
  re-derive relationships on a town the sim has run.
- **Jobs, wealth and traits at generation.** The sim's setup fills them in
  (for example staff for empty workshops, merchants, florin amounts), so the
  generator doesn't change.

## Good to know

- Large towns: on a 21,220-person town generated with Riverport's settings
  (target 29,000), one simulated year takes 8 minutes and about 2 GB, nearly
  all of it ties. TownShape generates 26 relationships per person at
  Riverport's size and 36 at 21,000, because neighbour ties grow with how
  densely the town is built. Capping neighbours per person in big towns may
  come later; nothing to do now.
- Questions and changes to this brief go through the owner.
