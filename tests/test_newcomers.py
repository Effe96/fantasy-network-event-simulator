# tests/test_newcomers.py -- residents added mid-run (pipeline step 3)
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from demo import build_phenomena
from engine import run_simulation
from graph import Edge, Node, SocialGraph
from phenomena import ContagionPhenomenon


def _family_town():
    """Two parents (1, 2) and a neighbour (3), all at home building 10 in
    district 7; the parents are one family."""
    graph = SocialGraph()
    for resident_id, gender in [(1, "female"), (2, "male"), (3, "female")]:
        graph.add_node(Node(resident_id=resident_id, ses="poor", alive=True, gender=gender, age=30,
                            household_id=100, home_building_id=10, district_id=7, district_zone="poor_residential"))
    graph.add_edge(Edge(1, 2, "spouse", "Communal Sharing", 0.8, 0.8, 0.8, 0.5, 0.5))
    graph.add_edge(Edge(1, 3, "neighbor", "Equality Matching", 0.3, 0.2, 0.3, 0.0, 0.0))
    graph.building_districts = {10: (7, "poor_residential")}
    graph.family_root = {1: 1, 2: 1}
    graph.family_baselines = {1: {"religiousness": 0.9, "skepticism": 0.1}}
    graph.reference_year = 1300
    return graph


def _baby_row():
    # shaped like a TownShape `residents` row, as vital_records' births produce
    return {"ses": "poor", "gender": "male", "birth_date": "1300-01-01", "occupation": None, "is_noble": 0,
            "household_id": 100, "home_building_id": 10, "workplace_building_id": None}


def test_a_newcomer_is_built_like_an_imported_resident():
    graph = _family_town()
    baby = graph.add_resident(_baby_row(), [(1, "parent"), (2, "parent")], random.Random(0))
    assert baby == 4 == graph.next_resident_id() - 1
    node = graph.nodes[baby]
    assert node.age == 0 and node.household_id == 100
    assert (node.district_id, node.district_zone) == (7, "poor_residential")  # from the home building
    assert graph.family_root[baby] == 1  # inherits the parents' family...
    assert 0.5 < node.religiousness  # ...and lands near its centre (0.9), not the town's 0.5
    assert graph.get_edge(baby, 1).source_type == "parent" and graph.get_edge(baby, 2) is not None
    assert graph.get_edge(baby, 3) is None  # only the ties it was given
    assert graph.newcomers == [baby]


def test_an_existing_id_is_rejected():
    graph = _family_town()
    try:
        graph.add_resident(dict(_baby_row(), id=2), [], random.Random(0))
    except ValueError:
        return
    raise AssertionError("expected a ValueError")


class _BirthOnDay:
    """A minimal phenomenon that adds a baby on a given day."""
    name = "births"

    def __init__(self, day):
        self.day, self.baby = day, None

    def init_state(self, graph):
        return {rid: None for rid in graph.nodes}

    def edge_probability(self, edge, state_a, state_b, day):
        return 0.0

    def apply_effect(self, graph, state, a, b, day, rng):
        return []

    def end_of_day(self, graph, state, day, rng):
        if day == self.day:
            self.baby = graph.add_resident(_baby_row(), [(1, "parent"), (2, "parent")], rng)
        return []

    def summarize(self, state):
        return {}

    def add_resident(self, graph, state, resident_id):
        state[resident_id] = None


def test_every_standard_phenomenon_takes_on_a_newcomer_mid_run():
    graph = _family_town()
    births = _BirthOnDay(day=2)
    phenomena = [births] + build_phenomena(graph, outbreak_chance=1.0)
    captured = {}
    run_simulation(graph, phenomena, days=30, seed=1,
                   on_day_end=lambda day, g, states: captured.update(states=states))
    for phenomenon in phenomena:
        assert births.baby in captured["states"][phenomenon.name], phenomenon.name


def test_a_newborn_can_catch_the_disease_from_a_parent():
    graph = _family_town()
    births = _BirthOnDay(day=1)
    contagion = ContagionPhenomenon(base_rate=1.0, infectious_days=10, patient_zero=1, case_fatality_rate=0.0)
    result = run_simulation(graph, [births, contagion], days=10, seed=0)
    assert any(e.kind == "infected" and e.resident_b == births.baby for e in result.events)


def test_a_phenomenon_without_add_resident_fails_loudly():
    graph = _family_town()
    phenomena = [_BirthOnDay(day=1), _Legacy()]
    try:
        run_simulation(graph, phenomena, days=2, seed=0)
    except TypeError as error:
        assert "_Legacy" in str(error)
        return
    raise AssertionError("expected a TypeError")


class _Legacy:
    name = "legacy"

    def init_state(self, graph):
        return {rid: None for rid in graph.nodes}

    def edge_probability(self, edge, state_a, state_b, day):
        return 0.0

    def apply_effect(self, graph, state, a, b, day, rng):
        return []

    def end_of_day(self, graph, state, day, rng):
        return []

    def summarize(self, state):
        return {}


def _run_all():
    test_a_newcomer_is_built_like_an_imported_resident()
    test_an_existing_id_is_rejected()
    test_every_standard_phenomenon_takes_on_a_newcomer_mid_run()
    test_a_newborn_can_catch_the_disease_from_a_parent()
    test_a_phenomenon_without_add_resident_fails_loudly()
    print("OK")


if __name__ == "__main__":
    _run_all()
