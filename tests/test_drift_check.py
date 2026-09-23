# tests/test_drift_check.py
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from drift_check import drift_per_year
from engine import run_simulation
from graph import Node, SocialGraph
from phenomena import ContagionPhenomenon


def test_drift_is_relative_for_counts_and_absolute_for_averages():
    assert drift_per_year([100, 90, 80], years=2, absolute=False) == -10.0   # -10% of the start a year
    assert abs(drift_per_year([0.50, 0.52, 0.54], years=2, absolute=True) - 0.02) < 1e-12
    assert drift_per_year([0, 5], years=1, absolute=False) == 0.0  # no divide-by-zero on an empty start


def test_engine_calls_the_day_end_hook_once_per_day():
    graph = SocialGraph()
    graph.add_node(Node(resident_id=1, ses="poor", alive=True))
    seen = []
    run_simulation(graph, [ContagionPhenomenon()], days=5, seed=0,
                   on_day_end=lambda day, g, states: seen.append((day, "contagion" in states)))
    assert seen == [(day, True) for day in range(1, 6)]


def _run_all():
    test_drift_is_relative_for_counts_and_absolute_for_averages()
    test_engine_calls_the_day_end_hook_once_per_day()
    print("OK")


if __name__ == "__main__":
    _run_all()
