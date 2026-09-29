import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from graph import Edge, Node, SocialGraph
from phenomena import PopulationPhenomenon, RomancePhenomenon


def _street():
    """Mother 1 and father 2 married; 3 is their neighbour; 4 staffs a shop
    (building 50) where the mother buys; 5 buys at the mother's own stall
    (building 60); 6 is their 17-year-old son."""
    graph = SocialGraph()
    graph.add_node(Node(resident_id=1, ses="poor", gender="female", age=30, household_id=7, workplace_building_id=60))
    graph.add_node(Node(resident_id=2, ses="poor", gender="male", age=30, household_id=7))
    graph.add_node(Node(resident_id=3, ses="poor", gender="male", age=40))
    graph.add_node(Node(resident_id=4, ses="poor", gender="male", age=40, workplace_building_id=50))
    graph.add_node(Node(resident_id=5, ses="poor", gender="female", age=40))
    graph.add_node(Node(resident_id=6, ses="poor", gender="male", age=17, household_id=7))
    graph.add_edge(Edge(1, 2, "spouse", "Communal Sharing", 0.7, 0.7, 0.7, 0.5, 0.5))
    graph.add_edge(Edge(1, 3, "neighbor", "Equality Matching", 0.3, 0.2, 0.2, 0.0, 0.0))
    graph.add_edge(Edge(1, 4, "shopkeeper_customer", "Market Pricing", 0.6, 0.1, 0.4, 0.1, 0.1))
    graph.add_edge(Edge(5, 1, "shopkeeper_customer", "Market Pricing", 0.5, 0.1, 0.3, 0.0, 0.0))
    graph.add_edge(Edge(1, 6, "parent", "Communal Sharing", 0.7, 0.7, 0.7, 0.5, 0.5))
    return graph


def test_a_newborn_has_the_mother_s_neighbours():
    graph = _street()
    romance = RomancePhenomenon(birth_base_rate=1.0)
    state = romance.init_state(graph)
    events = romance.apply_effect(graph, state, 1, 2, day=1, rng=random.Random(0))
    baby = next(e.resident_b for e in events if e.kind == "born")
    assert graph.get_edge(baby, 3).source_type == "neighbor"


def test_coming_of_age_brings_the_household_s_shops_not_the_parent_s_customers():
    graph = _street()
    population = PopulationPhenomenon()
    state = population.init_state(graph)
    population.end_of_day(graph, state, day=365, rng=random.Random(0))
    assert graph.nodes[6].age == 18
    tie = graph.get_edge(6, 4)
    assert tie is not None and tie.source_type == "shopkeeper_customer" and tie.time == 0.6
    assert graph.get_edge(6, 5) is None  # 5 is the mother's customer, not a shop the family uses


def test_the_ties_of_the_dead_move_to_the_archive_after_a_day():
    graph = _street()
    graph.record_death(3, day=5, cause="flu")
    assert graph.retire_ties_of_dead(before_day=5) == 0  # everyone reads today's deaths first
    assert graph.retire_ties_of_dead(before_day=6) == 1
    assert graph.get_edge(1, 3) is None and 3 not in graph.neighbors(1)
    record = graph.archived_ties[0]
    assert (record["resident_a"], record["resident_b"], record["source_type"], record["on_death_of"]) == (1, 3, "neighbor", 3)
    assert graph.archived_ties_of(3) == [record]


def test_an_arrival_takes_over_ties_already_archived():
    graph = _street()
    population = PopulationPhenomenon(arrival_daily_chance=0.0)
    state = population.init_state(graph)
    graph.record_death(4, day=1, cause="flu")  # the shop's staff member
    population.end_of_day(graph, state, day=1, rng=random.Random(0))
    graph.retire_ties_of_dead(before_day=2)
    population.arrival_daily_chance = 1.0
    events = population.end_of_day(graph, state, day=90, rng=random.Random(0))
    newcomer = next(e.resident_a for e in events if e.kind == "arrived")
    assert graph.get_edge(newcomer, 1).source_type == "shopkeeper_customer"


def _run_all():
    test_a_newborn_has_the_mother_s_neighbours()
    test_coming_of_age_brings_the_household_s_shops_not_the_parent_s_customers()
    test_the_ties_of_the_dead_move_to_the_archive_after_a_day()
    test_an_arrival_takes_over_ties_already_archived()
    print("OK")


if __name__ == "__main__":
    _run_all()
