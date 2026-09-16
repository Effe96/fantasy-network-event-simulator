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
