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
