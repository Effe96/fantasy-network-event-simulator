"""Goods slice 1: the food chain (food.py)."""
import random
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from economy import COMMUNE, EconomyPhenomenon
from food import BAKER_MARGIN, HARVEST_DAY, HOARD_RESENTMENT
from graph import Edge, Node, SocialGraph


def _town():
    """Household 1: a farmer. 2: a baker. 3: a poor couple. 4: a rich couple."""
    graph = SocialGraph()
    rows = [(1, "farmer", "middling", 1), (2, "baker", "middling", 2), (3, None, "poor", 3), (4, None, "poor", 3),
            (5, "merchant", "rich", 4), (6, None, "rich", 4)]
    for resident_id, occupation, ses, household in rows:
        graph.add_node(Node(resident_id=resident_id, ses=ses, alive=True, gender="male", age=40,
                            household_id=household, occupation=occupation))
    graph.household_money = {1: 0.0, 2: 0.0, 3: 10.0, 4: 100.0, COMMUNE: 0.0}
    graph.household_property = {}
    economy = EconomyPhenomenon()
    economy.init_state(graph)
    members = defaultdict(list)
    for node in graph.nodes.values():
        members[node.household_id].append(node)
    return graph, economy, members


def _harvest(graph, economy, members, seed=0):
    nodes = graph.nodes
    economy.food.harvest(economy, graph, members, [nodes[1]], [nodes[5]], random.Random(seed), defaultdict(float))


def test_a_harvest_fills_the_farmer_and_cheapens_grain_and_running_low_dears_it():
    graph, economy, members = _town()
    food = economy.food
    food.famine_chance = 0.0
    _harvest(graph, economy, members)
    assert food.year["harvested"] > 0
    monthly = sum(food.staia_needed(p) for k, p in members.items() if k != 4)  # the rich eat from their store
    food.farm_stock[1] = 8 * monthly
    for _ in range(12):
        food.update_price(members)
    assert food.price < 1.0  # stocks for eight months: cheap
    food.farm_stock.clear()
    for _ in range(12):
        food.update_price(members)
    assert abs(food.price - food.outside * (1 + food.import_margin)) < 0.01  # empty: at what imports cost


def test_the_rich_store_a_year_and_pay_only_the_baker_s_fee():
    graph, economy, members = _town()
    economy.food.famine_chance = 0.0
    _harvest(graph, economy, members)
    store = economy.food.stores[4]
    assert abs(store - economy.food.staia_needed(members[4]) * 12) < 1e-6
    bread = economy.food.grain_cost(3, members[3]) / economy.food.staia_needed(members[3])
    fee = economy.food.grain_cost(4, members[4]) / economy.food.staia_needed(members[4])
    assert abs(fee - bread * BAKER_MARGIN / (1 + BAKER_MARGIN)) < 1e-9


def test_bread_money_reaches_the_baker_and_the_farmer_and_none_is_lost():
    graph, economy, members = _town()
    economy.food.famine_chance = 0.0
    _harvest(graph, economy, members)
    economy.food.farm_stock[1] = stock = 100.0  # grain left at the farm (the rich bought this tiny town's harvest)
    total = sum(graph.household_money.values())
    cost = economy.food.grain_cost(3, members[3])
    nodes = graph.nodes
    eaten = economy.food.feed(economy, graph, 3, members[3], cost, [nodes[2]], [nodes[1]], [nodes[5]],
                              random.Random(0), defaultdict(float))
    assert abs(eaten - 1.0) < 1e-9
    assert graph.household_money[2] > 0  # the baker kept the margin
    assert economy.food.farm_stock[1] < stock  # and bought the grain from the farmer
    assert abs(sum(graph.household_money.values()) - total) < 1e-9


def test_in_a_famine_the_granary_sells_below_the_market():
    graph, economy, members = _town()
    food = economy.food
    food.price, food.granary = 2.2, 1000.0
    food.start_month(members)
    full = food.staio_fl * food.price * food.staia_needed(members[3])
    assert food.grain_cost(3, members[3]) < full


def test_a_hoarder_selling_dear_is_resented_by_the_hungry_who_know_them():
    graph, economy, members = _town()
    food = economy.food
    food.hoards[4] = 50.0
    food.price = 2.0
    graph.hunger_last = {3: 0.5}
    graph.add_edge(Edge(3, 5, "neighbor", "Equality Matching", 0.5, 0.5, 0.3, 0.2, 0.2))
    food.start_month(members)
    nodes = graph.nodes
    food.feed(economy, graph, 3, members[3], 5.0, [nodes[2]], [], [], random.Random(0), defaultdict(float))
    assert food.hoards[4] < 50.0 and graph.household_money[4] > 100.0  # sold to the baker, at a dear price
    assert abs(graph.get_edge(3, 5).valence_a_to_b - (0.2 - HOARD_RESENTMENT)) < 1e-9


def test_the_harvest_comes_once_a_year_in_summer_on_the_calendar():
    graph, economy, members = _town()
    food = economy.food
    food.famine_chance = 0.0
    nodes = graph.nodes
    harvests = []
    for day in range(30, 25 * 365, 30):  # 25 years of 30-day months
        before = food.year["harvested"]
        food.month(economy, graph, members, [nodes[1]], [nodes[5]], random.Random(day), defaultdict(float), day)
        if food.year["harvested"] > before:
            harvests.append(day)
    assert len(harvests) == 25
    assert all(HARVEST_DAY <= (day - 1) % 365 < HARVEST_DAY + 30 for day in harvests)  # no drift


def test_a_growing_town_gets_a_podere_whose_harvest_is_split_and_whose_land_stops_paying_rent():
    graph, economy, members = _town()
    food = economy.food
    food.famine_chance = 0.0
    for resident_id in (3, 4):
        graph.nodes[resident_id].ses, graph.nodes[resident_id].occupation = "very_poor", "day_labourer"
    graph.household_property = {4: 10_000.0}
    food.yield_per_farm, food.podere_yield = 1.0, 20.0  # the farm grows far less than the town's share
    _harvest(graph, economy, members)
    (building, podere), = food.poderi.items()  # one couple to work it, so one podere
    assert podere["owner"] == 4 and graph.building_types[building] == "podere"
    assert all(graph.nodes[r].occupation == "sharecropper" and graph.nodes[r].workplace_building_id == building
               for r in (3, 4))
    assert food.land_in_hand(4) == podere["value"]
    food.farm_stock.clear()
    food._crop(graph, building, podere, 1.0, members)
    assert food.farm_stock[3] == food.farm_stock[4] == 10.0  # mezzadria: half each
    # the owner's half of a normal harvest, at the normal price, replaces the rent on that land
    assert abs(10.0 * food.staio_fl / (1 + BAKER_MARGIN) - podere["value"] * 0.07) < 1e-9


def _run_all():
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
    print("OK")


if __name__ == "__main__":
    _run_all()
