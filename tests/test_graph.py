import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from graph import Node, Edge, SocialGraph


def test_add_node_and_get_edge_roundtrip():
    graph = SocialGraph()
    graph.add_node(Node(resident_id=1, ses="poor", alive=True))
    graph.add_node(Node(resident_id=2, ses="rich", alive=True))
    edge = Edge(1, 2, "neighbor", "Equality Matching", time=0.3, intimacy=0.2, services=0.2,
                valence_a_to_b=0.1, valence_b_to_a=0.1)
    graph.add_edge(edge)
    assert graph.get_edge(1, 2) is edge
    assert graph.get_edge(2, 1) is edge


def test_tie_strength_uses_absolute_valence():
    edge = Edge(1, 2, "neighbor", "Equality Matching", time=0.8, intimacy=0.8, services=0.8,
                valence_a_to_b=-0.8, valence_b_to_a=-0.8)
    assert abs(edge.tie_strength - 0.8) < 1e-9


def test_tie_strength_averages_both_directions():
    # 1 loves 2 (+0.8), but 2 is indifferent (0.0) -- tie_strength should reflect the average magnitude
    edge = Edge(1, 2, "neighbor", "Equality Matching", time=0.8, intimacy=0.8, services=0.8,
                valence_a_to_b=0.8, valence_b_to_a=0.0)
    assert abs(edge.tie_strength - 0.7) < 1e-9  # mean(0.8, 0.4, 0.8, 0.8)


def test_valence_from_and_set_valence_from_respect_direction():
    edge = Edge(1, 2, "neighbor", "Equality Matching", time=0.5, intimacy=0.5, services=0.5,
                valence_a_to_b=0.3, valence_b_to_a=-0.6)
    assert edge.valence_from(1) == 0.3
    assert edge.valence_from(2) == -0.6
    edge.set_valence_from(2, -0.9)
    assert edge.valence_b_to_a == -0.9
    assert edge.valence_a_to_b == 0.3  # the other direction is untouched


def test_add_edge_dedup_keeps_higher_tie_strength():
    weak = Edge(1, 2, "neighbor", "Equality Matching", time=0.1, intimacy=0.1, services=0.1,
                valence_a_to_b=0.0, valence_b_to_a=0.0)
    strong = Edge(1, 2, "coworker", "Authority Ranking", time=0.9, intimacy=0.5, services=0.6,
                  valence_a_to_b=0.2, valence_b_to_a=0.2)

    graph_a = SocialGraph()
    graph_a.add_edge(weak)
    graph_a.add_edge(strong)
    assert graph_a.get_edge(1, 2) is strong

    graph_b = SocialGraph()
    graph_b.add_edge(strong)
    graph_b.add_edge(weak)
    assert graph_b.get_edge(1, 2) is strong


def test_neighbors_finds_both_directions():
    graph = SocialGraph()
    graph.add_edge(Edge(1, 2, "neighbor", "Equality Matching", 0.3, 0.2, 0.2, 0.1, 0.1))
    graph.add_edge(Edge(3, 1, "coworker", "Authority Ranking", 0.4, 0.2, 0.3, 0.0, 0.0))
    assert sorted(graph.neighbors(1)) == [2, 3]


def _run_all():
    test_add_node_and_get_edge_roundtrip()
    test_tie_strength_uses_absolute_valence()
    test_tie_strength_averages_both_directions()
    test_valence_from_and_set_valence_from_respect_direction()
    test_add_edge_dedup_keeps_higher_tie_strength()
    test_neighbors_finds_both_directions()
    print("OK")


if __name__ == "__main__":
    _run_all()
