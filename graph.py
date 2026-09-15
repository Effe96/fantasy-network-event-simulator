import random
import sqlite3
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
