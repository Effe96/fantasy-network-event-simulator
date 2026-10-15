# For TownShape: a big town's institutions grow with it (2026-10-15)

> From the social-sim side. The owner passes this on. Owner's rule
> (2026-10-11): the social sim's rules come first; TownShape is the tool that
> builds the town you can see.

## What we'd like

When `target_population` is large, the number of temples, workshops and guard
posts should grow with the population, the way residences, taverns and shops
already do.

## Why

We generated a town with Riverport's settings at `target_population=34,200`
(seed `riverport-25k`; 24,545 residents) and ran it for 25 years. Comparing
it with Riverport (1,889 residents), about 13 times as many people:

| Buildings | Riverport | Big town | Big town at Riverport's ratio |
|---|---|---|---|
| residence | 203 | 1,990 | ~2,640 |
| tavern | 4 | 49 | ~52 |
| shop | 4 | 39 | ~52 |
| blacksmith | 1 | 17 | ~13 |
| **workshop** | 28 | **9** | ~365 |
| **temple** | 1 | **2** | ~13 |
| **guard_post** | 8 | **16** | ~104 |
| guards (residents) | 31 | 64 | ~400 |
| manor | 11 | 17 | ~143 |
| farmstead | 12 | 15 | ~156 |

Taverns, shops and smithies scale. Temples, workshops and guard posts barely
do, and workshops fall in number. In the sim this has three effects:

- **Workshops.** The sim staffs each workshop with a master and hands.
  Everyone else gets putting-out work or day labour. With 9 workshops, 25.6%
  of the town are day labourers (Riverport 18.4%). Day work never runs short
  of hands, so no newcomers come looking for work, and the town doesn't grow.
- **Temples.** Two temples means about 12,000 people per parish. Each priest
  is tied to thousands of people. In a plague year, priests seal off infected
  districts, and their parishioners turn on them: one priest had about 3,800
  ties and was hated by 226 people by the end of the year. Every riot left in
  the big town after our own fixes was against a priest.
- **Guards.** 64 guards for 24,545 people (Riverport: 31 for 1,889). In the
  sim, guards catch thieves and killers and put down riots, so the big town
  is policed about six times more thinly.

## What we'd ask

- Temples, workshops and guard posts (with their guards) scale with the
  population, at about Riverport's ratio or a ratio TownShape thinks right.
  For temples, historical towns had many small parishes: Norwich, around
  25,000 people, had about 50 parish churches, so one per 500–2,000 people is
  a fair range. These numbers are approximate, from general history and not
  checked against a source, so TownShape may pick its own.
- Each temple gets a priest. Acolytes are optional.

## Open for TownShape

- **Manors and farmsteads.** They don't scale either. Fewer nobles in a big
  town is plausible. Farmsteads may not need to scale, because a big town
  buys grain from outside. We're not asking for either, but TownShape may
  have its own view.
- **Where the extra workshops go.** We'd expect workshops in the craft
  districts, mixed with residences, but that is TownShape's call.

## What we'll do on our side

Nothing, until TownShape answers. For now we load what TownShape gives us. If
TownShape would rather not change this, the sim can add parish churches,
workshops and guard posts when it loads a town. We'd prefer TownShape to do
it, since these are buildings on the map.
