import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from graph import Edge, Node, SocialGraph
from phenomena import FriendshipPhenomenon, PopulationPhenomenon, RiotPhenomenon, RomancePhenomenon


def _trio(feeling_1_2=0.0, feeling_2_1=0.0):
    """1 and 2 are neighbours; 2 and 3 are neighbours; 1 and 3 have never met."""
    graph = SocialGraph()
    for resident_id, gender in [(1, "male"), (2, "male"), (3, "female")]:
        graph.add_node(Node(resident_id=resident_id, ses="poor", alive=True, gender=gender, age=25))
    graph.add_edge(Edge(1, 2, "neighbor", "Equality Matching", 1.0, 0.2, 0.3, feeling_1_2, feeling_2_1))
    graph.add_edge(Edge(2, 3, "neighbor", "Equality Matching", 1.0, 0.2, 0.3, 0.0, 0.0))
    return graph


def test_a_tie_warm_both_ways_becomes_a_friendship_and_cools_back():
    graph = _trio(0.6, 0.5)
    friendship = FriendshipPhenomenon(meetings_per_year=0.0)
    state = friendship.init_state(graph)
    friendship.end_of_day(graph, state, day=30, rng=random.Random(0))
    edge = graph.get_edge(1, 2)
    assert edge.source_type == "friend" and edge.intimacy >= 0.5 and edge.former_type == "neighbor"
    edge.valence_b_to_a = 0.0  # one side has cooled
    friendship.end_of_day(graph, state, day=60, rng=random.Random(0))
    assert edge.source_type == "neighbor"


def test_a_one_sided_warmth_is_not_a_friendship():
    graph = _trio(0.9, 0.1)
    friendship = FriendshipPhenomenon(meetings_per_year=0.0)
    state = friendship.init_state(graph)
    friendship.end_of_day(graph, state, day=30, rng=random.Random(0))
    assert graph.get_edge(1, 2).source_type == "neighbor"


def test_people_meet_through_someone_they_know_and_can_then_fall_in_love():
    graph = _trio()
    friendship = FriendshipPhenomenon(meetings_per_year=365.0)  # meets someone every day
    state = friendship.init_state(graph)
    friendship.end_of_day(graph, state, day=1, rng=random.Random(1))
    edge = graph.get_edge(1, 3)
    assert edge is not None and edge.source_type == "acquaintance"
    edge.valence_a_to_b = edge.valence_b_to_a = 0.9  # two singles who met and hit it off
    romance = RomancePhenomenon(love_threshold=0.5)
    romance_state = romance.init_state(graph)
    assert romance.edge_probability(edge, romance_state[1], romance_state[3], day=2) > 0.0


def test_an_acquaintance_that_never_warms_fades_into_the_archive():
    graph = _trio()
    graph.add_edge(Edge(1, 3, "acquaintance", "Equality Matching", 0.1, 0.1, 0.1, 0.0, 0.0))
    friendship = FriendshipPhenomenon(meetings_per_year=0.0, acquaintance_fade_per_year=0.99)
    state = friendship.init_state(graph)
    for day in range(30, 400, 30):
        friendship.end_of_day(graph, state, day=day, rng=random.Random(day))
        graph.retire_ties_of_dead(before_day=day + 1)
    assert graph.get_edge(1, 3) is None and 3 not in graph.neighbors(1)
    assert graph.archived_ties[-1]["reason"] == "faded"


def test_riots_skip_a_cached_tie_that_has_faded():
    graph = _trio()
    graph.add_node(Node(resident_id=4, ses="rich", alive=True, age=40, occupation="guard"))
    graph.add_edge(Edge(1, 4, "acquaintance", "Equality Matching", 0.1, 0.1, 0.1, -0.5, 0.0))
    riot = RiotPhenomenon()
    riot.init_state(graph)  # caches the civilian-guard pair
    graph.retire_tie(1, 4, day=30, reason="faded")
    graph.retire_ties_of_dead(before_day=31)
    assert riot._start_riot(graph, day=31, rng=random.Random(0)) == []


def test_an_arrival_inherits_the_place_not_the_dead_person_s_friends():
    graph = _trio(0.6, 0.6)
    graph.add_edge(Edge(1, 3, "acquaintance", "Equality Matching", 0.1, 0.1, 0.1, 0.0, 0.0))
    from graph import befriend
    befriend(graph.get_edge(1, 2))  # 1 and 2: neighbours who became friends
    graph.nodes[1].workplace_building_id = 20  # a job: someone comes to take it
    population = PopulationPhenomenon(arrival_daily_chance=1.0)
    state = population.init_state(graph)
    graph.record_death(1, day=1, cause="flu")
    events = population.end_of_day(graph, state, day=1, rng=random.Random(0))
    newcomer = next(e.resident_a for e in events if e.kind == "arrived")
    assert graph.get_edge(newcomer, 2).source_type == "neighbor"  # the neighbour, not the friend
    assert graph.get_edge(newcomer, 3) is None  # the dead person's acquaintance


def _run_all():
    test_a_tie_warm_both_ways_becomes_a_friendship_and_cools_back()
    test_a_one_sided_warmth_is_not_a_friendship()
    test_people_meet_through_someone_they_know_and_can_then_fall_in_love()
    test_an_acquaintance_that_never_warms_fades_into_the_archive()
    test_riots_skip_a_cached_tie_that_has_faded()
    test_an_arrival_inherits_the_place_not_the_dead_person_s_friends()
    print("OK")


if __name__ == "__main__":
    _run_all()
