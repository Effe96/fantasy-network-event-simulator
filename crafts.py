"""The crafts (goods slice 2, Project_Vision/04 §7, user 2026-10-01).

Workshops make goods from inputs: weavers, fullers and dyers make cloth
from imported wool; tailors make clothing from cloth; tanners make leather
from the farmers' hides; shoemakers make shoes from leather; carpenters,
coopers, the potter and the blacksmith make housewares from timber, clay
and iron. Households buy clothing, shoes and housewares from the workshops
that have them in stock; what none has is imported (the money leaves town).

Every workshop works at capacity: it pays its people whether or not the
town buys. What it makes beyond a month's stock goes to the merchants, who
export it, as Florence exported its cloth and leather. Goods are counted in
florins' worth at their fixed price (prices start moving in slice 3).
"""
import random
from collections import defaultdict
from typing import Any, Dict, List

# trade -> (good, input, the input's share of the good's value, where the input comes from)
CRAFTS = {
    "weaver": ("cloth", "wool", 0.3, "import"),  # 0.3: economy.RAW_WOOL_SHARE
    "fuller": ("cloth", "wool", 0.3, "import"),
    "dyer": ("cloth", "wool", 0.3, "import"),
    "tanner": ("leather", "hides", 0.5, "farmers"),  # C
    "tailor": ("clothing", "cloth", 0.5, "cloth"),  # C
    "shoemaker": ("shoes", "leather", 0.4, "leather"),  # C
    "carpenter": ("housewares", "timber", 0.3, "import"),  # C
    "cooper": ("housewares", "timber", 0.3, "import"),
    "blacksmith": ("housewares", "iron", 0.3, "import"),
    "potter": ("housewares", None, 0.0, None),  # clay dug outside the walls
}
# of the whole basket, what households buy from the crafts (user, 2026-10-01; C, from
# typical pre-industrial budgets): the rest of what isn't grain or rent goes to shops and taverns
BASKET_SHARES = {"clothing": 0.06, "shoes": 0.02, "housewares": 0.05}
WAGE_COVER = 1.3  # C: a workshop selling all it makes at the local price covers its people's wages this many times
STOCK_MONTHS = 1.0  # C: a workshop keeps about a month of what it makes; the rest goes for export
CAPACITY_SLACK = 1.2  # C: at import each good's workshops can make this times what the town buys (equilibrium)
CREDIT_MONTHS = 2.0  # C: a workshop takes materials on account up to this many months of them
EXPORT_PRICE = 0.85  # C: merchants pay this share of the local price for goods to export


class CraftMarket:
    def __init__(self, wage: float, import_margin: float):
        self.wage = wage  # a worker's yearly wage (economy.UNSKILLED_WAGE)
        self.import_margin = import_margin
        self.stock: Dict[Any, float] = defaultdict(float)  # workshop (building) -> fl worth of its good
        self.seeded = set()  # workshops given their month of stock at import
        self.year: Dict[str, float] = defaultdict(float)
        self._shops = None  # this month's workshops, set by start_month
        self.output: Dict[str, float] = {}  # good -> times the wage-based output a worker makes, set at import
        self.wanted: Dict[str, float] = defaultdict(float)  # fl households asked for this month, by good
        self.owed: Dict[Any, Dict[Any, float]] = defaultdict(lambda: defaultdict(float))  # workshop -> creditor -> fl
        self._masters: Dict[Any, Any] = {}  # workshop -> its master's household, this month

    # -- workshops ------------------------------------------------------------

    def workshops(self, alive) -> Dict[Any, dict]:
        """Workshop building -> its trade, master and staff count."""
        shops: Dict[Any, dict] = {}
        for node in alive:
            trade = node.occupation[:-5] if node.occupation and node.occupation.endswith("_hand") else node.occupation
            trade = "blacksmith" if trade == "smith_apprentice" else trade  # TownShape's smithy staff
            if trade not in CRAFTS or node.workplace_building_id is None:
                continue
            shop = shops.setdefault(node.workplace_building_id, {"trade": trade, "master": None, "staff": 0})
            shop["staff"] += 1
            if node.occupation == trade:
                shop["master"] = node
        return {b: s for b, s in shops.items() if s["master"] is not None}

    def capacity(self, shop) -> float:
        """Fl worth a workshop makes in a month: enough, sold locally, to cover
        its wages WAGE_COVER times, or more where the town needs it (calibrate)."""
        good, _, input_share, _ = CRAFTS[shop["trade"]]
        return shop["staff"] * WAGE_COVER * self.wage / 12 / (1 - input_share) * self.output.get(good, 1.0)

    def calibrate(self, alive, monthly: Dict[str, float]) -> None:
        """Once, after the first month: where a good's workshops can't make CAPACITY_SLACK
        times what households asked for that month (`monthly`, fl), each worker makes
        more (a town that has stood for decades makes what it wears). Cloth and
        leather are sized for what the tailors and shoemakers then use.
        2026-10-01: wage-based output alone left clothing and housewares short,
        ~1,100 fl a year of goods imported."""
        if self.output or not any(monthly.values()):
            return  # done, or no month of demand seen yet
        shops = self.workshops(alive)
        demand = dict(monthly)
        for good in ("clothing", "shoes", "housewares", "cloth", "leather"):
            if good in ("cloth", "leather"):
                demand[good] = sum(self.capacity(s) * CRAFTS[s["trade"]][2] for s in shops.values()
                                   if CRAFTS[s["trade"]][3] == good)
            made = sum(self.capacity(s) for s in shops.values() if CRAFTS[s["trade"]][0] == good)
            if made > 0:
                self.output[good] = max(1.0, CAPACITY_SLACK * demand.get(good, 0.0) / made)
        self.output.setdefault("calibrated", 1.0)

    # -- the month ------------------------------------------------------------

    def produce(self, econ, graph, alive, farmers, merchants, rng: random.Random, income) -> None:
        """Each workshop makes what it can, taking its materials on credit
        (Florence's merchants advanced wool; tanners sold on account): cloth
        and leather first, then the trades that use them, and only then the
        surplus beyond a month's stock goes to the merchants for export.
        2026-10-01: paying for materials up front from the master's household
        purse left the workshops short (shoes made 92 fl of 870 in a year)."""
        from economy import household_key
        self.calibrate(alive, self.wanted)
        self.wanted = defaultdict(float)
        shops = self.workshops(alive)
        self._masters = {b: household_key(s["master"]) for b, s in shops.items()}
        uses_town_goods = lambda b: CRAFTS[shops[b]["trade"]][3] in ("cloth", "leather")
        for building in sorted(shops, key=lambda b: (uses_town_goods(b), str(b))):
            shop = shops[building]
            good, _, share, source = CRAFTS[shop["trade"]]
            cap = self.capacity(shop)
            made = cap
            if share > 0:
                credit = CREDIT_MONTHS * cap * share - sum(self.owed[building].values())
                made = self._draw_input(building, source, min(cap * share, max(0.0, credit)), shops, farmers,
                                        rng) / share
            self.stock[building] += made
            self.year[f"made {good}"] += made
        for building in sorted(shops, key=str):
            extra = self.stock[building] - STOCK_MONTHS * self.capacity(shops[building])
            if extra > 1e-9 and merchants:
                self._export(econ, graph, self._masters[building], building, CRAFTS[shops[building]["trade"]][0],
                             extra, merchants, rng, income)

    def _draw_input(self, building, source, value: float, shops, farmers, rng) -> float:
        """Take `value` fl of materials on account: cloth or leather from the
        town's workshops, hides from a farmer, the rest imported through the
        merchants (at their margin). Returns what was taken."""
        from economy import household_key
        got = 0.0
        if source in ("cloth", "leather"):
            makers = [b for b, s in shops.items() if CRAFTS[s["trade"]][0] == source and self.stock[b] > 1e-9]
            rng.shuffle(makers)
            for maker in makers:
                take = min(self.stock[maker], value - got)
                self.stock[maker] -= take
                self.owed[building][self._masters[maker]] += take
                got += take
                if got >= value - 1e-9:
                    break
        elif source == "farmers" and farmers:
            farmer = household_key(farmers[rng.randrange(len(farmers))])
            self.owed[building][farmer] += value
            got = value
        if got < value - 1e-9:  # wool, timber, iron, or what the town lacks
            self.owed[building]["import"] += (value - got) * (1 + self.import_margin)
            self.year[f"imported {source if source != 'import' else 'materials'}"] += value - got
            got = value
        return got

    def settle(self, econ, graph, merchants, rng: random.Random, income) -> None:
        """At the month's end each workshop pays what it owes for materials, as
        far as its takings allow; the rest stays on account (CREDIT_MONTHS caps it)."""
        for building, debts in self.owed.items():
            master = self._masters.get(building)
            if master is None:
                continue  # ponytail: a closed workshop's account is left unpaid
            for creditor in list(debts):
                cash = max(0.0, graph.household_money.get(master, 0.0))
                amount = min(debts[creditor], cash)
                if amount <= 1e-9:
                    continue
                if creditor == "import":
                    before = graph.household_money.get(master, 0.0)
                    econ._import(graph, master, amount, merchants, rng, income)
                    paid = before - graph.household_money.get(master, 0.0)
                else:
                    paid = econ._pay(graph, master, creditor, amount)
                    income[creditor] += paid
                income[master] -= paid
                debts[creditor] -= paid

    def _from_workshops(self, econ, graph, buyer, good, value: float, shops, rng, income, business=False) -> float:
        """Buy up to `value` fl of `good` from the workshops that have it, at the
        local price, taxed like anything bought in town. Returns what was bought."""
        from economy import household_key
        makers = [b for b, s in shops.items() if CRAFTS[s["trade"]][0] == good and self.stock[b] > 1e-9
                  and household_key(s["master"]) != buyer]
        rng.shuffle(makers)
        got = 0.0
        for building in makers:
            if got >= value - 1e-9:
                break
            seller = household_key(shops[building]["master"])
            want = min(self.stock[building], value - got)
            before = graph.household_money.get(buyer, 0.0)
            econ._buy(graph, buyer, want, [shops[building]["master"]], rng, income)
            paid = before - graph.household_money.get(buyer, 0.0)
            if business:
                income[buyer] -= paid
            self.stock[building] -= paid
            got += paid
            if paid < want - 1e-9:
                break  # the buyer ran out of money
        return got

    def _export(self, econ, graph, master, building, good, extra: float, merchants, rng, income) -> None:
        """A merchant buys the surplus at EXPORT_PRICE and sells it outside at the local price."""
        from economy import household_key
        merchant = household_key(merchants[rng.randrange(len(merchants))])
        paid = econ._pay(graph, merchant, master, extra * EXPORT_PRICE)
        income[master] += paid
        sold = paid / EXPORT_PRICE
        self.stock[building] -= sold
        sale = econ._pay(graph, None, merchant, sold)
        income[merchant] += sale - paid
        self.year[f"exported {good}"] += sold
        econ._year["in: craft exports"] += sale

    # -- households -------------------------------------------------------------

    def buy(self, econ, graph, key, amount: float, alive, merchants, rng: random.Random, income) -> float:
        """A household spends `amount` on clothing, shoes and housewares in the
        basket's proportions: from the workshops that have them, else imported,
        dearer. Returns what it spent."""
        shops = self._shops if self._shops is not None else self.workshops(alive)
        total = sum(BASKET_SHARES.values())
        spent = 0.0
        for good, share in BASKET_SHARES.items():
            want = amount * share / total
            self.wanted[good] += want
            got = self._from_workshops(econ, graph, key, good, want, shops, rng, income)
            spent += got
            if got < want - 1e-9 and merchants:  # none in town: imported, dearer
                before = graph.household_money.get(key, 0.0)
                econ._import(graph, key, min(want - got, max(0.0, before)), merchants, rng, income)
                spent += before - graph.household_money.get(key, 0.0)
                self.year[f"imported {good}"] += before - graph.household_money.get(key, 0.0)
        return spent

    def start_month(self, alive) -> None:
        self._shops = self.workshops(alive)
        for building, shop in self._shops.items():  # an imported town's workshops have their stock (equilibrium)
            if building not in self.seeded:
                self.seeded.add(building)
                if not self.output:  # at import; a workshop opened later starts empty
                    self.stock[building] = STOCK_MONTHS * self.capacity(shop)

    def summary(self) -> Dict[str, float]:
        by_good = defaultdict(float)
        for building, value in self.stock.items():
            shop = (self._shops or {}).get(building)
            if shop:
                by_good[CRAFTS[shop["trade"]][0]] += value
        return {**{f"crafts_stock_{g}": round(v, 1) for g, v in by_good.items()},
                **{f"crafts_{k}": round(v, 1) for k, v in self.year.items()}}
