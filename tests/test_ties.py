import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import graph as graph_module
from graph import Edge, Node, SocialGraph, add_wider_family, link_lineages, sync_classmates, sync_coworkers, sync_neighbours
from phenomena import FriendshipPhenomenon, PopulationPhenomenon, RomancePhenomenon


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


def test_coworkers_are_tied_and_a_left_job_s_ties_become_acquaintances():
    graph = _street()  # 1 works at the stall (60), 4 at the shop (50)
    graph.add_node(Node(resident_id=8, ses="poor", gender="male", age=30, workplace_building_id=50))
    graph.add_node(Node(resident_id=9, ses="poor", gender="male", age=50, occupation="merchant"))
    graph.add_node(Node(resident_id=10, ses="poor", gender="female", age=20, occupation="outworker"))
    graph.employer = {10: 9}
    rng = random.Random(0)
    sync_coworkers(graph, rng)
    assert graph.get_edge(4, 8).source_type == "coworker"
    assert graph.get_edge(10, 9).source_type == "coworker"  # an outworker and their merchant
    assert graph.get_edge(1, 8) is None  # different workplaces
    assert graph.get_edge(1, 4).source_type == "shopkeeper_customer"
    graph.nodes[8].workplace_building_id = 60  # 8 moves to the stall
    sync_coworkers(graph, rng)
    assert graph.get_edge(4, 8).source_type == "acquaintance"
    assert graph.get_edge(1, 8).source_type == "coworker"


def test_moving_brings_the_new_street_and_old_neighbours_become_friends_who_drift_apart():
    graph = _street()  # 1 and 3 are neighbours on the old street
    graph.nodes[1].home_building_id, graph.nodes[3].home_building_id = 20, 21
    graph.add_node(Node(resident_id=11, ses="poor", gender="male", age=40, home_building_id=30))  # new street
    graph.add_node(Node(resident_id=12, ses="poor", gender="male", age=40, home_building_id=31))
    graph.add_edge(Edge(11, 12, "neighbor", "Equality Matching", 0.3, 0.2, 0.2, 0.0, 0.0))
    rng = random.Random(0)
    sync_neighbours(graph, rng)  # where everyone lives
    graph.nodes[1].home_building_id = 30  # 1 moves in with 11
    sync_neighbours(graph, rng)
    assert graph.get_edge(1, 3).source_type == "friend" and (1, 3) in graph.fading_friends  # an old neighbour
    assert graph.get_edge(1, 11).source_type == graph.get_edge(1, 12).source_type == "neighbor"
    assert graph.get_edge(1, 2).source_type == "spouse"  # family stays family
    friendship = FriendshipPhenomenon(moved_away_fade_per_year=1.0)  # they drift apart
    friendship._monthly(graph, 30, rng)
    graph.retire_ties_of_dead(31)
    assert graph.get_edge(1, 3) is None


def _kin(graph, a, b, kind):
    graph.add_edge(Edge(a, b, kind, "Communal Sharing", 0.7, 0.7, 0.7, 0.5, 0.5))


def test_wider_family_comes_through_parents_and_their_siblings():
    graph = SocialGraph()
    for resident_id, age in ((20, 70), (21, 40), (22, 10), (23, 38), (24, 8)):
        graph.add_node(Node(resident_id=resident_id, ses="poor", gender="female", age=age))
    _kin(graph, 20, 21, "parent")  # grandmother 20 -> mother 21 -> child 22
    _kin(graph, 21, 22, "parent")
    _kin(graph, 21, 23, "sibling")  # the mother's sister 23 and her son 24
    _kin(graph, 23, 24, "parent")
    add_wider_family(graph, random.Random(0), [22])
    assert graph.get_edge(22, 20).source_type == "grandparent"
    assert graph.get_edge(22, 23).source_type == "aunt_uncle"
    assert graph.get_edge(22, 24).source_type == "cousin"


def test_a_younger_household_is_linked_to_its_parents_household():
    graph = SocialGraph()
    rows = ((30, 60, 1), (31, 58, 1), (32, 20, 1), (33, 32, 2))  # an old couple with a son at home; a man of 32
    for resident_id, age, household in rows:
        graph.add_node(Node(resident_id=resident_id, ses="poor", gender="male", age=age, household_id=household))
    _kin(graph, 30, 31, "spouse")
    _kin(graph, 30, 32, "parent")
    _kin(graph, 31, 32, "parent")
    share, graph_module.LINEAGE_SHARE = graph_module.LINEAGE_SHARE, 1.0
    try:
        assert link_lineages(graph, random.Random(0)) == 1
    finally:
        graph_module.LINEAGE_SHARE = share
    assert graph.get_edge(30, 33).source_type == graph.get_edge(31, 33).source_type == "parent"
    assert graph.get_edge(32, 33).source_type == "sibling"


def test_middling_children_go_to_school_together_and_leave_at_15():
    graph = SocialGraph()
    for resident_id, age, ses in ((40, 9, "middling"), (41, 10, "rich"), (42, 9, "poor"), (43, 13, "middling")):
        graph.add_node(Node(resident_id=resident_id, ses=ses, gender="male", age=age, district_id=1))
    rng = random.Random(0)
    sync_classmates(graph, rng)
    assert graph.get_edge(40, 41).source_type == "classmate"
    assert graph.get_edge(40, 42) is None  # a poor child works instead
    assert graph.get_edge(40, 43) is None  # four years older
    graph.nodes[41].age = 15
    sync_classmates(graph, rng)
    assert graph.get_edge(40, 41).source_type == "acquaintance"


def _run_all():
    test_a_newborn_has_the_mother_s_neighbours()
    test_coming_of_age_brings_the_household_s_shops_not_the_parent_s_customers()
    test_the_ties_of_the_dead_move_to_the_archive_after_a_day()
    test_an_arrival_takes_over_ties_already_archived()
    test_coworkers_are_tied_and_a_left_job_s_ties_become_acquaintances()
    test_moving_brings_the_new_street_and_old_neighbours_become_friends_who_drift_apart()
    test_wider_family_comes_through_parents_and_their_siblings()
    test_a_younger_household_is_linked_to_its_parents_household()
    test_middling_children_go_to_school_together_and_leave_at_15()
    print("OK")


if __name__ == "__main__":
    _run_all()
