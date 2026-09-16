# tests/test_contagion.py
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from graph import Edge, Node, SocialGraph
from phenomena import ContagionPhenomenon


def test_edge_probability_matches_worked_example():
    graph = SocialGraph()
    graph.add_node(Node(resident_id=1, ses="poor", alive=True))
    graph.add_node(Node(resident_id=2, ses="rich", alive=True))
    edge = Edge(1, 2, "coworker", "Authority Ranking", time=0.4, intimacy=0.4, services=0.4,
                valence_a_to_b=0.4, valence_b_to_a=0.4)
    graph.add_edge(edge)

    phenomenon = ContagionPhenomenon(base_rate=0.5)
    state = {1: {"status": "infected", "days_left": 7}, 2: {"status": "susceptible", "days_left": 0}}
    probability = phenomenon.edge_probability(edge, state[1], state[2], day=12)
    # tie_strength = mean(0.4, 0.4, 0.4, 0.4) = 0.4; type_weight[coworker] = 0.3
    assert abs(probability - (0.5 * 0.4 * 0.3)) < 1e-9


def test_probability_is_zero_when_neither_endpoint_infected():
    graph = SocialGraph()
    edge = Edge(1, 2, "coworker", "Authority Ranking", 0.4, 0.4, 0.4, 0.0, 0.0)
    graph.add_edge(edge)
    phenomenon = ContagionPhenomenon()
    state_a = {"status": "susceptible", "days_left": 0}
    state_b = {"status": "susceptible", "days_left": 0}
    assert phenomenon.edge_probability(edge, state_a, state_b, day=1) == 0.0


def test_infected_recovers_after_infectious_days():
    graph = SocialGraph()
    graph.add_node(Node(resident_id=1, ses="poor", alive=True))
    graph.add_node(Node(resident_id=2, ses="rich", alive=True))
    phenomenon = ContagionPhenomenon(infectious_days=3, patient_zero=1, case_fatality_rate=0.0)
    state = phenomenon.init_state(graph)
    for day in range(1, 4):
        phenomenon.end_of_day(graph, state, day, random.Random(0))
    assert state[1]["status"] == "recovered"


def test_infected_can_die_instead_of_recovering():
    graph = SocialGraph()
    graph.add_node(Node(resident_id=1, ses="poor", alive=True))
    phenomenon = ContagionPhenomenon(infectious_days=1, patient_zero=1, case_fatality_rate=1.0)
    state = phenomenon.init_state(graph)
    events = phenomenon.end_of_day(graph, state, day=1, rng=random.Random(0))
    assert state[1]["status"] == "deceased"
    assert graph.nodes[1].alive is False
    assert any(event.kind == "died" for event in events)


def test_summarize_counts_every_status():
    state = {
        1: {"status": "infected", "days_left": 2},
        2: {"status": "susceptible", "days_left": 0},
        3: {"status": "recovered", "days_left": 0},
        4: {"status": "deceased", "days_left": 0},
    }
    phenomenon = ContagionPhenomenon()
    assert phenomenon.summarize(state) == {"susceptible": 1, "infected": 1, "recovered": 1, "deceased": 1}


def test_infection_is_not_infectious_until_the_next_day():
    graph = SocialGraph()
    for resident_id in (1, 2):
        graph.add_node(Node(resident_id=resident_id, ses="poor", alive=True))
    phenomenon = ContagionPhenomenon(infectious_days=7, patient_zero=1)
    state = phenomenon.init_state(graph)

    phenomenon.apply_effect(graph, state, 1, 2, day=1, rng=random.Random(0))
    # still day-start state, so a later edge roll today can't chain off resident 2
    assert state[2]["status"] == "susceptible"
    assert phenomenon.edge_probability(
        Edge(2, 1, "spouse", "Communal Sharing", 0.9, 0.9, 0.9, 0.9, 0.9), state[2], state[1], day=1
    ) > 0.0

    phenomenon.end_of_day(graph, state, day=1, rng=random.Random(0))
    assert state[2]["status"] == "infected"
    # a day-1 infection starts day 2 with the full counter, not one day short
    assert state[2]["days_left"] == 7
    assert state[1]["days_left"] == 6  # patient zero did tick


def test_dead_residents_do_not_recover():
    graph = SocialGraph()
    graph.add_node(Node(resident_id=1, ses="poor", alive=False))
    graph.add_node(Node(resident_id=2, ses="rich", alive=True))
    phenomenon = ContagionPhenomenon(infectious_days=1, patient_zero=1)
    state = phenomenon.init_state(graph)
    events = phenomenon.end_of_day(graph, state, day=1, rng=random.Random(0))
    assert events == []
    assert state[1]["status"] == "infected"  # frozen, not recovered


def _run_all():
    test_edge_probability_matches_worked_example()
    test_probability_is_zero_when_neither_endpoint_infected()
    test_infected_recovers_after_infectious_days()
    test_infected_can_die_instead_of_recovering()
    test_summarize_counts_every_status()
    test_infection_is_not_infectious_until_the_next_day()
    test_dead_residents_do_not_recover()
    print("OK")


if __name__ == "__main__":
    _run_all()
