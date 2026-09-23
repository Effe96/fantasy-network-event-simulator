# tests/test_quarantine.py
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from graph import Edge, Node, SocialGraph
from phenomena import ContagionPhenomenon, QuarantinePhenomenon


class _FixedRng:
    def __init__(self, value):
        self.value = value

    def random(self):
        return self.value


def _node(resident_id, district, zone="merchant", ses="middling", **kwargs):
    return Node(resident_id=resident_id, ses=ses, alive=True, district_id=district, district_zone=zone, **kwargs)


def _edge(a, b, source_type="coworker", valence=0.0):
    return Edge(a, b, source_type, "Authority Ranking", 0.5, 0.5, 0.5, valence, valence)


def _kill(graph, resident_ids, day, cause="plague"):
    for resident_id in resident_ids:
        graph.add_node(graph.nodes.get(resident_id) or _node(resident_id, 1))
        graph.record_death(resident_id, day, cause)


# --- Contagion side: the effects ---

def test_sealed_boundary_leaks_at_a_tiny_rate_but_inside_ties_are_untouched():
    graph = SocialGraph()
    for resident_id, district in [(1, 1), (2, 1), (3, 2)]:
        graph.add_node(_node(resident_id, district))
    inside, crossing = _edge(1, 2), _edge(1, 3)
    graph.add_edge(inside)
    graph.add_edge(crossing)
    contagion = ContagionPhenomenon(base_rate=0.5, quarantine_leak_factor=0.02)
    contagion.init_state(graph)
    infected, susceptible = {"status": "infected"}, {"status": "susceptible"}
    open_inside = contagion.edge_probability(inside, infected, susceptible, 1)
    open_crossing = contagion.edge_probability(crossing, infected, susceptible, 1)

    graph.quarantined_districts[1] = "priest"
    assert contagion.edge_probability(inside, infected, susceptible, 1) == open_inside
    sealed_crossing = contagion.edge_probability(crossing, infected, susceptible, 1)
    assert 0 < sealed_crossing == open_crossing * 0.02


def test_sick_residents_sealed_inside_die_more_often():
    def outcome(sealed):
        graph = SocialGraph()
        graph.add_node(_node(1, 1))
        contagion = ContagionPhenomenon(infectious_days=1, patient_zero=1, case_fatality_rate=0.5,
                                        quarantined_fatality_multiplier=2.0)
        state = contagion.init_state(graph)
        if sealed:
            graph.quarantined_districts[1] = "priest"
        contagion.end_of_day(graph, state, day=1, rng=_FixedRng(0.7))  # 0.7: survives 0.5, not 1.0
        return state[1]["status"]

    assert outcome(sealed=False) == "recovered"
    assert outcome(sealed=True) == "deceased"


# --- QuarantinePhenomenon: who seals, when ---

def _town():
    """District 1 merchant, district 2 poor_residential, district 3 rich; a
    priest and a governor-noble, both living elsewhere (district 9)."""
    graph = SocialGraph()
    graph.add_node(_node(100, 9, occupation="priest"))
    graph.add_node(_node(200, 9, is_noble=True))
    graph.add_node(_node(201, 9, is_noble=True))
    graph.governor_id = 200
    for resident_id in range(1, 11):
        graph.add_node(_node(resident_id, 1))
    for resident_id in range(11, 21):
        graph.add_node(_node(resident_id, 2, zone="poor_residential", ses="poor"))
    for resident_id in range(21, 25):
        graph.add_node(_node(resident_id, 3, zone="rich_residential", ses="rich"))
    return graph


def test_priests_seal_after_three_deaths_but_poor_districts_need_six():
    graph = _town()
    quarantine = QuarantinePhenomenon(death_threshold=3, poor_death_threshold=6)
    quarantine.init_state(graph)
    _kill(graph, [1, 2, 3], day=5)          # 3 in the merchant district
    _kill(graph, [11, 12, 13, 14, 15], day=5)  # 5 in the poor district: not enough
    quarantine.end_of_day(graph, {}, 5, random.Random(0))
    assert graph.quarantined_districts == {1: "priest"}

    _kill(graph, [16], day=6)                # sixth poor death
    quarantine.end_of_day(graph, {}, 6, random.Random(0))
    assert graph.quarantined_districts == {1: "priest", 2: "priest"}


def test_flu_deaths_never_trigger_a_quarantine():
    graph = _town()
    quarantine = QuarantinePhenomenon(death_threshold=3, poor_death_threshold=6)
    quarantine.init_state(graph)
    _kill(graph, [1, 2, 3, 4], day=5, cause="flu")
    _kill(graph, [21], day=5, cause="diarrhea")  # a rich death, but not plague
    quarantine.end_of_day(graph, {}, 5, random.Random(0))
    assert graph.quarantined_districts == {}


def test_a_noble_dying_puts_nobles_in_charge_at_the_same_bar():
    graph = _town()
    quarantine = QuarantinePhenomenon(death_threshold=3, poor_death_threshold=6)
    quarantine.init_state(graph)
    _kill(graph, [1, 2, 3], day=5)  # merchant district reaches the bar
    _kill(graph, [11], day=5)       # one poor death -- below the bar, never sealed
    _kill(graph, [201], day=5)      # a noble dies
    quarantine.end_of_day(graph, {}, 5, random.Random(0))
    assert graph.quarantined_districts == {1: "noble"}


def test_a_rich_commoner_dying_does_not_alarm_the_nobles():
    graph = _town()
    graph.add_node(_node(30, 1, ses="rich"))  # a rich merchant, not a noble
    quarantine = QuarantinePhenomenon(death_threshold=3, poor_death_threshold=6)
    quarantine.init_state(graph)
    _kill(graph, [30, 1, 2], day=5)
    quarantine.end_of_day(graph, {}, 5, random.Random(0))
    assert graph.quarantined_districts == {1: "priest"}


def test_no_living_priest_means_no_priest_quarantine():
    graph = _town()
    graph.nodes[100].alive = False
    quarantine = QuarantinePhenomenon(death_threshold=3, poor_death_threshold=6)
    quarantine.init_state(graph)
    _kill(graph, [1, 2, 3], day=5)
    quarantine.end_of_day(graph, {}, 5, random.Random(0))
    assert graph.quarantined_districts == {}


def test_quarantine_lifts_after_a_quiet_stretch():
    graph = _town()
    quarantine = QuarantinePhenomenon(death_threshold=3, poor_death_threshold=6, release_days=14)
    quarantine.init_state(graph)
    _kill(graph, [1, 2, 3], day=5)
    quarantine.end_of_day(graph, {}, 5, random.Random(0))
    quarantine.end_of_day(graph, {}, 18, random.Random(0))
    assert 1 in graph.quarantined_districts   # 13 quiet days
    quarantine.end_of_day(graph, {}, 19, random.Random(0))
    assert graph.quarantined_districts == {}  # 14 quiet days
    assert quarantine.summarize({})["quarantines_lifted"] == 1


# --- anger ---

def test_priest_seal_angers_residents_inside_toward_priests_they_know():
    graph = _town()
    graph.add_edge(_edge(4, 100))  # inside resident knows the priest
    graph.add_edge(_edge(4, 200))  # ...and the governor
    quarantine = QuarantinePhenomenon(death_threshold=3, poor_death_threshold=6, anger_shock=0.1)
    quarantine.init_state(graph)
    _kill(graph, [1, 2, 3], day=5)
    quarantine.end_of_day(graph, {}, 5, random.Random(0))
    assert abs(graph.get_edge(4, 100).valence_from(4) - -0.1) < 1e-9
    assert graph.get_edge(4, 100).valence_from(100) == 0.0  # the priest's own feelings don't move
    assert graph.get_edge(4, 200).valence_from(4) == 0.0    # nobles didn't call it


def test_noble_seal_puts_most_of_the_anger_on_the_governor():
    graph = _town()
    graph.add_edge(_edge(22, 200))  # rich-district resident knows the governor
    graph.add_edge(_edge(22, 201))  # ...and another noble
    quarantine = QuarantinePhenomenon(death_threshold=3, poor_death_threshold=6, anger_shock=0.1, other_noble_anger_share=0.25)
    quarantine.init_state(graph)
    _kill(graph, [21, 23, 24], day=5)  # 3 deaths in the rich district
    quarantine.end_of_day(graph, {}, 5, random.Random(0))
    assert graph.quarantined_districts == {3: "noble"}
    assert abs(graph.get_edge(22, 200).valence_from(22) - -0.1) < 1e-9
    assert abs(graph.get_edge(22, 201).valence_from(22) - -0.025) < 1e-9


def _run_all():
    test_sealed_boundary_leaks_at_a_tiny_rate_but_inside_ties_are_untouched()
    test_sick_residents_sealed_inside_die_more_often()
    test_priests_seal_after_three_deaths_but_poor_districts_need_six()
    test_flu_deaths_never_trigger_a_quarantine()
    test_a_noble_dying_puts_nobles_in_charge_at_the_same_bar()
    test_a_rich_commoner_dying_does_not_alarm_the_nobles()
    test_no_living_priest_means_no_priest_quarantine()
    test_quarantine_lifts_after_a_quiet_stretch()
    test_priest_seal_angers_residents_inside_toward_priests_they_know()
    test_noble_seal_puts_most_of_the_anger_on_the_governor()
    print("OK")


if __name__ == "__main__":
    _run_all()
