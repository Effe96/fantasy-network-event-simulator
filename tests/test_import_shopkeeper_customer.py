import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from graph import import_snapshot
from tests.fixtures import make_test_db


def test_shopkeeper_customer_edges_created_for_each_staff_member():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = str(Path(tmp) / "town.db")
        make_test_db(
            db_path,
            residents=[(1, "poor", None), (2, "rich", 100), (3, "middling", 100)],
            shop_relationships=[(1, 100, 8.0, 5, 1)],
        )
        graph = import_snapshot(db_path, seed=1)
        assert graph.get_edge(1, 2) is not None
        assert graph.get_edge(1, 2).source_type == "shopkeeper_customer"
        assert graph.get_edge(1, 3) is not None


def test_staff_member_buying_from_own_shop_does_not_self_link():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = str(Path(tmp) / "town.db")
        make_test_db(
            db_path,
            residents=[(2, "rich", 100)],
            shop_relationships=[(2, 100, 5.0, 2, 1)],
        )
        graph = import_snapshot(db_path, seed=1)
        assert len(graph.edges) == 0


def test_time_and_services_scale_with_real_purchase_data():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = str(Path(tmp) / "town.db")
        make_test_db(
            db_path,
            residents=[(1, "poor", None), (2, "rich", 100), (10, "poor", None)],
            shop_relationships=[(1, 100, 2.0, 1, 0), (10, 100, 8.0, 5, 1)],
        )
        graph = import_snapshot(db_path, seed=1)
        low_engagement = graph.get_edge(1, 2)
        high_engagement = graph.get_edge(10, 2)
        assert low_engagement.time < high_engagement.time
        assert low_engagement.services < high_engagement.services


def test_noble_poor_skew_applies_to_shopkeeper_customer_edges_too():
    # a poor customer buying from a noble shopkeeper should carry the same
    # extra resentment shift the relationship-edge path applies -- checked
    # statistically since the underlying draw still has its own variance
    noble_valences = []
    for seed in range(40):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = str(Path(tmp) / "town.db")
            make_test_db(
                db_path,
                residents=[(1, "poor", None), (2, "rich", 100, None, None, None, None, 1)],  # 2 is a noble
                shop_relationships=[(1, 100, 8.0, 5, 1)],
            )
            graph = import_snapshot(db_path, seed=seed)
            noble_valences.append(graph.get_edge(1, 2).valence_from(1))
    # shopkeeper_customer's own baseline mean is 0.15 for a primary customer
    # (is_primary=1 here) -- with the skew applied it should average well below that
    avg_noble = sum(noble_valences) / len(noble_valences)
    assert avg_noble < 0.0


def _run_all():
    test_shopkeeper_customer_edges_created_for_each_staff_member()
    test_staff_member_buying_from_own_shop_does_not_self_link()
    test_time_and_services_scale_with_real_purchase_data()
    test_noble_poor_skew_applies_to_shopkeeper_customer_edges_too()
    print("OK")


if __name__ == "__main__":
    _run_all()
