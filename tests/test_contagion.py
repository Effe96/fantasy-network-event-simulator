# tests/test_contagion.py
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from graph import Edge, Node, SocialGraph
from phenomena import ContagionPhenomenon


def test_edge_probability_matches_worked_example():
    graph = SocialGraph()
    graph.add_node(Node(resident_id=1, ses="poor", alive=True))
    graph.add_node(Node(resident_id=2, ses="rich", alive=True))
    edge = Edge(1, 2, "coworker", "Authority Ranking", time=0.4, intimacy=0.4, services=0.4, valence=0.4)
    graph.add_edge(edge)

    phenomenon = ContagionPhenomenon(base_rate=0.5)
    state = {1: {"status": "infected", "days_left": 7}, 2: {"status": "susceptible", "days_left": 0}}
    probability = phenomenon.edge_probability(edge, state[1], state[2], day=12)
    # tie_strength = mean(0.4, 0.4, 0.4, 0.4) = 0.4; type_weight[coworker] = 0.3
    assert abs(probability - (0.5 * 0.4 * 0.3)) < 1e-9


def test_probability_is_zero_when_neither_endpoint_infected():
    graph = SocialGraph()
    edge = Edge(1, 2, "coworker", "Authority Ranking", 0.4, 0.4, 0.4, 0.0)
    graph.add_edge(edge)
    phenomenon = ContagionPhenomenon()
    state_a = {"status": "susceptible", "days_left": 0}
    state_b = {"status": "susceptible", "days_left": 0}
    assert phenomenon.edge_probability(edge, state_a, state_b, day=1) == 0.0


def test_infected_recovers_after_infectious_days():
    graph = SocialGraph()
    graph.add_node(Node(resident_id=1, ses="poor", alive=True))
    graph.add_node(Node(resident_id=2, ses="rich", alive=True))
    phenomenon = ContagionPhenomenon(infectious_days=3, patient_zero=1)
    state = phenomenon.init_state(graph)
    for day in range(1, 4):
        phenomenon.end_of_day(graph, state, day)
    assert state[1]["status"] == "recovered"


def test_summarize_counts_every_status():
    state = {
        1: {"status": "infected", "days_left": 2},
        2: {"status": "susceptible", "days_left": 0},
        3: {"status": "recovered", "days_left": 0},
    }
    phenomenon = ContagionPhenomenon()
    assert phenomenon.summarize(state) == {"susceptible": 1, "infected": 1, "recovered": 1}


def _run_all():
    test_edge_probability_matches_worked_example()
    test_probability_is_zero_when_neither_endpoint_infected()
    test_infected_recovers_after_infectious_days()
    test_summarize_counts_every_status()
    print("OK")


if __name__ == "__main__":
    _run_all()
