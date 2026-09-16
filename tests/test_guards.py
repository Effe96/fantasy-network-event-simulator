import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from graph import Edge, Node, SocialGraph
from phenomena import GuardPhenomenon


def _civilian_guard_graph(cunning=0.8, ses="rich", guard_valence_from_guard=0.0):
    graph = SocialGraph()
    graph.add_node(Node(resident_id=1, ses=ses, alive=True, cunning=cunning))
    graph.add_node(Node(resident_id=2, ses="middling", alive=True, occupation="guard"))
    graph.add_edge(
        Edge(1, 2, "neighbor", "Equality Matching", time=0.5, intimacy=0.5, services=0.5,
             valence_a_to_b=0.0, valence_b_to_a=guard_valence_from_guard)
    )
    return graph


def test_only_fires_between_a_civilian_and_a_guard():
    graph = SocialGraph()
    graph.add_node(Node(resident_id=1, ses="rich", alive=True, cunning=0.8))
    graph.add_node(Node(resident_id=2, ses="rich", alive=True, cunning=0.8))  # both civilians
    graph.add_edge(Edge(1, 2, "neighbor", "Equality Matching", 0.5, 0.5, 0.5, 0.0, 0.0))
    phenomenon = GuardPhenomenon(bribe_base_rate=1.0)
    state = phenomenon.init_state(graph)
    edge = graph.get_edge(1, 2)
    assert phenomenon.edge_probability(edge, state[1], state[2], day=1) == 0.0


def test_more_cunning_civilians_bribe_more_readily():
    graph = _civilian_guard_graph(cunning=0.9)
    phenomenon = GuardPhenomenon(bribe_base_rate=0.1)
    state = phenomenon.init_state(graph)
    edge = graph.get_edge(1, 2)
    p_high = phenomenon.edge_probability(edge, state[1], state[2], day=1)

    graph_low = _civilian_guard_graph(cunning=0.1)
    state_low = phenomenon.init_state(graph_low)
    edge_low = graph_low.get_edge(1, 2)
    p_low = phenomenon.edge_probability(edge_low, state_low[1], state_low[2], day=1)

    assert p_high > p_low


def test_richer_civilians_bribe_more_readily():
    graph_rich = _civilian_guard_graph(ses="rich")
    graph_poor = _civilian_guard_graph(ses="poor")
    phenomenon = GuardPhenomenon(bribe_base_rate=0.1)
    state_rich = phenomenon.init_state(graph_rich)
    state_poor = phenomenon.init_state(graph_poor)
    p_rich = phenomenon.edge_probability(graph_rich.get_edge(1, 2), state_rich[1], state_rich[2], day=1)
    p_poor = phenomenon.edge_probability(graph_poor.get_edge(1, 2), state_poor[1], state_poor[2], day=1)
    assert p_rich > p_poor


def test_apply_effect_raises_only_the_guards_affinity_toward_the_briber():
    graph = _civilian_guard_graph(guard_valence_from_guard=0.2)
    phenomenon = GuardPhenomenon(bribe_affinity_gain=0.15)
    state = phenomenon.init_state(graph)

    events = phenomenon.apply_effect(graph, state, 1, 2, day=10, rng=random.Random(0))

    edge = graph.get_edge(1, 2)
    assert abs(edge.valence_from(2) - 0.35) < 1e-9  # the guard's feeling toward the briber went up
    assert edge.valence_from(1) == 0.0  # the briber's own feelings are untouched
    assert any(event.kind == "bribed" for event in events)
    assert phenomenon.summarize(state)["bribes"] == 1


def test_bribe_affinity_is_clamped_at_one():
    graph = _civilian_guard_graph(guard_valence_from_guard=0.95)
    phenomenon = GuardPhenomenon(bribe_affinity_gain=0.5)
    state = phenomenon.init_state(graph)
    phenomenon.apply_effect(graph, state, 1, 2, day=1, rng=random.Random(0))
    assert graph.get_edge(1, 2).valence_from(2) == 1.0


def _run_all():
    test_only_fires_between_a_civilian_and_a_guard()
    test_more_cunning_civilians_bribe_more_readily()
    test_richer_civilians_bribe_more_readily()
    test_apply_effect_raises_only_the_guards_affinity_toward_the_briber()
    test_bribe_affinity_is_clamped_at_one()
    print("OK")


if __name__ == "__main__":
    _run_all()
