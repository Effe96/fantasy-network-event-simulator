import heapq
import random
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

from phenomena import Event, Phenomenon


@dataclass
class SimulationResult:
    daily_summaries: List[Dict[str, int]] = field(default_factory=list)
    events: List[Event] = field(default_factory=list)


def run_simulation(graph, phenomena: List[Phenomenon], days: int, seed: int,
                   on_day_end: Optional[Callable[[int, object, Dict], None]] = None) -> SimulationResult:
    # on_day_end(day, graph, states): read-only hook for diagnostics (drift_check.py)
    rng = random.Random(seed)
    states = {phenomenon.name: phenomenon.init_state(graph) for phenomenon in phenomena}
    result = SimulationResult()
    # every live tie's place in the order ties were added: new ties go at the
    # end, retired ones leave a gap (speed-up 2026-09-30: renumbering all ~80k
    # after every retirement cost more than the ties' own phenomena), so the
    # order always matches graph.edges
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
                # a phenomenon's cached ties can include ties since retired with the dead
                ordered = sorted({position[key] for key in candidates if key in position})
                drain = getattr(phenomenon, "drain_new_candidates", None)
                if drain is None:  # nothing can join mid-pass: walk the list, no heap
                    edges = graph.edges
                    for current in ordered:
                        _roll_edge(graph, phenomenon, state, edges[edge_order[current]], day, rng, result)
                    result.events.extend(phenomenon.end_of_day(graph, state, day, rng))
                    if graph.newcomers or len(graph.edges) > len(position):
                        _register_newcomers(graph, phenomena, states, edge_order, position)
                    continue
                heap = ordered
                queued = set(heap)
                while heap:
                    current = heapq.heappop(heap)
                    fired = _roll_edge(graph, phenomenon, state, graph.edges[edge_order[current]], day, rng, result)
                    if fired and drain is not None:
                        for key in drain():
                            if key not in position:
                                continue
                            later = position[key]
                            if later > current and later not in queued:
                                queued.add(later)
                                heapq.heappush(heap, later)
            result.events.extend(phenomenon.end_of_day(graph, state, day, rng))
            if graph.newcomers or len(graph.edges) > len(position):
                _register_newcomers(graph, phenomena, states, edge_order, position)

        # everyone has now read yesterday's deaths: their ties go to the archive
        if graph.retire_ties_of_dead(before_day=day):
            for key in graph.last_retired_keys:
                del position[key]

        summary = {"day": day}
        for phenomenon in phenomena:
            summary.update(phenomenon.summarize(states[phenomenon.name]))
        # alive/dead is a graph-wide fact (any phenomenon can kill), not a single
        # phenomenon's own bookkeeping -- always wins over a per-phenomenon guess.
        alive_count = graph.alive_count
        summary["alive"] = alive_count
        summary["dead"] = len(graph.nodes) - alive_count
        result.daily_summaries.append(summary)
        if on_day_end is not None:
            on_day_end(day, graph, states)

    return result


def _register_newcomers(graph, phenomena, states, edge_order, position) -> None:
    """Residents added mid-run (graph.add_resident) join every phenomenon's
    state, and their new ties join the fixed tie order, at the end of the
    phenomenon that created them -- so later phenomena that same day, and
    every phenomenon from the next day, see them. Also takes new ties
    between existing residents (an arranged marriage)."""
    while graph.newcomers:
        resident_id = graph.newcomers.pop(0)
        for phenomenon in phenomena:
            if not hasattr(phenomenon, "add_resident"):
                raise TypeError(f"{type(phenomenon).__name__} can't take a resident added mid-run")
            phenomenon.add_resident(graph, states[phenomenon.name], resident_id)
    # new ties are only ever appended to graph.edges (a re-made tie too: its old
    # place was dropped when it was retired), so they are the ones after the
    # last known tie; walk back from the end to find them
    fresh = []
    for key in reversed(graph.edges):
        if key in position:
            break
        fresh.append(key)
    for key in reversed(fresh):
        position[key] = len(edge_order)
        edge_order.append(key)


def _roll_edge(graph, phenomenon, state, edge, day, rng, result) -> bool:
    a, b = edge.resident_a, edge.resident_b
    if not (graph.nodes[a].alive and graph.nodes[b].alive):
        return False
    probability = phenomenon.edge_probability(edge, state[a], state[b], day)
    if probability > 0 and rng.random() < probability:
        result.events.extend(phenomenon.apply_effect(graph, state, a, b, day, rng))
        return True
    return False
