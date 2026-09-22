import math
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
                    graph.record_death(resident_id, day, "plague")
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


class CommonAilmentsPhenomenon:
    """Common ailments (added 2026-09-21, user feedback): unlike
    `ContagionPhenomenon`'s single rare, severe, patient-zero-driven
    epidemic, a town should also have ordinary sickness running
    continuously all year, alongside it, not instead of it. Two named
    ailments for now (the user's own examples, not exhaustive):

    - **Flu is contagious** -- spreads over edges the same way
      `ContagionPhenomenon` does (same staged-pending-infection discipline,
      so a case caught this morning can't chain further today), plus a
      small daily spontaneous chance (`flu_spontaneous_rate`) of catching
      it from outside the tracked social graph entirely. That spontaneous
      trickle is what lets flu keep circulating all year without ever
      needing a `patient_zero` seed or dying out for good.
    - **Diarrhea is not contagious** -- a plain per-resident daily hazard
      roll, no edges involved at all (`edge_probability` never fires for
      it); getting it doesn't depend on who you know.

    Both scale by poverty on *two* independent axes, reusing
    `SES_VULNERABILITY` the same way other phenomena already do: the odds
    of getting sick at all, and separately, the odds of dying from it once
    sick (kept low by default -- these are common, not catastrophic).
    Recovering grants **temporary** immunity (`flu_immunity_days` /
    `diarrhea_immunity_days`), not permanent like the big epidemic and not
    zero either. Zero immunity was tried first and produced a runaway
    result: on a densely-tied real town (~40-80 edges/resident), a
    same-day-reinfectable population never runs out of susceptible
    neighbors the way the big epidemic's *permanent* immunity eventually
    does, so flu alone produced ~30,000 "cases" in a year (repeat
    infections of the same few hundred people cycling every few days, not
    30,000 different people) and several hundred deaths -- nowhere near
    "common but not catastrophic." A temporary immunity window is what
    lets someone genuinely get the same ailment again later in the year
    (unlike the epidemic model) while still giving each local wave room to
    actually burn out before the same people are reinfected. A resident
    can independently have the big epidemic, flu, and/or diarrhea at once
    -- no cross-phenomenon link exists to prevent that, matching how every
    other phenomenon here stays self-contained.

    Flu is also **seasonal** (user feedback, 2026-09-21): both its
    transmission rate and its spontaneous rate are multiplied by
    `flu_winter_multiplier` during Q4 and Q1 (day-of-year <=91 or >=274).
    Diarrhea has no seasonality -- the user's own framing only asked for
    it on flu."""

    name = "ailments"

    def __init__(
        self,
        flu_transmission_rate: float = 0.0004,
        flu_spontaneous_rate: float = 0.0003,
        flu_duration_days: int = 5,
        flu_immunity_days: int = 90,
        flu_case_fatality_rate: float = 0.005,
        flu_winter_multiplier: float = 3.0,
        diarrhea_spontaneous_rate: float = 0.0015,
        diarrhea_duration_days: int = 3,
        diarrhea_immunity_days: int = 30,
        diarrhea_case_fatality_rate: float = 0.01,
    ):
        self.flu_transmission_rate = flu_transmission_rate
        self.flu_spontaneous_rate = flu_spontaneous_rate
        self.flu_duration_days = flu_duration_days
        self.flu_immunity_days = flu_immunity_days
        self.flu_case_fatality_rate = flu_case_fatality_rate
        # applied to both the spontaneous rate and the per-edge transmission
        # rate during Q4+Q1 (day-of-year < 91 or >= 273) -- flu is seasonal,
        # diarrhea isn't (user feedback, 2026-09-21)
        self.flu_winter_multiplier = flu_winter_multiplier
        self.diarrhea_spontaneous_rate = diarrhea_spontaneous_rate
        self.diarrhea_duration_days = diarrhea_duration_days
        self.diarrhea_immunity_days = diarrhea_immunity_days
        self.diarrhea_case_fatality_rate = diarrhea_case_fatality_rate
        # staged like ContagionPhenomenon's _pending_infections -- a case
        # transmitted this morning shouldn't be infectious again this
        # afternoon against a fresh roll of the same day's edges
        self._pending_flu: List[int] = []
        self._flu_cases = 0
        self._flu_deaths = 0
        self._diarrhea_cases = 0
        self._diarrhea_deaths = 0

    def init_state(self, graph) -> Dict[int, Any]:
        return {
            resident_id: {
                "ses": node.ses,
                "flu": {"status": "healthy", "days_left": 0},
                "diarrhea": {"status": "healthy", "days_left": 0},
            }
            for resident_id, node in graph.nodes.items()
        }

    def _flu_season_factor(self, day: int) -> float:
        # day-of-year (1-indexed) so multi-year runs re-enter winter every year;
        # Q1 = day-of-year 1-91, Q4 = 274-365 -- "last quarter and first quarter"
        day_of_year = ((day - 1) % 365) + 1
        if day_of_year <= 91 or day_of_year >= 274:
            return self.flu_winter_multiplier
        return 1.0

    def edge_probability(self, edge, state_a, state_b, day: int) -> float:
        # diarrhea never fires through the per-edge path -- only flu is contagious.
        # "immune" is a third status (see _resolve_ailment) -- transmission needs
        # exactly one side sick and the other genuinely healthy, not immune
        if {state_a["flu"]["status"], state_b["flu"]["status"]} != {"sick", "healthy"}:
            return 0.0
        return self.flu_transmission_rate * edge.tie_strength * self._flu_season_factor(day)

    def apply_effect(self, graph, state, a: int, b: int, day: int, rng: random.Random) -> List[Event]:
        newly_sick, source = (a, b) if state[a]["flu"]["status"] == "healthy" else (b, a)
        if newly_sick in self._pending_flu:
            return []  # already caught it earlier today via another edge
        self._pending_flu.append(newly_sick)
        return [Event(day, self.name, "flu_transmission", source, newly_sick, "caught the flu")]

    def _resolve_ailment(
        self,
        graph,
        state,
        day: int,
        rng: random.Random,
        ailment: str,
        just_sickened,
        case_fatality_rate: float,
        immunity_days: int,
    ) -> List[Event]:
        events: List[Event] = []
        for resident_id, resident_state in state.items():
            if not graph.nodes[resident_id].alive:
                continue  # the dead don't recover -- another phenomenon may have killed them
            ailment_state = resident_state[ailment]

            if ailment_state["status"] == "immune":
                ailment_state["days_left"] -= 1
                if ailment_state["days_left"] <= 0:
                    ailment_state["status"] = "healthy"  # immunity wore off -- can catch it again
                continue

            if ailment_state["status"] != "sick" or resident_id in just_sickened:
                continue  # a case caught today hasn't started losing days yet
            ailment_state["days_left"] -= 1
            if ailment_state["days_left"] > 0:
                continue
            fatality_p = min(1.0, case_fatality_rate * SES_VULNERABILITY.get(resident_state["ses"], 1.0))
            if rng.random() < fatality_p:
                graph.record_death(resident_id, day, ailment)
                if ailment == "flu":
                    self._flu_deaths += 1
                else:
                    self._diarrhea_deaths += 1
                events.append(Event(day, self.name, f"{ailment}_died", resident_id, resident_id, f"died of {ailment}"))
            else:
                ailment_state["status"] = "immune"
                ailment_state["days_left"] = immunity_days
                events.append(
                    Event(day, self.name, f"{ailment}_recovered", resident_id, resident_id, f"recovered from {ailment}")
                )
        return events

    def end_of_day(self, graph, state, day: int, rng: random.Random) -> List[Event]:
        events: List[Event] = []

        just_flu: set = set(self._pending_flu)
        for resident_id in self._pending_flu:
            state[resident_id]["flu"] = {"status": "sick", "days_left": self.flu_duration_days}
            self._flu_cases += 1
        self._pending_flu.clear()

        # flu's small background trickle -- "caught it outside the tracked
        # social graph" -- is what lets it keep circulating all year without
        # a patient_zero seed or ever fully dying out
        for resident_id, resident_state in state.items():
            if resident_id in just_flu or resident_state["flu"]["status"] != "healthy":
                continue
            if not graph.nodes[resident_id].alive:
                continue
            p = self.flu_spontaneous_rate * SES_VULNERABILITY.get(resident_state["ses"], 1.0) * self._flu_season_factor(day)
            if rng.random() < p:
                resident_state["flu"] = {"status": "sick", "days_left": self.flu_duration_days}
                self._flu_cases += 1
                just_flu.add(resident_id)
                events.append(Event(day, self.name, "flu_spontaneous", resident_id, resident_id, "caught the flu"))

        just_diarrhea: set = set()
        for resident_id, resident_state in state.items():
            if resident_state["diarrhea"]["status"] != "healthy":
                continue
            if not graph.nodes[resident_id].alive:
                continue
            p = self.diarrhea_spontaneous_rate * SES_VULNERABILITY.get(resident_state["ses"], 1.0)
            if rng.random() < p:
                resident_state["diarrhea"] = {"status": "sick", "days_left": self.diarrhea_duration_days}
                self._diarrhea_cases += 1
                just_diarrhea.add(resident_id)
                events.append(Event(day, self.name, "diarrhea_onset", resident_id, resident_id, "came down with diarrhea"))

        events.extend(
            self._resolve_ailment(
                graph, state, day, rng, "flu", just_flu, self.flu_case_fatality_rate, self.flu_immunity_days
            )
        )
        events.extend(
            self._resolve_ailment(
                graph, state, day, rng, "diarrhea", just_diarrhea, self.diarrhea_case_fatality_rate,
                self.diarrhea_immunity_days,
            )
        )
        return events

    def summarize(self, state) -> Dict[str, int]:
        return {
            "flu_sick": sum(1 for s in state.values() if s["flu"]["status"] == "sick"),
            "flu_cases": self._flu_cases,
            "flu_deaths": self._flu_deaths,
            "diarrhea_sick": sum(1 for s in state.values() if s["diarrhea"]["status"] == "sick"),
            "diarrhea_cases": self._diarrhea_cases,
            "diarrhea_deaths": self._diarrhea_deaths,
        }


class ViolencePhenomenon:
    """Assassination refinement (added 2026-09-21, per
    `Project_Vision/01-network-simulation.md`'s Criminals section): a
    violent attempt is no longer guaranteed to kill. Success reuses the
    same `SES_VULNERABILITY` dict two ways at once -- the victim's own
    value (a poor victim is easier to actually kill, same reasoning
    `_pick_aggressor` already uses) divided by the attacker's value,
    inverted (a rich attacker's resources make success easier, a poor
    attacker's lack of them makes it harder) -- so same-class violence
    stays close to `success_base_rate` while a poor-attacker-vs-rich-
    victim attempt succeeds rarely and the reverse succeeds almost
    always. A failed attempt never kills; the surviving victim's own
    valence toward the culprit drops sharply instead (`discovery_shock`)
    -- they now know exactly who came after them. No grief_shock fires
    on a failure, since nobody died for bystanders to react to.

    Group violence (added 2026-09-21, Criminals' last item per
    `docs/plans.md`): a town-wide check, run once a day in `end_of_day`
    alongside the per-edge solo path above. If enough people who each hate
    the same target above `group_hate_threshold` are *also* tied to each
    other by at least `group_affinity_threshold` mutual affinity (a `band`,
    found by union-find over the haters), they can act together -- a much
    higher success chance than any one of them alone (`success_base_rate`
    boosted by `sqrt(len(band))`). If the band is already large enough to
    qualify as a riot (`riot_phenomenon.min_participants`), it skips the
    group-kill roll entirely and becomes a riot instead, via
    `RiotPhenomenon._begin_riot` -- this is the bottom-up riot trigger
    flagged as "not yet built" in the design doc, reusing the riot state
    machine directly rather than inventing a second one. Only the single
    largest qualifying band acts per day, to keep this rare and avoid a
    victim being processed twice.

    Nobles hire assassins (added 2026-09-22, Nobles' second slice): a noble
    picked as the solo-violence aggressor doesn't swing the blade personally
    -- same success-chance formula (their wealth already buys a skilled
    assassin, nothing new to model there), but a hired hand insulates the
    noble from the personal fallout a witnessed act would carry, so
    `noble_hired_assassin_shock_factor` scales down both `grief_shock`
    (neighbors) and `discovery_shock` (a surviving victim) rather than
    zeroing them -- word still gets around, just less directly than if the
    noble had been seen doing it themselves.

    Mercenary protection (added 2026-09-22, Nobles' third slice, per vision
    doc: "Nobles (and priests) can hire mercenary protection, scaling with
    how much animosity is directed at them, with a sensible cap. More hired
    protection lowers an attacker's success chance."). A daily check in
    `end_of_day` (`_check_mercenary_hiring`), same shape as group violence's
    own town-wide scan: for every noble/priest under `mercenary_cap`, count
    neighbors hostile enough to count as a genuine enemy
    (`mercenary_enemy_threshold`, same cutoff `group_hate_threshold` uses,
    for consistency). Past `mercenary_min_enemies`, a daily hire roll scales
    with *how far* past it they are (`mercenary_hire_rate * excess`, the
    same shape `RiotPhenomenon`'s own trigger uses) -- more targeted nobles
    hire faster, not at a flat rate. A hire (`_mercenary_candidates`) picks
    one `is_ex_soldier` resident not already protecting someone else --
    a direct neighbor if one is available, and only if none are does it
    widen to a neighbor-of-a-neighbor (a real chain of existing ties, never
    a fabricated edge to a stranger this project's edges don't allow). No
    candidate within two hops, no hire. `apply_effect` then multiplies an attacker's
    success chance by `mercenary_protection_factor` once per *living*
    mercenary the victim currently employs (dead ones stop counting, and
    free up that slot for a later hire, without any explicit cleanup).

    Coup mechanic (added 2026-09-22, Nobles' last slice, per vision doc:
    "Rising taxes raise noble animosity toward the governor; past a
    threshold, nobles may hire mercenaries to move against the governor
    and seize power themselves. The governing body's suspicion of an
    in-progress coup grows with the number of mercenaries hired."). Taxes
    doesn't exist yet, so the "rising taxes" driver is deferred -- built
    on whatever noble-to-governor animosity the graph already carries or
    accumulates dynamically, same deferral `_apply_noble_poor_skew` already
    made for tax-driven growth. `graph.governor_id` (see `graph.py`) is
    lazily picked/re-picked by `_ensure_governor` -- the highest-degree
    living noble, since no real TownShape data models a governor at all;
    36 of 39 other nobles already share a direct edge with that pick on
    the reference town, so the "most connected" convention also happens to
    maximize who can actually plot against them.

    `_check_coup`, run once a day: only one coup is ever in progress at a
    time (`_active_coup`, same "one active event" shape `RiotPhenomenon`
    uses for `_active_riot`). With none active, the living noble most
    hostile toward the governor -- if any clears `coup_animosity_threshold`
    over an *existing* edge to them -- rolls `coup_start_rate` to begin
    plotting. Once active, each day rolls `coup_hire_rate` to add one more
    `_mercenary_candidates`-found mercenary (the exact same hire pool
    `_check_mercenary_hiring` draws from -- an ex-soldier hired for a coup
    isn't available for protection elsewhere, and vice versa, since both
    read/write the same `state[id]["hired_by"]`), each hire raising
    `suspicion`. Every day past the first hire, `coup_detection_rate *
    suspicion` is the day's chance the plot is discovered outright -- more
    mercenaries hired means more daily risk, not a hard cap, so even a
    fully-staffed plot always has *some* chance of going undetected.
    Reaching `coup_mercenary_cap` mercenaries (if not already caught)
    triggers the attempt itself: `coup_success_base_rate * (1 +
    len(mercenaries))`, then reduced by the governor's own *living*
    protection mercenaries via the exact same `mercenary_protection_factor`
    defense formula `apply_effect` uses -- the two mechanics pay off
    together, a well-protected governor is genuinely harder to depose.
    Success kills the governor and hands `graph.governor_id` to the
    plotter; failure (whether by the attempt or by detection) kills the
    plotter instead -- armed insurrection against the town's ruler is not
    a survivable mistake in either direction, matching how severe the
    vision doc's own framing ("seize power themselves") reads."""

    name = "violence"

    def __init__(
        self,
        base_rate: float = 0.01,
        grief_shock: float = 0.15,
        success_base_rate: float = 0.85,
        discovery_shock: float = 0.5,
        riot_phenomenon: Optional["RiotPhenomenon"] = None,
        group_hate_threshold: float = 0.7,
        group_affinity_threshold: float = 0.3,
        min_group_size: int = 2,
        group_action_rate: float = 0.1,
        noble_hired_assassin_shock_factor: float = 0.5,
        mercenary_enemy_threshold: float = 0.7,
        mercenary_min_enemies: int = 3,
        mercenary_hire_rate: float = 0.05,
        mercenary_cap: int = 3,
        mercenary_protection_factor: float = 0.8,
        coup_animosity_threshold: float = 0.5,
        coup_start_rate: float = 0.05,
        coup_hire_rate: float = 0.2,
        coup_mercenary_cap: int = 3,
        coup_suspicion_per_mercenary: float = 0.15,
        coup_detection_rate: float = 0.1,
        coup_success_base_rate: float = 0.25,
    ):
        self.base_rate = base_rate
        self.grief_shock = grief_shock
        self.success_base_rate = success_base_rate
        self.discovery_shock = discovery_shock
        self.riot_phenomenon = riot_phenomenon
        self.noble_hired_assassin_shock_factor = noble_hired_assassin_shock_factor
        self._hired_assassinations = 0
        self.mercenary_enemy_threshold = mercenary_enemy_threshold
        self.mercenary_min_enemies = mercenary_min_enemies
        self.mercenary_hire_rate = mercenary_hire_rate
        self.mercenary_cap = mercenary_cap
        self.mercenary_protection_factor = mercenary_protection_factor
        self.group_hate_threshold = group_hate_threshold
        self.group_affinity_threshold = group_affinity_threshold
        self.min_group_size = min_group_size
        # a qualifying band existing doesn't mean it acts *today* -- same idea
        # as RiotPhenomenon's own riot_base_rate roll on top of its unrest
        # threshold. A first version had neither this roll nor thresholds
        # this strict: at group_hate_threshold=0.4 (a first-guess "meaningful
        # hostility" number), 15,248 directed edges already cross it on day 1
        # from baseline relationship-valence noise alone, no events ever
        # having fired, and some resulting bands reached 65 people -- so
        # group violence fired 345 times in a year, almost all escalating
        # straight into a riot. Fixed with both a stricter threshold pair
        # (0.7/0.3, where day-1 bands cap out at size 3) and this rate --
        # together they reproduce the pre-existing ~1/year organic riot rate
        # plus a handful of group-triggered ones on top, not 345. See
        # docs/decisions.md's 2026-09-21 entry.
        self.group_action_rate = group_action_rate
        self._group_kills = 0
        self.coup_animosity_threshold = coup_animosity_threshold
        self.coup_start_rate = coup_start_rate
        self.coup_hire_rate = coup_hire_rate
        self.coup_mercenary_cap = coup_mercenary_cap
        self.coup_suspicion_per_mercenary = coup_suspicion_per_mercenary
        self.coup_detection_rate = coup_detection_rate
        self.coup_success_base_rate = coup_success_base_rate
        self._active_coup: Optional[Dict[str, Any]] = None
        self._coups_attempted = 0
        self._coups_succeeded = 0
        self._coup_mercenaries_hired = 0

    def init_state(self, graph) -> Dict[int, Any]:
        # "mercenaries" (only meaningful for a noble/priest) and "hired_by"
        # (only meaningful for an ex-soldier) sit on every resident's state
        # dict either way, same uniform shape "alive" already uses
        return {resident_id: {"alive": True, "mercenaries": [], "hired_by": None} for resident_id in graph.nodes}

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
        hired = graph.nodes[culprit].is_noble
        shock_factor = self.noble_hired_assassin_shock_factor if hired else 1.0

        victim_vulnerability = SES_VULNERABILITY.get(graph.nodes[victim].ses, 1.0)
        attacker_vulnerability = SES_VULNERABILITY.get(graph.nodes[culprit].ses, 1.0)
        success_chance = min(1.0, self.success_base_rate * victim_vulnerability / attacker_vulnerability)
        living_mercenaries = sum(1 for m in state[victim]["mercenaries"] if graph.nodes[m].alive)
        success_chance *= self.mercenary_protection_factor ** living_mercenaries

        if rng.random() >= success_chance:
            shock = self.discovery_shock * shock_factor
            edge.set_valence_from(victim, max(-1.0, edge.valence_from(victim) - shock))
            kind = "hired_assassin_failed" if hired else "failed_attempt"
            return [
                Event(day, self.name, kind, culprit, victim,
                      f"survived -- victim's valence -{shock:.2f}")
            ]

        state[victim]["alive"] = False
        graph.record_death(victim, day, "violence", killed_by=culprit)
        if hired:
            self._hired_assassinations += 1

        kind = "hired_assassination" if hired else "violence"
        events = [Event(day, self.name, kind, culprit, victim, "escalated conflict")]

        for neighbor_id in graph.neighbors(victim):
            if neighbor_id == culprit:
                continue
            edge_to_culprit = graph.get_edge(neighbor_id, culprit)
            if edge_to_culprit is None:
                continue
            edge_to_victim = graph.get_edge(neighbor_id, victim)
            shock = self.grief_shock * edge_to_victim.tie_strength * shock_factor
            new_valence = max(-1.0, edge_to_culprit.valence_from(neighbor_id) - shock)
            edge_to_culprit.set_valence_from(neighbor_id, new_valence)
            events.append(Event(day, self.name, "grief_shock", neighbor_id, culprit, f"valence -{shock:.3f}"))

        return events

    def end_of_day(self, graph, state, day: int, rng: random.Random) -> List[Event]:
        return (
            self._check_group_violence(graph, state, day, rng)
            + self._check_mercenary_hiring(graph, state, day, rng)
            + self._check_coup(graph, state, day, rng)
        )

    def _ensure_governor(self, graph, rng: random.Random) -> None:
        if graph.governor_id is not None and graph.nodes[graph.governor_id].alive:
            return
        living_nobles = [n for n in graph.nodes.values() if n.alive and n.is_noble]
        if not living_nobles:
            graph.governor_id = None
            return
        top_degree = max(len(graph.neighbors(n.resident_id)) for n in living_nobles)
        candidates = [n.resident_id for n in living_nobles if len(graph.neighbors(n.resident_id)) == top_degree]
        graph.governor_id = rng.choice(candidates)

    def _check_coup(self, graph, state, day: int, rng: random.Random) -> List[Event]:
        self._ensure_governor(graph, rng)
        if graph.governor_id is None:
            return []

        if self._active_coup is not None:
            return self._advance_coup(graph, state, day, rng)

        governor_id = graph.governor_id
        worst_animosity = 0.0
        plotter_id = None
        for resident_id, node in graph.nodes.items():
            if not node.alive or not node.is_noble or resident_id == governor_id:
                continue
            edge = graph.get_edge(resident_id, governor_id)
            if edge is None:
                continue
            animosity = -edge.valence_from(resident_id)
            if animosity > worst_animosity:
                worst_animosity = animosity
                plotter_id = resident_id
        if plotter_id is None or worst_animosity < self.coup_animosity_threshold:
            return []
        if rng.random() >= self.coup_start_rate:
            return []

        self._active_coup = {"plotter": plotter_id, "mercenaries": [], "suspicion": 0.0}
        return [Event(day, self.name, "coup_begins", plotter_id, governor_id,
                      f"animosity {worst_animosity:.2f} toward the governor")]

    def _advance_coup(self, graph, state, day: int, rng: random.Random) -> List[Event]:
        coup = self._active_coup
        plotter_id = coup["plotter"]
        if not graph.nodes[plotter_id].alive:
            self._active_coup = None
            return [Event(day, self.name, "coup_abandoned", plotter_id, graph.governor_id, "plotter died")]

        events: List[Event] = []
        if rng.random() < self.coup_hire_rate:
            candidates = self._mercenary_candidates(graph, state, plotter_id)
            if candidates:
                mercenary_id = rng.choice(candidates)
                coup["mercenaries"].append(mercenary_id)
                coup["suspicion"] += self.coup_suspicion_per_mercenary
                state[mercenary_id]["hired_by"] = plotter_id
                self._coup_mercenaries_hired += 1
                events.append(Event(day, self.name, "coup_mercenary_hired", plotter_id, mercenary_id,
                                     f"suspicion now {coup['suspicion']:.2f}"))

        if coup["suspicion"] > 0 and rng.random() < self.coup_detection_rate * coup["suspicion"]:
            self._active_coup = None
            graph.record_death(plotter_id, day, "execution")
            self._coups_attempted += 1
            events.append(Event(day, self.name, "coup_discovered", plotter_id, graph.governor_id,
                                 "plot uncovered before it could strike"))
            return events

        living_mercenaries = [m for m in coup["mercenaries"] if graph.nodes[m].alive]
        if len(living_mercenaries) < self.coup_mercenary_cap:
            return events

        governor_id = graph.governor_id
        success_chance = min(1.0, self.coup_success_base_rate * (1 + len(living_mercenaries)))
        governor_protection = [m for m in state[governor_id]["mercenaries"] if graph.nodes[m].alive]
        success_chance *= self.mercenary_protection_factor ** len(governor_protection)

        self._active_coup = None
        self._coups_attempted += 1
        if rng.random() < success_chance:
            graph.record_death(governor_id, day, "coup", killed_by=plotter_id)
            graph.governor_id = plotter_id
            self._coups_succeeded += 1
            events.append(Event(day, self.name, "coup_succeeds", plotter_id, governor_id,
                                 f"seized power with {len(living_mercenaries)} mercenaries"))
        else:
            graph.record_death(plotter_id, day, "coup", killed_by=governor_id)
            events.append(Event(day, self.name, "coup_fails", plotter_id, governor_id,
                                 f"attempt with {len(living_mercenaries)} mercenaries repelled"))
        return events

    def _check_mercenary_hiring(self, graph, state, day: int, rng: random.Random) -> List[Event]:
        events: List[Event] = []
        for resident_id, node in graph.nodes.items():
            if not node.alive or node.role not in ("noble", "priest"):
                continue
            hired = state[resident_id]["mercenaries"]
            living_hired = [m for m in hired if graph.nodes[m].alive]
            if len(living_hired) >= self.mercenary_cap:
                continue
            enemy_count = sum(
                1 for neighbor_id in graph.neighbors(resident_id)
                if graph.nodes[neighbor_id].alive
                and -graph.get_edge(neighbor_id, resident_id).valence_from(neighbor_id) >= self.mercenary_enemy_threshold
            )
            excess = enemy_count - self.mercenary_min_enemies
            if excess <= 0:
                continue
            if rng.random() >= self.mercenary_hire_rate * excess:
                continue
            candidates = self._mercenary_candidates(graph, state, resident_id)
            if not candidates:
                continue
            mercenary_id = rng.choice(candidates)
            hired.append(mercenary_id)
            state[mercenary_id]["hired_by"] = resident_id
            events.append(Event(day, self.name, "mercenary_hired", resident_id, mercenary_id,
                                 f"protection {len(living_hired) + 1}/{self.mercenary_cap}"))
        return events

    def _mercenary_candidates(self, graph, state, resident_id: int) -> List[int]:
        """A noble/priest hires someone they already have a real tie to --
        directly, or a friend of a friend (a connection of a connection,
        never a fabricated edge to a stranger). Direct ties are tried first
        and returned alone if any exist -- reaching out to someone you
        actually know comes before going through an intermediary, and it
        keeps the common case (most nobles already have a direct candidate)
        cheap, saving the wider 2-hop scan for the rarer case where nobody
        direct is available."""

        def available(candidate_id: int) -> bool:
            if not (graph.nodes[candidate_id].alive and graph.nodes[candidate_id].is_ex_soldier):
                return False
            hired_by = state[candidate_id]["hired_by"]
            return hired_by is None or not graph.nodes[hired_by].alive

        direct = [n for n in graph.neighbors(resident_id) if available(n)]
        if direct:
            return direct

        seen = {resident_id, *graph.neighbors(resident_id)}
        two_hop = []
        for neighbor_id in graph.neighbors(resident_id):
            for candidate_id in graph.neighbors(neighbor_id):
                if candidate_id in seen:
                    continue
                seen.add(candidate_id)
                if available(candidate_id):
                    two_hop.append(candidate_id)
        return two_hop

    def _check_group_violence(self, graph, state, day: int, rng: random.Random) -> List[Event]:
        # one pass over every live edge, same cost as the engine's own
        # per-edge solo-violence pass -- there's no cheaper way to find "who
        # is hated by several different people at once" without scanning
        hostile_toward: Dict[int, List[int]] = {}
        for edge in graph.edges.values():
            a, b = edge.resident_a, edge.resident_b
            if not (graph.nodes[a].alive and graph.nodes[b].alive):
                continue
            if -edge.valence_from(a) >= self.group_hate_threshold:
                hostile_toward.setdefault(b, []).append(a)
            if -edge.valence_from(b) >= self.group_hate_threshold:
                hostile_toward.setdefault(a, []).append(b)

        candidates = sorted(
            (victim for victim, haters in hostile_toward.items() if len(haters) >= self.min_group_size),
            key=lambda victim: -len(hostile_toward[victim]),
        )
        for victim in candidates:
            band = self._find_band(graph, hostile_toward[victim])
            if len(band) < self.min_group_size:
                continue
            if rng.random() >= self.group_action_rate:
                return []  # a band exists, but grudges don't boil over every single day
            return self._resolve_group_violence(graph, state, victim, band, day, rng)
        return []

    def _find_band(self, graph, haters: List[int]) -> List[int]:
        # union-find over the haters: two of them only band together if they
        # also know and like each other (group_affinity_threshold), not just
        # because they happen to share a grudge against the same person
        parent = {hater: hater for hater in haters}

        def find(x: int) -> int:
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        for i in range(len(haters)):
            for j in range(i + 1, len(haters)):
                edge = graph.get_edge(haters[i], haters[j])
                if edge is None:
                    continue
                mutual_affinity = (edge.valence_from(haters[i]) + edge.valence_from(haters[j])) / 2
                if mutual_affinity >= self.group_affinity_threshold:
                    root_i, root_j = find(haters[i]), find(haters[j])
                    if root_i != root_j:
                        parent[root_i] = root_j

        groups: Dict[int, List[int]] = {}
        for hater in haters:
            groups.setdefault(find(hater), []).append(hater)
        return max(groups.values(), key=len)

    def _resolve_group_violence(
        self, graph, state, victim: int, band: List[int], day: int, rng: random.Random
    ) -> List[Event]:
        if (
            self.riot_phenomenon is not None
            and self.riot_phenomenon._active_riot is None
            and len(band) >= self.riot_phenomenon.min_participants
        ):
            avg_band_hostility = sum(-graph.get_edge(h, victim).valence_from(h) for h in band) / len(band)
            events = [
                Event(day, self.name, "group_escalates_to_riot", band[0], victim,
                      f"{len(band)} people banded together against {victim}, spilling into a riot")
            ]
            events.extend(self.riot_phenomenon._begin_riot(graph, day, band, avg_band_hostility))
            return events

        # the band's own worst hater is the "ringleader" for bookkeeping
        # (event attribution, grief_shock target) -- the others still get a
        # discovery_shock hit on failure and count toward the success roll
        ringleader = max(band, key=lambda h: -graph.get_edge(h, victim).valence_from(h))
        victim_vulnerability = SES_VULNERABILITY.get(graph.nodes[victim].ses, 1.0)
        avg_attacker_vulnerability = sum(SES_VULNERABILITY.get(graph.nodes[h].ses, 1.0) for h in band) / len(band)
        success_chance = min(
            1.0,
            self.success_base_rate * victim_vulnerability / avg_attacker_vulnerability * math.sqrt(len(band)),
        )

        if rng.random() >= success_chance:
            for hater in band:
                edge = graph.get_edge(hater, victim)
                edge.set_valence_from(victim, max(-1.0, edge.valence_from(victim) - self.discovery_shock))
            return [
                Event(day, self.name, "group_failed_attempt", ringleader, victim,
                      f"{len(band)}-strong band failed -- victim's valence dropped toward all of them")
            ]

        state[victim]["alive"] = False
        graph.record_death(victim, day, "violence", killed_by=ringleader)
        self._group_kills += 1
        events = [Event(day, self.name, "group_violence", ringleader, victim, f"killed by a {len(band)}-strong band")]

        for neighbor_id in graph.neighbors(victim):
            if neighbor_id in band:
                continue
            edge_to_ringleader = graph.get_edge(neighbor_id, ringleader)
            if edge_to_ringleader is None:
                continue
            edge_to_victim = graph.get_edge(neighbor_id, victim)
            shock = self.grief_shock * edge_to_victim.tie_strength
            new_valence = max(-1.0, edge_to_ringleader.valence_from(neighbor_id) - shock)
            edge_to_ringleader.set_valence_from(neighbor_id, new_valence)
            events.append(Event(day, self.name, "grief_shock", neighbor_id, ringleader, f"valence -{shock:.3f}"))

        return events

    def summarize(self, state) -> Dict[str, int]:
        alive = sum(1 for resident_state in state.values() if resident_state["alive"])
        mercenaries_hired = sum(len(resident_state["mercenaries"]) for resident_state in state.values())
        return {
            "alive": alive,
            "dead": len(state) - alive,
            "group_kills": self._group_kills,
            "hired_assassinations": self._hired_assassinations,
            "mercenaries_hired": mercenaries_hired,
            "coups_attempted": self._coups_attempted,
            "coups_succeeded": self._coups_succeeded,
            "coup_mercenaries_hired": self._coup_mercenaries_hired,
        }


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
    instead of resolving atomically in a single end_of_day call: guards and
    rioters trade casualties day by day (guards are armed and trained, so
    they die at a lower rate than the rioters they fight) until one side
    breaks -- either the guards retreat (scaled by their own average loyalty)
    and nobles become exposed, or the rioters themselves rout (scaled by how
    angry the mob actually was) and the riot ends there, guards never having
    broken. Only once guards have retreated are nobles targeted, most-hated
    first, until a "riot bar" (the mob's remaining bloodlust, sized off how
    many people showed up) runs out or no nobles are left."""

    name = "riot"

    def __init__(
        self,
        unrest_threshold: float = 0.15,
        riot_base_rate: float = 0.03,
        join_rate: float = 0.5,
        min_participants: int = 3,
        guard_lethality: float = 0.2,
        rioter_lethality: float = 0.6,
        noble_lethality: float = 0.1,
        retreat_threshold: float = 0.3,
        rioter_retreat_threshold: float = 0.3,
        riot_bar_per_participant: float = 0.1,
        death_cap: float = 0.9,
    ):
        self.unrest_threshold = unrest_threshold
        self.riot_base_rate = riot_base_rate
        self.join_rate = join_rate
        self.min_participants = min_participants
        self.guard_lethality = guard_lethality
        # armed and trained: rioters die faster fighting guards than guards die
        # fighting rioters. Per-day totals scale with sqrt(participants *
        # guards) on BOTH sides (see _advance_riot), which makes the
        # guard:rioter casualty *ratio* exactly guard_lethality:rioter_lethality
        # regardless of mob size -- an earlier linear-ratio version let a
        # large mob (more common than not, since the mob is drawn from the
        # whole town but the guard corps is small and fixed) swamp this
        # 3:1 intent entirely; confirmed empirically (30-seed aggregate: 649
        # guard deaths vs 539 rioter deaths, guards dying *more*) before
        # retuning, see docs/decisions.md's 2026-09-21 entry
        self.rioter_lethality = rioter_lethality
        self.noble_lethality = noble_lethality
        # base fraction of the initial guard count that needs to die before they
        # retreat -- scaled per-riot by the guards' own average loyalty (see
        # _start_riot): a more loyal force holds far longer than this alone
        # suggests, a less loyal one breaks far sooner
        self.retreat_threshold = retreat_threshold
        # same idea for the mob itself, scaled by how angry it was to begin
        # with: an enraged mob absorbs more losses before it routs than a
        # lukewarm one
        self.rioter_retreat_threshold = rioter_retreat_threshold
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
        self._rioter_deaths = 0

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

        # same shape for the mob: how angry it was joining (its own worst
        # grievances, not a class-wide average) decides how much it can take
        # before it breaks and runs
        avg_participant_hostility = sum(worst_grievance[p] for p in participants) / len(participants)
        return self._begin_riot(graph, day, participants, avg_participant_hostility)

    def _begin_riot(
        self, graph, day: int, participants: List[int], avg_participant_hostility: float
    ) -> List[Event]:
        """The actual riot-state-creation tail, factored out of `_start_riot` so
        a pre-formed band from `ViolencePhenomenon`'s group-violence mechanic can
        become a riot directly -- reusing this same state machine (per
        `docs/plans.md`) rather than inventing a second riot concept.
        `avg_participant_hostility` is the caller's own measure of how angry the
        band was (organic riots use each participant's worst grievance toward an
        authority figure; group violence uses their hostility toward the shared
        target instead), since it feeds the mob's retreat threshold below."""
        guards = [rid for rid, node in graph.nodes.items() if node.alive and node.role == "guard"]
        # a more loyal garrison holds much longer than an unloyal one -- 0.5 is
        # the trait's own default mean, so an average-loyalty force reproduces
        # the plain retreat_threshold unchanged
        avg_guard_loyalty = sum(graph.nodes[g].loyalty for g in guards) / len(guards) if guards else 0.5
        effective_guard_retreat_threshold = self.retreat_threshold * (0.5 + avg_guard_loyalty)
        effective_rioter_retreat_threshold = self.rioter_retreat_threshold * (0.5 + avg_participant_hostility)

        self._riots += 1
        self._active_riot = {
            "participants": participants,
            "initial_participant_count": len(participants),
            "rioter_deaths": 0,
            "rioter_retreat_threshold": effective_rioter_retreat_threshold,
            "guards_remaining": guards,
            "initial_guard_count": len(guards),
            "guard_deaths": 0,
            "guards_retreated": len(guards) == 0,
            "guard_retreat_threshold": effective_guard_retreat_threshold,
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

        if not riot["guards_retreated"]:
            # guards and rioters trade blows simultaneously this day, both
            # using today's starting counts -- not sequential with an early
            # exit, so the mob still takes fire even on the day guards happen
            # to break.
            #
            # Per-individual death chance scales with sqrt(opposing side's
            # headcount / own side's headcount), not the raw ratio: total
            # expected deaths on each side then reduce to
            # lethality * sqrt(guards * rioters) -- the same size factor for
            # both sides -- so the guard:rioter *casualty ratio* comes out to
            # exactly guard_lethality:rioter_lethality regardless of how the
            # mob's size compares to the guard corps. A plain linear ratio
            # (removed 2026-09-21) let mob size dominate instead: since the
            # mob is drawn from the whole town but the guard corps is small
            # and fixed, a merely-somewhat-larger-than-usual mob was enough
            # to make guards die *more* than rioters despite
            # rioter_lethality > guard_lethality -- confirmed on a 30-seed
            # aggregate (649 guard deaths vs 539 rioter deaths) before this
            # fix, see docs/decisions.md.
            still_standing_guards = [g for g in riot["guards_remaining"] if graph.nodes[g].alive]
            riot["guards_remaining"] = still_standing_guards
            living_guard_count = len(still_standing_guards)
            living_participant_count = len(participants)
            size_factor = math.sqrt(living_participant_count / max(1, living_guard_count))
            p_death_guard = min(self.death_cap, self.guard_lethality * size_factor)
            p_death_rioter = min(self.death_cap, self.rioter_lethality / size_factor)

            for guard_id in list(still_standing_guards):
                if rng.random() < p_death_guard:
                    graph.record_death(guard_id, day, "riot")
                    riot["guard_deaths"] += 1
                    self._guard_deaths += 1
                    riot["guards_remaining"].remove(guard_id)
                    events.append(Event(day, self.name, "guard_killed", guard_id, guard_id, "killed in the riot"))

            for rioter_id in list(participants):
                if rng.random() < p_death_rioter:
                    graph.record_death(rioter_id, day, "riot")
                    riot["rioter_deaths"] += 1
                    self._rioter_deaths += 1
                    events.append(Event(day, self.name, "rioter_killed", rioter_id, rioter_id, "killed in the riot"))

            if not riot["guards_remaining"] or riot["guard_deaths"] / riot["initial_guard_count"] >= riot["guard_retreat_threshold"]:
                riot["guards_retreated"] = True
                events.append(
                    Event(day, self.name, "guards_retreat", participants[0], participants[0], "guards break and flee")
                )
            elif riot["rioter_deaths"] / riot["initial_participant_count"] >= riot["rioter_retreat_threshold"]:
                events.append(
                    Event(day, self.name, "rioters_rout", participants[0], participants[0],
                          "the mob breaks and scatters -- guards hold the line")
                )
                self._active_riot = None

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
                        graph.record_death(noble_id, day, "riot")
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
            "riot_rioter_deaths": self._rioter_deaths,
        }


# ponytail: wealth as a bribe-affordability proxy, since there's no town-wide
# wealth aggregate yet (see the "Wealth inequality" candidate town parameter);
# swap for that once it exists
BRIBE_WEALTH_FACTOR = {"poor": 0.5, "middling": 1.0, "rich": 2.0}
# graph.deaths causes that count as "disease" for priests' curer blame
SICKNESS_CAUSES = {"plague", "flu", "diarrhea"}


class GuardPhenomenon:
    """First scoped slice of Guards: bribery only -- the vision doc's arrest/
    skewed-affinity/patron-protection mechanics all depend on either Criminals
    (doesn't exist) or a cross-phenomenon link to violence's culprits (no event
    bus between phenomena exists), so they're deliberately deferred rather than
    half-built. Bribery is self-contained and is also the first concrete
    instance of the "favor" event type (see the event taxonomy doc): it only
    ever raises affinity, in the guard's own outgoing valence toward the
    briber."""

    name = "guards"

    def __init__(self, bribe_base_rate: float = 0.001, bribe_affinity_gain: float = 0.15):
        self.bribe_base_rate = bribe_base_rate
        self.bribe_affinity_gain = bribe_affinity_gain
        self._bribes = 0

    def init_state(self, graph) -> Dict[int, Any]:
        # edge_probability has no graph access, only edge + per-resident state,
        # so the static fields it needs are copied in here -- same reason
        # RomancePhenomenon copies gender/age instead of looking them up live
        return {
            resident_id: {"role": node.role, "cunning": node.cunning, "ses": node.ses, "loyalty": node.loyalty}
            for resident_id, node in graph.nodes.items()
        }

    def edge_probability(self, edge, state_a, state_b, day: int) -> float:
        roles = {state_a["role"], state_b["role"]}
        if roles != {"civilian", "guard"}:
            return 0.0
        civilian_state = state_a if state_a["role"] == "civilian" else state_b
        guard_state = state_a if state_a["role"] == "guard" else state_b
        wealth_factor = BRIBE_WEALTH_FACTOR.get(civilian_state["ses"], 1.0)
        # a loyal guard refuses far more often than a corruptible one -- at the
        # trait's own default mean (0.5) this halves the plain base rate, so
        # a genuinely high-bribery town has to actually be low-loyalty/
        # high-corruption to reach the old, too-high rate, not just any town
        guard_restraint = 1.0 - guard_state["loyalty"]
        return self.bribe_base_rate * civilian_state["cunning"] * wealth_factor * guard_restraint * edge.tie_strength

    def apply_effect(self, graph, state, a: int, b: int, day: int, rng: random.Random) -> List[Event]:
        edge = graph.get_edge(a, b)
        guard_id = a if state[a]["role"] == "guard" else b
        briber_id = b if guard_id == a else a
        new_valence = min(1.0, edge.valence_from(guard_id) + self.bribe_affinity_gain)
        edge.set_valence_from(guard_id, new_valence)
        self._bribes += 1
        return [Event(day, self.name, "bribed", briber_id, guard_id, f"guard's affinity +{self.bribe_affinity_gain:.2f}")]

    def end_of_day(self, graph, state, day: int, rng: random.Random) -> List[Event]:
        return []

    def summarize(self, state) -> Dict[str, int]:
        return {"bribes": self._bribes}


# ponytail: same placeholder shape as SES_VULNERABILITY -- poverty raises the
# odds someone turns to thievery; tune if a real wealth-inequality dial lands
THIEF_SES_FACTOR = {"poor": 2.0, "middling": 1.0, "rich": 0.3}


class TheftPhenomenon:
    """First scoped slice of Criminals: thief occupation + theft only --
    assassination refinement and group-violence-as-riot-trigger (vision doc's
    other two Criminals items) are deferred to a later slice, same pattern
    GuardPhenomenon used for bribery-only.

    Becoming a thief is a sticky per-resident flag rolled once in
    end_of_day (like Romance's `married` flag) -- poverty raises the daily
    odds of the roll, but once it lands a resident stays a thief; it is not
    a status recomputed from circumstances every day, and not a new `Node`
    field. Nobles never become thieves (vision doc: "Nobles don't steal").

    Theft itself reuses the per-edge Phenomenon shape: it fires on an edge
    with exactly one thief endpoint, scaled by the thief's own cunning and
    the victim's wealth (richer victims are more attractive targets --
    reuses GuardPhenomenon's BRIBE_WEALTH_FACTOR, since both are "how
    tempting is this person's wealth" the same way). A caught thief's
    relationship with the victim, and with any guard they know, both take
    an animosity hit.

    Arrest/deterrence (added 2026-09-21, user feedback: an unbounded thief
    population -- 27% of a town in one year -- isn't realistic since
    nothing ever removed the flag). A caught thief can be arrested
    (clears `is_thief`, so they can go straight or become a thief again
    later) or, in a low-loyalty (corrupt) town, executed instead (removed
    from the graph entirely) -- a harsher, more effective deterrent.
    Every arrest or execution raises a decaying town-wide `_deterrence`
    level that suppresses the become-a-thief roll.

    First version of this (still 2026-09-21) gated arrest on the thief
    having an actual guard *neighbor* in the social graph -- with only
    ~40 guards among 1,911 residents, most caught thieves never had one,
    so only ~10% of catches ever led to a removal and the population kept
    climbing steadily for years (94 -> 221 thieves from year 1 to year 3
    on the reference town, not a plateau at all -- verified with a 3-year
    run before trusting a 1-year trajectory that merely looked flat).
    Corrected to a flat town-wide arrest chance, using the town's average
    guard loyalty (not just a caught thief's own guard neighbors) for the
    execution-vs-arrest split -- law enforcement catching up with you
    doesn't require personally knowing a guard. The local guard-neighbor
    valence hit (guards *you know* getting angrier at you) stays
    proximity-based, separate from whether you actually get arrested.
    Patron protection and the full poverty-severity/corruption-dial
    version of this stay deferred (see the design doc's Economy &
    poverty section)."""

    name = "theft"

    def __init__(
        self,
        become_thief_rate: float = 0.00015,
        theft_base_rate: float = 0.01,
        discovery_chance: float = 0.4,
        caught_animosity: float = 0.3,
        arrest_chance: float = 0.5,
        execution_weight: float = 0.5,
        deterrence_decay: float = 0.985,
        deterrence_weight: float = 0.25,
    ):
        self.become_thief_rate = become_thief_rate
        self.theft_base_rate = theft_base_rate
        self.discovery_chance = discovery_chance
        self.caught_animosity = caught_animosity
        # town-wide, not scaled by the thief's own guard neighbors -- law
        # enforcement catching up with a caught thief doesn't require them
        # to personally know a guard (see class docstring for why this
        # changed from a per-neighbor chance)
        self.arrest_chance = arrest_chance
        # given an arrest happens, a corrupt (low-loyalty) town is more
        # likely to just kill the thief than book them -- 0.5 is the trait's
        # own default mean, so an average-loyalty town only executes about
        # a quarter of its arrests
        self.execution_weight = execution_weight
        self.deterrence_decay = deterrence_decay
        self.deterrence_weight = deterrence_weight
        self._thefts = 0
        self._caught = 0
        self._arrests = 0
        self._executions = 0
        # town-wide, decaying "how much deterrence is in the air right now"
        # -- same reason RiotPhenomenon keeps its own bookkeeping on self
        # rather than in the per-resident state dict
        self._deterrence = 0.0
        # precomputed once at init (guard roles/loyalty are static) -- the
        # execution-vs-arrest split reads the town's law enforcement as a
        # whole, not just the individual guards a given thief happens to
        # know
        self._avg_guard_loyalty = 0.5

    def init_state(self, graph) -> Dict[int, Any]:
        guard_loyalties = [node.loyalty for node in graph.nodes.values() if node.role == "guard"]
        if guard_loyalties:
            self._avg_guard_loyalty = sum(guard_loyalties) / len(guard_loyalties)
        return {
            resident_id: {"role": node.role, "ses": node.ses, "cunning": node.cunning, "is_thief": False}
            for resident_id, node in graph.nodes.items()
        }

    def edge_probability(self, edge, state_a, state_b, day: int) -> float:
        if state_a["is_thief"] == state_b["is_thief"]:
            return 0.0  # exactly one thief needed on the edge -- neither, or both, doesn't fire
        thief_state, victim_state = (state_a, state_b) if state_a["is_thief"] else (state_b, state_a)
        wealth_factor = BRIBE_WEALTH_FACTOR.get(victim_state["ses"], 1.0)
        return self.theft_base_rate * thief_state["cunning"] * wealth_factor * edge.tie_strength

    def apply_effect(self, graph, state, a: int, b: int, day: int, rng: random.Random) -> List[Event]:
        thief_id, victim_id = (a, b) if state[a]["is_thief"] else (b, a)
        self._thefts += 1
        events = [Event(day, self.name, "theft", thief_id, victim_id, "stole from")]

        if rng.random() >= self.discovery_chance:
            return events
        self._caught += 1

        edge = graph.get_edge(thief_id, victim_id)
        new_valence = max(-1.0, edge.valence_from(victim_id) - self.caught_animosity)
        edge.set_valence_from(victim_id, new_valence)
        events.append(
            Event(day, self.name, "caught", victim_id, thief_id, f"victim's valence -{self.caught_animosity:.2f}")
        )

        for guard_id in graph.neighbors(thief_id):
            if graph.nodes[guard_id].role != "guard":
                continue
            guard_edge = graph.get_edge(thief_id, guard_id)
            new_guard_valence = max(-1.0, guard_edge.valence_from(guard_id) - self.caught_animosity)
            guard_edge.set_valence_from(guard_id, new_guard_valence)
            events.append(
                Event(day, self.name, "guard_notified", guard_id, thief_id,
                      f"guard's valence -{self.caught_animosity:.2f}")
            )

        if rng.random() >= self.arrest_chance:
            return events

        execution_chance = self.execution_weight * (1.0 - self._avg_guard_loyalty)

        self._deterrence += 1.0
        if rng.random() < execution_chance:
            graph.record_death(thief_id, day, "execution")
            self._executions += 1
            events.append(Event(day, self.name, "executed", thief_id, thief_id, "killed after being caught stealing"))
        else:
            state[thief_id]["is_thief"] = False
            self._arrests += 1
            events.append(Event(day, self.name, "arrested", thief_id, thief_id, "arrested and no longer a thief"))

        return events

    def end_of_day(self, graph, state, day: int, rng: random.Random) -> List[Event]:
        self._deterrence *= self.deterrence_decay
        events: List[Event] = []
        for resident_id, resident_state in state.items():
            if resident_state["is_thief"] or resident_state["role"] == "noble":
                continue
            if not graph.nodes[resident_id].alive:
                continue
            base_p = self.become_thief_rate * THIEF_SES_FACTOR.get(resident_state["ses"], 1.0)
            p = base_p / (1.0 + self.deterrence_weight * self._deterrence)
            if rng.random() < p:
                resident_state["is_thief"] = True
                events.append(Event(day, self.name, "became_thief", resident_id, resident_id, "turned to thievery"))
        return events

    def summarize(self, state) -> Dict[str, int]:
        return {
            "thieves": sum(1 for s in state.values() if s["is_thief"]),
            "thefts": self._thefts,
            "thefts_caught": self._caught,
            "thefts_arrested": self._arrests,
            "thefts_executed": self._executions,
        }


class ReligionPhenomenon:
    """Priests: religious devotion + skepticism, corruption, and blame as the
    town's disease-curers.

    Fires per edge, only between a civilian and a priest. Most civilians'
    own affinity toward priests they know grows slowly over time, scaled by
    their own religiousness -- a devotion event, the second concrete
    instance of the "favor" event type after bribery. A small,
    deliberately-chosen minority (skepticism above heretic_skepticism_
    threshold -- ~11% of civilians on the reference town, since skepticism
    now clusters somewhat by family, see graph.py's FAMILY_CORRELATED_TRAITS)
    feel the opposite: their own affinity toward priests they know erodes
    instead, scaled by their own skepticism -- a "friction" event, the
    mirror case. Which one applies to a given civilian is decided once, in
    init_state (skepticism > threshold), not re-rolled daily -- same
    "sticky, not recomputed" shape TheftPhenomenon's is_thief flag uses.

    Corruption (added 2026-09-22) reuses bribery's exact shape rather than
    reinventing it: a civilian pays a priest for favorable treatment,
    scaled by the civilian's own cunning and wealth (GuardPhenomenon's
    BRIBE_WEALTH_FACTOR) and restrained by the priest's own loyalty --
    same "corruptible if low-loyalty" logic guards use, no separate
    "integrity" trait needed. Only the priest's own outgoing valence
    toward the payer moves, same one-directional "favor" shape bribery and
    devotion both use. Devotion/friction and corruption share the same
    edge and roll against each other, not independently: edge_probability
    returns their sum, and apply_effect draws which one actually fired,
    weighted by their relative odds -- same pattern ViolencePhenomenon's
    _pick_aggressor uses to resolve which of two outcomes wins a shared
    roll.

    Disease-curer blame (added 2026-09-23) reads graph.deaths, the shared
    death record, rather than wiring a reference to Contagion/Ailments:
    during an outbreak -- at least blame_outbreak_threshold sickness deaths
    in the last blame_window_days -- every living civilian who had a tie to
    someone who just died of sickness lowers their own valence toward each
    priest they know, by blame_shock * tie_strength to the deceased (losing
    a spouse stings more than losing a neighbor). Same grief-shaped,
    one-directional move as violence's grief_shock. The threshold sits far
    above routine illness: on the reference town flu+diarrhea never exceed
    7 deaths in any 30-day window, while the epidemic kills 112 in a week.
    Deaths from before the outbreak crossed the threshold aren't blamed
    retroactively."""

    name = "religion"

    def __init__(
        self,
        devotion_base_rate: float = 0.01,
        devotion_affinity_gain: float = 0.1,
        heretic_skepticism_threshold: float = 0.8,
        friction_base_rate: float = 0.01,
        friction_animosity_loss: float = 0.1,
        corruption_base_rate: float = 0.005,
        corruption_affinity_gain: float = 0.15,
        blame_window_days: int = 30,
        blame_outbreak_threshold: int = 10,
        # 0.1 was tried first: on the reference town it pushed 87
        # civilian-priest pairs past group_hate_threshold (from 4) and bands
        # of 15 mourners rioted against 3 of the 4 priests. 0.05 leaves no
        # priest-targeted mobs; riots/group kills unchanged over 5 seeds.
        blame_shock: float = 0.05,
    ):
        self.devotion_base_rate = devotion_base_rate
        self.devotion_affinity_gain = devotion_affinity_gain
        self.heretic_skepticism_threshold = heretic_skepticism_threshold
        self.friction_base_rate = friction_base_rate
        self.friction_animosity_loss = friction_animosity_loss
        self.corruption_base_rate = corruption_base_rate
        self.corruption_affinity_gain = corruption_affinity_gain
        self._devotions = 0
        self._frictions = 0
        self._corruptions = 0
        self._heretics = 0
        self.blame_window_days = blame_window_days
        self.blame_outbreak_threshold = blame_outbreak_threshold
        self.blame_shock = blame_shock
        self._deaths_seen = 0  # index into graph.deaths already processed
        self._blames = 0

    def init_state(self, graph) -> Dict[int, Any]:
        state = {}
        for resident_id, node in graph.nodes.items():
            is_heretic = node.role == "civilian" and node.skepticism > self.heretic_skepticism_threshold
            if is_heretic:
                self._heretics += 1
            state[resident_id] = {
                "role": node.role,
                "religiousness": node.religiousness,
                "skepticism": node.skepticism,
                "is_heretic": is_heretic,
                "ses": node.ses,
                "cunning": node.cunning,
                "loyalty": node.loyalty,
            }
        return state

    def _faith_probability(self, civilian_state) -> float:
        if civilian_state["is_heretic"]:
            return self.friction_base_rate * civilian_state["skepticism"]
        return self.devotion_base_rate * civilian_state["religiousness"]

    def _corruption_probability(self, civilian_state, priest_state) -> float:
        wealth_factor = BRIBE_WEALTH_FACTOR.get(civilian_state["ses"], 1.0)
        priest_restraint = 1.0 - priest_state["loyalty"]
        return self.corruption_base_rate * civilian_state["cunning"] * wealth_factor * priest_restraint

    def edge_probability(self, edge, state_a, state_b, day: int) -> float:
        roles = {state_a["role"], state_b["role"]}
        if roles != {"civilian", "priest"}:
            return 0.0
        civilian_state = state_a if state_a["role"] == "civilian" else state_b
        priest_state = state_a if state_a["role"] == "priest" else state_b
        total = self._faith_probability(civilian_state) + self._corruption_probability(civilian_state, priest_state)
        return total * edge.tie_strength

    def apply_effect(self, graph, state, a: int, b: int, day: int, rng: random.Random) -> List[Event]:
        edge = graph.get_edge(a, b)
        civilian_id = a if state[a]["role"] == "civilian" else b
        priest_id = b if civilian_id == a else a
        civilian_state = state[civilian_id]
        priest_state = state[priest_id]

        faith_p = self._faith_probability(civilian_state)
        corruption_p = self._corruption_probability(civilian_state, priest_state)
        total = faith_p + corruption_p
        # total > 0 always holds here: edge_probability already required a
        # positive roll against this same total for apply_effect to be called
        if rng.random() < corruption_p / total:
            new_valence = min(1.0, edge.valence_from(priest_id) + self.corruption_affinity_gain)
            edge.set_valence_from(priest_id, new_valence)
            self._corruptions += 1
            return [
                Event(day, self.name, "corruption", civilian_id, priest_id,
                      f"priest's affinity +{self.corruption_affinity_gain:.2f}")
            ]

        if civilian_state["is_heretic"]:
            new_valence = max(-1.0, edge.valence_from(civilian_id) - self.friction_animosity_loss)
            edge.set_valence_from(civilian_id, new_valence)
            self._frictions += 1
            return [
                Event(day, self.name, "friction", civilian_id, priest_id,
                      f"civilian's affinity -{self.friction_animosity_loss:.2f}")
            ]

        new_valence = min(1.0, edge.valence_from(civilian_id) + self.devotion_affinity_gain)
        edge.set_valence_from(civilian_id, new_valence)
        self._devotions += 1
        return [
            Event(day, self.name, "devotion", civilian_id, priest_id,
                  f"civilian's affinity +{self.devotion_affinity_gain:.2f}")
        ]

    def end_of_day(self, graph, state, day: int, rng: random.Random) -> List[Event]:
        new_deaths = graph.deaths[self._deaths_seen:]
        self._deaths_seen = len(graph.deaths)
        new_sickness = [d for d in new_deaths if d["cause"] in SICKNESS_CAUSES]
        if not new_sickness:
            return []
        recent = sum(
            1 for d in graph.deaths
            if d["cause"] in SICKNESS_CAUSES and d["day"] > day - self.blame_window_days
        )
        if recent < self.blame_outbreak_threshold:
            return []

        # ponytail: graph.neighbors scans every edge, fine for one outbreak's
        # deaths; index adjacency on the graph if blame ever runs daily at scale
        blame_by_civilian: Dict[int, float] = {}
        for death in new_sickness:
            deceased = death["resident_id"]
            for mourner in graph.neighbors(deceased):
                if graph.nodes[mourner].alive and state[mourner]["role"] == "civilian":
                    shock = self.blame_shock * graph.get_edge(mourner, deceased).tie_strength
                    blame_by_civilian[mourner] = blame_by_civilian.get(mourner, 0.0) + shock

        events = []
        for civilian_id, shock in blame_by_civilian.items():
            for priest_id in graph.neighbors(civilian_id):
                if not graph.nodes[priest_id].alive or state[priest_id]["role"] != "priest":
                    continue
                edge = graph.get_edge(civilian_id, priest_id)
                edge.set_valence_from(civilian_id, max(-1.0, edge.valence_from(civilian_id) - shock))
                self._blames += 1
                events.append(Event(day, self.name, "blame", civilian_id, priest_id,
                                    f"lost ties to sickness -- civilian's affinity -{shock:.2f}"))
        return events

    def summarize(self, state) -> Dict[str, int]:
        return {
            "devotions": self._devotions,
            "frictions": self._frictions,
            "corruptions": self._corruptions,
            "heretics": self._heretics,
            "blames": self._blames,
        }
