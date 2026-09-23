# tests/test_town_parameters.py
import random
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from graph import Edge, Node, SocialGraph, TownParameters, import_snapshot
from phenomena import TheftPhenomenon, ViolencePhenomenon
from tests.fixtures import make_test_db


def _import(overrides=None, residents=300):
    with tempfile.TemporaryDirectory() as tmp:
        db_path = str(Path(tmp) / "town.db")
        make_test_db(db_path, residents=[(i, "poor", None) for i in range(1, residents + 1)])
        return import_snapshot(db_path, seed=1, overrides=overrides)


def test_defaults_leave_every_factor_at_one():
    params = TownParameters()
    assert params.aggression_factor() == 1.0 and params.strictness_factor() == 1.0


def test_loyalty_and_religiosity_set_the_trait_averages_at_import():
    graph = _import({"loyalty": 0.9, "religiosity": 0.1})
    mean = lambda trait: sum(getattr(n, trait) for n in graph.nodes.values()) / len(graph.nodes)
    assert graph.params.loyalty == 0.9
    assert mean("loyalty") > 0.75 and mean("religiousness") < 0.25
    assert 0.4 < mean("cunning") < 0.6  # traits without a town parameter keep the 0.5 average


def test_an_unknown_parameter_is_rejected():
    try:
        _import({"wealthiness": 0.5}, residents=2)
    except ValueError as error:
        assert "wealthiness" in str(error)
    else:
        raise AssertionError("expected a ValueError")


def test_raising_aggression_mid_run_raises_violence_odds_at_once():
    graph = SocialGraph()
    for resident_id in (1, 2):
        graph.add_node(Node(resident_id=resident_id, ses="poor", alive=True))
    edge = Edge(1, 2, "neighbor", "Equality Matching", 0.5, 0.5, 0.5, -0.9, -0.9)
    graph.add_edge(edge)
    violence = ViolencePhenomenon(base_rate=0.1)
    state = violence.init_state(graph)
    calm = violence.edge_probability(edge, state[1], state[2], day=1)
    graph.params.aggression = 1.0  # e.g. an external event, mid-run
    assert abs(violence.edge_probability(edge, state[1], state[2], day=2) - 3 * calm) < 1e-12


def test_strictness_scales_the_execution_chance():
    assert TownParameters(strictness=1.0).strictness_factor() == 2.0
    assert TownParameters(strictness=0.0).strictness_factor() == 0.0
    # and theft actually reads it: at strictness 0, a caught thief is never executed
    graph = SocialGraph()
    graph.add_node(Node(resident_id=1, ses="poor", alive=True, cunning=1.0))
    graph.add_node(Node(resident_id=2, ses="rich", alive=True))
    graph.add_edge(Edge(1, 2, "neighbor", "Equality Matching", 0.5, 0.5, 0.5, 0.0, 0.0))
    graph.params.strictness = 0.0
    theft = TheftPhenomenon(discovery_chance=1.0, arrest_chance=1.0, execution_weight=1.0)
    state = theft.init_state(graph)
    state[1]["is_thief"] = True
    for seed in range(20):
        theft.apply_effect(graph, state, 1, 2, day=1, rng=random.Random(seed))
        state[1]["is_thief"] = True
    assert graph.nodes[1].alive is True


def _run_all():
    test_defaults_leave_every_factor_at_one()
    test_loyalty_and_religiosity_set_the_trait_averages_at_import()
    test_an_unknown_parameter_is_rejected()
    test_raising_aggression_mid_run_raises_violence_odds_at_once()
    test_strictness_scales_the_execution_chance()
    print("OK")


if __name__ == "__main__":
    _run_all()
