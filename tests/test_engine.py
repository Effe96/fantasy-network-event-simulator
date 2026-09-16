# tests/test_engine.py
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from graph import Edge, Node, SocialGraph
from phenomena import ContagionPhenomenon, ViolencePhenomenon
from engine import run_simulation


def _sample_graph() -> SocialGraph:
    graph = SocialGraph()
    for resident_id, ses in [(1, "poor"), (2, "rich"), (3, "middling"), (4, "poor")]:
        graph.add_node(Node(resident_id=resident_id, ses=ses, alive=True))
    graph.add_edge(Edge(1, 2, "spouse", "Communal Sharing", 0.9, 0.9, 0.9, 0.8, 0.8))
    graph.add_edge(Edge(2, 3, "coworker", "Authority Ranking", 0.4, 0.2, 0.3, -0.9, -0.9))
    # resident 4 has no edges at all -- isolated
    return graph


def test_isolated_resident_never_gets_infected():
    graph = _sample_graph()
    phenomenon = ContagionPhenomenon(base_rate=1.0)  # patient zero = resident 1 (lowest id)
    result = run_simulation(graph, [phenomenon], days=60, seed=1)
    assert all(event.resident_a != 4 and event.resident_b != 4 for event in result.events)
    # the negative assertion above is vacuous on its own, so also prove the
    # outbreak actually reached the connected residents
    assert result.events, "expected the outbreak to produce events elsewhere in the graph"
    assert any(event.kind == "infected" for event in result.events)
    # patient zero (1) and their spouse (2, tie_strength 0.9) both run the
    # course; resident 4 is unreachable and must still be susceptible at the end
    final = result.daily_summaries[-1]
    assert final["recovered"] >= 2, final
    assert final["susceptible"] >= 1, final
    assert final["recovered"] + final["susceptible"] + final["infected"] == 4, final


def test_violence_can_remove_a_resident():
    graph = _sample_graph()
    contagion = ContagionPhenomenon(base_rate=1.0, infectious_days=5)
    violence = ViolencePhenomenon(base_rate=10.0, grief_shock=0.2)  # overdriven so it fires on day 1
    result = run_simulation(graph, [contagion, violence], days=30, seed=3)
    deaths = [event for event in result.events if event.kind == "violence"]
    assert len(deaths) >= 1
    assert result.daily_summaries[-1]["dead"] >= 1


def test_daily_summaries_cover_every_day_requested():
    graph = _sample_graph()
    phenomenon = ContagionPhenomenon()
    result = run_simulation(graph, [phenomenon], days=10, seed=1)
    assert [row["day"] for row in result.daily_summaries] == list(range(1, 11))


def _run_all():
    test_isolated_resident_never_gets_infected()
    test_violence_can_remove_a_resident()
    test_daily_summaries_cover_every_day_requested()
    print("OK")


if __name__ == "__main__":
    _run_all()
