"""Goods slice 2: the crafts (crafts.py)."""
import random
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from crafts import EXPORT_PRICE, STOCK_MONTHS
from economy import COMMUNE, EconomyPhenomenon
from graph import Node, SocialGraph


def _town():
    """A tailor's workshop (building 50: master 1, hand 2), a weaver's (51: master 3),
    a household (4), a merchant (5)."""
    graph = SocialGraph()
    rows = [(1, "tailor", 50, 1), (2, "tailor_hand", 50, 1), (3, "weaver", 51, 3), (4, None, None, 4),
            (5, "merchant", None, 5)]
    for resident_id, occupation, workplace, household in rows:
        graph.add_node(Node(resident_id=resident_id, ses="middling", alive=True, gender="male", age=40,
                            household_id=household, occupation=occupation, workplace_building_id=workplace))
    graph.household_money = {1: 10.0, 3: 10.0, 4: 10.0, 5: 100.0, COMMUNE: 0.0}
    graph.household_property = {}
    economy = EconomyPhenomenon()
    economy.init_state(graph)
    alive = list(graph.nodes.values())
    return graph, economy, alive


def test_a_workshop_takes_its_materials_on_account_and_pays_from_its_takings():
    graph, economy, alive = _town()
    crafts = economy.crafts
    crafts.start_month(alive)
    nodes = graph.nodes
    crafts.produce(economy, graph, alive, [], [nodes[5]], random.Random(0), defaultdict(float))
    assert crafts.year["made cloth"] > 0 and crafts.year["made clothing"] > 0
    assert crafts.owed[51][("import", "cloth")] > 0 and crafts.owed[50][3] > 0  # wool from outside, cloth from the weaver
    crafts.settle(economy, graph, [nodes[5]], random.Random(0), defaultdict(float))
    assert crafts.owed[50][3] < 1e-9 and graph.household_money[3] > 10.0  # the tailor paid the weaver


def test_a_full_store_goes_to_the_merchants_for_export():
    graph, economy, alive = _town()
    crafts = economy.crafts
    crafts.start_month(alive)
    shops = crafts.workshops(alive)
    crafts.stock[50] = 5 * crafts.capacity(shops[50])
    total = sum(graph.household_money.values())
    crafts.produce(economy, graph, alive, [], [graph.nodes[5]], random.Random(0), defaultdict(float))
    assert abs(crafts.stock[50] - STOCK_MONTHS * crafts.capacity(shops[50])) < 1e-6
    assert crafts.year["exported clothing"] > 0
    assert sum(graph.household_money.values()) > total  # sold outside: money came into town


def test_a_household_buys_from_a_workshop_with_stock_else_imports():
    graph, economy, alive = _town()
    crafts = economy.crafts
    crafts.start_month(alive)  # the workshops start with a month's stock
    stock = crafts.stock[50]
    crafts.buy(economy, graph, 4, 1.0, alive, [graph.nodes[5]], random.Random(0), defaultdict(float))
    assert crafts.stock[50] < stock and graph.household_money[1] > 10.0  # clothing from the tailor
    crafts.stock[50] = 0.0
    crafts.buy(economy, graph, 4, 1.0, alive, [graph.nodes[5]], random.Random(0), defaultdict(float))
    assert crafts.year["imported clothing"] > 0


def test_where_the_town_wants_more_than_its_workshops_make_they_make_more():
    graph, economy, alive = _town()
    crafts = economy.crafts
    shops = crafts.workshops(alive)
    made = crafts.capacity(shops[50])
    crafts.calibrate(alive, {"clothing": 3 * made, "shoes": 0.0, "housewares": 0.0})
    assert abs(crafts.capacity(shops[50]) - 1.2 * 3 * made) < 1e-6


def test_a_good_dears_when_short_and_cheapens_in_a_glut_within_what_trade_allows():
    graph, economy, alive = _town()
    crafts = economy.crafts
    shops = crafts.workshops(alive)
    crafts._masters = {b: s["master"].household_id for b, s in shops.items()}
    crafts.stock[50] = 0.1 * crafts.capacity(shops[50])  # little clothing against a month's demand
    for _ in range(12):
        crafts._move_prices(shops, {"clothing": crafts.capacity(shops[50])})
    assert abs(crafts.price["clothing"] - (1 + crafts.import_margin)) < 1e-9  # capped at what imports cost
    crafts.stock[50] = 20 * crafts.capacity(shops[50])
    crafts._move_prices(shops, {"clothing": crafts.capacity(shops[50])})
    assert crafts.price["clothing"] < 1 + crafts.import_margin  # a glut: cheaper
    for _ in range(24):
        crafts._move_prices(shops, {"clothing": crafts.capacity(shops[50])})
    assert abs(crafts.price["clothing"] - EXPORT_PRICE) < 1e-9  # never below what export pays


def _run_all():
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
    print("OK")


if __name__ == "__main__":
    _run_all()
