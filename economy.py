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

from food import FoodMarket

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
EXCESS_CASH_SPENT_PER_YEAR = 2.0  # C: share of cash above the cushion spent each year (user, 2026-10-01: at 0.5 a ~1,400 fl/yr trade surplus piled up, cash +55% in 4 years, very poor 15% -> 6-11%)
LUXURY_IMPORT_SHARE = 0.5  # C: of spending above the basket, bought from outside through merchants
DAY_LABOUR_OF_SPENDING = 0.4  # C: of spending above the basket in town, paid to day labourers
EXPORT_MARKUP = 1.7  # B-derived: 1338, 30,000 wool workers made ~1.2M fl of cloth (~40 fl each) on ~23 fl wages; 1.35 lost merchants 5.5% of each wage after raw wool
RAW_WOOL_SHARE = 0.3  # C: of the cloth's price, spent on raw wool bought outside
PROPERTYLESS_BELOW = 10.0  # C: under this (a few weeks of wages in hand) counts as owning nothing
DAY_LABOUR_SHARE = 0.3  # C: of local sellers' takings spent hiring day labour
ARRIVAL_SAVINGS = 5.0  # C: what a newcomer brings
# C: someone taking a master's, shopkeeper's or merchant's place brings the
# trade's capital (slice 4, 2026-10-01): with 5 fl they started poor
ARRIVAL_CAPITAL = {"master": 100.0, "shopkeep": 100.0, "barkeep": 100.0, "blacksmith": 100.0,
                   "trader": 100.0, "merchant": 500.0}

WEALTH_PER_PERSON = 45.0  # book §3a: small cities, 1427 (decided: Riverport is a small city)
PROPERTYLESS_SHARE = 0.25  # between the book's 14% (Florence 1427) and 38% (Prato 1372)
# book §3b, Prato 1300: share of wealth held by each tenth of those who own something
PRATO_1300_DECILES = [1.58, 1.82, 1.98, 2.14, 2.27, 2.49, 5.93, 6.69, 9.39, 65.72]
PRATO_1300_TOP1 = 29.18

MERCHANT_PER_RESIDENTS = 150  # C: ~13 merchants in a town of 1,900
MERCHANT_MIN_AGE = 30  # C: a merchant at import heads an established house
MERCHANT_KEEPS_JOB = ("master", "shopkeep", "barkeep", "blacksmith", "trader", "mage", "farmer", "noble")  # employers
PUTTING_OUT_SHARE = 0.5  # C: of the otherwise jobless, work at home for a merchant
RENTIER_HOUSEHOLD_SHARE = 0.1  # C: the richest tenth of households live off property, not wages
# houses and rent (slice 5, user 2026-10-01). Rents are missing from the
# research notes: a house earns its owner PROPERTY_RETURN of its value a
# year (the book's 7% rule), and lodging is RENT_SHARE of the basket
# (de la Roncière's budget shares, C), now paid as rent instead of to shops.
RENT_SHARE = 0.15  # C (0.10 tried 2026-10-01: homelessness barely moved, owner-occupiers doubled)
HOUSE_VALUE_PER_PERSON = BASKET_PER_PERSON * RENT_SHARE / PROPERTY_RETURN  # ~17.6 fl
HOUSE_CLASS_FACTOR = {"very_poor": 1.0, "poor": 1.0, "middling": 1.5, "rich": 3.0, "very_rich": 6.0}  # C: bigger houses
EVICT_AFTER_MONTHS = (3, 6)  # user: 3 to 6 months behind, longer the better landlord and tenants get on
HOST_MAX = 8  # C: kin or friends take in the evicted while their household has room
BUY_CUSHION_MONTHS = 3  # C: a tenant buys their house when it can pay and keep this many months of its basket
LANDLORD_CLASSES = ("rich", "very_rich")

# the commune's and the Church's money (slice 3 C, user 2026-10-01)
# C: tax on what's bought in town and imported, about what public wages cost
# (~0.4 fl a person a year; Florence 3-5 fl, book §9, paid for wars and debt
# too). 6% raised 2,000 fl a year against 850 of wages: the commune hoarded
# 35k fl in 25 years, drawn from households (2026-10-01 run)
GABELLE = 0.025
COMMUNE_FUND_MONTHS = 12  # C: the commune keeps a year of public wages against famine
COMMUNE_WORKS_SHARE = 0.5  # C: of cash above that fund, spent each month on public works
COMMUNE_RESERVE_MONTHS = 2  # C: the commune keeps this many months of public wages before repaying loans
FORCED_LOAN_RATE = 0.05  # C: prestanze, repaid with interest (the Monte paid about 5%)
DEVOUT = 0.7  # C: religiousness at which a middling or rich adult gives alms
ALMS_SHARE = 0.03  # C: of a devout member's share of the household's usual income, each month
CHURCH_GIVES_PER_MONTH = 0.5  # C: share of the Church's money it can give out in a month
# famine years (book §5c, §6: grain swings about 2.5x between good and bad
# years); harvests, stocks and the price itself are in food.py (goods slice 1)
FAMINE_CHANCE = 1 / 15  # C: a famine year every 10-20 years
FAMINE_PRICE = (1.8, 2.2)  # C: grain's cost outside in a famine year; with merchants' margin ~2.1-2.5x (1329: 31 s = 2.4x)
FAMINE_AT = 1.8  # grain priced this high is a famine: the commune's granary sells cheap

# beggars and death from hardship (slice 3 D, user 2026-10-01)
BEG_AFTER_MONTHS = 6  # C: a household hungry this many months in a row begins to beg
BEG_MIN_AGE = 7  # C
BEGGING_SHARE = 0.75  # C: each member this old joins in: when one begs, most of the household does
BEG_STOP_AFTER_FED = 3  # C: months fed in a row before a household stops begging
BEG_ASKS = 10  # C: people a beggar asks each month, among those they know
BEG_GIFT = 0.02  # C: fl a giver gives, about a soldo (0.05 was ~3 soldi: more than alms)
BEG_GIVE_BASE = 0.05  # C: chance someone the beggar asks gives, before piety and warmth
BEG_GIVE_PIETY = 0.3  # C: times the giver's religiousness
BEG_GIVE_WARMTH = 0.3  # C: times the giver's warmth toward the beggar
ROOMMATE_MAX = 6  # C: singles and small households share a room up to this many (4 left out the evicted, mostly families of 5+)
HOST_FOOD_COVER = 0.75  # C: kin take in the evicted if their income covers this share of both households' food (all of it left 150 on the street in year 1)
HARDSHIP_DEATH_PER_MONTH = 0.01  # C: at a whole basket short, for the under-5s and the over-60s
# famine (user to-do, 2026-10-01: nobody died in a famine the commune fed):
# the granary covers only part of what the hungry lack, and hunger in a
# famine kills (Villani: ~4,000 of Florence's ~90k in 1346-47, a severe one)
FAMINE_DEATH_PER_MONTH = 0.05  # C: a hungry under-5 or over-60 in a famine (0.015 killed 0.3% of the town)
FAMINE_ADULT_FACTOR = 0.2  # C: everyone else hungry in a famine, relative to that

# debt (slice 3 B, user 2026-10-01): who lends, at what rate
DEBT_FAMILY_WARMTH = 0.3  # C: a relative or friend this warm lends, without interest
DEBT_PATRON_RATE = 0.10  # C: an employer or rich acquaintance, a year (Florentine commercial loans 8-12%)
DEBT_LENDER_RATE = 0.25  # C: a moneylender, a year (licensed pawnbrokers 20-33%)
DEBT_MONEYLENDERS = 2  # C: the merchant houses with the most cash lend to anyone
DEBT_LENDER_LIMIT_MONTHS = 6  # C: a moneylender lends up to this many months of usual income
DEBT_LENDER_KEEPS_MONTHS = 3  # C: a lender keeps this many months of its own basket
DEBT_TERM_MONTHS = 24  # C: a debt is meant to be repaid over two years
DEBT_CUTOFF_MONTHS = 3  # C: nobody lends to a household this many months behind
DEBT_SEIZE_MONTHS = 12  # C: a year behind, a creditor (not family) seizes property
DEBT_RESENTMENT = 0.02  # C: each month behind cools the tie, on both sides
DEBT_FORGIVE_PER_MONTH = 0.2  # C: times the creditor's feeling for the debtor, each month behind
RENTIER_CLASSES = ("rich", "very_rich")  # a young adult of these classes lives off property too
SERVANT_CLASS_CAP = "poor"  # a live-in servant isn't rich because the household is
UNEMPLOYED_AT_START = 0.05  # C: of the otherwise jobless, still looking for work at import
JOB_FIND_PER_MONTH = 0.2  # C: about 4 months to find work
JOB_LOSS_PER_MONTH = 0.01  # C: putting-out and day labour are precarious
PRECARIOUS = ("outworker", "day_labourer")
# teenagers work (2026-10-01: none of 257 aged 10-17 did, and a quarter of
# households earned less than food and rent from the first month): from
# WORKING_AGE the young of households that aren't rich card and spin wool for
# a merchant, putting-out work largely done by women and children, at a share of the wage
WORKING_AGE = 12  # C
TEEN_WAGE_SHARE = 1 / 3  # C: of the adult wage, until 18
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
    _assign_houses(graph, rng)
    _set_class_lines(graph, rng)


def _assign_houses(graph, rng) -> None:
    """Who owns each home building (slice 5): the richest household living
    there if its property covers the house (owner-occupiers), else a rich
    household elsewhere, weighted by property (landlords: the user's
    merchants and rich owning the homes of the poor and middling); with
    nobody able to, the Church. A house's value comes out of its owner's
    property, so no wealth is invented, except the Church's."""
    graph.houses, graph.house_wealth = {}, {}
    living = defaultdict(list)
    for node in graph.nodes.values():
        if node.alive and node.home_building_id is not None:
            living[node.home_building_id].append(node)
    prop = graph.household_property
    pool = _landlord_pool(graph)
    for building in sorted(living):
        people = living[building]
        top = max(people, key=lambda n: CLASSES.index(n.ses) if n.ses in CLASSES else 1).ses
        value = HOUSE_VALUE_PER_PERSON * len(people) * HOUSE_CLASS_FACTOR.get(top, 1.0)
        residents = sorted({household_key(n) for n in people}, key=lambda k: -prop.get(k, 0.0))
        owner = next((k for k in residents if prop.get(k, 0.0) >= value), None)
        if owner is None:
            landlords = [k for k in pool if prop.get(k, 0.0) >= value and k not in residents]
            owner = rng.choices(landlords, weights=[prop[k] for k in landlords])[0] if landlords else CHURCH
        if owner != CHURCH:
            prop[owner] -= value
        graph.houses[building] = {"owner": None, "value": value}
        set_house_owner(graph, building, owner)


def _landlord_pool(graph) -> List[Any]:
    keys = set()
    for node in graph.nodes.values():
        if node.alive and (node.ses in LANDLORD_CLASSES or node.occupation == "merchant" or node.is_noble):
            keys.add(household_key(node))
    return sorted(keys, key=str)


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


def _set_class_lines(graph, rng, yearly_income: Optional[Dict[Any, float]] = None) -> None:
    """Rank residents by resources per person, cut them into the town's
    class shares (params.class_shares) and keep the cut points as the fixed
    lines people are judged against from then on. At import the income is
    what each job is expected to pay; a year later the lines are cut once
    more from what households actually earned (see _update_class)."""
    per_person = resources_per_person(graph, yearly_income if yearly_income is not None else _expected_income(graph))
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
    """The class for these resources, with the same margin both ways: someone
    keeps their class until they fall below CLASS_KEEP_SHARE of its line, and
    rises only once clear of the next line by as much (2026-10-01: rising on
    touching a line but falling only 20% under it ratcheted the town upward,
    very poor 15% -> 5-8% in five years in every seed)."""
    level = sum(1 for line in lines if resources >= line)
    held = CLASSES.index(current) if current in CLASSES else 0
    if level < held and resources >= lines[held - 1] * CLASS_KEEP_SHARE:
        return current
    if level > held:
        return CLASSES[max(held, sum(1 for line in lines if resources >= line / CLASS_KEEP_SHARE))]
    return CLASSES[level]


def _jobless_adults(graph) -> List[Any]:
    return [n for n in sorted(graph.nodes.values(), key=lambda n: n.resident_id)
            if n.alive and n.age is not None and n.age >= 18 and n.occupation is None and not n.is_noble]


def _assign_jobs(graph, townshape_wealth, rng) -> None:
    alive = sum(1 for n in graph.nodes.values() if n.alive)
    jobless = _jobless_adults(graph)
    rng.shuffle(jobless)

    # the richest households with jobless adults (their adults live off property, below)
    by_household = defaultdict(list)
    for node in jobless:
        by_household[household_key(node)].append(node)
    richest = sorted(by_household, key=lambda h: -townshape_wealth.get(h, 0.0) if not isinstance(h, tuple) else 0.0)
    # the head of each of the richest houses trades (user, 2026-10-01: merchants
    # were among a town's richest), whatever job TownShape gave them, unless
    # others depend on it: an employer, or a public post (guards, clergy).
    # A head of house, aged 30+: the eldest jobless adult was often a young
    # child who married out and left the capital behind. TownShape's
    # generator should do this on integration (docs/townshape-integration.md)
    adults = defaultdict(list)
    for node in graph.nodes.values():
        if (node.alive and not node.is_noble and node.age is not None and node.age >= MERCHANT_MIN_AGE
                and job_kind(node.occupation) not in MERCHANT_KEEPS_JOB
                and PAY.get(job_kind(node.occupation), (0.0, None))[1] != "public"):
            adults[household_key(node)].append(node)
    merchants = []
    for key in sorted(adults, key=lambda h: -townshape_wealth.get(h, 0.0) if not isinstance(h, tuple) else 0.0):
        if len(merchants) >= max(2, round(alive / MERCHANT_PER_RESIDENTS)):
            break
        head = max(adults[key], key=lambda n: n.age)
        head.occupation, head.workplace_building_id = "merchant", None
        merchants.append(head.resident_id)
    jobless = [n for n in jobless if n.occupation is None]
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
    if merchants:
        for node in sorted(graph.nodes.values(), key=lambda n: n.resident_id):
            if (_working_teen(node) and node.occupation is None and household_key(node) not in wealthy
                    and rng.random() >= UNEMPLOYED_AT_START):
                node.occupation = "outworker"
                graph.employer[node.resident_id] = rng.choice(merchants)


def _working_teen(node) -> bool:
    """A young person of a household that isn't rich, old enough to work."""
    return (node.alive and not node.is_noble and node.age is not None and WORKING_AGE <= node.age < 18
            and node.ses not in RENTIER_CLASSES)


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


def house_wealth(graph, key) -> float:
    return getattr(graph, "house_wealth", {}).get(key, 0.0)


def set_house_owner(graph, building, owner) -> None:
    """Change who owns a house, keeping each owner's total house value current."""
    house = graph.houses[building]
    totals = graph.house_wealth
    if house["owner"] is not None:
        totals[house["owner"]] = totals.get(house["owner"], 0.0) - house["value"]
    house["owner"] = owner
    totals[owner] = totals.get(owner, 0.0) + house["value"]


def pass_houses(graph, old, new) -> None:
    for building, house in getattr(graph, "houses", {}).items():
        if house["owner"] == old:
            set_house_owner(graph, building, new)


def wealth(graph, key) -> float:
    """A household's cash plus property."""
    return (graph.household_money.get(key, 0.0) + getattr(graph, "household_property", {}).get(key, 0.0)
            + house_wealth(graph, key))


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
        self._harvest = 1.0  # grain's price this month, times normal (the food market's)
        self.food = FoodMarket(13 / FLORIN_IN_SOLDI, LOCAL_GRAIN_SHARE, FAMINE_CHANCE, FAMINE_PRICE, FAMINE_AT,
                               IMPORT_MARGIN, CHILD_BASKET)  # goods slice 1
        self._fed_months: Dict[Any, int] = {}  # household -> months fed in a row, while it begs
        self._hardship_deaths = 0
        self._evictions = 0
        self._houses_bought = 0
        self._famines = 0
        self._public_bill = 0.0

    def init_state(self, graph) -> Dict[int, Any]:
        self._graph = graph  # summarize reads the town's money
        self._deaths_seen = len(graph.deaths)
        # the jobless at import, until the first month's count (it read 0 for a month)
        self._unemployed = sum(1 for n in graph.nodes.values() if n.alive and not n.is_noble and (n.age or 0) >= 18
                               and n.ses not in RENTIER_CLASSES and n.occupation is None)
        for name, empty in (("household_money", dict), ("household_property", dict), ("employer", dict),
                            ("merchants", list), ("building_types", dict), ("debts", list),
                            ("houses", dict), ("house_wealth", dict), ("rent_behind", dict)):
            if not hasattr(graph, name):  # a town imported without the economy (test fixtures)
                setattr(graph, name, empty())
        return {resident_id: {} for resident_id in graph.nodes}

    def add_resident(self, graph, state, resident_id: int) -> None:
        state[resident_id] = {}
        key = household_key(graph.nodes[resident_id])
        if key not in graph.household_money:
            brought = ARRIVAL_CAPITAL.get(job_kind(graph.nodes[resident_id].occupation), ARRIVAL_SAVINGS)
            graph.household_money[key] = brought
            self._year["in: newcomers"] += brought

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
            if death["cause"] == "moved away":  # left with their money: no estate
                continue
            outcome = settle_estate(graph, death["resident_id"])
            if outcome:
                self._estates[outcome] += 1
            moved = join_family(graph, death["resident_id"])
            if moved:
                self._estates[moved] += 1
            if pass_on_merchant_house(graph, death["resident_id"]):
                self._estates["merchant house to an heir"] += 1
        self._deaths_seen = len(graph.deaths)
        if day % 30 == 0:
            self._month(graph, rng, day)
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

    def _month(self, graph, rng: random.Random, day: int = 0) -> None:
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
        # public wages come from the commune (user, 2026-10-01: its gabelle,
        # its land); when it runs short the richest lend to it (prestanze)
        public = [(node, PAY[job_kind(node.occupation)][0] * month) for node in alive
                  if PAY.get(job_kind(node.occupation), (0.0, None))[1] == "public"]
        bill = sum(wage for _, wage in public)
        self._public_bill = bill
        self._commune_borrow(graph, bill - graph.household_money.get(COMMUNE, 0.0), alive)
        for node, wage in public:
            gain = self._pay(graph, COMMUNE, household_key(node), wage)
            income[household_key(node)] += gain
            self._year["in: public wages"] += gain
            self._year["public wages unpaid"] += wage - gain

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
            if (node.age or 0) < 18:
                wage *= TEEN_WAGE_SHARE
            paid = self._pay(graph, boss, household_key(node), wage * month)
            income[household_key(node)] += paid
            income[boss] -= paid  # a business cost, not living expenses
            if payer == "merchant" and kind == "outworker":
                sale = self._pay(graph, None, boss, paid * EXPORT_MARKUP)
                wool = self._pay(graph, boss, None, sale * RAW_WOOL_SHARE)
                income[boss] += sale - wool
                self._year["in: cloth exports"] += sale
                self._year["out: raw wool"] += wool

        # households buy their basket: grain as bread (the food market, goods
        # slice 1), the rest from workshops, shops and taverns
        members = defaultdict(list)
        for node in alive:
            members[household_key(node)].append(node)
        if self._months % 12 == 1:  # a new harvest year
            self.food.harvest(self, graph, members, farmers, merchants, rng, income)
        else:
            self.food.update_price(members)
        self.food.start_month(members)
        self._harvest, self._famines = self.food.price, self.food.famines
        basket = BASKET_PER_PERSON * (1 - GRAIN_SHARE_OF_BASKET)  # what isn't grain
        if graph.houses:  # lodging is paid as rent (slice 5), after food
            basket -= BASKET_PER_PERSON * RENT_SHARE
        shops = self._tied_shops(graph, members, sellers)
        grain_cost = {key: self.food.grain_cost(key, people) for key, people in members.items()}
        needs = {key: sum(CHILD_BASKET if (n.age or 0) < 12 else 1.0 for n in people) * basket * month
                 + grain_cost[key] for key, people in members.items()}
        bakers = by_occupation.get("master", [])
        bakers = [n for n in bakers if n.occupation == "baker"]
        church_budget = CHURCH_GIVES_PER_MONTH * max(0.0, graph.household_money.get(CHURCH, 0.0))
        self._hungry = 0
        graph.hunger_last = getattr(graph, "hunger", {}) or {}  # hoarders' customers remember (food.py)
        graph.hunger = {}  # household -> share of this month's basket it couldn't buy (stress reads it)
        for key, people in members.items():
            need = needs[key]
            if graph.household_money.get(key, 0.0) < need:  # borrow before going hungry (slice 3 B)
                self._borrow(graph, key, people, need - max(0.0, graph.household_money.get(key, 0.0)),
                             needs, members, merchants)
            short = need - max(0.0, graph.household_money.get(key, 0.0))
            if short > 0 and church_budget > 0:  # alms, through the priests
                given = self._pay(graph, CHURCH, key, min(short, church_budget))
                church_budget -= given
                short -= given
                self._year["church: gave to the hungry"] += given
            spend = min(need, max(0.0, graph.household_money.get(key, 0.0)))
            if spend < need * 0.999:
                self._hungry += 1
                graph.hunger[key] = 1.0 - spend / need
            before = graph.household_money.get(key, 0.0)  # bread first, then the rest
            self.food.feed(self, graph, key, people, min(spend, grain_cost[key]), bakers, farmers, merchants,
                           rng, income)
            self._buy(graph, key, spend - (before - graph.household_money.get(key, 0.0)), sellers, rng, income, shops)

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
            self._buy(graph, key, local * (1 - DAY_LABOUR_OF_SPENDING), sellers, rng, income, shops)

        # public works keep the city running: walls, streets, bridges (day
        # labour and purchases in town), from what the commune holds beyond its fund
        works = COMMUNE_WORKS_SHARE * max(0.0, graph.household_money.get(COMMUNE, 0.0)
                                          - COMMUNE_FUND_MONTHS * self._public_bill)
        if works > 0:
            hire[COMMUNE] = works * DAY_LABOUR_OF_SPENDING
            self._buy(graph, COMMUNE, works * (1 - DAY_LABOUR_OF_SPENDING), sellers, rng, income)
            self._year["commune: public works"] += works
        self._collect_alms(graph, members)
        needs[COMMUNE] = COMMUNE_RESERVE_MONTHS * self._public_bill
        self._housing(graph, members, needs, income, rng)
        self._repay_debts(graph, needs, members, rng)
        self._sell_commune_land(graph, members)
        self._hire_day_labour(graph, by_occupation["day_labourer"], hire, income, month, rng)
        self._hardship(graph, members, rng, day)
        for key in members:  # the month is complete: update each household's usual income
            usual = self._income.get(key, income.get(key, 0.0))
            self._income[key] = usual + (income.get(key, 0.0) - usual) * INCOME_MEMORY

    def _housing(self, graph, members, needs, income, rng: random.Random) -> None:
        """Once food is bought (user: food first): tenants pay rent; a tenant
        who can buy its house does; a household behind on rent for 3 to 6
        months (longer the better it gets on with its landlord) is evicted,
        to kin or friends with room, or onto the street as beggars; the
        homeless who can pay rent find a home again."""
        if not graph.houses:
            return
        # houses whose owners are gone go to the commune (moved away, died out)
        for building, house in graph.houses.items():
            if house["owner"] not in members and house["owner"] not in (COMMUNE, CHURCH):
                set_house_owner(graph, building, COMMUNE)
        home = {}  # household -> the building it lives in
        in_building = defaultdict(list)
        people_in = defaultdict(int)  # building -> people living there
        for key, people in members.items():
            buildings = [n.home_building_id for n in people if n.home_building_id in graph.houses]
            if buildings:
                home[key] = max(set(buildings), key=buildings.count)
                in_building[home[key]].append(key)
                people_in[home[key]] += len(people)
        month = 30 / 365
        for key, people in members.items():
            building = home.get(key)
            if building is None:
                if all(n.home_building_id is None for n in people):
                    self._rehouse(graph, key, people, needs, rng)
                continue
            house = graph.houses[building]
            if house["owner"] == key:
                continue
            cash = graph.household_money.get(key, 0.0)
            # a landlord living elsewhere sells to a tenant who can pay; one who
            # lives there keeps it (a co-tenant forcing sales made houses change
            # hands back and forth: 648 sales of 226 houses in 25 years)
            if (house["owner"] not in in_building[building]
                    and cash >= house["value"] + BUY_CUSHION_MONTHS * needs.get(key, 0.0)):
                self._pay(graph, key, house["owner"], house["value"])  # bought from the owner (user)
                set_house_owner(graph, building, key)
                self._houses_bought += 1
                graph.rent_behind.pop(key, None)
                continue
            # split by people, the space each household takes (split by household,
            # a single paid as much as a family of six)
            due = house["value"] * PROPERTY_RETURN * month * len(people) / people_in[building]
            owed = graph.rent_behind.get(key, 0.0) + due  # this month's rent and any arrears
            paid = self._pay(graph, key, house["owner"], owed)
            income[house["owner"]] += paid
            income[key] -= paid
            self._year["rent: paid"] += paid
            if paid + 1e-9 >= owed:
                graph.rent_behind.pop(key, None)
                continue
            # what's still owed, in months of rent: part-payments count (every
            # short month counted as a whole month behind: 59 evictions in year 1)
            graph.rent_behind[key] = owed - paid
            grace = EVICT_AFTER_MONTHS[0] + round((EVICT_AFTER_MONTHS[1] - EVICT_AFTER_MONTHS[0])
                                                  * max(0.0, self._affinity(graph, people, members.get(house["owner"], ()))))
            if graph.rent_behind[key] >= grace * due:
                graph.rent_behind.pop(key, None)
                self._evict(graph, key, people, members, needs)

    @staticmethod
    def _affinity(graph, tenants, owners) -> float:
        """How well tenants and landlord get on: their warmest tie, both ways averaged (0 without one)."""
        best = 0.0
        for owner in owners:
            ties = graph.ties_of(owner.resident_id)
            for tenant in tenants:
                edge = ties.get(tenant.resident_id)
                if edge is not None:
                    best = max(best, (edge.valence_a_to_b + edge.valence_b_to_a) / 2)
        return best

    def _evict(self, graph, key, people, members, needs) -> None:
        """Evicted: family or friends who like them take them in, if they can
        feed them too (user, 2026-10-01: taken in by anyone, the poorest were
        pooled into other households and nobody went hungry); else single
        people and small households move in with singles they know who rent
        (the user's point: singles clubbed together to rent a small house);
        else the street."""
        self._evictions += 1
        hosts, roommates = [], []
        for person in people:
            for other, edge in graph.ties_of(person.resident_id).items():
                host = graph.nodes[other]
                host_key = household_key(host)
                if not host.alive or host_key == key or host.home_building_id is None:
                    continue
                feeling = edge.valence_a_to_b if edge.resident_a == other else edge.valence_b_to_a
                household = members.get(host_key, ())
                if ((edge.source_type in FAMILY_TIES or edge.source_type == "friend") and feeling >= 0.3
                        and len(household) + len(people) <= HOST_MAX
                        and self._income.get(host_key, 0.0) >= HOST_FOOD_COVER * (needs.get(host_key, 0.0) + needs.get(key, 0.0))):
                    hosts.append((feeling, other))
                elif (feeling >= 0 and len(people) <= ROOMMATE_MAX and len(household) + len(people) <= ROOMMATE_MAX
                      and all((n.age or 0) >= 18 for n in household)):
                    roommates.append((feeling, other))
        for found, kind in ((hosts, "evicted: taken in"), (roommates, "evicted: shared a room")):
            if found:
                host = graph.nodes[max(found)[1]]
                self._join(graph, key, people, host)
                self._year[kind] += len(people)
                return
        for node in people:  # onto the street: homeless people beg (user)
            node.home_building_id = None
            if (node.age or 0) >= BEG_MIN_AGE and not node.is_noble:
                node.beggar = True
        self._year["evicted: onto the street"] += len(people)

    @staticmethod
    def _join(graph, key, people, host) -> None:
        """`people` (household `key`) move into `host`'s household and home, with their money and debts."""
        new = _real_household_id(graph, household_key(host))
        host.household_id = new
        graph.household_money.setdefault(new, 0.0)
        _move_wealth(graph, key, new, 1.0)
        _retarget_debts(graph, key, new)
        for node in people:
            node.household_id, node.home_building_id = new, host.home_building_id

    def _rehouse(self, graph, key, people, needs, rng: random.Random) -> None:
        """The homeless find a home again once they hold a month's rent and
        food. Small homeless households pool with homeless people they know
        first, to rent a room together (user, 2026-10-01)."""
        if len(people) <= ROOMMATE_MAX and graph.household_money.get(key, 0.0) > 0:
            for person in people:
                for other, edge in graph.ties_of(person.resident_id).items():
                    mate = graph.nodes[other]
                    mate_key = household_key(mate)
                    feeling = edge.valence_a_to_b if edge.resident_a == other else edge.valence_b_to_a
                    if (mate.alive and mate.home_building_id is None and mate_key != key and feeling >= 0
                            and sum(1 for n in graph.nodes.values() if n.alive and household_key(n) == mate_key)
                            + len(people) <= ROOMMATE_MAX):
                        # ponytail: the mate's household still sits in this month's members
                        # under its old key; it simply finds no one left and skips
                        mates = [n for n in graph.nodes.values() if n.alive and household_key(n) == mate_key]
                        new = _real_household_id(graph, key)
                        for node in people:
                            node.household_id = new
                        graph.household_money.setdefault(new, 0.0)
                        _move_wealth(graph, mate_key, new, 1.0)
                        _retarget_debts(graph, mate_key, new)
                        for node in mates:
                            node.household_id = new
                        key, people = new, people + mates
                        self._year["homeless: pooled to rent"] += len(mates)
                        break
                else:
                    continue
                break
        building = rng.choice(sorted(graph.houses))
        rent = graph.houses[building]["value"] * PROPERTY_RETURN / 12
        if graph.household_money.get(key, 0.0) >= rent + needs.get(key, 0.0):  # a month's rent and food
            for node in people:
                node.home_building_id = building
                node.beggar = False
            self._year["homeless: found a home"] += len(people)

    def _commune_borrow(self, graph, amount: float, alive) -> None:
        """Prestanze: the commune borrows what it lacks from the households
        with the most cash, each keeping a year of its own basket, at FORCED_LOAN_RATE."""
        if amount <= 1e-9:
            return
        heads = {}
        for node in alive:  # one person per household, to hang the debt on
            heads.setdefault(household_key(node), node.resident_id)
        for key in sorted(heads, key=lambda k: -graph.household_money.get(k, 0.0))[:10]:
            size = sum(1 for n in alive if household_key(n) == key)
            spare = graph.household_money.get(key, 0.0) - BASKET_PER_PERSON * size  # keeps a year of its basket
            if spare <= 1e-9:
                break  # sorted by cash: nobody further down can lend either
            lent = self._pay(graph, key, COMMUNE, min(amount, spare))
            graph.debts.append({"debtor": COMMUNE, "creditor": key, "debtor_person": None,
                                "creditor_person": heads[key], "amount": lent, "rate": FORCED_LOAN_RATE,
                                "kind": "forced loan", "behind": 0})
            self._year["commune: forced loans"] += lent
            amount -= lent
            if amount <= 1e-9:
                return

    def _hardship(self, graph, members, rng: random.Random, day: int) -> None:
        """The month's hunger, after all help (user, 2026-10-01): counts each
        member's hungry months; a household hungry BEG_AFTER_MONTHS begins to
        beg (most members; begging is by household), and stops after
        BEG_STOP_AFTER_FED months fed. Beggars ask people they know: the
        devout and those who like them give most. Small children and the old
        can die of hardship while hungry."""
        for key, people in members.items():
            short = graph.hunger.get(key, 0.0)
            for node in people:
                node.hungry_months = node.hungry_months + 1 if short > 0 else 0
            if short > 0:
                self._fed_months[key] = 0
                if people[0].hungry_months >= BEG_AFTER_MONTHS and not any(n.beggar for n in people):
                    for node in people:
                        if (node.age or 0) >= BEG_MIN_AGE and not node.is_noble and rng.random() < BEGGING_SHARE:
                            node.beggar = True
                famine = self._harvest >= FAMINE_AT
                for node in people:
                    frail = (node.age or 0) < 5 or (node.age or 0) >= 60
                    chance = HARDSHIP_DEATH_PER_MONTH * short if frail else 0.0
                    if famine:
                        chance += FAMINE_DEATH_PER_MONTH * (1.0 if frail else FAMINE_ADULT_FACTOR)
                    if chance and rng.random() < chance:
                        graph.record_death(node.resident_id, day, "famine" if famine else "hardship")
                        self._hardship_deaths += 1
            elif any(n.beggar for n in people) and not (graph.houses and all(n.home_building_id is None for n in people)):
                # fed again, and not homeless: the homeless beg until they have a home (user)
                self._fed_months[key] = self._fed_months.get(key, 0) + 1
                if self._fed_months[key] >= BEG_STOP_AFTER_FED:
                    for node in people:
                        node.beggar = False
        # alms from people who know the beggar (user, 2026-10-01: not a sure
        # thing): mostly the devout and those who like them; each person gives
        # to one beggar a month at most, so more beggars share less; the poor
        # give half as often, the very poor and other beggars not at all
        given = set()
        for key, people in members.items():
            for node in people:
                if not (node.beggar and node.alive):
                    continue
                ties = list(graph.ties_of(node.resident_id).items())
                for other, edge in rng.sample(ties, min(BEG_ASKS, len(ties))):
                    giver = graph.nodes[other]
                    if (not giver.alive or giver.beggar or giver.ses == "very_poor" or other in given
                            or household_key(giver) == key):
                        continue
                    feeling = edge.valence_a_to_b if edge.resident_a == other else edge.valence_b_to_a
                    chance = BEG_GIVE_BASE + BEG_GIVE_PIETY * giver.religiousness + BEG_GIVE_WARMTH * max(0.0, feeling)
                    if rng.random() < chance * (0.5 if giver.ses == "poor" else 1.0):
                        given.add(other)
                        self._year["begging: alms"] += self._pay(graph, household_key(giver), key, BEG_GIFT)

    def _collect_alms(self, graph, members) -> None:
        """Devout middling and rich adults give a little to the Church each month (user, 2026-10-01)."""
        for key, people in members.items():
            usual = self._income.get(key, 0.0)
            if usual <= 0:
                continue
            adults = [n for n in people if (n.age or 0) >= 18]
            devout = [n for n in adults if n.ses in ("middling", "rich", "very_rich") and n.religiousness >= DEVOUT]
            if devout:
                given = self._pay(graph, key, CHURCH, ALMS_SHARE * usual * len(devout) / len(adults))
                self._year["church: alms"] += given

    def _spare(self, graph, key, needs) -> float:
        """Cash a household can lend: what it holds beyond DEBT_LENDER_KEEPS_MONTHS of its basket."""
        return graph.household_money.get(key, 0.0) - DEBT_LENDER_KEEPS_MONTHS * needs.get(key, 0.0)

    def _borrow(self, graph, key, people, shortfall: float, needs, members, merchants) -> None:
        """A household short of its basket borrows (user, 2026-10-01): from
        family and friends who care for it, without interest; then from an
        employer or a rich household it knows; then from a moneylender (the
        two merchant houses with the most cash). None lends to a household
        behind on a debt; a moneylender only up to DEBT_LENDER_LIMIT_MONTHS of
        its usual income. Each debt sits on the tie between the two people."""
        debts = graph.debts
        if any(d["debtor"] == key and d["behind"] >= DEBT_CUTOFF_MONTHS for d in debts):
            return
        family, patrons = [], []
        for person in people:
            pid = person.resident_id
            boss = graph.employer.get(pid)
            if boss is not None and graph.nodes[boss].alive:
                patrons.append((boss, pid))
            for other, edge in graph.ties_of(pid).items():
                lender = graph.nodes[other]
                if not lender.alive or household_key(lender) == key:
                    continue
                feeling = edge.valence_a_to_b if edge.resident_a == other else edge.valence_b_to_a
                if edge.source_type in ("parent", "sibling", "spouse", "friend") and feeling >= DEBT_FAMILY_WARMTH:
                    family.append((other, pid))
                elif lender.ses in RENTIER_CLASSES and feeling >= 0:
                    patrons.append((other, pid))
        houses = sorted({household_key(n) for n in merchants}, key=lambda k: -graph.household_money.get(k, 0.0))
        lenders = [(k, None) for k in houses[:DEBT_MONEYLENDERS]]
        owed_to_lenders = sum(d["amount"] for d in debts if d["debtor"] == key and d["kind"] == "moneylender")
        limit = DEBT_LENDER_LIMIT_MONTHS * max(0.0, self._income.get(key, 0.0)) - owed_to_lenders
        for group, kind, rate in ((family, "family", 0.0), (patrons, "patron", DEBT_PATRON_RATE),
                                  (lenders, "moneylender", DEBT_LENDER_RATE)):
            for lender, borrower in group:
                if shortfall <= 1e-9:
                    return
                lender_key = household_key(graph.nodes[lender]) if kind != "moneylender" else lender
                if lender_key == key:
                    continue
                amount = min(shortfall, self._spare(graph, lender_key, needs))
                if kind == "moneylender":
                    amount = min(amount, limit)
                if amount <= 1e-9:
                    continue
                if kind == "moneylender":
                    limit -= amount
                    lender = next(n.resident_id for n in members[lender_key] if n.occupation == "merchant")
                self._pay(graph, lender_key, key, amount)
                shortfall -= amount
                debts.append({"debtor": key, "creditor": lender_key, "debtor_person": borrower,
                              "creditor_person": lender, "amount": amount, "rate": rate, "kind": kind, "behind": 0})
                self._year[f"debt: lent by {kind}"] += amount

    def _repay_debts(self, graph, needs, members, rng: Optional[random.Random] = None) -> None:
        """Monthly: interest accrues; the debtor pays what it holds beyond
        next month's basket, up to the debt. A month that pays less than the
        interest and a 24th of the debt counts as behind: the tie between the
        two cools on both sides, for a year at most, and the creditor may
        forgive what's left, likelier the more they like the debtor (user,
        2026-10-01); a year behind, one who hasn't seizes property. The
        commune repays forced loans to noble and very rich households with
        its heirless land first (user, 2026-10-01).
        Debts of a household with nobody left are settled by its estate
        (settle_estate) or written off."""
        kept = []
        for debt in graph.debts:
            key, creditor = debt["debtor"], debt["creditor"]
            if (key not in members and key != COMMUNE) or (creditor not in members and creditor != COMMUNE):
                self._year["debt: written off"] += debt["amount"]
                continue
            if debt["kind"] == "forced loan" and getattr(graph, "commune_lots", None) and any(
                    n.is_noble or n.ses == "very_rich" for n in members.get(creditor, ())):
                self._repay_in_land(graph, debt)
                if debt["amount"] <= 0.01:
                    continue
            interest = debt["amount"] * debt["rate"] / 12
            debt["amount"] += interest
            due = interest + debt["amount"] / DEBT_TERM_MONTHS
            paid = self._pay(graph, key, creditor,
                             min(debt["amount"], max(0.0, graph.household_money.get(key, 0.0) - needs.get(key, 0.0))))
            debt["amount"] -= paid
            self._year["debt: repaid"] += paid
            if paid + 1e-9 < due:
                debt["behind"] += 1
                if debt["behind"] <= DEBT_SEIZE_MONTHS:  # resentment builds for a year, then settles
                    self._cool(graph, debt)
                if rng is not None and rng.random() < DEBT_FORGIVE_PER_MONTH * max(0.0, self._feeling(graph, debt)):
                    self._year[f"debt: forgiven ({debt['kind']})"] += debt["amount"]
                    continue
                if debt["behind"] >= DEBT_SEIZE_MONTHS and debt["kind"] != "forced loan":
                    owned = max(0.0, graph.household_property.get(key, 0.0))
                    seized = min(owned, debt["amount"])
                    if seized > 0:
                        graph.household_property[key] -= seized
                        graph.household_property[creditor] = graph.household_property.get(creditor, 0.0) + seized
                        debt["amount"] -= seized
                        self._year["debt: property seized"] += seized
            else:
                debt["behind"] = 0
            if debt["amount"] > 0.01:
                kept.append(debt)
        graph.debts = kept

    def _repay_in_land(self, graph, debt) -> None:
        lots = graph.commune_lots
        while lots and debt["amount"] > 0.01:
            part = min(lots[0], debt["amount"])
            graph.household_property[COMMUNE] -= part
            graph.household_property[debt["creditor"]] = graph.household_property.get(debt["creditor"], 0.0) + part
            debt["amount"] -= part
            lots[0] -= part
            if lots[0] <= 0.01:
                lots.pop(0)
            self._year["commune: land for forced loans"] += part

    @staticmethod
    def _feeling(graph, debt) -> float:
        """How the creditor feels about the debtor, on their tie (0 without one)."""
        a, b = debt["debtor_person"], debt["creditor_person"]
        edge = graph.get_edge(a, b) if a is not None and b is not None else None
        if edge is None:
            return 0.0
        return edge.valence_a_to_b if edge.resident_a == b else edge.valence_b_to_a

    @staticmethod
    def _cool(graph, debt) -> None:
        a, b = debt["debtor_person"], debt["creditor_person"]
        edge = graph.get_edge(a, b) if a is not None and b is not None else None
        if edge is None:
            return
        for person, change in ((a, DEBT_RESENTMENT), (b, DEBT_RESENTMENT)):
            if edge.resident_a == person:
                edge.valence_a_to_b = max(-1.0, edge.valence_a_to_b - change)
            else:
                edge.valence_b_to_a = max(-1.0, edge.valence_b_to_a - change)

    def _sell_commune_land(self, graph, members) -> None:
        """Land the commune got from heirless estates goes to whoever can pay
        for it: the household with the most cash buys a lot if it has its
        price (user, 2026-10-01). Unsold lots stay with the commune."""
        lots = getattr(graph, "commune_lots", [])
        for lot in list(lots):
            buyer = max(members, key=lambda k: graph.household_money.get(k, 0.0), default=None)
            if buyer is None or graph.household_money.get(buyer, 0.0) < lot:
                break  # the richest can't pay for this one; later lots wait their turn
            self._pay(graph, buyer, COMMUNE, lot)
            graph.household_property[COMMUNE] -= lot
            graph.household_property[buyer] = graph.household_property.get(buyer, 0.0) + lot
            lots.remove(lot)
            self._year["commune: land sold"] += lot

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
        seekers = 0  # adults who could look for work: the base of the unemployment rate
        for node in alive:
            if not node.is_noble and (node.age or 0) >= 18 and node.ses not in RENTIER_CLASSES:
                seekers += 1
            if node.occupation in PRECARIOUS and rng.random() < JOB_LOSS_PER_MONTH:
                node.occupation = None
                graph.employer.pop(node.resident_id, None)
            if node.occupation is None and merchants and _working_teen(node):
                if rng.random() < JOB_FIND_PER_MONTH:
                    node.occupation = "outworker"
                    graph.employer[node.resident_id] = rng.choice(merchants)
                continue
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
        # how hard work is to find: what keeps people from coming (slice 4)
        graph.unemployment_rate = self._unemployed / max(1, seekers)

    @staticmethod
    def _tied_shops(graph, members, sellers) -> Tuple[Dict[Any, Tuple[List[Any], List[float]]], set]:
        """Where each household shops (user, 2026-10-01: money went to a random
        seller in town, not the shops people know): the seller households of
        the workplaces its members have a shop tie to, weighted by the tie's
        time (how much they buy there). The shop is the staff member's
        workplace; its takings go to the seller(s) working there.

        Also returns the sellers anyone is tied to: only shops and taverns
        have customer ties at import, so workshops (bakers, tailors...) are
        still reached at random; sending all spending to tied shops took 98%
        of the workshops' takings and filled the streets in year 1."""
        shop_of = defaultdict(list)
        for seller in sellers:
            if seller.workplace_building_id is not None:
                shop_of[seller.workplace_building_id].append(household_key(seller))
        shops = {}
        for key, people in members.items():
            weight = defaultdict(float)
            for person in people:
                for other, edge in graph.ties_of(person.resident_id).items():
                    if edge.source_type != "shopkeeper_customer":
                        continue
                    place = graph.nodes[other].workplace_building_id
                    if place not in shop_of or place == person.workplace_building_id or not graph.nodes[other].alive:
                        continue  # the member is the staff here, or it isn't a shop that sells
                    for seller_key in shop_of[place]:
                        if seller_key != key:
                            weight[seller_key] += edge.time / len(shop_of[place])
            if weight:
                shops[key] = (list(weight), list(weight.values()))
        return shops, {seller for keys, _ in shops.values() for seller in keys}

    def _buy(self, graph, key, amount: float, sellers, rng: random.Random, income, shops=None) -> None:
        """Bought in town from any seller, as before; when that is a shop or
        tavern (one somebody is tied to), from the ones this household knows
        (`shops`, see _tied_shops). The seller's takings count as their income."""
        if amount <= 0 or not sellers:
            return
        seller = household_key(sellers[rng.randrange(len(sellers))])
        if shops and seller in shops[1] and key in shops[0]:
            seller = rng.choices(*shops[0][key])[0]
        tax = self._pay(graph, key, COMMUNE, amount * GABELLE)
        self._year["commune: gabelle"] += tax
        income[seller] += self._pay(graph, key, seller, amount - tax)

    def _import(self, graph, key, amount: float, merchants, rng: random.Random, income) -> None:
        """Bought from outside through a merchant, who keeps a margin."""
        if amount <= 0:
            return
        if not merchants:
            self._year["out: imports"] += self._pay(graph, key, None, amount)
            return
        merchant = household_key(merchants[rng.randrange(len(merchants))])
        tax = self._pay(graph, key, COMMUNE, amount * GABELLE)  # at the gates
        self._year["commune: gabelle"] += tax
        paid = self._pay(graph, key, merchant, amount - tax)
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
        yearly = {key: 12 * v for key, v in self._income.items()}
        if not getattr(graph, "class_lines_from_earnings", False):
            # 2026-10-01: lines cut from expected incomes, which run 50-80% above
            # what poor households then earn (teens, irregular day labour, masters
            # short of cash), pushed the very poor up ~20% in year 1 in every
            # seed. Cut once more, the same way, from a year of real earnings
            graph.class_lines_from_earnings = True
            _set_class_lines(graph, random.Random(len(graph.nodes)), yearly)
            return
        per_person = resources_per_person(graph, yearly)
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
            "economy_church_cash": round(graph.household_money.get(CHURCH, 0.0), 1),
            "economy_beggars": sum(1 for n in graph.nodes.values() if n.alive and n.beggar),
            "economy_homeless": sum(1 for n in graph.nodes.values()
                                    if n.alive and n.home_building_id is None and graph.houses),
            "economy_evictions": self._evictions,
            "economy_houses_bought": self._houses_bought,
            "economy_houses_owner_occupied": len({(n.home_building_id, household_key(n)) for n in graph.nodes.values()
                                                  if n.alive} & {(b, h["owner"]) for b, h in graph.houses.items()}),
            "economy_houses_church": sum(1 for h in graph.houses.values() if h["owner"] == CHURCH),
            "economy_houses_commune": sum(1 for h in graph.houses.values() if h["owner"] == COMMUNE),
            "economy_houses": len(graph.houses),
            "economy_hardship_deaths": self._hardship_deaths,
            "economy_grain_price": round(self._harvest, 2),
            "economy_famines": self._famines,
            **{f"economy_{k}": v for k, v in self.food.summary().items()},
            "economy_debt_total": round(sum(d["amount"] for d in graph.debts), 1),
            "economy_debts": len(graph.debts),
            "economy_debts_behind": sum(1 for d in graph.debts if d["behind"] > 0),
            **{f"economy_debt_{kind}": round(sum(d["amount"] for d in graph.debts if d["kind"] == kind), 1)
               for kind in ("family", "patron", "moneylender", "forced loan")},
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
        _retarget_debts(graph, old, home)


def _retarget_debts(graph, old, new) -> None:
    """Debts owed by or to a household, and the houses it owns, go with its money when it moves."""
    pass_houses(graph, old, new)
    for debt in getattr(graph, "debts", []):
        for side in ("debtor", "creditor"):
            if debt[side] == old:
                debt[side] = new


def _real_household_id(graph, key):
    """An arrival living alone has a stand-in key: give them a real household id."""
    if not isinstance(key, tuple):
        return key
    home_id = new_household_id(graph)
    for store in (graph.household_money, getattr(graph, "household_property", {})):
        if key in store:
            store[home_id] = store.pop(key)
    _retarget_debts(graph, key, home_id)
    return home_id


def settle_estate(graph, dead: int) -> Optional[str]:
    """What happens to a dead adult's share of their household's wealth
    (2026-09-30, user: to all children). A surviving spouse at home keeps it;
    otherwise it is split equally among all living children wherever they
    live; with no children it stays with the household. A household left
    with nobody goes to the siblings, then the nephews and nieces, like a
    title (2026-10-01: 183 heirless estates in 25 years went out of town,
    wealth 91k -> 70k fl); with no kin to the commune (COMMUNE), which
    sells the land to whoever can pay. Returns what happened, for counting."""
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
        # still living in the household keep theirs where it is. Houses
        # aren't split: with nobody left at home they go to the eldest child
        if not others:
            pass_houses(graph, key, household_key(max(children, key=lambda n: n.age or 0)))
        part = (wealth(graph, key) - house_wealth(graph, key)) / adults / len(children)
        for child in children:
            current = wealth(graph, key) - house_wealth(graph, key)
            if household_key(child) != key and current > 0:
                _move_wealth(graph, key, household_key(child), part / current)
        return "split among children"
    if others:
        return "stays in the household"
    _pay_debts_from_estate(graph, key)
    siblings = _kin(graph, dead, "sibling")
    nephews = [n for s in graph.neighbors(dead) if graph.get_edge(dead, s).source_type == "sibling"
               for n in _kin(graph, s, "parent", younger=True)]
    for heirs, outcome in ((siblings, "to siblings"), (nephews, "to nephews and nieces")):
        if heirs:
            pass_houses(graph, key, household_key(max(heirs, key=lambda n: n.age or 0)))
            for share, heir in enumerate(heirs):  # equal parts: 1/n, then 1/(n-1) of what's left, ...
                _move_wealth(graph, key, household_key(heir), 1.0 / (len(heirs) - share))
            return outcome
    graph.household_money.setdefault(COMMUNE, 0.0)
    pass_houses(graph, key, COMMUNE)  # the commune becomes the landlord (user: it can be one)
    lot = max(0.0, getattr(graph, "household_property", {}).get(key, 0.0))
    _move_wealth(graph, key, COMMUNE, 1.0)
    if lot > 0:
        graph.commune_lots = getattr(graph, "commune_lots", []) + [lot]
    return "to the commune"


def _pay_debts_from_estate(graph, key) -> None:
    """A household left with nobody pays what it owes before heirs or the commune get the rest."""
    for debt in getattr(graph, "debts", []):
        if debt["debtor"] != key:
            continue
        for store in (graph.household_money, graph.household_property):
            paid = min(debt["amount"], max(0.0, store.get(key, 0.0)))
            store[key] = store.get(key, 0.0) - paid
            store[debt["creditor"]] = store.get(debt["creditor"], 0.0) + paid
            debt["amount"] -= paid
    graph.debts = [d for d in getattr(graph, "debts", []) if d["debtor"] != key or d["amount"] > 0.01]


# The commune's household key (user, 2026-10-01). Land from heirless estates
# is sold to a household that can pay (the monthly _sell_commune_land);
# unsold it stays with the commune, earning its return. The commune's cash
# pays the guards and the other public wages before any outside money.
COMMUNE = "commune"
CHURCH = "church"  # the Church's household key: alms in, gifts to the hungry out
LEFT_ALONE_MOVES_IN_AGE = 50  # C: a widow(er) this old moves in with a grown child


def pass_on_merchant_house(graph, dead: int) -> bool:
    """A dead merchant's firm passes to the eldest adult at home, else the
    eldest adult child (2026-10-01: nothing replaced dead merchants, 13 -> 8
    in 25 years, and their capital left the trade with the heirs). Their
    outworkers find the new head through _employer."""
    node = graph.nodes[dead]
    if node.occupation != "merchant":
        return False
    key = household_key(node)
    adults = [n for n in graph.nodes.values() if n.alive and household_key(n) == key and (n.age or 0) >= 18
              and not n.is_noble and n.occupation not in ("servant", "merchant")]
    adults = adults or [n for n in _kin(graph, dead, "parent", younger=True) if (n.age or 0) >= 18
                        and not n.is_noble and n.occupation != "merchant"]
    if not adults:
        return False
    heir = max(adults, key=lambda n: n.age or 0)
    heir.occupation, heir.workplace_building_id = "merchant", None
    graph.employer.pop(heir.resident_id, None)
    return True


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
            _retarget_debts(graph, key, home)
            for n in left:
                n.household_id = home
            return outcome
    return None
