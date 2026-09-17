# Tennis Launch Calendar 2026

Which tennis tournaments to list, in what order, every week from 21 September to
31 December 2026 — with the evidence behind every row and an honest label on the
rows that have none. Sibling project to
[cricket-calendar](https://github.com/vonapets/cricket-calendar); same idea, a
sport with 37× the traded volume and a much harder scheduling problem.

Open `calendar.html` from disk. One self-contained file, no server, no network.

## The plan in one paragraph

Run **one Challenger every week with no gaps** in slot 1. The sub-tour circuit is
roughly half of all tennis volume on *both* Polymarket and Kalshi, and it runs
Monday–Sunday every week of the year — no December shutdown, no Asian trough, no
week where there is nothing to list. Open **slot 2 only for a tour event that
clears the bar**: Shanghai from 5 Oct, Basel from 26 Oct, then the two that
actually matter — **Paris Masters (2 Nov)** and the **ATP Finals (15 Nov)**.

| Week | Slot 1 | Slot 2 |
|---|---|---|
| Sep 21 | San Diego C75 | — |
| Sep 28 | Columbus C75 | — |
| Oct 5 | Villena C100 | **Shanghai Masters** |
| Oct 12 | Olbia C125 | Shanghai (week 2) |
| Oct 19 | Fort Worth C75 | — |
| Oct 26 | Sioux Falls C100 | **Basel** |
| **Nov 2** | Charlottesville C75 | **★★ Paris Masters** |
| Nov 9 | Knoxville C75 | WTA Finals |
| **Nov 16** | Drummondville C75 | **★★ ATP Finals** |
| Nov 23 | Florianópolis C75 | — (Davis Cup skipped) |
| Nov 30 | Bogotá C75 | — |
| Dec 7 | Rio C50 | — |
| Dec 14 | Limoges WTA 125 | — |

## Check these two before listing anything in slot 1

1. **Can the listing layer carry ATP Challenger and ITF events?** Many sports
   integrations key off per-tour identifiers that cover only ATP and WTA main
   tour. Every slot-1 pick here is a Challenger.
2. **Is there a settlement feed for Challenger and ITF results?** Tour-level
   result feeds are well covered; sub-tour is thinner, and resolution risk is
   the main operational cost of this plan.

## What the two venues say

Kalshi's per-match tennis book, by tier:

| Tier | Volume | Share | Tournaments | Median |
|---|---|---|---|---|
| Tour-level | $4.78bn | 41.1% | 24 | $102.3M |
| **ITF** | **$3.93bn** | **33.8%** | 237 | $10.9M |
| **ATP Challenger** | **$2.44bn** | **21.0%** | 60 | $38.3M |
| **WTA 125** | **$481M** | **4.1%** | 17 | $28.2M |

Tour-level is a minority of the book, and sub-tour does not sit underneath it —
it interleaves. **M15 Bali, a $15,000 ITF event, is Kalshi's 7th biggest tennis
tournament at $197.8M**, ahead of ATP Washington, Winston-Salem and Los Cabos.
ATP Challenger Lincoln (NE) at $106.7M outranks ATP Estoril.

Polymarket agrees independently: non-tour-level is 27.8% of its tennis volume,
and that volume is real — on settled events only 1.9% of Challenger volume
arrives in the 24 hours after resolution, the same share as tour-level.

**Units caution.** Kalshi `volume_fp` is contracts at $1 notional, summed across
both per-player books. Polymarket `volume` is dollar trade value on the single
moneyline market. Cross-venue absolute levels are **not** comparable; rankings
within a venue are.

## The one event to get right

**ATP Finals, Turin, 15–22 November.** 2025: **$18.08M across 18 matches, median
$993,686 per match, 100% traded** — the highest per-match median anywhere in the
dataset, and only 18 markets to run. If you list one tour event all year, that is
the one.

Paris Masters (2–8 Nov, moved from Bercy to Nanterre) is second at $17.45M/57.

## How a row is sized

Two estimators, both shown, because they disagree and the disagreement *is* the
uncertainty:

- **Own history** — the event's own 2025 volume × platform growth.
- **Tier benchmark** — the class-A benchmark for its tier × a geography factor.

Where an event has its own history, trust that. The benchmarks are built from
Rome, Cincinnati, Canada and Madrid; Shanghai has never traded like those.

**Growth factor: 3–8×, and the anchor is unreliable.** The US Open 2025→2026 pair
gives 2.8× on raw per-match but 8.1× depth-matched, because its listing went from
170 to 532 matches. An earlier 2.1–3.4× estimate was withdrawn: it rested on a
Guangzhou pair that compared the **WTA 250** against the **men's Challenger** of
the same city.

### Evidence class

| | |
|---|---|
| `[A]` | current platform, ≥ Apr 2026 |
| `[B]` | Jan–Mar 2026, platform 1.3–3.1× smaller |
| `[C]` | 2025 only, platform 3–8× smaller — rank order beats level |
| `[D]` | **listed and dead** — the strongest negative signal there is |
| `[E]` | never listed on either venue |

Confidence is `measured` (own settled history), `range` (tier and region only) or
`none` (never listed — the number is a prior, not a measurement). **Every slot-1
Challenger pick is `[E] none`.** None of those specific events has ever traded
anywhere. The only backing is that North American Challengers median **$83.9M** on
Kalshi against **$35.2M** elsewhere — and that cohort is confounded with Kalshi's
11 July product launch, so it is a tiebreaker, not a law.

## How it works

```
data/schedule.json   the launch calendar   — hand-maintained (see below)
data/context.json    venue volumes, benchmarks, caveats
refresh.py           re-pull volumes from Kalshi and Polymarket
build.py             schedule + context + template.html -> calendar.html
```

```bash
python3 refresh.py     # optional: update the volume figures
python3 build.py       # rebuild the page
open calendar.html
```

Stdlib only, no dependencies.

### Why the calendar is hand-maintained

cricket-calendar pulls fixtures from ESPN because ESPN publishes them. **Nothing
publishes ATP Challenger or ITF draws in a machine-readable feed.** This calendar
was parsed once from the 2026 ATP Challenger Tour and 2026 WTA 125 calendars
(which cite the official ATP PDF) and cross-checked against `api.wtatennis.com`
for tour level. `refresh.py` updates **volumes only** — it will never discover a
new tournament. Do not expect the page to self-update.

`atptour.com` is Cloudflare-blocked to scripted requests, including its own
calendar PDF. ESPN is not usable either: its dates run 2–7 days wide because they
include qualifying (Wimbledon as 22 Jun–13 Jul against the official 29 Jun–12 Jul),
it carries 60 ATP events against the official 65, and its WTA feed mixes WTA 125
and ITF in with tour level.

## Known corrections

Three tournaments recommended in earlier drafts **do not exist in 2026**: Athens
(Hellenic Championship), Metz (Open de Moselle) and Lyon — all three have zero
mentions on the official 2026 ATP calendar. Newport is also gone, and Antwerp
became the European Open in Brussels.

Nine WTA tier assignments and one ATP were wrong and have been corrected: Doha and
Dubai are WTA 1000s; Linz, Strasbourg, Bad Homburg and Monterrey are WTA 500s;
Ostrava is a 250; Munich is an ATP 500.

An earlier claim that Kalshi lists no Challenger or ITF events was false — it came
from an incomplete series pull and is corrected above.

## Sources

Polymarket Gamma API · Kalshi trade API (`api.elections.kalshi.com`) ·
`api.wtatennis.com` · 2026 ATP Challenger Tour and 2026 WTA 125 calendars.
