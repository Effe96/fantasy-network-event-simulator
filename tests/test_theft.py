import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from graph import Edge, Node, SocialGraph
from phenomena import TheftPhenomenon


def _thief_victim_graph(thief_ses="poor", victim_ses="rich", cunning=0.8, victim_valence_from_victim=0.0):
    graph = SocialGraph()
    graph.add_node(Node(resident_id=1, ses=thief_ses, alive=True, cunning=cunning))
    graph.add_node(Node(resident_id=2, ses=victim_ses, alive=True))
    graph.add_edge(
        Edge(1, 2, "neighbor", "Equality Matching", time=0.5, intimacy=0.5, services=0.5,
             valence_a_to_b=0.0, valence_b_to_a=victim_valence_from_victim)
    )
    return graph


def test_no_theft_edge_when_neither_side_is_a_thief():
    graph = _thief_victim_graph()
    phenomenon = TheftPhenomenon(theft_base_rate=1.0)
    state = phenomenon.init_state(graph)
    edge = graph.get_edge(1, 2)
    assert phenomenon.edge_probability(edge, state[1], state[2], day=1) == 0.0


def test_no_theft_edge_when_both_sides_are_thieves():
    graph = _thief_victim_graph()
    phenomenon = TheftPhenomenon(theft_base_rate=1.0)
    state = phenomenon.init_state(graph)
    state[1]["is_thief"] = True
    state[2]["is_thief"] = True
    edge = graph.get_edge(1, 2)
    assert phenomenon.edge_probability(edge, state[1], state[2], day=1) == 0.0


def test_richer_victims_are_more_attractive_targets():
    phenomenon = TheftPhenomenon(theft_base_rate=0.1)

    graph_rich = _thief_victim_graph(victim_ses="rich")
    state_rich = phenomenon.init_state(graph_rich)
    state_rich[1]["is_thief"] = True
    p_rich = phenomenon.edge_probability(graph_rich.get_edge(1, 2), state_rich[1], state_rich[2], day=1)

    graph_poor = _thief_victim_graph(victim_ses="poor")
    state_poor = phenomenon.init_state(graph_poor)
    state_poor[1]["is_thief"] = True
    p_poor = phenomenon.edge_probability(graph_poor.get_edge(1, 2), state_poor[1], state_poor[2], day=1)

    assert p_rich > p_poor


def test_apply_effect_records_a_theft_event_regardless_of_discovery():
    graph = _thief_victim_graph()
    phenomenon = TheftPhenomenon(discovery_chance=0.0)
    state = phenomenon.init_state(graph)
    state[1]["is_thief"] = True

    events = phenomenon.apply_effect(graph, state, 1, 2, day=5, rng=random.Random(0))

    assert any(event.kind == "theft" and event.resident_a == 1 and event.resident_b == 2 for event in events)
    assert phenomenon.summarize(state)["thefts"] == 1
    assert phenomenon.summarize(state)["thefts_caught"] == 0


def test_when_caught_the_victims_valence_toward_the_thief_drops():
    graph = _thief_victim_graph(victim_valence_from_victim=0.5)
    phenomenon = TheftPhenomenon(discovery_chance=1.0, caught_animosity=0.3)
    state = phenomenon.init_state(graph)
    state[1]["is_thief"] = True

    events = phenomenon.apply_effect(graph, state, 1, 2, day=5, rng=random.Random(0))

    edge = graph.get_edge(1, 2)
    assert abs(edge.valence_from(2) - 0.2) < 1e-9
    assert any(event.kind == "caught" for event in events)
    assert phenomenon.summarize(state)["thefts_caught"] == 1


def test_when_caught_a_nearby_guards_valence_toward_the_thief_also_drops():
    graph = _thief_victim_graph()
    graph.add_node(Node(resident_id=3, ses="middling", alive=True, occupation="guard"))
    graph.add_edge(
        Edge(1, 3, "neighbor", "Equality Matching", time=0.5, intimacy=0.5, services=0.5,
             valence_a_to_b=0.0, valence_b_to_a=0.4)
    )
    phenomenon = TheftPhenomenon(discovery_chance=1.0, caught_animosity=0.3)
    state = phenomenon.init_state(graph)
    state[1]["is_thief"] = True

    events = phenomenon.apply_effect(graph, state, 1, 2, day=5, rng=random.Random(0))

    guard_edge = graph.get_edge(1, 3)
    assert abs(guard_edge.valence_from(3) - 0.1) < 1e-9
    assert any(event.kind == "guard_notified" for event in events)


def test_nobles_never_become_thieves():
    graph = SocialGraph()
    graph.add_node(Node(resident_id=1, ses="poor", alive=True, is_noble=True))
    phenomenon = TheftPhenomenon(become_thief_rate=1.0)
    state = phenomenon.init_state(graph)

    phenomenon.end_of_day(graph, state, day=1, rng=random.Random(0))

    assert state[1]["is_thief"] is False


def test_arrested_thief_loses_thief_status_but_stays_alive():
    graph = _thief_victim_graph()
    graph.add_node(Node(resident_id=3, ses="middling", alive=True, occupation="guard", loyalty=1.0))
    graph.add_edge(
        Edge(1, 3, "neighbor", "Equality Matching", time=0.5, intimacy=0.5, services=0.5,
             valence_a_to_b=0.0, valence_b_to_a=0.0)
    )
    phenomenon = TheftPhenomenon(discovery_chance=1.0, arrest_chance=1.0, execution_weight=0.0)
    state = phenomenon.init_state(graph)
    state[1]["is_thief"] = True

    events = phenomenon.apply_effect(graph, state, 1, 2, day=5, rng=random.Random(0))

    assert state[1]["is_thief"] is False
    assert graph.nodes[1].alive is True
    assert any(event.kind == "arrested" for event in events)
    assert phenomenon.summarize(state)["thefts_arrested"] == 1


def test_thief_can_be_arrested_with_no_guard_neighbor_at_all():
    # the original version required a guard *neighbor* to arrest at all --
    # with a sparse guard corps that meant most catches could never lead to
    # a removal. Arrest is now town-wide: no guard node exists in this
    # graph at all, and the thief should still be arrestable.
    graph = _thief_victim_graph()
    phenomenon = TheftPhenomenon(discovery_chance=1.0, arrest_chance=1.0, execution_weight=0.0)
    state = phenomenon.init_state(graph)
    state[1]["is_thief"] = True

    events = phenomenon.apply_effect(graph, state, 1, 2, day=5, rng=random.Random(0))

    assert state[1]["is_thief"] is False
    assert any(event.kind == "arrested" for event in events)
    assert not any(event.kind == "guard_notified" for event in events)


def test_low_loyalty_guards_execute_instead_of_arresting():
    graph = _thief_victim_graph()
    graph.add_node(Node(resident_id=3, ses="middling", alive=True, occupation="guard", loyalty=0.0))
    graph.add_edge(
        Edge(1, 3, "neighbor", "Equality Matching", time=0.5, intimacy=0.5, services=0.5,
             valence_a_to_b=0.0, valence_b_to_a=0.0)
    )
    phenomenon = TheftPhenomenon(discovery_chance=1.0, arrest_chance=1.0, execution_weight=1.0)
    state = phenomenon.init_state(graph)
    state[1]["is_thief"] = True

    events = phenomenon.apply_effect(graph, state, 1, 2, day=5, rng=random.Random(0))

    assert graph.nodes[1].alive is False
    assert any(event.kind == "executed" for event in events)
    assert phenomenon.summarize(state)["thefts_executed"] == 1


def test_recent_arrests_suppress_the_become_thief_probability():
    trials = 200
    become_thief_rate = 0.05

    def hits(deterrence):
        count = 0
        for seed in range(trials):
            graph = SocialGraph()
            graph.add_node(Node(resident_id=1, ses="poor", alive=True))
            phenomenon = TheftPhenomenon(become_thief_rate=become_thief_rate)
            phenomenon._deterrence = deterrence
            state = phenomenon.init_state(graph)
            phenomenon.end_of_day(graph, state, day=1, rng=random.Random(seed))
            count += state[1]["is_thief"]
        return count

    assert hits(deterrence=0.0) > hits(deterrence=50.0)


def test_poorer_residents_become_thieves_more_readily():
    trials = 200
    become_thief_rate = 0.05
    poor_hits = 0
    rich_hits = 0
    for seed in range(trials):
        graph = SocialGraph()
        graph.add_node(Node(resident_id=1, ses="poor", alive=True))
        graph.add_node(Node(resident_id=2, ses="rich", alive=True))
        phenomenon = TheftPhenomenon(become_thief_rate=become_thief_rate)
        state = phenomenon.init_state(graph)
        phenomenon.end_of_day(graph, state, day=1, rng=random.Random(seed))
        poor_hits += state[1]["is_thief"]
        rich_hits += state[2]["is_thief"]

    assert poor_hits > rich_hits


def _run_all():
    test_no_theft_edge_when_neither_side_is_a_thief()
    test_no_theft_edge_when_both_sides_are_thieves()
    test_richer_victims_are_more_attractive_targets()
    test_apply_effect_records_a_theft_event_regardless_of_discovery()
    test_when_caught_the_victims_valence_toward_the_thief_drops()
    test_when_caught_a_nearby_guards_valence_toward_the_thief_also_drops()
    test_arrested_thief_loses_thief_status_but_stays_alive()
    test_thief_can_be_arrested_with_no_guard_neighbor_at_all()
    test_low_loyalty_guards_execute_instead_of_arresting()
    test_recent_arrests_suppress_the_become_thief_probability()
    test_nobles_never_become_thieves()
    test_poorer_residents_become_thieves_more_readily()
    print("OK")


if __name__ == "__main__":
    _run_all()
