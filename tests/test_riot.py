import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from graph import Edge, Node, SocialGraph
from phenomena import RiotPhenomenon


def _town(num_hostile_civilians, num_guards=1, num_nobles=1, hostility=-0.9):
    """civilians (ids 1..N) each hostile toward guard #100 (a `neighbor` edge);
    guards get ids 100..; nobles get ids 200.. -- none connected to civilians
    directly, since RiotPhenomenon treats all living authority members as
    town-wide defenders regardless of adjacency."""
    graph = SocialGraph()
    for i in range(1, num_hostile_civilians + 1):
        graph.add_node(Node(resident_id=i, ses="poor", alive=True, loyalty=0.0))
    for g in range(num_guards):
        guard_id = 100 + g
        graph.add_node(Node(resident_id=guard_id, ses="middling", alive=True, occupation="guard"))
    for n in range(num_nobles):
        noble_id = 200 + n
        graph.add_node(Node(resident_id=noble_id, ses="rich", alive=True, is_noble=True))

    guard_target = 100 if num_guards > 0 else None
    if guard_target is not None:
        for i in range(1, num_hostile_civilians + 1):
            graph.add_edge(
                Edge(i, guard_target, "neighbor", "Equality Matching", time=0.5, intimacy=0.5, services=0.5,
                     valence_a_to_b=hostility, valence_b_to_a=0.0)
            )
    return graph


def test_no_riot_below_unrest_threshold():
    graph = _town(num_hostile_civilians=5, hostility=-0.1)
    phenomenon = RiotPhenomenon(unrest_threshold=0.3, riot_base_rate=1000.0, join_rate=1000.0)
    state = phenomenon.init_state(graph)
    events = phenomenon.end_of_day(graph, state, day=1, rng=random.Random(0))
    assert events == []
    assert phenomenon._riots == 0


def test_no_riot_when_too_few_join():
    # only 2 hostile civilians -- even if both join, that's below min_participants
    graph = _town(num_hostile_civilians=2)
    phenomenon = RiotPhenomenon(unrest_threshold=0.3, riot_base_rate=1000.0, join_rate=1000.0, min_participants=3)
    state = phenomenon.init_state(graph)
    events = phenomenon.end_of_day(graph, state, day=1, rng=random.Random(0))
    assert events == []
    assert phenomenon._riots == 0


def test_riot_fires_with_enough_hostile_joiners():
    graph = _town(num_hostile_civilians=5)
    phenomenon = RiotPhenomenon(
        unrest_threshold=0.3, riot_base_rate=1000.0, join_rate=1000.0, min_participants=3, guard_lethality=0.0
    )
    state = phenomenon.init_state(graph)
    events = phenomenon.end_of_day(graph, state, day=1, rng=random.Random(0))
    assert phenomenon._riots == 1
    assert any(event.kind == "riot" for event in events)


def test_guards_shield_nobles_until_they_retreat():
    # guard_lethality=0 -> no guard ever dies -> guards never retreat -> nobles untouched
    graph = _town(num_hostile_civilians=5, num_guards=2, num_nobles=1)
    # give the noble some haters so they'd be at risk if exposed
    graph.add_edge(Edge(1, 200, "neighbor", "Equality Matching", 0.5, 0.5, 0.5, -0.9, 0.0))
    phenomenon = RiotPhenomenon(
        unrest_threshold=0.3, riot_base_rate=1000.0, join_rate=1000.0, min_participants=3,
        guard_lethality=0.0, noble_lethality=1000.0, death_cap=1.0,
    )
    state = phenomenon.init_state(graph)
    events = phenomenon.end_of_day(graph, state, day=1, rng=random.Random(0))
    assert phenomenon._guard_deaths == 0
    assert phenomenon._noble_deaths == 0  # shielded: guards never broke
    assert graph.nodes[200].alive is True


def test_nobles_are_exposed_once_guards_retreat():
    graph = _town(num_hostile_civilians=5, num_guards=2, num_nobles=1)
    graph.add_edge(Edge(1, 200, "neighbor", "Equality Matching", 0.5, 0.5, 0.5, -0.9, 0.0))
    phenomenon = RiotPhenomenon(
        unrest_threshold=0.3, riot_base_rate=1000.0, join_rate=1000.0, min_participants=3,
        guard_lethality=1000.0, retreat_threshold=0.3, noble_lethality=1000.0, death_cap=1.0,
    )
    state = phenomenon.init_state(graph)
    events = phenomenon.end_of_day(graph, state, day=1, rng=random.Random(0))
    assert phenomenon._guard_deaths >= 1
    assert any(event.kind == "guards_retreat" for event in events)
    assert phenomenon._noble_deaths == 1  # the only noble, guaranteed lethality, guards broke


def test_nobles_are_exposed_immediately_when_no_guards_exist():
    graph = _town(num_hostile_civilians=5, num_guards=0, num_nobles=1)
    # civilians need an authority-adjacency edge to trigger the riot at all;
    # with no guards, wire the hostility straight to the noble instead
    graph.add_edge(Edge(1, 200, "neighbor", "Equality Matching", 0.5, 0.5, 0.5, -0.9, 0.0))
    graph.add_edge(Edge(2, 200, "neighbor", "Equality Matching", 0.5, 0.5, 0.5, -0.9, 0.0))
    graph.add_edge(Edge(3, 200, "neighbor", "Equality Matching", 0.5, 0.5, 0.5, -0.9, 0.0))
    phenomenon = RiotPhenomenon(
        unrest_threshold=0.3, riot_base_rate=1000.0, join_rate=1000.0, min_participants=3,
        noble_lethality=1000.0, death_cap=1.0,
    )
    state = phenomenon.init_state(graph)
    events = phenomenon.end_of_day(graph, state, day=1, rng=random.Random(0))
    assert phenomenon._noble_deaths == 1


def test_hatred_toward_sums_only_hostile_incoming_valence():
    graph = SocialGraph()
    graph.add_node(Node(resident_id=1, ses="poor", alive=True))
    graph.add_node(Node(resident_id=2, ses="poor", alive=True))
    graph.add_node(Node(resident_id=200, ses="rich", alive=True, is_noble=True))
    graph.add_edge(Edge(1, 200, "neighbor", "Equality Matching", 0.5, 0.5, 0.5, valence_a_to_b=-0.6, valence_b_to_a=0.9))
    graph.add_edge(Edge(2, 200, "neighbor", "Equality Matching", 0.5, 0.5, 0.5, valence_a_to_b=-0.3, valence_b_to_a=0.0))
    # only the negative valence *directed at* 200 counts; 200's own outgoing feelings don't
    assert abs(RiotPhenomenon._hatred_toward(graph, 200) - 0.9) < 1e-9


def _run_all():
    test_no_riot_below_unrest_threshold()
    test_no_riot_when_too_few_join()
    test_riot_fires_with_enough_hostile_joiners()
    test_guards_shield_nobles_until_they_retreat()
    test_nobles_are_exposed_once_guards_retreat()
    test_nobles_are_exposed_immediately_when_no_guards_exist()
    test_hatred_toward_sums_only_hostile_incoming_valence()
    print("OK")


if __name__ == "__main__":
    _run_all()
