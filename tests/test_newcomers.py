# tests/test_newcomers.py -- residents added mid-run (pipeline step 3)
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from demo import build_phenomena
from engine import run_simulation
from graph import Edge, Node, SocialGraph
from phenomena import ContagionPhenomenon, PopulationPhenomenon, TheftPhenomenon


def _family_town():
    """Two parents (1, 2) and a neighbour (3), all at home building 10 in
    district 7; the parents are one family."""
    graph = SocialGraph()
    for resident_id, gender in [(1, "female"), (2, "male"), (3, "female")]:
        graph.add_node(Node(resident_id=resident_id, ses="poor", alive=True, gender=gender, age=30,
                            household_id=100, home_building_id=10, district_id=7, district_zone="poor_residential"))
    graph.add_edge(Edge(1, 2, "spouse", "Communal Sharing", 0.8, 0.8, 0.8, 0.5, 0.5))
    graph.add_edge(Edge(1, 3, "neighbor", "Equality Matching", 0.3, 0.2, 0.3, 0.0, 0.0))
    graph.building_districts = {10: (7, "poor_residential")}
    graph.family_root = {1: 1, 2: 1}
    graph.family_baselines = {1: {"religiousness": 0.9, "skepticism": 0.1}}
    graph.reference_year = 1300
    return graph


def _baby_row():
    # shaped like a TownShape `residents` row, as vital_records' births produce
    return {"ses": "poor", "gender": "male", "birth_date": "1300-01-01", "occupation": None, "is_noble": 0,
            "household_id": 100, "home_building_id": 10, "workplace_building_id": None}


def test_a_newcomer_is_built_like_an_imported_resident():
    graph = _family_town()
    baby = graph.add_resident(_baby_row(), [(1, "parent"), (2, "parent")], random.Random(0))
    assert baby == 4 == graph.next_resident_id() - 1
    node = graph.nodes[baby]
    assert node.age == 0 and node.household_id == 100
    assert (node.district_id, node.district_zone) == (7, "poor_residential")  # from the home building
    assert graph.family_root[baby] == 1  # inherits the parents' family...
    assert 0.5 < node.religiousness  # ...and lands near its centre (0.9), not the town's 0.5
    assert graph.get_edge(baby, 1).source_type == "parent" and graph.get_edge(baby, 2) is not None
    assert graph.get_edge(baby, 3) is None  # only the ties it was given
    assert graph.newcomers == [baby]


def test_an_existing_id_is_rejected():
    graph = _family_town()
    try:
        graph.add_resident(dict(_baby_row(), id=2), [], random.Random(0))
    except ValueError:
        return
    raise AssertionError("expected a ValueError")


class _BirthOnDay:
    """A minimal phenomenon that adds a baby on a given day."""
    name = "births"

    def __init__(self, day):
        self.day, self.baby = day, None

    def init_state(self, graph):
        return {rid: None for rid in graph.nodes}

    def edge_probability(self, edge, state_a, state_b, day):
        return 0.0

    def apply_effect(self, graph, state, a, b, day, rng):
        return []

    def end_of_day(self, graph, state, day, rng):
        if day == self.day:
            self.baby = graph.add_resident(_baby_row(), [(1, "parent"), (2, "parent")], rng)
        return []

    def summarize(self, state):
        return {}

    def add_resident(self, graph, state, resident_id):
        state[resident_id] = None


def test_every_standard_phenomenon_takes_on_a_newcomer_mid_run():
    graph = _family_town()
    births = _BirthOnDay(day=2)
    phenomena = [births] + build_phenomena(graph, outbreak_chance=1.0)
    captured = {}
    run_simulation(graph, phenomena, days=30, seed=1,
                   on_day_end=lambda day, g, states: captured.update(states=states))
    for phenomenon in phenomena:
        assert births.baby in captured["states"][phenomenon.name], phenomenon.name


def test_a_newborn_can_catch_the_disease_from_a_parent():
    graph = _family_town()
    births = _BirthOnDay(day=1)
    contagion = ContagionPhenomenon(base_rate=1.0, infectious_days=10, patient_zero=1, case_fatality_rate=0.0)
    result = run_simulation(graph, [births, contagion], days=10, seed=0)
    assert any(e.kind == "infected" and e.resident_b == births.baby for e in result.events)


def test_a_phenomenon_without_add_resident_fails_loudly():
    graph = _family_town()
    phenomena = [_BirthOnDay(day=1), _Legacy()]
    try:
        run_simulation(graph, phenomena, days=2, seed=0)
    except TypeError as error:
        assert "_Legacy" in str(error)
        return
    raise AssertionError("expected a TypeError")


class _Legacy:
    name = "legacy"

    def init_state(self, graph):
        return {rid: None for rid in graph.nodes}

    def edge_probability(self, edge, state_a, state_b, day):
        return 0.0

    def apply_effect(self, graph, state, a, b, day, rng):
        return []

    def end_of_day(self, graph, state, day, rng):
        return []

    def summarize(self, state):
        return {}


def _guard_post():
    """Guards 1 and 2 are coworkers; 3 is a civilian neighbour of guard 1."""
    graph = SocialGraph()
    for resident_id, occupation in [(1, "guard"), (2, "guard"), (3, None)]:
        graph.add_node(Node(resident_id=resident_id, ses="middling", alive=True, gender="male", age=30,
                            occupation=occupation, home_building_id=10, workplace_building_id=20))
    graph.add_edge(Edge(1, 2, "coworker", "Authority Ranking", 0.5, 0.2, 0.4, 0.0, 0.0))
    graph.add_edge(Edge(1, 3, "neighbor", "Equality Matching", 0.3, 0.2, 0.3, 0.0, 0.0))
    return graph


def test_a_dead_guard_is_replaced_by_an_arrival_who_takes_over_the_post():
    graph = _guard_post()
    population = PopulationPhenomenon(arrival_daily_chance=1.0)
    state = population.init_state(graph)
    graph.record_death(1, day=1, cause="riot")
    events = population.end_of_day(graph, state, day=1, rng=random.Random(0))
    newcomer = graph.nodes[events[0].resident_a]
    assert events[0].kind == "arrived" and events[0].resident_b == 1
    assert newcomer.role == "guard" and newcomer.workplace_building_id == 20 and 18 <= newcomer.age <= 35
    assert graph.get_edge(newcomer.resident_id, 2).source_type == "coworker"
    assert graph.get_edge(newcomer.resident_id, 3).source_type == "neighbor"


def test_a_civilian_place_stays_open_while_the_town_is_at_full_size():
    graph = _guard_post()
    graph.nodes[3].workplace_building_id = None  # jobless: replaced only below the target
    population = PopulationPhenomenon(arrival_daily_chance=1.0, annual_growth=0.0)
    state = population.init_state(graph)
    graph.record_death(3, day=1, cause="flu")
    graph.add_node(Node(resident_id=4, ses="poor", alive=True, age=0))  # a birth made up the loss
    assert population.end_of_day(graph, state, day=1, rng=random.Random(0)) == []
    graph.record_death(4, day=2, cause="diarrhea")  # now one short: the old place is filled
    assert [e.resident_b for e in population.end_of_day(graph, state, day=2, rng=random.Random(0))] == [3]


def test_a_job_is_refilled_even_when_the_town_is_at_full_size():
    graph = _guard_post()  # civilian 3 works at building 20
    population = PopulationPhenomenon(arrival_daily_chance=1.0, annual_growth=0.0)
    state = population.init_state(graph)
    graph.record_death(3, day=1, cause="flu")
    graph.add_node(Node(resident_id=4, ses="poor", alive=True, age=0))  # a birth made up the loss
    events = population.end_of_day(graph, state, day=1, rng=random.Random(0))
    assert [e.resident_b for e in events if e.kind == "arrived"] == [3]
    assert graph.nodes[events[0].resident_a].workplace_building_id == 20


def test_the_town_may_grow_past_its_starting_size():
    graph = _guard_post()
    population = PopulationPhenomenon(arrival_daily_chance=1.0, annual_growth=0.5)
    state = population.init_state(graph)
    graph.record_death(3, day=365, cause="flu")
    graph.add_node(Node(resident_id=4, ses="poor", alive=True, age=0))  # back at 3, target now 4.5
    events = population.end_of_day(graph, state, day=365, rng=random.Random(0))
    assert [e.resident_b for e in events] == [3]


def test_everyone_ages_at_the_year_end():
    graph = _guard_post()
    population = PopulationPhenomenon()
    state = population.init_state(graph)
    population.end_of_day(graph, state, day=364, rng=random.Random(0))
    assert graph.nodes[1].age == 30
    population.end_of_day(graph, state, day=365, rng=random.Random(0))
    assert graph.nodes[1].age == 31


def test_a_dead_noble_s_eldest_child_inherits_and_no_stranger_arrives():
    graph = SocialGraph()
    graph.add_node(Node(resident_id=1, ses="rich", alive=True, gender="male", age=50, is_noble=True, household_id=7))
    for resident_id, age, household in [(2, 20, 7), (3, 25, 8), (4, 12, 7)]:  # 3 has moved out
        graph.add_node(Node(resident_id=resident_id, ses="rich", alive=True, gender="male", age=age, household_id=household))
        graph.add_edge(Edge(1, resident_id, "parent", "Communal Sharing", 0.7, 0.7, 0.7, 0.4, 0.4))
    population = PopulationPhenomenon(arrival_daily_chance=1.0)
    state = population.init_state(graph)
    graph.record_death(1, day=1, cause="assassination")
    events = population.end_of_day(graph, state, day=1, rng=random.Random(0))
    assert [(event.kind, event.resident_a) for event in events] == [("inherited", 2)]
    assert graph.nodes[2].role == "noble" and not graph.nodes[3].is_noble


def test_with_no_children_a_sibling_then_a_nephew_takes_the_title():
    graph = SocialGraph()
    graph.add_node(Node(resident_id=1, ses="rich", alive=True, gender="male", age=60, is_noble=True, household_id=7))
    graph.add_node(Node(resident_id=2, ses="rich", alive=True, gender="female", age=55, household_id=8))  # sister
    graph.add_node(Node(resident_id=3, ses="rich", alive=True, gender="male", age=30, household_id=9))  # her son
    graph.add_edge(Edge(1, 2, "sibling", "Communal Sharing", 0.6, 0.6, 0.6, 0.3, 0.3))
    graph.add_edge(Edge(2, 3, "parent", "Communal Sharing", 0.7, 0.7, 0.7, 0.4, 0.4))
    population = PopulationPhenomenon(arrival_daily_chance=0.0)
    state = population.init_state(graph)
    graph.record_death(1, day=1, cause="old age")
    events = population.end_of_day(graph, state, day=1, rng=random.Random(0))
    assert [(e.kind, e.resident_a) for e in events] == [("inherited", 2)] and graph.nodes[2].household_id == 7
    graph.record_death(2, day=2, cause="old age")  # the sister dies too: her son, the nephew... of 1
    graph.nodes[2].is_noble = True
    events = population.end_of_day(graph, state, day=2, rng=random.Random(0))
    assert [(e.kind, e.resident_a) for e in events] == [("inherited", 3)]


def test_a_small_child_never_turns_thief():
    graph = _guard_post()
    graph.add_node(Node(resident_id=4, ses="poor", alive=True, age=3, stress=1.0))
    graph.nodes[3].stress = 1.0
    theft = TheftPhenomenon(become_thief_rate=1.0)
    state = theft.init_state(graph)
    theft.end_of_day(graph, state, day=1, rng=random.Random(0))
    assert state[3]["is_thief"] and not state[4]["is_thief"]


def _run_all():
    test_a_newcomer_is_built_like_an_imported_resident()
    test_an_existing_id_is_rejected()
    test_every_standard_phenomenon_takes_on_a_newcomer_mid_run()
    test_a_newborn_can_catch_the_disease_from_a_parent()
    test_a_phenomenon_without_add_resident_fails_loudly()
    test_a_dead_guard_is_replaced_by_an_arrival_who_takes_over_the_post()
    test_a_civilian_place_stays_open_while_the_town_is_at_full_size()
    test_a_job_is_refilled_even_when_the_town_is_at_full_size()
    test_the_town_may_grow_past_its_starting_size()
    test_everyone_ages_at_the_year_end()
    test_a_dead_noble_s_eldest_child_inherits_and_no_stranger_arrives()
    test_with_no_children_a_sibling_then_a_nephew_takes_the_title()
    test_a_small_child_never_turns_thief()
    print("OK")


if __name__ == "__main__":
    _run_all()
