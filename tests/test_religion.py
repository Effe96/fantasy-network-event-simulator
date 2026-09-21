import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from graph import Edge, Node, SocialGraph
from phenomena import ReligionPhenomenon


def _civilian_priest_graph(religiousness=0.8, skepticism=0.2, civilian_valence_from_civilian=0.0):
    graph = SocialGraph()
    graph.add_node(Node(resident_id=1, ses="middling", alive=True, religiousness=religiousness, skepticism=skepticism))
    graph.add_node(Node(resident_id=2, ses="middling", alive=True, occupation="priest"))
    graph.add_edge(
        Edge(1, 2, "neighbor", "Equality Matching", time=0.5, intimacy=0.5, services=0.5,
             valence_a_to_b=civilian_valence_from_civilian, valence_b_to_a=0.0)
    )
    return graph


def test_only_fires_between_a_civilian_and_a_priest():
    graph = SocialGraph()
    graph.add_node(Node(resident_id=1, ses="middling", alive=True, religiousness=0.9))
    graph.add_node(Node(resident_id=2, ses="middling", alive=True, religiousness=0.9))  # both civilians
    graph.add_edge(Edge(1, 2, "neighbor", "Equality Matching", 0.5, 0.5, 0.5, 0.0, 0.0))
    phenomenon = ReligionPhenomenon(devotion_base_rate=1.0)
    state = phenomenon.init_state(graph)
    edge = graph.get_edge(1, 2)
    assert phenomenon.edge_probability(edge, state[1], state[2], day=1) == 0.0


def test_more_religious_civilians_show_devotion_more_readily():
    graph_devout = _civilian_priest_graph(religiousness=0.9, skepticism=0.1)
    graph_lukewarm = _civilian_priest_graph(religiousness=0.1, skepticism=0.1)
    phenomenon = ReligionPhenomenon(devotion_base_rate=0.1)
    state_devout = phenomenon.init_state(graph_devout)
    state_lukewarm = phenomenon.init_state(graph_lukewarm)
    p_devout = phenomenon.edge_probability(graph_devout.get_edge(1, 2), state_devout[1], state_devout[2], day=1)
    p_lukewarm = phenomenon.edge_probability(graph_lukewarm.get_edge(1, 2), state_lukewarm[1], state_lukewarm[2], day=1)
    assert p_devout > p_lukewarm


def test_heretics_use_skepticism_driven_friction_odds_instead():
    # both civilians share the same religiousness, but only one crosses the
    # heretic threshold -- the heretic's odds should track skepticism, not
    # religiousness, and should be nonzero even with religiousness at 0
    graph_heretic = _civilian_priest_graph(religiousness=0.0, skepticism=0.95)
    phenomenon = ReligionPhenomenon(friction_base_rate=0.1, heretic_skepticism_threshold=0.8)
    state = phenomenon.init_state(graph_heretic)
    assert state[1]["is_heretic"] is True
    p = phenomenon.edge_probability(graph_heretic.get_edge(1, 2), state[1], state[2], day=1)
    assert p > 0.0


def test_apply_effect_devotion_raises_only_the_civilians_own_affinity():
    graph = _civilian_priest_graph(religiousness=0.9, skepticism=0.1, civilian_valence_from_civilian=0.2)
    phenomenon = ReligionPhenomenon(devotion_affinity_gain=0.1)
    state = phenomenon.init_state(graph)

    events = phenomenon.apply_effect(graph, state, 1, 2, day=10, rng=random.Random(0))

    edge = graph.get_edge(1, 2)
    assert abs(edge.valence_from(1) - 0.3) < 1e-9  # the civilian's own feeling toward the priest went up
    assert edge.valence_from(2) == 0.0  # the priest's own feelings are untouched
    assert any(event.kind == "devotion" for event in events)
    assert phenomenon.summarize(state)["devotions"] == 1


def test_apply_effect_friction_lowers_only_the_heretics_own_affinity():
    graph = _civilian_priest_graph(religiousness=0.1, skepticism=0.95, civilian_valence_from_civilian=0.2)
    phenomenon = ReligionPhenomenon(friction_animosity_loss=0.3, heretic_skepticism_threshold=0.8)
    state = phenomenon.init_state(graph)

    events = phenomenon.apply_effect(graph, state, 1, 2, day=10, rng=random.Random(0))

    edge = graph.get_edge(1, 2)
    assert abs(edge.valence_from(1) - (-0.1)) < 1e-9  # the heretic's own feeling toward the priest dropped
    assert edge.valence_from(2) == 0.0  # the priest's own feelings are untouched
    assert any(event.kind == "friction" for event in events)
    assert phenomenon.summarize(state)["frictions"] == 1


def test_devotion_affinity_is_clamped_at_one():
    graph = _civilian_priest_graph(religiousness=0.9, skepticism=0.1, civilian_valence_from_civilian=0.95)
    phenomenon = ReligionPhenomenon(devotion_affinity_gain=0.5)
    state = phenomenon.init_state(graph)
    phenomenon.apply_effect(graph, state, 1, 2, day=1, rng=random.Random(0))
    assert graph.get_edge(1, 2).valence_from(1) == 1.0


def test_friction_animosity_is_clamped_at_negative_one():
    graph = _civilian_priest_graph(religiousness=0.1, skepticism=0.95, civilian_valence_from_civilian=-0.95)
    phenomenon = ReligionPhenomenon(friction_animosity_loss=0.5, heretic_skepticism_threshold=0.8)
    state = phenomenon.init_state(graph)
    phenomenon.apply_effect(graph, state, 1, 2, day=1, rng=random.Random(0))
    assert graph.get_edge(1, 2).valence_from(1) == -1.0


def test_summarize_counts_heretics_among_civilians_only():
    graph = SocialGraph()
    graph.add_node(Node(resident_id=1, ses="middling", alive=True, skepticism=0.95))  # civilian heretic
    graph.add_node(Node(resident_id=2, ses="middling", alive=True, skepticism=0.95, occupation="priest"))  # not a civilian
    graph.add_node(Node(resident_id=3, ses="middling", alive=True, skepticism=0.1))  # not a heretic
    phenomenon = ReligionPhenomenon(heretic_skepticism_threshold=0.8)
    state = phenomenon.init_state(graph)
    assert phenomenon.summarize(state)["heretics"] == 1


def _run_all():
    test_only_fires_between_a_civilian_and_a_priest()
    test_more_religious_civilians_show_devotion_more_readily()
    test_heretics_use_skepticism_driven_friction_odds_instead()
    test_apply_effect_devotion_raises_only_the_civilians_own_affinity()
    test_apply_effect_friction_lowers_only_the_heretics_own_affinity()
    test_devotion_affinity_is_clamped_at_one()
    test_friction_animosity_is_clamped_at_negative_one()
    test_summarize_counts_heretics_among_civilians_only()
    print("OK")


if __name__ == "__main__":
    _run_all()
