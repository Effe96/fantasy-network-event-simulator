import random
import sqlite3
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


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
    # TownShape home district (resident -> home building -> district) and
    # that district's zone_type, e.g. "poor_residential". None when the
    # snapshot has no buildings/districts (test fixtures).
    district_id: Optional[int] = None
    district_zone: Optional[str] = None

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


class SocialGraph:
    def __init__(self) -> None:
        self.nodes: Dict[int, Node] = {}
        self.edges: Dict[Tuple[int, int], Edge] = {}
        # TownShape's own town-wide generation dial (0..1, defaults to 0.0
        # meaning "no extra volatility" -- not "no violence at all"). Read
        # at import; a "guardrail" multiplier for phenomena to apply, not a
        # phenomenon itself.
        self.town_aggression: float = 0.0
        # No real TownShape data for this (checked town_state's own columns
        # and the wider source -- no governor/mayor/ruler concept exists to
        # import). A single town-wide fact, same shape as town_aggression,
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
        # resident -> neighbor ids, built lazily in edge order (the same order
        # the old full-scan neighbors() returned) and dropped on add_edge
        self._adjacency: Optional[Dict[int, List[int]]] = None

    def record_recovery(self, resident_id: int, day: int, cause: str) -> None:
        # the counterpart of record_death, for anything that reacts to
        # someone getting better (priests' curer gratitude)
        self.recoveries.append({"resident_id": resident_id, "day": day, "cause": cause})

    def record_death(self, resident_id: int, day: int, cause: str, killed_by: Optional[int] = None) -> None:
        self.nodes[resident_id].alive = False
        self.deaths.append({"resident_id": resident_id, "day": day, "cause": cause, "killed_by": killed_by})

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
        self._adjacency = None

    def get_edge(self, a: int, b: int) -> Optional[Edge]:
        return self.edges.get(self._key(a, b))

    def neighbors(self, resident_id: int) -> List[int]:
        if self._adjacency is None:
            adjacency: Dict[int, List[int]] = {}
            for a, b in self.edges:
                adjacency.setdefault(a, []).append(b)
                adjacency.setdefault(b, []).append(a)
            self._adjacency = adjacency
        return list(self._adjacency.get(resident_id, ()))

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


def synthesize_traits(rng: random.Random, family_baseline: Optional[Dict[str, float]] = None) -> Dict[str, float]:
    traits = {}
    for name in TRAIT_NAMES:
        if family_baseline is not None and name in FAMILY_CORRELATED_TRAITS:
            traits[name] = _clamp01(rng.gauss(family_baseline[name], FAMILY_TRAIT_STDEV))
        else:
            traits[name] = _clamp01(rng.gauss(0.5, 0.2))
    return traits


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
    if node_a.is_noble and not node_b.is_noble and node_b.ses == "poor":
        poor_id = node_b.resident_id
    elif node_b.is_noble and not node_a.is_noble and node_a.ses == "poor":
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
    family_of = _family_groups(conn)
    # each family's shared center is drawn once, the first time any of its
    # members is processed, keyed by family root id so every member of the
    # same family reuses the same center
    family_baselines: Dict[int, Dict[str, float]] = {}
    for resident_id, ses, gender, birth_date, occupation, is_noble in rows:
        age = _age_from_birth_date(birth_date, reference_year)
        family_root = family_of.get(resident_id, resident_id)
        if family_root not in family_baselines:
            family_baselines[family_root] = {
                name: _clamp01(rng.gauss(0.5, 0.2)) for name in FAMILY_CORRELATED_TRAITS
            }
        is_civilian = not is_noble and occupation not in _NON_CIVILIAN_OCCUPATIONS
        is_ex_soldier = is_civilian and rng.random() < EX_SOLDIER_BASE_RATE
        graph.add_node(
            Node(
                resident_id=resident_id, ses=ses, alive=True, gender=gender, age=age,
                occupation=occupation, is_noble=bool(is_noble), is_ex_soldier=is_ex_soldier,
                **synthesize_traits(rng, family_baselines[family_root]),
            )
        )


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
        attrs = synthesize_relationship_attributes(relationship_type, rng)
        edge = Edge(
            resident_a=resident_a_id,
            resident_b=resident_b_id,
            source_type=relationship_type,
            fiske_type=FISKE_TAGS[relationship_type],
            **attrs,
        )
        _apply_noble_poor_skew(graph, edge)
        graph.add_edge(edge)


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
        graph.town_aggression = aggression
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
        rows = conn.execute(
            "SELECT r.id, d.id, d.zone_type FROM residents r"
            " JOIN buildings b ON b.id = r.home_building_id"
            " JOIN districts d ON d.id = b.district_id"
        ).fetchall()
    except sqlite3.OperationalError:
        return
    for resident_id, district_id, zone_type in rows:
        node = graph.nodes.get(resident_id)
        if node is not None:
            node.district_id = district_id
            node.district_zone = zone_type


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
        time = _clamp01(customer_score / max_customer_score)
        services = _clamp01(purchase_count / max_purchase_count)
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
        graph.add_edge(edge)


def import_snapshot(db_path: str, seed: int) -> SocialGraph:
    rng = random.Random(seed)
    graph = SocialGraph()
    # read-only: a snapshot is never written to, and a mistyped path must fail
    # loudly instead of silently creating an empty .db
    conn = sqlite3.connect(f"file:{Path(db_path).resolve().as_posix()}?mode=ro", uri=True)
    try:
        reference_year = _load_town_state(conn, graph)
        _load_residents(conn, graph, rng, reference_year)
        _load_relationships(conn, graph, rng)
        _load_shopkeeper_customer(conn, graph, rng)
        _load_districts(conn, graph)
    finally:
        conn.close()
    return graph
