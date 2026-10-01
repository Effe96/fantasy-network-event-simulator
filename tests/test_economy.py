import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from economy import (CHURCH, COMMUNE, house_wealth, set_house_owner, DOWRY_SHARE, PRATO_1300_TOP1, EconomyPhenomenon, _decile_shares, class_for,
                     form_household, gini, join_family, pass_on_merchant_house, settle_estate, setup_economy, wealth)
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


def test_teenagers_of_poor_households_spin_for_a_merchant():
    graph = SocialGraph()
    for resident_id in range(1, 21):
        graph.add_node(Node(resident_id=resident_id, ses="poor", alive=True, gender="male", age=30,
                            household_id=resident_id))
    graph.add_node(Node(resident_id=30, ses="poor", alive=True, gender="female", age=14, household_id=20))
    graph.add_node(Node(resident_id=31, ses="poor", alive=True, gender="female", age=9, household_id=20))
    setup_economy(graph, {50: "workshop", 60: "farmstead"}, {1: 500.0}, seed=2)
    assert graph.nodes[30].occupation == "outworker" and graph.nodes[31].occupation is None


def test_a_dead_merchant_s_firm_passes_to_the_eldest_adult_at_home():
    graph = _town()
    graph.nodes[1].occupation = "merchant"
    graph.nodes[2].occupation = "rentier"
    graph.employer = {}
    graph.nodes[1].alive = False
    assert pass_on_merchant_house(graph, 1) and graph.nodes[2].occupation == "merchant"
    graph.nodes[2].alive = False  # no adult left at home: the adult daughter elsewhere takes it
    assert pass_on_merchant_house(graph, 2) and graph.nodes[3].occupation == "merchant"


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
    assert graph.household_money[COMMUNE] == 50.0  # kept in town, spent there


def test_the_commune_sells_land_to_whoever_can_pay_and_pays_the_guards():
    graph = _town()
    graph.record_death(1, day=1, cause="flu")
    graph.record_death(2, day=1, cause="flu")
    graph.record_death(3, day=1, cause="flu")
    graph.nodes[4].household_id = graph.nodes[5].household_id = 3
    settle_estate(graph, 2)  # household 1 (100 cash, 900 land), with no heir alive
    assert graph.commune_lots == [900.0]
    economy = EconomyPhenomenon()
    economy.init_state(graph)
    economy._sell_commune_land(graph, [3])
    assert graph.household_property[COMMUNE] == 900.0  # household 3 can't pay: the commune keeps it
    graph.household_money[3] = 1000.0
    economy._sell_commune_land(graph, [3])
    assert graph.household_property[3] == 900.0 and graph.household_money[COMMUNE] == 1000.0
    graph.nodes[4].occupation = "guard"
    economy._month(graph, random.Random(0))
    assert graph.household_money[COMMUNE] < 1000.0  # the guard's pay came from the commune


def _lenders_and_borrower():
    graph = _town()
    economy = EconomyPhenomenon()
    economy.init_state(graph)
    members = {1: [graph.nodes[1], graph.nodes[2]], 2: [graph.nodes[3]], 3: [graph.nodes[4], graph.nodes[5]]}
    return graph, economy, members, {1: 1.0, 2: 1.0, 3: 1.0}


def test_a_short_household_borrows_from_family_without_interest():
    graph, economy, members, needs = _lenders_and_borrower()
    economy._borrow(graph, 2, members[2], 5.0, needs, members, [])
    assert graph.household_money[2] == 5.0 and graph.household_money[1] == 95.0
    assert [(d["creditor"], d["kind"], d["rate"]) for d in graph.debts] == [(1, "family", 0.0)]


def test_nobody_lends_to_a_stranger_without_a_moneylender():
    graph, economy, members, needs = _lenders_and_borrower()
    economy._borrow(graph, 3, members[3], 5.0, needs, members, [])  # household 3 knows nobody
    assert graph.debts == [] and graph.household_money[3] == 0.0


def test_a_debt_a_year_behind_cools_the_tie_and_costs_property():
    graph, economy, members, needs = _lenders_and_borrower()
    graph.household_property[2] = 30.0
    graph.debts = [{"debtor": 2, "creditor": 1, "debtor_person": 3, "creditor_person": 1, "amount": 50.0,
                    "rate": 0.1, "kind": "patron", "behind": 0}]
    graph.get_edge(1, 3).valence_a_to_b = 0.0  # a creditor who doesn't care for them: no forgiving
    before = graph.get_edge(1, 3).valence_a_to_b
    for month in range(12):
        economy._repay_debts(graph, needs, members, random.Random(month))
    assert graph.household_property[2] == 0.0 and graph.household_property[1] == 930.0
    assert graph.get_edge(1, 3).valence_a_to_b < before
    assert 20.0 < graph.debts[0]["amount"] < 50.0  # grew with interest, then 30 seized


def test_a_creditor_who_cares_forgives_a_debt_behind():
    graph, economy, members, needs = _lenders_and_borrower()
    graph.debts = [{"debtor": 2, "creditor": 1, "debtor_person": 3, "creditor_person": 1, "amount": 50.0,
                    "rate": 0.0, "kind": "family", "behind": 0}]
    graph.get_edge(1, 3).valence_a_to_b = 0.9  # a loving father
    for month in range(60):
        economy._repay_debts(graph, needs, members, random.Random(month))
        if not graph.debts:
            break
    assert graph.debts == [] and month < 24 and graph.household_property[2] == 0.0  # forgiven, nothing seized


def test_the_commune_repays_a_very_rich_lender_in_land():
    graph, economy, members, needs = _lenders_and_borrower()
    graph.nodes[1].ses = "very_rich"
    graph.household_property[COMMUNE] = 40.0
    graph.commune_lots = [40.0]
    graph.debts = [{"debtor": COMMUNE, "creditor": 1, "debtor_person": None, "creditor_person": 1, "amount": 30.0,
                    "rate": 0.05, "kind": "forced loan", "behind": 0}]
    economy._repay_debts(graph, needs, members, random.Random(0))
    assert graph.debts == [] and graph.household_property[1] == 930.0 and graph.commune_lots == [10.0]


def test_devout_middling_people_give_alms_and_the_poor_don_t():
    graph, economy, members, needs = _lenders_and_borrower()
    for resident_id, ses in ((1, "middling"), (2, "middling"), (4, "poor"), (5, "poor")):
        graph.nodes[resident_id].ses, graph.nodes[resident_id].religiousness = ses, 0.9
    economy._income = {1: 10.0, 3: 10.0}
    economy._collect_alms(graph, members)
    assert graph.household_money[CHURCH] > 0 and graph.household_money[1] < 100.0
    assert graph.household_money[3] == 0.0


def test_a_commune_short_of_wages_borrows_from_the_richest():
    graph, economy, members, needs = _lenders_and_borrower()
    graph.household_money[1] = 1000.0
    economy._commune_borrow(graph, 50.0, [n for n in graph.nodes.values() if n.alive])
    assert graph.household_money[COMMUNE] == 50.0 and graph.household_money[1] == 950.0
    assert graph.debts[0]["debtor"] == COMMUNE and graph.debts[0]["kind"] == "forced loan"


def test_a_household_hungry_for_half_a_year_begs_and_people_it_knows_give():
    graph, economy, members, needs = _lenders_and_borrower()
    graph.household_money[3] = 0.0
    for _ in range(6):
        graph.hunger = {3: 0.5}
        economy._hardship(graph, members, random.Random(1), day=30)
    assert graph.nodes[4].beggar or graph.nodes[5].beggar
    graph.add_edge(Edge(1, 4, "neighbor", "Equality Matching", 0.8, 0.8, 0.3, 0.9, 0.9))
    graph.add_edge(Edge(1, 5, "neighbor", "Equality Matching", 0.8, 0.8, 0.3, 0.9, 0.9))
    graph.nodes[1].religiousness = 1.0
    for month in range(12):  # a devout neighbour who likes them gives, though not every month
        graph.hunger = {3: 0.5}
        economy._hardship(graph, members, random.Random(month), day=60)
    assert 0 < graph.household_money[3] <= 12 * 0.02  # at most one small gift a month from them
    for _ in range(3):
        graph.hunger = {}
        economy._hardship(graph, members, random.Random(1), day=90)
    assert not graph.nodes[4].beggar and not graph.nodes[5].beggar  # fed again: they stop


def test_the_old_can_die_of_hardship_while_hungry():
    graph, economy, members, needs = _lenders_and_borrower()
    graph.nodes[1].age = 80
    for month in range(600):
        graph.hunger = {1: 1.0}
        economy._hardship(graph, members, random.Random(month), day=30 * month)
        if not graph.nodes[1].alive:
            break
    assert graph.deaths and graph.deaths[0]["cause"] == "hardship"


def _tenement():
    """Building 10: household 1 (1, 2) owns it; household 3 (4, 5) rents there.
    Building 11: household 2 (3, the daughter)."""
    graph, economy, members, needs = _lenders_and_borrower()
    for resident_id, building in ((1, 10), (2, 10), (4, 10), (5, 10), (3, 11)):
        graph.nodes[resident_id].home_building_id = building
    graph.houses, graph.house_wealth = {10: {"owner": None, "value": 120.0}, 11: {"owner": None, "value": 60.0}}, {}
    set_house_owner(graph, 10, 1)
    set_house_owner(graph, 11, 1)
    return graph, economy, members, needs


def test_tenants_pay_rent_to_their_landlord():
    graph, economy, members, needs = _tenement()
    graph.household_money[3] = 10.0
    economy._housing(graph, members, needs, __import__("collections").defaultdict(float), random.Random(0))
    rent_share = 120.0 * 0.07 * 30 / 365 * 2 / 4  # 2 of the 4 people in building 10
    assert abs(graph.household_money[3] - (10.0 - rent_share)) < 1e-9
    assert house_wealth(graph, 1) == 180.0


def test_a_tenant_who_can_pay_buys_its_house():
    graph, economy, members, needs = _tenement()
    graph.household_money[2] = 100.0  # the daughter's household, alone in building 11
    economy._housing(graph, members, needs, __import__("collections").defaultdict(float), random.Random(0))
    assert graph.houses[11]["owner"] == 2 and graph.household_money[2] == 40.0 and graph.household_money[1] == 160.0


def test_a_landlord_living_in_the_house_is_not_bought_out():
    graph, economy, members, needs = _tenement()
    graph.household_money[3] = 1000.0  # rich tenants sharing building 10 with its owner
    economy._housing(graph, members, needs, __import__("collections").defaultdict(float), random.Random(0))
    assert graph.houses[10]["owner"] == 1


def test_a_tenant_behind_on_rent_is_evicted_onto_the_street():
    graph, economy, members, needs = _tenement()
    graph.household_money[3] = 0.0
    for month in range(6):
        economy._housing(graph, members, needs, __import__("collections").defaultdict(float), random.Random(month))
    assert graph.nodes[4].home_building_id is None and graph.nodes[4].beggar  # nobody who likes them to go to


def test_the_evicted_move_in_with_family_who_like_them():
    graph, economy, members, needs = _tenement()
    graph.household_money[3] = 0.0
    graph.household_money[2] = 10.0  # the sister pays her own rent (and can't buy)
    economy._income[2] = 10.0  # and earns enough to feed them too
    graph.add_edge(Edge(4, 3, "sibling", "Communal Sharing", 0.7, 0.7, 0.7, 0.8, 0.8))
    for month in range(6):
        members = __import__("collections").defaultdict(list)
        for node in graph.nodes.values():
            members[node.household_id].append(node)
        economy._housing(graph, members, needs, __import__("collections").defaultdict(float), random.Random(month))
    assert graph.nodes[4].home_building_id == 11 and graph.nodes[4].household_id == graph.nodes[3].household_id


def test_the_evicted_share_a_room_with_a_single_they_know_when_family_can_t_feed_them():
    graph, economy, members, needs = _tenement()
    graph.household_money[3] = 0.0
    graph.household_money[2] = 10.0
    graph.add_node(Node(resident_id=7, ses="poor", alive=True, gender="male", age=30, household_id=9,
                        home_building_id=11))  # a single man renting in building 11
    graph.household_money[9] = 10.0  # who pays his rent
    graph.add_edge(Edge(4, 7, "coworker", "Equality Matching", 0.5, 0.2, 0.3, 0.1, 0.1))
    for month in range(6):
        members = __import__("collections").defaultdict(list)
        for node in graph.nodes.values():
            members[node.household_id].append(node)
        economy._housing(graph, members, needs, __import__("collections").defaultdict(float), random.Random(month))
    assert graph.nodes[4].household_id == graph.nodes[7].household_id and graph.nodes[4].home_building_id == 11


def test_homeless_people_who_know_each_other_pool_to_rent_a_room():
    graph, economy, members, needs = _tenement()
    graph.add_node(Node(resident_id=7, ses="poor", alive=True, gender="male", age=30, household_id=9))
    graph.add_node(Node(resident_id=8, ses="poor", alive=True, gender="male", age=30, household_id=10))
    graph.add_edge(Edge(7, 8, "friend", "Communal Sharing", 0.5, 0.5, 0.3, 0.5, 0.5))
    graph.household_money[9] = graph.household_money[10] = 0.6  # neither can pay a month alone
    economy._rehouse(graph, 9, [graph.nodes[7]], {9: 0.5, 10: 0.5}, random.Random(0))
    assert graph.nodes[7].household_id == graph.nodes[8].household_id
    assert graph.nodes[7].home_building_id is not None and graph.nodes[8].home_building_id is not None


def test_an_heirless_landlord_s_houses_go_to_the_commune():
    graph, economy, members, needs = _tenement()
    for resident_id in (1, 2, 3):
        graph.record_death(resident_id, day=1, cause="flu")
    settle_estate(graph, 2)
    assert graph.houses[10]["owner"] == COMMUNE and house_wealth(graph, COMMUNE) == 180.0


def test_a_household_buys_from_the_shop_it_knows():
    graph, economy, members, needs = _lenders_and_borrower()
    baker = Node(resident_id=20, ses="middling", alive=True, age=40, household_id=20, occupation="baker",
                 workplace_building_id=50)
    potter = Node(resident_id=21, ses="middling", alive=True, age=40, household_id=21, occupation="potter",
                  workplace_building_id=51)
    for node in (baker, potter):
        graph.add_node(node)
        graph.household_money[node.household_id] = 0.0
    graph.add_edge(Edge(4, 20, "shopkeeper_customer", "Market Pricing", 0.3, 0.1, 0.5, 0.0, 0.0))
    graph.household_money[3] = 10.0
    members = {**members, 20: [baker], 21: [potter]}
    shops = economy._tied_shops(graph, members, [baker, potter])
    income = __import__("collections").defaultdict(float)
    for _ in range(20):
        economy._buy(graph, 3, 0.1, [baker, potter], random.Random(_), income, shops)
    # the potter is a workshop nobody is tied to: it still gets its share at random
    assert graph.household_money[21] > 0.0 and graph.household_money[20] > 0.0
    graph.add_edge(Edge(1, 21, "shopkeeper_customer", "Market Pricing", 0.3, 0.1, 0.5, 0.0, 0.0))
    graph.household_money[20] = graph.household_money[21] = 0.0
    shops = economy._tied_shops(graph, members, [baker, potter])
    for _ in range(20):
        economy._buy(graph, 3, 0.1, [baker, potter], random.Random(_), income, shops)
    assert graph.household_money[21] == 0.0 and graph.household_money[20] > 1.9  # a shop now: all to the one they know


def test_an_estate_pays_its_debts_before_the_heirs():
    graph = _town()
    graph.household_money[2] = 50.0
    graph.debts = [{"debtor": 2, "creditor": 3, "debtor_person": 3, "creditor_person": 4, "amount": 20.0,
                    "rate": 0.0, "kind": "family", "behind": 0}]
    graph.record_death(3, day=1, cause="flu")
    settle_estate(graph, 3)
    assert graph.household_money[3] == 20.0 and graph.debts == []


def test_a_heirless_estate_goes_to_the_siblings():
    graph = _town()
    graph.add_edge(Edge(3, 4, "sibling", "Communal Sharing", 0.7, 0.7, 0.7, 0.5, 0.5))
    graph.household_money[2] = 50.0
    graph.record_death(3, day=1, cause="flu")
    assert settle_estate(graph, 3) == "to siblings"
    assert wealth(graph, 3) == 50.0


def test_an_old_widow_left_alone_moves_in_with_her_daughter():
    graph = _town()
    graph.record_death(1, day=1, cause="old age")  # 2 (55) is left alone in household 1
    assert join_family(graph, 1) == "widowed to a child"
    assert graph.nodes[2].household_id == 2 and wealth(graph, 2) == 1000.0


def test_orphans_go_to_their_grown_sibling():
    graph = _town()
    graph.add_node(Node(resident_id=6, ses="poor", alive=True, gender="male", age=10, household_id=1))
    graph.add_edge(Edge(3, 6, "sibling", "Communal Sharing", 0.7, 0.7, 0.7, 0.5, 0.5))
    graph.record_death(1, day=1, cause="flu")
    graph.record_death(2, day=1, cause="flu")
    assert join_family(graph, 2) == "orphans to family"
    assert graph.nodes[6].household_id == 2


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
    test_a_dead_merchant_s_firm_passes_to_the_eldest_adult_at_home()
    test_teenagers_of_poor_households_spin_for_a_merchant()
    test_newlyweds_set_up_a_household_with_the_bride_s_dowry()
    test_a_widow_keeps_the_estate()
    test_with_no_spouse_the_estate_goes_to_all_children()
    test_a_household_left_with_nobody_goes_to_the_commune()
    test_a_heirless_estate_goes_to_the_siblings()
    test_a_short_household_borrows_from_family_without_interest()
    test_nobody_lends_to_a_stranger_without_a_moneylender()
    test_a_debt_a_year_behind_cools_the_tie_and_costs_property()
    test_a_creditor_who_cares_forgives_a_debt_behind()
    test_the_commune_repays_a_very_rich_lender_in_land()
    test_devout_middling_people_give_alms_and_the_poor_don_t()
    test_a_commune_short_of_wages_borrows_from_the_richest()
    test_a_household_hungry_for_half_a_year_begs_and_people_it_knows_give()
    test_the_old_can_die_of_hardship_while_hungry()
    test_tenants_pay_rent_to_their_landlord()
    test_a_tenant_who_can_pay_buys_its_house()
    test_a_landlord_living_in_the_house_is_not_bought_out()
    test_a_tenant_behind_on_rent_is_evicted_onto_the_street()
    test_the_evicted_move_in_with_family_who_like_them()
    test_the_evicted_share_a_room_with_a_single_they_know_when_family_can_t_feed_them()
    test_homeless_people_who_know_each_other_pool_to_rent_a_room()
    test_an_heirless_landlord_s_houses_go_to_the_commune()
    test_a_household_buys_from_the_shop_it_knows()
    test_an_estate_pays_its_debts_before_the_heirs()
    test_the_commune_sells_land_to_whoever_can_pay_and_pays_the_guards()
    test_an_old_widow_left_alone_moves_in_with_her_daughter()
    test_orphans_go_to_their_grown_sibling()
    test_the_month_pays_wages_and_feeds_people()
    test_adults_lose_and_find_work()
    test_five_classes_at_import_follow_the_town_s_shares()
    test_class_follows_resources_with_a_margin_before_dropping()
    print("OK")


if __name__ == "__main__":
    _run_all()
