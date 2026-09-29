# Parameter Book for Simulating a Medieval Italian City's Market

*Calibration base: Florence and Tuscany, c. 1330–1430. This is where the medieval evidence is densest in all of Europe. A machine-readable version of the key numbers is in `medieval_city_sim_parameters.json`.*

## How to read this file

Every number carries a confidence grade:

| Grade | Meaning |
|---|---|
| **A** | Archival or peer-reviewed figure, quoted from the study |
| **B** | Figure reported by a reputable secondary source, or a medieval chronicler (Villani) as analysed by historians |
| **C** | **My own derivation or assumption.** Arithmetic on A/B numbers, or a modelling choice. Change these freely. |
| ⚠️ | Weak source (blog, popular site). Use only as a placeholder until you replace it. |

**Two regimes worth simulating separately:**
- **Pre-plague, c. 1330.** Many people, low real wages, high inequality.
- **Post-plague, c. 1350–1430.** A third to half of the people gone, wages up, inequality down for about a century.

Most figures below are tagged with one of these two.

---

## 1. Money and units

### Money of account
The city kept its books in a "ghost" currency (A, Caferro):
- **1 lira = 20 soldi = 240 denari**
- The gold florin floated against this unit of account, which was based on silver coin.

| Florin exchange rate | Year | Grade |
|---|---|---|
| ~60 soldi | early 1330s | B |
| 66 soldi | c. 1328–30 | A (Nanni, from Pinto) |
| 64 soldi | 1349–50 | A (city budgets, Caferro) |

- A florin weighed about **3.5 g of gold**, stable from 1252 to 1533 (B).
- **Two-currency rule for the simulation:**
  - Wages and food were quoted in lire/soldi.
  - Cloth, dowries, property and large contracts were quoted in florins.
  - Some public salaries were paid in gold, others in silver (A, Caferro).
  - The florin gained value against the soldo over time, so wage earners paid in silver lost ground on anything priced in gold.

### Physical units

| Unit | Conversion | Grade |
|---|---|---|
| 1 *moggio* (dry measure) | 24 *staia* | A (Ito: 89 moggia = 2,136 staia) |
| 1 *staio* of wheat | ~18 kg | B |
| 1 *moggio* of wheat | ~426–432 kg (~584 L) | B/C |
| 1 Neapolitan *salma* of grain | 10.5 Florentine *staia* | A (Pegolotti, via Ito/Pinto) |
| 1 Florentine *libbra* (pound) | 12 *once* | B |

---

## 2. Population and households

### Florence (big-city reference)

| Item | Value | Grade |
|---|---|---|
| Men of fighting age (15–70), c. 1338 | ~25,000 | B (Villani) |
| City households in the 1427 tax census | **9,780** | A |
| Average household size, 1427 | **~3.8–4.1 persons** | C (≈37–40k people ÷ 9,780) |
| Age at first marriage, 1427 | men ~27, women ~18 | A (Barbiera & Dalla-Zuanna) |
| Life expectancy at birth; birth rate | e0 ~20 years; ~50‰ | A (same) |

### Prato (medium-city template)

| Year | Population | Grade |
|---|---|---|
| 1339 | 10,559 | A (Alfani & Ammannati) |
| 1372 | 6,504 | A |
| 1428 | 3,533 | A |

The three dates give you a pre-plague state, a plague-shock state and a trough.

### Default template (C)
- **Pre-plague:** 10,000 people ÷ ~4 per household ≈ **2,500 households**.
- **Post-plague:** 4,000 people ≈ **1,000 households**.

---

## 3. Wealth distribution — "how much money people had"

### 3a. Wealth per person, by type of place (1427 tax census)

| Place type | Average wealth per person | Grade |
|---|---|---|
| Florence (capital) | **273 fl** | A (Herlihy, via Alfani & Ammannati) |
| Medium cities (Arezzo, Pistoia, Pisa) | **70–85 fl** | A |
| Small cities (Prato, Cortona, Volterra) | **~45 fl** | A |
| Villages | 32 fl | A |
| Sparsely settled areas | 14 fl | A |

### 3b. Deciles for a medium city: Prato

Share of total wealth held by each tenth of **taxpayers who owned something**. The propertyless are excluded (A, Alfani & Ammannati, Table 4).

| Year (source date) | D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | D9 | D10 | Top 5% | Top 1% |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **1300** (1325) | 1.58 | 1.82 | 1.98 | 2.14 | 2.27 | 2.49 | 5.93 | 6.69 | 9.39 | **65.72** | 55.26 | **29.18** |
| **1350** (1372) | 2.26 | 2.39 | 2.62 | 2.76 | 3.06 | 3.57 | 6.44 | 10.22 | 18.58 | **48.12** | 31.99 | 10.81 |
| **1450** (1428) | 0.61 | 0.61 | 0.97 | 1.81 | 2.71 | 3.82 | 7.03 | 11.46 | 17.39 | **53.59** | 35.96 | 13.04 |

**Gini index, Prato, propertyless excluded (A):**

| Year | Gini |
|---|---|
| 1325 | 0.703 |
| 1428 | 0.683 |
| 1487 | 0.624 |

**Gini with the propertyless included, Prato 1450: 0.740 (A).**

**Other benchmarks (A):**
- Florence 1427: Gini **0.788**.
- Six subject cities combined: 0.747.
- Pistoia city 1427: 0.713.
- Rural villages c. 1450: 0.43–0.52.

### 3c. Share of households with no taxable property

| Place | Share with nothing | Grade |
|---|---|---|
| Prato 1372 | **37.6%** | A |
| Prato 1428 | 17.9% (after allowances) | A |
| Prato 1487 | 32.2% (after allowances) | A |
| Florence 1427, after the 200-florin-per-person allowance | 28.8–31% | A |
| Florence 1427, truly owning nothing | **14%** | A |
| Florence 1427, households with no assessable wealth | 14.6% (1,431 of 9,780) | A |

### 3d. The very top — Florence 1427
- The **137 richest households (1.4%) held 29.8% of assessed wealth**, 3,000,672 fl in total (A).
- Implied totals (C):
  - All city wealth ≈ 10.1 M fl.
  - Average ≈ 1,030 fl per household, ≈ 260 fl per person. This agrees with Herlihy's 273 fl ✔︎.
  - Top-137 average ≈ **21,900 fl per household**.
- The poorest 50% held **2.68%** of wealth in Florence, against about 6% in the village of Impruneta (A).
- Florentine citizens owned **99.75% of the public debt** and **78% of all movable wealth** in the state (A).

### 3e. Converting wealth to annual income
The 1427 tax census valued property by **capitalising its declared income at 7%**. The owner's own house was excluded (A).

**Simulation rule (C):** annual property income ≈ **0.07 × taxable wealth**.

Worked examples:
- A top-137 Florentine household: ≈ 1,530 fl/year from property alone.
- An average Prato person with 45 fl of wealth: ≈ 3 fl/year of property income.
- Add labour income on top of this for everyone below the top.

---

## 4. Wages and salaries — "who earned what"

### 4a. Daily wages, Florence building trades (soldi per day)

| Worker | Before plague (1349) | After (1350) | Grade |
|---|---|---|---|
| Unskilled labourer | **8.4** | **10.0** (+19%) | A (Goldthwaite, via Caferro) |
| Master mason | **13.4** | **16.8** (+25%) | A (same) |
| Masons at a war-supply site (Scarperia) | — | 18 | A (Caferro) |

- In the three years after the plague, de la Roncière finds **+160% for masons** and **+354% for unskilled labourers** (A).
- **Skill premium** (skilled ÷ unskilled wage): about 100% before the plague, falling to a stable 60–80% afterwards (A, JEH 2019 online appendix).
- Florence passed **no wage-cap law** after the plague, unlike England's Statute of Labourers (A, Caferro).
- ⚠️ Popular summaries give 6–8 soldi/day for labourers in the early 1300s and 12–14 soldi by 1400. Treat these as placeholders.

### 4b. Daily rates for temporary public work, 1350 (soldi per day, A, Caferro)

| Role | Rate |
|---|---|
| Paymaster | 90 |
| Supply officer | 70 |
| Troop inspector | 40 |
| Blacksmith | 25–50 |
| Army doctor | 30 |
| Town crier riding with the army | 20 |
| Civic musician with the army | 4 (plus clothing twice a year) |

### 4c. Monthly salaries, 1349 (soldi per month; 1 fl = 64 s; A, Caferro)

| Role | 1349 | 1350 |
|---|---|---|
| Podestà (chief magistrate; the salary also covers his 38-man staff) | 26,667 | 26,667 |
| Executor of Justice | 6,667 | 6,667 |
| German cavalry captain | 1,920 | 1,920 |
| Italian cavalry captain | 800–1,000 | same |
| Chancellor | 533 | 533 |
| German mercenary cavalryman | 522 | 522 |
| Notary of the Priors | 400 | 400 |
| Italian cavalryman | 400 | 400 |
| Ligurian crossbowman | 207 | 256 |
| Public doctor | 200 | 200 |
| Treasury accountant | 200 | 200 |
| Local crossbowman | 138 | 180 |
| Town crier | 121 | 121 |
| Shield-bearer (lowest soldier) | 120 | 140–170 |
| Domestic servant, bell-ringer or cook of the Signoria | **80** | 80 |
| Judge | 60 | 60 |

**Modelling warning (A, Caferro): a person's income ≠ the wage of their stated job.**
- A bell-ringer on 4 lire a month earned **180 lire** from a single 60-day embassy.
- A notary on 10 lire a month earned 35.5 lire in 12 days of side jobs.
- Suggested rule: give households a **secondary-income draw**.

### 4d. Annual earnings

The standard convention is **250 working days per year** (Allen method; C). It allows for about 115 Sundays and feast days plus seasonal gaps.

| Worker, 1349–50 | Annual earnings |
|---|---|
| Unskilled | 8.4–10 s × 250 = 2,100–2,500 s ≈ **33–39 fl** |
| Master mason | 13.4–16.8 s × 250 ≈ **52–66 fl** |
| Servant | 80 s × 12 = 960 s ≈ **15 fl** (probably plus board, which is unknown) |

⚠️ Popular sources say the cathedral architect earned 100 fl/year in the late 1200s.

### 4e. Workforce structure
- **Wool industry, 1338:** 200 firms, ~30,000 workers, 70–80k cloths worth 1.2 M fl (B, Villani via Munro).
  - About **150 workers per firm** (C).
  - About **375 bolts per firm** per year (B, Munro).
  - About **6,000 fl of output per firm** (C).
  - One-third of the city depended on wool directly or indirectly (B).
- **Artisans with guild wage data** were only **4–8% of the urban population** (A, Malanima via Caferro). Building wages are a proxy, not the whole labour market.

---

## 5. Consumption per person — "who was buying what, how much"

### 5a. Annual intake of Florence (~90–110k people)

| Good | City total | Per person (C) | Grade |
|---|---|---|---|
| Grain | **230 *moggia* per day** (1339) ≈ 98 t/day | **~0.9 kg/day ≈ 330 kg/year** | B (1339 city description, via Salvemini); per-person figure C |
| Wine | ~5.9 M "gallons"/year, +1.1 M in good years | **~0.5–0.6 L/day** if US gallons are meant | B (Villani, English translation); unit C ⚠️ |
| Oxen and calves | 4,000/year | see meat below | B (Villani) |
| Sheep | 60,000/year | | B |
| Goats | 20,000/year | | B |
| Pigs | 30,000/year | | B |
| Melons (July only) | 4,000 cartloads | | B |

**Meat (C, carcass weights are my assumption):** ox 150 kg, sheep 15, goat 12, pig 50 → about 3.2 M kg/year → **~30 kg per person per year (~90 g/day)**. Also allow for fish, poultry and cheese, which Villani does not count.

### 5b. Daily demand for a 10,000-person city (C, from 5a)

| Good | Per day | Per year |
|---|---|---|
| Grain | ~9 t ≈ **500 *staia*** | ~3,300 t |
| Wine | ~5,500 L | — |
| Meat | ~900 kg | — |

**Grain cost at a normal price of 13 s/staio:**
- ~6,500 soldi/day ≈ **325 lire/day ≈ 108 fl/day**
- ≈ **40,000 fl/year**, the single largest cash flow in the city.

### 5c. Example budget: unskilled household of 4, around 1330–50 (C)

| Line | Value |
|---|---|
| Income | 8.4 s × 250 days ≈ 2,100 s/year |
| Grain need | 4 × 0.9 kg × 365 ≈ 1,314 kg ≈ 73 staia |
| Grain cost at 13 s/staio | ≈ 950 s ≈ **45% of income** |
| Grain cost at 26 s (bad year) | ≈ 90% of income |
| Grain cost at 31 s (1329 famine) | more than the whole income, so the household needs charity or subsidised bread |

**Validation target:** Allen's "welfare ratio" = annual wage ÷ cost of a subsistence basket for a family of four (~1,940–2,100 kcal/person/day, plus a little cloth, fuel and light).
- A ratio of 1 means bare subsistence.
- If your simulation gives an unskilled pre-plague ratio far from ~1, or a post-1400 ratio far from ~1.5–2, recheck your prices.

---

## 6. Prices

| Item | Price | Year | Grade |
|---|---|---|---|
| Wheat, normal year | **~13 s/staio** | 1331 | B (American Numismatic Society) |
| Wheat, range across early-1330s harvests | 10–26 s/staio | 1330s | B |
| Wheat, public famine price | 28 s set, 31 s net per staio | 1329 | A (Lenzi's grain-market ledger, via Ito) |
| Cheaper grains (barley, millet, sorghum) | 6–20 s/staio | 1329 | A (Ito) |
| Wheat in the 1347 dearth | doubled by May | 1347 | B |
| Florentine wool cloth, average | 7.5–8.6 fl/bolt | 1308 | B (Hoshino, via Rinucci ledger study) |
| Florentine wool cloth, average | **15–17 fl/bolt** (~16) | 1338 | B (Villani / Munro) |
| Florentine woollens sold in Pisa, average | 55.9 fl | late 1300s | A (Munro) |
| Florentine woollens sold in Spain by Datini, average | **64.43 fl** (2,652 pieces) | 1390s | A (Munro) |
| Shipping cloth Bruges→Barcelona by sea | 15% of value | 1398 | A (Munro) |
| Same route overland | 22% of value | 1398 | A |
| Crossbow bolts | 5,000 bolts = one German cavalryman's pay | May 1350 | A (Caferro) |

**Price shocks to model:**
- Grain prices swing about 2.5× between good and bad harvests.
- In a famine the commune intervenes. Florence in 1329 spent **60,000 fl** on imports and requisitioned ovens (B).
- In the 1346–47 famine Florence **fed about 94,000 people**, roughly four-fifths of the city (B).

---

## 7. What limited the wealth of the rich

These mechanisms are documented. Each can become a model rule.

| Mechanism | Evidence | Suggested rule (C) |
|---|---|---|
| **Low return on land and property** | Property was capitalised at 7% (A) | Land yields ~5–7%/year; trade can yield more but with risk of loss |
| **Equal division of estates among heirs** | Estates were split evenly among heirs, which broke up fortunes after 1348 (A, Alfani & Ammannati) | Divide an estate by the number of surviving sons at each death |
| **Dowries** | 13th century: **100 lire** was a normal dowry, 200–300 "excessive" (B, Villani). 1425–42: the public dowry fund paid 1,814 brides an average of **417 fl** (A, Kirshner & Molho). A 60-fl deposit could mature into up to 500 fl. Dowries inflated after the plague. | Each daughter's marriage moves ~5–15% of her family's wealth to another family |
| **Forced loans and direct tax** | The city was funded by indirect taxes plus **forced loans (*prestanze*)**; from 1315 Florentine citizens were exempt from direct tax (A). In 1427 the tax census allowed deductions of 200 fl per family member (A). | Wealthy households get irregular levies in war years |
| **Bank failure and counterparty risk** | The Bardi lent ~900,000 fl and the Peruzzi ~600,000 fl to Edward III of England; neither was repaid and both firms collapsed in the 1340s (B) | Large merchant firms have a small annual chance of a total wipe-out |
| **Political confiscation and exile** | The Ubaldini were outlawed in 1349 and their goods made seizable (A). Exiled Ghibelline houses had their palaces demolished (B, Villani). | Faction membership carries a risk of confiscation after regime changes |
| **Status spending** | Villani (c. 1338) says that within about 6 miles of the city there were twice as many great country mansions as in Florence itself, and that citizens were thought "mad" for the expense (B). A magistrate checked women's ornaments (sumptuary law). | Top deciles spend a fixed share of income on housing and display; sumptuary law caps visible luxury |
| **Plague** | Killed heirs and partners. It also raised wages and lowered inequality for about a century (A). | Mortality shocks reset both capital and labour prices |

**The ceiling to target (C):**
- Top Florentine households around 1427 held ~20,000 fl.
- The richest single households held a few tens of thousands of florins. For example, the Capponi brothers declared **8,664 fl** of gross assets in one district (A).
- An unskilled labourer earned ~35–50 fl/year.
- The **property income of a top household is roughly 30–40× a labourer's wage**. This is a useful sanity check on your simulated distribution.

---

## 8. Public finance (scale checks)

| Item | Value | Grade |
|---|---|---|
| Revenue collected under the Duke of Athens in 10½ months (from gabelle, direct tax, fines) | ~400,000 fl | B (Villani, Nuova Cronica XIII) |
| Spending in one year of the Duke's rule | >450,000 fl | B (Villani XI) |
| Repairs after the 1333 flood | >150,000 fl | B (Villani XII.1) |
| New Ponte alla Carraia bridge | >25,000 fl | B (Villani XII.12) |
| Security chief's salary (1335), for 50 horse and 100 foot | 10,000 fl/year | B (Villani XII.39) |
| Palace bought from a bankrupt firm's creditors | 7,000 fl | B (same) |
| Wine gate toll, 1504 | 12 s 6 d per *barile* | B |

**Rule of thumb (C):** Florence raised on the order of **3–5 fl per person per year**, mostly from indirect taxes on goods entering the gates and on salt, wine and contracts. For a medium city, scale by population and by its lower wealth per person.

---

## 9. Gaps: what I could NOT verify

Do not invent these; they are the next things to extract.

| Missing parameter | Where to get it |
|---|---|
| Wine, meat, oil, cheese, salt and bread retail prices by year | de la Roncière, *Prix et salaires à Florence au XIVe siècle* (1982); Tognetti, "Prezzi e salari nella Firenze tardomedievale" (*Archivio Storico Italiano*, 1995); Malanima's online price and wage database (paolomalanima.it) |
| House rents | Goldthwaite, *The Economy of Renaissance Florence* (2009), ch. 5 and the florin appendix; Goldthwaite, *The Building of Renaissance Florence* (1980) |
| Florin–soldo exchange rate after 1350 | Goldthwaite 2009, appendix "Changing values of the florin" |
| Interest rates (pawnbrokers, commercial credit, public debt yield) | Goldthwaite 2009, ch. 6; Molho, *Florentine Public Finances* (1971) |
| Occupational census of a medium town | Herlihy, *Medieval and Renaissance Pistoia* (1967), ch. 7; the Online Catasto (Brown University) includes occupation codes for Florence 1427 |
| Budget shares (food, rent, clothing) | de la Roncière 1982, pp. 381–96; Goldthwaite 1980, pp. 342–50 |

**Direct data source:** the **Online Catasto of 1427** (Brown University) has about 10,000 Florentine households with wealth, occupation, household size and address. You could sample your simulated wealthy population directly from it.

---

## Sources

- Caferro, *Florentine Wages at the Time of the Black Death* — [Yale PDF](https://economics.yale.edu/sites/default/files/florence_wages-caferro.pdf)
- Alfani & Ammannati 2017, *Long-term trends in economic inequality: the Florentine state* — [PDF](http://piketty.pse.ens.fr/files/AlfaniAmmannati2017EHR.pdf)
- Barbiera & Dalla-Zuanna 2024 — [Wiley](https://onlinelibrary.wiley.com/doi/full/10.1111/padr.12611)
- Florence Catasto 1427 — [World History Commons](https://worldhistorycommons.org/florence-catasto-1427) · [Online Catasto (Brown)](https://cds.lib.brown.edu/cds-project/florentine-renaissance-resources-online-catasto-1427-database)
- Villani (English excerpts) — [Hanover College](https://history.hanover.edu/courses/excerpts/344villa.html) · Italian text: [Wikisource, Libro XII](https://it.wikisource.org/wiki/Nuova_Cronica/Libro_dodecimo), [Libro XIII](https://it.wikisource.org/wiki/Nuova_Cronica/Libro_tredecimo)
- Grain per day (1339) — [Italian Tales, citing Salvemini](https://www.italiantales.info/florence-medieval-political-evolution-magnati-popolani-1289-1347/)
- Ito 2014, *Orsanmichele: The Florentine Grain Market* — [Academia](https://www.academia.edu/30638502/)
- Wheat price 1331 and florin value — [American Numismatic Society](https://numismatics.org/pocketchange/florin/)
- Munro, Florentine cloth industry — [working paper](https://www.economics.utoronto.ca/public/workingPapers/tecipa-487.pdf) · [output series](https://www.economics.utoronto.ca/munro5/FlorentineClothIndustryCopenhagen2012B.pdf)
- Rinucci ledger / Villani cloth figures — [Academia](https://www.academia.edu/103223242/)
- Kirshner & Molho, *The Dowry Fund and the Marriage Market* — [Academia](https://www.academia.edu/81494869/)
- Nanni, *Facing the Crisis in Medieval Florence* — [ResearchGate](https://www.researchgate.net/publication/337950282)
- Skill-premium appendix (JEH 2019) — [Cambridge](https://static.cambridge.org/content/id/urn:cambridge.org:id:article:S0022050719000354/resource/name/S0022050719000354sup001.pdf)
- Allen welfare-ratio method — [Allen 2001](http://piketty.pse.ens.fr/files/Allen2001.pdf)
- Bardi and Peruzzi loans — [Wikipedia](https://en.wikipedia.org/wiki/Bardi_family) · 1347 famine — [Wikipedia](https://en.wikipedia.org/wiki/Archdiocese_of_Florence)
- Capponi assets — [Addressing Wealth in Renaissance Florence](https://www.academia.edu/6434025/)
- ⚠️ Placeholder sources — [From Poverty to Progress (Substack)](https://frompovertytoprogress.substack.com/p/northern-italy-and-the-birth-of-progress) · [lenpenzo.com](https://lenpenzo.com/blog/id47735-historical-gold-and-silver-benchmarks-for-job-wages-and-commodity-prices-2.html)
