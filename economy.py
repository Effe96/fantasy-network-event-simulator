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

from crafts import BASKET_SHARES as CRAFT_SHARES, CRAFTS, CraftMarket
from food import FoodMarket
from graph import FAMILY, sync_classmates, sync_coworkers, sync_neighbours
from merchants import MerchantTrade

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
# new houses as the town grows (Project_Vision/04 §10, user 2026-10-08)
HOUSE_ROOM = 8  # the median house at import, in people; a new house holds this many
BUILDERS = "builders"  # money set aside for houses being built, paid out as day labour
NEW_HOUSEHOLD_MONTHS = 12  # C: newlyweds and newcomers move into new houses ahead of others for a year
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
# user, 2026-10-11: from 8 children work in shops, taverns and workshops (staff,
# apprentices), one to a workplace; never in charge of one before 18
CHILD_WORK_AGE = 8
CHILD_PLACE_SHARE = 0.5  # C: of the 12-17s finding work while a place is free, those who take it rather than spin
# the employer's job -> what a child does there ("_hand": the master's trade's hand)
CHILD_PLACES = {"shopkeep": "shop_staff", "barkeep": "tavern_staff", "blacksmith": "smith_apprentice", "master": "_hand"}
FARMHANDS_ADDED = 4  # decided: more farm work outside the walls
# C: the crafts of a small Tuscan town, for TownShape's empty workshops
WORKSHOP_TRADES = [("weaver", 3), ("dyer", 1), ("fuller", 1), ("tanner", 1), ("shoemaker", 2), ("tailor", 2),
                   ("carpenter", 2), ("cooper", 1), ("baker", 2), ("potter", 1), ("mason", 2)]
WORKSHOP_HANDS = (3, 5)
WORKSHOP_COST = HOUSE_VALUE_PER_PERSON * HOUSE_ROOM  # C: a new workshop costs what a house for eight does

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
# what households buy that isn't bread or a craft good (wine, oil, meat, firewood...)
# comes from shops and taverns (goods slice 2: the crafts sell their own goods)
SHOP_SELLERS = ("shopkeep", "barkeep", "trader", "mage")
DAY_LABOUR_WORK = 0.6  # C: share of working days a day labourer finds work, when there's demand


def household_key(node) -> Any:
    return node.household_id if node.household_id is not None else ("alone", node.resident_id)


# personal money (Project_Vision/09, user 2026-10-12): everyone holds their own
# cash, land, houses, debts and belongings, under their person key. A
# household holds nothing: paying "from" a household draws its shared costs
# (food, rent, the basket) from its members' purses (EconomyPhenomenon._draw),
# paying "to" one pays its head. Keys in graph.money and graph.land are
# person keys, COMMUNE, CHURCH and BUILDERS.
MONEY_AGE = 16  # user: no money of their own before this; their wages go to a parent
ALLOWANCE_AGE = 12  # user: noble and rich children get an allowance from this age
ALLOWANCE = 0.25  # C: fl a month, about 16 soldi
WIFE_DOWRY_SHARE = 0.10  # at import a wife holds this share of her household's cash and land as her dowry (book §7)


def person_key(resident_id: int) -> Tuple[str, int]:
    return ("p", resident_id)


def is_person(key) -> bool:
    return isinstance(key, tuple) and key[0] == "p"


def has_purse(node) -> bool:
    """Spends money of their own: adults from MONEY_AGE, noble and rich children on an allowance."""
    age = node.age or 0
    return age >= MONEY_AGE or (age >= ALLOWANCE_AGE and (node.is_noble or node.ses in RENTIER_CLASSES))


# the payment log (Project_Vision/09 §2, user 2026-10-12): every payment that
# isn't buying, selling or wages, as (day, kind, payer, payee, amount), payer
# and payee being money keys (None: the outside world); totals per kind kept
# alongside. ponytail: one list for the whole run (~tens of thousands a year);
# trim to the last years if it ever weighs on memory
def log_payment(graph, kind: str, payer, payee, amount: float) -> None:
    if amount <= 1e-9:
        return
    if not hasattr(graph, "payments"):
        graph.payments, graph.payment_totals = [], defaultdict(float)
    graph.payments.append((getattr(graph, "day", 0), kind, payer, payee, round(amount, 3)))
    graph.payment_totals[kind] += amount


def transfer(graph, kind: str, payer: int, payee: int, amount: float, whole: bool = False) -> float:
    """One person pays another from their own purse, up to what they hold
    (nothing if `whole` and they can't pay it all); recorded. Returns what moved."""
    have = max(0.0, graph.money.get(person_key(payer), 0.0))
    paid = 0.0 if whole and have < amount else min(amount, have)
    if paid > 0:
        graph.money[person_key(payer)] -= paid
        graph.money[person_key(payee)] = graph.money.get(person_key(payee), 0.0) + paid
        log_payment(graph, kind, person_key(payer), person_key(payee), paid)
    return paid


STOLEN_GOODS_SHARE = 0.25  # C: a thief carries off this share of one kind of the victim's belongings


def steal(graph, thief: int, victim: int, cash: float, rng: random.Random) -> float:
    """A theft (07 4.1, 09 §6 step 3): up to `cash` from the victim's purse,
    or, as often, a share of one kind of their belongings, which the thief
    keeps. Returns the value taken."""
    owned = {k: v for k, v in graph.belongings.get(victim, {}).items() if v > 0}
    if owned and (graph.money.get(person_key(victim), 0.0) <= 0 or rng.random() < 0.5):
        kind = rng.choice(sorted(owned))
        taken = owned[kind] * STOLEN_GOODS_SHARE
        graph.belongings[victim][kind] -= taken
        mine = graph.belongings.setdefault(thief, {})
        mine[kind] = mine.get(kind, 0.0) + taken
        log_payment(graph, f"theft: {kind}", person_key(victim), person_key(thief), taken)
        return taken
    return transfer(graph, "theft", victim, thief, cash)


def _married(graph, node) -> bool:
    return any(e.source_type == "spouse" and graph.nodes[o].alive for o, e in graph.ties_of(node.resident_id).items())


def head_of(graph, people):
    """The household's head: the eldest married man, else the eldest adult, else the eldest."""
    return max(people, key=lambda n: ((n.age or 0) >= 18, n.gender == "male" and _married(graph, n),
                                      n.age or 0, -n.resident_id))


def host_of(graph, people):
    """Whose household it is: the head among those who aren't lodgers
    (graph.lodgers: roommates and newcomers who came to lodge)."""
    lodgers = getattr(graph, "lodgers", {})
    return head_of(graph, [n for n in people if not lodgers.get(n.resident_id)] or people)


def mark_lodgers(graph, people, lodging: bool) -> None:
    graph.lodgers = getattr(graph, "lodgers", {})
    for node in people:
        if lodging:
            graph.lodgers[node.resident_id] = True
        else:
            graph.lodgers.pop(node.resident_id, None)


def family_groups(graph, people) -> List[List[Any]]:
    """A household's families: members joined by family ties (spouse, parent,
    sibling, grandparent, aunt or uncle, cousin), and the evicted friends
    they took in (graph.guests). A lodger is a family of their own."""
    ids = {n.resident_id: n for n in people}
    parent = {rid: rid for rid in ids}

    def root(rid):
        while parent[rid] != rid:
            parent[rid] = parent[parent[rid]]
            rid = parent[rid]
        return rid
    guests = getattr(graph, "guests", {})
    for rid in ids:
        for other, edge in graph.ties_of(rid).items():
            if other in ids and edge.source_type in FAMILY:
                parent[root(other)] = root(rid)
        if guests.get(rid) in ids:  # taken in by friends: their family keeps them
            parent[root(guests[rid])] = root(rid)
    groups = defaultdict(list)
    for rid, node in ids.items():
        groups[root(rid)].append(node)
    return sorted(groups.values(), key=lambda g: -len(g))


def shares_of(graph, people) -> List[Tuple[float, List[Any]]]:
    """Each family in a household and its share of the household's costs,
    by mouths to feed (a child under 12 eats CHILD_BASKET of an adult)."""
    groups = family_groups(graph, people)
    weights = [sum(CHILD_BASKET if (n.age or 0) < 12 else 1.0 for n in g) for g in groups]
    total = sum(weights) or 1.0
    return [(w / total, g) for w, g in zip(weights, groups)]


def earner_key(graph, node):
    """Whose purse this person's earnings go to: their own from MONEY_AGE,
    else the eldest parent at home, else the eldest adult at home."""
    if (node.age or 0) >= MONEY_AGE:
        return person_key(node.resident_id)
    home = node.household_id
    parents = [graph.nodes[o] for o, e in graph.ties_of(node.resident_id).items()
               if e.source_type == "parent" and graph.nodes[o].alive and home is not None
               and graph.nodes[o].household_id == home and (graph.nodes[o].age or 0) >= MONEY_AGE]
    if not parents and home is not None:
        parents = [n for n in graph.nodes.values() if n.alive and n.household_id == home and (n.age or 0) >= MONEY_AGE]
    return person_key(max(parents, key=lambda n: (n.age, -n.resident_id)).resident_id) if parents \
        else person_key(node.resident_id)


def person_wealth(graph, resident_id: int) -> float:
    return wealth(graph, person_key(resident_id))


def household_wealth(graph, people) -> float:
    return sum(person_wealth(graph, n.resident_id) for n in people)


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
    _split_purses(graph)
    _set_class_lines(graph, rng)
    give_belongings(graph)


def _split_purses(graph) -> None:
    """Each household's wealth goes to its members (Project_Vision/09 §3.2,
    user 2026-10-12): a married woman keeps her dowry, WIFE_DOWRY_SHARE of the
    cash and land; the head gets the land and the houses; the rest of the
    cash is split among those of MONEY_AGE and over. Children get nothing.
    The town holds exactly what it did."""
    members = defaultdict(list)
    for node in graph.nodes.values():
        if node.alive:
            members[household_key(node)].append(node)
    money, land = {}, {}
    for key, people in members.items():
        cash, owned = graph.money.get(key, 0.0), graph.land.get(key, 0.0)
        head = head_of(graph, people)
        wives = [n for n in people if n is not head and n.gender == "female" and (n.age or 0) >= MONEY_AGE
                 and _married(graph, n)]
        for wife in wives:
            money[person_key(wife.resident_id)] = cash * WIFE_DOWRY_SHARE
            land[person_key(wife.resident_id)] = owned * WIFE_DOWRY_SHARE
        cash *= 1 - WIFE_DOWRY_SHARE * len(wives)
        land[person_key(head.resident_id)] = owned * (1 - WIFE_DOWRY_SHARE * len(wives))
        adults = [n for n in people if (n.age or 0) >= MONEY_AGE] or [head]
        for node in adults:
            money[person_key(node.resident_id)] = money.get(person_key(node.resident_id), 0.0) + cash / len(adults)
        pass_houses(graph, key, person_key(head.resident_id))
    for store in ("money", "land"):
        kept = {k: v for k, v in getattr(graph, store).items() if k in (COMMUNE, CHURCH)}
        setattr(graph, store, {**kept, **(money if store == "money" else land)})


# belongings (Project_Vision/09 §5, user 2026-10-12): one value per kind, worn
# out over the years; the basket buys back what's worn (crafts.BASKET_SHARES of
# it, at the standard below), the better off buy more out of what they spend
LASTS_YEARS = {"clothing": 2, "shoes": 1, "housewares": 10}  # C
WEAPON_VALUE = 2.0  # C: a sword or a crossbow; doesn't wear out


def belongings_standard(graph, node, household=None) -> Dict[str, float]:
    """What a person of ordinary means owns of each kind: what the basket buys
    in a year times the years it lasts. Housewares are the head's, for their family."""
    weight = CHILD_BASKET if (node.age or 0) < 12 else 1.0
    out = {k: weight * CRAFT_SHARES[k] * BASKET_PER_PERSON * LASTS_YEARS[k] for k in ("clothing", "shoes")}
    family = household or []
    out["housewares"] = sum(CHILD_BASKET if (n.age or 0) < 12 else 1.0 for n in family) \
        * CRAFT_SHARES["housewares"] * BASKET_PER_PERSON * LASTS_YEARS["housewares"]
    return out


def give_belongings(graph) -> None:
    """At import everyone owns what someone of ordinary means would: the
    1427 catasto left clothing and furnishings out of a household's wealth,
    so they come on top of it. Guards, soldiers, veterans and nobles own a weapon."""
    graph.belongings = {}
    members = defaultdict(list)
    for node in graph.nodes.values():
        if node.alive:
            members[household_key(node)].append(node)
    for people in members.values():
        for group in family_groups(graph, people):
            head = head_of(graph, group)
            for node in group:
                graph.belongings[node.resident_id] = new_belongings(graph, node, group if node is head else None)


def new_belongings(graph, node, family=None) -> Dict[str, float]:
    own = belongings_standard(graph, node, family)
    armed = node.occupation in ("guard", "soldier") or node.is_ex_soldier or (node.is_noble and (node.age or 0) >= 16)
    own["weapon"] = WEAPON_VALUE if armed else 0.0
    return own


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
    prop = graph.land
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
        graph.houses[building] = {"owner": None, "value": value, "room": len(people)}  # room: who lived there
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


def resources_per_person(graph, yearly_income: Dict[Any, float]) -> Dict[int, float]:
    """Each resident's family's wealth plus a year of its income, per member:
    how well they live (user, 2026-10-12: class is per person, and a family
    shares it; a lodger has their own). Wealth alone can't rank the quarter
    of households owning nothing."""
    members = defaultdict(list)
    for node in graph.nodes.values():
        if node.alive:
            members[household_key(node)].append(node)
    out = {}
    for people in members.values():
        for group in family_groups(graph, people):
            keys = [person_key(n.resident_id) for n in group]
            value = sum(wealth(graph, k) + yearly_income.get(k, 0.0) for k in keys) / len(group)
            for node in group:
                out[node.resident_id] = value
    return out


def _expected_income(graph) -> Dict[Any, float]:
    income = defaultdict(float)
    for node in graph.nodes.values():
        if node.alive:
            kind = job_kind(node.occupation)
            income[earner_key(graph, node)] += EXPECTED_EARNINGS.get(kind, PAY.get(kind, (0.0, None))[0])
    for key, owned in getattr(graph, "land", {}).items():
        income[key] += owned * PROPERTY_RETURN
    return income


def _set_class_lines(graph, rng, yearly_income: Optional[Dict[Any, float]] = None) -> None:
    """Rank residents by resources per person, cut them into the town's
    class shares (params.class_shares) and keep the cut points as the fixed
    lines people are judged against from then on. At import the income is
    what each job is expected to pay; a year later the lines are cut once
    more from what households actually earned (see _update_class)."""
    per_person = resources_per_person(graph, yearly_income if yearly_income is not None else _expected_income(graph))
    people = sorted((per_person.get(n.resident_id, 0.0), rng.random(), n) for n in graph.nodes.values() if n.alive)
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
    places = _free_child_places([n for n in graph.nodes.values() if n.alive])
    for node in sorted(graph.nodes.values(), key=lambda n: n.resident_id):  # younger children placed too
        if (places and _working_child(node) and node.occupation is None and household_key(node) not in wealthy
                and rng.random() < CHILD_PLACE_SHARE):
            node.occupation, node.workplace_building_id = places.pop(rng.randrange(len(places)))


def _working_teen(node) -> bool:
    """A young person of a household that isn't rich, old enough to work."""
    return (node.alive and not node.is_noble and node.age is not None and WORKING_AGE <= node.age < 18
            and node.ses not in RENTIER_CLASSES)


def _working_child(node) -> bool:
    """A child of a household that isn't rich, old enough for a place in a shop, tavern or workshop."""
    return (node.alive and not node.is_noble and node.age is not None and CHILD_WORK_AGE <= node.age < 18
            and node.ses not in RENTIER_CLASSES)


def _free_child_places(alive) -> List[Tuple[str, Any]]:
    """(occupation, workplace) for each shop, tavern, smithy and workshop
    with no one under 18 working there yet."""
    taken = {n.workplace_building_id for n in alive if (n.age or 0) < 18 and n.occupation}
    places = {}
    for node in alive:
        kind = job_kind(node.occupation)
        if kind in CHILD_PLACES and node.workplace_building_id is not None and node.workplace_building_id not in taken:
            places[node.workplace_building_id] = f"{node.occupation}_hand" if kind == "master" else CHILD_PLACES[kind]
    return [(places[workplace], workplace) for workplace in sorted(places)]


FARM_UNSTAFFED_MONTHS = 6  # C: a dead farmer's place is taken by a newcomer in ~2 months; after this, nobody is coming


def _staff_farms(graph, alive, unstaffed: Dict[Any, int]) -> None:
    """A farm whose farmer left it with no place for a newcomer to fill (a
    noble farmer's title passes to an heir, a farmer becomes a merchant house's
    heir) goes to its eldest hand after FARM_UNSTAFFED_MONTHS, who takes on the
    others (2026-10-08: 2 of 12 farms lost in 10 years, their hands unpaid,
    their grain imported)."""
    staffed = {n.workplace_building_id for n in alive if n.occupation == "farmer"}
    hands = defaultdict(list)
    for node in alive:
        if node.occupation == "farmhand" and node.workplace_building_id not in staffed:
            hands[node.workplace_building_id].append(node)
    for farm in list(unstaffed):
        if farm not in hands:
            del unstaffed[farm]
    for farm, farm_hands in hands.items():
        unstaffed[farm] = unstaffed.get(farm, 0) + 1
        if unstaffed[farm] < FARM_UNSTAFFED_MONTHS:
            continue
        del unstaffed[farm]
        farmer = max(farm_hands, key=lambda n: (n.age or 0, -n.resident_id))
        farmer.occupation = "farmer"
        for node in farm_hands:
            graph.employer.pop(node.resident_id, None)
        for node in farm_hands:
            if node is not farmer:
                graph.employer[node.resident_id] = farmer.resident_id


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
    graph.money = {key: 0.0 for key in keys[:propertyless]}
    graph.land = {key: 0.0 for key in keys[:propertyless]}
    for key, share in zip(owners, shares):
        graph.money[key] = total * share * CASH_SHARE_OF_WEALTH
        graph.land[key] = total * share * (1.0 - CASH_SHARE_OF_WEALTH)


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


def _homes(graph, members):
    """Each household's building (where most of it lives), the households in
    each building, and the people living in each."""
    home, in_building, people_in = {}, defaultdict(list), defaultdict(int)
    for key, people in members.items():
        buildings = [n.home_building_id for n in people if n.home_building_id in graph.houses]
        if buildings:
            home[key] = max(set(buildings), key=buildings.count)
            in_building[home[key]].append(key)
            people_in[home[key]] += len(people)
    return home, in_building, people_in


def mark_new_household(graph, key, kind: str) -> None:
    """Newlyweds' and newcomers' households, for a year: they move into new
    houses after the most crowded (economy `_move_in`)."""
    if not hasattr(graph, "new_households"):
        graph.new_households = {}
    graph.new_households[key] = [kind, 0]


def pass_houses(graph, old, new) -> None:
    for building, house in getattr(graph, "houses", {}).items():
        if house["owner"] == old:
            set_house_owner(graph, building, new)


def wealth(graph, key) -> float:
    """A household's cash plus property."""
    return (graph.money.get(key, 0.0) + getattr(graph, "land", {}).get(key, 0.0)
            + house_wealth(graph, key))


def gini(values: List[float]) -> float:
    values = sorted(values)
    n, total = len(values), sum(values)
    if not n or total <= 0:
        return 0.0
    return sum((2 * i - n + 1) * v for i, v in enumerate(values)) / (n * total)


class EconomyPhenomenon:
    """Monthly (every 30 days): who earns, who spends, where money comes
    from and goes. Money is held per household (graph.money).
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
        self.crafts = CraftMarket(UNSKILLED_WAGE, IMPORT_MARGIN)  # goods slice 2
        self.trade = MerchantTrade(GABELLE, IMPORT_MARGIN)  # goods slice 4: merchants' warehouses and cargoes
        self._fed_months: Dict[Any, int] = {}  # household -> months fed in a row, while it begs
        self._hardship_deaths = 0
        self._evictions = 0
        self._houses_bought = 0
        self._famines = 0
        self._public_bill = 0.0
        self._unstaffed: Dict[Any, int] = {}  # farm -> months without a farmer
        self._paid_in: Dict[Any, float] = {}  # person -> usual monthly share of their household's costs
        self._paid_month: Dict[Any, float] = defaultdict(float)  # person -> paid into the household this month
        self._members: Dict[Any, List[Any]] = {}  # household -> its people, this month
        self._groups: Dict[Any, List[Tuple[float, List[Any]]]] = {}  # household -> (weight, family), this month

    def init_state(self, graph) -> Dict[int, Any]:
        self._graph = graph  # summarize reads the town's money
        self._deaths_seen = len(graph.deaths)
        # the jobless at import, until the first month's count (it read 0 for a month)
        self._unemployed = sum(1 for n in graph.nodes.values() if n.alive and not n.is_noble and (n.age or 0) >= 18
                               and n.ses not in RENTIER_CLASSES and n.occupation is None)
        for name, empty in (("money", dict), ("land", dict), ("employer", dict),
                            ("merchants", list), ("building_types", dict), ("debts", list),
                            ("houses", dict), ("house_wealth", dict), ("rent_behind", dict), ("belongings", dict)):
            if not hasattr(graph, name):  # a town imported without the economy (test fixtures)
                setattr(graph, name, empty())
        return {resident_id: {} for resident_id in graph.nodes}

    def add_resident(self, graph, state, resident_id: int) -> None:
        """A newcomer founding a household brings savings (or a trade's
        capital) and the clothes they stand in; a baby owns nothing yet."""
        state[resident_id] = {}
        node = graph.nodes[resident_id]
        graph.belongings[resident_id] = new_belongings(graph, node) if (node.age or 0) > 0 else \
            {k: 0.0 for k in ("clothing", "shoes", "housewares", "weapon")}
        founds = node.household_id is None or not any(
            n.alive and n.household_id == node.household_id and n.resident_id != resident_id for n in graph.nodes.values())
        if not founds and (node.age or 0) > 0:
            mark_lodgers(graph, [node], True)  # came to lodge: pays their share of the household's costs
        if founds:
            brought = ARRIVAL_CAPITAL.get(job_kind(node.occupation), ARRIVAL_SAVINGS)
            key = person_key(resident_id)
            graph.money[key] = graph.money.get(key, 0.0) + brought
            self._year["in: newcomers"] += brought

    def candidate_edges(self, graph, state):
        return []

    def edge_probability(self, edge, state_a, state_b, day: int) -> float:
        return 0.0

    def apply_effect(self, graph, state, a: int, b: int, day: int, rng: random.Random) -> List[Any]:
        return []

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

    def _pay(self, graph, from_key, to_key, amount: float, kind: Optional[str] = None) -> float:
        """Move up to `amount` (None = the outside world); returns what
        actually moved. A household pays from its members' purses (_draw)
        and is paid through its head. With a `kind`, it goes in the payment log."""
        if amount <= 0:
            return 0.0
        if from_key is not None:
            if self._is_household(from_key):
                amount = self._draw(graph, from_key, amount)
            else:
                amount = min(amount, max(0.0, graph.money.get(from_key, 0.0)))
                graph.money[from_key] = graph.money.get(from_key, 0.0) - amount
        if to_key is not None:
            if self._is_household(to_key):
                people = self._people(graph, to_key)
                to_key = person_key(head_of(graph, people).resident_id) if people else to_key
            graph.money[to_key] = graph.money.get(to_key, 0.0) + amount
        if kind:
            log_payment(graph, kind, from_key, to_key, amount)
        return amount

    @staticmethod
    def _is_household(key) -> bool:
        return isinstance(key, int) or (isinstance(key, tuple) and key[0] == "alone")

    def _people(self, graph, key) -> List[Any]:
        """A household's living members (this month's, else looked up)."""
        if key in self._members:
            return self._members[key]
        return [n for n in graph.nodes.values() if n.alive and household_key(n) == key]

    def household_of(self, graph, key):
        """The household a key spends for: a person's, or the household itself."""
        return household_key(graph.nodes[key[1]]) if is_person(key) else key

    def _household_income(self, graph, key) -> float:
        """A household's usual monthly income: its members' together."""
        return sum(self._income.get(person_key(n.resident_id), 0.0) for n in self._people(graph, key))

    @staticmethod
    def _owners(graph, key) -> List[Any]:
        """The person behind a key, as a list (none for the commune or the Church)."""
        return [graph.nodes[key[1]]] if is_person(key) else []

    @staticmethod
    def _living(graph, key) -> bool:
        """A key that can still pay or be paid: a living person, or the commune or the Church."""
        return graph.nodes[key[1]].alive if is_person(key) else key in (COMMUNE, CHURCH)

    def cash(self, graph, key) -> float:
        """What a key can pay: a person's or the commune's cash; a household's,
        what its members hold."""
        if self._is_household(key):
            return sum(max(0.0, graph.money.get(person_key(n.resident_id), 0.0)) for n in self._people(graph, key))
        return graph.money.get(key, 0.0)

    def _family_shares(self, graph, key) -> List[Tuple[float, List[Any]]]:
        """Each family in a household and its share of the household's costs,
        by mouths to feed (a child under 12 eats CHILD_BASKET of an adult)."""
        if key not in self._groups:
            self._groups[key] = shares_of(graph, self._people(graph, key))
        return self._groups[key]

    def _draw(self, graph, key, amount: float) -> float:
        """A household's shared cost, paid from its members' purses (user,
        2026-10-12): each family pays its share; a lodger pays theirs whatever
        they earn, and nobody covers for them. Within a family the earners pay
        in proportion to what they usually earn; what that leaves short, the
        head pays, then the other adults, eldest first, then what's held for
        the children. Returns what was paid."""
        paid = 0.0
        for share, family in self._family_shares(graph, key):
            paid += self._draw_family(graph, family, amount * share)
        return paid

    def _draw_family(self, graph, family, amount: float) -> float:
        money, paid = graph.money, 0.0
        keys = [person_key(n.resident_id) for n in family]
        earning = {k: max(0.0, self._income.get(k, 0.0)) for k in keys}
        total = sum(earning.values())
        if total > 0:
            for k in keys:
                take = min(amount * earning[k] / total, max(0.0, money.get(k, 0.0)))
                if take > 0:
                    money[k] -= take
                    self._paid_month[k] += take
                    paid += take
        if paid < amount - 1e-12:
            head = head_of(graph, family)
            order = sorted(family, key=lambda n: (n is not head, (n.age or 0) < MONEY_AGE, -(n.age or 0)))
            for node in order:
                k = person_key(node.resident_id)
                take = min(amount - paid, max(0.0, money.get(k, 0.0)))
                if take > 0:
                    money[k] -= take
                    self._paid_month[k] += take
                    paid += take
                if paid >= amount - 1e-12:
                    break
        return paid

    def _affordable(self, graph, key, amount: float) -> float:
        """How much of a shared cost of `amount` a household's families can pay between them."""
        money = graph.money
        return sum(min(amount * share, sum(max(0.0, money.get(person_key(n.resident_id), 0.0)) for n in family))
                   for share, family in self._family_shares(graph, key))

    def _give_household(self, graph, giver, key, amount: float, need: float) -> float:
        """Help for a hungry household goes to the families short of their share, through their heads."""
        given = 0.0
        for share, family in self._family_shares(graph, key):
            held = sum(max(0.0, graph.money.get(person_key(n.resident_id), 0.0)) for n in family)
            short = max(0.0, need * share - held)
            if short > 0 and given < amount:
                given += self._pay(graph, giver, person_key(head_of(graph, family).resident_id),
                                   min(short, amount - given))
        return given

    @staticmethod
    def _wear(graph, alive) -> None:
        """A month's wear on everyone's clothing, shoes and housewares."""
        for node in alive:
            own = graph.belongings.get(node.resident_id)
            if own:
                for good, years in LASTS_YEARS.items():
                    own[good] -= own.get(good, 0.0) / (12 * years)

    def _worn(self, graph, key) -> List[Tuple[int, str, float]]:
        """(resident, good, fl) a household's basket buys this month: for
        each member's clothing and shoes, and the head's housewares, what an
        ordinary person's wear out in a month. A household that can't afford
        it goes shabbier; what's missing, and anything finer, is bought out of
        what people spend beyond the basket (2026-10-12: buying back all that
        was missing as a need deepened hunger, 7 -> 22 hungry households in
        two quiet years). Each family in the household buys its own."""
        out = []
        for _, family in self._family_shares(graph, key):
            head = head_of(graph, family)
            for node in family:
                standard = belongings_standard(graph, node, family if node is head else None)
                for good, years in LASTS_YEARS.items():
                    worn = standard[good] / (12 * years)
                    if worn > 1e-9:
                        out.append((node.resident_id, good, worn))
        return out

    def _buy_goods(self, graph, key, wanted, scale: float, alive, merchants, rng, income) -> float:
        """`key` buys `scale` of the (resident, good, fl) wanted; what it gets
        goes to each resident's belongings in proportion. Returns fl spent."""
        by_good = defaultdict(float)
        for _, good, value in wanted:
            by_good[good] += value * scale
        if not any(v > 1e-12 for v in by_good.values()):
            return 0.0
        spent = self.crafts.buy(self, graph, key, by_good, alive, merchants, rng, income)
        for rid, good, value in wanted:
            if by_good[good] > 1e-12:
                own = graph.belongings.setdefault(rid, {})
                own[good] = own.get(good, 0.0) + spent.get(good, 0.0) * value * scale / by_good[good]
        return sum(spent.values())

    def _allowances(self, graph, alive, income) -> None:
        """Noble and rich children from ALLOWANCE_AGE get an allowance from the parent who keeps their wages."""
        for node in alive:
            if ALLOWANCE_AGE <= (node.age or 0) < MONEY_AGE and has_purse(node):
                parent, child = earner_key(graph, node), person_key(node.resident_id)
                if parent != child:
                    paid = self._pay(graph, parent, child, ALLOWANCE, "allowance")
                    income[parent] -= paid
                    income[child] += paid

    def _spending(self, graph, members, income, month: float) -> Dict[Any, float]:
        """What each person spends this month beyond their share of the
        household's costs. A family decides together, as a household did
        before (user, 2026-10-12: each holds their own money, family pools
        for its costs): it spends (1 - saving) of what it usually earns beyond
        what it usually pays in, plus EXCESS_CASH_SPENT_PER_YEAR of the cash
        it holds beyond its cushion, never more than it holds. Each member
        spends their part from their own purse: the first by what they earn
        beyond what they pay in, the second by the cash they hold; what one
        can't cover, the others with cash spend instead. Children without a
        purse spend nothing."""
        out = {}
        committed = self.trade.committed
        for key in members:
            for _, family in self._family_shares(graph, key):
                keys = [person_key(n.resident_id) for n in family if has_purse(n)]
                if not keys:
                    continue
                usual = {k: self._income.get(k, income.get(k, 0.0)) for k in keys}
                paid = {k: self._paid_in.get(k, self._paid_month.get(k, 0.0)) for k in keys}
                # a merchant's takings owed to the next order aren't theirs to spend
                held = {k: max(0.0, graph.money.get(k, 0.0) - committed.get(k, 0.0)) for k in keys}
                wealth_ = sum(held.values())
                cushion = SAVINGS_CUSHION_YEARS * 12 * max(0.0, sum(usual.values()))
                saving = SAVING_SHARE * max(0.0, 1.0 - wealth_ / cushion) if cushion > 0 else SAVING_SHARE
                beyond = {k: max(0.0, usual[k] - paid[k]) for k in keys}
                spare = (1.0 - saving) * max(0.0, sum(usual.values()) - sum(paid.values()))
                # cash well beyond the cushion gets spent down (2026-09-29: without
                # this, merchants and masters kept gaining, town cash +4.4k a year)
                excess = EXCESS_CASH_SPENT_PER_YEAR * month * max(0.0, wealth_ - cushion)
                total = min(spare + excess, wealth_)
                if total <= 1e-12:
                    continue
                parts = {k: min(held[k], (spare * beyond[k] / sum(beyond.values()) if sum(beyond.values()) > 0 else 0.0)
                                + excess * held[k] / wealth_) for k in keys}
                left, room = total - sum(parts.values()), {k: held[k] - parts[k] for k in keys}
                for k in keys:
                    if left > 1e-12 and sum(room.values()) > 0:
                        parts[k] += left * room[k] / sum(room.values())
                    if parts[k] > 1e-12:
                        out[k] = parts[k]
        return out

    def _month(self, graph, rng: random.Random, day: int = 0) -> None:
        self._months += 1
        month = 30 / 365
        alive = [n for n in graph.nodes.values() if n.alive]
        self._give_work(graph, alive, rng)
        _staff_farms(graph, alive, self._unstaffed)
        income = defaultdict(float)  # person (or commune) -> net income this month
        members = defaultdict(list)
        for node in alive:
            members[household_key(node)].append(node)
        self._members, self._groups, self._paid_month = members, {}, defaultdict(float)
        self.trade.start_month(self, graph, alive, self.food, rng, income)  # cargoes land, heirs, ruin
        by_occupation = defaultdict(list)
        for node in alive:
            by_occupation[job_kind(node.occupation)].append(node)
        sellers = [n for n in alive if job_kind(n.occupation) in LOCAL_SELLERS]
        shop_sellers = [n for n in alive if job_kind(n.occupation) in SHOP_SELLERS]
        self.crafts.start_month(alive)
        merchants = [n for n in by_occupation["merchant"]]
        farmers = by_occupation["farmer"]

        # money in: property (land and houses; cash earns nothing: 7% on all
        # money compounded, +5% a year), public wages
        for key, owned in list(graph.land.items()):
            owned -= self.food.land_in_hand(key)  # poderi pay their owners in grain (food.py)
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
        self._commune_borrow(graph, bill - graph.money.get(COMMUNE, 0.0), alive)
        for node, wage in public:
            to = earner_key(graph, node)
            gain = self._pay(graph, COMMUNE, to, wage)
            income[to] += gain
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
            boss = person_key(employer.resident_id)
            if (node.age or 0) < 18:
                wage *= TEEN_WAGE_SHARE
            to = earner_key(graph, node)
            paid = self._pay(graph, boss, to, wage * month)
            income[to] += paid
            income[boss] -= paid  # a business cost, not living expenses
            if payer == "merchant" and kind == "outworker":
                sale = self._pay(graph, None, boss, paid * EXPORT_MARKUP)
                wool = self._pay(graph, boss, None, sale * RAW_WOOL_SHARE)
                income[boss] += sale - wool
                self._year["in: cloth exports"] += sale
                self._year["out: raw wool"] += wool

        # workshops buy their inputs and make goods before households spend:
        # a master's household spending first left weavers no cash for wool
        self.crafts.produce(self, graph, alive, farmers, merchants, rng, income)

        # households buy their basket: grain as bread (the food market, goods
        # slice 1), what's worn of their belongings from the workshops, the
        # rest from shops and taverns. A household pays from its members'
        # purses (_draw)
        self.food.month(self, graph, members, farmers, merchants, rng, income, day)  # harvests in summer
        self.food.start_month(members)
        self._harvest, self._famines = self.food.price, self.food.famines
        basket = BASKET_PER_PERSON * (1 - GRAIN_SHARE_OF_BASKET)  # what isn't grain
        if graph.houses:  # lodging is paid as rent (slice 5), after food
            basket -= BASKET_PER_PERSON * RENT_SHARE
        shops = self._tied_shops(graph, members, shop_sellers)
        # of what isn't bread or rent, the crafts' share (clothing, shoes, housewares)
        craft_share = min(1.0, sum(CRAFT_SHARES.values()) * BASKET_PER_PERSON / basket) if basket > 0 else 0.0
        other = basket - craft_share * basket  # wine, oil, firewood...: from shops and taverns
        self._wear(graph, alive)
        worn = {key: self._worn(graph, key) for key in members}
        grain_cost = {key: self.food.grain_cost(key, people) for key, people in members.items()}
        needs = {key: sum(CHILD_BASKET if (n.age or 0) < 12 else 1.0 for n in people) * other * month
                 + grain_cost[key] + sum(v for _, _, v in worn[key]) for key, people in members.items()}
        bakers = by_occupation.get("master", [])
        bakers = [n for n in bakers if n.occupation == "baker"]
        church_budget = CHURCH_GIVES_PER_MONTH * max(0.0, graph.money.get(CHURCH, 0.0))
        self._hungry = 0
        graph.hunger_last = getattr(graph, "hunger", {}) or {}  # hoarders' customers remember (food.py)
        graph.hunger = {}  # resident -> share of their family's basket it couldn't buy this month (stress reads it)
        for key, people in members.items():
            need = needs[key]
            if self._affordable(graph, key, need) < need:  # borrow before going hungry (slice 3 B)
                self._borrow(graph, key, people, need - self._affordable(graph, key, need), needs, members, merchants)
            short = need - self._affordable(graph, key, need)
            if short > 0 and church_budget > 0:  # alms, through the priests
                given = self._give_household(graph, CHURCH, key, min(short, church_budget), need)
                church_budget -= given
                self._year["church: gave to the hungry"] += given
            spend = self._affordable(graph, key, need)
            if spend < need * 0.999:  # hungry: the families that couldn't pay their share (a lodger, not their hosts)
                self._hungry += 1
                for share, family in self._family_shares(graph, key):
                    held = sum(max(0.0, graph.money.get(person_key(n.resident_id), 0.0)) for n in family)
                    if share > 0 and held < need * share * 0.999:
                        for node in family:
                            graph.hunger[node.resident_id] = 1.0 - held / (need * share)
            before = self.cash(graph, key)  # bread first, then the rest
            self.food.feed(self, graph, key, people, min(spend, grain_cost[key]), bakers, farmers, merchants,
                           rng, income)
            rest = spend - (before - self.cash(graph, key))
            crafts_due = sum(v for _, _, v in worn[key])
            scale = min(1.0, rest / max(1e-9, need - grain_cost[key])) if crafts_due > 0 else 0.0
            rest -= self._buy_goods(graph, key, worn[key], scale, alive, merchants, rng, income)
            self._buy(graph, key, rest, shop_sellers, rng, income, shops)

        # then everyone spends what they earned above their share of the
        # household's costs, minus what they save. Income here is net: takings
        # and wages in, wages and day labour paid out (2026-09-29: counting only
        # wages and property let sellers hoard, +13% money a year). A family
        # decides together (_spending): saving tapers off as its money nears
        # SAVINGS_CUSHION_YEARS of its income, so no one piles up money forever
        # (a flat 20% saving did: masters +160 fl a year); the rich spend their
        # property income and keep their capital. The decision uses usual income
        # from past months, not this month's so far: takings and day labour
        # arrive later in the month, and deciding on a partial month quietly
        # saved them (money +6.5k a year).
        hire = defaultdict(float)
        for s in sellers:
            hire[person_key(s.resident_id)] = max(0.0, income.get(person_key(s.resident_id), 0.0)) * DAY_LABOUR_SHARE
        self._allowances(graph, alive, income)
        for key, extra in self._spending(graph, members, income, month).items():
            self.trade.sell(self, graph, key, "luxuries", extra * LUXURY_IMPORT_SHARE, merchants, rng, income)
            local = extra * (1 - LUXURY_IMPORT_SHARE)
            hire[key] += local * DAY_LABOUR_OF_SPENDING  # builders, porters, carters
            goods = local * (1 - DAY_LABOUR_OF_SPENDING)
            goods -= self._buy_goods(graph, key, [(key[1], good, goods * craft_share * share / sum(CRAFT_SHARES.values()))
                                                  for good, share in CRAFT_SHARES.items()], 1.0,
                                     alive, merchants, rng, income)
            self._buy(graph, key, goods, shop_sellers, rng, income, shops)

        # public works keep the city running: walls, streets, bridges (day
        # labour and purchases in town), from what the commune holds beyond its fund
        works = COMMUNE_WORKS_SHARE * max(0.0, graph.money.get(COMMUNE, 0.0)
                                          - COMMUNE_FUND_MONTHS * self._public_bill)
        if works > 0:
            hire[COMMUNE] = works * DAY_LABOUR_OF_SPENDING
            self._buy(graph, COMMUNE, works * (1 - DAY_LABOUR_OF_SPENDING), sellers, rng, income)
            self._year["commune: public works"] += works
        self.crafts.settle(self, graph, merchants, rng, income)  # workshops pay for their materials
        self.trade.order(self, graph, alive, needs, self.food, members, rng)  # merchants send for next months' goods
        self._collect_alms(graph, members)
        needs[COMMUNE] = COMMUNE_RESERVE_MONTHS * self._public_bill
        self._build_houses(graph, members, needs)
        if self._months % 12 == 0:
            self._open_workshops(graph, alive, members, needs, rng)
        self._housing(graph, members, needs, income, rng)
        self._repay_debts(graph, needs, members, rng)
        self._sell_commune_land(graph, members)
        # houses being built hire first: their money is set aside for it
        pot = graph.money.get(BUILDERS, 0.0)
        budget = {BUILDERS: pot} if pot > 0 else {}
        for key, amount in hire.items():
            budget[key] = budget.get(key, 0.0) + amount
        self._hire_day_labour(graph, by_occupation["day_labourer"], budget, income, month, rng)
        self._raise_houses(graph, pot - graph.money.get(BUILDERS, 0.0))
        self._hardship(graph, members, rng, day)
        # the month is complete: update each person's usual income and share of their household's costs
        for node in alive:
            key = person_key(node.resident_id)
            for usual_of, now in ((self._income, income), (self._paid_in, self._paid_month)):
                usual = usual_of.get(key, now.get(key, 0.0))
                usual_of[key] = usual + (now.get(key, 0.0) - usual) * INCOME_MEMORY
        for usual_of in (self._income, self._paid_in):
            for key in [k for k in usual_of if is_person(k) and not graph.nodes[k[1]].alive]:
                del usual_of[key]
        self._year["coworker ties added"] += sync_coworkers(graph, rng)  # this month's job changes
        self._year["neighbour ties added"] += sync_neighbours(graph, rng)  # and moves
        self._year["classmate ties added"] += sync_classmates(graph, rng)

    def _housing(self, graph, members, needs, income, rng: random.Random) -> None:
        """Once food is bought (user: food first): tenants pay rent; a tenant
        who can buy its house does; a household behind on rent for 3 to 6
        months (longer the better it gets on with its landlord) is evicted,
        to kin or friends with room, or onto the street as beggars; the
        homeless who can pay rent find a home again; new houses fill."""
        if not graph.houses:
            return
        # houses whose owners are gone go to the commune (moved away, died out)
        for building, house in graph.houses.items():
            owner = house["owner"]
            if not (is_person(owner) and graph.nodes[owner[1]].alive) and owner not in (COMMUNE, CHURCH):
                set_house_owner(graph, building, COMMUNE)
        home, in_building, people_in = _homes(graph, members)
        month = 30 / 365
        for key, people in members.items():
            building = home.get(key)
            if building is None:
                if all(n.home_building_id is None for n in people):
                    self._rehouse(graph, key, people, needs, rng, people_in)
                continue
            house = graph.houses[building]
            owners_home = self.household_of(graph, house["owner"]) if is_person(house["owner"]) else None
            if owners_home == key:
                continue
            # the tenant with the most cash buys (personal money, 2026-10-12)
            buyer = max((person_key(n.resident_id) for n in people), key=lambda k: (graph.money.get(k, 0.0), k))
            # a landlord living elsewhere sells to a tenant who can pay; one who
            # lives there keeps it (a co-tenant forcing sales made houses change
            # hands back and forth: 648 sales of 226 houses in 25 years)
            if (owners_home not in in_building[building]
                    and graph.money.get(buyer, 0.0) >= house["value"] + BUY_CUSHION_MONTHS * needs.get(key, 0.0)):
                self._pay(graph, buyer, house["owner"], house["value"], "house sale")  # bought from the owner (user)
                set_house_owner(graph, building, buyer)
                self._houses_bought += 1
                graph.rent_behind.pop(key, None)
                continue
            # split by people, the space each household takes (split by household,
            # a single paid as much as a family of six); a house below its room
            # costs its owner the empty places, not the tenants (2026-10-08)
            due = (house["value"] * PROPERTY_RETURN * month * len(people)
                   / max(people_in[building], house.get("room", 0)))
            # each family pays its share (user, 2026-10-12): a lodger behind on
            # theirs is put out on their own, not their hosts with them
            head, families = host_of(graph, people), shares_of(graph, people)
            for share, family in families:
                if head in family:
                    continue
                behind = person_key(head_of(graph, family).resident_id)  # a lodger's arrears
                if self._pay_rent(graph, behind, family, house, due * share, income):
                    lodgers = new_household_id(graph)
                    for node in family:
                        node.household_id = lodgers
                    mark_lodgers(graph, family, False)  # a household of their own now
                    self._year["lodgers put out"] += len(family)
                    self._evict(graph, lodgers, family, members, needs, leaving=key)
            share, host = next((s, f) for s, f in families if head in f)
            if self._pay_rent(graph, key, host, house, due * share, income):
                self._evict(graph, key, [n for n in people if n.household_id == key], members, needs)
        self._move_in(graph, needs)

    # -- new houses as the town grows (Project_Vision/04 §10) -----------------

    def _build_houses(self, graph, members, needs) -> None:
        """While the town's people exceed its houses' room by more than half a
        house, one more is started (sim-only until TownShape can place it).
        Whoever can pays for it (user, 2026-10-08: all three ways): the
        household with the most cash, keeping a cushion; else the one with the
        most land outside, selling some; else the commune, from what it holds
        beyond its fund. The money is set aside to pay builders (day labour)."""
        rooms = [house.get("room") for house in graph.houses.values()]
        if not rooms or None in rooms:  # a town without rooms (test fixtures)
            return
        people = sum(len(p) for p in members.values())
        value = HOUSE_VALUE_PER_PERSON * HOUSE_ROOM
        free = getattr(graph, "land", {})
        persons = sorted(person_key(n.resident_id) for group in members.values() for n in group if has_purse(n))
        while persons and people - sum(rooms) > HOUSE_ROOM / 2:
            cash = max(persons, key=lambda k: graph.money.get(k, 0.0) - self.trade.committed.get(k, 0.0))
            land = max(persons, key=lambda k: free.get(k, 0.0) - self.food.land_in_hand(k))
            if (graph.money.get(cash, 0.0) - self.trade.committed.get(cash, 0.0)
                    >= value + BUY_CUSHION_MONTHS * needs.get(self.household_of(graph, cash), 0.0)):
                owner, how = cash, "cash"
            elif free.get(land, 0.0) - self.food.land_in_hand(land) >= value:
                owner, how = land, "land"
            elif graph.money.get(COMMUNE, 0.0) - COMMUNE_FUND_MONTHS * self._public_bill >= value:
                owner, how = COMMUNE, "commune"
            else:
                return
            building = new_building(graph, "residence", HOUSE_ROOM, self._owners(graph, owner))
            if how == "cash":
                paid = self._pay(graph, cash, BUILDERS, value)
                self._year["houses: built from cash"] += 1
            elif how == "land":
                free[land] -= value  # sold outside the walls: money in from outside
                paid = self._pay(graph, None, BUILDERS, value)
                self._year["houses: built from land sold"] += 1
                self._year["in: land sold"] += value
            else:
                paid = self._pay(graph, COMMUNE, BUILDERS, value)
                self._year["houses: built by the commune"] += 1
            graph.building_types[building] = "residence"
            graph.houses[building] = {"owner": None, "value": paid, "room": HOUSE_ROOM, "built": True, "left": paid}
            set_house_owner(graph, building, owner)
            rooms.append(HOUSE_ROOM)

    def _open_workshops(self, graph, alive, members, needs, rng: random.Random) -> None:
        """Yearly (Project_Vision/04 §10 D; user, 2026-10-09: workshops grow
        with the town, as farms and houses do): a good whose workshops fall
        short of their margin at import by more than half a new workshop gets
        one. Its master is a hand of that trade, the eldest; their household
        pays WORKSHOP_COST if it can spare it, else the household with the
        most to spare lends it (a patron's loan). The money pays builders.
        Hands come from the unemployed, then day labourers, then outworkers.
        ponytail: the workshop works at once while its cost is paid out as
        builders' wages, from the pot houses being built also draw on."""
        weights = dict(WORKSHOP_TRADES)
        for good, short in sorted(self.crafts.shortfall(alive).items()):
            trades = sorted(t for t, craft in CRAFTS.items() if craft[0] == good)
            trade = rng.choices(trades, [weights.get(t, 1) for t in trades])[0]
            if short <= self.crafts.capacity({"trade": trade, "staff": 1 + sum(WORKSHOP_HANDS) / 2}) / 2:
                continue
            hands = [n for n in alive if (n.age or 0) >= 18 and n.occupation
                     and n.occupation.endswith("_hand") and n.occupation[:-5] in trades]
            if not hands:
                continue
            master = max(hands, key=lambda n: (n.occupation == f"{trade}_hand", n.age or 0, -n.resident_id))
            trade, key = master.occupation[:-5], person_key(master.resident_id)
            if self._spare(graph, key, needs) < WORKSHOP_COST:
                lender = max((person_key(n.resident_id) for n in alive if has_purse(n) and n is not master),
                             key=lambda k: (self._spare(graph, k, needs), k))
                if self._spare(graph, lender, needs) < WORKSHOP_COST:
                    continue
            building = new_building(graph, "workshop", 0, [master])
            if self._spare(graph, key, needs) >= WORKSHOP_COST:
                self._pay(graph, key, BUILDERS, WORKSHOP_COST)
                self._year["workshops: from savings"] += 1
            else:
                self._pay(graph, lender, BUILDERS, WORKSHOP_COST)
                graph.debts.append({"debtor": key, "creditor": lender, "debtor_person": master.resident_id,
                                    "creditor_person": lender[1],
                                    "amount": WORKSHOP_COST, "rate": DEBT_PATRON_RATE, "kind": "patron", "behind": 0})
                self._year["workshops: from a patron's loan"] += 1
            graph.building_types[building] = "workshop"
            graph.workshops_opened = getattr(graph, "workshops_opened", 0) + 1
            master.occupation, master.workplace_building_id = trade, building
            graph.employer.pop(master.resident_id, None)
            pool = [n for job in (None, "day_labourer", "outworker") for n in alive
                    if n.occupation == job and (n.age or 0) >= 18 and not n.is_noble and n.ses not in RENTIER_CLASSES]
            for hand in pool[:rng.randint(*WORKSHOP_HANDS)]:
                hand.occupation, hand.workplace_building_id = f"{trade}_hand", building
                graph.employer[hand.resident_id] = master.resident_id

    def _raise_houses(self, graph, paid: float) -> None:
        """What the builders were paid this month goes to the houses being
        built, oldest first; a house whose cost is all paid is finished."""
        for house in graph.houses.values():
            if paid <= 1e-9:
                return
            if "left" in house:
                spent = min(paid, house["left"])
                house["left"] -= spent
                paid -= spent
                if house["left"] <= 1e-6:
                    del house["left"]
                    self._year["houses: built"] += 1

    def _move_in(self, graph, needs) -> None:
        """New houses fill (user, 2026-10-08): first the poorest household of
        the most crowded house, then newlyweds, then newcomers, each only if
        it can pay a month of its share of the rent and of food. Owners and
        nobles stay, and so do households behind on rent.
        ponytail: candidates are ranked once a month, not after each move."""
        new = getattr(graph, "new_households", {})
        members = defaultdict(list)
        for node in graph.nodes.values():
            if node.alive:
                members[household_key(node)].append(node)
        for key in list(new):
            new[key][1] += 1
            if key not in members or new[key][1] > NEW_HOUSEHOLD_MONTHS:
                del new[key]
        open_ = [b for b, h in graph.houses.items() if h.get("built") and "left" not in h]
        if not open_:
            return
        home, _, people_in = _homes(graph, members)

        def crowding(key):
            return people_in[home[key]] / max(1, graph.houses[home[key]].get("room") or people_in[home[key]])

        movable = [k for k in home if not graph.houses[home[k]].get("built") and graph.houses[home[k]]["owner"] != k
                   and k not in graph.rent_behind and not any(n.is_noble for n in members[k])]
        crowded = sorted((k for k in movable if crowding(k) > 1),
                         key=lambda k: (-crowding(k), household_wealth(graph, members[k]) / len(members[k]), str(k)))
        later = [k for kind in ("newlyweds", "newcomers") for k in movable if new.get(k, [None])[0] == kind]
        moved = set()
        for building in open_:
            house = graph.houses[building]
            for key in crowded + later:
                spare = house["room"] - people_in[building]
                if spare <= 0:
                    break
                people = members[key]
                rent = house["value"] * PROPERTY_RETURN / 12 * len(people) / house["room"]
                # a crowded house splits its rent among more people: moving costs
                # more, and its usual income must still cover food (one month's
                # cash let the poorest move, fall behind and be evicted: homeless
                # 20 -> 32 per 1,000)
                old = graph.houses[home[key]]
                now = (old["value"] * PROPERTY_RETURN / 12 * len(people)
                       / max(people_in[home[key]], old.get("room") or 0))
                if (key in moved or len(people) > spare
                        or self.cash(graph, key) < rent + needs.get(key, 0.0)
                        or self._household_income(graph, key) - (rent - now) < needs.get(key, 0.0)):
                    continue
                for node in people:
                    node.home_building_id = building
                people_in[building] += len(people)
                moved.add(key)
                new.pop(key, None)
                self._year["houses: moved into new"] += len(people)

    def _pay_rent(self, graph, behind, family, house, due: float, income) -> bool:
        """A family pays this month's rent and any arrears (kept under
        `behind`) to the house's owner, from its members' purses. Returns
        whether it's now so far behind it must go: 3 to 6 months, longer the
        better landlord and tenants get on (part-payments count: every short
        month counted as a whole month behind made 59 evictions in year 1)."""
        owed = graph.rent_behind.get(behind, 0.0) + due
        paid = self._draw_family(graph, family, owed)
        owner = house["owner"]
        graph.money[owner] = graph.money.get(owner, 0.0) + paid
        log_payment(graph, "rent", person_key(head_of(graph, family).resident_id), owner, paid)
        income[owner] += paid
        self._year["rent: paid"] += paid
        if paid + 1e-9 >= owed:
            graph.rent_behind.pop(behind, None)
            return False
        graph.rent_behind[behind] = owed - paid
        grace = EVICT_AFTER_MONTHS[0] + round((EVICT_AFTER_MONTHS[1] - EVICT_AFTER_MONTHS[0])
                                              * max(0.0, self._affinity(graph, family, self._owners(graph, owner))))
        if graph.rent_behind[behind] >= grace * due:
            graph.rent_behind.pop(behind, None)
            return True
        return False

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

    def _evict(self, graph, key, people, members, needs, leaving=None) -> None:
        """Evicted: family or friends who like them take them in, if they can
        feed them too (user, 2026-10-01: taken in by anyone, the poorest were
        pooled into other households and nobody went hungry); else single
        people and small households move in with singles they know who rent
        (the user's point: singles clubbed together to rent a small house);
        else the street. Lodgers put out (`leaving` their hosts' household)
        don't go back to it."""
        self._evictions += 1
        hosts, roommates = [], []
        for person in people:
            for other, edge in graph.ties_of(person.resident_id).items():
                host = graph.nodes[other]
                host_key = household_key(host)
                if not host.alive or host_key in (key, leaving) or host.home_building_id is None:
                    continue
                feeling = edge.valence_a_to_b if edge.resident_a == other else edge.valence_b_to_a
                household = members.get(host_key, ())
                if ((edge.source_type in FAMILY_TIES or edge.source_type == "friend") and feeling >= 0.3
                        and len(household) + len(people) <= HOST_MAX
                        and self._household_income(graph, host_key)
                        >= HOST_FOOD_COVER * (needs.get(host_key, 0.0) + needs.get(key, 0.0))):
                    hosts.append((feeling, other))
                elif (feeling >= 0 and len(people) <= ROOMMATE_MAX and len(household) + len(people) <= ROOMMATE_MAX
                      and all((n.age or 0) >= 18 for n in household)):
                    roommates.append((feeling, other))
        for found, kind in ((hosts, "evicted: taken in"), (roommates, "evicted: shared a room")):
            if found:
                host = graph.nodes[max(found)[1]]
                self._join(graph, key, people, host)
                if kind == "evicted: taken in":  # fed and housed as family; roommates pay their share
                    graph.guests = getattr(graph, "guests", {})
                    for node in people:
                        graph.guests[node.resident_id] = host.resident_id
                mark_lodgers(graph, people, kind == "evicted: shared a room")
                self._year[kind] += len(people)
                return
        for node in people:  # onto the street: homeless people beg (user)
            node.home_building_id = None
            if (node.age or 0) >= BEG_MIN_AGE and not node.is_noble:
                node.beggar = True
        self._year["evicted: onto the street"] += len(people)

    @staticmethod
    def _join(graph, key, people, host) -> None:
        """`people` (household `key`) move into `host`'s household and home; their money is their own."""
        new = _real_household_id(graph, household_key(host))
        host.household_id = new
        for node in people:
            node.household_id, node.home_building_id = new, host.home_building_id

    def _rehouse(self, graph, key, people, needs, rng: random.Random, people_in=None) -> None:
        """The homeless find a home again once they hold a month of their
        share of a house's rent, and food: a house with room if their income
        covers it (2026-10-08: was a whole house's rent, whatever their size). Small
        homeless households pool with homeless people they know first, to
        rent a room together (user, 2026-10-01)."""
        people_in = people_in if people_in is not None else {}
        if len(people) <= ROOMMATE_MAX and self.cash(graph, key) > 0:
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
                        for node in mates:
                            node.household_id = new
                        mark_lodgers(graph, mates, True)  # they pool to rent; each pays their share
                        key, people = new, people + mates
                        self._year["homeless: pooled to rent"] += len(mates)
                        break
                else:
                    continue
                break
        ready = [b for b, h in graph.houses.items() if "left" not in h]
        roomy = [b for b in ready if people_in.get(b, 0) + len(people) <= graph.houses[b].get("room", 0)]
        # a house with room costs a full share: only for those whose income
        # covers it and food; the rest crowd in where rent is split more ways
        full = HOUSE_VALUE_PER_PERSON * PROPERTY_RETURN / 12 * len(people)
        if self._household_income(graph, key) < full + needs.get(key, 0.0):
            roomy = []
        building = rng.choice(sorted(roomy or ready))
        house = graph.houses[building]
        rent = (house["value"] * PROPERTY_RETURN / 12 * len(people)
                / max(people_in.get(building, 0) + len(people), house.get("room", 0)))
        if self.cash(graph, key) >= rent + needs.get(key, 0.0):  # a month's rent and food
            for node in people:
                node.home_building_id = building
                node.beggar = False
            people_in[building] = people_in.get(building, 0) + len(people)
            self._year["homeless: found a home"] += len(people)

    def _commune_borrow(self, graph, amount: float, alive) -> None:
        """Prestanze: the commune borrows what it lacks from the households
        with the most cash, each keeping a year of its own basket, at FORCED_LOAN_RATE."""
        if amount <= 1e-9:
            return
        size = defaultdict(int)
        for node in alive:
            size[household_key(node)] += 1
        lenders = sorted((person_key(n.resident_id) for n in alive if has_purse(n)),
                         key=lambda k: (-graph.money.get(k, 0.0), k))
        for key in lenders[:10]:
            # keeps a year of the household's basket
            spare = graph.money.get(key, 0.0) - BASKET_PER_PERSON * size[self.household_of(graph, key)]
            if spare <= 1e-9:
                break  # sorted by cash: nobody further down can lend either
            lent = self._pay(graph, key, COMMUNE, min(amount, spare), "forced loan")
            graph.debts.append({"debtor": COMMUNE, "creditor": key, "debtor_person": None,
                                "creditor_person": key[1], "amount": lent, "rate": FORCED_LOAN_RATE,
                                "kind": "forced loan", "behind": 0})
            self._year["commune: forced loans"] += lent
            amount -= lent
            if amount <= 1e-9:
                return

    def _hardship(self, graph, members, rng: random.Random, day: int) -> None:
        """The month's hunger, after all help (user, 2026-10-01): counts each
        member's hungry months; a household hungry BEG_AFTER_MONTHS begins to
        beg (most members; begging is by family: a lodger's hunger isn't their
        hosts'), and stops after BEG_STOP_AFTER_FED months fed. Beggars ask
        people they know: the devout and those who like them give most. Small
        children and the old can die of hardship while hungry."""
        families = [(key, family) for key in members for _, family in self._family_shares(graph, key)]
        for _, people in families:
            key = head_of(graph, people).resident_id  # begging months are counted per family
            short = graph.hunger.get(people[0].resident_id, 0.0)
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
        for key, people in families:
            for node in people:
                if not (node.beggar and node.alive):
                    continue
                ties = list(graph.ties_of(node.resident_id).items())
                for other, edge in rng.sample(ties, min(BEG_ASKS, len(ties))):
                    giver = graph.nodes[other]
                    if (not giver.alive or giver.beggar or giver.ses == "very_poor" or other in given
                            or household_key(giver) == key or not has_purse(giver)):
                        continue
                    feeling = edge.valence_a_to_b if edge.resident_a == other else edge.valence_b_to_a
                    chance = BEG_GIVE_BASE + BEG_GIVE_PIETY * giver.religiousness + BEG_GIVE_WARMTH * max(0.0, feeling)
                    if rng.random() < chance * (0.5 if giver.ses == "poor" else 1.0):
                        given.add(other)
                        self._year["begging: alms"] += self._pay(graph, person_key(other), earner_key(graph, node),
                                                                 BEG_GIFT, "alms")

    def _collect_alms(self, graph, members) -> None:
        """Devout middling and rich adults give a little to the Church each month (user, 2026-10-01)."""
        for key, people in members.items():
            usual = self._household_income(graph, key)
            if usual <= 0:
                continue
            adults = [n for n in people if (n.age or 0) >= 18]
            for node in adults:  # from the giver's own purse (user, 2026-10-12)
                if node.ses in ("middling", "rich", "very_rich") and node.religiousness >= DEVOUT:
                    given = self._pay(graph, person_key(node.resident_id), CHURCH, ALMS_SHARE * usual / len(adults), "alms")
                    self._year["church: alms"] += given

    def _spare(self, graph, key, needs) -> float:
        """Cash a person can lend: what they hold beyond DEBT_LENDER_KEEPS_MONTHS of their household's basket."""
        return graph.money.get(key, 0.0) - DEBT_LENDER_KEEPS_MONTHS * needs.get(self.household_of(graph, key), 0.0)

    def _borrow(self, graph, key, people, shortfall: float, needs, members, merchants) -> None:
        """A household short of its basket borrows (user, 2026-10-01): from
        family and friends who care for it, without interest; then from an
        employer or a rich household it knows; then from a moneylender (the
        two merchant houses with the most cash). None lends to a household
        behind on a debt; a moneylender only up to DEBT_LENDER_LIMIT_MONTHS of
        its usual income. Each debt sits on the tie between the two people;
        it is owed by the household's head, since food is a shared cost, to
        the lender, purse to purse (personal money, 2026-10-12)."""
        debts = graph.debts
        mine = {person_key(n.resident_id) for n in people}
        if any(d["debtor"] in mine and d["behind"] >= DEBT_CUTOFF_MONTHS for d in debts):
            return
        family, patrons = [], []
        for person in people:
            pid = person.resident_id
            boss = graph.employer.get(pid)
            if boss is not None and graph.nodes[boss].alive:
                patrons.append((boss, pid))
            for other, edge in graph.ties_of(pid).items():
                lender = graph.nodes[other]
                if not lender.alive or household_key(lender) == key or not has_purse(lender):
                    continue
                feeling = edge.valence_a_to_b if edge.resident_a == other else edge.valence_b_to_a
                if (edge.source_type in FAMILY or edge.source_type == "friend") and feeling >= DEBT_FAMILY_WARMTH:
                    family.append((other, pid))
                elif lender.ses in RENTIER_CLASSES and feeling >= 0:
                    patrons.append((other, pid))
        houses = sorted((n.resident_id for n in merchants), key=lambda m: (-graph.money.get(person_key(m), 0.0), m))
        lenders = [(m, None) for m in houses[:DEBT_MONEYLENDERS]]
        owed_to_lenders = sum(d["amount"] for d in debts if d["debtor"] in mine and d["kind"] == "moneylender")
        limit = DEBT_LENDER_LIMIT_MONTHS * max(0.0, self._household_income(graph, key)) - owed_to_lenders
        for group, kind, rate in ((family, "family", 0.0), (patrons, "patron", DEBT_PATRON_RATE),
                                  (lenders, "moneylender", DEBT_LENDER_RATE)):
            for lender, borrower in group:
                if shortfall <= 1e-9:
                    return
                lender_key = person_key(lender)
                if household_key(graph.nodes[lender]) == key:
                    continue
                amount = min(shortfall, self._spare(graph, lender_key, needs))
                if kind == "moneylender":
                    amount = min(amount, limit)
                if amount <= 1e-9:
                    continue
                if kind == "moneylender":
                    limit -= amount
                    borrower = head_of(graph, people).resident_id
                debtor = person_key(head_of(graph, people).resident_id)  # food is a shared cost: the head owes it
                self._pay(graph, lender_key, debtor, amount, "loan")
                shortfall -= amount
                debts.append({"debtor": debtor, "creditor": lender_key, "debtor_person": borrower,
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
        A debtor pays from their own purse beyond their usual share of their
        household's costs. A dead debtor's debts are settled by their estate
        (settle_estate) or written off."""
        kept = []
        for debt in graph.debts:
            key, creditor = debt["debtor"], debt["creditor"]
            if not (self._living(graph, key) and self._living(graph, creditor)):
                self._year["debt: written off"] += debt["amount"]
                continue
            if debt["kind"] == "forced loan" and getattr(graph, "commune_lots", None) and any(
                    n.is_noble or n.ses == "very_rich" for n in self._owners(graph, creditor)):
                self._repay_in_land(graph, debt)
                if debt["amount"] <= 0.01:
                    continue
            interest = debt["amount"] * debt["rate"] / 12
            debt["amount"] += interest
            due = interest + debt["amount"] / DEBT_TERM_MONTHS
            keep = self._paid_in.get(key, 0.0) if is_person(key) else needs.get(key, 0.0)
            paid = self._pay(graph, key, creditor, min(debt["amount"], max(0.0, graph.money.get(key, 0.0) - keep)), "debt repaid")
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
                    owned = max(0.0, graph.land.get(key, 0.0))
                    seized = min(owned, debt["amount"])
                    if seized > 0:
                        graph.land[key] -= seized
                        graph.land[creditor] = graph.land.get(creditor, 0.0) + seized
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
            graph.land[COMMUNE] -= part
            graph.land[debt["creditor"]] = graph.land.get(debt["creditor"], 0.0) + part
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
        persons = sorted(person_key(n.resident_id) for group in members.values() for n in group if has_purse(n))
        for lot in list(lots):
            buyer = max(persons, key=lambda k: graph.money.get(k, 0.0), default=None)
            if buyer is None or graph.money.get(buyer, 0.0) < lot:
                break  # the richest can't pay for this one; later lots wait their turn
            self._pay(graph, buyer, COMMUNE, lot)
            graph.land[COMMUNE] -= lot
            graph.land[buyer] = graph.land.get(buyer, 0.0) + lot
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
        graph.day_labour_spare = total / max(1e-9, sum(wanted)) - 1.0  # work beyond what labourers take: draws newcomers
        for node, want in zip(labourers, wanted):
            want *= scale
            to = earner_key(graph, node)
            for key in budget:
                if want <= 1e-9:
                    break
                if budget[key] <= 1e-12:
                    continue
                paid = self._pay(graph, key, to, min(want, budget[key]))
                budget[key] -= paid
                want -= paid
                income[key] -= paid
                income[to] += paid

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
        places = None  # free places for children, found when first needed
        for node in alive:
            if not node.is_noble and (node.age or 0) >= 18 and node.ses not in RENTIER_CLASSES:
                seekers += 1
            if node.occupation in PRECARIOUS and rng.random() < JOB_LOSS_PER_MONTH:
                node.occupation = None
                graph.employer.pop(node.resident_id, None)
            if node.occupation is None and _working_child(node):
                if rng.random() < JOB_FIND_PER_MONTH:
                    if places is None:
                        places = _free_child_places(alive)
                    teen = node.age >= WORKING_AGE  # spins for a merchant, or takes a free place
                    if places and (not teen or not merchants or rng.random() < CHILD_PLACE_SHARE):
                        node.occupation, node.workplace_building_id = places.pop(rng.randrange(len(places)))
                    elif teen and merchants:
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
                shop_of[seller.workplace_building_id].append((person_key(seller.resident_id), household_key(seller)))
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
                    for seller_key, home in shop_of[place]:
                        if home != key:
                            weight[seller_key] += edge.time / len(shop_of[place])
            # imported shop ties can have time 0 (~14% at Riverport; children copy
            # them): a household with only those buys from any seller, as untied
            if any(weight.values()):
                shops[key] = (list(weight), list(weight.values()))
        return shops, {seller for keys, _ in shops.values() for seller in keys}

    def _buy(self, graph, key, amount: float, sellers, rng: random.Random, income, shops=None) -> None:
        """Bought in town from any seller, as before; when that is a shop or
        tavern (one somebody is tied to), from the ones this household knows
        (`shops`, see _tied_shops). The seller's takings count as their income."""
        if amount <= 0 or not sellers:
            return
        seller = person_key(sellers[rng.randrange(len(sellers))].resident_id)
        home = self.household_of(graph, key)
        if shops and seller in shops[1] and home in shops[0]:
            seller = rng.choices(*shops[0][home])[0]
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
        merchant = person_key(merchants[rng.randrange(len(merchants))].resident_id)
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
        yearly = {key: 12 * v for key, v in self._income.items()}  # per person
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
                node.ses = _capped(node, class_for(per_person.get(node.resident_id, 0.0), node.ses, lines))

    def summarize(self, state) -> Dict[str, float]:
        # recomputed only when something it reads changed (speed-up 2026-09-30:
        # sorting every household's money every day cost more than the month)
        graph = self._graph
        signature = (self._months, len(graph.deaths), graph.alive_count, getattr(graph, "dowries", 0.0),
                     len(graph.money), self._unemployed, self._hungry)
        if signature != getattr(self, "_summary_signature", None):
            self._summary = self._compute_summary(graph)
            self._summary_signature = signature
        paid = {f"paid_{k.replace(' ', '_').replace(':', '')}": round(v, 1)
                for k, v in getattr(graph, "payment_totals", {}).items()}
        return {**self._summary, **paid} if paid else self._summary

    def _compute_summary(self, graph) -> Dict[str, float]:
        held = defaultdict(float)  # per household, its members' wealth (comparable with before 2026-10-12)
        for node in graph.nodes.values():
            if node.alive:
                held[household_key(node)] += person_wealth(graph, node.resident_id)
        living = set(held)
        money = [max(0.0, v) for v in held.values()]
        total = sum(money)
        alive = [n for n in graph.nodes.values() if n.alive]
        classes = defaultdict(int)
        for n in alive:
            classes[n.ses] += 1
        top = sorted(money, reverse=True)[:max(1, len(money) // 10)]
        return {
            "economy_town_money": round(total, 1),  # cash and property
            "economy_town_cash": round(sum(max(0.0, graph.money.get(person_key(n.resident_id), 0.0)) for n in alive), 1),
            "economy_belongings": round(sum(sum(graph.belongings.get(n.resident_id, {}).values()) for n in alive), 1),
            "economy_gini": round(gini(money), 3),
            # a few weeks' wages in hand aren't property
            "economy_propertyless_share": round(sum(1 for m in money if m < PROPERTYLESS_BELOW) / max(1, len(money)), 3),
            "economy_top10_share": round(sum(top) / total, 3) if total else 0.0,
            "economy_hungry_households": self._hungry,
            "economy_unemployed": self._unemployed,
            **{f"economy_class_{c}": classes[c] for c in CLASSES},
            "economy_dowries": round(getattr(graph, "dowries", 0.0), 1),
            "economy_households": len(living),
            "economy_commune_cash": round(graph.money.get(COMMUNE, 0.0), 1),
            "economy_church_cash": round(graph.money.get(CHURCH, 0.0), 1),
            "economy_beggars": sum(1 for n in alive if n.beggar),
            "economy_homeless": sum(1 for n in alive if n.home_building_id is None) if graph.houses else 0,
            "economy_evictions": self._evictions,
            "economy_houses_bought": self._houses_bought,
            "economy_houses_owner_occupied": len({(n.home_building_id, household_key(n)) for n in alive}
                                                 & {(b, self.household_of(graph, h["owner"]))
                                                    for b, h in graph.houses.items() if is_person(h["owner"])}),
            "economy_houses_church": sum(1 for h in graph.houses.values() if h["owner"] == CHURCH),
            "economy_houses_commune": sum(1 for h in graph.houses.values() if h["owner"] == COMMUNE),
            "economy_houses": len(graph.houses),
            "economy_houses_new": sum(1 for h in graph.houses.values() if h.get("built") and "left" not in h),
            "economy_workshops_new": getattr(graph, "workshops_opened", 0),
            "economy_houses_building": sum(1 for h in graph.houses.values() if "left" in h),
            "economy_house_room": sum(h.get("room", 0) for h in graph.houses.values() if "left" not in h),
            "economy_hardship_deaths": self._hardship_deaths,
            "economy_grain_price": round(self._harvest, 2),
            "economy_famines": self._famines,
            **{f"economy_{k}": v for k, v in self.food.summary().items()},
            **{f"economy_{k}": v for k, v in self.crafts.summary().items()},
            **{f"economy_{k}": v for k, v in self.trade.summary().items()},
            "economy_debt_total": round(sum(d["amount"] for d in graph.debts), 1),
            "economy_debts": len(graph.debts),
            "economy_debts_behind": sum(1 for d in graph.debts if d["behind"] > 0),
            **{f"economy_debt_{kind}": round(sum(d["amount"] for d in graph.debts if d["kind"] == kind), 1)
               for kind in ("family", "patron", "moneylender", "forced loan")},
            "economy_commune_property": round(graph.land.get(COMMUNE, 0.0), 1),
            **{f"economy_estates_{k.replace(' ', '_')}": v for k, v in self._estates.items()},
            **{f"economy_{k}": round(v, 1) for k, v in self._last.items()},
        }


# --- Households forming and passing on (economy slice 2, user 2026-09-30) ---

DOWRY_SHARE = 0.10  # book §7: a daughter's marriage moves ~5-15% of her family's wealth
FAMILY_TIES = FAMILY  # wider family takes in the evicted too (2026-10-10)


def _move_wealth(graph, from_key, to_key, fraction: float) -> float:
    """Move `fraction` of a household's cash and property to another
    household (to_key None: to the commune, out of town). Returns the amount."""
    fraction = max(0.0, min(1.0, fraction))
    moved = 0.0
    for store in (graph.money, getattr(graph, "land", {})):
        amount = max(0.0, store.get(from_key, 0.0)) * fraction
        store[from_key] = store.get(from_key, 0.0) - amount
        if to_key is not None:
            store[to_key] = store.get(to_key, 0.0) + amount
        moved += amount
    return moved


def new_building(graph, building_type: str, capacity: int, people) -> int:
    """The id of a building the sim puts up. While the town is stored in a
    database (town.py), TownShape places it on the map, near where `people`
    live (graph.place_building). The sim's rules decide what gets built
    (user, 2026-10-11: TownShape draws the town, it doesn't set its rules):
    with no room on the map it's built all the same, unplaced, with an id
    below zero, clear of TownShape's. Not stored: the next free id."""
    if graph.place_building is None:
        return max([*graph.building_types, *getattr(graph, "houses", {})], default=0) + 1
    district = next((n.district_id for n in people if n.district_id is not None), None)
    building = graph.place_building(building_type, capacity, district)
    if building is None:
        building = min(min(graph.building_types, default=0), 0) - 1
    return building


def new_household_id(graph) -> int:
    ids = [n.household_id for n in graph.nodes.values() if isinstance(n.household_id, int)]
    graph.next_household_id = max(getattr(graph, "next_household_id", 0), max(ids, default=0) + 1,
                                  getattr(graph, "max_stored_household_id", 0) + 1)
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
    joins it. The bride's father (else her mother) gives her a dowry,
    DOWRY_SHARE of his cash and land, which stays hers (user, 2026-10-12);
    for two men or two women, each family gives half of that to its own."""
    first, second = graph.nodes[a], graph.nodes[b]
    old_first, old_second = household_key(first), household_key(second)
    if _dependent_children(graph, first):
        home = old_first
    elif _dependent_children(graph, second):
        home = old_second
    else:
        home = new_household_id(graph)
    if hasattr(graph, "money"):
        for node in (first, second):
            if first.gender == second.gender:
                share = DOWRY_SHARE / 2
            else:
                share = DOWRY_SHARE if node.gender == "female" else 0.0
            parents = [p for p in _kin(graph, node.resident_id, "parent") if (p.age or 0) > (node.age or 0)]
            if share and parents:
                giver = max(parents, key=lambda p: (p.gender == "male", p.age or 0))
                dowry = _move_wealth(graph, person_key(giver.resident_id), person_key(node.resident_id), share)
                graph.dowries = getattr(graph, "dowries", 0.0) + dowry
                log_payment(graph, "dowry", person_key(giver.resident_id), person_key(node.resident_id), dowry)
    first.household_id = second.household_id = home = _real_household_id(graph, home)
    if home not in (old_first, old_second):
        mark_new_household(graph, home, "newlyweds")


def _real_household_id(graph, key):
    """An arrival living alone has a stand-in key: give them a real household id."""
    if not isinstance(key, tuple):
        return key
    return new_household_id(graph)


def settle_estate(graph, dead: int) -> Optional[str]:
    """What a dead person owned (personal money, user 2026-10-12): their
    debts are paid first, then it goes to their children in equal parts,
    wherever they live (2026-09-30, user: to all children); with none, to a
    surviving spouse; then the parents, then the siblings, then the nephews
    and nieces, like a title (2026-10-01: 183 heirless estates in 25 years
    went out of town, wealth 91k -> 70k fl); with no kin to the commune
    (COMMUNE), which sells the land to whoever can pay. A widow keeps what is
    hers, her dowry with it, and the house she lives in (a widow's right to
    stay in her husband's house). Other houses aren't split: they go to the
    eldest heir, and so do debts owed to the dead. Returns what happened, for counting."""
    if not hasattr(graph, "money"):
        return None
    node = graph.nodes[dead]
    key = person_key(dead)
    belongings = getattr(graph, "belongings", {}).pop(dead, {})
    if not (graph.money.get(key) or graph.land.get(key) or house_wealth(graph, key) or any(belongings.values())
            or any(d["creditor"] == key or d["debtor"] == key for d in getattr(graph, "debts", []))):
        return None
    _pay_debts_from_estate(graph, key)
    children = [graph.nodes[o] for o in graph.neighbors(dead)
                if graph.get_edge(dead, o).source_type == "parent" and graph.nodes[o].alive
                and (graph.nodes[o].age or 0) < (node.age or 0)]
    nephews = [n for s in graph.neighbors(dead) if graph.get_edge(dead, s).source_type == "sibling"
               for n in _kin(graph, s, "parent", younger=True)]
    for spouse in _kin(graph, dead, "spouse"):
        for building, house in getattr(graph, "houses", {}).items():
            if house["owner"] == key and building == spouse.home_building_id:
                set_house_owner(graph, building, person_key(spouse.resident_id))
    parents = [n for n in _kin(graph, dead, "parent") if (n.age or 0) > (node.age or 0)]
    for heirs, outcome in ((children, "split among children"), (_kin(graph, dead, "spouse"), "spouse keeps it"),
                           (parents, "to parents"), (_kin(graph, dead, "sibling"), "to siblings"),
                           (nephews, "to nephews and nieces")):
        if heirs:
            eldest = person_key(max(heirs, key=lambda n: (n.age or 0, -n.resident_id)).resident_id)
            pass_houses(graph, key, eldest)
            for debt in getattr(graph, "debts", []):
                if debt["creditor"] == key:
                    debt["creditor"], debt["creditor_person"] = eldest, eldest[1]
            for share, heir in enumerate(heirs):  # equal parts: 1/n, then 1/(n-1) of what's left, ...
                _move_wealth(graph, key, person_key(heir.resident_id), 1.0 / (len(heirs) - share))
                own = getattr(graph, "belongings", {}).setdefault(heir.resident_id, {})
                for good, value in belongings.items():
                    own[good] = own.get(good, 0.0) + value / len(heirs)
            return outcome
    graph.money.setdefault(COMMUNE, 0.0)
    pass_houses(graph, key, COMMUNE)  # the commune becomes the landlord (user: it can be one)
    lot = max(0.0, graph.land.get(key, 0.0))
    _move_wealth(graph, key, COMMUNE, 1.0)
    if lot > 0:
        graph.commune_lots = getattr(graph, "commune_lots", []) + [lot]
    return "to the commune"


def _pay_debts_from_estate(graph, key) -> None:
    """A dead person pays what they owe before heirs or the commune get the rest."""
    for debt in getattr(graph, "debts", []):
        if debt["debtor"] != key:
            continue
        for store in (graph.money, graph.land):
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
    child. Their money is their own. Nobles stay (their household
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
            for n in left:
                n.household_id = home
            return outcome
    return None
