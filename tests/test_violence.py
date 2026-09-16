import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from graph import Edge, Node, SocialGraph
from phenomena import ViolencePhenomenon


def _graph_with_valence(valence: float) -> SocialGraph:
    graph = SocialGraph()
    graph.add_node(Node(resident_id=1, ses="poor", alive=True))
    graph.add_node(Node(resident_id=2, ses="rich", alive=True))
    graph.add_edge(Edge(1, 2, "neighbor", "Equality Matching", time=0.5, intimacy=0.5, services=0.5, valence=valence))
    return graph


def test_positive_valence_edges_never_fire():
    graph = _graph_with_valence(0.6)
    phenomenon = ViolencePhenomenon(base_rate=0.5)
    state = phenomenon.init_state(graph)
    edge = graph.get_edge(1, 2)
    assert phenomenon.edge_probability(edge, state[1], state[2], day=1) == 0.0


def test_edge_probability_formula():
    graph = SocialGraph()
    graph.add_node(Node(resident_id=1, ses="poor", alive=True))
    graph.add_node(Node(resident_id=2, ses="rich", alive=True))
    edge = Edge(1, 2, "neighbor", "Equality Matching", time=0.4, intimacy=0.4, services=0.4, valence=-0.4)
    graph.add_edge(edge)
    phenomenon = ViolencePhenomenon(base_rate=0.1)
    state = phenomenon.init_state(graph)
    probability = phenomenon.edge_probability(edge, state[1], state[2], day=1)
    # tie_strength = mean(0.4, 0.4, 0.4, 0.4) = 0.4; probability = base_rate * |valence| * tie_strength
    assert abs(probability - (0.1 * 0.4 * 0.4)) < 1e-9


def test_probability_is_monotonic_in_animosity_magnitude():
    phenomenon = ViolencePhenomenon(base_rate=0.5)
    mild = _graph_with_valence(-0.2)
    severe = _graph_with_valence(-0.9)
    state_mild = phenomenon.init_state(mild)
    state_severe = phenomenon.init_state(severe)
    p_mild = phenomenon.edge_probability(mild.get_edge(1, 2), state_mild[1], state_mild[2], day=1)
    p_severe = phenomenon.edge_probability(severe.get_edge(1, 2), state_severe[1], state_severe[2], day=1)
    assert p_severe > p_mild


def test_grief_shock_increases_neighbors_animosity_toward_culprit():
    graph = SocialGraph()
    for resident_id, ses in [(1, "poor"), (2, "rich"), (3, "middling")]:
        graph.add_node(Node(resident_id=resident_id, ses=ses, alive=True))
    # 1 and 2 are the violent pair; 3 is close to 1 (the victim) and already knows 2 (the culprit)
    graph.add_edge(Edge(1, 2, "neighbor", "Equality Matching", 0.5, 0.5, 0.5, -0.9))
    graph.add_edge(Edge(1, 3, "sibling", "Communal Sharing", 0.8, 0.8, 0.8, 0.7))
    graph.add_edge(Edge(2, 3, "coworker", "Authority Ranking", 0.4, 0.2, 0.3, 0.1))

    phenomenon = ViolencePhenomenon(base_rate=1.0, grief_shock=0.15)
    state = phenomenon.init_state(graph)
    phenomenon._pick_victim = lambda graph, a, b, rng: 1  # force resident 1 to be the victim

    events = phenomenon.apply_effect(graph, state, 1, 2, day=200, rng=random.Random(0))

    assert graph.nodes[1].alive is False
    assert state[1]["alive"] is False
    edge_2_3 = graph.get_edge(2, 3)
    assert edge_2_3.valence < 0.1  # nudged more negative from its starting 0.1
    assert any(event.kind == "grief_shock" and event.resident_a == 3 for event in events)


def test_summarize_counts_alive_and_dead():
    graph = _graph_with_valence(-0.5)
    phenomenon = ViolencePhenomenon()
    state = phenomenon.init_state(graph)
    state[1]["alive"] = False
    assert phenomenon.summarize(state) == {"alive": 1, "dead": 1}


def _run_all():
    test_positive_valence_edges_never_fire()
    test_edge_probability_formula()
    test_probability_is_monotonic_in_animosity_magnitude()
    test_grief_shock_increases_neighbors_animosity_toward_culprit()
    test_summarize_counts_alive_and_dead()
    print("OK")


if __name__ == "__main__":
    _run_all()
