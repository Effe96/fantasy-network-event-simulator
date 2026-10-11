# For TownShape: what the end-to-end check found (2026-10-11)

> From the social-sim side, after working through
> `TownShape/docs/sim-integration-for-social-sim.md` steps 1-5 on TownShape
> `main` (d495e51). The owner passes these on. Owner's rule (2026-10-11): the
> social sim's rules come first; TownShape is the tool that builds the town
> you can see.

## The check

A 2,000-person town (`TownParameters(seed="e2e-c", target_population=2000)`)
was generated, set up by the sim, run for a year and saved, then opened with
`scripts/serve_town_viewer.py`. That year saw a plague outbreak, 242 deaths, 5
people leaving to soldier, 33 homeless and one new house placed by
`place_building`. Through the viewer's API:

- **Deaths:** date and cause show, for example "plague, 1301-10-11".
- **Departures:** date and reason show, for example "soldiering, 1301-07-30".
- **The homeless:** a living resident with no home shows as homeless.
- **The new house:** it's on the map (`/api/map`) and drawn in the SVG, with
  its occupants listed.
- **Newborns:** they get a name, the household's surname, and a row.
- **The enforced call order:** `derive_relationships` refuses a town the sim
  runs.

## Wrong on TownShape's side

1. **The viewer lists dead people as living in their old house.**
   - What happens: `get_building_detail` leaves out residents with a
     `departures` row, but not those with a `death_date`. A house's occupant
     list mixes the living and the dead, all marked "lives here". In the test
     town, 268 dead residents still point at a home.
   - TownShape's own generation-year dead keep `home_building_id` too (all 29 in
     `demo_riverport_town.db`), so the sim does the same.
   - Suggested fix: add `death_date IS NULL` to that query (and to "works
     here").
2. **`derive_relationships` leaves the database open when it refuses.**
   - What happens: on `SimOwnedTownError` the connection isn't closed (there's
     no `try/finally`, unlike `advance_town`). On Windows the file stays
     locked until garbage collection, so it can't be moved or deleted.

## Missing, or worth knowing

3. **`place_building` needs shapely, so it doesn't run under PyPy.**
   - The sim's long runs use PyPy (about 3x faster).
   - A stored town is therefore run with CPython: about 10 seconds a year at
     2,000 people, so this isn't urgent.
   - A batch call isn't needed yet: about one house a year at this size.
4. **No room on the map:** the sim still builds the house (its rules decide).
   - It's kept unplaced and its occupants show as homeless in the viewer.
   - Only matters if `place_building` ever returns `None`; it never did here.
5. **Farmsteads for the sim's new farms** (integration doc 3.3).
   - Still not built. Until they are, sharecroppers are stored with no
     workplace.
6. **The sim's own data has no view.** The viewer doesn't show anything from:
   - `resident_traits`;
   - `household_economy` (cash, property, rent owed);
   - `house_tenure` (who owns a house, who rents);
   - the feelings on `relationships`;
   - `former_type`.

   Only if the owner wants to see them there.
7. **`shop_relationships` stays as generated.**
   - The sim keeps its customers as `shopkeeper_customer` rows in
     `relationships`.
   - The viewer's "shopping" list doesn't follow the sim.
8. **Generation lives the town's first year** (`year_start` 1300,
   `current_date` 1301). The sim counts ages from `year_start` (its rules
   stand), so when it saves, it moves birth dates on by that year: the ages
   TownShape shows match the sim's.
