import sqlite3
from typing import Iterable, Tuple


def make_test_db(
    path: str,
    residents: Iterable[Tuple[int, str, "int | None"]],
    relationships: Iterable[Tuple[int, int, str]] = (),
    shop_relationships: Iterable[Tuple[int, int, float, int, int]] = (),
) -> None:
    """residents: (id, ses, workplace_building_id)
    relationships: (resident_a_id, resident_b_id, relationship_type)
    shop_relationships: (resident_id, shop_building_id, customer_score, purchase_count, is_primary)
    """
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE residents (id INTEGER PRIMARY KEY, ses TEXT, workplace_building_id INTEGER)")
    conn.execute("CREATE TABLE relationships (resident_a_id INTEGER, resident_b_id INTEGER, relationship_type TEXT)")
    conn.execute(
        "CREATE TABLE shop_relationships (resident_id INTEGER, shop_building_id INTEGER, "
        "customer_score REAL, purchase_count INTEGER, is_primary INTEGER)"
    )
    conn.executemany("INSERT INTO residents VALUES (?, ?, ?)", list(residents))
    conn.executemany("INSERT INTO relationships VALUES (?, ?, ?)", list(relationships))
    conn.executemany("INSERT INTO shop_relationships VALUES (?, ?, ?, ?, ?)", list(shop_relationships))
    conn.commit()
    conn.close()
