import random
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Protocol, Tuple

from graph import FISKE_TAGS


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
    def end_of_day(self, graph, state, day: int, rng: random.Random) -> List[Event]: ...
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

    def __init__(
        self,
        base_rate: float = 0.5,
        infectious_days: int = 7,
        patient_zero: Optional[int] = None,
        case_fatality_rate: float = 0.03,
    ):
        self.base_rate = base_rate
        self.infectious_days = infectious_days
        self.patient_zero = patient_zero
        self.case_fatality_rate = case_fatality_rate
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

    def end_of_day(self, graph, state, day: int, rng: random.Random) -> List[Event]:
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
                fatality_p = min(1.0, self.case_fatality_rate * SES_VULNERABILITY.get(graph.nodes[resident_id].ses, 1.0))
                if rng.random() < fatality_p:
                    resident_state["status"] = "deceased"
                    graph.nodes[resident_id].alive = False
                    events.append(Event(day, self.name, "died", resident_id, resident_id, "died from infection"))
                else:
                    resident_state["status"] = "recovered"
                    events.append(Event(day, self.name, "recovered", resident_id, resident_id, "recovered"))
        return events

    def summarize(self, state) -> Dict[str, int]:
        counts = {"susceptible": 0, "infected": 0, "recovered": 0, "deceased": 0}
        for resident_state in state.values():
            counts[resident_state["status"]] += 1
        return counts


# ponytail: placeholder vulnerability rule (skews toward lower socioeconomic status);
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
        # animosity is directed and need not be mutual; the more hostile side
        # is the one who might snap, so that's what drives the day's odds
        hostility = max(-edge.valence_a_to_b, -edge.valence_b_to_a, 0.0)
        if hostility <= 0:
            return 0.0
        return self.base_rate * hostility * edge.tie_strength

    def _pick_aggressor(self, graph, edge, a: int, b: int, rng: random.Random) -> int:
        # whoever wants to hurt the other more is more likely to be the one who
        # snaps; whoever is more vulnerable is more likely to end up the victim
        # if they do -- so aggression is weighted by hostility toward the *other*
        # side's vulnerability, not by SES alone. A more loyal person restrains
        # themselves even when equally hostile, so their own loyalty dampens
        # their own weight to strike.
        hostility_a_to_b = max(0.0, -edge.valence_from(a))
        hostility_b_to_a = max(0.0, -edge.valence_from(b))
        vulnerability_a = SES_VULNERABILITY.get(graph.nodes[a].ses, 1.0)
        vulnerability_b = SES_VULNERABILITY.get(graph.nodes[b].ses, 1.0)
        weight_a_attacks = hostility_a_to_b * vulnerability_b * (1.0 - graph.nodes[a].loyalty)
        weight_b_attacks = hostility_b_to_a * vulnerability_a * (1.0 - graph.nodes[b].loyalty)
        total = weight_a_attacks + weight_b_attacks
        if total <= 0:
            return a  # edge_probability already requires hostility > 0 somewhere; a fallback only
        return a if rng.random() < weight_a_attacks / total else b

    def apply_effect(self, graph, state, a: int, b: int, day: int, rng: random.Random) -> List[Event]:
        edge = graph.get_edge(a, b)
        culprit = self._pick_aggressor(graph, edge, a, b, rng)
        victim = b if culprit == a else a

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
            new_valence = max(-1.0, edge_to_culprit.valence_from(neighbor_id) - shock)
            edge_to_culprit.set_valence_from(neighbor_id, new_valence)
            events.append(Event(day, self.name, "grief_shock", neighbor_id, culprit, f"valence -{shock:.3f}"))

        return events

    def end_of_day(self, graph, state, day: int, rng: random.Random) -> List[Event]:
        return []

    def summarize(self, state) -> Dict[str, int]:
        alive = sum(1 for resident_state in state.values() if resident_state["alive"])
        return {"alive": alive, "dead": len(state) - alive}


ADULT_MIN_AGE = 18  # matches TownShape's own town_relationships/family.py adulthood threshold
FERTILE_MAX_AGE = 45  # ponytail: placeholder cutoff, tune if it reads oddly


class RomancePhenomenon:
    name = "romance"

    def __init__(self, love_threshold: float = 0.5, marriage_base_rate: float = 0.05, birth_base_rate: float = 0.01):
        self.love_threshold = love_threshold
        self.marriage_base_rate = marriage_base_rate
        self.birth_base_rate = birth_base_rate
        self._marriages = 0
        # ponytail: births are log-only for now -- no Node is created, since every
        # other phenomenon's state dict is fixed at day 0 and doesn't yet tolerate
        # residents added mid-run. Upgrade path: give Phenomenon a default_state
        # hook so a newborn can join contagion/violence too.
        self._births = 0

    def init_state(self, graph) -> Dict[int, Any]:
        # edge_probability has no graph access, only edge + per-resident state, so
        # the static fields it needs (gender, age) are copied in here rather than
        # looked up live -- same reason ContagionPhenomenon keeps its own "status".
        state = {
            resident_id: {"married": False, "gender": node.gender, "age": node.age}
            for resident_id, node in graph.nodes.items()
        }
        for edge in graph.edges.values():
            if edge.source_type == "spouse":
                state[edge.resident_a]["married"] = True
                state[edge.resident_b]["married"] = True
        return state

    @staticmethod
    def _is_adult(person_state) -> bool:
        return person_state["age"] is not None and person_state["age"] >= ADULT_MIN_AGE

    @staticmethod
    def _is_opposite_gender_pair(state_a, state_b) -> bool:
        # v1 only models opposite-gender romance/births, matching every gender
        # value seen in TownShape data so far; known gap, not a deliberate exclusion
        return (
            state_a["gender"] is not None
            and state_b["gender"] is not None
            and state_a["gender"] != state_b["gender"]
        )

    def edge_probability(self, edge, state_a, state_b, day: int) -> float:
        if edge.source_type == "spouse":
            if not self._is_opposite_gender_pair(state_a, state_b):
                return 0.0
            if not (self._is_adult(state_a) and self._is_adult(state_b)):
                return 0.0
            if state_a["age"] > FERTILE_MAX_AGE or state_b["age"] > FERTILE_MAX_AGE:
                return 0.0
            return self.birth_base_rate * edge.tie_strength

        if edge.source_type in ("parent", "sibling"):
            return 0.0  # no romance within family
        if state_a["married"] or state_b["married"]:
            return 0.0  # monogamy: v1 has no divorce/remarriage
        if not self._is_opposite_gender_pair(state_a, state_b):
            return 0.0
        if not (self._is_adult(state_a) and self._is_adult(state_b)):
            return 0.0
        # both sides must feel it -- an unrequited crush never leads to marriage
        mutual_affinity = min(edge.valence_a_to_b, edge.valence_b_to_a)
        if mutual_affinity <= self.love_threshold:
            return 0.0
        return self.marriage_base_rate * (mutual_affinity - self.love_threshold) * edge.tie_strength

    def apply_effect(self, graph, state, a: int, b: int, day: int, rng: random.Random) -> List[Event]:
        edge = graph.get_edge(a, b)
        if edge.source_type == "spouse":
            self._births += 1
            return [Event(day, self.name, "born", a, b, "had a child (not yet a tracked resident)")]

        edge.source_type = "spouse"
        edge.fiske_type = FISKE_TAGS["spouse"]
        state[a]["married"] = True
        state[b]["married"] = True
        self._marriages += 1
        return [Event(day, self.name, "married", a, b, "fell in love and married")]

    def end_of_day(self, graph, state, day: int, rng: random.Random) -> List[Event]:
        return []

    def summarize(self, state) -> Dict[str, int]:
        return {
            "married_residents": sum(1 for resident_state in state.values() if resident_state["married"]),
            "births": self._births,
        }


AUTHORITY_ROLES = ("guard", "noble")


class RiotPhenomenon:
    """A town-wide event, not a per-edge one: all the real logic runs once a day
    in end_of_day. edge_probability/apply_effect are never meaningfully used --
    that's cheaper than adding a town-wide hook to the Phenomenon protocol for
    the one phenomenon that needs it.

    A riot now persists across days as explicit state (self._active_riot)
    instead of resolving atomically in a single end_of_day call: guards take
    casualties day by day until enough of them break and flee, then nobles are
    targeted day by day -- most-hated first -- until a "riot bar" (the mob's
    remaining bloodlust, sized off how many people showed up) runs out or no
    nobles are left. That bar, not an arbitrary one-shot roll, is what actually
    stops the riot."""

    name = "riot"

    def __init__(
        self,
        unrest_threshold: float = 0.25,
        riot_base_rate: float = 0.02,
        join_rate: float = 0.5,
        min_participants: int = 3,
        guard_lethality: float = 0.3,
        noble_lethality: float = 0.1,
        retreat_threshold: float = 0.3,
        riot_bar_per_participant: float = 0.1,
        death_cap: float = 0.9,
    ):
        self.unrest_threshold = unrest_threshold
        self.riot_base_rate = riot_base_rate
        self.join_rate = join_rate
        self.min_participants = min_participants
        self.guard_lethality = guard_lethality
        self.noble_lethality = noble_lethality
        # base fraction of the initial guard count that needs to die before they
        # retreat -- scaled per-riot by the guards' own average loyalty (see
        # _start_riot): a more loyal force holds far longer than this alone
        # suggests, a less loyal one breaks far sooner
        self.retreat_threshold = retreat_threshold
        # ponytail: how many noble kills a riot's fervor is "worth," per rioter;
        # tune this if riots feel too bloody or fizzle out too fast
        self.riot_bar_per_participant = riot_bar_per_participant
        self.death_cap = death_cap
        # town-wide bookkeeping lives on self, not the per-resident state dict --
        # same reason ContagionPhenomenon keeps _pending_infections on self
        self._adjacency: List[Tuple[int, int]] = []
        self._active_riot: Optional[Dict[str, Any]] = None
        self._riots = 0
        self._guard_deaths = 0
        self._noble_deaths = 0

    def init_state(self, graph) -> Dict[int, Any]:
        # civilian <-> authority (guard or noble) edges, precomputed once: roles
        # don't change during the run, so re-deriving this from all edges daily
        # would be wasted work on a real town's ~75k edges
        for edge in graph.edges.values():
            role_a, role_b = graph.nodes[edge.resident_a].role, graph.nodes[edge.resident_b].role
            if role_a == "civilian" and role_b in AUTHORITY_ROLES:
                self._adjacency.append((edge.resident_a, edge.resident_b))
            elif role_b == "civilian" and role_a in AUTHORITY_ROLES:
                self._adjacency.append((edge.resident_b, edge.resident_a))
        # the engine indexes state[resident_id] for every phenomenon on every
        # edge regardless of what edge_probability does with it -- this dict's
        # values are never read, only its keys need to exist
        return {resident_id: None for resident_id in graph.nodes}

    def edge_probability(self, edge, state_a, state_b, day: int) -> float:
        return 0.0  # riots never fire through the per-edge path -- see end_of_day

    def apply_effect(self, graph, state, a: int, b: int, day: int, rng: random.Random) -> List[Event]:
        return []

    @staticmethod
    def _hatred_toward(graph, resident_id: int) -> float:
        # total hostile valence directed at this resident from everyone they
        # know, not just riot participants -- "how much they are hated overall"
        total = 0.0
        for neighbor_id in graph.neighbors(resident_id):
            if not graph.nodes[neighbor_id].alive:
                continue
            edge = graph.get_edge(resident_id, neighbor_id)
            total += max(0.0, -edge.valence_from(neighbor_id))
        return total

    def _start_riot(self, graph, day: int, rng: random.Random) -> List[Event]:
        hostile_links = [
            (civ, member) for civ, member in self._adjacency
            if graph.nodes[civ].alive and graph.nodes[member].alive
            and graph.get_edge(civ, member).valence_from(civ) < 0
        ]
        if not hostile_links:
            return []
        avg_hostility = sum(-graph.get_edge(civ, member).valence_from(civ) for civ, member in hostile_links) / len(
            hostile_links
        )
        if avg_hostility <= self.unrest_threshold:
            return []
        if rng.random() >= self.riot_base_rate * (avg_hostility - self.unrest_threshold):
            return []

        # a civilian's worst grievance against any single authority figure is
        # what might drag them into the streets
        worst_grievance: Dict[int, float] = {}
        for civ, member in hostile_links:
            hostility = -graph.get_edge(civ, member).valence_from(civ)
            worst_grievance[civ] = max(worst_grievance.get(civ, 0.0), hostility)

        participants = [
            civ for civ, hostility in worst_grievance.items()
            if rng.random() < min(1.0, self.join_rate * hostility * (1.0 - graph.nodes[civ].loyalty))
        ]
        if len(participants) < self.min_participants:
            return []  # not enough people banded together for it to count as a riot

        guards = [rid for rid, node in graph.nodes.items() if node.alive and node.role == "guard"]
        # a more loyal garrison holds much longer than an unloyal one -- 0.5 is
        # the trait's own default mean, so an average-loyalty force reproduces
        # the plain retreat_threshold unchanged
        avg_guard_loyalty = sum(graph.nodes[g].loyalty for g in guards) / len(guards) if guards else 0.5
        effective_retreat_threshold = self.retreat_threshold * (0.5 + avg_guard_loyalty)

        self._riots += 1
        self._active_riot = {
            "participants": participants,
            "guards_remaining": guards,
            "initial_guard_count": len(guards),
            "guard_deaths": 0,
            "retreated": len(guards) == 0,
            "retreat_threshold": effective_retreat_threshold,
            "riot_bar": max(1, round(self.riot_bar_per_participant * len(participants))),
        }
        return [Event(day, self.name, "riot", participants[0], participants[0], f"{len(participants)} rioters joined")]

    def _advance_riot(self, graph, day: int, rng: random.Random) -> List[Event]:
        riot = self._active_riot
        events: List[Event] = []
        participants = [p for p in riot["participants"] if graph.nodes[p].alive]
        if not participants:
            self._active_riot = None
            return events

        if not riot["retreated"]:
            # guards are the front line -- they take the mob's violence first,
            # a fresh independent roll per guard per day, until enough of them
            # fall and the rest break and flee
            still_standing = [g for g in riot["guards_remaining"] if graph.nodes[g].alive]
            riot["guards_remaining"] = still_standing
            p_death_guard = min(
                self.death_cap, self.guard_lethality * len(participants) / max(1, riot["initial_guard_count"])
            )
            for guard_id in list(still_standing):
                if riot["retreated"]:
                    break
                if rng.random() < p_death_guard:
                    graph.nodes[guard_id].alive = False
                    riot["guard_deaths"] += 1
                    self._guard_deaths += 1
                    riot["guards_remaining"].remove(guard_id)
                    events.append(Event(day, self.name, "guard_killed", guard_id, guard_id, "killed in the riot"))
                    if riot["guard_deaths"] / riot["initial_guard_count"] >= riot["retreat_threshold"]:
                        riot["retreated"] = True
                        events.append(
                            Event(day, self.name, "guards_retreat", guard_id, guard_id, "guards break and flee")
                        )
            if not riot["retreated"] and not riot["guards_remaining"]:
                riot["retreated"] = True  # every guard fell without technically crossing the threshold

        else:
            # nobles are shielded until the guards break -- then personal hatred,
            # not proximity to this riot, decides who among them gets targeted,
            # most-hated first, until the mob's bloodlust (riot_bar) is spent
            nobles = sorted(
                (rid for rid, node in graph.nodes.items() if node.alive and node.role == "noble"),
                key=lambda rid: -self._hatred_toward(graph, rid),
            )
            if not nobles:
                self._active_riot = None
                return events
            hatred = {noble_id: self._hatred_toward(graph, noble_id) for noble_id in nobles}
            avg_hatred = sum(hatred.values()) / len(nobles)
            if avg_hatred > 0:
                for noble_id in nobles:
                    if riot["riot_bar"] <= 0:
                        break
                    relative_hatred = hatred[noble_id] / avg_hatred
                    p_death_noble = min(
                        self.death_cap,
                        self.noble_lethality * len(participants) / len(nobles) * relative_hatred,
                    )
                    if rng.random() < p_death_noble:
                        graph.nodes[noble_id].alive = False
                        self._noble_deaths += 1
                        riot["riot_bar"] -= 1
                        events.append(Event(day, self.name, "noble_killed", noble_id, noble_id, "killed in the riot"))

            if riot["riot_bar"] <= 0:
                events.append(
                    Event(day, self.name, "riot_ends", participants[0], participants[0], "the mob disperses, sated")
                )
                self._active_riot = None

        return events

    def end_of_day(self, graph, state, day: int, rng: random.Random) -> List[Event]:
        if self._active_riot is None:
            return self._start_riot(graph, day, rng)
        return self._advance_riot(graph, day, rng)

    def summarize(self, state) -> Dict[str, int]:
        return {
            "riots": self._riots,
            "riot_guard_deaths": self._guard_deaths,
            "riot_noble_deaths": self._noble_deaths,
        }
