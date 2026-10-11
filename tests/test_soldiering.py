import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import graph as graph_module
from economy import _free_child_places
from graph import Edge, Node, SocialGraph, node_from_resident_row
from phenomena import FEUD_AVENGER_HOSTILITY, PopulationPhenomenon, SoldieringPhenomenon, ViolencePhenomenon


class _Always(random.Random):
    """Every chance comes up."""
    def random(self):
        return 0.0


def _family():
    """Daughter 1 (18, unmarried) lives with her mother 2; 3 is her brother
    elsewhere, 4 a stranger to her."""
    graph = SocialGraph()
    graph.add_node(Node(resident_id=1, ses="poor", gender="female", age=18, household_id=7))
    graph.add_node(Node(resident_id=2, ses="poor", gender="female", age=45, household_id=7, home_building_id=70))
    graph.add_node(Node(resident_id=3, ses="poor", gender="male", age=40, household_id=8))
    graph.add_node(Node(resident_id=4, ses="poor", gender="male", age=40, household_id=9))
    graph.add_edge(Edge(1, 2, "parent", "Communal Sharing", 0.7, 0.7, 0.7, 0.6, 0.6))
    graph.add_edge(Edge(1, 3, "sibling", "Communal Sharing", 0.7, 0.7, 0.7, 0.5, 0.5))
    graph.household_money = {7: 10.0}
    return graph


def _send_away(graph, soldiering):
    soldiering.per_1000 = 12 * 1000 / graph.alive_count  # one a month
    soldiering.init_state(graph)
    events = soldiering.end_of_day(graph, {}, day=30, rng=random.Random(1))
    assert [e.kind for e in events] == ["left_to_soldier"] and events[0].resident_a == 1
    graph.retire_ties_of_dead(before_day=31)  # the day ends
    soldiering.per_1000 = 0.0


def test_a_soldier_is_away_with_ties_paused_and_comes_back_a_veteran_with_savings():
    graph, soldiering = _family(), SoldieringPhenomenon()
    _send_away(graph, soldiering)
    assert not graph.nodes[1].alive and graph.alive_count == 3 and graph.neighbors(1) == []
    soldiering.away[1]["until"] = 30 + 2 * 365
    events = soldiering.end_of_day(graph, {}, day=30 + 2 * 365, rng=random.Random(1))
    assert [e.kind for e in events] == ["came_back"]
    node = graph.nodes[1]
    assert node.alive and node.is_ex_soldier and node.age == 20 and node.home_building_id == 70
    assert graph.get_edge(1, 2).valence_from(1) == 0.6  # the ties as she left them
    assert abs(graph.household_money[7] - 10.0 - 2 * 26.0) < 1e-9


def test_a_soldier_who_dies_away_is_mourned_through_their_ties():
    graph, soldiering = _family(), SoldieringPhenomenon()
    _send_away(graph, soldiering)
    events = soldiering.end_of_day(graph, {}, day=60, rng=_Always())
    assert "died_soldiering" in [e.kind for e in events]
    assert graph.deaths[-1]["cause"] == "war" and graph.get_edge(1, 2) is not None  # until the day ends
    graph.retire_ties_of_dead(before_day=61)
    assert graph.get_edge(1, 2) is None and graph.alive_count == 3


def test_coming_back_they_learn_of_a_killing_and_join_the_feud():
    graph, soldiering = _family(), SoldieringPhenomenon()
    _send_away(graph, soldiering)
    graph.record_death(3, day=100, cause="violence", killed_by=4)  # her brother, killed while she was away
    graph.feuds, graph.feud_ties = [{"avengers": [2], "killers": [4], "keys": [], "day": 100}], {}
    events = soldiering.end_of_day(graph, {}, day=soldiering.away[1]["until"], rng=random.Random(1))
    assert "learned_of_killing" in [e.kind for e in events]
    tie = graph.get_edge(1, 4)
    assert tie.source_type == "feud" and tie.valence_from(1) <= -FEUD_AVENGER_HOSTILITY
    assert (1, 4) in graph.feud_ties and (1, 4) in graph.feuds[0]["keys"]


def test_a_child_never_strikes_but_can_be_struck():
    graph = SocialGraph()
    graph.add_node(Node(resident_id=1, ses="poor", age=10))
    graph.add_node(Node(resident_id=2, ses="poor", age=30))
    graph.add_edge(Edge(1, 2, "neighbor", "Equality Matching", 0.9, 0.9, 0.9, -1.0, 0.5))
    violence = ViolencePhenomenon(base_rate=1.0)
    state = violence.init_state(graph)
    assert violence.apply_effect(graph, state, 1, 2, day=1, rng=random.Random(0)) == []  # only the child hates
    graph.get_edge(1, 2).valence_b_to_a = -1.0
    assert all(violence._pick_aggressor(graph, graph.get_edge(1, 2), 1, 2, random.Random(s)) == 2 for s in range(20))


def test_a_veteran_takes_a_dead_guard_s_post():
    graph = SocialGraph()
    graph.add_node(Node(resident_id=1, ses="poor", age=40, occupation="guard", workplace_building_id=90))
    graph.add_node(Node(resident_id=2, ses="poor", age=25, is_ex_soldier=True, occupation="day_labourer"))
    graph.add_node(Node(resident_id=3, ses="poor", age=25, occupation=None))
    population = PopulationPhenomenon()
    state = population.init_state(graph)
    graph.record_death(1, day=1, cause="violence")
    events = population.end_of_day(graph, state, day=1, rng=random.Random(0))
    assert [e.kind for e in events] == ["veteran_took_post"]
    assert graph.nodes[2].role == "guard" and graph.nodes[2].workplace_building_id == 90
    assert graph.role_changes == [2]


def test_no_child_is_an_ex_soldier():
    graph = SocialGraph()
    graph.reference_year = 1300
    rate, graph_module.EX_SOLDIER_BASE_RATE = graph_module.EX_SOLDIER_BASE_RATE, 1.0
    try:
        child = node_from_resident_row(graph, {"id": 1, "birth_date": "1290-01-01"}, random.Random(0))
        grown = node_from_resident_row(graph, {"id": 2, "birth_date": "1270-01-01"}, random.Random(0))
    finally:
        graph_module.EX_SOLDIER_BASE_RATE = rate
    assert not child.is_ex_soldier and grown.is_ex_soldier


def test_a_child_takes_a_free_place_one_to_a_workplace():
    keeper = Node(resident_id=1, ses="middling", age=40, occupation="shopkeep", workplace_building_id=50)
    master = Node(resident_id=2, ses="middling", age=40, occupation="dyer", workplace_building_id=60)
    child = Node(resident_id=3, ses="poor", age=9, occupation="dyer_hand", workplace_building_id=60)
    assert _free_child_places([keeper, master, child]) == [("shop_staff", 50)]  # the dyer has a child already


def _run_all():
    test_a_soldier_is_away_with_ties_paused_and_comes_back_a_veteran_with_savings()
    test_a_soldier_who_dies_away_is_mourned_through_their_ties()
    test_coming_back_they_learn_of_a_killing_and_join_the_feud()
    test_a_child_never_strikes_but_can_be_struck()
    test_a_veteran_takes_a_dead_guard_s_post()
    test_no_child_is_an_ex_soldier()
    test_a_child_takes_a_free_place_one_to_a_workplace()
    print("OK")


if __name__ == "__main__":
    _run_all()
