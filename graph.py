import random
import sqlite3
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional, Tuple


@dataclass
class Node:
    resident_id: int
    ses: Optional[str]
    alive: bool = True
    # personal traits, each 0..1, independent of ses; shape event odds
    # (bribability, crime success, riot participation, ...) as those
    # phenomena get built. Not yet mutated by events themselves.
    religiousness: float = 0.5
    cunning: float = 0.5
    skepticism: float = 0.5
    loyalty: float = 0.5
    gender: Optional[str] = None
    # whole years, computed once at import against town_state.year_start;
    # None if birth_date or year_start is unavailable (e.g. test fixtures)
    age: Optional[int] = None
    occupation: Optional[str] = None
    is_noble: bool = False

    @property
    def role(self) -> str:
        """Coarse social role, derived from TownShape's own occupation/is_noble
        fields -- infra for Guards/Priests/Nobles phenomena, not a new schema."""
        if self.is_noble:
            return "noble"  # takes priority: a noble who also guards isn't rank-and-file
        if self.occupation == "guard":
            return "guard"
        if self.occupation in ("priest", "acolyte"):
            return "priest"
        return "civilian"


@dataclass
class Edge:
    resident_a: int
    resident_b: int
    source_type: str
    fiske_type: str
    time: float
    intimacy: float
    services: float
    valence_a_to_b: float
    valence_b_to_a: float

    @property
    def tie_strength(self) -> float:
        avg_abs_valence = (abs(self.valence_a_to_b) + abs(self.valence_b_to_a)) / 2
        return (self.time + avg_abs_valence + self.intimacy + self.services) / 4

    def valence_from(self, resident_id: int) -> float:
        """How `resident_id` feels about the other endpoint."""
        if resident_id == self.resident_a:
            return self.valence_a_to_b
        if resident_id == self.resident_b:
            return self.valence_b_to_a
        raise ValueError(f"{resident_id} is not part of this edge")

    def set_valence_from(self, resident_id: int, value: float) -> None:
        if resident_id == self.resident_a:
            self.valence_a_to_b = value
        elif resident_id == self.resident_b:
            self.valence_b_to_a = value
        else:
            raise ValueError(f"{resident_id} is not part of this edge")


class SocialGraph:
    def __init__(self) -> None:
        self.nodes: Dict[int, Node] = {}
        self.edges: Dict[Tuple[int, int], Edge] = {}
        # TownShape's own town-wide generation dial (0..1, defaults to 0.0
        # meaning "no extra volatility" -- not "no violence at all"). Read
        # at import; a "guardrail" multiplier for phenomena to apply, not a
        # phenomenon itself.
        self.town_aggression: float = 0.0

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


TRAIT_NAMES = ["religiousness", "cunning", "skepticism", "loyalty"]


def synthesize_traits(rng: random.Random) -> Dict[str, float]:
    # ponytail: flat, uncorrelated draw per resident; once occupations/roles
    # exist (e.g. Priests), skew religiousness etc. by role instead
    return {name: _clamp01(rng.gauss(0.5, 0.2)) for name in TRAIT_NAMES}


def synthesize_relationship_attributes(relationship_type: str, rng: random.Random) -> Dict[str, float]:
    baseline = RELATIONSHIP_TYPE_BASELINES[relationship_type]
    return {
        "time": _clamp01(rng.gauss(*baseline["time"])),
        "intimacy": _clamp01(rng.gauss(*baseline["intimacy"])),
        "services": _clamp01(rng.gauss(*baseline["services"])),
        # drawn independently: how much A resents/loves B need not match the reverse
        "valence_a_to_b": _clamp_signed(rng.gauss(*baseline["valence"])),
        "valence_b_to_a": _clamp_signed(rng.gauss(*baseline["valence"])),
    }


def _age_from_birth_date(birth_date: Optional[str], reference_year: Optional[int]) -> Optional[int]:
    if birth_date is None or reference_year is None:
        return None
    try:
        birth_year = date.fromisoformat(birth_date).year
    except ValueError:
        return None
    # ponytail: year-only precision (no month/day), fine for an adulthood gate
    return max(0, reference_year - birth_year)


def _load_residents(
    conn: sqlite3.Connection, graph: SocialGraph, rng: random.Random, reference_year: Optional[int]
) -> None:
    rows = conn.execute(
        "SELECT id, ses, gender, birth_date, occupation, is_noble FROM residents WHERE death_date IS NULL"
        " ORDER BY id"
    ).fetchall()
    for resident_id, ses, gender, birth_date, occupation, is_noble in rows:
        age = _age_from_birth_date(birth_date, reference_year)
        graph.add_node(
            Node(
                resident_id=resident_id, ses=ses, alive=True, gender=gender, age=age,
                occupation=occupation, is_noble=bool(is_noble), **synthesize_traits(rng),
            )
        )


def _load_relationships(conn: sqlite3.Connection, graph: SocialGraph, rng: random.Random) -> None:
    rows = conn.execute(
        "SELECT resident_a_id, resident_b_id, relationship_type FROM relationships"
        " ORDER BY resident_a_id, resident_b_id"
    ).fetchall()
    for resident_a_id, resident_b_id, relationship_type in rows:
        if relationship_type not in RELATIONSHIP_TYPE_BASELINES:
            continue
        # skip dangling edges: either endpoint may be absent (dead, or a data gap)
        if resident_a_id not in graph.nodes or resident_b_id not in graph.nodes:
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


def _load_town_state(conn: sqlite3.Connection, graph: SocialGraph) -> Optional[int]:
    # not every snapshot (e.g. test fixtures) has a town_state table -- default to
    # neutral aggression (0.0) and no reference year, rather than fail an otherwise-valid import
    try:
        row = conn.execute("SELECT aggression, year_start FROM town_state LIMIT 1").fetchone()
    except sqlite3.OperationalError:
        return None
    if row is None:
        return None
    aggression, year_start = row
    if aggression is not None:
        graph.town_aggression = aggression
    if year_start is None:
        return None
    try:
        return date.fromisoformat(year_start).year
    except ValueError:
        return None


def _load_shopkeeper_customer(conn: sqlite3.Connection, graph: SocialGraph, rng: random.Random) -> None:
    rows = conn.execute(
        """
        SELECT sr.resident_id, r.id AS staff_id, sr.customer_score, sr.purchase_count, sr.is_primary
        FROM shop_relationships sr
        JOIN residents r ON r.workplace_building_id = sr.shop_building_id
        WHERE sr.resident_id != r.id
        ORDER BY sr.resident_id, r.id
        """
    ).fetchall()
    # skip dangling edges: either endpoint may be absent (dead, or a data gap)
    rows = [row for row in rows if row[0] in graph.nodes and row[1] in graph.nodes]
    if not rows:
        return

    max_customer_score = max(row[2] for row in rows) or 1.0
    max_purchase_count = max(row[3] for row in rows) or 1.0

    for customer_id, staff_id, customer_score, purchase_count, is_primary in rows:
        time = _clamp01(customer_score / max_customer_score)
        services = _clamp01(purchase_count / max_purchase_count)
        intimacy = _clamp01(rng.gauss(0.10, 0.08))
        valence_mean = 0.15 if is_primary else 0.0
        # drawn independently: the customer's opinion of the staff member need not match the reverse
        valence_a_to_b = _clamp_signed(rng.gauss(valence_mean, 0.30))
        valence_b_to_a = _clamp_signed(rng.gauss(valence_mean, 0.30))
        graph.add_edge(
            Edge(
                resident_a=customer_id,
                resident_b=staff_id,
                source_type="shopkeeper_customer",
                fiske_type=FISKE_TAGS["shopkeeper_customer"],
                time=time,
                intimacy=intimacy,
                services=services,
                valence_a_to_b=valence_a_to_b,
                valence_b_to_a=valence_b_to_a,
            )
        )


def import_snapshot(db_path: str, seed: int) -> SocialGraph:
    rng = random.Random(seed)
    graph = SocialGraph()
    # read-only: a snapshot is never written to, and a mistyped path must fail
    # loudly instead of silently creating an empty .db
    conn = sqlite3.connect(f"file:{Path(db_path).resolve().as_posix()}?mode=ro", uri=True)
    try:
        reference_year = _load_town_state(conn, graph)
        _load_residents(conn, graph, rng, reference_year)
        _load_relationships(conn, graph, rng)
        _load_shopkeeper_customer(conn, graph, rng)
    finally:
        conn.close()
    return graph
