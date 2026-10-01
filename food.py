"""The food chain (goods slice 1, Project_Vision/04 §6, user 2026-10-01).

Grain is a good, counted in staia (18 kg): farmers harvest once a year,
merchants import the rest, bakers bake it, households eat it. Its price
follows how many months the town's stocks cover. The rich store a year's
grain at harvest and hoard more in cheap years, selling it dear in famines;
the commune keeps a public granary and sells it below the market in famines.

Money stays conserved: every staio bought is paid to a farmer, a hoarder,
the commune, or (imports) a merchant and the outside world. In a normal year
a household pays what it paid before this slice: the book's 13 soldi a staio
is taken as the bread price, and the baker's margin comes out of it.
"""
import random
from collections import defaultdict
from typing import Any, Dict, List

STAIA_PER_PERSON_MONTH = 0.9 * 365 / 18 / 12  # book §5: 0.9 kg a day, 18 kg a staio (~1.52)
BAKER_MARGIN = 0.15  # C: the baker's share of the bread price
NORMAL_COVER_MONTHS = 4.0  # C: stocks covering this many months of demand sell at the normal price
PRICE_ELASTICITY = 0.3  # C: price ~ (normal cover / cover) ** this
PRICE_STEP = 0.5  # C: each month the price moves this share of the way to its target
GLUT_PRICE = 10 / 13  # book §6: ~10 soldi a staio after the best harvests of the 1330s
YIELD_RANGE = (0.8, 1.2)  # C: an ordinary harvest, times a normal one
FAMINE_YIELD = (0.4, 0.55)  # C: a famine harvest
OUTSIDE_RANGE = (0.8, 0.95)  # C: merchants' cost outside in an ordinary year; with their margin, imported
# grain sells near the book's 13 soldi (at 0.9-1.1 a normal year cost 12% more: local grain runs out by month 5)
STORE_CLASSES = ("rich", "very_rich")  # store a year's grain at harvest (user: only the rich)
GRANARY_MONTHS = 2.0  # C: the commune's granary holds this many months of the town's grain
GRANARY_BUY_BELOW = 1.0  # C: it buys after harvests priced at most this
GRANARY_PRICE_SHARE = 0.8  # C: in a famine it sells at this share of the market (1329: set below it)
HOARD_YEARS = 1.0  # C: a rich household hoards up to this many years of its own grain on top
HOARD_CASH_SHARE = 0.3  # C: spending at most this share of its cash on a hoard
HOARD_BUY_BELOW = 1.0  # C: buying after harvests priced at most this
HOARD_SELL_AT = 1.6  # C: and selling once the price reaches this
HOARD_RESENTMENT = 0.05  # C: a hungry person's feeling toward a hoarder they know drops this, a month it sells


class FoodMarket:
    def __init__(self, staio_fl: float, local_share: float, famine_chance: float, famine_price, famine_at: float,
                 import_margin: float, child_share: float):
        self.staio_fl = staio_fl  # a staio as bread, at a price of 1.0
        self.local_share = local_share  # of a normal year's grain, grown by the town's farmers
        self.famine_chance, self.famine_price, self.famine_at = famine_chance, famine_price, famine_at
        self.import_margin, self.child_share = import_margin, child_share
        self.price = 1.0  # times normal
        self.outside = 1.0
        self.yield_per_farm = None  # staia a farmstead harvests in a normal year, set at the first harvest
        self.farm_stock: Dict[Any, float] = defaultdict(float)  # farmer household -> staia
        self.stores: Dict[Any, float] = defaultdict(float)  # rich household -> staia for its own table
        self.hoards: Dict[Any, float] = defaultdict(float)  # rich household -> staia held to sell
        self.granary = 0.0  # the commune's staia
        self.famines = 0
        self.year: Dict[str, float] = defaultdict(float)  # counts for summaries
        self._ration = 0.0  # set each month by start_month
        self._last_baker = None
        self._resented: set = set()

    def staia_needed(self, people) -> float:
        """Staia a household eats in a month."""
        return sum(self.child_share if (n.age or 0) < 12 else 1.0 for n in people) * STAIA_PER_PERSON_MONTH

    def wholesale(self) -> float:
        """What a baker or a buyer at harvest pays a staio of grain."""
        return self.staio_fl * self.price / (1 + BAKER_MARGIN)

    def famine(self) -> bool:
        return self.price >= self.famine_at

    # -- the year's harvest -------------------------------------------------

    def harvest(self, econ, graph, members, farmers, merchants, rng: random.Random, income) -> None:
        famine = rng.random() < self.famine_chance
        self.famines += famine
        self.outside = rng.uniform(*(self.famine_price if famine else OUTSIDE_RANGE))
        demand = sum(self.staia_needed(people) for people in members.values()) * 12
        farms = [econ_key(n) for n in farmers]
        if self.yield_per_farm is None:  # the first harvest of an imported town
            self._stocked(members, demand)
        if farms:
            if self.yield_per_farm is None:
                self.yield_per_farm = self.local_share * demand / len(farms)
            factor = rng.uniform(*(FAMINE_YIELD if famine else YIELD_RANGE))
            for key in farms:
                self.farm_stock[key] += self.yield_per_farm * factor
                self.year["harvested"] += self.yield_per_farm * factor
        self.update_price(members)
        price = self.wholesale()
        # the rich lay in the year's grain, and a hoard while it's cheap
        for key, people in members.items():
            if not _stores(people):
                continue
            want = self.staia_needed(people) * 12 - self.stores[key]
            if want > 0:
                self.stores[key] += self._buy_grain(econ, graph, key, want, price, farmers, merchants, rng, income)
            cash = max(0.0, graph.household_money.get(key, 0.0))
            room = HOARD_YEARS * self.staia_needed(people) * 12 - self.hoards[key]
            if self.price <= HOARD_BUY_BELOW and room > 0 and cash > 0:
                bought = self._buy_grain(econ, graph, key, min(room, HOARD_CASH_SHARE * cash / price), price,
                                         farmers, merchants, rng, income, local_only=True)
                self.hoards[key] += bought
                self.year["hoarded"] += bought
        # the commune fills its granary after a cheap harvest
        target = GRANARY_MONTHS * demand / 12
        if self.price <= GRANARY_BUY_BELOW and self.granary < target:
            from economy import COMMUNE
            # paid with forced loans when the commune is short, as Florence funded its grain
            cost = (target - self.granary) * price
            econ._commune_borrow(graph, cost - graph.household_money.get(COMMUNE, 0.0),
                                 [n for people in members.values() for n in people])
            affordable = max(0.0, graph.household_money.get(COMMUNE, 0.0)) / price
            self.granary += self._buy_grain(econ, graph, COMMUNE, min(target - self.granary, affordable), price,
                                            farmers, merchants, rng, income)
        self.update_price(members)

    def _stocked(self, members, demand: float) -> None:
        """An imported town has stood for decades (the equilibrium rule): its
        granary is full, the rich have their year's grain and their hoards.
        Bought from scratch in year 1, they took ~8,000 staia off the market,
        imports replaced it, and ~2,300 fl left town: the very poor 283 -> 391."""
        self.granary = GRANARY_MONTHS * demand / 12
        for key, people in members.items():
            if _stores(people):
                self.stores[key] = self.staia_needed(people) * 12
                self.hoards[key] = HOARD_YEARS * self.staia_needed(people) * 12

    def update_price(self, members) -> None:
        """Move toward the price the town's stocks call for, capped by what imports cost."""
        monthly = sum(self.staia_needed(people) for people in members.values() if not _stores(people))
        stock = sum(self.farm_stock.values()) + (sum(self.hoards.values()) if self.price >= HOARD_SELL_AT else 0.0)
        cover = stock / max(monthly, 1e-9)
        cap = self.outside * (1 + self.import_margin)
        target = min(cap, max(GLUT_PRICE, (NORMAL_COVER_MONTHS / max(cover, 0.05)) ** PRICE_ELASTICITY))
        self.price += (target - self.price) * PRICE_STEP

    # -- buying ---------------------------------------------------------------

    def _buy_grain(self, econ, graph, key, staia: float, price: float, farmers, merchants, rng, income,
                   local_only: bool = False, business: bool = False) -> float:
        """`key` buys up to `staia` at `price` a staio: from farmers' stocks,
        then hoarders selling in a dear year, then imports. Returns staia bought.
        For a baker (`business`) it's a cost against income; for a household
        it's spending, which income doesn't count."""
        bought = 0.0
        sellers = [k for k in self.farm_stock if self.farm_stock[k] > 1e-9 and k != key]
        if self.price >= HOARD_SELL_AT:
            sellers += [k for k in self.hoards if self.hoards[k] > 1e-9 and k != key]
        rng.shuffle(sellers)
        for seller in sellers:
            if bought >= staia - 1e-9:
                break
            stock = self.farm_stock if self.farm_stock.get(seller, 0.0) > 1e-9 else self.hoards
            take = min(stock[seller], staia - bought)
            paid = econ._pay(graph, key, seller, take * price)
            take = paid / price if price > 0 else 0.0
            stock[seller] -= take
            bought += take
            income[seller] += paid
            income[key] -= paid if business else 0.0
            if stock is self.hoards:
                self.year["hoards sold"] += take
                self._resent(graph, seller)
            if paid < 1e-12:
                break
        if bought < staia - 1e-9 and not local_only:
            cost = (staia - bought) * self.staio_fl * self.outside / (1 + BAKER_MARGIN) * (1 + self.import_margin)
            before = graph.household_money.get(key, 0.0)
            econ._import(graph, key, min(cost, max(0.0, before)), merchants, rng, income)
            spent = before - graph.household_money.get(key, 0.0)
            income[key] -= spent if business else 0.0
            got = (staia - bought) * spent / cost if cost > 0 else 0.0
            bought += got
            self.year["imported"] += got
        return bought

    def grain_cost(self, key, people) -> float:
        """What this month's grain costs a household: the baking fee on what
        the rich have stored, the granary's price on its ration in a famine,
        bread at the market price for the rest (feed buys in the same order)."""
        rest = self.staia_needed(people)
        bread = self.staio_fl * self.price
        cost = 0.0
        if _stores(people) and self.stores[key] > 1e-9:
            take = min(self.stores[key], rest)
            cost += take * bread * BAKER_MARGIN / (1 + BAKER_MARGIN)
            rest -= take
        if rest > 0 and self.famine() and self.granary > 1e-9:
            take = min(rest, self.staia_needed(people) * self._ration)
            cost += take * bread * GRANARY_PRICE_SHARE
            rest -= take
        return cost + rest * bread

    def feed(self, econ, graph, key, people, spend: float, bakers, farmers, merchants, rng, income) -> float:
        """A household spends `spend` on this month's grain. The rich eat from
        their store and pay the baker's fee; in a famine everyone else buys
        part from the granary below the market; the rest is bread from a
        baker, who buys the grain (no baker: baked at home, the grain bought
        at the bread price). Returns the share of the month's grain eaten."""
        need = self.staia_needed(people)
        if need <= 0:
            return 1.0
        eaten = 0.0
        bread = self.staio_fl * self.price
        if _stores(people) and self.stores[key] > 1e-9:
            take = min(self.stores[key], need)
            fee = take * bread * BAKER_MARGIN / (1 + BAKER_MARGIN)
            paid = self._pay_baker(econ, graph, key, min(spend, fee), bakers, rng, income)
            spend -= paid
            self.stores[key] -= take
            eaten += take
        if eaten < need and self.famine() and self.granary > 1e-9:
            from economy import COMMUNE
            cheap = bread * GRANARY_PRICE_SHARE
            take = min(need * self._ration, need - eaten, spend / cheap)
            paid = econ._pay(graph, key, COMMUNE, take * cheap)
            self.granary -= paid / cheap
            self.year["granary sold"] += paid / cheap
            spend -= paid
            eaten += paid / cheap
        if eaten < need and spend > 1e-12:
            staia = min(need - eaten, spend / bread)
            if bakers:
                paid = self._pay_baker(econ, graph, key, staia * bread, bakers, rng, income)
                baker = self._last_baker
                self._buy_grain(econ, graph, baker, paid / bread, self.wholesale(), farmers, merchants, rng, income,
                                business=True)
                eaten += paid / bread
            else:
                got = self._buy_grain(econ, graph, key, staia, bread, farmers, merchants, rng, income)
                self.year["baked at home"] += got
                eaten += got
        return min(1.0, eaten / need)

    def start_month(self, members) -> None:
        """The share of its grain each household can buy from the granary this
        month in a famine (the granary shared out evenly), and a fresh month of resentment."""
        demand = sum(self.staia_needed(people) for people in members.values() if not _stores(people))
        self._ration = min(1.0, self.granary / max(demand, 1e-9))
        self._resented = set()

    def _pay_baker(self, econ, graph, key, amount: float, bakers, rng, income) -> float:
        """Bread (or the baking fee) from a baker, taxed like anything bought in town."""
        if not bakers or amount <= 0:
            self._last_baker = None
            return 0.0
        before = graph.household_money.get(key, 0.0)
        baker = bakers[rng.randrange(len(bakers))]
        econ._buy(graph, key, amount, [baker], rng, income)
        self._last_baker = econ_key(baker)
        return before - graph.household_money.get(key, 0.0)

    def _resent(self, graph, hoarder) -> None:
        """The hungry who know a hoarder selling dear think less of them."""
        hungry = getattr(graph, "hunger_last", {}) or {}
        for node in graph.nodes.values():
            if not node.alive or econ_key(node) != hoarder:
                continue
            for other, edge in graph.ties_of(node.resident_id).items():
                if econ_key(graph.nodes[other]) in hungry and other not in self._resented:
                    self._resented.add(other)
                    if edge.resident_a == other:
                        edge.valence_a_to_b = max(-1.0, edge.valence_a_to_b - HOARD_RESENTMENT)
                    else:
                        edge.valence_b_to_a = max(-1.0, edge.valence_b_to_a - HOARD_RESENTMENT)

    def summary(self) -> Dict[str, float]:
        return {"food_grain_stock": round(sum(self.farm_stock.values()), 1),
                "food_rich_stores": round(sum(self.stores.values()), 1),
                "food_hoards": round(sum(self.hoards.values()), 1),
                "food_granary": round(self.granary, 1),
                "food_outside_price": round(self.outside, 2),
                **{f"food_{k}": round(v, 1) for k, v in self.year.items()}}


def econ_key(node):
    from economy import household_key
    return household_key(node)


def _stores(people) -> bool:
    return any(n.ses in STORE_CLASSES for n in people)
