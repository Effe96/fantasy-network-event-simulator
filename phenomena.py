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
