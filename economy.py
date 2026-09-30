# economy.py
"""Economy, slice 1 (Project_Vision/03-economy-design.md, decided with the
user 2026-09-29): jobs, household money, income and spending, and merchants
as the town's trade with the outside. Amounts in florins. Numbers come from
the user's parameter book, medieval_city_sim_parameters.md (cited as
"book §"); grade C numbers there are assumptions, and so are the ones marked
`# C` here.

Two halves:
- setup_economy (at import, from graph.import_snapshot): gives work to the
  92% of adults TownShape leaves jobless (workshop trades, more farmhands,
  merchants, putting-out, day labour) and turns TownShape's household wealth
  into florins shaped like the book's Prato 1300 deciles.
- EconomyPhenomenon (monthly): wages, property income, spending, merchants'
  imports and exports, and class following wealth once a year.
"""
import random
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

FLORIN_IN_SOLDI = 64  # book §1, 1349
WORKING_DAYS = 250  # book §4d (Allen convention)
UNSKILLED_WAGE = 8.4 * WORKING_DAYS / FLORIN_IN_SOLDI  # ~32.8 fl a year, book §4a (1349)
SKILLED_WAGE = 13.4 * WORKING_DAYS / FLORIN_IN_SOLDI  # ~52.3 fl a year, master mason

# grain per person per year: 0.9 kg a day, 18 kg a staio, 13 soldi a staio (book §5, §6)
GRAIN_PER_PERSON = 0.9 * 365 / 18 * 13 / FLORIN_IN_SOLDI  # ~3.71 fl
GRAIN_SHARE_OF_BASKET = 0.45  # book §5c: grain ~45% of an unskilled family's budget
BASKET_PER_PERSON = GRAIN_PER_PERSON / GRAIN_SHARE_OF_BASKET  # ~8.2 fl: food, fuel, cloth, lodging
CHILD_BASKET = 0.6  # C: a child under 12 needs less
LOCAL_GRAIN_SHARE = 0.5  # C: the rest is imported by merchants
IMPORT_MARGIN = 0.15  # C: merchants keep this share of what they import and sell
PROPERTY_RETURN = 0.07  # book §3e: the 1427 census capitalised income at 7%; property only, not cash
CASH_SHARE_OF_WEALTH = 0.1  # C: of the wealth seeded at import, held as cash rather than property
SAVING_SHARE = 0.2  # C: of income above the basket, saved while far below the cushion
SAVINGS_CUSHION_YEARS = 0.25  # C: saving stops at about three months of income (the poor held little)
INCOME_MEMORY = 0.1  # C: how fast a household's sense of its usual income follows this month's
EXCESS_CASH_SPENT_PER_YEAR = 0.5  # C: share of cash above the cushion spent each year
LUXURY_IMPORT_SHARE = 0.5  # C: of spending above the basket, bought from outside through merchants
DAY_LABOUR_OF_SPENDING = 0.4  # C: of spending above the basket in town, paid to day labourers
EXPORT_MARKUP = 1.35  # C: merchants sell putting-out cloth for this times the wages they paid
RAW_WOOL_SHARE = 0.3  # C: of the cloth's price, spent on raw wool bought outside
PROPERTYLESS_BELOW = 10.0  # C: under this (a few weeks of wages in hand) counts as owning nothing
DAY_LABOUR_SHARE = 0.3  # C: of local sellers' takings spent hiring day labour
ARRIVAL_SAVINGS = 5.0  # C: what a newcomer brings

WEALTH_PER_PERSON = 45.0  # book §3a: small cities, 1427 (decided: Riverport is a small city)
PROPERTYLESS_SHARE = 0.25  # between the book's 14% (Florence 1427) and 38% (Prato 1372)
# book §3b, Prato 1300: share of wealth held by each tenth of those who own something
PRATO_1300_DECILES = [1.58, 1.82, 1.98, 2.14, 2.27, 2.49, 5.93, 6.69, 9.39, 65.72]
PRATO_1300_TOP1 = 29.18

MERCHANT_PER_RESIDENTS = 150  # C: ~13 merchants in a town of 1,900
PUTTING_OUT_SHARE = 0.5  # C: of the otherwise jobless, work at home for a merchant
RENTIER_HOUSEHOLD_SHARE = 0.1  # C: the richest tenth of households live off property, not wages
RENTIER_CLASSES = ("rich", "very_rich")  # a young adult of these classes lives off property too
SERVANT_CLASS_CAP = "poor"  # a live-in servant isn't rich because the household is
UNEMPLOYED_AT_START = 0.05  # C: of the otherwise jobless, still looking for work at import
JOB_FIND_PER_MONTH = 0.2  # C: about 4 months to find work
JOB_LOSS_PER_MONTH = 0.01  # C: putting-out and day labour are precarious
PRECARIOUS = ("outworker", "day_labourer")
FARMHANDS_ADDED = 4  # decided: more farm work outside the walls
# C: the crafts of a small Tuscan town, for TownShape's empty workshops
WORKSHOP_TRADES = [("weaver", 3), ("dyer", 1), ("fuller", 1), ("tanner", 1), ("shoemaker", 2), ("tailor", 2),
                   ("carpenter", 2), ("cooper", 1), ("baker", 2), ("potter", 1), ("mason", 2)]
WORKSHOP_HANDS = (3, 5)

# occupation -> (yearly wage, who pays). "self": earns from what they sell;
# "public": paid from outside (the commune or the Church) until taxes exist.
PAY: Dict[str, Tuple[float, str]] = {
    "day_labourer": (UNSKILLED_WAGE, "day labour"),  # when there is work
    "outworker": (0.7 * UNSKILLED_WAGE, "merchant"),  # piece rates, book §4e putting-out
    "farmhand": (0.9 * UNSKILLED_WAGE, "farmer"),
    "shop_staff": (UNSKILLED_WAGE, "shopkeep"),
    "tavern_staff": (UNSKILLED_WAGE, "barkeep"),
    "smith_apprentice": (0.6 * UNSKILLED_WAGE, "blacksmith"),
    "servant": (15.0, "noble"),  # book §4d, plus board
    "laborer": (UNSKILLED_WAGE, "merchant"),
    "dockworker": (UNSKILLED_WAGE, "merchant"),
    "warehouse_clerk": (SKILLED_WAGE, "merchant"),
    "apprentice": (0.6 * UNSKILLED_WAGE, "mage"),
    "guard": (138 * 12 / FLORIN_IN_SOLDI, "public"),  # book §4c, local crossbowman 1349
    "soldier": (138 * 12 / FLORIN_IN_SOLDI, "public"),
    "priest": (40.0, "public"),  # C
    "acolyte": (15.0, "public"),
    "clerk": (400 * 12 / FLORIN_IN_SOLDI, "public"),  # book §4c, notary
    "teacher": (40.0, "public"),
    "healer": (200 * 12 / FLORIN_IN_SOLDI, "public"),  # book §4c, public doctor
    "scholar": (60.0, "public"),
    "harbormaster": (75.0, "public"),
    "customs_clerk": (40.0, "public"),
}
# who takes the town's everyday spending on goods (grain goes to farmers and
# merchants, imports through merchants)
LOCAL_SELLERS = ("master", "shopkeep", "barkeep", "blacksmith", "trader", "mage")
DAY_LABOUR_WORK = 0.6  # C: share of working days a day labourer finds work, when there's demand


def household_key(node) -> Any:
    return node.household_id if node.household_id is not None else ("alone", node.resident_id)


def is_master(occupation: Optional[str]) -> bool:
    return occupation in dict(WORKSHOP_TRADES)


def job_kind(occupation: Optional[str]) -> Optional[str]:
    """The pay line an occupation falls under."""
    if occupation is None:
        return None
    if is_master(occupation):
        return "master"
    if occupation.endswith("_hand"):
        return "craft_hand"
    return occupation


def setup_economy(graph, building_types: Dict[int, str], townshape_wealth: Dict[int, float], seed: int) -> None:
    """At import (the adapted importer): jobs for the jobless, then money."""
    rng = random.Random(f"economy-{seed}")
    graph.building_types = building_types
    graph.employer = {}
    _assign_jobs(graph, townshape_wealth, rng)
    _seed_wealth(graph, townshape_wealth, rng)
    _set_class_lines(graph, rng)


CLASSES = ("very_poor", "poor", "middling", "rich", "very_rich")
CLASS_KEEP_SHARE = 0.8  # C: someone drops a class only below this share of its line
# a seller's or merchant's yearly income at import, before any month has run (C)
EXPECTED_EARNINGS = {"master": SKILLED_WAGE, "shopkeep": SKILLED_WAGE, "barkeep": SKILLED_WAGE,
                     "blacksmith": SKILLED_WAGE, "trader": SKILLED_WAGE, "farmer": SKILLED_WAGE,
                     "mage": 1.7 * SKILLED_WAGE, "merchant": 100.0, "craft_hand": UNSKILLED_WAGE,
                     "day_labourer": 0.6 * UNSKILLED_WAGE}


def resources_per_person(graph, yearly_income: Dict[Any, float]) -> Dict[Any, float]:
    """A household's wealth plus a year of its income, per member: how well
    it lives. Wealth alone can't rank the quarter of households owning
    nothing."""
    members = defaultdict(int)
    for node in graph.nodes.values():
        if node.alive:
            members[household_key(node)] += 1
    return {key: (wealth(graph, key) + yearly_income.get(key, 0.0)) / count for key, count in members.items()}


def _expected_income(graph) -> Dict[Any, float]:
    income = defaultdict(float)
    for node in graph.nodes.values():
        if node.alive:
            kind = job_kind(node.occupation)
            income[household_key(node)] += EXPECTED_EARNINGS.get(kind, PAY.get(kind, (0.0, None))[0])
    for key, owned in getattr(graph, "household_property", {}).items():
        income[key] += owned * PROPERTY_RETURN
    return income


def _set_class_lines(graph, rng) -> None:
    """Rank residents by resources per person, cut them into the town's
    class shares (params.class_shares) and keep the cut points as the fixed
    lines people are judged against from then on."""
    per_person = resources_per_person(graph, _expected_income(graph))
    people = sorted((per_person.get(household_key(n), 0.0), rng.random(), n) for n in graph.nodes.values() if n.alive)
    shares = getattr(graph.params, "class_shares", (0.15, 0.50, 0.25, 0.09, 0.01))
    graph.class_lines, cut = [], 0.0
    for share in shares[:-1]:
        cut += share
        index = min(len(people) - 1, int(round(cut * len(people))))
        graph.class_lines.append(people[index][0] if people else 0.0)
    bounds = [0] + [int(round(c * len(people))) for c in _cumulative(shares)]
    for level, (lo, hi) in enumerate(zip(bounds, bounds[1:])):
        for _, _, node in people[lo:hi]:
            node.ses = _capped(node, CLASSES[level])


def _capped(node, level: str) -> str:
    if node.occupation == "servant" and CLASSES.index(level) > CLASSES.index(SERVANT_CLASS_CAP):
        return SERVANT_CLASS_CAP
    return level


def _cumulative(shares):
    total, out = 0.0, []
    for share in shares:
        total += share
        out.append(min(1.0, total))
    return out


def class_for(resources: float, current: str, lines: List[float]) -> str:
    """The class for these resources, keeping someone in their class until
    they fall below CLASS_KEEP_SHARE of its line."""
    level = sum(1 for line in lines if resources >= line)
    held = CLASSES.index(current) if current in CLASSES else 0
    if level < held and resources >= lines[held - 1] * CLASS_KEEP_SHARE:
        return current
    return CLASSES[level]


def _jobless_adults(graph) -> List[Any]:
    return [n for n in sorted(graph.nodes.values(), key=lambda n: n.resident_id)
            if n.alive and n.age is not None and n.age >= 18 and n.occupation is None and not n.is_noble]


def _assign_jobs(graph, townshape_wealth, rng) -> None:
    alive = sum(1 for n in graph.nodes.values() if n.alive)
    jobless = _jobless_adults(graph)
    rng.shuffle(jobless)

    # merchants: an adult of each of the richest non-noble households
    by_household = defaultdict(list)
    for node in jobless:
        by_household[household_key(node)].append(node)
    richest = sorted(by_household, key=lambda h: -townshape_wealth.get(h, 0.0) if not isinstance(h, tuple) else 0.0)
    merchants = []
    for key in richest[:max(2, round(alive / MERCHANT_PER_RESIDENTS))]:
        head = max(by_household[key], key=lambda n: n.age)
        head.occupation = "merchant"
        merchants.append(head.resident_id)
    graph.merchants = merchants
    # the other adults of the richest households live off the family's
    # property (2026-09-30: they were being handed day labour)
    wealthy = set(richest[:max(1, round(len(richest) * RENTIER_HOUSEHOLD_SHARE))])
    for node in jobless:
        if node.occupation is None and household_key(node) in wealthy:
            node.occupation = "rentier"
    jobless = [n for n in jobless if n.occupation is None]

    def take(count):
        taken = jobless[:count]
        del jobless[:count]
        return taken

    trades, weights = zip(*WORKSHOP_TRADES)
    for building_id, kind in sorted(building_types_items(graph)):
        if kind == "workshop":
            staff = take(1 + rng.randint(*WORKSHOP_HANDS))
            if not staff:
                break
            trade = rng.choices(trades, weights)[0]
            staff[0].occupation, staff[0].workplace_building_id = trade, building_id
            for hand in staff[1:]:
                hand.occupation, hand.workplace_building_id = f"{trade}_hand", building_id
                graph.employer[hand.resident_id] = staff[0].resident_id
        elif kind == "farmstead":
            for hand in take(FARMHANDS_ADDED):
                hand.occupation, hand.workplace_building_id = "farmhand", building_id

    for node in jobless:  # putting-out for a merchant, or day labour; a few still looking
        if rng.random() < UNEMPLOYED_AT_START:
            continue
        if merchants and rng.random() < PUTTING_OUT_SHARE:
            node.occupation = "outworker"
            graph.employer[node.resident_id] = rng.choice(merchants)
        else:
            node.occupation = "day_labourer"


def building_types_items(graph):
    return getattr(graph, "building_types", {}).items()


def _seed_wealth(graph, townshape_wealth, rng) -> None:
    """Florins per household: TownShape's ranking, the book's amounts."""
    members = defaultdict(int)
    for node in graph.nodes.values():
        if node.alive:
            members[household_key(node)] += 1
    keys = sorted(members, key=lambda h: (townshape_wealth.get(h, 0.0) if not isinstance(h, tuple) else 0.0,
                                          rng.random()))
    propertyless = round(len(keys) * PROPERTYLESS_SHARE)
    owners = keys[propertyless:]
    total = WEALTH_PER_PERSON * sum(members.values())
    shares = _decile_shares(len(owners))
    # most of a household's wealth is property (land, houses) earning 7% a
    # year; a little is cash to live on
    graph.household_money = {key: 0.0 for key in keys[:propertyless]}
    graph.household_property = {key: 0.0 for key in keys[:propertyless]}
    for key, share in zip(owners, shares):
        graph.household_money[key] = total * share * CASH_SHARE_OF_WEALTH
        graph.household_property[key] = total * share * (1.0 - CASH_SHARE_OF_WEALTH)


def _decile_shares(count: int) -> List[float]:
    """Each owner's share of wealth, poorest first: equal within each tenth
    (Prato 1300), with the top 1% holding PRATO_1300_TOP1 of it all."""
    if count == 0:
        return []
    shares = []
    for decile, pct in enumerate(PRATO_1300_DECILES):
        lo, hi = round(count * decile / 10), round(count * (decile + 1) / 10)
        size = max(0, hi - lo)
        if decile == 9 and size > 1:
            top = max(1, round(count / 100))
            shares += [(pct - PRATO_1300_TOP1) / 100 / (size - top)] * (size - top)
            shares += [PRATO_1300_TOP1 / 100 / top] * top
        else:
            shares += [pct / 100 / size] * size if size else []
    total = sum(shares)
    return [s / total for s in shares]


def wealth(graph, key) -> float:
    """A household's cash plus property."""
    return graph.household_money.get(key, 0.0) + getattr(graph, "household_property", {}).get(key, 0.0)


def gini(values: List[float]) -> float:
    values = sorted(values)
    n, total = len(values), sum(values)
    if not n or total <= 0:
        return 0.0
    return sum((2 * i - n + 1) * v for i, v in enumerate(values)) / (n * total)


class EconomyPhenomenon:
    """Monthly (every 30 days): who earns, who spends, where money comes
    from and goes. Money is held per household (graph.household_money).
    - **In:** public wages (commune, Church), 7% a year on wealth (land
      outside the walls), merchants' cloth sold outside, newcomers' savings.
    - **Out:** the grain the town doesn't grow and the luxuries the rich buy,
      both imported through merchants (who keep a margin).
    - **Around:** employers pay their workers; households buy their basket
      (grain from farmers and merchants, the rest from workshops, shops,
      taverns), then spend part of what's left; local sellers hire day labour.
    Once a year a resident's class follows their household's wealth per
    person, with thresholds fixed at import so the town starts with its
    TownShape split."""
    name = "economy"

    def __init__(self):
        self._year = defaultdict(float)  # flows this year, for summaries
        self._last = {}
        self._hungry = 0
        self._income: Dict[Any, float] = {}  # each household's usual monthly net income
        self._deaths_seen = 0
        self._estates = defaultdict(int)
        self._unemployed = 0
        self._months = 0

    def init_state(self, graph) -> Dict[int, Any]:
        self._graph = graph  # summarize reads the town's money
        self._deaths_seen = len(graph.deaths)
        for name, empty in (("household_money", dict), ("household_property", dict), ("employer", dict),
                            ("merchants", list), ("building_types", dict)):
            if not hasattr(graph, name):  # a town imported without the economy (test fixtures)
                setattr(graph, name, empty())
        return {resident_id: {} for resident_id in graph.nodes}

    def add_resident(self, graph, state, resident_id: int) -> None:
        state[resident_id] = {}
        key = household_key(graph.nodes[resident_id])
        if key not in graph.household_money:
            graph.household_money[key] = ARRIVAL_SAVINGS
            self._year["in: newcomers"] += ARRIVAL_SAVINGS

    def candidate_edges(self, graph, state):
        return []

    def edge_probability(self, edge, state_a, state_b, day: int) -> float:
        return 0.0

    def apply_effect(self, graph, state, a: int, b: int, day: int, rng: random.Random) -> List[Any]:
        return []

    @staticmethod
    def _wealth_per_person(graph) -> Dict[Any, float]:
        members = defaultdict(int)
        for node in graph.nodes.values():
            if node.alive:
                members[household_key(node)] += 1
        return {key: wealth(graph, key) / count for key, count in members.items()}

    def end_of_day(self, graph, state, day: int, rng: random.Random) -> List[Any]:
        for death in graph.deaths[self._deaths_seen:]:
            outcome = settle_estate(graph, death["resident_id"])
            if outcome:
                self._estates[outcome] += 1
            moved = join_family(graph, death["resident_id"])
            if moved:
                self._estates[moved] += 1
        self._deaths_seen = len(graph.deaths)
        if day % 30 == 0:
            self._month(graph, rng)
        if day % 365 == 0:
            self._update_class(graph)
            self._last = dict(self._year)
            self._year = defaultdict(float)
        return []

    def _pay(self, graph, from_key, to_key, amount: float) -> float:
        """Move up to `amount` between households (None = the outside world);
        returns what actually moved."""
        if from_key is not None:
            amount = min(amount, max(0.0, graph.household_money.get(from_key, 0.0)))
            graph.household_money[from_key] = graph.household_money.get(from_key, 0.0) - amount
        if to_key is not None:
            graph.household_money[to_key] = graph.household_money.get(to_key, 0.0) + amount
        return amount

    def _month(self, graph, rng: random.Random) -> None:
        self._months += 1
        month = 30 / 365
        alive = [n for n in graph.nodes.values() if n.alive]
        self._give_work(graph, alive, rng)
        by_occupation = defaultdict(list)
        for node in alive:
            by_occupation[job_kind(node.occupation)].append(node)
        sellers = [n for n in alive if job_kind(n.occupation) in LOCAL_SELLERS]
        merchants = [n for n in by_occupation["merchant"]]
        farmers = by_occupation["farmer"]
        income = defaultdict(float)

        # money in: property (land and houses; cash earns nothing: 7% on all
        # money compounded, +5% a year), public wages
        for key, owned in list(graph.household_property.items()):
            if owned > 0:
                gain = self._pay(graph, None, key, owned * PROPERTY_RETURN * month)
                income[key] += gain
                self._year["in: property"] += gain
        for node in alive:
            wage, payer = PAY.get(job_kind(node.occupation), (0.0, None))
            if payer == "public":
                gain = self._pay(graph, None, household_key(node), wage * month)
                income[household_key(node)] += gain
                self._year["in: public wages"] += gain

        # employers pay their workers; merchants sell the cloth outside
        for node in alive:
            kind = job_kind(node.occupation)
            wage, payer = PAY.get(kind, (UNSKILLED_WAGE, "master") if kind == "craft_hand" else (0.0, None))
            if payer in (None, "public", "day labour"):
                continue
            employer = self._employer(graph, node, payer, rng)
            if employer is None:
                continue
            boss = household_key(employer)
            paid = self._pay(graph, boss, household_key(node), wage * month)
            income[household_key(node)] += paid
            income[boss] -= paid  # a business cost, not living expenses
            if payer == "merchant" and kind == "outworker":
                sale = self._pay(graph, None, boss, paid * EXPORT_MARKUP)
                wool = self._pay(graph, boss, None, sale * RAW_WOOL_SHARE)
                income[boss] += sale - wool
                self._year["in: cloth exports"] += sale
                self._year["out: raw wool"] += wool

        # households buy their basket: grain from farmers and (imported)
        # merchants, the rest from workshops, shops and taverns
        members = defaultdict(list)
        for node in alive:
            members[household_key(node)].append(node)
        needs = {}
        self._hungry = 0
        for key, people in members.items():
            need = sum(CHILD_BASKET if (n.age or 0) < 12 else 1.0 for n in people) * BASKET_PER_PERSON * month
            needs[key] = need
            spend = min(need, max(0.0, graph.household_money.get(key, 0.0)))
            if spend < need * 0.999:
                self._hungry += 1
            grain = spend * GRAIN_SHARE_OF_BASKET
            self._buy(graph, key, grain * LOCAL_GRAIN_SHARE, farmers, rng, income)
            self._import(graph, key, grain * (1 - LOCAL_GRAIN_SHARE), merchants, rng, income)
            self._buy(graph, key, spend - grain, sellers, rng, income)

        # then everyone spends what they earned above their needs, minus what
        # they save. Income here is net: takings and wages in, wages and day
        # labour paid out (2026-09-29: counting only wages and property let
        # sellers hoard, +13% money a year). Saving tapers off as a household's
        # money nears SAVINGS_CUSHION_YEARS of its income, so no one piles up
        # money forever (a flat 20% saving did: masters +160 fl a year); the
        # rich spend their property income and keep their capital.
        # The decision uses the household's usual income from past months, not
        # this month's so far: takings and day labour arrive later in the month,
        # and deciding on a partial month quietly saved them (money +6.5k a year).
        hire = {household_key(s): max(0.0, income.get(household_key(s), 0.0)) * DAY_LABOUR_SHARE for s in sellers}
        for key in members:
            usual = self._income.get(key, income.get(key, 0.0))
            wealth = max(0.0, graph.household_money.get(key, 0.0))
            cushion = SAVINGS_CUSHION_YEARS * 12 * max(0.0, usual)
            saving = SAVING_SHARE * max(0.0, 1.0 - wealth / cushion) if cushion > 0 else SAVING_SHARE
            extra = (1.0 - saving) * max(0.0, usual - needs[key])
            # cash well beyond the cushion gets spent down (2026-09-29: without
            # this, merchants and masters kept gaining, town cash +4.4k a year)
            extra += EXCESS_CASH_SPENT_PER_YEAR * month * max(0.0, wealth - cushion)
            extra = min(extra, wealth)
            self._import(graph, key, extra * LUXURY_IMPORT_SHARE, merchants, rng, income)
            local = extra * (1 - LUXURY_IMPORT_SHARE)
            hire[key] = hire.get(key, 0.0) + local * DAY_LABOUR_OF_SPENDING  # builders, porters, carters
            self._buy(graph, key, local * (1 - DAY_LABOUR_OF_SPENDING), sellers, rng, income)

        # the commune spends what heirless estates left it: public works, purchases
        public = COMMUNE_SPENT_PER_YEAR * month * max(0.0, graph.household_money.get(COMMUNE, 0.0))
        if public > 0:
            hire[COMMUNE] = public * DAY_LABOUR_OF_SPENDING
            self._buy(graph, COMMUNE, public * (1 - DAY_LABOUR_OF_SPENDING), sellers, rng, income)
            self._year["out: commune spending"] += public
        self._hire_day_labour(graph, by_occupation["day_labourer"], hire, income, month, rng)
        for key in members:  # the month is complete: update each household's usual income
            usual = self._income.get(key, income.get(key, 0.0))
            self._income[key] = usual + (income.get(key, 0.0) - usual) * INCOME_MEMORY

    def _hire_day_labour(self, graph, labourers, budget, income, month: float, rng: random.Random) -> None:
        """Households pay for day labour out of their budget (sellers a share of
        their takings, everyone a share of their spending in town), spread over
        the labourers by how much work each found."""
        if not labourers:
            return
        total = sum(budget.values())
        if total <= 0:
            return
        found = [rng.random() for _ in labourers]  # share of the month's days each found work
        wanted = [UNSKILLED_WAGE * month * 2 * DAY_LABOUR_WORK * f for f in found]
        scale = min(1.0, total / max(1e-9, sum(wanted)))
        for node, want in zip(labourers, wanted):
            want *= scale
            for key in budget:
                if want <= 1e-9:
                    break
                paid = self._pay(graph, key, household_key(node), min(want, budget[key]))
                budget[key] -= paid
                want -= paid
                income[key] -= paid
                income[household_key(node)] += paid

    def _employer(self, graph, node, payer: str, rng: random.Random):
        """The living person paying this worker: the recorded employer, or
        whoever now holds the paying post at the same workplace."""
        employer_id = graph.employer.get(node.resident_id)
        if employer_id is not None and graph.nodes[employer_id].alive:
            return graph.nodes[employer_id]
        candidates = [n for n in graph.nodes.values() if n.alive and job_kind(n.occupation) == payer
                      and (payer == "merchant" or n.workplace_building_id == node.workplace_building_id)]
        if not candidates:
            return None
        chosen = rng.choice(candidates)
        graph.employer[node.resident_id] = chosen.resident_id
        return chosen

    def _give_work(self, graph, alive, rng: random.Random) -> None:
        """Unemployment (user, 2026-09-30): adults without work (come of age,
        arrived without a trade, or let go) look for it and find some with
        JOB_FIND_PER_MONTH chance; precarious work (putting-out, day labour)
        is lost with JOB_LOSS_PER_MONTH chance. Settles near
        loss / (loss + find) unemployed, about 5%. The unemployed earn nothing
        and live off their household."""
        merchants = [n.resident_id for n in alive if n.occupation == "merchant"]
        self._unemployed = 0
        for node in alive:
            if node.occupation in PRECARIOUS and rng.random() < JOB_LOSS_PER_MONTH:
                node.occupation = None
                graph.employer.pop(node.resident_id, None)
            if node.occupation is None and not node.is_noble and node.age is not None and node.age >= 18:
                if node.ses in RENTIER_CLASSES:
                    node.occupation = "rentier"
                    continue
                if rng.random() >= JOB_FIND_PER_MONTH:
                    self._unemployed += 1
                    continue
                if merchants and rng.random() < PUTTING_OUT_SHARE:
                    node.occupation = "outworker"
                    graph.employer[node.resident_id] = rng.choice(merchants)
                else:
                    node.occupation = "day_labourer"

    def _buy(self, graph, key, amount: float, sellers, rng: random.Random, income) -> None:
        """Bought in town: the seller's takings count as their income."""
        if amount <= 0 or not sellers:
            return
        seller = household_key(sellers[rng.randrange(len(sellers))])
        income[seller] += self._pay(graph, key, seller, amount)

    def _import(self, graph, key, amount: float, merchants, rng: random.Random, income) -> None:
        """Bought from outside through a merchant, who keeps a margin."""
        if amount <= 0:
            return
        if not merchants:
            self._year["out: imports"] += self._pay(graph, key, None, amount)
            return
        merchant = household_key(merchants[rng.randrange(len(merchants))])
        paid = self._pay(graph, key, merchant, amount)
        cost = self._pay(graph, merchant, None, paid * (1 - IMPORT_MARGIN))
        income[merchant] += paid - cost
        self._year["out: imports"] += cost

    def _update_class(self, graph) -> None:
        """Once a year: each resident's class from their household's resources
        per person (wealth plus a year of usual income) against the lines set at
        import."""
        lines = getattr(graph, "class_lines", None)
        if not lines:
            return
        per_person = resources_per_person(graph, {key: 12 * v for key, v in self._income.items()})
        for node in graph.nodes.values():
            if node.alive:
                node.ses = _capped(node, class_for(per_person.get(household_key(node), 0.0), node.ses, lines))

    def summarize(self, state) -> Dict[str, float]:
        # recomputed only when something it reads changed (speed-up 2026-09-30:
        # sorting every household's money every day cost more than the month)
        graph = self._graph
        signature = (self._months, len(graph.deaths), graph.alive_count, getattr(graph, "dowries", 0.0),
                     len(graph.household_money), self._unemployed, self._hungry)
        if signature != getattr(self, "_summary_signature", None):
            self._summary = self._compute_summary(graph)
            self._summary_signature = signature
        return self._summary

    def _compute_summary(self, graph) -> Dict[str, float]:
        living = {household_key(n) for n in graph.nodes.values() if n.alive}
        money = [max(0.0, wealth(graph, key)) for key in living]
        total = sum(money)
        top = sorted(money, reverse=True)[:max(1, len(money) // 10)]
        return {
            "economy_town_money": round(total, 1),  # cash and property
            "economy_town_cash": round(sum(max(0.0, graph.household_money.get(k, 0.0)) for k in living), 1),
            "economy_gini": round(gini(money), 3),
            # a few weeks' wages in hand aren't property
            "economy_propertyless_share": round(sum(1 for m in money if m < PROPERTYLESS_BELOW) / max(1, len(money)), 3),
            "economy_top10_share": round(sum(top) / total, 3) if total else 0.0,
            "economy_hungry_households": self._hungry,
            "economy_unemployed": self._unemployed,
            **{f"economy_class_{c}": sum(1 for n in graph.nodes.values() if n.alive and n.ses == c) for c in CLASSES},
            "economy_dowries": round(getattr(graph, "dowries", 0.0), 1),
            "economy_households": len(living),
            "economy_commune_cash": round(graph.household_money.get(COMMUNE, 0.0), 1),
            "economy_commune_property": round(graph.household_property.get(COMMUNE, 0.0), 1),
            **{f"economy_estates_{k.replace(' ', '_')}": v for k, v in self._estates.items()},
            **{f"economy_{k}": round(v, 1) for k, v in self._last.items()},
        }


# --- Households forming and passing on (economy slice 2, user 2026-09-30) ---

DOWRY_SHARE = 0.10  # book §7: a daughter's marriage moves ~5-15% of her family's wealth
FAMILY_TIES = ("spouse", "parent", "sibling")


def _move_wealth(graph, from_key, to_key, fraction: float) -> float:
    """Move `fraction` of a household's cash and property to another
    household (to_key None: to the commune, out of town). Returns the amount."""
    fraction = max(0.0, min(1.0, fraction))
    moved = 0.0
    for store in (graph.household_money, getattr(graph, "household_property", {})):
        amount = max(0.0, store.get(from_key, 0.0)) * fraction
        store[from_key] = store.get(from_key, 0.0) - amount
        if to_key is not None:
            store[to_key] = store.get(to_key, 0.0) + amount
        moved += amount
    return moved


def new_household_id(graph) -> int:
    ids = [n.household_id for n in graph.nodes.values() if isinstance(n.household_id, int)]
    graph.next_household_id = max(getattr(graph, "next_household_id", 0), max(ids, default=0) + 1)
    graph.next_household_id += 1
    return graph.next_household_id - 1


def _dependent_children(graph, node) -> List[int]:
    return [o for o in graph.neighbors(node.resident_id)
            if graph.get_edge(node.resident_id, o).source_type == "parent" and graph.nodes[o].alive
            and (graph.nodes[o].age or 0) < 18 and (graph.nodes[o].age or 0) < (node.age or 0)
            and graph.nodes[o].household_id == node.household_id]


def form_household(graph, a: int, b: int) -> None:
    """Newlyweds set up their own household (2026-09-30: households never
    split before, so they swelled, hunger rose and the rich thinned out). A
    spouse with children under 18 at home keeps that household and the other
    joins it. The bride's family gives a dowry (DOWRY_SHARE of its wealth);
    for two men or two women, each family gives half of that."""
    first, second = graph.nodes[a], graph.nodes[b]
    old_first, old_second = household_key(first), household_key(second)
    if _dependent_children(graph, first):
        home = old_first
    elif _dependent_children(graph, second):
        home = old_second
    else:
        home = new_household_id(graph)
    if hasattr(graph, "household_money"):
        graph.household_money.setdefault(home, 0.0)
        for node, old in ((first, old_first), (second, old_second)):
            if first.gender == second.gender:
                share = DOWRY_SHARE / 2
            else:
                share = DOWRY_SHARE if node.gender == "female" else 0.0
            if old != home and share:
                graph.dowries = getattr(graph, "dowries", 0.0) + _move_wealth(graph, old, home, share)
    first.household_id = second.household_id = home = _real_household_id(graph, home)
    for old in (old_first, old_second):
        follow_if_emptied(graph, old, home)


def follow_if_emptied(graph, old, home) -> None:
    """A household everyone has left (someone living alone marries, an heir
    moves into the noble house): what it still holds goes with them
    (2026-10-01: it stayed under a household nobody lived in, out of every count)."""
    if old != home and hasattr(graph, "household_money") \
            and not any(n.alive and household_key(n) == old for n in graph.nodes.values()):
        graph.household_money.setdefault(home, 0.0)
        _move_wealth(graph, old, home, 1.0)


def _real_household_id(graph, key):
    """An arrival living alone has a stand-in key: give them a real household id."""
    if not isinstance(key, tuple):
        return key
    home_id = new_household_id(graph)
    for store in (graph.household_money, getattr(graph, "household_property", {})):
        if key in store:
            store[home_id] = store.pop(key)
    return home_id


def settle_estate(graph, dead: int) -> Optional[str]:
    """What happens to a dead adult's share of their household's wealth
    (2026-09-30, user: to all children). A surviving spouse at home keeps it;
    otherwise it is split equally among all living children wherever they
    live; with no children it stays with the household. A household left
    with nobody goes to the siblings, then the nephews and nieces, like a
    title (2026-10-01: 183 heirless estates in 25 years went out of town,
    wealth 91k -> 70k fl); with no kin to the commune, which keeps it
    and spends its income in town (COMMUNE). Returns what happened, for counting."""
    node = graph.nodes[dead]
    key = household_key(node)
    if not hasattr(graph, "household_money") or (node.age or 0) < 18:
        return None
    others = [n for n in graph.nodes.values() if n.alive and household_key(n) == key]
    if any(graph.get_edge(dead, n.resident_id) is not None
           and graph.get_edge(dead, n.resident_id).source_type == "spouse" for n in others):
        return "spouse keeps it"
    adults = sum(1 for n in others if (n.age or 0) >= 18) + 1
    children = [graph.nodes[o] for o in graph.neighbors(dead)
                if graph.get_edge(dead, o).source_type == "parent" and graph.nodes[o].alive
                and (graph.nodes[o].age or 0) < (node.age or 0)]
    if children:
        # the dead adult's share of the household, split equally; children
        # still living in the household keep theirs where it is
        part = wealth(graph, key) / adults / len(children)
        for child in children:
            current = wealth(graph, key)
            if household_key(child) != key and current > 0:
                _move_wealth(graph, key, household_key(child), part / current)
        return "split among children"
    if others:
        return "stays in the household"
    siblings = _kin(graph, dead, "sibling")
    nephews = [n for s in graph.neighbors(dead) if graph.get_edge(dead, s).source_type == "sibling"
               for n in _kin(graph, s, "parent", younger=True)]
    for heirs, outcome in ((siblings, "to siblings"), (nephews, "to nephews and nieces")):
        if heirs:
            for share, heir in enumerate(heirs):  # equal parts: 1/n, then 1/(n-1) of what's left, ...
                _move_wealth(graph, key, household_key(heir), 1.0 / (len(heirs) - share))
            return outcome
    graph.household_money.setdefault(COMMUNE, 0.0)
    _move_wealth(graph, key, COMMUNE, 1.0)
    return "to the commune"


# the commune's household key. It keeps the land and houses it gets (like the
# Church's mortmain) and spends their income: selling them for cash that was
# then spent lost the 7% for good (2026-10-01 run: wealth 91k -> 74k fl)
COMMUNE = "commune"
COMMUNE_SPENT_PER_YEAR = EXCESS_CASH_SPENT_PER_YEAR  # C: on public works and purchases in town
LEFT_ALONE_MOVES_IN_AGE = 50  # C: a widow(er) this old moves in with a grown child


def _kin(graph, person: int, kind: str, younger: bool = False) -> List[Any]:
    age = graph.nodes[person].age or 0
    return [graph.nodes[o] for o in graph.neighbors(person)
            if graph.get_edge(person, o).source_type == kind and graph.nodes[o].alive
            and (not younger or (graph.nodes[o].age or 0) < age)]


def join_family(graph, dead: int) -> Optional[str]:
    """Who a death leaves alone moves in with family (2026-10-01: households
    shrank 3.6 -> 2.2 people in 25 years; Florence 1427 about 4): children
    all under 18 go to an adult sibling, a grandparent, then an aunt or uncle;
    a lone widow(er) of LEFT_ALONE_MOVES_IN_AGE or more to their eldest grown
    child. They bring the household's wealth. Nobles stay (their household
    holds the title). Returns what happened, for counting."""
    key = household_key(graph.nodes[dead])
    left = [n for n in graph.nodes.values() if n.alive and household_key(n) == key]
    if not left or any(n.is_noble for n in left):
        return None
    if all((n.age or 0) < 18 for n in left):
        ids = {n.resident_id for n in left}
        kin = ([s for n in left for s in _kin(graph, n.resident_id, "sibling") if (s.age or 0) >= 18],
               [g for p in _kin(graph, left[0].resident_id, "parent") for g in _kin(graph, p.resident_id, "parent")],
               [a for p in _kin(graph, left[0].resident_id, "parent") for a in _kin(graph, p.resident_id, "sibling")],
               _kin(graph, dead, "parent"), _kin(graph, dead, "sibling"))
        outcome = "orphans to family"
    elif len(left) == 1 and (left[0].age or 0) >= LEFT_ALONE_MOVES_IN_AGE:
        ids = {left[0].resident_id}
        kin = ([c for c in _kin(graph, left[0].resident_id, "parent", younger=True) if (c.age or 0) >= 18],)
        outcome = "widowed to a child"
    else:
        return None
    for group in kin:
        group = [n for n in group if n.resident_id not in ids and household_key(n) != key
                 and not n.is_noble and (n.age or 0) >= 18]
        if group:
            host = max(group, key=lambda n: n.age or 0)
            host.household_id = home = _real_household_id(graph, household_key(host))
            graph.household_money.setdefault(home, 0.0)
            _move_wealth(graph, key, home, 1.0)
            for n in left:
                n.household_id = home
            return outcome
    return None
