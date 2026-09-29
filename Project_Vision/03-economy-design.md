# Economy Design

> **Status (2026-09-29):** reviewed by the user. Decided: florins only;
> Riverport a small city (~45 fl a person); before the plague; estates
> split among all children; merchants as a class, the town's trade with the
> outside, in slice 1; jobs from workshops, putting-out, day labour and
> farm work, set by the sim's importer; debt with several kinds of lender;
> beggars and death from hardship. Order: see the reply in section 6.

### A proposal for giving the town money: who has it, how they earn and spend it, what limits the rich, and how it feeds class, stress and migration. Written 2026-09-29 from the user's parameter book (`medieval_city_sim_parameters.md` / `.json`) for the user to read and comment on before anything is built.

**How to comment:** add a line starting `> Feedback:` under any section or
item, as in [`02-long-run-findings.md`](02-long-run-findings.md). Each
proposal is **Proposed** until you agree, change it or reject it.

**Sources:**
- The parameter book, cited below by section (for example "book §3b").
  Grades A/B/C are the book's own: C numbers are assumptions to change freely.
- What TownShape already stores (`demo_riverport_town.db`, 1,889
  residents, 483 households).
- The sim's own long runs (`02-long-run-findings.md`, the "Riverport Runs
  Compared" dashboard).

---

## 1. What the economy has to do for the sim

Each is a problem the sim already has, or a design the user asked for that
can't be built without money:

| Need | Today | Where it came up |
|---|---|---|
| **Class mobility.** People should rise and fall; fortunes should be limited. | `ses` is fixed for life; the rich tripled in 50 years (6% -> 14% of the town) | 50-year run; review 3.3 |
| **Migration driven by wages and work.** People come for jobs, open shops, move out when desperate and able to pay for it. | Arrivals only replace the dead, capped by a growth target | review 3.1; user feedback |
| **Real poverty behind stress.** Hunger and debt, not a class label. | Stress counts "poor" as a flat 0.4 | stress, 2026-09-27 |
| **Merchants, homeowners, landlords.** Who owns the houses the poor rent. | Don't exist | discussion list |
| **Taxes, riots, coups.** Taxes raising unrest and noble anger. | Taxes don't exist | vision: Taxes, Nobles |

---

## 2. What exists today

**In the sim:** no money at all. `ses` (poor / middling / rich) is copied
from TownShape at import and never changes. A baby takes its mother's
class, an arrival the dead person's.

**In TownShape** (never imported by the sim):
- **Household wealth:** a number per household, 0 to 5,402 (average 345).
  Starting wealth is 500 for rich households and 50 for poor ones, plus
  yearly income, minus purchases and taxes.
- **Daily income by role:** unemployed 0.5, apprentice 1.0, worker 2.5,
  noble 5.0, times 1.3 if rich, times a random 0.7-1.3.
- **20 goods, about 26,000 purchases, about 2,700 tax payments.**
- **Very few jobs:** 1,734 of 1,889 residents have no occupation; the
  largest trades are farmhands (35), servants (33) and guards (31).
- **Only two classes:** 1,778 poor, 111 rich, no middling.

TownShape's units are unnamed and its numbers aren't calibrated to the
book, so the proposal below keeps TownShape's structure (who is rich, who
works where, which household is which) and rescales the amounts to the
book's florins.

> Feedback: 

---

## 3. Units and scale

- **Proposed: one unit, the florin**, for all amounts. Wages are quoted in
  soldi in the book and converted at **64 soldi to the florin** (book §1,
  1349). The two-currency detail (wages in silver losing ground to gold) is
  left out at first: it matters for decades-long inflation, not for who is
  rich.
- **Which kind of place is Riverport?** At about 1,900 people it is below
  the book's "small city" (Prato, 3,500-10,000). The book's 1427 wealth per
  person: villages 32 fl, small cities about 45 fl, medium cities 70-85 fl
  (book §3a). **Proposed: 45 fl per person** (a small city), a town
  parameter so a bigger town can be set richer.
- **Which period?** The book gives two regimes: before the plague (many
  people, low wages, high inequality) and after it (wages up, inequality
  down for a century). **Proposed: before the plague** (Gini about 0.70) as
  the default, the other as an option. An epidemic big enough could later
  move a town from one to the other on its own.

> Feedback: What I have read above seems really good. 

---

## 4. The model, in slices

Each slice is buildable and checkable on its own, in this order.

### 4.1 Slice 1 — Household money, income and spending — Proposed

- **Wealth per household**, in florins, imported from TownShape's
  household wealth, rescaled so the town matches the book: average about
  45 fl per person, Gini about 0.70, and a share of households with no
  taxable property between the book's 14% (Florence 1427) and 38%
  (Prato 1372). **Proposed default: 25%**.
- **Income, once a month:**
  - **Wages** by kind of work, 250 working days a year (book §4d):
    unskilled about 8.4 soldi a day (about 33 fl a year), skilled about 13.4
    (about 52 fl), servants about 15 fl a year plus board. The jobless
    (most of TownShape's adults) get **day labour**: some weeks of
    unskilled wages, drawn at random.
  - **Property income:** about **7% of wealth a year** (book §3e, the rate
    the 1427 census used).
  - **Side income:** occasional windfalls, as the book warns a job's wage
    isn't a person's income (book §4c).
- **Spending, once a month:**
  - **Food first:** a grain ration of about 0.9 kg per person per day at
    about **13 soldi a staio** in a normal year (book §5, §6). An unskilled
    family of four then spends about 45% of its wage on grain, the book's
    check (book §5c).
  - **Everything else** (rent, clothing, fuel) as a share of income until
    rents are modelled (book §9 lists rents as missing data).
  - **Status spending** for the richest: a fixed share of income (book §7).
- **Class follows money:** `ses` becomes a label read from wealth
  (thresholds set so the town starts with today's split), so people move
  between classes as their money changes. This alone should stop the rich
  tripling: today a rich family stays rich forever and survives disease
  better.
- **Grain price shocks:** harvests vary about 2.5x between good and bad
  years; a famine year can price grain above an unskilled family's whole
  income (book §5c, §6).
- **Checks** (book "validation targets"): Gini about 0.70 staying there in
  quiet years; unskilled welfare ratio about 1 (bare subsistence); grain
  about 45% of an unskilled budget; a top household's property income 30-40x
  an unskilled wage.

> Feedback: I think this is all very good.

### 4.2 Slice 2 — What limits the rich — Proposed

The book's section 7, each as a rule:
- **Estates split among heirs** at death, equally among surviving sons
  (book: equal division). **Question for the user:** sons only, as
  historically, or all children, for the fantasy setting?
- **Dowries:** a daughter's marriage moves about 5-15% of her family's
  wealth to her husband's family.
- **Merchant firm failure:** a small yearly chance that a large merchant
  fortune is wiped out (the Bardi and Peruzzi collapses).
- **Forced loans in bad years** (once taxes and wars exist).
- **Confiscation after a coup:** the losing side's goods can be seized
  (the sim already has coups).
- **Status spending** (from slice 1).
- **Check:** in quiet years the richest tenth's share of wealth holds
  steady instead of growing.

> Feedback: regarding heirs, let's make it all children. The rest is good. We have to also make rules for who inherits money upon death of a noble, but it can come later. 

### 4.3 Slice 3 — Poverty that hurts — Proposed

- **Hunger replaces the flat "poor" stress pressure:** stress rises when a
  household can't afford its grain (welfare ratio below 1), falls when it
  can. A famine year then raises stress town-wide, and with it theft.
- **Debt:** a household that runs out of money borrows, at interest; the
  book lists interest rates as missing data, to be filled from Goldthwaite.
- **Charity and public grain** in famines: the commune bought grain and fed
  most of the city in 1329 and 1346-47 (book §6). Later, possibly through
  the Church (priests) and nobles.
- Opens the vision's older items: **beggars**, and **death from hardship**
  after long poverty.

> Feedback: I like the idea of debt, but who are people getting indebted to? That is also an important dynamic. Beggars and death from hardship should be introduced. 

> **Reply (2026-09-29):** Options for who lends, and I'd have more than one:
> 1. **Family and friends:** small loans, usually without interest; the
>    commonest credit. A new debt sits on the tie they already have.
> 2. **Moneylenders and pawnbrokers:** a licensed profession, at high
>    interest against a pledged object.
> 3. **Rich households and merchants:** larger loans at interest, often to
>    people who work for them, which gives the lender leverage.
> 4. **Charity:** confraternities and the Church give rather than lend (the
>    Monte di Pieta, a charitable pawn bank, came later, from the 1460s).
>
> Each debt links a debtor to a creditor. A late or unpaid debt breeds
> resentment on both sides; a creditor can seize goods, or push a desperate
> debtor into theft or begging. Beggars and death from hardship go into this
> slice, as you said.

### 4.4 Slice 4 — Jobs and organic migration — Proposed

- **Jobs as places:** each workplace has a number of posts (from TownShape's
  buildings and occupations), with a wage. Open posts draw arrivals from
  outside (people come for work, the user's rule); a full town draws fewer.
  This replaces the growth target.
- **Who arrives:** mostly poor single young adults, some whole families,
  a few with money and a trade who can open a shop if a building is free
  (user feedback, review 3.1).
- **Moving out:** only under extreme stress and with enough money to
  leave (user rule).
- **Check:** the town stays a demographic sink (deaths above births) and
  grows slowly because arrivals outnumber the gap, as in the research notes.

> Feedback: Good. 

### 4.5 Slice 5 — Merchants, homeowners and landlords — Open

- Who owns each house; rent flowing from tenants to owners; some
  merchants owning the houses of the poor and middling (user, discussion
  list). Needs rents (book §9: missing, from Goldthwaite).
- A merchant class as its own group: trade profits riskier than land,
  with the failure risk from slice 2.

> Feedback: We definitely have to add a merchants as a class. They are the ones importing and exporting goods to and from the city. They are basically the main source of flow of money from/to outside of the enclosed system of the city. 

> **Reply (2026-09-29):** Agreed, and it changes the order (see section 6):
> without merchants the town has no money coming in or going out, so wages
> and prices would have nothing behind them. Merchants buy what the town
> makes and sell it outside, and bring in what it lacks (grain above all).
> Their trade is the inflow; imports are the outflow.

---

## 5. Open questions

1. **Currency:** florins only (proposed), or both florins and lire/soldi?
2. **Riverport's size class:** small city at about 45 fl per person
   (proposed), or a village (32 fl)?
3. **Period:** before the plague (proposed default), or after?
4. **Inheritance:** sons only, or all children?
5. **Jobs:** TownShape leaves 92% of residents without an occupation.
   Should the sim invent a fuller job list (the book says building artisans
   were only 4-8% of a city, with day labour and the wool trade employing
   many more), or should TownShape's generator produce more jobs?
6. **Fantasy adjustments:** anything in the book to deliberately not
   follow, as with Florence's marriage ages?

> Feedback: florins only. Riverport is a small city. Before plague. All children. We cannot have 92% of people being jobless. What would the best solution for this be? Let's discuss options together. In terms of fantasy adjustements, just make sure to also consider magic-based shops (the rules for how many should already exist within town-shape)

> **Reply (2026-09-29):** Florins, a small city at about 45 fl a person,
> before the plague, all children inherit: noted. On jobs, TownShape makes
> jobs as posts in buildings (a shop has a shopkeeper and 2 staff, a
> farmstead a farmer and 3 farmhands, a manor a noble and 3 servants). In
> Riverport the 203 houses and the **28 workshops** offer no posts at all,
> hence 92% jobless. Options, which combine:
> 1. **Workshops get trades:** each of the 28 gets a craft (weaving,
>    dyeing, tanning, carpentry, baking, coopering...) with a master and
>    3-5 workers. About 100-150 jobs.
> 2. **Work at home for a merchant (putting-out):** how most of the medieval
>    cloth trade worked, and a third of Florence lived from wool. Poor
>    households spin, card or weave at home, paid by the piece by a
>    merchant. Employs many, including women and older children.
> 3. **Day labour:** porters, carters, builders hired day by day; work on a
>    given day depends on demand, so income is irregular.
> 4. **Farm work outside the walls:** Riverport's farmsteads and fields.
> 5. **Housework counted as work:** running a household was a full-time
>    job, often alongside piecework.
>
> My suggestion: 1, 2 and 3 together, set by the sim's importer (like the
> adapted importer) and written to move into TownShape's generator later.
> The target is an occupational mix where nearly every adult has
> some work, most of it poorly paid and irregular.
>
> **Magic shops:** TownShape adds "arcane shops" in the merchant district
> (a mage and 2 apprentices each), in proportion to the town's magic
> setting. Riverport's is 0, so it has none; a town with magic would get
> them as posts, selling TownShape's magic goods (healing potions, spell
> scrolls, arcane reagents) with their own prices and customers.

> **Decided (user, 2026-09-29):** all four job sources combined: workshops
> get trades, putting-out work at home for merchants, day labour, and more
> farm work outside the walls. Set by the sim's importer now, written to
> move into TownShape's generator later.

> **Decided (user, 2026-09-30):** adults can be unemployed while they look
> for work (built: about 5%, work found in about 4 months, precarious work
> lost at 1% a month). Unemployment does **not** add stress directly: a
> long spell makes a household poor, and poverty raises stress. That needs
> slice 3, where hunger (not affording the basket) replaces today's flat
> "poor" pressure, which reads a class label 94% of the town carries.
>
> **Decided (user, 2026-09-30):** a noble title passes to a child (at home
> first), then a sibling, then a nephew or niece, eldest first.

---

## 5b. Findings from the first full run, to solve (2026-09-30)

The first 25-year run with slice 1 and parts of slice 2 (households,
dowries, inheritance to all children, unemployment, five classes; seed 1,
epidemics off). Dashboard: "Riverport, 25 Quiet Years" v4,
https://claude.ai/artifact/2kmbLQcyGg34eG1bcDSkqC.

Works: class moves (rich 8% -> 10-12%, no longer growing without limit);
the very rich halve (17 -> ~8 people) as estates split among all
children; nobles 14 -> 12 with the wider succession; crime, faith,
feelings and marriage hold; ties per resident 83 -> 78.

**To solve:**
1. **Wealth drains away** (about 91,000 fl at year 5, 70,000 at year 25).
   Cash holds near 16,000; the loss is property from 183 heirless estates
   going to "the commune", which is outside the town. Proposed: heirless
   estates pass to siblings, then nephews (like titles), otherwise stay
   in town (commune or Church as a household that spends).
2. **Households shrink** (520 -> 964 households for +14% people; 3.6 ->
   2.2 people each; Florence 1427 about 4). Every arrival lives alone,
   newlyweds always start a household, widows stay alone. Proposed: some
   arrivals come as families (slice 4), widows join a child's household.
3. **Poverty grows** (very poor 15% -> 9% by year 5, then 23.5% by year
   25; hungry households 31 -> 134; Gini 0.75 -> 0.79, book ~0.70).
   Likely driven by 2; slice 3 (debt, charity, beggars) is the rest.
4. **Runs slowed** to 42 min for 25 years (24-30 before the economy;
   ~110 s a year by years 16-20). **First priority (user, 2026-09-30).**

> Feedback:

---

## 6. Proposed order

1. Slice 1 (money, income, spending, class from wealth), checked with a
   25-year run against the book's targets.
2. Slice 2 (limits on the rich), checked with a 50-year run: the richest
   tenth's share should hold.
3. Slice 3 (hunger, debt, famine relief).
4. Slice 4 (jobs and organic migration), replacing the growth target.
5. Slice 5 (merchants and landlords).

> Feedback: are you sure we should add the merchants and landlords first? Honest question, I wonder why you are putting them last. 

> **Reply (2026-09-29):** Honest answer: I put them last because I saw them as
> an extra layer on top of basic money, and because rents are missing from
> the book. Your point about merchants is right: they are where money
> enters and leaves, so they belong in the first slice. Landlords can still
> come later, since rents need data and homes matter most once migration
> exists. Revised order:
> 1. **Jobs** (the options above) **+ money, income and spending + merchants
>    as the town's trade with the outside.**
> 2. Limits on the rich, with inheritance to all children.
> 3. Debt with lenders, hunger, beggars, death from hardship.
> 4. Organic migration.
> 5. Homeowners, landlords and rent.
