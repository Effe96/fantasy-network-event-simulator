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
