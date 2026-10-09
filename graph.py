import random
import sqlite3
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from demography import MAX_AGE, settled_age_weights


@dataclass
class Node:
    resident_id: int
    ses: Optional[str]
    alive: bool = True
    # personal traits, each 0..1, independent of ses; shape event odds
    # (bribability, crime success, riot participation, ...) as those
    # phenomena get built. Only religiousness is mutated by events so far
    # (recovering from a sickness raises it, see ReligionPhenomenon).
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
    # a past military background, independent of (and layered on top of) their
    # *current* job -- a farmhand or blacksmith can still be an ex-soldier.
    # Only ever rolled for civilians at import (see _load_residents): a
    # currently-serving guard isn't "ex" anything, and nobles/priests aren't
    # the pool Nobles hires protection from, they're who it protects.
    is_ex_soldier: bool = False
    # drawn to their own sex (params.same_sex_share); marriages pair only
    # compatible people, and only mixed-sex couples have children
    same_sex_attracted: bool = False
    # 0..1, what they're going through (poverty, grief, illness), kept
    # current by StressPhenomenon; theft reads it
    stress: float = 0.0
    # months in a row their household went hungry, and whether they beg
    # (economy, slice 3 D)
    hungry_months: int = 0
    beggar: bool = False
    # TownShape home district (resident -> home building -> district) and
    # that district's zone_type, e.g. "poor_residential". None when the
    # snapshot has no buildings/districts (test fixtures).
    district_id: Optional[int] = None
    district_zone: Optional[str] = None
    # TownShape identity fields (residents table), kept so a resident can be
    # matched back to -- or later written back into -- the TownShape
    # database, and so a newborn can inherit a household and home. None when
    # the snapshot lacks the column (test fixtures).
    household_id: Optional[int] = None
    home_building_id: Optional[int] = None
    workplace_building_id: Optional[int] = None
    birth_date: Optional[str] = None

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


# Which ties changed (speed-up 2026-09-30): phenomena that need "every tie
# where ..." keep that set up to date from these reports (TieFilter) instead
# of scanning all ~80,000 ties every day. Each graph keeps its listeners'
# logs (SocialGraph._tie_listeners); a tie joining a graph points at them.
_TRACKED_TIE_FIELDS = frozenset(("valence_a_to_b", "valence_b_to_a", "source_type"))


class TieFilter:
    """The keys of every live tie matching `predicate(edge)`, in the order the
    ties were added (each tie's _serial) -- what a full scan of graph.edges
    would give, kept up to date from tie change reports."""

    def __init__(self, predicate):
        self.predicate = predicate
        self._log: List["Edge"] = []
        self._keys = None
        self._graph = None

    def keys(self, graph) -> List[Tuple[int, int]]:
        edges, predicate = graph.edges, self.predicate
        if self._keys is None or self._graph is not graph:
            self._graph = graph
            graph._tie_listeners.append(self._log)
            self._keys = {key for key, edge in edges.items() if predicate(edge)}
        else:
            keys = self._keys
            for edge in self._log:
                a, b = edge.resident_a, edge.resident_b
                key = (a, b) if a < b else (b, a)
                current = edges.get(key)  # the live tie there now, if any (it may be another graph's edge)
                if current is not None and predicate(current):
                    keys.add(key)
                else:
                    keys.discard(key)
            for key in [key for key in keys if key not in edges]:  # retired since
                keys.discard(key)
        self._log.clear()
        return sorted(self._keys, key=lambda key: edges[key]._serial)


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
    # what a friendship was before (neighbor, coworker, ...), see befriend
    former_type: Optional[str] = None

    def __setattr__(self, name, value):
        object.__setattr__(self, name, value)
        if name in _TRACKED_TIE_FIELDS:  # feelings or type changed: tell whoever is listening
            listeners = self.__dict__.get("_listeners")
            if listeners:
                for log in listeners:
                    log.append(self)

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


DEFAULT_TRAIT_MEAN = 0.5
DEFAULT_STRICTNESS = 0.5


@dataclass
class TownParameters:
    """City-wide parameters (pipeline step 2, 2026-09-23): the dials that set
    a town's character and so its equilibrium, in one place instead of
    constants scattered across phenomena. The defaults reproduce the town's
    behaviour before this existed exactly.

    aggression and strictness are read while the town runs, so changing them
    mid-run takes effect at once; loyalty and religiosity are the averages
    residents' traits are drawn around at import."""
    # TownShape's own 0..1 generation dial: 1x violence/riot odds at 0, 3x at 1
    aggression: float = 0.0
    loyalty: float = DEFAULT_TRAIT_MEAN
    religiosity: float = DEFAULT_TRAIT_MEAN
    # how harshly crime is punished; scales the chance a caught thief is
    # executed, 1x at the default
    strictness: float = DEFAULT_STRICTNESS
    # share of residents drawn to their own sex, drawn at import and birth;
    # roughly that share of new marriages are same-sex (user, 2026-09-27)
    same_sex_share: float = 0.1
    # shares of residents in each class at import, poorest first: very poor
    # (barely surviving), poor, middling, rich, very rich (user, 2026-09-30,
    # 15/50/25/9/1: unskilled wages sat at bare subsistence, book §5c;
    # the top 1% held ~30% of the wealth, book §3b/§3d). The lines between
    # them are then fixed and people move across them as their resources
    # change (economy.py).
    class_shares: Tuple[float, ...] = (0.15, 0.50, 0.25, 0.09, 0.01)

    def aggression_factor(self) -> float:
        return 1.0 + 2.0 * self.aggression

    def strictness_factor(self) -> float:
        return self.strictness / DEFAULT_STRICTNESS


class SocialGraph:
    def __init__(self) -> None:
        self.nodes: Dict[int, Node] = {}
        self.edges: Dict[Tuple[int, int], Edge] = {}
        # city-wide parameters; aggression is read from TownShape's own
        # town_state at import (0.0, "no extra volatility", when absent)
        self.params = TownParameters()
        # No real TownShape data for this (checked town_state's own columns
        # and the wider source -- no governor/mayor/ruler concept exists to
        # import). A single town-wide fact, same shape as params.aggression,
        # rather than a Node field almost everyone would carry as False.
        # Left unset at import; ViolencePhenomenon's coup mechanic picks (and
        # re-picks, on succession) the town's most powerful living noble the
        # first time it needs one, rather than duplicating that selection
        # logic here too.
        self.governor_id: Optional[int] = None
        # Same shape as TownShape's own `deaths` table (resident, date,
        # cause), in memory rather than written back: the reference .db is
        # opened read-only so reruns on one seed stay comparable. Every
        # phenomenon that kills goes through record_death, so "who died of
        # what" is one lookup for anything that needs it (e.g. blaming a
        # priest for an illness death).
        self.deaths: List[Dict[str, Any]] = []
        self.recoveries: List[Dict[str, Any]] = []
        # district_id -> "priest" or "noble" (who sealed it). Mutated in place,
        # never reassigned: ContagionPhenomenon holds a reference to it.
        self.quarantined_districts: Dict[int, str] = {}
        # resident -> {other resident -> their tie}, built lazily in edge order
        # (so neighbors() keeps the order it always had) and kept in step by
        # add_edge and the retire methods. A tie lookup is two dict reads,
        # no key to build (2026-09-30 speed-up: 8.5M lookups a year)
        self._links: Optional[Dict[int, Dict[int, Edge]]] = None
        # each live tie carries its number in the order ties were added (= graph.edges
        # order) as _serial (2026-10-09: a table of them held 51 B a tie)
        self._next_serial = 0
        self._tie_listeners: List[List[Edge]] = []  # change logs of this graph's TieFilters
        # Residents added mid-run (births, arrivals) enter through the same
        # code path as import (node_from_resident_row / edge_from_relationship),
        # fed TownShape-shaped rows. These keep what that needs after import:
        self.reference_year: Optional[int] = None  # for a newcomer's age
        self.building_districts: Dict[int, Tuple[int, str]] = {}  # building -> (district, zone)
        self.family_root: Dict[int, int] = {}  # resident -> family root (parent/sibling ties)
        self.family_baselines: Dict[int, Dict[str, float]] = {}  # family root -> shared trait centres
        # added but not yet registered with the phenomena; the engine drains it
        self.newcomers: List[int] = []
        # living residents, kept by add_node and record_death (speed-up
        # 2026-09-30: the engine counted everyone every day)
        self.alive_count = 0
        # Ties of the dead, moved out of `edges` once every phenomenon has
        # read them (retire_ties_of_dead): kept for safekeeping (user,
        # 2026-09-29) -- whose grandparents knew each other may matter one
        # day -- and for an arrival taking over a dead person's place.
        # Each record: both ids, type, closeness, both feelings, when retired.
        self.archived_ties: List[Dict[str, Any]] = []
        self._archived_by_dead: Dict[int, List[Dict[str, Any]]] = {}
        self._deaths_retired = 0  # cursor into self.deaths
        self._ties_to_retire: List[Tuple[int, int, int, str]] = []  # (a, b, day, reason), see retire_tie

    def record_recovery(self, resident_id: int, day: int, cause: str) -> None:
        # the counterpart of record_death, for anything that reacts to
        # someone getting better (priests' curer gratitude)
        self.recoveries.append({"resident_id": resident_id, "day": day, "cause": cause})

    def record_death(self, resident_id: int, day: int, cause: str, killed_by: Optional[int] = None) -> None:
        if self.nodes[resident_id].alive:
            self.alive_count -= 1
        self.nodes[resident_id].alive = False
        self.deaths.append({"resident_id": resident_id, "day": day, "cause": cause, "killed_by": killed_by})

    def add_node(self, node: Node) -> None:
        old = self.nodes.get(node.resident_id)
        self.alive_count += (1 if node.alive else 0) - (1 if old is not None and old.alive else 0)
        self.nodes[node.resident_id] = node

    def next_resident_id(self) -> int:
        """The id a resident created by the simulation should take: TownShape's
        residents table assigns max(id) + 1 on insert, so ids created here line
        up with what a later write-back would get (a write-back should still
        map them defensively, see docs/townshape-integration.md)."""
        return max(self.nodes, default=0) + 1

    def add_resident(self, row: Dict[str, Any], relationships: List[Tuple[int, str]],
                     rng: random.Random) -> int:
        """Add a resident mid-run (a birth, an arrival), shaped like a
        TownShape `residents` row (id optional: next_resident_id() if absent)
        plus TownShape-typed relationships to residents already in the town,
        e.g. [(mother_id, "parent"), (sibling_id, "sibling")]. Built exactly
        like an imported resident; the engine then registers them with every
        phenomenon at the end of the current phenomenon's day."""
        row = dict(row)
        resident_id = row.setdefault("id", self.next_resident_id())
        if resident_id in self.nodes:
            raise ValueError(f"resident {resident_id} already exists")
        for other_id, relationship_type in relationships:
            if relationship_type in ("parent", "sibling") and other_id in self.nodes:
                self.family_root[resident_id] = self.family_root.get(other_id, other_id)
                break
        node = node_from_resident_row(self, row, rng)
        location = self.building_districts.get(node.home_building_id)
        if location is not None:
            node.district_id, node.district_zone = location
        self.add_node(node)
        for other_id, relationship_type in relationships:
            if other_id in self.nodes and relationship_type in RELATIONSHIP_TYPE_BASELINES:
                self.add_edge(edge_from_relationship(self, resident_id, other_id, relationship_type, rng))
        self.newcomers.append(resident_id)
        return resident_id

    @staticmethod
    def _key(a: int, b: int) -> Tuple[int, int]:
        return (a, b) if a < b else (b, a)

    def add_edge(self, edge: Edge) -> None:
        key = self._key(edge.resident_a, edge.resident_b)
        existing = self.edges.get(key)
        if existing is not None and existing.tie_strength >= edge.tie_strength:
            return
        self.edges[key] = edge
        if existing is None:
            object.__setattr__(edge, "_serial", self._next_serial)  # not a field: no effect on ==
            self._next_serial += 1
        else:  # the stronger tie takes the old one's place
            object.__setattr__(edge, "_serial", existing._serial)
        object.__setattr__(edge, "_listeners", self._tie_listeners)  # not a field: no effect on ==
        for log in self._tie_listeners:  # a tie joining the graph is news too
            log.append(edge)
        # a new key goes to the end, like the edge order; a replaced one keeps
        # its place and only swaps in the stronger tie
        if self._links is not None:
            self._links.setdefault(key[0], {})[key[1]] = edge
            self._links.setdefault(key[1], {})[key[0]] = edge

    @staticmethod
    def _archive_record(edge: "Edge", day: int, dead: Optional[int], reason: str) -> Dict[str, Any]:
        return {"resident_a": edge.resident_a, "resident_b": edge.resident_b, "source_type": edge.source_type,
                "time": edge.time, "intimacy": edge.intimacy, "services": edge.services,
                "valence_a_to_b": edge.valence_a_to_b, "valence_b_to_a": edge.valence_b_to_a,
                "former_type": edge.former_type, "retired_on_day": day, "on_death_of": dead, "reason": reason}

    def retire_ties_of_dead(self, before_day: int) -> int:
        """Move the ties of everyone who died before `before_day` out of the
        live graph into the archive; returns how many ties moved. Called by the
        engine at the end of each day for deaths up to the day before, so every
        phenomenon reading a death (grief, widowhood, blame, inheritance,
        stress) has seen the ties first. Keeps the live graph from filling up
        with the dead (2026-09-29: runs had slowed from 19 to 35 minutes)."""
        moved = 0
        links = self._ensure_links()
        self.last_retired_keys = []  # the engine drops these from its tie order
        for a, b, day, reason in self._ties_to_retire:
            key = self._key(a, b)
            edge = self.edges.pop(key, None)
            if edge is None:
                continue  # already gone with a death
            self.archived_ties.append(self._archive_record(edge, day, None, reason))
            del links[a][b]
            del links[b][a]
            self.last_retired_keys.append(key)
            moved += 1
        self._ties_to_retire = []
        while self._deaths_retired < len(self.deaths) and self.deaths[self._deaths_retired]["day"] < before_day:
            dead = self.deaths[self._deaths_retired]["resident_id"]
            self._deaths_retired += 1
            records = self._archived_by_dead.setdefault(dead, [])
            for other in list(links.get(dead, ())):
                key = self._key(dead, other)
                edge = self.edges.pop(key)
                self.last_retired_keys.append(key)
                record = self._archive_record(edge, before_day - 1, dead, "death")
                self.archived_ties.append(record)
                records.append(record)
                del links[other][dead]
                moved += 1
            links.pop(dead, None)
        return moved

    def retire_tie(self, a: int, b: int, day: int, reason: str) -> None:
        """Queue a live tie between two living residents to leave the graph
        (e.g. an acquaintance that faded); it moves to the archive with the
        ties of the dead at the end of the day."""
        self._ties_to_retire.append((a, b, day, reason))

    def archived_ties_of(self, dead: int) -> List[Dict[str, Any]]:
        """The archive records of every tie a dead resident had when it was retired."""
        return list(self._archived_by_dead.get(dead, []))

    def _ensure_links(self) -> Dict[int, Dict[int, Edge]]:
        if self._links is None:
            links: Dict[int, Dict[int, Edge]] = {}
            for (a, b), edge in self.edges.items():
                links.setdefault(a, {})[b] = edge
                links.setdefault(b, {})[a] = edge
            self._links = links
        return self._links

    def get_edge(self, a: int, b: int) -> Optional[Edge]:
        ties = self._ensure_links().get(a)
        return ties.get(b) if ties is not None else None

    def neighbors(self, resident_id: int) -> List[int]:
        return list(self._ensure_links().get(resident_id, ()))

    def ties_of(self, resident_id: int) -> Dict[int, Edge]:
        """The live {other resident: tie} table: read it, don't change it (a
        copy-free neighbors() plus get_edge, for the hot loops)."""
        return self._ensure_links().get(resident_id, {})

    def edge_keys_of(self, resident_ids) -> List[Tuple[int, int]]:
        """Keys of every tie touching any of these residents, deduplicated."""
        keys = set()
        for resident_id in resident_ids:
            for other in self.neighbors(resident_id):
                keys.add(self._key(resident_id, other))
        return list(keys)


RELATIONSHIP_TYPE_BASELINES = {
    "spouse":    {"time": (0.75, 0.15), "intimacy": (0.80, 0.15), "services": (0.75, 0.15), "valence": (0.40, 0.40)},
    "parent":    {"time": (0.70, 0.15), "intimacy": (0.75, 0.15), "services": (0.70, 0.15), "valence": (0.40, 0.40)},
    "sibling":   {"time": (0.60, 0.20), "intimacy": (0.60, 0.20), "services": (0.60, 0.20), "valence": (0.30, 0.45)},
    "unit_mate": {"time": (0.55, 0.20), "intimacy": (0.40, 0.20), "services": (0.65, 0.20), "valence": (0.35, 0.30)},
    "coworker":  {"time": (0.45, 0.20), "intimacy": (0.20, 0.15), "services": (0.40, 0.20), "valence": (0.00, 0.35)},
    "neighbor":  {"time": (0.25, 0.15), "intimacy": (0.20, 0.15), "services": (0.30, 0.20), "valence": (0.00, 0.35)},
    "classmate": {"time": (0.45, 0.20), "intimacy": (0.20, 0.20), "services": (0.25, 0.20), "valence": (0.00, 0.40)},
    # sim-only types (2026-09-29, FriendshipPhenomenon): someone met through a
    # person you know; a friendship is normally a warmed-up tie of another type
    "acquaintance": {"time": (0.15, 0.10), "intimacy": (0.10, 0.08), "services": (0.10, 0.10), "valence": (0.00, 0.30)},
    "friend":    {"time": (0.45, 0.20), "intimacy": (0.55, 0.20), "services": (0.40, 0.20), "valence": (0.50, 0.25)},
}

# A non-family tie warm both ways at FRIEND_WARMTH or more is a friendship;
# it goes back to what it was once either side cools below FRIEND_COOLED.
# At 0.3 the reference town starts with ~2.8 friends a person.
FRIEND_WARMTH = 0.3
FRIEND_COOLED = 0.1
FRIEND_INTIMACY = 0.5  # a friendship is at least this close

FISKE_TAGS = {
    "spouse": "Communal Sharing",
    "parent": "Communal Sharing",
    "sibling": "Communal Sharing",
    "unit_mate": "Equality Matching",
    "coworker": "Authority Ranking",
    "neighbor": "Equality Matching",
    "classmate": "Communal Sharing",
    "shopkeeper_customer": "Market Pricing",
    "acquaintance": "Equality Matching",
    "friend": "Communal Sharing",
}


def befriend(edge: "Edge") -> None:
    """A warm tie becomes a friendship, remembering what it was."""
    edge.former_type = edge.source_type
    edge.source_type, edge.fiske_type = "friend", FISKE_TAGS["friend"]
    edge.intimacy = max(edge.intimacy, FRIEND_INTIMACY)


def unfriend(edge: "Edge") -> None:
    """A cooled friendship goes back to what it was (an acquaintance if it
    started as one, or had no other type)."""
    edge.source_type = edge.former_type or "acquaintance"
    edge.fiske_type = FISKE_TAGS[edge.source_type]
    edge.former_type = None


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _clamp_signed(value: float) -> float:
    return max(-1.0, min(1.0, value))


TRAIT_NAMES = ["religiousness", "cunning", "skepticism", "loyalty"]
# family members are more likely to share a similar level of faith/skepticism
# (raised in the same household, same religious practice) -- not assured, so
# this isn't a copy, just a shared per-family center each member's own draw
# lands near. cunning/loyalty stay fully independent -- nothing links them to
# upbringing the way faith is.
FAMILY_CORRELATED_TRAITS = ["religiousness", "skepticism"]
# ponytail: single tunable knob for how tightly faith/skepticism run in
# families. Individual draws use this stdev around the family's own center
# (itself drawn with the population stdev, 0.2), which works out to a
# within-family correlation of about 0.64 -- a real tendency, far from a
# guarantee. Lower this to make families more alike, raise it to loosen the
# tendency.
FAMILY_TRAIT_STDEV = 0.15


def synthesize_traits(rng: random.Random, family_baseline: Optional[Dict[str, float]] = None,
                      means: Optional[Dict[str, float]] = None) -> Dict[str, float]:
    # means: per-trait population average (TownParameters' loyalty and
    # religiosity); DEFAULT_TRAIT_MEAN for any trait not given
    means = means or {}
    traits = {}
    for name in TRAIT_NAMES:
        if family_baseline is not None and name in FAMILY_CORRELATED_TRAITS:
            traits[name] = _clamp01(rng.gauss(family_baseline[name], FAMILY_TRAIT_STDEV))
        else:
            traits[name] = _clamp01(rng.gauss(means.get(name, DEFAULT_TRAIT_MEAN), 0.2))
    return traits


def _trait_means(params: TownParameters) -> Dict[str, float]:
    return {"loyalty": params.loyalty, "religiousness": params.religiosity}


# civilians only -- see Node.is_ex_soldier. No real TownShape data to derive
# this from (checked town_db/military.py and the reference town's own
# military_service table: it only tracks *current* guards, end_date is
# always NULL, no retired-service records exist), so this is flat synthesis
# like the personal traits above, not an import of real history.
# 0.08 is a first guess sized against the reference town's noble/priest
# degree (median ~102 neighbors) so a typical noble/priest has several
# ex-soldier neighbors to hire from, not zero and not dozens -- tune if
# mercenary hiring reads as too easy or too starved of candidates.
EX_SOLDIER_BASE_RATE = 0.08
_NON_CIVILIAN_OCCUPATIONS = {"guard", "priest", "acolyte"}


def _family_groups(conn: sqlite3.Connection) -> Dict[int, int]:
    """Union-find over parent/sibling ties only -- the blood-relation subset
    of `relationships`, not spouse/coworker/etc -- so each resident maps to a
    family root id. A resident with no parent/sibling row of their own is
    simply absent from the map; callers treat that as "their own family"."""
    rows = conn.execute(
        "SELECT resident_a_id, resident_b_id FROM relationships WHERE relationship_type IN ('parent', 'sibling')"
    ).fetchall()
    parent: Dict[int, int] = {}

    def find(x: int) -> int:
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for resident_a_id, resident_b_id in rows:
        root_a, root_b = find(resident_a_id), find(resident_b_id)
        if root_a != root_b:
            parent[root_a] = root_b

    return {resident_id: find(resident_id) for resident_id in parent}


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


# ponytail: single tunable knob for the vision doc's own "resentment on
# the poor side" language -- a fixed extra negative shift layered on top
# of whatever the plain per-edge synthesis already drew, so real variance
# is preserved (the skew is additive, not a hard override). Tax-driven
# further growth (raising this as unrest/taxes rise) is deferred -- needs
# Taxes, which doesn't exist yet.
#
# 0.25 was a first guess, never checked against RiotPhenomenon's own
# unrest_threshold before shipping -- it pushed the reference town's
# civilian-authority hostility average from 0.251 (the historical
# baseline riots were calibrated against, see docs/decisions.md's
# 2026-09-17 riot-threshold entry) to 0.332, an 80% jump in the margin
# above threshold, and organic riots jumped from ~1/year to 4/year on a
# town whose own aggression dial is 0.0 -- not remotely "a stressed out
# city." 0.1 keeps that margin to about 1.26x the old baseline: a real,
# visible uptick without turning an average town into a permanently
# riot-prone one. See docs/decisions.md's 2026-09-22 correction entry.
NOBLE_POOR_RESENTMENT_SHIFT = 0.1


def _apply_noble_poor_skew(graph: "SocialGraph", edge: Edge) -> None:
    """Nobles and poor residents don't get the same neutral synthesis as
    everyone else (vision doc: "noble/poor animosity skewed toward
    resentment on the poor side from the start"). Only the poor party's own
    outgoing valence shifts further negative; a noble's own feelings toward
    a poor person they know are untouched -- same one-directional shape
    the family-trait correlation and every phenomenon's own favor/wrongdoing
    events already use."""
    node_a, node_b = graph.nodes[edge.resident_a], graph.nodes[edge.resident_b]
    if node_a.is_noble and not node_b.is_noble and node_b.ses in ("poor", "very_poor"):
        poor_id = node_b.resident_id
    elif node_b.is_noble and not node_a.is_noble and node_a.ses in ("poor", "very_poor"):
        poor_id = node_a.resident_id
    else:
        return
    edge.set_valence_from(poor_id, _clamp_signed(edge.valence_from(poor_id) - NOBLE_POOR_RESENTMENT_SHIFT))


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
    graph.reference_year = reference_year
    graph.family_root = _family_groups(conn)
    for resident_id, ses, gender, birth_date, occupation, is_noble in rows:
        graph.add_node(node_from_resident_row(graph, {
            "id": resident_id, "ses": ses, "gender": gender, "birth_date": birth_date,
            "occupation": occupation, "is_noble": is_noble,
        }, rng))


def node_from_resident_row(graph: "SocialGraph", row: Dict[str, Any], rng: random.Random) -> Node:
    """One resident, from a TownShape `residents`-shaped row: used by import
    and by SocialGraph.add_resident, so a newcomer is built exactly like a
    resident present from day 1. Each family's shared trait centre is drawn
    the first time any member is built (graph.family_baselines, keyed by
    graph.family_root), so every member -- including a later newborn --
    lands near the same one."""
    resident_id = row["id"]
    means = _trait_means(graph.params)
    family_root = graph.family_root.get(resident_id, resident_id)
    if family_root not in graph.family_baselines:
        graph.family_baselines[family_root] = {
            name: _clamp01(rng.gauss(means.get(name, DEFAULT_TRAIT_MEAN), 0.2)) for name in FAMILY_CORRELATED_TRAITS
        }
    occupation, is_noble = row.get("occupation"), bool(row.get("is_noble"))
    is_civilian = not is_noble and occupation not in _NON_CIVILIAN_OCCUPATIONS
    is_ex_soldier = is_civilian and rng.random() < EX_SOLDIER_BASE_RATE
    return Node(
        resident_id=resident_id, ses=row.get("ses"), alive=True, gender=row.get("gender"),
        age=_age_from_birth_date(row.get("birth_date"), graph.reference_year),
        occupation=occupation, is_noble=is_noble, is_ex_soldier=is_ex_soldier,
        household_id=row.get("household_id"), home_building_id=row.get("home_building_id"),
        workplace_building_id=row.get("workplace_building_id"), birth_date=row.get("birth_date"),
        same_sex_attracted=rng.random() < graph.params.same_sex_share,
        **synthesize_traits(rng, graph.family_baselines[family_root], means),
    )


def edge_from_relationship(graph: "SocialGraph", resident_a_id: int, resident_b_id: int,
                           relationship_type: str, rng: random.Random) -> Edge:
    """One tie of a TownShape relationship type, with synthesized strength
    and feelings (and the noble/poor resentment skew): used by import and by
    SocialGraph.add_resident."""
    attrs = synthesize_relationship_attributes(relationship_type, rng)
    edge = Edge(
        resident_a=resident_a_id,
        resident_b=resident_b_id,
        source_type=relationship_type,
        fiske_type=FISKE_TAGS[relationship_type],
        **attrs,
    )
    _apply_noble_poor_skew(graph, edge)
    return edge


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
        graph.add_edge(edge_from_relationship(graph, resident_a_id, resident_b_id, relationship_type, rng))


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
        graph.params.aggression = aggression
    if year_start is None:
        return None
    try:
        return date.fromisoformat(year_start).year
    except ValueError:
        return None


def _load_districts(conn: sqlite3.Connection, graph: SocialGraph) -> None:
    # not every snapshot has buildings/districts (test fixtures) -- leave
    # district_id None rather than fail the import. Draws no randomness, so
    # adding it left every seed's import unchanged.
    try:
        buildings = conn.execute(
            "SELECT b.id, d.id, d.zone_type FROM buildings b JOIN districts d ON d.id = b.district_id"
        ).fetchall()
    except sqlite3.OperationalError:
        return
    graph.building_districts = {building_id: (district_id, zone) for building_id, district_id, zone in buildings}
    for node in graph.nodes.values():
        location = graph.building_districts.get(node.home_building_id)
        if location is not None:
            node.district_id, node.district_zone = location


def _building_types(conn: sqlite3.Connection) -> Dict[int, str]:
    try:
        return dict(conn.execute("SELECT id, building_type FROM buildings").fetchall())
    except sqlite3.OperationalError:  # test fixtures without buildings
        return {}


def _household_wealth(conn: sqlite3.Connection) -> Dict[int, float]:
    try:
        return {hid: wealth or 0.0 for hid, wealth in conn.execute("SELECT id, wealth FROM households").fetchall()}
    except sqlite3.OperationalError:  # test fixtures without households or wealth
        return {}


def _load_resident_identity(conn: sqlite3.Connection, graph: SocialGraph) -> None:
    # TownShape identity fields (household, home, workplace, birth date);
    # test fixtures lack some columns, so this is best-effort. No randomness.
    try:
        rows = conn.execute(
            "SELECT id, household_id, home_building_id, workplace_building_id, birth_date FROM residents"
        ).fetchall()
    except sqlite3.OperationalError:
        return
    for resident_id, household_id, home_building_id, workplace_building_id, birth_date in rows:
        node = graph.nodes.get(resident_id)
        if node is not None:
            node.household_id, node.home_building_id = household_id, home_building_id
            node.workplace_building_id, node.birth_date = workplace_building_id, birth_date


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
        graph.add_edge(shop_edge(graph, customer_id, staff_id, _clamp01(customer_score / max_customer_score),
                                 _clamp01(purchase_count / max_purchase_count), bool(is_primary), rng))


def shop_edge(graph: SocialGraph, customer_id: int, staff_id: int, time: float, services: float,
              is_primary: bool, rng: random.Random) -> Edge:
    """A customer's tie to a shop's staff member: time and services from how
    much they buy there, fresh intimacy and feelings. Used by import and when
    a resident comes of age (PopulationPhenomenon)."""
    intimacy = _clamp01(rng.gauss(0.10, 0.08))
    valence_mean = 0.15 if is_primary else 0.0
    # drawn independently: the customer's opinion of the staff member need not match the reverse
    valence_a_to_b = _clamp_signed(rng.gauss(valence_mean, 0.30))
    valence_b_to_a = _clamp_signed(rng.gauss(valence_mean, 0.30))
    edge = Edge(
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
    _apply_noble_poor_skew(graph, edge)
    return edge


def _mark_same_sex_spouses(graph: SocialGraph) -> None:
    """TownShape draws each spouse's sex independently (about half its
    couples are same-sex); both partners of an imported same-sex couple are
    drawn to their own sex, so a widow(er) looks for the same again."""
    for edge in graph.edges.values():
        a, b = graph.nodes[edge.resident_a], graph.nodes[edge.resident_b]
        if edge.source_type == "spouse" and a.gender is not None and a.gender == b.gender:
            a.same_sex_attracted = b.same_sex_attracted = True


OFFSPRING_MAX_AGE = 29


def reshape_to_settled_town(graph: SocialGraph, seed: int) -> None:
    """The adapted importer (user, 2026-09-27): TownShape's town, buildings,
    households, jobs and ties kept as they are, but reshaped into the
    population the sim itself settles into, so a run doesn't open with years
    of adjustment (a dip in population and marriages).
    - Ages are re-drawn household by household from the settled age
      structure (demography.settled_age_weights) instead of TownShape's
      0.97^age curve, which gave 20% under-5s. Children stay children and
      adults stay adults, but a child may become an adult son or daughter
      still at home (up to 29); children are drawn first, then a first adult
      18-45 years older than each of them, and a second adult close in age
      to the first (so a second parent can fall a little outside 18-45).
    - TownShape draws each spouse's sex independently (about half its
      couples same-sex); just enough of them keep it for same-sex couples
      to be params.same_sex_share of all couples, the rest become mixed-sex.
    Upstream into TownShape's own generator later
    (docs/townshape-integration.md). Its own random stream, so every other
    import draw is unchanged."""
    rng = random.Random(f"reshape-{seed}")
    weights = settled_age_weights()

    def draw(lo: int, hi: int) -> int:
        lo, hi = max(0, lo), min(MAX_AGE, hi)
        if lo >= hi:
            return max(0, lo)
        return rng.choices(range(lo, hi + 1), weights=weights[lo:hi + 1])[0]

    spouses = [e for e in graph.edges.values() if e.source_type == "spouse"]
    same_sex = [e for e in spouses if graph.nodes[e.resident_a].gender is not None
                and graph.nodes[e.resident_a].gender == graph.nodes[e.resident_b].gender]
    if same_sex:
        keep = min(1.0, graph.params.same_sex_share * len(spouses) / len(same_sex))
        for edge in same_sex:
            if rng.random() >= keep:
                partner = graph.nodes[edge.resident_b]
                # ponytail: TownShape's first name stays as drawn for the old sex
                partner.gender = "male" if partner.gender == "female" else "female"

    households: Dict[Any, List[Node]] = defaultdict(list)
    for node in graph.nodes.values():
        if node.age is not None:
            households[node.household_id if node.household_id is not None else ("alone", node.resident_id)].append(node)
    for key in sorted(households, key=str):
        members = sorted(households[key], key=lambda n: n.resident_id)
        adults = [n for n in members if n.age >= 18]
        children = [n for n in members if n.age < 18]
        # children first, so the town's child ages follow the settled shape;
        # then a first adult 18-45 years older than every child. TownShape
        # makes 57% of the town children (2.2 a household); read as
        # offspring living at home, aged up to 29, about a third are young
        # adults, which brings children near the settled ~40%. They keep
        # TownShape's child record (no job) for now.
        for child in children:
            child.age = draw(0, OFFSPRING_MAX_AGE)
        if children:
            first = draw(max(child.age for child in children) + 18, min(child.age for child in children) + 45)
        else:
            first = draw(18, MAX_AGE)
        for index, adult in enumerate(adults):
            adult.age = first if index == 0 else min(MAX_AGE, max(18, first + round(rng.gauss(0, 4))))
        # TownShape children made adults here have a child's ties (no shops):
        # they buy where their household does, as if they had just come of age
        for child in children:
            if child.age >= 18:
                household_shop_ties(graph, child, rng)
        for node in members:
            if graph.reference_year is not None:
                node.birth_date = f"{graph.reference_year - node.age:04d}-01-01"


def household_shop_ties(graph: SocialGraph, node: Node, rng: random.Random, model: Optional[Node] = None) -> int:
    """TownShape gives shop ties to adults only; a resident coming of age
    starts buying where their household does: a tie to each shop staff member
    a living parent buys from (the parent's own buying pattern, fresh
    feelings). Used at 18 (PopulationPhenomenon) and by the importer for
    TownShape children it makes adults. `model`: whose shops to copy instead
    of a parent's (a lodger takes up their host's). Returns how many ties were added."""
    resident_id = node.resident_id
    parents = sorted(other for other in graph.neighbors(resident_id)
                     if graph.get_edge(resident_id, other).source_type == "parent"
                     and graph.nodes[other].alive and (graph.nodes[other].age or 0) > (node.age or 0))
    if model is None and not parents:
        return 0
    parent = model if model is not None else graph.nodes[parents[0]]
    added = 0
    for other in graph.neighbors(parent.resident_id):
        tie = graph.get_edge(parent.resident_id, other)
        staff = graph.nodes[other]
        if tie.source_type != "shopkeeper_customer" or not staff.alive or other == resident_id:
            continue
        # the parent is the customer, not the staff member serving customers
        if staff.workplace_building_id is None or staff.workplace_building_id == parent.workplace_building_id:
            continue
        if graph.get_edge(resident_id, other) is None:
            graph.add_edge(shop_edge(graph, resident_id, other, tie.time, tie.services, False, rng))
            added += 1
    return added


def import_snapshot(db_path: str, seed: int, overrides: Optional[Dict[str, float]] = None,
                    reshape: bool = True) -> SocialGraph:
    """overrides: TownParameters fields to set instead of the snapshot's own
    or the defaults (e.g. {"loyalty": 0.8}); applied before residents are
    drawn, so trait averages follow them."""
    rng = random.Random(seed)
    graph = SocialGraph()
    # read-only: a snapshot is never written to, and a mistyped path must fail
    # loudly instead of silently creating an empty .db
    conn = sqlite3.connect(f"file:{Path(db_path).resolve().as_posix()}?mode=ro", uri=True)
    try:
        reference_year = _load_town_state(conn, graph)
        for name, value in (overrides or {}).items():
            if not hasattr(graph.params, name):
                raise ValueError(f"unknown town parameter: {name}")
            setattr(graph.params, name, value)
        _load_residents(conn, graph, rng, reference_year)
        _load_relationships(conn, graph, rng)
        _load_shopkeeper_customer(conn, graph, rng)
        _load_resident_identity(conn, graph)
        if reshape:
            reshape_to_settled_town(graph, seed)
            # TownShape has no friendships: warm ties both ways are ones
            for edge in graph.edges.values():
                if (edge.source_type not in ("spouse", "parent", "sibling")
                        and min(edge.valence_a_to_b, edge.valence_b_to_a) >= FRIEND_WARMTH):
                    befriend(edge)
        _mark_same_sex_spouses(graph)
        _load_districts(conn, graph)
        if reshape:
            from economy import setup_economy  # imported here: economy reads graph objects, not the module
            setup_economy(graph, _building_types(conn), _household_wealth(conn), seed)
    finally:
        conn.close()
    return graph
