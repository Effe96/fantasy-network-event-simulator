"""Goods slice 1: the food chain (food.py)."""
import random
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from economy import COMMUNE, EconomyPhenomenon
from food import BAKER_MARGIN, HOARD_RESENTMENT
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


def _run_all():
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
    print("OK")


if __name__ == "__main__":
    _run_all()
