import sqlite3
from typing import Iterable, Tuple


def make_test_db(
    path: str,
    residents: Iterable[Tuple[int, str, "int | None"]],
    relationships: Iterable[Tuple[int, int, str]] = (),
    shop_relationships: Iterable[Tuple[int, int, float, int, int]] = (),
    aggression: "float | None" = None,
    year_start: "str | None" = None,
) -> None:
    """residents: (id, ses, workplace_building_id[, death_date[, gender[, birth_date]]])
    relationships: (resident_a_id, resident_b_id, relationship_type)
    shop_relationships: (resident_id, shop_building_id, customer_score, purchase_count, is_primary)
    aggression/year_start: if either is given, creates a town_state table (omitted -> table
    absent, exercising the real snapshots' occasional-missing-table fallback)
    """
    conn = sqlite3.connect(path)
    conn.execute(
        "CREATE TABLE residents (id INTEGER PRIMARY KEY, ses TEXT, workplace_building_id INTEGER, "
        "death_date TEXT, gender TEXT, birth_date TEXT)"
    )
    conn.execute("CREATE TABLE relationships (resident_a_id INTEGER, resident_b_id INTEGER, relationship_type TEXT)")
    conn.execute(
        "CREATE TABLE shop_relationships (resident_id INTEGER, shop_building_id INTEGER, "
        "customer_score REAL, purchase_count INTEGER, is_primary INTEGER)"
    )
    conn.executemany(
        "INSERT INTO residents (id, ses, workplace_building_id, death_date, gender, birth_date) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        [tuple(row) + (None,) * (6 - len(row)) for row in residents],
    )
    conn.executemany("INSERT INTO relationships VALUES (?, ?, ?)", list(relationships))
    conn.executemany("INSERT INTO shop_relationships VALUES (?, ?, ?, ?, ?)", list(shop_relationships))
    if aggression is not None or year_start is not None:
        conn.execute("CREATE TABLE town_state (aggression REAL, year_start TEXT)")
        conn.execute(
            "INSERT INTO town_state (aggression, year_start) VALUES (?, ?)",
            (aggression if aggression is not None else 0.0, year_start),
        )
    conn.commit()
    conn.close()
