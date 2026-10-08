# Goods and inventories — design proposal (2026-10-01)

**Status: Proposed.** Comment under any item with `> Feedback:`.

## 1. What exists today

Only money moves. Each month a household spends its basket (grain and
"everything else"), rent, and anything above its needs. The money is
conserved: it goes to farmers, merchants, local sellers, landlords, day
labourers and the commune's gabelle. Since 2026-10-01 local purchases go
to the shops a household is tied to, weighted by how much it uses each one.

But nothing is made, stocked or used up. A baker sells no bread, a tanner
buys no hides, and a shop with a dead master still takes the town's
money through whoever works there. The user asked: when someone buys 5 kg
of flour or leather, does it leave the seller's stock and reach the buyer?
Today, no.

## 2. Proposal: a small set of goods

Few goods, each with a clear chain, so the model stays readable and fast.

| Good | Made by | From | Bought by |
|---|---|---|---|
| Grain | farmers (half), imports via merchants (half) | land | bakers, households that bake at home |
| Bread | bakers | grain | every household (most of its food) |
| Wine | farmers, taverns sell it | land | households, taverns |
| Wool cloth | weavers, fullers, dyers (putting-out for merchants) | raw wool (imported) | tailors, merchants (export) |
| Clothing | tailors | cloth | households |
| Leather | tanners | hides (from farmers) | shoemakers, saddlers |
| Shoes | shoemakers | leather | households |
| Tools and ironwork | blacksmiths | iron (imported) | workshops, farmers |
| Wood and barrels | carpenters, coopers | timber (imported) | households, taverns, merchants |
| Pottery | potters | clay | households |
| Building work | masons | stone | the commune's public works, house buyers |
| Magic goods | mages (TownShape's magic shops) | reagents (C) | the rich |
| Luxuries | merchants (imports) | outside | the rich |

> Feedback:

## 3. How it would work

**Stocks.** Each seller household holds a stock of what it makes. Each
household holds a small stock of what it consumes (a week or two of food;
the rich store grain for the year, as Florentine families did).

**Production, monthly.** A workshop turns inputs into output: its master
and hands each make a fixed amount a month (C, from the book's wages and
prices where known), as far as inputs allow. A baker with no grain bakes
no bread; a tanner with no hides makes no leather.

**Buying.** A household's budget splits into goods by shares (grain or
bread about 45% of an unskilled budget, book §5c; clothing, fuel, the rest).
It buys from its tied shops first; a shop out of stock sends it to the
next one it knows, then any shop in town, then it goes without. Going
without food is hunger (slice 3).

**Prices.** Each good has a base price (the book's where it has one:
grain 13 soldi a staio in a normal year, cloth per bolt, wages). The price
moves with stock: scarce goods cost more, gluts sell cheap (C: a simple
rule, for example +/-10% a month toward the level where stock covers about
a month of demand). The harvest keeps setting grain's price as today.

**Merchants.** They import what the town lacks at the outside price plus
their margin, and export what piles up (cloth above all), as today, but
now in goods.

**What it brings:** a dead baker means a bread shortage until someone
takes over; a famine shows as empty granaries and bakers with no flour; a
shop with more customers needs more hands; prices rise and fall with
events, and stress follows them.

> Feedback:

## 4. Suggested slices

1. **Food chain:** grain -> bread (bakers), household food stocks, grain
   price from harvests and stock. The largest share of every budget.
2. **Crafts:** hides -> leather -> shoes; cloth -> clothing; tools; wood;
   pottery. Workshops produce as far as inputs allow.
3. **Prices that move** with stock for every good.
4. **Merchants in goods:** imports of what's short, exports of surplus.
5. **Stores of the rich:** grain hoarding, and selling in dear years
   (a classic source of famine anger).

> Feedback:

## 5. Questions for you

1. **How many goods:** the list above (about 12), or fewer to start?
2. **Household stocks:** should households keep food stores (the rich for
   a year, the poor for days), or buy each month what they eat?
3. **Prices:** should they float with supply, or stay fixed except grain?
4. **Magic goods:** how do TownShape's magic shops fit: what do they sell,
   and to whom?
5. **Speed:** goods add work every month; the food chain alone should be
   cheap, and I'd measure after each slice.

> Feedback: 1. I like the ones you listed. 2. I like the idea of stocks. 3. Prices should definitely float. 4. Magic shops are very expensive, so they need a large enough rich class that exists into town in order to support them. Not all cities get magic shops, only large ones. 5. Good. 

> **Decided (user, 2026-10-01):** all the goods listed; stocks; prices
> float; magic shops only in large towns with a rich class big enough to
> keep them. Start with slice 1, the food chain.

## 6. Slice 1 build plan: the food chain (2026-10-01) — for comments

Only grain and bread become real goods in this slice. The rest of the
basket (55%: wine, oil, cloth, fuel, lodging) stays money, as today.

**A. Grain in staia.** A person eats 0.9 kg of grain a day, about 18
staia a year (book §5). Riverport needs about 38,000 staia a year.
- **Farmers** harvest once a year, in summer. Each farmstead yields a
  fixed amount in a normal year (C, set so the town grows about half
  its grain, as today), times this year's harvest (0.8-1.25, worse in a
  famine). The harvest sets *how much grain there is*, not the price.
- **Merchants** import the rest at the outside price (13 soldi a staio
  normally, more in a regional famine) plus their margin, as much as
  buyers ask for.

**B. Who holds stocks.**
- **Farmers** sell their harvest over the year.
- **Bakers** hold about a month of flour.
- **Households:** the poor buy what they eat each month. Middling and
  rich households buy a year's grain at harvest, when it's cheapest, and
  live off it, as Florentine families did.
- **The commune** keeps a public granary (Florence's Orsanmichele) and
  sells from it in famines at a set price, as in 1329. This replaces
  today's famine relief in money.

**C. Bread.** Most households buy bread from the bakers they know (their
shop ties), and the baker's price is grain plus a margin (C: about 15%).
If the bakers they know are out of flour or dead, they try any baker,
then bake at home from grain (C: costs a little more), then go without.
Going without is hunger, as today. A town that loses its bakers keeps
eating, at a higher cost, until someone takes up the trade.

**D. Prices that move.** Grain's price follows how many months of
demand the town's stocks cover (C: about 13 soldi when stocks cover
about four months, up to the 1329 famine price of about 31 when they
run low, down to about 10 in a glut), and moves a little each month
rather than jumping. Bread follows grain. A bad harvest raises prices
because grain is short, and merchants' imports bring them back down.

**E. What stays the same.** Money is still conserved. Hunger, begging,
debt, famine deaths and stress keep working off what a household could
afford. Speed: a few stocks per household and shop each month should
cost little; I'll measure it.

**Checks:** the 25-year run should show normal years priced about
10-16 soldi, famine years near 28-31, the grain price swinging about
2.5x between good and bad years (book), and the town in balance (no
drift in quiet years).

**Questions for you:**
1. Should the middling and rich store a year's grain, or only the rich?
2. A public granary run by the commune, selling cheap in famines: yes?
3. Hoarding by the rich in dear years (selling high, the slice-5
   idea in §4) is a classic source of riots: now, or later?

> Feedback: only the rich should store. Do add a public granary, yes. And add hoarding.

> **Decided (user, 2026-10-01):** only the rich store a year's grain; the
> commune keeps a public granary; hoarding by the rich in dear years is in
> this slice.

> **Built (2026-10-01), `food.py`.** As planned, with four calibrations:
> - Merchants' cost outside is 0.8-0.95 of normal, so imported grain sells
>   near the book's 13 soldi (at 0.9-1.1 local grain ran out by month 5 and
>   a normal year cost 12% more). Famine years cost 1.8-2.2 outside.
> - The granary is funded by forced loans from the rich, as Florence did:
>   the commune never had the cash.
> - An imported town starts with its granary full and the rich stocked and
>   hoarding (the equilibrium rule): bought from scratch in year 1, the
>   imports replacing them sent ~2,300 fl out of town.
> - Bakers have no customer ties at import, so a household buys from any
>   baker; the shop ties stay for shops and taverns.
>
> Seed 1, 25 years: normal years 0.94-1.07 (12-14 soldi); 3 famines at
> 1.76-2.29 (up to ~30 soldi; 1329: 28-31); 7-19 famine deaths each
> (0.3-0.9%); the granary and hoards empty in each famine and refill;
> homeless 7-77, the lowest of any run; 0-6 hungry households in normal
> years, 18 in a famine. Seeds 2-5, year 1: very poor 337-346 against
> 316-367 without the food chain, homeless 6-54 against 32-118.
>
> **Found on the way, not from this slice:** in every seed the very poor
> rise ~20% in year 1 (283 -> ~340). Likely the class lines: they're cut at
> import from *expected* incomes, which differ from what people then earn.

## 7. Slice 2 build plan: the crafts (2026-10-01) — for comments

Today the rest of a household's basket (40% once grain and rent are out)
is money paid to a seller picked at random, so a tailor earns from a
household that buys no clothes. This slice turns the crafts into goods.

**A. What households buy** (C: the book has no shares beyond grain and
rent; they come from typical pre-industrial budgets, to check against de
la Roncière). Of the whole basket:

| Share | Goods | From |
|---|---|---|
| 45% | bread | slice 1 |
| 15% | lodging | rent (slice 5 of the economy) |
| 20% | wine, oil, meat, cheese, salt | taverns and shops, as today |
| 6% | clothing | tailors |
| 2% | shoes | shoemakers |
| 7% | firewood, candles | shops, as today |
| 5% | pots, barrels, wooden and iron goods | potters, coopers, carpenters, the blacksmith |

The rich spend most of their extra on clothing, furnishing and imports,
as today.

**B. The chains.**
- **Cloth:** weavers, fullers and dyers in the workshops make cloth from
  raw wool (imported by merchants). Tailors buy it to make clothing.
  Putting-out spinning for merchants stays as it is (export cloth).
- **Leather:** tanners make leather from hides bought from the farmers;
  shoemakers buy the leather.
- **Wood, pottery, iron:** carpenters and coopers buy timber, the
  blacksmith iron (both imported by merchants); the potter digs clay.

**C. Workshops.** Each makes a fixed amount a month per worker (C, set so
that at import the town's workshops make about what it buys:
the equilibrium rule), as far as its inputs allow. It keeps about a
month of output in stock and stops when its store is full. A household
buys from the makers of that good who have stock; if none do, a merchant
imports it at a dearer price (money leaves town); if no merchant, it
goes without.

**D. Surplus.** A workshop whose store is full sells the extra to the
merchants, who export it at the outside price (the town's cloth above
all). Without this, a town that makes more cloth than it wears would see
its weavers' takings collapse.

**E. Prices** stay fixed in this slice (C, set from the budget shares and
the workshops' output), and start moving in slice 3.

**What it brings:** a dead shoemaker means shoes are imported, dearer,
until someone takes up the trade; tanners need the farmers' hides; the
town's cloth trade shows as weavers selling to tailors and merchants.

**Questions for you:**
1. Are the budget shares in A reasonable, or do you have figures in mind?
2. Should masons belong here (building work for the commune and house
   buyers), or stay as day labour and purchases as today?
3. Should a household that can't find a good go without (no shoes this
   year), or always get it imported, dearer?

> Feedback:

> **Decided (user, 2026-10-01):** the shares in A to start with; masons
> later (with new houses being built); a good no workshop has is imported,
> dearer (the household goes without only if there's no merchant).

> **Built (2026-10-01), `crafts.py`.** As planned, with three changes the
> checks forced:
> - **Materials on account.** Paying for materials up front from the
>   master's household purse left workshops short (shoes: 92 fl made of
>   ~870 in a year). Workshops take materials on credit, up to two months
>   of them (Florence's merchants advanced wool), and pay from their
>   takings at the month's end. Cloth and leather are made first, then the
>   trades that use them, then the surplus is exported.
> - **Output set from real demand.** Wage-based output left clothing and
>   housewares short (~1,100 fl a year imported). After the first month,
>   each good's workshops make 1.2x what households asked for (clothing
>   1.7x, housewares 1.8x a worker's wage-based output); an imported town
>   starts with a month of stock.
> - **Every workshop works at capacity** and exports its surplus through
>   the merchants: selling only to the town, tanners would have earned a
>   quarter of their wages.
>
> Seed 1, 25 years: very poor 11-14%, rich 10-12%, money flat; craft
> exports 0.8-2k fl a year; finished goods imported ~250 fl in all; the
> tailors outgrow the weavers (4k fl of cloth imported). Masters earn from
> what they sell (carpenters and potters ~200 fl a year, tailors 150-290,
> shoemakers 115-210). Hides from the farmers are unlimited for now.

## 8. Slice 3: prices that move (built 2026-10-01)

Each craft good's price now moves, by at most 10% a month (§3), toward the
level where the workshops' stocks cover a month of demand (C: price ~
(cover) ** -0.3, as grain's). Trade bounds it: never above what merchants
charge to import it (1.15 of normal), never below what they pay to export
it (0.85). Households spend the same money on each good, so a dearer good
means less of it; cloth and leather bought on account cost the tailors and
shoemakers their current price. Bread already moved (slice 1); wine, oil,
meat and firewood from shops stay money only.

Seed 1, 25 years: cloth at or near the import price (the tailors use more
than the weavers make), leather near the export price (an export trade),
clothing, shoes and housewares 0.93 at first, rising to ~1.0 as the town
grows into its workshops. Classes hold (very poor 11-15%, rich 10-12%),
hungry 0-2, homeless 34-70. A coup in year 19 sent an heirless landlord's
22 houses to the commune (households' money -5k, the commune's +).

## 9. Slice 4 build plan: merchants in goods (2026-10-08) — for comments

Today a merchant is a till. Anything the town lacks (grain beyond the
farmers', wool, iron, timber, a missing craft good, the rich's luxuries)
comes from outside the moment someone asks, through a merchant picked at
random who keeps 15%. Nothing limits how much, nothing has to wait, and no
merchant ever runs out of goods or money. Exports are the same: a
workshop's surplus is sold outside at once.

**A. Lines of trade.** Each merchant house trades one line (C): grain;
wool and cloth; iron, timber and hides; luxuries. At import the ~13
merchants are split across lines by what the town imports of each (the
equilibrium rule). A dead merchant's line passes with the house.

**B. Warehouses.** Imports are bought from a merchant's stock, no longer
straight from outside. The merchant's grain counts in the town's stocks
that set grain's price.

**C. Orders take time.** Each month a merchant orders what their line has
been selling (C: enough for about two months), paid up front from the
house's cash. Grain comes up the river in about a month; wool, iron and
timber in about two; luxuries in about three (C). After a sudden jump in
demand (a bad harvest, a dead baker, a burnt workshop), prices climb until
the cargo lands.

**D. Money limits.** A merchant orders only what the house can pay for,
keeping a cushion. A town whose grain merchants are poor can't import
its way out of a famine; the granary and the rich's hoards matter more.

**E. Exports.** Merchants buy a workshop's surplus only with cash they
have. They are paid when the cargo sells outside, about two months later.
Putting-out cloth stays as it is.

**F. What it brings:** real shortages and their timing, merchants who
grow rich in a dear year, and a town that depends on a handful of houses
(a dead or ruined grain merchant shows up in the bread price).

**Checks:** normal years unchanged within noise (no drift); in a famine
grain rises above the import price for a month or two, then eases as
cargo lands; money conserved; merchants stay in their class band; no
line runs empty in quiet years. Speed: ~13 merchants a month, negligible.

**Questions for you:**
1. When every merchant in a line is out of stock: does the town go
   without until the cargo lands (real shortages), or can it still buy
   from outside at a steep price?
2. One line per merchant house, or every merchant trades everything?
3. Lost cargoes (shipwreck, bandits, a correspondent who goes bankrupt)
   that can ruin a merchant house: now, or later?
4. In a famine, do grain merchants sell at the market price, or hold
   back for a higher one like the rich hoarders (and draw the same anger)?

> Feedback:

> **Decided (user, 2026-10-08):** a line out of stock goes without until
> the cargo lands; one line per merchant house; lost cargoes (that can
> ruin a house) in this slice; grain merchants sell at the market price
> in a famine, without holding back.

> **Built (2026-10-08), `merchants.py`.** As planned, with these choices
> the checks forced:
> - **Takings pay for the next cargo.** The 12-13 merchant houses hold only
>   40-220 fl in cash (households spend down what's above their cushion),
>   against an import bill of ~1,500 fl a month. So each merchant orders at
>   the month's end from that month's takings, keeping two months of the
>   household's needs; the cost of what they sold is set aside so the
>   household doesn't spend it first. An imported town starts with its
>   warehouses holding two months of sales and a cargo afloat for every
>   month at sea (the equilibrium rule).
> - **The lines** are split by what each sold in the first month: 3 grain,
>   1 wool and cloth, 1 iron, timber and hides, 7-8 luxuries.
> - **Merchants' grain doesn't set the price.** Counted in the town's
>   stocks, it held a famine's price at 1.1 against an outside price of 2.
>   Merchants sell at what grain costs to replace (the market price, or the
>   import price if higher); their stock only decides whether imports cap
>   the price. With no grain in any warehouse the cap lifts, up to 3x.
> - **Losses:** 2% of cargoes are lost (river trade, below the 3-6% of sea
>   voyages); a correspondent fails for 1% of merchants a year, taking all
>   their cargo afloat. A loss that leaves a house under half of what it
>   trades ruins it; the head looks for other work, and the head of the
>   richest house that could trade takes up the line and the warehouse.
>   About one house in 12 years (at 60%: 1-3 in 8 years; at 40%: none in 75).
>
> Three seeds, 25 years: no famine-time shortage of grain (the warehouses
> hold ~7,000 staia, two months, and grain lands in one); in a forced famine
> the price climbs to the import cap (2.1-2.4x) as before, and stays there.
> Shortages in quiet years are tiny (at most 350 fl of cloth in 25 years).
> Lost cargoes cost the town ~450 fl a year (~2% of imports), which slows the
> old upward drift of town cash. At year 25 the very poor average 317
> (before this slice 355) and the rich 258 (230; one seed lower, two higher:
> the rich were already rising from ~155 before this slice).
