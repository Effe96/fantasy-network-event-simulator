import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from graph import Edge, Node, SocialGraph
from phenomena import THIEF_STRESS_THRESHOLD, StressPhenomenon


def _widow():
    """1 and 2 are spouses; 3 is 1's neighbour."""
    graph = SocialGraph()
    for resident_id in (1, 2, 3):
        graph.add_node(Node(resident_id=resident_id, ses="poor", alive=True, age=40))
    graph.add_edge(Edge(1, 2, "spouse", "Communal Sharing", 0.7, 0.7, 0.7, 0.5, 0.5))
    graph.add_edge(Edge(1, 3, "neighbor", "Equality Matching", 0.3, 0.2, 0.2, 0.0, 0.0))
    return graph


def test_poverty_alone_is_below_the_thief_threshold():
    graph = _widow()
    stress = StressPhenomenon()
    stress.init_state(graph)
    assert graph.nodes[1].stress < THIEF_STRESS_THRESHOLD


def test_losing_a_spouse_raises_stress_past_the_threshold_then_it_fades():
    graph = _widow()
    stress = StressPhenomenon()
    state = stress.init_state(graph)
    graph.record_death(2, day=1, cause="flu")
    for day in range(1, 91):
        stress.end_of_day(graph, state, day, random.Random(day))
    assert graph.nodes[1].stress > THIEF_STRESS_THRESHOLD  # the widow
    assert graph.nodes[3].stress < THIEF_STRESS_THRESHOLD  # a neighbour doesn't grieve
    for day in range(91, 500):
        stress.end_of_day(graph, state, day, random.Random(day))
    assert graph.nodes[1].stress < THIEF_STRESS_THRESHOLD


def test_an_illness_adds_a_month_of_strain():
    graph = _widow()
    stress = StressPhenomenon()
    state = stress.init_state(graph)
    before = graph.nodes[3].stress
    graph.record_recovery(3, day=1, cause="flu")
    for day in range(1, 21):
        stress.end_of_day(graph, state, day, random.Random(day))
    assert graph.nodes[3].stress > before


def _run_all():
    test_poverty_alone_is_below_the_thief_threshold()
    test_losing_a_spouse_raises_stress_past_the_threshold_then_it_fades()
    test_an_illness_adds_a_month_of_strain()
    print("OK")


if __name__ == "__main__":
    _run_all()
