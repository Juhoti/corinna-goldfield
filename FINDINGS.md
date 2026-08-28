# Corinna Goldfield — Research Findings

*Analysis date: 28 August 2026. Tenure changes daily — re-run the workflow
before relying on any access statement. Positions ±100–200 m unless marked
surveyed. A snapshot of every dataset behind these findings is committed
under [`data/`](data/).*

This document summarises what the toolkit found when the 1880s record of the
Corinna–Pieman goldfield (western Tasmania) was cross-examined against the
live government layers: MRT tenements, MRT Mineral Occurrences, LIST 1:25k
geology, the Tasmanian Reserve Estate, and LIST hydrography.

## 1. The field is almost entirely under tenement — but not quite

Two Georgina Resources exploration licences (EL2/2018 to Aug 2027, EL25/2020
to Dec 2026) blanket most of the historic workings; Grange Resources holds the
north-east (EL30/2003, lease 2M/2001 at Golden Ridge, to 2030–31); a silica
lease (25M/2003) covers the central Brookside block. The exceptions:

- **Middleton Creek** — clear of every tenement. Also the field's most
  recently productive ground (7.9 kg recorded 1935–41; ~1.2 kg c. 1990).
- **ERA9999 released ground** (no holder; open for applications) over
  Longback Creek, Mt Donaldson and the Savage River workings.
- **Two licences lapse in December 2026**: EL25/2020 (Frenchmans, Nancy,
  Hangmans Creeks) on the 2nd; EL7/2021 (Sabbath Creek) on the 21st. The
  [tenure watcher](README.md#tenure-monitoring) monitors both weekly.

No target sits in a mining-prohibited reserve; the Pieman River State Reserve
corridor is the standing local exception.

## 2. Reach-level result: where creek, lead and open ground coincide

`reach_analysis.py` samples each creek centreline every 25 m and classifies
tenure × lead proximity (≤150 m of mapped Tertiary lead units, `Ts*`) ×
reserve. Of ~67 km of mapped creek, approximately 4.5 km is "prime":
accessible tenure and lead-fed.

| Creek | Prime length | Tenure class |
|---|---|---|
| Longback Creek ("The Badger") | 1,325 m in 3 reaches | released (ERA9999) |
| Frenchman Creek | 972 m in 3 reaches | EL25/2020 — opens Dec 2026 if not renewed |
| Brown Plains Creek | 824 m | EL25/2020 — as above |
| None Such Creek | 645 m (397 m open, 248 m released) | open / released |
| Doodie Creek | 298 m in 2 reaches | EL25/2020 — as above |
| Nancy Creek | 224 m | EL25/2020 — as above |
| Middleton Creek | 175 m | open |

Longback Creek was rushed in 1879, is absent from the modern mining
appendices, and was relocated here through its surviving name in the LIST
hydrography layer. Its lead-crossing reaches fall on released ground. Reach coordinates are in `data/*/corinna_reaches.geojson`.

## 3. The occurrence audit found ground the histories never named

All 111 recorded gold/osmiridium workings in the core field (212 in the wide
frame) were put through the same tenure/lead/reserve tests as the historical
targets. Workings >750 m from every historical target, ranked by access:

- **Nonesuch Creek** — recorded gold working, clear of all tenements,
  directly on mapped Tertiary lead — a combination recorded in none of the
  1880s reports.
- Also open: Section 11663 (Au + Os-Ir), Whyte Creek, Savage River Alluvial.
- On released ground and on mapped lead: Brooklyn, New Donaldson.
- The cluster sits NE of Corinna township, on the near side of the field.

## 4. Corrections to the historical record

- **Main Rivulet** (600–900 kg est., the field's richest number): the
  converted source grid ref plotted ~87 km south of the field. MRT's surveyed
  occurrence data places the actual workings at Golden Ridge (145.2004,
  -41.5087) — inside a granted mining lease (2M/2001), in reef country approximately
  7 km from mapped lead.
- **Hangmans and Longback Creeks** — "archival-only" in the source pack —
  both survive by name in modern hydrography and now carry coordinates.
- Four creeks initially appeared to have no named centreline in modern
  hydrography (Sabbath, Frenchmans, Whyte, Nonesuch). The LIST Named
  Features layer (the Placenames Tasmania register) resolved all four as
  spelling or naming differences: the registered hydrography names are
  **Sunday Creek** (Sabbath's 1879 name), **Frenchman Creek**, **White
  Creek** and **None Such Creek**. The register also preserves superseded
  and unofficial names — Sydney Tom Creek (Hangmans Creek's alias in the
  1880 reports), Chinaman Creek (superseded), McGinty Creek — making it the
  bridge dataset between the historical record and modern hydrography.

## 5. The wider district

A 30 km sweep (`--margin 0.30`) adds: **Specimen Reef** (the reef source
Haygarth identifies as feeding the Long Plains alluvials) with four
neighbouring workings on released ground; the **Bald Hill osmiridium field**
(freshly licensed EL7/2026); the **Wilson River corridor** (~24 workings,
EL22/2025); and **three declared MRT Fossick Areas** — Castray (with the
Brassy North gold working inside it), Magnet Range, and Melba Flat.

## 6. Access tracks

The LIST track layer records 159 track segments in the wide analysis window,
13 of them closed. Directly relevant to the field: **Longback Track**
(approaching the Longback Creek prime reaches from the north), **Whyte River
Track** and the **Historic Graves Track** near Corinna township. Closed
segments mark former routes and are retained in `corinna_tracks.geojson`;
track status says nothing about land access permission.

Ten further historic routes were recovered from the Placenames Tasmania
register, whose name-extent polygons for linear features are thin corridors
tracing the route: the superseded **Corinna Track / Old Corinna Track** (the
southern overland approach to the township), the superseded **Corinna Road**
and **Balfour Road** alignments, the **Cleveland Tram Road**, and the Dennis,
Salmons, Climies, Duck Creek, Top Farm and Trail Creek Tracks. These are
committed as `historic_routes.geojson` (corridor polygons, not surveyed
centrelines). The 1877–85 network itself is documented in freely available text
(Haygarth 2012) and is reconstructed as `documented_routes_1881.geojson`,
five routes with the source quotation attached to each feature:

- **Savage River water route** (1879–81) — "the thoroughfare between the
  Middletons Creek diggings and the Pieman River"; the Donaldson Inn at its
  mouth "could only be approached by water". Traced along the river.
- **Pieman River water route** — steamer and boat thoroughfare from the
  heads past Corinna to the middle reaches. Traced along the river.
- **Corinna Track** (by 1880, improved for machinery 1883) — Waratah to the
  diggings and Corinna, with stores at Long Plains and the 20-Mile Mark and
  the mile-long "Underground Railway" crawl. Alignment indicative.
- **Government Store track** (1881) — Corinna store to the Middletons Creek
  workings. Alignment indicative.
- **Sprent's track** (1876) — Waratah to Mount Heemskirk via the Ramsay
  River and Yellowband Plain. Alignment indicative.

Water routes follow the actual river geometry; land routes are indicative
lines between documented waypoints. Exact 1880s land alignments would still
require a full-resolution scan of Thureau's map (Parliamentary Paper
82/1881, which marks "Thureau's Track"); the reproduction in Haygarth (2012)
is too small to digitise.

## 7. Attested but unworked or under-tested ground

A cross-examination of the narrative record (Thureau's 1881 map, Haygarth
2012 and 2022, Montgomery 1894) against the occurrence database and the
placenames register, looking for ground the record praises that the modern
datasets do not know. Candidates, with their evidence, are committed as
`unworked_candidates.geojson`. Ranked:

- **Brooklyn Hydraulic** (released ground, on mapped lead). The company's
  manager recalled sluicing a fortnight in 1895 for 16 oz "which paid
  expenses for the actual time of sluicing" — then being shut by a
  directors' wire when *other* companies' clean-ups disappointed. Paying
  ground closed by corporate contagion, barely opened.
- **New Donaldson Hydraulic** (released ground, on mapped lead). After more
  than a year of works and a 19.4 km head race, the mine "was abandoned
  without its gravels being tested". The unused race survives beside the
  Western Explorer road.
- **George Town Packet Creek** (EL25/2020 — December 2026 window; 129 m from
  mapped lead). A numbered gold locality on Thureau's 1881 field map with no
  recorded occurrence within ~8 km today.
- **Duck Creek** (EL2/2018 to Aug 2027; 213 m from mapped lead). As above:
  1881-mapped, no modern record within ~9 km.
- **Mount Livingstone southern plateau** (EL23/2020 — also lapses 2 December
  2026). Montgomery 1894: "undoubtedly an excellent field for hydraulic
  sluicing in the terraces along the Savage, Whyte, and Pieman Rivers, and
  on the plateau lying south of Mount Livingstone." No occurrence within
  ~5 km; note the 25K mapping shows no Ts unit there, so the terraces are
  either unmapped at that scale or Montgomery overreached.
- **Amelia Creek and Alice Creek** — two of the four creeks the Slater
  brothers named in 1879. Their siblings Nancy and Lucy carry recorded
  workings; Amelia and Alice do not appear in the placenames register at
  all. Lost localities; the 1879–85 newspapers are the relocation source.
- A tail of digger-era stream names with no recorded working nearby
  (Linger and Die, Doctors, Cruncher, Smoko, Post Office, Paradox Creeks
  and others) — name-evidence only, listed in the analysis but not in the
  candidates file.

Context for the hydraulic-era candidates: the 1895 clean-ups were poor
overall (Corinna Hydraulic 80 oz, Brookside 34 oz), and Haygarth's verdict
on the craze is that terrace elevation, thin wash and "ultimately, there
wasn't enough gold" ended it. Brooklyn (paying when closed) and New
Donaldson (never tested) are the two documented exceptions to that verdict.

A third December date emerged from this search: **EL23/2020 (Georgina
Resources) also expires 2 December 2026**, covering the Mount Livingstone
ground; it has been added to the tenure watcher.

## 8. Negative results

- **No LiDAR coverage** over the field — canopy-penetrating detection of old
  workings is not currently possible from public data.
- Historic aerial scans (893 frames over the field, oldest 1946) exist but
  sit behind the LIST login — browser access via LISTmap's Aerial Photo
  Viewer only.
- MRT DIGS, the Tasmanian Parliament digitised papers, and mindat.org all
  block automated access; the primary 1880s reports must be pulled manually.

## Method + caveats

Every claim above is reproducible: `corinna_workflow.py` (targets),
`reach_analysis.py` (reaches), `tenure_watch.py` (change detection) — see the
README. This is a screening analysis, not legal advice: tenure comes from a
daily snapshot, "mining available under the MRDA" still requires a
Prospecting Licence plus reserve conditions, and every position should be
verified on LISTmap and the MRT tenement viewer. Confirm access questions
with MRT (info@mrt.tas.gov.au).
