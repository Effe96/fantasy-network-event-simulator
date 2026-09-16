import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from graph import Edge, Node, SocialGraph
from phenomena import RomancePhenomenon


def _lovers_graph(source_type="neighbor", valence_a_to_b=0.8, valence_b_to_a=0.8,
                   gender_a="male", gender_b="female", age_a=25, age_b=25):
    graph = SocialGraph()
    graph.add_node(Node(resident_id=1, ses="poor", alive=True, gender=gender_a, age=age_a))
    graph.add_node(Node(resident_id=2, ses="rich", alive=True, gender=gender_b, age=age_b))
    fiske = "Equality Matching" if source_type != "spouse" else "Communal Sharing"
    graph.add_edge(Edge(1, 2, source_type, fiske, time=0.5, intimacy=0.5, services=0.5,
                         valence_a_to_b=valence_a_to_b, valence_b_to_a=valence_b_to_a))
    return graph


def test_mutual_high_affinity_has_positive_marriage_probability():
    graph = _lovers_graph()
    phenomenon = RomancePhenomenon(love_threshold=0.5)
    state = phenomenon.init_state(graph)
    edge = graph.get_edge(1, 2)
    assert phenomenon.edge_probability(edge, state[1], state[2], day=1) > 0.0


def test_unrequited_affinity_never_fires():
    # 1 loves 2, but 2 is indifferent -- min() should gate this to zero
    graph = _lovers_graph(valence_a_to_b=0.9, valence_b_to_a=0.0)
    phenomenon = RomancePhenomenon(love_threshold=0.5)
    state = phenomenon.init_state(graph)
    edge = graph.get_edge(1, 2)
    assert phenomenon.edge_probability(edge, state[1], state[2], day=1) == 0.0


def test_same_gender_pair_never_fires():
    graph = _lovers_graph(gender_a="male", gender_b="male")
    phenomenon = RomancePhenomenon(love_threshold=0.5)
    state = phenomenon.init_state(graph)
    edge = graph.get_edge(1, 2)
    assert phenomenon.edge_probability(edge, state[1], state[2], day=1) == 0.0


def test_minors_never_fire():
    graph = _lovers_graph(age_a=15, age_b=25)
    phenomenon = RomancePhenomenon(love_threshold=0.5)
    state = phenomenon.init_state(graph)
    edge = graph.get_edge(1, 2)
    assert phenomenon.edge_probability(edge, state[1], state[2], day=1) == 0.0


def test_family_edges_never_fire():
    for source_type in ("parent", "sibling"):
        graph = _lovers_graph(source_type=source_type)
        phenomenon = RomancePhenomenon(love_threshold=0.5)
        state = phenomenon.init_state(graph)
        edge = graph.get_edge(1, 2)
        assert phenomenon.edge_probability(edge, state[1], state[2], day=1) == 0.0


def test_already_married_resident_never_fires_a_second_romance():
    graph = _lovers_graph()
    phenomenon = RomancePhenomenon(love_threshold=0.5)
    state = phenomenon.init_state(graph)
    state[1]["married"] = True
    edge = graph.get_edge(1, 2)
    assert phenomenon.edge_probability(edge, state[1], state[2], day=1) == 0.0


def test_init_state_marks_existing_spouses_as_married():
    graph = _lovers_graph(source_type="spouse")
    phenomenon = RomancePhenomenon()
    state = phenomenon.init_state(graph)
    assert state[1]["married"] is True
    assert state[2]["married"] is True


def test_apply_effect_marries_and_retypes_the_edge():
    graph = _lovers_graph()
    phenomenon = RomancePhenomenon()
    state = phenomenon.init_state(graph)
    events = phenomenon.apply_effect(graph, state, 1, 2, day=10, rng=random.Random(0))

    edge = graph.get_edge(1, 2)
    assert edge.source_type == "spouse"
    assert state[1]["married"] is True
    assert state[2]["married"] is True
    assert any(event.kind == "married" for event in events)


def test_married_couple_can_have_a_birth_event_without_a_new_node():
    graph = _lovers_graph(source_type="spouse")
    phenomenon = RomancePhenomenon(birth_base_rate=1.0)
    state = phenomenon.init_state(graph)
    node_count_before = len(graph.nodes)

    edge = graph.get_edge(1, 2)
    assert phenomenon.edge_probability(edge, state[1], state[2], day=1) > 0.0
    events = phenomenon.apply_effect(graph, state, 1, 2, day=1, rng=random.Random(0))

    assert len(graph.nodes) == node_count_before  # log-only: no new resident yet
    assert any(event.kind == "born" for event in events)
    assert phenomenon.summarize(state)["births"] == 1


def test_summarize_counts_married_residents():
    graph = _lovers_graph(source_type="spouse")
    phenomenon = RomancePhenomenon()
    state = phenomenon.init_state(graph)
    assert phenomenon.summarize(state)["married_residents"] == 2


def _run_all():
    test_mutual_high_affinity_has_positive_marriage_probability()
    test_unrequited_affinity_never_fires()
    test_same_gender_pair_never_fires()
    test_minors_never_fire()
    test_family_edges_never_fire()
    test_already_married_resident_never_fires_a_second_romance()
    test_init_state_marks_existing_spouses_as_married()
    test_apply_effect_marries_and_retypes_the_edge()
    test_married_couple_can_have_a_birth_event_without_a_new_node()
    test_summarize_counts_married_residents()
    print("OK")


if __name__ == "__main__":
    _run_all()
