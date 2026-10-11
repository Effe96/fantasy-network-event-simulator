# tests/test_town.py -- a town kept in TownShape's database (town.py); needs ../TownShape and shapely
import gc
import random
import sqlite3
import sys
import tempfile
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import town
from town import create_town, load_town

town._townshape()
from town_narrative.parameters import TownParameters  # noqa: E402
from town_db.schema import SimOwnedTownError  # noqa: E402
from town_relationships.generate import derive_relationships  # noqa: E402

PARAMETERS = TownParameters(seed="test-town", target_population=400)


def _record(result):
    return result.daily_summaries, [asdict(e) for e in result.events]


def test_a_saved_town_carries_on_as_if_it_never_stopped():
    with tempfile.TemporaryDirectory() as folder:
        straight = create_town(PARAMETERS, f"{folder}/a.db")
        whole = straight.run(70)
        stopped = create_town(PARAMETERS, f"{folder}/b.db")
        first = stopped.run(35)  # across a month's end: the economy's monthly round runs after the load
        stopped.save()
        second = load_town(f"{folder}/b.db").run(35)
        assert _record(whole) == tuple(a + b for a, b in zip(_record(first), _record(second)))


def test_the_saved_town_is_the_sim_s_and_its_tables_follow_the_sim():
    with tempfile.TemporaryDirectory() as folder:
        path = f"{folder}/t.db"
        made = create_town(PARAMETERS, path)
        graph = made.graph
        made.run(40)
        mother = next(n for n in graph.nodes.values() if n.alive and n.gender == "female" and (n.age or 0) > 20)
        newborn = graph.add_resident({"ses": mother.ses, "gender": "male", "birth_date": "1301-02-09",
                                      "household_id": mother.household_id, "home_building_id": mother.home_building_id},
                                     [(mother.resident_id, "parent")], random.Random(0))
        lone = graph.add_resident({"ses": "poor", "gender": "female", "birth_date": "1280-01-01"}, [], random.Random(0))
        graph.record_death(min(n for n in graph.nodes if graph.nodes[n].alive), 40, "moved away")
        made.save()
        conn = sqlite3.connect(path)
        try:
            derive_relationships(path)
        except SimOwnedTownError:
            pass
        else:
            raise AssertionError("TownShape re-derived the ties of a town the sim runs")
        alive = conn.execute("SELECT COUNT(*) FROM residents r WHERE death_date IS NULL"
                             " AND NOT EXISTS (SELECT 1 FROM departures d WHERE d.resident_id = r.id)").fetchone()[0]
        assert alive == graph.alive_count
        family = conn.execute("SELECT family_name FROM households WHERE id = ?", (mother.household_id,)).fetchone()[0]
        assert conn.execute("SELECT last_name FROM residents WHERE id = ?", (newborn,)).fetchone()[0] == family
        assert conn.execute("SELECT COUNT(*) FROM departures WHERE reason = 'moved away'").fetchone()[0] >= 1
        # living alone in the sim (no household): a household of their own in TownShape
        assert conn.execute("SELECT household_id FROM residents WHERE id = ?", (lone,)).fetchone()[0] == -lone
        assert conn.execute("SELECT COUNT(*) FROM relationships").fetchone()[0] >= len(graph.edges)
        assert conn.execute('SELECT "current_date" FROM town_state').fetchone()[0] == "1301-02-10"
        conn.close()
        gc.collect()  # TownShape's refusal leaves its connection open until collected (Windows locks the file)


def _run_all():
    test_a_saved_town_carries_on_as_if_it_never_stopped()
    test_the_saved_town_is_the_sim_s_and_its_tables_follow_the_sim()
    print("OK")


if __name__ == "__main__":
    _run_all()
