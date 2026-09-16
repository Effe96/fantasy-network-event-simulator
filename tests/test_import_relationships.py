import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from graph import import_snapshot
from tests.fixtures import make_test_db


def _build_fixture(path: str) -> None:
    make_test_db(
        path,
        residents=[(1, "poor", None), (2, "rich", None), (3, "middling", None)],
        relationships=[(1, 2, "spouse"), (2, 3, "coworker")],
    )


def test_import_loads_all_residents():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = str(Path(tmp) / "town.db")
        _build_fixture(db_path)
        graph = import_snapshot(db_path, seed=1)
        assert set(graph.nodes) == {1, 2, 3}


def test_import_loads_relationship_edges_with_correct_types():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = str(Path(tmp) / "town.db")
        _build_fixture(db_path)
        graph = import_snapshot(db_path, seed=1)
        assert graph.get_edge(1, 2).source_type == "spouse"
        assert graph.get_edge(2, 3).source_type == "coworker"
        assert graph.get_edge(1, 3) is None


def test_import_is_deterministic_given_same_seed():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = str(Path(tmp) / "town.db")
        _build_fixture(db_path)
        graph_a = import_snapshot(db_path, seed=7)
        graph_b = import_snapshot(db_path, seed=7)
        assert graph_a.get_edge(1, 2).valence_a_to_b == graph_b.get_edge(1, 2).valence_a_to_b
        assert graph_a.get_edge(1, 2).valence_b_to_a == graph_b.get_edge(1, 2).valence_b_to_a


def test_dead_residents_are_not_imported_and_leave_no_dangling_edges():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = str(Path(tmp) / "town.db")
        make_test_db(
            db_path,
            residents=[(1, "poor", None), (2, "rich", None, "0450-03-01"), (3, "middling", None)],
            relationships=[(1, 2, "spouse"), (2, 3, "coworker"), (1, 3, "neighbor")],
        )
        graph = import_snapshot(db_path, seed=1)
        assert set(graph.nodes) == {1, 3}
        # only the edge between two living residents survives
        assert set(graph.edges) == {(1, 3)}


def test_relationship_to_unknown_resident_is_skipped():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = str(Path(tmp) / "town.db")
        make_test_db(
            db_path,
            residents=[(1, "poor", None), (2, "rich", None)],
            relationships=[(1, 2, "spouse"), (1, 999, "sibling")],
        )
        graph = import_snapshot(db_path, seed=1)
        assert set(graph.edges) == {(1, 2)}


def _run_all():
    test_import_loads_all_residents()
    test_import_loads_relationship_edges_with_correct_types()
    test_import_is_deterministic_given_same_seed()
    test_dead_residents_are_not_imported_and_leave_no_dangling_edges()
    test_relationship_to_unknown_resident_is_skipped()
    print("OK")


if __name__ == "__main__":
    _run_all()
