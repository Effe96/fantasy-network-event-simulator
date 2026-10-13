import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from economy import (sync_parishes, CHURCH, COMMUNE, house_wealth, set_house_owner, DOWRY_SHARE, PRATO_1300_TOP1, EconomyPhenomenon, _decile_shares, class_for,
                     earner_key, form_household, gini, join_family, pass_on_merchant_house, settle_estate, setup_economy,
                     wealth)


def P(resident_id):
    """A resident's purse key (personal money, Project_Vision/09)."""
    return ("p", resident_id)
from graph import Edge, Node, SocialGraph


def test_starting_wealth_follows_the_prato_deciles():
    shares = _decile_shares(1000)
    assert abs(sum(shares) - 1.0) < 1e-9
    assert abs(sum(sorted(shares)[-10:]) - PRATO_1300_TOP1 / 100) < 1e-3  # the top 1% (book deciles sum to 99.99)
    assert gini([0.0] * 10 + [1.0] * 90) < gini(shares)


def _town():
    """Household 1: a rich couple (1, 2) and their married-off daughter's
    family lives in household 2 (3). Household 3: a poor jobless couple
    (4, 5). Building 50 is a workshop, 60 a farmstead. The husband holds the
    rich couple's money and land."""
    graph = SocialGraph()
    rows = [(1, "male", 60, 1), (2, "female", 55, 1), (3, "female", 30, 2), (4, "male", 25, 3), (5, "female", 25, 3)]
    for resident_id, gender, age, household in rows:
        graph.add_node(Node(resident_id=resident_id, ses="poor", alive=True, gender=gender, age=age,
                            household_id=household))
    graph.add_edge(Edge(1, 2, "spouse", "Communal Sharing", 0.7, 0.7, 0.7, 0.5, 0.5))
    graph.add_edge(Edge(1, 3, "parent", "Communal Sharing", 0.7, 0.7, 0.7, 0.5, 0.5))
    graph.add_edge(Edge(2, 3, "parent", "Communal Sharing", 0.7, 0.7, 0.7, 0.5, 0.5))
    graph.add_edge(Edge(4, 5, "spouse", "Communal Sharing", 0.7, 0.7, 0.7, 0.5, 0.5))
    graph.money = {P(1): 100.0}
    graph.land = {P(1): 900.0}
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


def test_after_a_year_the_class_lines_are_cut_again_from_real_earnings():
    graph = SocialGraph()
    for resident_id in range(1, 21):
        graph.add_node(Node(resident_id=resident_id, ses="poor", alive=True, gender="male", age=30,
                            household_id=resident_id))
    setup_economy(graph, {50: "workshop", 60: "farmstead"}, {1: 500.0}, seed=1)
    economy = EconomyPhenomenon()
    economy.init_state(graph)
    economy._income = {P(r): 0.1 * r for r in range(1, 21)}  # everyone earns less than expected
    expected_lines = list(graph.class_lines)
    economy._update_class(graph)
    assert graph.class_lines != expected_lines
    assert sum(1 for n in graph.nodes.values() if n.ses == "very_poor") == 3  # still 15% of the town
    lines = list(graph.class_lines)
    economy._update_class(graph)
    assert graph.class_lines == lines  # cut once; fixed from then on


def test_the_jobless_get_work_at_import():
    graph = SocialGraph()
    for resident_id in range(1, 21):
        graph.add_node(Node(resident_id=resident_id, ses="poor", alive=True, gender="male", age=30,
                            household_id=resident_id))
    setup_economy(graph, {50: "workshop", 60: "farmstead"}, {1: 500.0}, seed=1)
    assert all(n.occupation for n in graph.nodes.values())
    assert sum(1 for n in graph.nodes.values() if n.occupation == "merchant") >= 1
    assert sum(1 for n in graph.nodes.values() if n.workplace_building_id == 50) >= 4  # a master and hands


def test_newlyweds_set_up_a_household_and_the_bride_s_father_gives_her_a_dowry():
    graph = _town()
    graph.add_node(Node(resident_id=6, ses="poor", alive=True, gender="female", age=20, household_id=1))
    graph.add_node(Node(resident_id=7, ses="poor", alive=True, gender="male", age=24, household_id=4))
    graph.add_edge(Edge(1, 6, "parent", "Communal Sharing", 0.7, 0.7, 0.7, 0.5, 0.5))
    graph.add_edge(Edge(2, 6, "parent", "Communal Sharing", 0.7, 0.7, 0.7, 0.5, 0.5))
    form_household(graph, 6, 7)  # 6 (daughter of household 1) marries 7 (household 4)
    home = graph.nodes[6].household_id
    assert home == graph.nodes[7].household_id and home not in (1, 4)
    assert abs(wealth(graph, P(6)) - DOWRY_SHARE * 1000.0) < 1e-6  # hers, from her father's
    assert abs(wealth(graph, P(1)) - (1 - DOWRY_SHARE) * 1000.0) < 1e-6 and wealth(graph, P(7)) == 0.0


def test_children_inherit_and_the_widow_keeps_her_own_and_the_house_she_lives_in():
    graph = _town()
    graph.money[P(2)] = 30.0  # her dowry
    for resident_id in (1, 2):
        graph.nodes[resident_id].home_building_id = 10
    graph.houses, graph.house_wealth = {10: {"owner": None, "value": 120.0}}, {}
    set_house_owner(graph, 10, P(1))
    graph.record_death(1, day=1, cause="old age")
    assert settle_estate(graph, 1) == "split among children"
    assert abs(wealth(graph, P(3)) - 1000.0) < 1e-6  # the only child, living elsewhere
    assert graph.houses[10]["owner"] == P(2) and graph.money[P(2)] == 30.0


def test_with_no_children_the_spouse_inherits():
    graph = _town()
    graph.record_death(3, day=1, cause="flu")
    graph.record_death(1, day=2, cause="old age")
    assert settle_estate(graph, 1) == "spouse keeps it"
    assert wealth(graph, P(2)) == 1000.0


def test_someone_with_no_kin_leaves_their_estate_to_the_commune():
    graph = _town()
    graph.add_node(Node(resident_id=8, ses="poor", alive=True, gender="male", age=40, household_id=8))
    graph.money[P(8)] = 50.0
    graph.record_death(8, day=1, cause="flu")
    assert settle_estate(graph, 8) == "to the commune"
    assert wealth(graph, P(8)) == 0.0
    assert graph.money[COMMUNE] == 50.0  # kept in town, spent there


def test_the_commune_sells_land_to_whoever_can_pay_and_pays_the_guards():
    graph = _town()
    graph.record_death(1, day=1, cause="flu")
    graph.record_death(2, day=1, cause="flu")
    graph.record_death(3, day=1, cause="flu")
    graph.nodes[4].household_id = graph.nodes[5].household_id = 3
    settle_estate(graph, 1)  # 100 cash, 900 land, with no heir alive
    assert graph.commune_lots == [900.0]
    economy = EconomyPhenomenon()
    economy.init_state(graph)
    members = {3: [graph.nodes[4], graph.nodes[5]]}
    economy._sell_commune_land(graph, members)
    assert graph.land[COMMUNE] == 900.0  # nobody can pay: the commune keeps it
    graph.money[P(4)] = 1000.0
    economy._sell_commune_land(graph, members)
    assert graph.land[P(4)] == 900.0 and graph.money[COMMUNE] == 1000.0
    graph.nodes[4].occupation = "guard"
    economy._month(graph, random.Random(0))
    assert graph.money[COMMUNE] < 1000.0  # the guard's pay came from the commune


def _lenders_and_borrower():
    graph = _town()
    economy = EconomyPhenomenon()
    economy.init_state(graph)
    members = {1: [graph.nodes[1], graph.nodes[2]], 2: [graph.nodes[3]], 3: [graph.nodes[4], graph.nodes[5]]}
    return graph, economy, members, {1: 1.0, 2: 1.0, 3: 1.0}


def test_a_short_household_borrows_from_family_without_interest():
    graph, economy, members, needs = _lenders_and_borrower()
    economy._borrow(graph, 2, members[2], 5.0, needs, members, [])
    assert graph.money[P(3)] == 5.0 and graph.money[P(1)] == 95.0  # from her father's purse to hers
    assert [(d["debtor"], d["creditor"], d["kind"], d["rate"]) for d in graph.debts] == [(P(3), P(1), "family", 0.0)]


def test_nobody_lends_to_a_stranger_without_a_moneylender():
    graph, economy, members, needs = _lenders_and_borrower()
    economy._borrow(graph, 3, members[3], 5.0, needs, members, [])  # household 3 knows nobody
    assert graph.debts == [] and graph.money.get(P(4), 0.0) == 0.0


def test_a_debt_a_year_behind_cools_the_tie_and_costs_property():
    graph, economy, members, needs = _lenders_and_borrower()
    graph.land[P(3)] = 30.0
    graph.debts = [{"debtor": P(3), "creditor": P(1), "debtor_person": 3, "creditor_person": 1, "amount": 50.0,
                    "rate": 0.1, "kind": "patron", "behind": 0}]
    graph.get_edge(1, 3).valence_a_to_b = 0.0  # a creditor who doesn't care for them: no forgiving
    before = graph.get_edge(1, 3).valence_a_to_b
    for month in range(12):
        economy._repay_debts(graph, needs, members, random.Random(month))
    assert graph.land[P(3)] == 0.0 and graph.land[P(1)] == 930.0
    assert graph.get_edge(1, 3).valence_a_to_b < before
    assert 20.0 < graph.debts[0]["amount"] < 50.0  # grew with interest, then 30 seized


def test_a_creditor_who_cares_forgives_a_debt_behind():
    graph, economy, members, needs = _lenders_and_borrower()
    graph.debts = [{"debtor": P(3), "creditor": P(1), "debtor_person": 3, "creditor_person": 1, "amount": 50.0,
                    "rate": 0.0, "kind": "family", "behind": 0}]
    graph.get_edge(1, 3).valence_a_to_b = 0.9  # a loving father
    for month in range(60):
        economy._repay_debts(graph, needs, members, random.Random(month))
        if not graph.debts:
            break
    assert graph.debts == [] and month < 24 and graph.land.get(P(3), 0.0) == 0.0  # forgiven, nothing seized


def test_the_commune_repays_a_very_rich_lender_in_land():
    graph, economy, members, needs = _lenders_and_borrower()
    graph.nodes[1].ses = "very_rich"
    graph.land[COMMUNE] = 40.0
    graph.commune_lots = [40.0]
    graph.debts = [{"debtor": COMMUNE, "creditor": P(1), "debtor_person": None, "creditor_person": 1, "amount": 30.0,
                    "rate": 0.05, "kind": "forced loan", "behind": 0}]
    economy._repay_debts(graph, needs, members, random.Random(0))
    assert graph.debts == [] and graph.land[P(1)] == 930.0 and graph.commune_lots == [10.0]


def test_devout_middling_people_give_alms_and_the_poor_don_t():
    graph, economy, members, needs = _lenders_and_borrower()
    for resident_id, ses in ((1, "middling"), (2, "middling"), (4, "poor"), (5, "poor")):
        graph.nodes[resident_id].ses, graph.nodes[resident_id].religiousness = ses, 0.9
    economy._income = {P(1): 10.0, P(4): 10.0}
    economy._collect_alms(graph, members)
    assert graph.money[CHURCH] > 0 and graph.money[P(1)] < 100.0  # from the giver's own purse
    assert graph.money.get(P(4), 0.0) == 0.0


def test_a_commune_short_of_wages_borrows_from_the_richest():
    graph, economy, members, needs = _lenders_and_borrower()
    graph.money[P(1)] = 1000.0
    economy._commune_borrow(graph, 50.0, [n for n in graph.nodes.values() if n.alive])
    assert graph.money[COMMUNE] == 50.0 and graph.money[P(1)] == 950.0
    assert graph.debts[0]["debtor"] == COMMUNE and graph.debts[0]["kind"] == "forced loan"


def test_a_household_hungry_for_half_a_year_begs_and_people_it_knows_give():
    graph, economy, members, needs = _lenders_and_borrower()
    for _ in range(6):
        graph.hunger = {4: 0.5, 5: 0.5}
        economy._hardship(graph, members, random.Random(1), day=30)
    assert graph.nodes[4].beggar or graph.nodes[5].beggar
    graph.add_edge(Edge(1, 4, "neighbor", "Equality Matching", 0.8, 0.8, 0.3, 0.9, 0.9))
    graph.add_edge(Edge(1, 5, "neighbor", "Equality Matching", 0.8, 0.8, 0.3, 0.9, 0.9))
    graph.nodes[1].religiousness = 1.0
    for month in range(12):  # a devout neighbour who likes them gives, though not every month
        graph.hunger = {4: 0.5, 5: 0.5}
        economy._hardship(graph, members, random.Random(month), day=60)
    given = graph.money.get(P(4), 0.0) + graph.money.get(P(5), 0.0)
    assert 0 < given <= 12 * 0.02  # at most one small gift a month from them
    for _ in range(3):
        graph.hunger = {}
        economy._hardship(graph, members, random.Random(1), day=90)
    assert not graph.nodes[4].beggar and not graph.nodes[5].beggar  # fed again: they stop


def test_the_old_can_die_of_hardship_while_hungry():
    graph, economy, members, needs = _lenders_and_borrower()
    graph.nodes[1].age = 80
    for month in range(600):
        graph.hunger = {1: 1.0, 2: 1.0}
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
    set_house_owner(graph, 10, P(1))
    set_house_owner(graph, 11, P(1))
    return graph, economy, members, needs


def test_tenants_pay_rent_to_their_landlord():
    graph, economy, members, needs = _tenement()
    graph.money[P(4)] = 10.0
    economy._housing(graph, members, needs, __import__("collections").defaultdict(float), random.Random(0))
    rent_share = 120.0 * 0.07 * 30 / 365 * 2 / 4  # 2 of the 4 people in building 10
    assert abs(graph.money[P(4)] - (10.0 - rent_share)) < 1e-9
    assert house_wealth(graph, P(1)) == 180.0


def test_a_tenant_who_can_pay_buys_its_house():
    graph, economy, members, needs = _tenement()
    graph.money[P(3)] = 100.0  # the daughter, alone in building 11
    economy._housing(graph, members, needs, __import__("collections").defaultdict(float), random.Random(0))
    assert graph.houses[11]["owner"] == P(3) and graph.money[P(3)] == 40.0 and graph.money[P(1)] == 160.0


def test_a_landlord_living_in_the_house_is_not_bought_out():
    graph, economy, members, needs = _tenement()
    graph.money[P(4)] = 1000.0  # rich tenants sharing building 10 with its owner
    economy._housing(graph, members, needs, __import__("collections").defaultdict(float), random.Random(0))
    assert graph.houses[10]["owner"] == P(1)


def test_a_tenant_behind_on_rent_is_evicted_onto_the_street():
    graph, economy, members, needs = _tenement()
    for month in range(6):
        economy._housing(graph, members, needs, __import__("collections").defaultdict(float), random.Random(month))
    assert graph.nodes[4].home_building_id is None and graph.nodes[4].beggar  # nobody who likes them to go to


def test_the_evicted_move_in_with_family_who_like_them():
    graph, economy, members, needs = _tenement()
    graph.money[P(3)] = 10.0  # the sister pays her own rent (and can't buy)
    economy._income[P(3)] = 10.0  # and earns enough to feed them too
    graph.add_edge(Edge(4, 3, "sibling", "Communal Sharing", 0.7, 0.7, 0.7, 0.8, 0.8))
    for month in range(6):
        members = __import__("collections").defaultdict(list)
        for node in graph.nodes.values():
            members[node.household_id].append(node)
        economy._housing(graph, members, needs, __import__("collections").defaultdict(float), random.Random(month))
    assert graph.nodes[4].home_building_id == 11 and graph.nodes[4].household_id == graph.nodes[3].household_id


def test_a_crowded_town_builds_a_house_and_the_poorest_of_the_most_crowded_move_in():
    import economy as econ
    graph, economy, members, needs = _tenement()
    graph.houses[10]["room"], graph.houses[11]["room"] = 1, 1  # 4 people in a house for 1: crowded
    graph.money[P(4)] = 10.0
    total = sum(graph.money.values())
    room, econ.HOUSE_ROOM = econ.HOUSE_ROOM, 2  # 5 people, room for 2: one more house of 2
    try:
        economy._build_houses(graph, members, needs)
    finally:
        econ.HOUSE_ROOM = room
    (building, house), = [(b, h) for b, h in graph.houses.items() if h.get("built")]
    assert house["owner"] == P(1) and house["left"] == house["value"]  # the richest in cash builds
    assert abs(sum(graph.money.values()) - total) < 1e-9  # its cash is set aside for the builders
    economy._raise_houses(graph, house["value"])  # the builders are paid: finished
    assert "left" not in house
    economy._move_in(graph, needs)
    assert graph.nodes[4].home_building_id != building  # no usual income to pay the dearer rent: they stay
    economy._income[P(4)] = needs[3] + 1.0
    economy._move_in(graph, needs)
    assert graph.nodes[4].home_building_id == graph.nodes[5].home_building_id == building


def test_a_short_craft_opens_a_workshop_for_a_hand_on_a_patron_s_loan():
    import economy as econ
    graph, economy, members, needs = _lenders_and_borrower()
    graph.building_types = {}
    graph.nodes[3].occupation = "shoemaker_hand"  # household 2, no cash of its own
    graph.money[P(1)] = 500.0
    economy.crafts.shortfall = lambda alive: {"shoes": 1e6, "cloth": -1.0}
    alive = [n for n in graph.nodes.values() if n.alive]
    economy._open_workshops(graph, alive, members, needs, random.Random(0))
    master = graph.nodes[3]
    assert master.occupation == "shoemaker" and graph.building_types[master.workplace_building_id] == "workshop"
    assert [(d["debtor"], d["creditor"], d["kind"]) for d in graph.debts] == [(P(3), P(1), "patron")]
    assert graph.money[econ.BUILDERS] == econ.WORKSHOP_COST  # the cost pays builders
    for hand in (4, 5):  # the jobless are its hands
        assert graph.nodes[hand].occupation == "shoemaker_hand" and graph.employer[hand] == 3


def test_the_evicted_share_a_room_with_a_single_they_know_when_family_can_t_feed_them():
    graph, economy, members, needs = _tenement()
    graph.money[P(3)] = 10.0
    graph.add_node(Node(resident_id=7, ses="poor", alive=True, gender="male", age=30, household_id=9,
                        home_building_id=11))  # a single man renting in building 11
    graph.money[P(7)] = 10.0  # who pays his rent
    graph.add_edge(Edge(4, 7, "coworker", "Equality Matching", 0.5, 0.2, 0.3, 0.1, 0.1))
    for month in range(12):
        members = __import__("collections").defaultdict(list)
        for node in graph.nodes.values():
            members[node.household_id].append(node)
        economy._housing(graph, members, needs, __import__("collections").defaultdict(float), random.Random(month))
        if graph.nodes[4].household_id == graph.nodes[7].household_id:
            break
    assert graph.nodes[4].home_building_id == 11
    # roommates pay their own share of the rent (user, 2026-10-12): with
    # nothing to pay it, the couple is put out on their own, and he stays
    for month in range(12):
        members = __import__("collections").defaultdict(list)
        for node in graph.nodes.values():
            members[node.household_id].append(node)
        economy._housing(graph, members, needs, __import__("collections").defaultdict(float), random.Random(month))
    assert graph.nodes[4].household_id != graph.nodes[7].household_id and graph.nodes[7].home_building_id == 11


def test_homeless_people_who_know_each_other_pool_to_rent_a_room():
    graph, economy, members, needs = _tenement()
    graph.add_node(Node(resident_id=7, ses="poor", alive=True, gender="male", age=30, household_id=9))
    graph.add_node(Node(resident_id=8, ses="poor", alive=True, gender="male", age=30, household_id=10))
    graph.add_edge(Edge(7, 8, "friend", "Communal Sharing", 0.5, 0.5, 0.3, 0.5, 0.5))
    graph.money[P(7)] = graph.money[P(8)] = 0.6  # neither can pay a month alone
    economy._rehouse(graph, 9, [graph.nodes[7]], {9: 0.5, 10: 0.5}, random.Random(0))
    assert graph.nodes[7].household_id == graph.nodes[8].household_id
    assert graph.nodes[7].home_building_id is not None and graph.nodes[8].home_building_id is not None


def test_an_heirless_landlord_s_houses_go_to_the_commune():
    graph, economy, members, needs = _tenement()
    for resident_id in (1, 2, 3):
        graph.record_death(resident_id, day=1, cause="flu")
    settle_estate(graph, 1)
    assert graph.houses[10]["owner"] == COMMUNE and house_wealth(graph, COMMUNE) == 180.0


def test_a_household_buys_from_the_shop_it_knows():
    graph, economy, members, needs = _lenders_and_borrower()
    baker = Node(resident_id=20, ses="middling", alive=True, age=40, household_id=20, occupation="baker",
                 workplace_building_id=50)
    potter = Node(resident_id=21, ses="middling", alive=True, age=40, household_id=21, occupation="potter",
                  workplace_building_id=51)
    for node in (baker, potter):
        graph.add_node(node)
        graph.money[P(node.resident_id)] = 0.0
    graph.add_edge(Edge(4, 20, "shopkeeper_customer", "Market Pricing", 0.3, 0.1, 0.5, 0.0, 0.0))
    graph.money[P(4)] = 10.0
    members = {**members, 20: [baker], 21: [potter]}
    shops = economy._tied_shops(graph, members, [baker, potter])
    income = __import__("collections").defaultdict(float)
    for _ in range(20):
        economy._buy(graph, 3, 0.1, [baker, potter], random.Random(_), income, shops)
    # the potter is a workshop nobody is tied to: it still gets its share at random
    assert graph.money[P(21)] > 0.0 and graph.money[P(20)] > 0.0
    graph.add_edge(Edge(1, 21, "shopkeeper_customer", "Market Pricing", 0.3, 0.1, 0.5, 0.0, 0.0))
    graph.money[P(20)] = graph.money[P(21)] = 0.0
    shops = economy._tied_shops(graph, members, [baker, potter])
    for _ in range(20):
        economy._buy(graph, 3, 0.1, [baker, potter], random.Random(_), income, shops)
    assert graph.money[P(21)] == 0.0 and graph.money[P(20)] > 1.9  # a shop now: all to the one they know
    # shop ties with time 0 (some imported ones): buys as if untied, doesn't crash
    graph.get_edge(4, 20).time = graph.get_edge(1, 21).time = 0.0
    shops = economy._tied_shops(graph, members, [baker, potter])
    economy._buy(graph, 3, 0.1, [baker, potter], random.Random(0), income, shops)


def test_an_estate_pays_its_debts_before_the_heirs():
    graph = _town()
    graph.money[P(3)] = 50.0
    graph.debts = [{"debtor": P(3), "creditor": P(4), "debtor_person": 3, "creditor_person": 4, "amount": 20.0,
                    "rate": 0.0, "kind": "family", "behind": 0}]
    graph.record_death(3, day=1, cause="flu")
    settle_estate(graph, 3)
    assert graph.money[P(4)] == 20.0 and graph.debts == []


def test_with_no_children_spouse_or_parents_the_estate_goes_to_the_siblings():
    graph = _town()
    graph.add_edge(Edge(3, 4, "sibling", "Communal Sharing", 0.7, 0.7, 0.7, 0.5, 0.5))
    graph.money[P(3)] = 50.0
    graph.record_death(1, day=1, cause="flu")
    graph.record_death(2, day=1, cause="flu")
    graph.record_death(3, day=1, cause="flu")
    assert settle_estate(graph, 3) == "to siblings"
    assert wealth(graph, P(4)) == 50.0


def test_an_old_widow_left_alone_moves_in_with_her_daughter():
    graph = _town()
    graph.record_death(1, day=1, cause="old age")  # 2 (55) is left alone in household 1
    assert join_family(graph, 1) == "widowed to a child"
    assert graph.nodes[2].household_id == 2


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
    graph.money = {P(i): 5.0 for i in range(1, 201)}
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
    assert class_for(110.0, "middling", lines) == "middling"  # just over the next line: not yet rich
    assert class_for(130.0, "middling", lines) == "rich"  # clear of it by the same margin: risen


def test_a_farm_left_without_a_farmer_goes_to_its_eldest_hand_after_six_months():
    from economy import FARM_UNSTAFFED_MONTHS, _staff_farms
    graph = SocialGraph()
    for resident_id, age, occupation in [(1, 40, "farmhand"), (2, 50, "farmhand"), (3, 45, "merchant")]:
        graph.add_node(Node(resident_id=resident_id, ses="poor", alive=True, age=age, household_id=resident_id,
                            occupation=occupation, workplace_building_id=60 if occupation == "farmhand" else None))
    graph.employer = {1: 3, 2: 3}  # their farmer became a merchant house's heir
    alive, unstaffed = list(graph.nodes.values()), {}
    for _ in range(FARM_UNSTAFFED_MONTHS - 1):  # a newcomer might still come for a dead farmer's place
        _staff_farms(graph, alive, unstaffed)
    assert graph.nodes[2].occupation == "farmhand"
    _staff_farms(graph, alive, unstaffed)
    assert graph.nodes[2].occupation == "farmer" and graph.nodes[2].workplace_building_id == 60
    assert graph.employer == {1: 2}


def test_at_import_each_household_s_wealth_is_split_among_its_people_and_none_is_lost():
    import economy as econ
    graph = _town()
    graph.add_node(Node(resident_id=6, ses="poor", alive=True, gender="male", age=10, household_id=1))
    graph.add_node(Node(resident_id=7, ses="poor", alive=True, gender="male", age=20, household_id=1))
    for child in (6, 7):
        graph.add_edge(Edge(1, child, "parent", "Communal Sharing", 0.7, 0.7, 0.7, 0.5, 0.5))
    graph.money, graph.land = {1: 100.0, 3: 10.0, COMMUNE: 5.0}, {1: 900.0}  # per household, as TownShape gives it
    graph.houses, graph.house_wealth = {10: {"owner": None, "value": 120.0}}, {}
    set_house_owner(graph, 10, 1)
    total = sum(graph.money.values()) + sum(graph.land.values()) + sum(graph.house_wealth.values())
    econ._split_purses(graph)
    assert abs(sum(graph.money.values()) + sum(graph.land.values()) + sum(graph.house_wealth.values()) - total) < 1e-9
    assert graph.houses[10]["owner"] == P(1) and graph.land[P(1)] == 900.0 * 0.9  # the head: land and houses
    assert graph.money[P(2)] == 10.0 + 90.0 / 3 and graph.land[P(2)] == 90.0  # the wife: her dowry, and a share
    assert graph.money[P(7)] == 30.0 and P(6) not in graph.money  # cash among those of 16 and over, none for a child
    assert abs(graph.money[P(4)] - 4.5) < 1e-9 and abs(graph.money[P(5)] - 5.5) < 1e-9  # a poor couple too
    assert graph.money[COMMUNE] == 5.0


def test_a_child_s_wages_go_to_a_parent_until_sixteen():
    graph = _town()
    graph.add_node(Node(resident_id=6, ses="poor", alive=True, gender="male", age=13, household_id=3))
    graph.add_edge(Edge(4, 6, "parent", "Communal Sharing", 0.7, 0.7, 0.7, 0.5, 0.5))
    assert earner_key(graph, graph.nodes[6]) == P(4)
    graph.nodes[6].age = 16
    assert earner_key(graph, graph.nodes[6]) == P(6)


def test_a_family_pays_in_by_earnings_and_a_lodger_pays_their_share_whatever_they_earn():
    graph = _town()
    graph.add_node(Node(resident_id=8, ses="poor", alive=True, gender="male", age=30, household_id=3))  # a lodger
    economy = EconomyPhenomenon()
    economy.init_state(graph)
    graph.money.update({P(4): 30.0, P(5): 30.0, P(8): 1.0})
    economy._income = {P(4): 3.0, P(5): 1.0, P(8): 10.0}
    paid = economy._pay(graph, 3, COMMUNE, 6.0)  # food for three, a third each
    assert abs(graph.money[P(4)] - 27.0) < 1e-9 and abs(graph.money[P(5)] - 29.0) < 1e-9  # 3:1, as they earn
    assert graph.money[P(8)] == 0.0 and abs(paid - 5.0) < 1e-9  # the lodger's 2 fl: he had 1, nobody covers him


def test_belongings_wear_out_and_the_basket_buys_back_the_wear():
    graph = _town()
    setup_economy(graph, {50: "workshop"}, {1: 1000.0, 2: 0.0, 3: 0.0}, seed=1)
    economy = EconomyPhenomenon()
    economy.init_state(graph)
    before = dict(graph.belongings[4])
    economy._wear(graph, [graph.nodes[4]])
    assert graph.belongings[4]["clothing"] < before["clothing"] and graph.belongings[4]["weapon"] == before["weapon"]
    worn = before["clothing"] - graph.belongings[4]["clothing"]
    economy._members = {3: [graph.nodes[4], graph.nodes[5]]}
    wanted = {(rid, good): value for rid, good, value in economy._worn(graph, 3)}
    assert abs(wanted[(4, "clothing")] - worn) < 1e-9  # what an ordinary person wears out in a month


def test_a_quarantine_border_stops_buying_across_it():
    # Project_Vision/08 2.5 (user, 2026-10-12)
    graph, economy, members, needs = _lenders_and_borrower()
    baker = Node(resident_id=20, ses="middling", alive=True, age=40, household_id=20, occupation="baker",
                 workplace_building_id=50)
    potter = Node(resident_id=21, ses="middling", alive=True, age=40, household_id=21, occupation="potter",
                  workplace_building_id=51)
    for node in (baker, potter):
        graph.add_node(node)
        graph.money[P(node.resident_id)] = 0.0
    graph.nodes[4].home_building_id = graph.nodes[5].home_building_id = 30
    graph.building_districts.update({30: (1, "poor"), 50: (2, "merchant"), 51: (1, "merchant")})
    graph.add_edge(Edge(4, 20, "shopkeeper_customer", "Market Pricing", 0.3, 0.1, 0.5, 0.0, 0.0))
    graph.add_edge(Edge(1, 20, "shopkeeper_customer", "Market Pricing", 0.3, 0.1, 0.5, 0.0, 0.0))
    graph.money[P(4)] = 10.0
    economy._members = members = {**members, 20: [baker], 21: [potter]}
    shops = economy._tied_shops(graph, members, [baker, potter])
    graph.quarantined_districts[2] = "priest"  # the baker's shop is sealed off
    income = __import__("collections").defaultdict(float)
    for i in range(20):
        economy._buy(graph, 3, 0.1, [baker, potter], random.Random(i), income, shops)
    assert graph.money[P(20)] == 0.0 and graph.money[P(21)] > 1.9  # all to the potter on their side
    assert not economy.can_reach(graph, 3, 50) and economy.can_reach(graph, 3, 51)


def test_each_head_of_household_knows_the_priest_of_the_nearest_church():
    # Project_Vision/08 2.7 (user, 2026-10-13)
    graph = _town()  # households 1 (1, 2), 2 (3) and 3 (4, 5)
    for resident_id, job, church in [(10, "priest", 70), (11, "acolyte", 71)]:
        graph.add_node(Node(resident_id=resident_id, ses="middling", alive=True, gender="male", age=50,
                            occupation=job, workplace_building_id=church, household_id=resident_id))
    graph.building_types = {70: "temple", 71: "temple"}
    graph.building_xy.update({70: (0, 0), 71: (10, 0), 30: (1, 0), 31: (9, 0)})
    for resident_id, home in [(1, 30), (2, 30), (3, 30), (4, 31), (5, 31)]:
        graph.nodes[resident_id].home_building_id = home
    rng = random.Random(0)
    assert sync_parishes(graph, rng) == 3
    assert graph.get_edge(1, 10).source_type == "parishioner" and graph.get_edge(3, 10) is not None
    assert graph.get_edge(4, 11).source_type == "parishioner"  # no priest there: the acolyte
    assert graph.get_edge(2, 10) is None  # the head only
    graph.nodes[4].home_building_id = graph.nodes[5].home_building_id = 30  # they move near the other church
    sync_parishes(graph, rng)
    assert graph.get_edge(4, 10).source_type == "parishioner"
    assert graph.get_edge(4, 11).source_type == "acquaintance" and (4, 11) in graph.fading_friends


def _run_all():
    test_each_head_of_household_knows_the_priest_of_the_nearest_church()
    test_a_quarantine_border_stops_buying_across_it()
    test_at_import_each_household_s_wealth_is_split_among_its_people_and_none_is_lost()
    test_a_child_s_wages_go_to_a_parent_until_sixteen()
    test_a_family_pays_in_by_earnings_and_a_lodger_pays_their_share_whatever_they_earn()
    test_belongings_wear_out_and_the_basket_buys_back_the_wear()
    test_starting_wealth_follows_the_prato_deciles()
    test_the_jobless_get_work_at_import()
    test_after_a_year_the_class_lines_are_cut_again_from_real_earnings()
    test_a_dead_merchant_s_firm_passes_to_the_eldest_adult_at_home()
    test_teenagers_of_poor_households_spin_for_a_merchant()
    test_newlyweds_set_up_a_household_and_the_bride_s_father_gives_her_a_dowry()
    test_children_inherit_and_the_widow_keeps_her_own_and_the_house_she_lives_in()
    test_with_no_children_the_spouse_inherits()
    test_someone_with_no_kin_leaves_their_estate_to_the_commune()
    test_with_no_children_spouse_or_parents_the_estate_goes_to_the_siblings()
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
    test_a_crowded_town_builds_a_house_and_the_poorest_of_the_most_crowded_move_in()
    test_a_short_craft_opens_a_workshop_for_a_hand_on_a_patron_s_loan()
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
    test_a_farm_left_without_a_farmer_goes_to_its_eldest_hand_after_six_months()
    print("OK")


if __name__ == "__main__":
    _run_all()
