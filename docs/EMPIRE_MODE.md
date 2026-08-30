# NEXUS TECH Empire Mode

Empire Mode is the optional long-run preview introduced in version 0.329.0. It
extends the existing company simulation instead of replacing Standard Mode.

## Start A Run

Choose `Founder Empire` from the New Game scenario list, or run:

```bash
.venv313/bin/nexus-tech play-2d --scenario empire_founder_journey
```

The difficulty and campaign goal remain selectable. The campaign goal also
defines the Scale Thesis for that run.

## Five Eras

| Era | Turns | Objective |
| --- | --- | --- |
| Foundation | 1-5 | Build one reliable product loop and protect runway |
| Growth | 6-10 | Open a second growth engine without abandoning the core |
| Scale | 11-16 | Build repeatable operations and leadership depth |
| Expansion | 17-24 | Control multiple territories under adaptive rival pressure |
| Legacy | 25+ | Sustain the selected thesis and qualify for victory |

Empire victory cannot trigger before Turn 25. Failure conditions remain active,
so extra turns are not guaranteed survival.

## Scale Theses

- `profit_machine` becomes **Operating Flywheel**. Positive cash flow gradually
  repairs the highest product debt, support backlog, and profitability trust.
- `portfolio_empire` becomes **Platform Ecosystem**. Two active products across
  two segments gradually improve the weakest product-market fit.
- `category_leader` becomes **Category Standard**. Average active-product quality
  of at least 65 converts into reputation.

These are small compounding effects, not additional actions or currencies. The
normal product, finance, team, roadmap, customer, and partner decisions remain
the way the player creates the required conditions.

## Territory Map

Open **Report** during an Empire run to see **Empire Plan / Market Map**. The
four territories are the existing `indie`, `startup`, `SMB`, and `enterprise`
segments. Their control scores are reconstructed from products, users, active
accounts, active partners, and direct rival pressure.

Territories progress through `untapped`, `under pressure`, `contested`,
`foothold`, and `leading`. A foothold or leading territory counts as controlled.

## Rival And Crisis Pressure

From the later Growth era onward, rivals periodically counter the strongest
territory. The response depends on the Scale Thesis and uses the existing rival
move system. One material cross-system crisis can also dominate the Empire Plan:

- Platform integrity from debt, defects, or support backlog
- Market backlash from rival momentum, account risk, or low reputation
- Leadership bottleneck from weak leadership depth or exhausted teams

The Report shows the current crisis, next milestone, and strategic priority.

## Saves And Compatibility

Empire Mode adds no database columns and keeps persistence schema 28. The save
stores the same company, product, employee, finance, market, rival, customer,
partner, roadmap, event, and history records as Standard Mode. Era, thesis,
territory, and crisis views are derived again after load from that source state.

Standard scenarios do not receive Empire effects or the Turn 25 victory gate.

## Validation Status

Automated regression coverage protects scenario creation, era boundaries,
thesis mapping, territory derivation, Standard Mode isolation, rival response,
victory gating, Report/catalog presentation, turn feedback, and save round trips.
This does not replace human evidence. No human has yet validated the full Empire
route through Turn 25, and the project remains a Stable Alpha.
