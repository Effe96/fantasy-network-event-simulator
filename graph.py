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
