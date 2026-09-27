import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from graph import Edge, Node, SocialGraph
from phenomena import EverydayPhenomenon


def _pair(feeling_1_to_2, feeling_2_to_1=0.0):
    graph = SocialGraph()
    for resident_id in (1, 2):
        graph.add_node(Node(resident_id=resident_id, ses="poor", alive=True))
    graph.add_edge(Edge(1, 2, "neighbor", "Equality Matching", 1.0, 0.5, 0.5, feeling_1_to_2, feeling_2_to_1))
    return graph


def test_warm_ties_mostly_bring_favors_and_hostile_ones_scorn():
    for feeling, expect_favors in ((0.9, True), (-0.9, False)):
        graph = _pair(feeling, feeling)
        everyday = EverydayPhenomenon(interactions_per_day=1.0, pull_per_year=0.0)
        state = everyday.init_state(graph)
        for day in range(1, 200):
            everyday.end_of_day(graph, state, day, random.Random(day))
        counts = everyday.summarize(state)
        assert (counts["favors"] > counts["scorns"]) == expect_favors


def test_a_favor_or_a_slight_moves_feelings_only_a_little():
    graph = _pair(0.0, 0.0)
    everyday = EverydayPhenomenon(interactions_per_day=1.0, nudge=0.002, pull_per_year=0.0)
    state = everyday.init_state(graph)
    everyday.end_of_day(graph, state, 1, random.Random(0))
    edge = graph.get_edge(1, 2)
    assert all(abs(v) <= 0.004 + 1e-12 for v in (edge.valence_a_to_b, edge.valence_b_to_a))


def test_feelings_are_pulled_back_toward_where_the_tie_started():
    graph = _pair(0.2, 0.2)
    everyday = EverydayPhenomenon(interactions_per_day=0.0, pull_per_year=0.5)
    state = everyday.init_state(graph)
    graph.get_edge(1, 2).valence_a_to_b = -0.8  # e.g. a grudge after a theft
    for day in range(1, 366):
        everyday.end_of_day(graph, state, day, random.Random(day))
    assert -0.4 < graph.get_edge(1, 2).valence_a_to_b < 0.2


def _run_all():
    test_warm_ties_mostly_bring_favors_and_hostile_ones_scorn()
    test_a_favor_or_a_slight_moves_feelings_only_a_little()
    test_feelings_are_pulled_back_toward_where_the_tie_started()
    print("OK")


if __name__ == "__main__":
    _run_all()
