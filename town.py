"""A town kept in TownShape's database: created by both tools, run by the sim,
saved back (docs/townshape-integration.md; TownShape's side:
TownShape/docs/sim-integration-for-social-sim.md).

    town = create_town(TownParameters(seed="my-town", target_population=800), "my_town.db")
    town.run(365)
    town.save()
    town = load_town("my_town.db")  # carries on exactly where it stopped

The tables TownShape reads (residents, households, deaths, departures,
relationships, the sim's own tables) are written from the sim's state at each
save. The sim's whole state is also kept, pickled, in sim_state["snapshot"]:
a resumed run is exactly the run that never stopped, without every
phenomenon learning to rebuild itself from tables.
ponytail: the snapshot, not the tables, is what a resumed run reads; edits
made to the tables by hand in between are not seen.

Needs TownShape on the path (TOWNSHAPE, default ../TownShape) and, to place
buildings, its dependencies (shapely): CPython, not PyPy.
"""
import base64
import io
import json
import os
import pickle
import sqlite3
import sys
import zlib
from datetime import date, timedelta
from pathlib import Path
from typing import Dict, Optional

from demo import build_phenomena
from economy import CHURCH, COMMUNE, household_key, person_key
from engine import run_simulation
from graph import TieFilter, import_snapshot

TOWNSHAPE = Path(os.environ.get("TOWNSHAPE", Path(__file__).resolve().parent.parent / "TownShape"))
LEFT_ALIVE = ("moved away", "banished")  # recorded as deaths in the sim; departures in TownShape
# events saved to TownShape's town_events (Project_Vision/08 3.4), by its kind there
PLACED_EVENTS = {"violence": "killing", "hired_assassination": "hired_assassination",
                 "group_violence": "group_killing", "theft": "theft", "riot": "riot"}


# The sim's rules stand where TownShape's differ (user, 2026-10-11: TownShape
# draws the town). So someone living alone, with no household in the sim
# (economy.household_key), gets one in TownShape (where every resident needs
# one) numbered minus their id; and a building TownShape found no room for
# (an id below zero, economy.new_building) is stored as no building.
def _household(key):
    return -key[1] if isinstance(key, tuple) else key


def _sim_household(household_id: int):
    return household_id if household_id >= 0 else ("alone", -household_id)


def _shift_years(day: Optional[str], years: int) -> Optional[str]:
    if day is None or not years:
        return day
    y, m, d = (int(part) for part in day.split("-"))
    return date(y + years, m, min(d, 28) if m == 2 else d).isoformat()


def _placed(building: Optional[int]) -> Optional[int]:
    return building if building is not None and building >= 0 else None  # TownShape counts from 0


def _townshape() -> None:
    if str(TOWNSHAPE) not in sys.path:
        sys.path.insert(0, str(TOWNSHAPE))


class _Pickler(pickle.Pickler):
    """Leaves out the phenomena's tie filters: their tests are lambdas, and
    each phenomenon makes its filter again, from a full scan, when it finds none."""

    def reducer_override(self, obj):
        if isinstance(obj, TieFilter):
            return type(None), ()
        return NotImplemented


class Town:
    def __init__(self, path: str, seed, graph, phenomena, resume: Optional[Dict] = None):
        self.path, self.seed, self.graph, self.phenomena, self.resume = str(path), seed, graph, phenomena, resume
        graph.place_building = self._place

    @property
    def day(self) -> int:
        return self.resume["day"] if self.resume else 0

    def run(self, days: int):
        result = run_simulation(self.graph, self.phenomena, days, self.seed, resume=self.resume)
        self.resume = result.resume
        # the whole history, kept in the graph (so in the snapshot) for each save
        self.graph.__dict__.setdefault("town_events", []).extend(
            (e.day, PLACED_EVENTS[e.kind], e.place, e.district,
             *((None, None) if e.kind == "riot" else (e.resident_a, e.resident_b)), e.detail)
            for e in result.events if e.kind in PLACED_EVENTS)
        return result

    def _place(self, building_type: str, capacity: int, district: Optional[int]) -> Optional[int]:
        """A plot on TownShape's map (economy.new_building)."""
        _townshape()
        from town_db.construction import place_building
        building = place_building(self.path, self.seed, building_type, capacity, district)
        if building is not None:
            conn = sqlite3.connect(self.path)
            d, zone, x, y = conn.execute("SELECT district_id, zone_type, x, y FROM buildings WHERE id = ?",
                                         (building,)).fetchone()
            conn.close()
            self.graph.building_districts[building], self.graph.building_xy[building] = (d, zone), (x, y)
        return building

    def _date(self, start: date, day: int) -> str:
        """The date `day` days into the sim's run, in 365-day years."""
        return (date(start.year + day // 365, start.month, start.day) + timedelta(days=day % 365)).isoformat()

    def save(self) -> None:
        _townshape()
        from town_db.names import draw_race, name_new_resident
        from town_db.schema import ensure_sim_schema
        from town_shaper.seeding import rng_for
        graph, seed = self.graph, self.seed
        conn = sqlite3.connect(self.path)
        conn.execute("PRAGMA foreign_keys = ON")
        with conn:
            ensure_sim_schema(conn)
            clock = conn.execute("SELECT value FROM sim_state WHERE key = 'clock'").fetchone()
            start = date.fromisoformat(json.loads(clock[0])["start"] if clock else
                                       conn.execute('SELECT "current_date" FROM town_state').fetchone()[0])
            on_day = lambda day: self._date(start, day)
            # TownShape's town is a year on from year_start (generation lives
            # its first year); the sim counts ages from year_start, and its
            # ages stand: every birth date moves on by the same years
            years_on = start.year - graph.reference_year if graph.reference_year is not None else 0

            # households first: residents point at them
            households = {hid: (name, race) for hid, name, race in conn.execute(
                "SELECT id, family_name, race FROM households")}
            stored = {rid: (last, race) for rid, last, race in conn.execute("SELECT id, last_name, race FROM residents")}
            nodes = sorted(graph.nodes.values(), key=lambda n: n.resident_id)
            household_of = {n.resident_id: _household(household_key(n)) for n in nodes}
            for node in nodes:  # a new household of people already stored takes the first one's name
                hid = household_of[node.resident_id]
                if hid not in households and node.resident_id in stored:
                    households[hid] = stored[node.resident_id]
                    conn.execute("INSERT INTO households (id, family_name, race) VALUES (?, ?, ?)",
                                 (hid, *stored[node.resident_id]))
            for node in nodes:
                hid = household_of[node.resident_id]
                if node.resident_id in stored:
                    continue
                if hid in households:  # born into it, or joined it
                    family, race = households[hid]
                    first, last = name_new_resident(seed, node.resident_id, race, node.gender, family)
                else:  # a newcomer founding a household: a name of their own
                    race = draw_race(rng_for(seed, "race", node.resident_id))
                    first, last = name_new_resident(seed, node.resident_id, race, node.gender)
                    households[hid] = (last, race)
                    conn.execute("INSERT INTO households (id, family_name, race) VALUES (?, ?, ?)", (hid, last, race))
                conn.execute("INSERT INTO residents (id, household_id, first_name, last_name, gender, race, birth_date,"
                             " ses) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                             (node.resident_id, hid, first, last, node.gender, race,
                              _shift_years(node.birth_date, years_on), node.ses))

            died = {d["resident_id"]: d for d in graph.deaths if d["cause"] not in LEFT_ALIVE}
            conn.executemany(
                "UPDATE residents SET household_id = ?, home_building_id = ?, workplace_building_id = ?, occupation = ?,"
                " ses = ?, is_noble = ?, birth_date = ?, death_date = ? WHERE id = ?",
                [(household_of[n.resident_id], _placed(n.home_building_id),
                  _placed(n.workplace_building_id),  # a podere: not on the map
                  n.occupation, n.ses, int(n.is_noble), _shift_years(n.birth_date, years_on),
                  on_day(died[n.resident_id]["day"]) if n.resident_id in died else None, n.resident_id)
                 for n in nodes])
            conn.executemany("INSERT OR IGNORE INTO deaths (resident_id, death_date, cause) VALUES (?, ?, ?)",
                             [(rid, on_day(d["day"]), d["cause"]) for rid, d in died.items()])
            conn.execute("DELETE FROM departures")
            away = getattr(graph, "soldiers_away", {})
            conn.executemany("INSERT INTO departures (resident_id, departure_date, reason) VALUES (?, ?, ?)",
                             [(d["resident_id"], on_day(d["day"]), d["cause"]) for d in graph.deaths
                              if d["cause"] in LEFT_ALIVE]
                             + [(rid, on_day(record["left"]), "soldiering") for rid, record in sorted(away.items())])
            conn.execute("DELETE FROM town_events")
            conn.executemany("INSERT INTO town_events (event_date, kind, building_id, district_id, actor_resident_id,"
                             " target_resident_id, detail) VALUES (?, ?, ?, ?, ?, ?, ?)",
                             [(on_day(day), kind, _placed(place), district, actor, target, detail)
                              for day, kind, place, district, actor, target, detail
                              in getattr(graph, "town_events", [])])

            conn.execute("DELETE FROM resident_traits")
            conn.executemany("INSERT INTO resident_traits VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                             [(n.resident_id, n.religiousness, n.skepticism, n.cunning, n.loyalty,
                               int(n.is_ex_soldier), int(n.same_sex_attracted), n.stress, n.hungry_months,
                               int(n.beggar)) for n in nodes])

            # every live tie, and the paused ties of those away soldiering
            ties = list(graph.edges.values()) + [e for r in away.values() for e in r["ties"].values()]
            conn.execute("DELETE FROM relationships")
            conn.executemany(
                "INSERT INTO relationships (resident_a_id, resident_b_id, relationship_type, time, intimacy, services,"
                " valence_a_to_b, valence_b_to_a, former_type) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [(e.resident_a, e.resident_b, e.source_type, e.time, e.intimacy, e.services,
                  e.valence_a_to_b, e.valence_b_to_a, e.former_type) for e in ties])

            if hasattr(graph, "money"):
                economy = next((p for p in self.phenomena if p.name == "economy"), None)
                income = getattr(economy, "_income", {}) or {}
                # money is personal in the sim (Project_Vision/09): TownShape keeps
                # it per household, so each household gets its members' together
                total = {hid: [0.0, 0.0, 0.0, None] for hid in households}
                for node in nodes:
                    if node.alive:
                        k, row = person_key(node.resident_id), total[household_of[node.resident_id]]
                        row[0] += graph.money.get(k, 0.0)
                        row[1] += graph.land.get(k, 0.0)
                        row[2] += graph.house_wealth.get(k, 0.0)
                        if k in income:
                            row[3] = (row[3] or 0.0) + income[k]
                keys = [(hid, _sim_household(hid)) for hid in sorted(households)]
                conn.execute("DELETE FROM household_economy")
                conn.executemany("INSERT INTO household_economy VALUES (?, ?, ?, ?, ?)",
                                 [(hid, total[hid][0], total[hid][1], getattr(graph, "rent_behind", {}).get(k, 0.0),
                                   total[hid][3]) for hid, k in keys])
                conn.executemany("UPDATE households SET wealth = ? WHERE id = ?",
                                 [(sum(total[hid][:3]), hid) for hid, k in keys])
                conn.execute("DELETE FROM house_tenure")
                conn.executemany("INSERT INTO house_tenure VALUES (?, ?, ?, ?, ?, ?)",
                                 [(b, None if h["owner"] in (COMMUNE, CHURCH)
                                   else household_of.get(h["owner"][1], _household(household_key(graph.nodes[h["owner"][1]]))),
                                   {COMMUNE: "commune", CHURCH: "church"}.get(h["owner"], "household"),
                                   h["value"], h["room"], h.get("left"))
                                  for b, h in sorted(graph.houses.items()) if _placed(b) is not None])

            params = graph.params
            conn.execute('UPDATE town_state SET "current_date" = ?, aggression = ?, loyalty = ?, religiosity = ?,'
                         " strictness = ?", (on_day(self.day), params.aggression, params.loyalty,
                                             params.religiosity, params.strictness))

            # last: once sim_state has a row, TownShape won't advance the town or re-derive its ties
            buffer = io.BytesIO()
            graph.place_building = None  # Town's own, given back on load
            try:
                _Pickler(buffer, protocol=4).dump({"seed": seed, "graph": graph, "phenomena": self.phenomena,
                                                   "resume": self.resume})
            finally:
                graph.place_building = self._place
            conn.execute("DELETE FROM sim_state")
            conn.executemany("INSERT INTO sim_state VALUES (?, ?)", [
                ("clock", json.dumps({"start": start.isoformat(), "day": self.day})),
                ("soldiers_away", json.dumps({rid: on_day(r["until"]) for rid, r in sorted(away.items())})),
                ("snapshot", json.dumps({"format": "pickle+zlib+base64",
                                         "data": base64.b64encode(zlib.compress(buffer.getvalue())).decode()})),
            ])
        conn.close()


def create_town(parameters, path: str, overrides: Optional[Dict[str, float]] = None, **phenomena_options) -> Town:
    """A new town (integration doc 1.2): TownShape generates it and derives its
    ties, the sim sets it up, and it's saved, sim_state last (TownShape's
    enforced order). `parameters` is TownShape's TownParameters; its seed is
    the sim's too. phenomena_options go to demo.build_phenomena."""
    _townshape()
    from town_narrative.generate import generate_town_from_parameters
    from town_relationships.generate import derive_relationships
    generate_town_from_parameters(parameters, path)
    derive_relationships(path)
    graph = import_snapshot(path, parameters.seed, overrides)
    town = Town(path, parameters.seed, graph, build_phenomena(graph, **phenomena_options))
    town.save()
    return town


def load_town(path: str) -> Town:
    """A town the sim has saved, as it was."""
    conn = sqlite3.connect(f"file:{Path(path).resolve().as_posix()}?mode=ro", uri=True)
    try:
        row = conn.execute("SELECT value FROM sim_state WHERE key = 'snapshot'").fetchone()
    finally:
        conn.close()
    if row is None:
        raise ValueError(f"{path}: the sim hasn't run this town (create_town first)")
    snapshot = json.loads(row[0])
    state = pickle.loads(zlib.decompress(base64.b64decode(snapshot["data"])))
    graph = state["graph"]
    graph._tie_listeners.clear()  # the left-out filters' logs; the ties share this list
    return Town(path, state["seed"], graph, state["phenomena"], state["resume"])
