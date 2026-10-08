"""Goods slice 4: merchants in goods (merchants.py)."""
import random
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from economy import COMMUNE, GABELLE, EconomyPhenomenon
from graph import Node, SocialGraph
from merchants import COVER_MONTHS, EXPORT_MONTHS, LEAD_MONTHS


def _town():
    """Merchants 5 and 6, a household (4), a rich house (7) that could take up trade."""
    graph = SocialGraph()
    rows = [(4, None, 4, "middling"), (5, "merchant", 5, "rich"), (6, "merchant", 6, "rich"), (7, None, 7, "rich")]
    for resident_id, occupation, household, ses in rows:
        graph.add_node(Node(resident_id=resident_id, ses=ses, alive=True, gender="male", age=50,
                            household_id=household, occupation=occupation))
    graph.household_money = {4: 100.0, 5: 100.0, 6: 100.0, 7: 500.0, COMMUNE: 0.0}
    graph.household_property = {}
    economy = EconomyPhenomenon()
    economy.init_state(graph)
    merchants = [graph.nodes[5], graph.nodes[6]]
    return graph, economy, list(graph.nodes.values()), merchants


def _trading(graph, economy, alive, merchants, line="luxuries", sold=10.0):
    """The first month sold `sold` of `line`; the warehouses open."""
    trade = economy.trade
    trade.sell(economy, graph, 4, line, sold, merchants, random.Random(0), defaultdict(float))
    trade.order(economy, graph, alive, {}, economy.food, {}, random.Random(0))
    return trade


def test_the_first_month_buys_from_outside_then_the_warehouses_open_stocked():
    graph, economy, alive, merchants = _town()
    trade = _trading(graph, economy, alive, merchants)
    assert trade.trading and set(trade.line) == {5, 6}
    assert "luxuries" in trade.line.values()
    dealer = next(m for m, l in trade.line.items() if l == "luxuries")
    assert abs(trade.stock[dealer] - COVER_MONTHS * 10.0) < 1e-6
    assert sum(1 for c in trade.afloat if c[1] == dealer) == LEAD_MONTHS["luxuries"]


def test_a_sale_pays_the_gabelle_and_the_merchant_and_sets_aside_the_cost():
    graph, economy, alive, merchants = _town()
    trade = _trading(graph, economy, alive, merchants)
    dealer = next(m for m, l in trade.line.items() if l == "luxuries")
    before = {k: graph.household_money[k] for k in (4, dealer, COMMUNE)}
    spent = trade.sell(economy, graph, 4, "luxuries", 5.0, merchants, random.Random(0), defaultdict(float))
    assert abs(spent - 5.0) < 1e-9
    assert abs(graph.household_money[COMMUNE] - before[COMMUNE] - 5.0 * GABELLE) < 1e-9
    assert abs(graph.household_money[dealer] - before[dealer] - 5.0 * (1 - GABELLE)) < 1e-9
    assert trade.committed[dealer] > 0


def test_a_line_out_of_stock_goes_without():
    graph, economy, alive, merchants = _town()
    trade = _trading(graph, economy, alive, merchants)
    for merchant in trade.line:
        trade.stock[merchant] = 0.0
    money = graph.household_money[4]
    spent = trade.sell(economy, graph, 4, "luxuries", 5.0, merchants, random.Random(0), defaultdict(float))
    assert spent == 0.0 and graph.household_money[4] == money and trade.year["short luxuries"] == 5.0


def test_an_order_is_paid_up_front_and_lands_after_its_months_at_sea():
    graph, economy, alive, merchants = _town()
    trade = _trading(graph, economy, alive, merchants)
    dealer = next(m for m, l in trade.line.items() if l == "luxuries")
    trade.sell(economy, graph, 4, "luxuries", 8.0, merchants, random.Random(0), defaultdict(float))
    trade.afloat = []
    cash = graph.household_money[dealer]
    trade.order(economy, graph, alive, {}, economy.food, {}, random.Random(0))
    assert graph.household_money[dealer] < cash  # paid outside
    (due, _, units, _), = trade.afloat
    assert due == trade.month + LEAD_MONTHS["luxuries"]
    stock = trade.stock[dealer]
    for _ in range(LEAD_MONTHS["luxuries"]):
        trade.start_month(economy, graph, alive, economy.food, random.Random(1), defaultdict(float))
    assert abs(trade.stock[dealer] - stock - units) < 1e-6


def test_exports_take_the_merchants_cash_and_pay_when_they_sell_outside():
    graph, economy, alive, merchants = _town()
    trade = _trading(graph, economy, alive, merchants, line="cloth")
    dealer = next(m for m, l in trade.line.items() if l == "cloth")
    trade.exports = []
    bought = trade.export(economy, graph, 4, "clothing", 20.0, merchants, random.Random(0), defaultdict(float))
    assert bought > 0 and len(trade.exports) == 1
    cash = graph.household_money[dealer]
    for _ in range(EXPORT_MONTHS):
        trade.start_month(economy, graph, alive, economy.food, random.Random(1), defaultdict(float))
    assert abs(graph.household_money[dealer] - cash - bought) < 1e-6  # sold at the normal price


def test_a_failed_correspondent_ruins_a_house_and_the_richest_takes_up_its_line():
    graph, economy, alive, merchants = _town()
    trade = _trading(graph, economy, alive, merchants)
    dealer = next(m for m, l in trade.line.items() if l == "luxuries")
    trade.stock[dealer] = 0.0
    graph.household_money[dealer] = 0.0

    class Unlucky(random.Random):
        def random(self):
            return 0.0  # every cargo lost, every correspondent fails
    trade.start_month(economy, graph, alive, economy.food, Unlucky(), defaultdict(float))
    assert trade.year["houses ruined"] >= 1
    assert graph.nodes[dealer].occupation is None
    assert graph.nodes[7].occupation == "merchant" and trade.line[7] == "luxuries"


def _run_all():
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
    print("OK")


if __name__ == "__main__":
    _run_all()
