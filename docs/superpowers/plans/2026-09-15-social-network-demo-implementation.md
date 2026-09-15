# Social Network Demo Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the standalone `social-sim-demo` prototype: import a TownShape town snapshot into an enriched social graph, and run two example "phenomena" (disease-like contagion, animosity-driven violence) over it day-by-day through one generic engine.

**Architecture:** Four small modules with no framework dependencies. `graph.py` owns the data model (`Node`, `Edge`, `SocialGraph`) and the read-only import from a TownShape `.db` file, synthesizing edge attributes TownShape doesn't store. `phenomena.py` defines the generic `Phenomenon` interface plus the two concrete phenomena. `engine.py` runs the daily simulation loop against any list of phenomena. `demo.py` is the CLI that wires them together and writes output.

**Tech Stack:** Python 3, standard library only (`sqlite3`, `random`, `dataclasses`, `csv`, `json`, `argparse`, `pathlib`, `tempfile`). No pytest — plain `assert`-based test functions, runnable directly (e.g. `py -3 tests/test_graph.py`).

**Spec:** `docs/2026-09-15-social-network-design.md` (this plan implements it in full; read it first for the concepts — this plan focuses on exact code).

## Global Constraints

- Standard library only. Do not add any third-party dependency (no `pytest`, no `networkx`, no `numpy`).
- Every SQLite connection this project opens is read-only in effect — never call `INSERT`/`UPDATE`/`DELETE`/`CREATE` against a TownShape snapshot `.db` file. (Test fixtures are the one exception: they are throwaway temp files this project creates and owns.)
- Same `(db_path, seed)` must always produce the same `SocialGraph` and the same `SimulationResult` — every source of randomness goes through a `random.Random(seed)` instance passed explicitly, never the global `random` module.
- Tests must be hermetic: never read a file from the sibling `TownShape` repo. Use the `tests/fixtures.py` helper to build tiny temp-file SQLite databases instead (the real `demo_svg_overlay_town.db` is gitignored in TownShape and not guaranteed to exist).
- No test framework. Test files are plain Python with `assert` statements and a `_run_all()` / `if __name__ == "__main__":` block, runnable directly.

---

## Task 1: Core graph data structures

**Files:**
- Create: `graph.py`
- Test: `tests/test_graph.py`

**Interfaces:**
- Produces: `Node(resident_id: int, ses: Optional[str], alive: bool = True)` (dataclass); `Edge(resident_a: int, resident_b: int, source_type: str, fiske_type: str, time: float, intimacy: float, services: float, valence: float)` (dataclass, positional order as given) with a computed `.tie_strength` property; `SocialGraph` with `.nodes: Dict[int, Node]`, `.edges: Dict[Tuple[int,int], Edge]`, `.add_node(node)`, `.add_edge(edge)` (keeps the higher-`tie_strength` edge when a `(a,b)` pair already exists), `.get_edge(a, b) -> Optional[Edge]`, `.neighbors(resident_id) -> List[int]`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_graph.py
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from graph import Node, Edge, SocialGraph


def test_add_node_and_get_edge_roundtrip():
    graph = SocialGraph()
    graph.add_node(Node(resident_id=1, ses="poor", alive=True))
    graph.add_node(Node(resident_id=2, ses="rich", alive=True))
    edge = Edge(1, 2, "neighbor", "Equality Matching", time=0.3, intimacy=0.2, services=0.2, valence=0.1)
    graph.add_edge(edge)
    assert graph.get_edge(1, 2) is edge
    assert graph.get_edge(2, 1) is edge


def test_tie_strength_uses_absolute_valence():
    edge = Edge(1, 2, "neighbor", "Equality Matching", time=0.8, intimacy=0.8, services=0.8, valence=-0.8)
    assert abs(edge.tie_strength - 0.8) < 1e-9


def test_add_edge_dedup_keeps_higher_tie_strength():
    weak = Edge(1, 2, "neighbor", "Equality Matching", time=0.1, intimacy=0.1, services=0.1, valence=0.0)
    strong = Edge(1, 2, "coworker", "Authority Ranking", time=0.9, intimacy=0.5, services=0.6, valence=0.2)

    graph_a = SocialGraph()
    graph_a.add_edge(weak)
    graph_a.add_edge(strong)
    assert graph_a.get_edge(1, 2) is strong

    graph_b = SocialGraph()
    graph_b.add_edge(strong)
    graph_b.add_edge(weak)
    assert graph_b.get_edge(1, 2) is strong


def test_neighbors_finds_both_directions():
    graph = SocialGraph()
    graph.add_edge(Edge(1, 2, "neighbor", "Equality Matching", 0.3, 0.2, 0.2, 0.1))
    graph.add_edge(Edge(3, 1, "coworker", "Authority Ranking", 0.4, 0.2, 0.3, 0.0))
    assert sorted(graph.neighbors(1)) == [2, 3]


def _run_all():
    test_add_node_and_get_edge_roundtrip()
    test_tie_strength_uses_absolute_valence()
    test_add_edge_dedup_keeps_higher_tie_strength()
    test_neighbors_finds_both_directions()
    print("OK")


if __name__ == "__main__":
    _run_all()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `py -3 tests/test_graph.py`
Expected: `ModuleNotFoundError: No module named 'graph'` (the file doesn't exist yet).

- [ ] **Step 3: Write the implementation**

```python
# graph.py
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass
class Node:
    resident_id: int
    ses: Optional[str]
    alive: bool = True


@dataclass
class Edge:
    resident_a: int
    resident_b: int
    source_type: str
    fiske_type: str
    time: float
    intimacy: float
    services: float
    valence: float

    @property
    def tie_strength(self) -> float:
        return (self.time + abs(self.valence) + self.intimacy + self.services) / 4


class SocialGraph:
    def __init__(self) -> None:
        self.nodes: Dict[int, Node] = {}
        self.edges: Dict[Tuple[int, int], Edge] = {}

    def add_node(self, node: Node) -> None:
        self.nodes[node.resident_id] = node

    @staticmethod
    def _key(a: int, b: int) -> Tuple[int, int]:
        return (a, b) if a < b else (b, a)

    def add_edge(self, edge: Edge) -> None:
        key = self._key(edge.resident_a, edge.resident_b)
        existing = self.edges.get(key)
        if existing is not None and existing.tie_strength >= edge.tie_strength:
            return
        self.edges[key] = edge

    def get_edge(self, a: int, b: int) -> Optional[Edge]:
        return self.edges.get(self._key(a, b))

    def neighbors(self, resident_id: int) -> List[int]:
        result = []
        for a, b in self.edges:
            if a == resident_id:
                result.append(b)
            elif b == resident_id:
                result.append(a)
        return result
```

- [ ] **Step 4: Run test to verify it passes**

Run: `py -3 tests/test_graph.py`
Expected: prints `OK`, exits 0.

- [ ] **Step 5: Commit**

```bash
git add graph.py tests/test_graph.py
git commit -m "feat: add SocialGraph core data structures"
```

---

## Task 2: Relationship-type attribute synthesis + Fiske tags

**Files:**
- Modify: `graph.py` (append)
- Test: `tests/test_attributes.py`

**Interfaces:**
- Consumes: nothing new from Task 1 beyond `Edge`'s field names.
- Produces: `RELATIONSHIP_TYPE_BASELINES: Dict[str, Dict[str, Tuple[float, float]]]` (mean, stddev pairs for `time`/`intimacy`/`services`/`valence`, keyed by TownShape `relationship_type`); `FISKE_TAGS: Dict[str, str]` (superset of `RELATIONSHIP_TYPE_BASELINES` keys, plus `"shopkeeper_customer"`); `synthesize_relationship_attributes(relationship_type: str, rng: random.Random) -> Dict[str, float]` returning `{"time", "intimacy", "services", "valence"}`, each clamped to its valid range.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_attributes.py
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from graph import synthesize_relationship_attributes, FISKE_TAGS, RELATIONSHIP_TYPE_BASELINES


def test_synthesized_values_are_in_range():
    rng = random.Random(1)
    for relationship_type in RELATIONSHIP_TYPE_BASELINES:
        for _ in range(50):
            attrs = synthesize_relationship_attributes(relationship_type, rng)
            assert 0.0 <= attrs["time"] <= 1.0
            assert 0.0 <= attrs["intimacy"] <= 1.0
            assert 0.0 <= attrs["services"] <= 1.0
            assert -1.0 <= attrs["valence"] <= 1.0


def test_synthesis_is_deterministic_given_same_seed():
    attrs_a = synthesize_relationship_attributes("spouse", random.Random(42))
    attrs_b = synthesize_relationship_attributes("spouse", random.Random(42))
    assert attrs_a == attrs_b


def test_every_baseline_type_has_a_fiske_tag():
    for relationship_type in RELATIONSHIP_TYPE_BASELINES:
        assert relationship_type in FISKE_TAGS
    assert FISKE_TAGS["shopkeeper_customer"] == "Market Pricing"


def _run_all():
    test_synthesized_values_are_in_range()
    test_synthesis_is_deterministic_given_same_seed()
    test_every_baseline_type_has_a_fiske_tag()
    print("OK")


if __name__ == "__main__":
    _run_all()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `py -3 tests/test_attributes.py`
Expected: `ImportError: cannot import name 'synthesize_relationship_attributes' from 'graph'`.

- [ ] **Step 3: Write the implementation**

Append to `graph.py` (after the existing imports, add `import random`; place the rest after the `SocialGraph` class):

```python
RELATIONSHIP_TYPE_BASELINES = {
    "spouse":    {"time": (0.75, 0.15), "intimacy": (0.80, 0.15), "services": (0.75, 0.15), "valence": (0.40, 0.40)},
    "parent":    {"time": (0.70, 0.15), "intimacy": (0.75, 0.15), "services": (0.70, 0.15), "valence": (0.40, 0.40)},
    "sibling":   {"time": (0.60, 0.20), "intimacy": (0.60, 0.20), "services": (0.60, 0.20), "valence": (0.30, 0.45)},
    "unit_mate": {"time": (0.55, 0.20), "intimacy": (0.40, 0.20), "services": (0.65, 0.20), "valence": (0.35, 0.30)},
    "coworker":  {"time": (0.45, 0.20), "intimacy": (0.20, 0.15), "services": (0.40, 0.20), "valence": (0.00, 0.35)},
    "neighbor":  {"time": (0.25, 0.15), "intimacy": (0.20, 0.15), "services": (0.30, 0.20), "valence": (0.00, 0.35)},
    "classmate": {"time": (0.45, 0.20), "intimacy": (0.20, 0.20), "services": (0.25, 0.20), "valence": (0.00, 0.40)},
}

FISKE_TAGS = {
    "spouse": "Communal Sharing",
    "parent": "Communal Sharing",
    "sibling": "Communal Sharing",
    "unit_mate": "Equality Matching",
    "coworker": "Authority Ranking",
    "neighbor": "Equality Matching",
    "classmate": "Communal Sharing",
    "shopkeeper_customer": "Market Pricing",
}


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _clamp_signed(value: float) -> float:
    return max(-1.0, min(1.0, value))


def synthesize_relationship_attributes(relationship_type: str, rng: random.Random) -> Dict[str, float]:
    baseline = RELATIONSHIP_TYPE_BASELINES[relationship_type]
    return {
        "time": _clamp01(rng.gauss(*baseline["time"])),
        "intimacy": _clamp01(rng.gauss(*baseline["intimacy"])),
        "services": _clamp01(rng.gauss(*baseline["services"])),
        "valence": _clamp_signed(rng.gauss(*baseline["valence"])),
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `py -3 tests/test_attributes.py`
Expected: prints `OK`, exits 0.

- [ ] **Step 5: Commit**

```bash
git add graph.py tests/test_attributes.py
git commit -m "feat: synthesize edge attributes per relationship type"
```

---

## Task 3: Import residents + relationships from a TownShape snapshot

**Files:**
- Modify: `graph.py` (append)
- Create: `tests/fixtures.py`
- Test: `tests/test_import_relationships.py`

**Interfaces:**
- Consumes: `Node`, `Edge`, `SocialGraph`, `RELATIONSHIP_TYPE_BASELINES`, `FISKE_TAGS`, `synthesize_relationship_attributes` (Tasks 1–2).
- Produces: `import_snapshot(db_path: str, seed: int) -> SocialGraph` (residents + relationships only at this point — Task 4 extends it); `tests/fixtures.py`'s `make_test_db(path, residents, relationships=(), shop_relationships=())` for building hermetic SQLite fixtures, reused by Task 4's tests.

- [ ] **Step 1: Write the failing test**

```python
# tests/fixtures.py
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
```

```python
# tests/test_import_relationships.py
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
        assert graph_a.get_edge(1, 2).valence == graph_b.get_edge(1, 2).valence


def _run_all():
    test_import_loads_all_residents()
    test_import_loads_relationship_edges_with_correct_types()
    test_import_is_deterministic_given_same_seed()
    print("OK")


if __name__ == "__main__":
    _run_all()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `py -3 tests/test_import_relationships.py`
Expected: `ImportError: cannot import name 'import_snapshot' from 'graph'`.

- [ ] **Step 3: Write the implementation**

Append to `graph.py` (add `import sqlite3` to the imports):

```python
def _load_residents(conn: sqlite3.Connection, graph: SocialGraph) -> None:
    rows = conn.execute("SELECT id, ses FROM residents").fetchall()
    for resident_id, ses in rows:
        graph.add_node(Node(resident_id=resident_id, ses=ses, alive=True))


def _load_relationships(conn: sqlite3.Connection, graph: SocialGraph, rng: random.Random) -> None:
    rows = conn.execute(
        "SELECT resident_a_id, resident_b_id, relationship_type FROM relationships"
    ).fetchall()
    for resident_a_id, resident_b_id, relationship_type in rows:
        if relationship_type not in RELATIONSHIP_TYPE_BASELINES:
            continue
        attrs = synthesize_relationship_attributes(relationship_type, rng)
        graph.add_edge(
            Edge(
                resident_a=resident_a_id,
                resident_b=resident_b_id,
                source_type=relationship_type,
                fiske_type=FISKE_TAGS[relationship_type],
                **attrs,
            )
        )


def import_snapshot(db_path: str, seed: int) -> SocialGraph:
    rng = random.Random(seed)
    graph = SocialGraph()
    conn = sqlite3.connect(db_path)
    try:
        _load_residents(conn, graph)
        _load_relationships(conn, graph, rng)
    finally:
        conn.close()
    return graph
```

- [ ] **Step 4: Run test to verify it passes**

Run: `py -3 tests/test_import_relationships.py`
Expected: prints `OK`, exits 0.

- [ ] **Step 5: Commit**

```bash
git add graph.py tests/fixtures.py tests/test_import_relationships.py
git commit -m "feat: import residents and relationships from a TownShape snapshot"
```

---

## Task 4: Derive shopkeeper-customer edges

**Files:**
- Modify: `graph.py` (append `_load_shopkeeper_customer`, extend `import_snapshot`)
- Test: `tests/test_import_shopkeeper_customer.py`

**Interfaces:**
- Consumes: `SocialGraph`, `Edge`, `FISKE_TAGS["shopkeeper_customer"]`, `_clamp01`, `_clamp_signed`, `import_snapshot` (Tasks 1–3); `make_test_db` (Task 3).
- Produces: `import_snapshot` now also creates `"shopkeeper_customer"` edges.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_import_shopkeeper_customer.py
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


def _run_all():
    test_shopkeeper_customer_edges_created_for_each_staff_member()
    test_staff_member_buying_from_own_shop_does_not_self_link()
    test_time_and_services_scale_with_real_purchase_data()
    print("OK")


if __name__ == "__main__":
    _run_all()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `py -3 tests/test_import_shopkeeper_customer.py`
Expected: `AssertionError` on the first test (no `shopkeeper_customer` edges exist yet — `import_snapshot` doesn't load them).

- [ ] **Step 3: Write the implementation**

Append to `graph.py`:

```python
def _load_shopkeeper_customer(conn: sqlite3.Connection, graph: SocialGraph, rng: random.Random) -> None:
    rows = conn.execute(
        """
        SELECT sr.resident_id, r.id AS staff_id, sr.customer_score, sr.purchase_count, sr.is_primary
        FROM shop_relationships sr
        JOIN residents r ON r.workplace_building_id = sr.shop_building_id
        WHERE sr.resident_id != r.id
        """
    ).fetchall()
    if not rows:
        return

    max_customer_score = max(row[2] for row in rows) or 1.0
    max_purchase_count = max(row[3] for row in rows) or 1.0

    for customer_id, staff_id, customer_score, purchase_count, is_primary in rows:
        time = _clamp01(customer_score / max_customer_score)
        services = _clamp01(purchase_count / max_purchase_count)
        intimacy = _clamp01(rng.gauss(0.10, 0.08))
        valence_mean = 0.15 if is_primary else 0.0
        valence = _clamp_signed(rng.gauss(valence_mean, 0.30))
        graph.add_edge(
            Edge(
                resident_a=customer_id,
                resident_b=staff_id,
                source_type="shopkeeper_customer",
                fiske_type=FISKE_TAGS["shopkeeper_customer"],
                time=time,
                intimacy=intimacy,
                services=services,
                valence=valence,
            )
        )
```

Modify `import_snapshot` to also call it:

```python
def import_snapshot(db_path: str, seed: int) -> SocialGraph:
    rng = random.Random(seed)
    graph = SocialGraph()
    conn = sqlite3.connect(db_path)
    try:
        _load_residents(conn, graph)
        _load_relationships(conn, graph, rng)
        _load_shopkeeper_customer(conn, graph, rng)
    finally:
        conn.close()
    return graph
```

- [ ] **Step 4: Run test to verify it passes**

Run: `py -3 tests/test_import_shopkeeper_customer.py`
Expected: prints `OK`, exits 0.
Also re-run: `py -3 tests/test_import_relationships.py` — must still print `OK` (no regression).

- [ ] **Step 5: Commit**

```bash
git add graph.py tests/test_import_shopkeeper_customer.py
git commit -m "feat: derive shopkeeper-customer edges from shop_relationships"
```

---

## Task 5: Generic Phenomenon interface + ContagionPhenomenon

**Files:**
- Create: `phenomena.py`
- Test: `tests/test_contagion.py`

**Interfaces:**
- Consumes: `Node`, `Edge`, `SocialGraph` (Task 1).
- Produces: `Event(day: int, phenomenon: str, kind: str, resident_a: int, resident_b: int, detail: str)` (dataclass); `Phenomenon` (`typing.Protocol` documenting the contract: `name: str`, `init_state(graph) -> Dict[int, Any]`, `edge_probability(edge, state_a, state_b, day) -> float`, `apply_effect(graph, state, a, b, day, rng) -> List[Event]`, `end_of_day(graph, state, day) -> List[Event]`, `summarize(state) -> Dict[str, int]`); `ContagionPhenomenon(base_rate: float = 0.5, infectious_days: int = 7, patient_zero: Optional[int] = None)` implementing that contract with SIR-style state.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_contagion.py
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from graph import Edge, Node, SocialGraph
from phenomena import ContagionPhenomenon


def test_edge_probability_matches_worked_example():
    graph = SocialGraph()
    graph.add_node(Node(resident_id=1, ses="poor", alive=True))
    graph.add_node(Node(resident_id=2, ses="rich", alive=True))
    edge = Edge(1, 2, "coworker", "Authority Ranking", time=0.4, intimacy=0.4, services=0.4, valence=0.4)
    graph.add_edge(edge)

    phenomenon = ContagionPhenomenon(base_rate=0.5)
    state = {1: {"status": "infected", "days_left": 7}, 2: {"status": "susceptible", "days_left": 0}}
    probability = phenomenon.edge_probability(edge, state[1], state[2], day=12)
    # tie_strength = mean(0.4, 0.4, 0.4, 0.4) = 0.4; type_weight[coworker] = 0.3
    assert abs(probability - (0.5 * 0.4 * 0.3)) < 1e-9


def test_probability_is_zero_when_neither_endpoint_infected():
    graph = SocialGraph()
    edge = Edge(1, 2, "coworker", "Authority Ranking", 0.4, 0.4, 0.4, 0.0)
    graph.add_edge(edge)
    phenomenon = ContagionPhenomenon()
    state_a = {"status": "susceptible", "days_left": 0}
    state_b = {"status": "susceptible", "days_left": 0}
    assert phenomenon.edge_probability(edge, state_a, state_b, day=1) == 0.0


def test_infected_recovers_after_infectious_days():
    graph = SocialGraph()
    graph.add_node(Node(resident_id=1, ses="poor", alive=True))
    graph.add_node(Node(resident_id=2, ses="rich", alive=True))
    phenomenon = ContagionPhenomenon(infectious_days=3, patient_zero=1)
    state = phenomenon.init_state(graph)
    for day in range(1, 4):
        phenomenon.end_of_day(graph, state, day)
    assert state[1]["status"] == "recovered"


def test_summarize_counts_every_status():
    state = {
        1: {"status": "infected", "days_left": 2},
        2: {"status": "susceptible", "days_left": 0},
        3: {"status": "recovered", "days_left": 0},
    }
    phenomenon = ContagionPhenomenon()
    assert phenomenon.summarize(state) == {"susceptible": 1, "infected": 1, "recovered": 1}


def _run_all():
    test_edge_probability_matches_worked_example()
    test_probability_is_zero_when_neither_endpoint_infected()
    test_infected_recovers_after_infectious_days()
    test_summarize_counts_every_status()
    print("OK")


if __name__ == "__main__":
    _run_all()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `py -3 tests/test_contagion.py`
Expected: `ModuleNotFoundError: No module named 'phenomena'`.

- [ ] **Step 3: Write the implementation**

```python
# phenomena.py
import random
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Protocol


@dataclass
class Event:
    day: int
    phenomenon: str
    kind: str
    resident_a: int
    resident_b: int
    detail: str


class Phenomenon(Protocol):
    name: str

    def init_state(self, graph) -> Dict[int, Any]: ...
    def edge_probability(self, edge, state_a, state_b, day: int) -> float: ...
    def apply_effect(self, graph, state, a: int, b: int, day: int, rng: random.Random) -> List[Event]: ...
    def end_of_day(self, graph, state, day: int) -> List[Event]: ...
    def summarize(self, state) -> Dict[str, int]: ...


# type_weight is higher for household-equivalent ties than for incidental ones (design doc §7)
CONTAGION_TYPE_WEIGHTS = {
    "spouse": 1.0,
    "parent": 1.0,
    "sibling": 1.0,
    "unit_mate": 0.6,
    "coworker": 0.3,
    "neighbor": 0.2,
    "classmate": 0.2,
    "shopkeeper_customer": 0.15,
}


class ContagionPhenomenon:
    name = "contagion"

    def __init__(self, base_rate: float = 0.5, infectious_days: int = 7, patient_zero: Optional[int] = None):
        self.base_rate = base_rate
        self.infectious_days = infectious_days
        self.patient_zero = patient_zero

    def init_state(self, graph) -> Dict[int, Any]:
        state = {resident_id: {"status": "susceptible", "days_left": 0} for resident_id in graph.nodes}
        patient_zero = self.patient_zero if self.patient_zero is not None else min(graph.nodes)
        state[patient_zero] = {"status": "infected", "days_left": self.infectious_days}
        return state

    def edge_probability(self, edge, state_a, state_b, day: int) -> float:
        statuses = {state_a["status"], state_b["status"]}
        if statuses != {"infected", "susceptible"}:
            return 0.0
        weight = CONTAGION_TYPE_WEIGHTS.get(edge.source_type, 0.2)
        return self.base_rate * edge.tie_strength * weight

    def apply_effect(self, graph, state, a: int, b: int, day: int, rng: random.Random) -> List[Event]:
        newly_infected, source = (a, b) if state[a]["status"] == "susceptible" else (b, a)
        state[newly_infected] = {"status": "infected", "days_left": self.infectious_days}
        return [Event(day, self.name, "infected", source, newly_infected, "transmission")]

    def end_of_day(self, graph, state, day: int) -> List[Event]:
        events: List[Event] = []
        for resident_id, resident_state in state.items():
            if resident_state["status"] != "infected":
                continue
            resident_state["days_left"] -= 1
            if resident_state["days_left"] <= 0:
                resident_state["status"] = "recovered"
                events.append(Event(day, self.name, "recovered", resident_id, resident_id, "recovered"))
        return events

    def summarize(self, state) -> Dict[str, int]:
        counts = {"susceptible": 0, "infected": 0, "recovered": 0}
        for resident_state in state.values():
            counts[resident_state["status"]] += 1
        return counts
```

- [ ] **Step 4: Run test to verify it passes**

Run: `py -3 tests/test_contagion.py`
Expected: prints `OK`, exits 0.

- [ ] **Step 5: Commit**

```bash
git add phenomena.py tests/test_contagion.py
git commit -m "feat: add generic Phenomenon interface and ContagionPhenomenon"
```

---

## Task 6: ViolencePhenomenon with grief feedback

**Files:**
- Modify: `phenomena.py` (append)
- Test: `tests/test_violence.py`

**Interfaces:**
- Consumes: `Event`, `Phenomenon` (Task 5); `Node`, `Edge`, `SocialGraph` (Task 1).
- Produces: `ViolencePhenomenon(base_rate: float = 0.01, grief_shock: float = 0.15)` implementing the `Phenomenon` contract with alive/dead state, valence-driven probability, and the victim's-neighbors-turn-against-the-culprit feedback effect described in design doc §8.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_violence.py
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from graph import Edge, Node, SocialGraph
from phenomena import ViolencePhenomenon


def _graph_with_valence(valence: float) -> SocialGraph:
    graph = SocialGraph()
    graph.add_node(Node(resident_id=1, ses="poor", alive=True))
    graph.add_node(Node(resident_id=2, ses="rich", alive=True))
    graph.add_edge(Edge(1, 2, "neighbor", "Equality Matching", time=0.5, intimacy=0.5, services=0.5, valence=valence))
    return graph


def test_positive_valence_edges_never_fire():
    graph = _graph_with_valence(0.6)
    phenomenon = ViolencePhenomenon(base_rate=0.5)
    state = phenomenon.init_state(graph)
    edge = graph.get_edge(1, 2)
    assert phenomenon.edge_probability(edge, state[1], state[2], day=1) == 0.0


def test_edge_probability_formula():
    graph = SocialGraph()
    graph.add_node(Node(resident_id=1, ses="poor", alive=True))
    graph.add_node(Node(resident_id=2, ses="rich", alive=True))
    edge = Edge(1, 2, "neighbor", "Equality Matching", time=0.4, intimacy=0.4, services=0.4, valence=-0.4)
    graph.add_edge(edge)
    phenomenon = ViolencePhenomenon(base_rate=0.1)
    state = phenomenon.init_state(graph)
    probability = phenomenon.edge_probability(edge, state[1], state[2], day=1)
    # tie_strength = mean(0.4, 0.4, 0.4, 0.4) = 0.4; probability = base_rate * |valence| * tie_strength
    assert abs(probability - (0.1 * 0.4 * 0.4)) < 1e-9


def test_probability_is_monotonic_in_animosity_magnitude():
    phenomenon = ViolencePhenomenon(base_rate=0.5)
    mild = _graph_with_valence(-0.2)
    severe = _graph_with_valence(-0.9)
    state_mild = phenomenon.init_state(mild)
    state_severe = phenomenon.init_state(severe)
    p_mild = phenomenon.edge_probability(mild.get_edge(1, 2), state_mild[1], state_mild[2], day=1)
    p_severe = phenomenon.edge_probability(severe.get_edge(1, 2), state_severe[1], state_severe[2], day=1)
    assert p_severe > p_mild


def test_grief_shock_increases_neighbors_animosity_toward_culprit():
    graph = SocialGraph()
    for resident_id, ses in [(1, "poor"), (2, "rich"), (3, "middling")]:
        graph.add_node(Node(resident_id=resident_id, ses=ses, alive=True))
    # 1 and 2 are the violent pair; 3 is close to 1 (the victim) and already knows 2 (the culprit)
    graph.add_edge(Edge(1, 2, "neighbor", "Equality Matching", 0.5, 0.5, 0.5, -0.9))
    graph.add_edge(Edge(1, 3, "sibling", "Communal Sharing", 0.8, 0.8, 0.8, 0.7))
    graph.add_edge(Edge(2, 3, "coworker", "Authority Ranking", 0.4, 0.2, 0.3, 0.1))

    phenomenon = ViolencePhenomenon(base_rate=1.0, grief_shock=0.15)
    state = phenomenon.init_state(graph)
    phenomenon._pick_victim = lambda graph, a, b, rng: 1  # force resident 1 to be the victim

    events = phenomenon.apply_effect(graph, state, 1, 2, day=200, rng=random.Random(0))

    assert graph.nodes[1].alive is False
    assert state[1]["alive"] is False
    edge_2_3 = graph.get_edge(2, 3)
    assert edge_2_3.valence < 0.1  # nudged more negative from its starting 0.1
    assert any(event.kind == "grief_shock" and event.resident_a == 3 for event in events)


def test_summarize_counts_alive_and_dead():
    graph = _graph_with_valence(-0.5)
    phenomenon = ViolencePhenomenon()
    state = phenomenon.init_state(graph)
    state[1]["alive"] = False
    assert phenomenon.summarize(state) == {"alive": 1, "dead": 1}


def _run_all():
    test_positive_valence_edges_never_fire()
    test_edge_probability_formula()
    test_probability_is_monotonic_in_animosity_magnitude()
    test_grief_shock_increases_neighbors_animosity_toward_culprit()
    test_summarize_counts_alive_and_dead()
    print("OK")


if __name__ == "__main__":
    _run_all()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `py -3 tests/test_violence.py`
Expected: `ImportError: cannot import name 'ViolencePhenomenon' from 'phenomena'`.

- [ ] **Step 3: Write the implementation**

Append to `phenomena.py`:

```python
# ponytail: placeholder victim-selection rule (skews toward lower socioeconomic status);
# swap for a real vulnerability model if "good enough" stops being good enough
SES_VULNERABILITY = {"poor": 2.0, "middling": 1.0, "rich": 0.5}


class ViolencePhenomenon:
    name = "violence"

    def __init__(self, base_rate: float = 0.01, grief_shock: float = 0.15):
        self.base_rate = base_rate
        self.grief_shock = grief_shock

    def init_state(self, graph) -> Dict[int, Any]:
        return {resident_id: {"alive": True} for resident_id in graph.nodes}

    def edge_probability(self, edge, state_a, state_b, day: int) -> float:
        if not (state_a["alive"] and state_b["alive"]):
            return 0.0
        if edge.valence >= 0:
            return 0.0
        return self.base_rate * (-edge.valence) * edge.tie_strength

    def _pick_victim(self, graph, a: int, b: int, rng: random.Random) -> int:
        weight_a = SES_VULNERABILITY.get(graph.nodes[a].ses, 1.0)
        weight_b = SES_VULNERABILITY.get(graph.nodes[b].ses, 1.0)
        return a if rng.random() < weight_a / (weight_a + weight_b) else b

    def apply_effect(self, graph, state, a: int, b: int, day: int, rng: random.Random) -> List[Event]:
        victim = self._pick_victim(graph, a, b, rng)
        culprit = b if victim == a else a

        state[victim]["alive"] = False
        graph.nodes[victim].alive = False

        events = [Event(day, self.name, "violence", culprit, victim, "escalated conflict")]

        for neighbor_id in graph.neighbors(victim):
            if neighbor_id == culprit:
                continue
            edge_to_culprit = graph.get_edge(neighbor_id, culprit)
            if edge_to_culprit is None:
                continue
            edge_to_victim = graph.get_edge(neighbor_id, victim)
            shock = self.grief_shock * edge_to_victim.tie_strength
            edge_to_culprit.valence = max(-1.0, edge_to_culprit.valence - shock)
            events.append(Event(day, self.name, "grief_shock", neighbor_id, culprit, f"valence -{shock:.3f}"))

        return events

    def end_of_day(self, graph, state, day: int) -> List[Event]:
        return []

    def summarize(self, state) -> Dict[str, int]:
        alive = sum(1 for resident_state in state.values() if resident_state["alive"])
        return {"alive": alive, "dead": len(state) - alive}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `py -3 tests/test_violence.py`
Expected: prints `OK`, exits 0.
Also re-run: `py -3 tests/test_contagion.py` — must still print `OK`.

- [ ] **Step 5: Commit**

```bash
git add phenomena.py tests/test_violence.py
git commit -m "feat: add ViolencePhenomenon with grief-feedback effect"
```

---

## Task 7: Simulation engine (daily loop)

**Files:**
- Create: `engine.py`
- Test: `tests/test_engine.py`

**Interfaces:**
- Consumes: `Node`, `Edge`, `SocialGraph` (Task 1); `Event`, `Phenomenon`, `ContagionPhenomenon`, `ViolencePhenomenon` (Tasks 5–6).
- Produces: `SimulationResult(daily_summaries: List[Dict[str, int]], events: List[Event])` (dataclass, both fields default to empty lists); `run_simulation(graph: SocialGraph, phenomena: List[Phenomenon], days: int, seed: int) -> SimulationResult`.

- [ ] **Step 1: Write the failing test**

```python
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
    graph.add_edge(Edge(1, 2, "spouse", "Communal Sharing", 0.9, 0.9, 0.9, 0.8))
    graph.add_edge(Edge(2, 3, "coworker", "Authority Ranking", 0.4, 0.2, 0.3, -0.9))
    # resident 4 has no edges at all -- isolated
    return graph


def test_isolated_resident_never_gets_infected():
    graph = _sample_graph()
    phenomenon = ContagionPhenomenon(base_rate=1.0)  # patient zero = resident 1 (lowest id)
    result = run_simulation(graph, [phenomenon], days=60, seed=1)
    assert all(event.resident_a != 4 and event.resident_b != 4 for event in result.events)


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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `py -3 tests/test_engine.py`
Expected: `ModuleNotFoundError: No module named 'engine'`.

- [ ] **Step 3: Write the implementation**

```python
# engine.py
import random
from dataclasses import dataclass, field
from typing import Dict, List

from phenomena import Event, Phenomenon


@dataclass
class SimulationResult:
    daily_summaries: List[Dict[str, int]] = field(default_factory=list)
    events: List[Event] = field(default_factory=list)


def run_simulation(graph, phenomena: List[Phenomenon], days: int, seed: int) -> SimulationResult:
    rng = random.Random(seed)
    states = {phenomenon.name: phenomenon.init_state(graph) for phenomenon in phenomena}
    result = SimulationResult()

    for day in range(1, days + 1):
        for phenomenon in phenomena:
            state = states[phenomenon.name]
            for edge in list(graph.edges.values()):
                a, b = edge.resident_a, edge.resident_b
                if not (graph.nodes[a].alive and graph.nodes[b].alive):
                    continue
                probability = phenomenon.edge_probability(edge, state[a], state[b], day)
                if probability > 0 and rng.random() < probability:
                    result.events.extend(phenomenon.apply_effect(graph, state, a, b, day, rng))
            result.events.extend(phenomenon.end_of_day(graph, state, day))

        summary = {"day": day}
        for phenomenon in phenomena:
            summary.update(phenomenon.summarize(states[phenomenon.name]))
        result.daily_summaries.append(summary)

    return result
```

- [ ] **Step 4: Run test to verify it passes**

Run: `py -3 tests/test_engine.py`
Expected: prints `OK`, exits 0.
Also re-run Tasks 1–6's test files — all must still print `OK`.

- [ ] **Step 5: Commit**

```bash
git add engine.py tests/test_engine.py
git commit -m "feat: add daily simulation engine driving phenomena over a SocialGraph"
```

---

## Task 8: CLI demo script + output writers

**Files:**
- Create: `demo.py`

**Interfaces:**
- Consumes: `import_snapshot` (Task 4); `ContagionPhenomenon`, `ViolencePhenomenon` (Tasks 5–6); `run_simulation`, `SimulationResult` (Task 7).
- Produces: `main(argv=None) -> None`, runnable as `py -3 demo.py --db <path> [--days N] [--seed N] [--out DIR]`.

No dedicated automated test for this task — it's CLI glue over already-tested modules (Tasks 3–7 cover the logic it calls). Verify it manually in Step 3.

- [ ] **Step 1: Write the implementation**

```python
# demo.py
import argparse
import csv
import json
from dataclasses import asdict
from pathlib import Path

from graph import import_snapshot
from phenomena import ContagionPhenomenon, ViolencePhenomenon
from engine import run_simulation


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description="Run the social-sim demo over a TownShape snapshot.")
    parser.add_argument("--db", required=True, help="Path to a TownShape .db snapshot")
    parser.add_argument("--days", type=int, default=365)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", default="output")
    args = parser.parse_args(argv)

    graph = import_snapshot(args.db, args.seed)
    phenomena = [ContagionPhenomenon(), ViolencePhenomenon()]
    result = run_simulation(graph, phenomena, args.days, args.seed)

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    _write_summary_csv(out_dir / "summary.csv", result.daily_summaries)
    _write_events_json(out_dir / "events.json", result.events)
    _print_summary(result)


def _write_summary_csv(path: Path, daily_summaries) -> None:
    if not daily_summaries:
        return
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(daily_summaries[0].keys()))
        writer.writeheader()
        writer.writerows(daily_summaries)


def _write_events_json(path: Path, events) -> None:
    with open(path, "w") as f:
        json.dump([asdict(event) for event in events], f, indent=2)


def _print_summary(result) -> None:
    last = result.daily_summaries[-1] if result.daily_summaries else {}
    print(f"Simulated {len(result.daily_summaries)} days.")
    print(f"Final state: {last}")
    print(f"Total events logged: {len(result.events)}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verify manually against the real sample town**

Run: `py -3 demo.py --db "../TownShape/demo_svg_overlay_town.db" --days 365 --seed 42`
Expected: prints `Simulated 365 days.`, a final-state dict with `susceptible`/`infected`/`recovered`/`alive`/`dead` counts, and a nonzero `Total events logged`. Confirm `output/summary.csv` has 365 data rows and `output/events.json` is valid JSON with `day`/`phenomenon`/`kind`/`resident_a`/`resident_b`/`detail` keys per entry.

(If `demo_svg_overlay_town.db` doesn't exist locally, regenerate it from the TownShape repo first, or point `--db` at any other snapshot that has a populated `relationships` table.)

- [ ] **Step 3: Commit**

```bash
git add demo.py
git commit -m "feat: add CLI demo script tying import, engine, and output together"
```

---

## Self-Review Notes

- **Spec coverage:** §4 (graph data structure) → Task 1. §3.2–3.4 (tie strength, valence, Fiske) → Task 2. §2 (residents/relationships import) → Task 3. §2/§5 (shopkeeper-customer derivation) → Task 4. §6/§7 (generic interface, contagion) → Task 5. §8 (violence + grief feedback) → Task 6. §6.2 (daily loop) → Task 7. §9 (output) → Task 8. §11's "no write-back, no topology change" constraints are enforced structurally (no `INSERT`/`UPDATE` anywhere in `graph.py`; `SocialGraph` has no edge-removal or edge-creation-after-import method).
- **Placeholder scan:** none found — every step has runnable code, no "TBD"/"add error handling" left implicit.
- **Type consistency:** `Edge`'s field order (`resident_a, resident_b, source_type, fiske_type, time, intimacy, services, valence`) is used identically in Tasks 1, 3, 4, 5, 6. `Phenomenon.name`/`init_state`/`edge_probability`/`apply_effect`/`end_of_day`/`summarize` signatures match between the Task 5 protocol, `ContagionPhenomenon`, `ViolencePhenomenon`, and `engine.run_simulation`'s usage.
