import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from graph import NOBLE_POOR_RESENTMENT_SHIFT, Edge, Node, SocialGraph, _apply_noble_poor_skew, import_snapshot
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


def test_siblings_have_more_similar_religiousness_than_unrelated_residents():
    # statistical: build many small towns of 2 siblings + 1 unrelated
    # resident, and check siblings' religiousness is closer to each other
    # than to the unrelated resident, on average across seeds
    sibling_gaps = []
    unrelated_gaps = []
    for seed in range(60):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = str(Path(tmp) / "town.db")
            make_test_db(
                db_path,
                residents=[(1, "middling", None), (2, "middling", None), (3, "middling", None)],
                relationships=[(1, 2, "sibling")],  # 3 is unrelated to both
            )
            graph = import_snapshot(db_path, seed=seed)
            sibling_gaps.append(abs(graph.nodes[1].religiousness - graph.nodes[2].religiousness))
            unrelated_gaps.append(abs(graph.nodes[1].religiousness - graph.nodes[3].religiousness))
    avg_sibling_gap = sum(sibling_gaps) / len(sibling_gaps)
    avg_unrelated_gap = sum(unrelated_gaps) / len(unrelated_gaps)
    assert avg_sibling_gap < avg_unrelated_gap


def test_family_grouping_does_not_extend_to_spouses():
    # a spouse isn't a blood relation -- their religiousness should draw
    # from the plain population baseline, not be pulled toward the other
    # spouse's, unlike siblings
    spouse_gaps = []
    for seed in range(60):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = str(Path(tmp) / "town.db")
            make_test_db(
                db_path,
                residents=[(1, "middling", None), (2, "middling", None)],
                relationships=[(1, 2, "spouse")],
            )
            graph = import_snapshot(db_path, seed=seed)
            spouse_gaps.append(abs(graph.nodes[1].religiousness - graph.nodes[2].religiousness))
    avg_spouse_gap = sum(spouse_gaps) / len(spouse_gaps)
    # two independent N(0.5, 0.2) draws have an expected |gap| around 0.22;
    # a family-correlated pair (see the sibling test) averages well under
    # half that -- this just confirms spouses land with the uncorrelated one
    assert avg_spouse_gap > 0.15


def test_apply_noble_poor_skew_lowers_only_the_poor_persons_own_valence():
    graph = SocialGraph()
    graph.add_node(Node(resident_id=1, ses="poor", alive=True))
    graph.add_node(Node(resident_id=2, ses="rich", alive=True, is_noble=True))
    edge = Edge(1, 2, "neighbor", "Equality Matching", 0.5, 0.5, 0.5, valence_a_to_b=0.1, valence_b_to_a=0.1)
    _apply_noble_poor_skew(graph, edge)
    assert abs(edge.valence_from(1) - (0.1 - NOBLE_POOR_RESENTMENT_SHIFT)) < 1e-9
    assert edge.valence_from(2) == 0.1  # the noble's own feelings are untouched


def test_apply_noble_poor_skew_does_nothing_between_two_nobles():
    graph = SocialGraph()
    graph.add_node(Node(resident_id=1, ses="rich", alive=True, is_noble=True))
    graph.add_node(Node(resident_id=2, ses="rich", alive=True, is_noble=True))
    edge = Edge(1, 2, "neighbor", "Equality Matching", 0.5, 0.5, 0.5, 0.1, 0.1)
    _apply_noble_poor_skew(graph, edge)
    assert edge.valence_from(1) == 0.1
    assert edge.valence_from(2) == 0.1


def test_apply_noble_poor_skew_does_nothing_for_non_poor_civilians():
    graph = SocialGraph()
    graph.add_node(Node(resident_id=1, ses="middling", alive=True))
    graph.add_node(Node(resident_id=2, ses="rich", alive=True, is_noble=True))
    edge = Edge(1, 2, "neighbor", "Equality Matching", 0.5, 0.5, 0.5, 0.1, 0.1)
    _apply_noble_poor_skew(graph, edge)
    assert edge.valence_from(1) == 0.1


def test_apply_noble_poor_skew_is_clamped_at_negative_one():
    graph = SocialGraph()
    graph.add_node(Node(resident_id=1, ses="poor", alive=True))
    graph.add_node(Node(resident_id=2, ses="rich", alive=True, is_noble=True))
    edge = Edge(1, 2, "neighbor", "Equality Matching", 0.5, 0.5, 0.5, valence_a_to_b=-0.9, valence_b_to_a=0.0)
    _apply_noble_poor_skew(graph, edge)
    assert edge.valence_from(1) == -1.0


def test_import_poor_residents_are_more_resentful_toward_nobles_than_toward_peers():
    # statistical: same poor resident, one edge to a noble and one to an
    # ordinary middling neighbor -- only the noble edge should carry the
    # extra resentment shift, on average across seeds
    noble_valences = []
    peer_valences = []
    for seed in range(40):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = str(Path(tmp) / "town.db")
            make_test_db(
                db_path,
                residents=[
                    (1, "poor", None),
                    (2, "rich", None, None, None, None, None, 1),  # noble
                    (3, "middling", None),
                ],
                relationships=[(1, 2, "neighbor"), (1, 3, "neighbor")],
            )
            graph = import_snapshot(db_path, seed=seed)
            noble_valences.append(graph.get_edge(1, 2).valence_from(1))
            peer_valences.append(graph.get_edge(1, 3).valence_from(1))
    avg_noble = sum(noble_valences) / len(noble_valences)
    avg_peer = sum(peer_valences) / len(peer_valences)
    assert avg_noble < avg_peer


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
    test_siblings_have_more_similar_religiousness_than_unrelated_residents()
    test_family_grouping_does_not_extend_to_spouses()
    test_apply_noble_poor_skew_lowers_only_the_poor_persons_own_valence()
    test_apply_noble_poor_skew_does_nothing_between_two_nobles()
    test_apply_noble_poor_skew_does_nothing_for_non_poor_civilians()
    test_apply_noble_poor_skew_is_clamped_at_negative_one()
    test_import_poor_residents_are_more_resentful_toward_nobles_than_toward_peers()
    print("OK")


if __name__ == "__main__":
    _run_all()
