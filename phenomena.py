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
        # Transmissions rolled during a day are staged here and only become
        # "infected" in end_of_day, so every edge roll for a given day is made
        # against day-start state (design doc §6.2/§7). Mutating state inline
        # would let someone infected this morning infect others this afternoon.
        self._pending_infections: List[int] = []

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
        if newly_infected in self._pending_infections:
            return []  # already caught it earlier today via another edge
        self._pending_infections.append(newly_infected)
        return [Event(day, self.name, "infected", source, newly_infected, "transmission")]

    def end_of_day(self, graph, state, day: int) -> List[Event]:
        just_infected = set(self._pending_infections)
        for resident_id in self._pending_infections:
            state[resident_id] = {"status": "infected", "days_left": self.infectious_days}
        self._pending_infections.clear()

        events: List[Event] = []
        for resident_id, resident_state in state.items():
            if resident_state["status"] != "infected" or resident_id in just_infected:
                continue
            # the dead don't recover (violence may have removed them)
            if not graph.nodes[resident_id].alive:
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
