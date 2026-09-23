import heapq
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
    # no phenomenon adds ties mid-run, so each tie's place in the order is fixed
    edge_order = list(graph.edges)
    position = {key: index for index, key in enumerate(edge_order)}

    for day in range(1, days + 1):
        for phenomenon in phenomena:
            state = states[phenomenon.name]
            candidates = phenomenon.candidate_edges(graph, state) if hasattr(phenomenon, "candidate_edges") else None
            if candidates is None:
                for edge in list(graph.edges.values()):
                    _roll_edge(graph, phenomenon, state, edge, day, rng, result)
            else:
                # Speed-up (2026-09-23): only ties whose probability can be
                # non-zero. The RNG is drawn only for probability > 0, so
                # visiting the same ties in the same order reproduces a full
                # scan exactly. A phenomenon whose own effects can make a later
                # tie eligible mid-pass (violence's grief) reports it via
                # drain_new_candidates, and it's queued if still ahead.
                heap = sorted({position[key] for key in candidates})
                queued = set(heap)
                drain = getattr(phenomenon, "drain_new_candidates", None)
                while heap:
                    current = heapq.heappop(heap)
                    fired = _roll_edge(graph, phenomenon, state, graph.edges[edge_order[current]], day, rng, result)
                    if fired and drain is not None:
                        for key in drain():
                            later = position[key]
                            if later > current and later not in queued:
                                queued.add(later)
                                heapq.heappush(heap, later)
            result.events.extend(phenomenon.end_of_day(graph, state, day, rng))

        summary = {"day": day}
        for phenomenon in phenomena:
            summary.update(phenomenon.summarize(states[phenomenon.name]))
        # alive/dead is a graph-wide fact (any phenomenon can kill), not a single
        # phenomenon's own bookkeeping -- always wins over a per-phenomenon guess.
        alive_count = sum(1 for node in graph.nodes.values() if node.alive)
        summary["alive"] = alive_count
        summary["dead"] = len(graph.nodes) - alive_count
        result.daily_summaries.append(summary)

    return result


def _roll_edge(graph, phenomenon, state, edge, day, rng, result) -> bool:
    a, b = edge.resident_a, edge.resident_b
    if not (graph.nodes[a].alive and graph.nodes[b].alive):
        return False
    probability = phenomenon.edge_probability(edge, state[a], state[b], day)
    if probability > 0 and rng.random() < probability:
        result.events.extend(phenomenon.apply_effect(graph, state, a, b, day, rng))
        return True
    return False
