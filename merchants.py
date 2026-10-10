"""Merchants in goods (goods slice 4, Project_Vision/04 §9, user 2026-10-08).

Each merchant house trades one line: grain; wool and cloth; iron, timber and
hides (the "wares"); luxuries. What the town imports is sold from a
merchant's warehouse, no longer straight from outside: a line out of stock
goes without until a cargo lands (user). At each month's end a merchant
orders what their line has been selling, paid up front from the month's
takings, and the cargo lands one to three months later. A cargo is lost now
and then, and now and then a correspondent abroad fails and takes every
cargo afloat with them; a house that can't absorb the loss is ruined, and
the richest house that can takes up its line. Merchants buy the workshops'
surplus for export with cash they have, and are paid when it sells outside.

Stocks are counted in staia for grain and, for the other lines, in florins'
worth at the normal import price. Money stays conserved: what merchants pay
outside leaves town when they order, what they sell comes back in. In a
quiet year the money moves as before this slice (the buyer pays the import
price, the gabelle goes to the commune, the merchant keeps their margin).
"""
import random
from collections import defaultdict
from typing import Any, Dict, List

LEAD_MONTHS = {"grain": 1, "cloth": 2, "wares": 2, "luxuries": 3}  # C: months a cargo takes to land
COVER_MONTHS = 2.0  # C: a merchant keeps about this many months of sales in the warehouse
EXPORT_MONTHS = 2  # C: months until a cargo of exports is sold outside and paid
SALES_MEMORY = 0.3  # C: each month's sales weigh this much in what a merchant expects to sell
RESERVE_MONTHS = 2.0  # C: a merchant keeps this many months of the household's needs out of trade
CARGO_LOST = 0.02  # C: chance a cargo never arrives (shipwreck, bandits, seizure); river trade, below
# the 3-6% premiums on 14th-century sea voyages. With failed correspondents, ~2% of imports a year
CORRESPONDENT_FAILS = 0.01  # C: yearly chance a merchant's correspondent abroad fails, taking every cargo afloat
RUIN_SHARE = 0.5  # C: a loss that leaves a house less than this share of what it trades ruins it; about one
# house in 12 years in the reference town (0.6: 1-3 in 8 years, some from one lost cargo; 0.4: none in 75)
# what a good's line is: whose warehouse it comes from, who exports it
GOOD_LINE = {"wool": "cloth", "cloth": "cloth", "clothing": "cloth", "timber": "wares", "iron": "wares",
             "hides": "wares", "leather": "wares", "shoes": "wares", "housewares": "wares", "import": "wares"}


class MerchantTrade:
    def __init__(self, gabelle: float, margin: float):
        self.gabelle, self.margin = gabelle, margin
        self.line: Dict[int, str] = {}  # merchant (resident) -> their line
        self.stock: Dict[int, float] = defaultdict(float)  # merchant -> units in the warehouse
        self.cost: Dict[int, float] = defaultdict(float)  # merchant -> what a unit in stock cost them
        self.afloat: List[list] = []  # [month due, merchant, units, cost a unit]: imports on the way
        self.exports: List[list] = []  # [month due, merchant, fl it sells for, fl paid]: exports on the way
        self.sold: Dict[int, float] = defaultdict(float)  # merchant -> units sold this month
        self.expected: Dict[int, float] = {}  # merchant -> units a month they expect to sell
        self.committed: Dict[Any, float] = defaultdict(float)  # household -> takings owed to the next order
        self.reserve: Dict[Any, float] = defaultdict(float)  # household -> cash kept out of trade
        self.till: Dict[str, float] = defaultdict(float)  # line -> units sold in the first month
        self.till_exports: Dict[str, float] = defaultdict(float)
        self.trading = False  # set at the end of the first month, when the warehouses are stocked
        self.month = 0
        self.year: Dict[str, float] = defaultdict(float)

    # -- prices -----------------------------------------------------------------

    def unit_cost(self, line: str, food) -> float:
        """What a merchant pays outside for a unit: the import price less the
        gabelle and their margin (as before this slice)."""
        return self.import_price(line, food) * (1 - self.gabelle) * (1 - self.margin)

    def import_price(self, line: str, food) -> float:
        """A unit's price in town when merchants have it: grain at the
        outside price plus the margin, the rest at 1 fl a unit."""
        if line != "grain":
            return 1.0
        from food import BAKER_MARGIN
        return food.staio_fl * food.outside / (1 + BAKER_MARGIN) * (1 + self.margin)

    # -- selling ------------------------------------------------------------------

    def sell(self, econ, graph, buyer, line: str, amount: float, merchants, rng: random.Random, income,
             price: float = 1.0, business: bool = False) -> float:
        """`buyer` spends up to `amount` fl on `line` at `price` a unit, from
        merchants who have it. Returns the fl spent. Before the warehouses
        are stocked (the first month) it's bought straight from outside."""
        from economy import COMMUNE, household_key
        amount = min(amount, max(0.0, graph.household_money.get(buyer, 0.0)))
        if amount <= 1e-12:
            return 0.0
        if not self.trading or not merchants:
            before = graph.household_money.get(buyer, 0.0)
            econ._import(graph, buyer, amount, merchants, rng, income)
            spent = before - graph.household_money.get(buyer, 0.0)
            self.till[line] += spent / price
            if business:
                income[buyer] -= spent
            return spent
        sellers = [m for m, l in self.line.items() if l == line and self.stock[m] > 1e-9
                   and household_key(graph.nodes[m]) != buyer]
        rng.shuffle(sellers)
        spent = 0.0
        for merchant in sellers:
            if spent >= amount - 1e-9:
                break
            key = household_key(graph.nodes[merchant])
            want = min(self.stock[merchant] * price, amount - spent)
            tax = econ._pay(graph, buyer, COMMUNE, want * self.gabelle)  # at the gates
            econ._year["commune: gabelle"] += tax
            got = econ._pay(graph, buyer, key, want - tax)
            units = (tax + got) / price
            self.stock[merchant] -= units
            cogs = units * self.cost[merchant]
            income[key] += got - cogs
            self.committed[key] += cogs
            self.sold[merchant] += units
            spent += tax + got
            if business:
                income[buyer] -= tax + got
            if tax + got < want - 1e-9:
                break  # the buyer ran out of money
        if spent < amount - 1e-9:
            self.year[f"short {line}"] += amount - spent
        return spent

    def take_on_account(self, line: str, value: float, rng: random.Random) -> List[tuple]:
        """A workshop takes up to `value` fl of materials on account from the
        merchants of `line`. Returns [(merchant, fl)] it owes them."""
        sellers = [m for m, l in self.line.items() if l == line and self.stock[m] > 1e-9]
        rng.shuffle(sellers)
        taken = []
        for merchant in sellers:
            take = min(self.stock[merchant], value)
            self.stock[merchant] -= take
            self.sold[merchant] += take
            taken.append((merchant, take))
            value -= take
            if value <= 1e-9:
                break
        if value > 1e-9:
            self.year[f"short {line}"] += value
        return taken

    def collect(self, econ, graph, payer, merchant: int, amount: float, income) -> float:
        """A workshop pays a merchant for materials taken on account (the
        gabelle at the gates, as on any import). Returns what it paid."""
        from economy import COMMUNE, household_key
        if not graph.nodes[merchant].alive:
            return 0.0  # ponytail: a dead merchant's accounts aren't passed to the heir
        key = household_key(graph.nodes[merchant])
        tax = econ._pay(graph, payer, COMMUNE, amount * self.gabelle)
        econ._year["commune: gabelle"] += tax
        got = econ._pay(graph, payer, key, amount - tax)
        cogs = (tax + got) * self.cost[merchant]
        income[key] += got - cogs
        self.committed[key] += cogs
        return tax + got

    def export(self, econ, graph, master, good: str, value: float, merchants, rng: random.Random, income) -> float:
        """Merchants of the good's line buy up to `value` fl (at the normal
        price) of a workshop's surplus at `export_price`, with cash they have;
        it sells outside EXPORT_MONTHS later. Returns the fl worth bought."""
        from crafts import EXPORT_PRICE
        from economy import household_key
        line = GOOD_LINE[good]
        if not self.trading:
            merchant = household_key(merchants[rng.randrange(len(merchants))])
            paid = econ._pay(graph, merchant, master, value * EXPORT_PRICE)
            income[master] += paid
            sale = econ._pay(graph, None, merchant, paid / EXPORT_PRICE)
            income[merchant] += sale - paid
            econ._year["in: craft exports"] += sale
            self.till_exports[line] += sale
            return paid / EXPORT_PRICE
        buyers = [m for m, l in self.line.items() if l == line]
        rng.shuffle(buyers)
        bought = 0.0
        for merchant in buyers:
            if bought >= value - 1e-9:
                break
            key = household_key(graph.nodes[merchant])
            cash = graph.household_money.get(key, 0.0) - self.committed[key] - self.reserve[key]
            paid = econ._pay(graph, key, master, min((value - bought) * EXPORT_PRICE, max(0.0, cash)))
            if paid <= 1e-9:
                continue
            income[master] += paid
            self.exports.append([self.month + EXPORT_MONTHS, merchant, paid / EXPORT_PRICE, paid])
            bought += paid / EXPORT_PRICE
        return bought

    # -- the month ----------------------------------------------------------------

    def start_month(self, econ, graph, alive, food, rng: random.Random, income) -> None:
        """Heirs take up their house's line, empty lines get a new house,
        cargoes land (or are lost), correspondents fail."""
        self.month += 1
        if not self.trading:
            return
        self._successions(graph, alive)
        from economy import household_key
        losers = set()
        for cargo in [c for c in self.afloat if c[0] <= self.month]:
            self.afloat.remove(cargo)
            _, merchant, units, cost = cargo
            if rng.random() < CARGO_LOST:
                self.year["cargoes lost"] += 1
                self.year["cargoes lost fl"] += units * cost
                losers.add(merchant)
                continue
            graph.cargoes_landed = getattr(graph, "cargoes_landed", []) + [merchant]  # disease can come with it
            held = self.stock[merchant]
            self.cost[merchant] = (held * self.cost[merchant] + units * cost) / max(held + units, 1e-12)
            self.stock[merchant] = held + units
        for cargo in [c for c in self.exports if c[0] <= self.month]:
            self.exports.remove(cargo)
            _, merchant, worth, paid = cargo
            if rng.random() < CARGO_LOST:
                self.year["cargoes lost"] += 1
                self.year["cargoes lost fl"] += paid
                losers.add(merchant)
                continue
            key = household_key(graph.nodes[merchant])
            sale = econ._pay(graph, None, key, worth)
            income[key] += sale - paid
            econ._year["in: craft exports"] += sale
        for merchant in list(self.line):
            if rng.random() < CORRESPONDENT_FAILS / 12:
                lost = [c for c in self.afloat + self.exports if c[1] == merchant]
                if lost:
                    self.year["correspondents failed"] += 1
                    self.year["cargoes lost fl"] += sum(c[2] * c[3] if c in self.afloat else c[3] for c in lost)
                    self.afloat = [c for c in self.afloat if c[1] != merchant]
                    self.exports = [c for c in self.exports if c[1] != merchant]
                    losers.add(merchant)
        for merchant in sorted(losers):
            if self._can_absorb(graph, merchant, food):
                continue
            self._ruin(graph, merchant, alive)
        food.merchant_grain = sum(s for m, s in self.stock.items() if self.line.get(m) == "grain")

    def order(self, econ, graph, alive, needs, food, members, rng: random.Random) -> None:
        """At the month's end each merchant orders what their line has been
        selling (grain: what the town will need beyond the farmers' stocks),
        paid up front from the month's takings, keeping RESERVE_MONTHS of the
        household's needs. The first month stocks the warehouses instead."""
        from economy import household_key
        if not self.trading:
            self._open(graph, alive, food, members)
            return
        for merchant, line in sorted(self.line.items()):
            key = household_key(graph.nodes[merchant])
            self.expected[merchant] = ((1 - SALES_MEMORY) * self.expected.get(merchant, 0.0)
                                       + SALES_MEMORY * self.sold[merchant])
            self.sold[merchant] = 0.0
            self.reserve[key] = RESERVE_MONTHS * needs.get(key, 0.0)
            want = self._target(merchant, food, members) - self._position(merchant)
            cost = self.unit_cost(line, food)
            cash = graph.household_money.get(key, 0.0) - self.reserve[key]
            units = min(max(0.0, want), max(0.0, cash) / cost)
            self.committed[key] = 0.0
            if units <= 1e-9:
                continue
            paid = econ._pay(graph, key, None, units * cost)
            econ._year["out: imports"] += paid
            self.afloat.append([self.month + LEAD_MONTHS[line], merchant, paid / cost, cost])

    # -- inside -------------------------------------------------------------------

    def _target(self, merchant: int, food, members) -> float:
        """Units a merchant wants in the warehouse and afloat."""
        line = self.line[merchant]
        monthly = self.expected.get(merchant, 0.0)
        if line == "grain":  # what the bakers' customers eat, less what the farmers still hold
            from food import _stores
            eaten = sum(food.staia_needed(p) for p in members.values() if not _stores(p))
            dealers = sum(1 for l in self.line.values() if l == "grain")
            horizon = LEAD_MONTHS[line] + COVER_MONTHS
            need = max(0.0, eaten - sum(food.farm_stock.values()) / horizon) / max(1, dealers)
            monthly = max(monthly, need)
        return (LEAD_MONTHS[line] + COVER_MONTHS) * monthly

    def _position(self, merchant: int) -> float:
        return self.stock[merchant] + sum(c[2] for c in self.afloat if c[1] == merchant)

    def _can_absorb(self, graph, merchant: int, food) -> bool:
        """After a loss: does the house still hold RUIN_SHARE of what it trades
        (stock, cargo afloat, cash beyond its reserve)?"""
        from economy import household_key
        line = self.line[merchant]
        key = household_key(graph.nodes[merchant])
        cost = self.unit_cost(line, food)
        target = (LEAD_MONTHS[line] + COVER_MONTHS) * self.expected.get(merchant, 0.0) * cost
        held = (self._position(merchant) * cost
                + max(0.0, graph.household_money.get(key, 0.0) - self.reserve[key]))
        return target <= 1e-9 or held >= RUIN_SHARE * target

    def _ruin(self, graph, merchant: int, alive) -> None:
        """A ruined house gives up trade; the richest house that can takes up
        the line, and the warehouse with it."""
        node = graph.nodes[merchant]
        line = self.line.pop(merchant)
        node.occupation = None  # looks for work like anyone (economy._give_work)
        for worker, boss in list(graph.employer.items()):
            if boss == merchant:  # their outworkers find another merchant (economy._employer)
                del graph.employer[worker]
        self.year["houses ruined"] += 1
        self.year[f"houses ruined {line}"] += 1
        successor = self._appoint(graph, alive, line, exclude=merchant)
        if successor is not None:
            self._hand_over(merchant, successor)

    def _appoint(self, graph, alive, line: str, exclude=None):
        """The head of the richest house that could trade takes up `line`
        (the same people as at import: economy._assign_jobs)."""
        from economy import (MERCHANT_KEEPS_JOB, MERCHANT_MIN_AGE, PAY, household_key, job_kind, wealth)
        ruined = household_key(graph.nodes[exclude]) if exclude is not None else None
        heads = {}
        for node in alive:
            key = household_key(node)
            if (node.alive and not node.is_noble and (node.age or 0) >= MERCHANT_MIN_AGE and key != ruined
                    and node.occupation != "merchant" and job_kind(node.occupation) not in MERCHANT_KEEPS_JOB
                    and PAY.get(job_kind(node.occupation), (0.0, None))[1] != "public"):
                if key not in heads or (node.age or 0) > (heads[key].age or 0):
                    heads[key] = node
        if not heads:
            return None
        key = max(sorted(heads, key=str), key=lambda k: wealth(graph, k))
        head = heads[key]
        head.occupation, head.workplace_building_id = "merchant", None
        graph.employer.pop(head.resident_id, None)
        self.line[head.resident_id] = line
        self.year["houses took up trade"] += 1
        return head.resident_id

    def _hand_over(self, old: int, new: int) -> None:
        """Stock, cargo afloat and custom pass from one merchant to another."""
        held, units = self.stock.pop(old, 0.0), self.stock[new]
        if held + units > 1e-12:
            self.cost[new] = (held * self.cost.pop(old, 0.0) + units * self.cost[new]) / (held + units)
        self.stock[new] = held + units
        for cargo in self.afloat + self.exports:
            if cargo[1] == old:
                cargo[1] = new
        self.expected[new] = self.expected.get(new, 0.0) + self.expected.pop(old, 0.0)
        self.sold[new] += self.sold.pop(old, 0.0)

    def _successions(self, graph, alive) -> None:
        """A dead merchant's line passes to the house's heir (economy.
        pass_on_merchant_house), else to another merchant of the line, else to
        a new house. A merchant with no line (a newcomer) takes the busiest."""
        from economy import household_key
        merchants = [n for n in alive if n.occupation == "merchant"]
        unlined = [n.resident_id for n in merchants if n.resident_id not in self.line]
        orphans = [m for m in sorted(self.line) if not graph.nodes[m].alive or graph.nodes[m].occupation != "merchant"]
        for old in orphans:
            line = self.line.pop(old)
            homes = {household_key(graph.nodes[old])}
            heir = next((m for m in unlined if household_key(graph.nodes[m]) in homes), unlined[0] if unlined else None)
            if heir is not None:
                unlined.remove(heir)
                self.line[heir] = line
            else:
                heir = next((m for m, l in sorted(self.line.items()) if l == line), None)
                if heir is None:
                    heir = self._appoint(graph, alive, line)
            if heir is not None:
                self._hand_over(old, heir)
        for merchant in unlined:
            busiest = max(sorted(LEAD_MONTHS), key=lambda l: sum(self.expected.get(m, 0.0) for m in self.line
                                                                 if self.line[m] == l)
                          / (1 + sum(1 for m in self.line.values() if m == l)))
            self.line[merchant] = busiest

    def _open(self, graph, alive, food, members) -> None:
        """After the first month: the merchants split across the lines by what
        each sold, and an imported town's warehouses hold COVER_MONTHS of it
        with a month's cargo afloat for each month at sea, and its exports
        afloat (the equilibrium rule: the town has traded for decades)."""
        merchants = sorted(n.resident_id for n in alive if n.occupation == "merchant")
        if not merchants:
            return
        lines = sorted(LEAD_MONTHS)
        value = {l: self.till[l] * (self.import_price(l, food) if l == "grain" else 1.0) for l in lines}
        total = sum(value.values()) or 1.0
        seats = {l: 1 for l in lines}
        for _ in range(max(0, len(merchants) - len(lines))):  # the rest by largest share per seat
            seats[max(lines, key=lambda l: value[l] / total / seats[l])] += 1
        queue = list(merchants)
        for line in sorted(lines, key=lambda l: -value[l]):
            for _ in range(seats[line]):
                if queue:
                    self.line[queue.pop(0)] = line
        self.trading = True
        for line in lines:
            dealers = [m for m, l in self.line.items() if l == line]
            if not dealers:
                continue
            monthly = self.till[line] / len(dealers)
            cost = self.unit_cost(line, food)
            for merchant in dealers:
                self.expected[merchant] = monthly
                self.stock[merchant] = COVER_MONTHS * monthly
                self.cost[merchant] = cost
                for ahead in range(1, LEAD_MONTHS[line] + 1):
                    self.afloat.append([self.month + ahead, merchant, monthly, cost])
                for ahead in range(1, EXPORT_MONTHS + 1):
                    worth = self.till_exports[line] / len(dealers)
                    if worth > 0:
                        from crafts import EXPORT_PRICE
                        self.exports.append([self.month + ahead, merchant, worth, worth * EXPORT_PRICE])
        food.merchant_grain = sum(s for m, s in self.stock.items() if self.line.get(m) == "grain")

    def summary(self) -> Dict[str, float]:
        by_line = defaultdict(float)
        for merchant, units in self.stock.items():
            if merchant in self.line:
                by_line[self.line[merchant]] += units
        return {**{f"merchants_stock_{l}": round(v, 1) for l, v in by_line.items()},
                **{f"merchants_in_{l}": sum(1 for x in self.line.values() if x == l) for l in LEAD_MONTHS},
                **{f"merchants_afloat_{l}": round(sum(c[2] for c in self.afloat if self.line.get(c[1]) == l), 1)
                   for l in LEAD_MONTHS},
                **{f"merchants_{k.replace(' ', '_')}": round(v, 1) for k, v in self.year.items()}}
