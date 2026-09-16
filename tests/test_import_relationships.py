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


def test_town_aggression_defaults_to_zero_when_table_is_missing():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = str(Path(tmp) / "town.db")
        _build_fixture(db_path)  # no town_state table
        graph = import_snapshot(db_path, seed=1)
        assert graph.town_aggression == 0.0


def test_town_aggression_is_read_from_town_state():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = str(Path(tmp) / "town.db")
        make_test_db(
            db_path,
            residents=[(1, "poor", None), (2, "rich", None)],
            relationships=[(1, 2, "spouse")],
            aggression=0.8,
        )
        graph = import_snapshot(db_path, seed=1)
        assert graph.town_aggression == 0.8


def test_gender_and_age_are_imported_against_town_reference_year():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = str(Path(tmp) / "town.db")
        make_test_db(
            db_path,
            residents=[
                (1, "poor", None, None, "male", "1280-01-01"),
                (2, "rich", None, None, "female", "1290-01-01"),
                (3, "middling", None, None, None, None),  # no gender/birth_date on record
            ],
            year_start="1300-01-01",
        )
        graph = import_snapshot(db_path, seed=1)
        assert graph.nodes[1].gender == "male"
        assert graph.nodes[1].age == 20
        assert graph.nodes[2].gender == "female"
        assert graph.nodes[2].age == 10
        assert graph.nodes[3].gender is None
        assert graph.nodes[3].age is None


def test_age_is_none_when_town_state_is_missing():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = str(Path(tmp) / "town.db")
        make_test_db(
            db_path,
            residents=[(1, "poor", None, None, "male", "1280-01-01")],  # no town_state at all
        )
        graph = import_snapshot(db_path, seed=1)
        assert graph.nodes[1].age is None


def test_occupation_and_is_noble_are_imported():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = str(Path(tmp) / "town.db")
        make_test_db(
            db_path,
            residents=[
                (1, "rich", None, None, None, None, "noble", 1),
                (2, "poor", None, None, None, None, "guard", 0),
                (3, "poor", None, None, None, None, None, None),
            ],
        )
        graph = import_snapshot(db_path, seed=1)
        assert graph.nodes[1].is_noble is True
        assert graph.nodes[1].role == "noble"
        assert graph.nodes[2].occupation == "guard"
        assert graph.nodes[2].role == "guard"
        assert graph.nodes[3].is_noble is False
        assert graph.nodes[3].role == "civilian"


def _run_all():
    test_import_loads_all_residents()
    test_import_loads_relationship_edges_with_correct_types()
    test_import_is_deterministic_given_same_seed()
    test_dead_residents_are_not_imported_and_leave_no_dangling_edges()
    test_relationship_to_unknown_resident_is_skipped()
    test_town_aggression_defaults_to_zero_when_table_is_missing()
    test_town_aggression_is_read_from_town_state()
    test_gender_and_age_are_imported_against_town_reference_year()
    test_age_is_none_when_town_state_is_missing()
    test_occupation_and_is_noble_are_imported()
    print("OK")


if __name__ == "__main__":
    _run_all()
