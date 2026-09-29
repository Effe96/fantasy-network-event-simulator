import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from economy import (DOWRY_SHARE, PRATO_1300_TOP1, EconomyPhenomenon, _decile_shares, class_for, form_household, gini,
                     settle_estate, setup_economy, wealth)
from graph import Edge, Node, SocialGraph


def test_starting_wealth_follows_the_prato_deciles():
    shares = _decile_shares(1000)
    assert abs(sum(shares) - 1.0) < 1e-9
    assert abs(sum(sorted(shares)[-10:]) - PRATO_1300_TOP1 / 100) < 1e-3  # the top 1% (book deciles sum to 99.99)
    assert gini([0.0] * 10 + [1.0] * 90) < gini(shares)


def _town():
    """Household 1: a rich couple (1, 2) and their married-off daughter's
    family lives in household 2 (3). Household 3: two poor jobless adults
    (4, 5). Building 50 is a workshop, 60 a farmstead."""
    graph = SocialGraph()
    rows = [(1, "male", 60, 1), (2, "female", 55, 1), (3, "female", 30, 2), (4, "male", 25, 3), (5, "female", 25, 3)]
    for resident_id, gender, age, household in rows:
        graph.add_node(Node(resident_id=resident_id, ses="poor", alive=True, gender=gender, age=age,
                            household_id=household))
    graph.add_edge(Edge(1, 2, "spouse", "Communal Sharing", 0.7, 0.7, 0.7, 0.5, 0.5))
    graph.add_edge(Edge(1, 3, "parent", "Communal Sharing", 0.7, 0.7, 0.7, 0.5, 0.5))
    graph.add_edge(Edge(2, 3, "parent", "Communal Sharing", 0.7, 0.7, 0.7, 0.5, 0.5))
    graph.household_money = {1: 100.0, 2: 0.0, 3: 0.0}
    graph.household_property = {1: 900.0, 2: 0.0, 3: 0.0}
    return graph


def test_the_jobless_get_work_at_import():
    graph = SocialGraph()
    for resident_id in range(1, 21):
        graph.add_node(Node(resident_id=resident_id, ses="poor", alive=True, gender="male", age=30,
                            household_id=resident_id))
    setup_economy(graph, {50: "workshop", 60: "farmstead"}, {1: 500.0}, seed=1)
    assert all(n.occupation for n in graph.nodes.values())
    assert sum(1 for n in graph.nodes.values() if n.occupation == "merchant") >= 1
    assert sum(1 for n in graph.nodes.values() if n.workplace_building_id == 50) >= 4  # a master and hands


def test_newlyweds_set_up_a_household_with_the_bride_s_dowry():
    graph = _town()
    graph.add_node(Node(resident_id=6, ses="poor", alive=True, gender="female", age=20, household_id=1))
    before = wealth(graph, 1)
    form_household(graph, 6, 4)  # 6 (daughter of household 1) marries 4 (household 3)
    home = graph.nodes[6].household_id
    assert home == graph.nodes[4].household_id and home not in (1, 3)
    assert abs(wealth(graph, home) - DOWRY_SHARE * before) < 1e-6


def test_a_widow_keeps_the_estate():
    graph = _town()
    graph.record_death(1, day=1, cause="old age")
    assert settle_estate(graph, 1) == "spouse keeps it"
    assert wealth(graph, 1) == 1000.0


def test_with_no_spouse_the_estate_goes_to_all_children():
    graph = _town()
    graph.record_death(2, day=1, cause="old age")
    graph.record_death(1, day=2, cause="old age")
    assert settle_estate(graph, 1) == "split among children"
    assert abs(wealth(graph, 2) - 1000.0) < 1e-6  # the only child, living elsewhere


def test_a_household_left_with_nobody_goes_to_the_commune():
    graph = _town()
    graph.record_death(3, day=1, cause="flu")  # childless, alone in household 2
    graph.household_money[2] = 50.0
    assert settle_estate(graph, 3) == "to the commune"
    assert wealth(graph, 2) == 0.0


def test_the_month_pays_wages_and_feeds_people():
    graph = _town()
    setup_economy(graph, {50: "workshop"}, {1: 1000.0, 2: 0.0, 3: 0.0}, seed=1)
    economy = EconomyPhenomenon()
    state = economy.init_state(graph)
    for day in range(1, 91):
        economy.end_of_day(graph, state, day, random.Random(day))
    summary = economy.summarize(state)
    assert summary["economy_town_money"] > 0 and 0.0 <= summary["economy_gini"] <= 1.0


def test_adults_lose_and_find_work():
    graph = SocialGraph()
    for resident_id in range(1, 201):
        graph.add_node(Node(resident_id=resident_id, ses="poor", alive=True, gender="male", age=30,
                            household_id=resident_id, occupation="day_labourer"))
    graph.household_money = {i: 5.0 for i in range(1, 201)}
    economy = EconomyPhenomenon()
    state = economy.init_state(graph)
    counts = []
    for day in range(30, 30 * 25, 30):
        economy.end_of_day(graph, state, day, random.Random(day))
        counts.append(economy.summarize(state)["economy_unemployed"])
    assert max(counts) > 0  # some are out of work at times
    assert sum(counts[-12:]) / 12 < 30  # but it stays a small share (~5% of 200)


def test_five_classes_at_import_follow_the_town_s_shares():
    graph = SocialGraph()
    for resident_id in range(1, 101):
        graph.add_node(Node(resident_id=resident_id, ses="poor", alive=True, gender="male", age=30,
                            household_id=resident_id))
    setup_economy(graph, {}, {i: float(i * i) for i in range(1, 101)}, seed=1)
    counts = {c: sum(1 for n in graph.nodes.values() if n.ses == c)
              for c in ("very_poor", "poor", "middling", "rich", "very_rich")}
    assert counts == {"very_poor": 15, "poor": 50, "middling": 25, "rich": 9, "very_rich": 1}


def test_class_follows_resources_with_a_margin_before_dropping():
    lines = [10.0, 30.0, 100.0, 1000.0]
    assert class_for(5.0, "poor", lines) == "very_poor"  # well below the poor line
    assert class_for(29.0, "middling", lines) == "middling"  # just under its line: kept
    assert class_for(20.0, "middling", lines) == "poor"  # below 80% of it: dropped
    assert class_for(2000.0, "middling", lines) == "very_rich"


def _run_all():
    test_starting_wealth_follows_the_prato_deciles()
    test_the_jobless_get_work_at_import()
    test_newlyweds_set_up_a_household_with_the_bride_s_dowry()
    test_a_widow_keeps_the_estate()
    test_with_no_spouse_the_estate_goes_to_all_children()
    test_a_household_left_with_nobody_goes_to_the_commune()
    test_the_month_pays_wages_and_feeds_people()
    test_adults_lose_and_find_work()
    test_five_classes_at_import_follow_the_town_s_shares()
    test_class_follows_resources_with_a_margin_before_dropping()
    print("OK")


if __name__ == "__main__":
    _run_all()
