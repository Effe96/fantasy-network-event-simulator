# For TownShape: events with a place (2026-10-13)

> From the social-sim side. The owner passes this on. Owner's rule
> (2026-10-11): the social sim's rules come first; TownShape is the tool that
> builds the town you can see.

## What we'd like

A table for things that happened somewhere in the town, which the sim fills
when it saves, and the viewer draws on the map.

## Why

The sim now knows where its events happen:
- **A killing or a theft** happens at a building: the workshop, shop or
  church where the two people know each other, otherwise the victim's home.
  Whoever lives or works there may see it.
- **A riot** starts in a district: the one where most rioters live.

The sim already writes back homes and workplaces, and deaths with a date and
cause, but nothing in TownShape's database can hold where an event happened:
- `deaths.reported_by_building_id` is the building that registered a death,
  not where it happened.
- `skirmish_events` has a name, a date and a severity, with no place and no
  people.

The owner's aim for this step is to make the simulation visible in the town:
after a 25-year run, the map should show where its killings, thefts and
riots happened.

## A suggested shape

TownShape owns the schema, so change anything that fits it better.

```
town_events
  id                  INTEGER PRIMARY KEY
  event_date          TEXT     -- same date format as deaths.death_date
  kind                TEXT     -- see below
  building_id         INTEGER NULL REFERENCES buildings(id)
  district_id         INTEGER NULL REFERENCES districts(id)
  actor_resident_id   INTEGER NULL REFERENCES residents(id)  -- who did it
  target_resident_id  INTEGER NULL REFERENCES residents(id)  -- to whom
  detail              TEXT NULL -- e.g. "8 saw it", "the killer was caught"
```

- **One place per row:** a building, or a district when there's no single
  building (riots). A building can be NULL when the event happened off the
  map (a sharecropper's farm, until farmsteads are placed).
- **Kinds for now:** `killing`, `hired_assassination`, `group_killing`,
  `theft`, `riot`. Fires and floods come later, with a building each. Please
  accept new kinds without a schema change (a plain text column, no CHECK
  list), as with `deaths.cause`.
- **Thefts:** every theft gets a row, with `detail` saying whether it was
  noticed. About 100 a year in Riverport.
- **Volume:** a 25-year run of Riverport gives about 2,700 rows (around
  2,600 thefts, 110 killings, 0-3 riots).

## How the sim fills it

The same way as `departures`: on each save, the sim deletes all rows and
writes the whole history again. TownShape never needs to write to it.

## What we'd ask of the viewer

- A building's panel lists what happened there, newest first.
- The map can mark events, filtered by kind and by year range, so killings
  aren't lost under the thefts.
- A riot shows on its district.

## Open for TownShape

- Whether this belongs in CONTRACTS.md as a sim-written table, alongside
  the sim-state tables.
- Whether `skirmish_events` should stay separate (TownShape's own) or be
  folded in.
