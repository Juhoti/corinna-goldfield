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
  [tenure watcher](README.md#the-tenure-watcher) monitors both weekly.

No target sits in a mining-prohibited reserve; the Pieman River State Reserve
corridor is the standing local exception.

## 2. Reach-level result: where creek, lead and open ground coincide

`reach_analysis.py` samples each creek centreline every 25 m and classifies
tenure × lead proximity (≤150 m of mapped Tertiary lead units, `Ts*`) ×
reserve. Of ~56 km of mapped creek, approximately 2.0 km is "prime": accessible
tenure and lead-fed.

| Creek | Prime length | Tenure class |
|---|---|---|
| **Longback Creek ("The Badger")** | **1,325 m** in 3 reaches | released (ERA9999) |
| Middleton Creek | 175 m | open |
| Nancy Creek | 224 m | EL25/2020 — opens Dec 2026 if not renewed |
| Doodie Creek | 298 m in 2 reaches | EL25/2020 — as above |

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
- **Sabbath, Frenchmans, Whyte and Nonesuch Creeks** have *no named
  centreline* in modern hydrography within the field, though their MRT
  occurrence points exist — a naming gap between the two government datasets.

## 5. The wider district

A 30 km sweep (`--margin 0.30`) adds: **Specimen Reef** (the reef source
Haygarth identifies as feeding the Long Plains alluvials) with four
neighbouring workings on released ground; the **Bald Hill osmiridium field**
(freshly licensed EL7/2026); the **Wilson River corridor** (~24 workings,
EL22/2025); and **three declared MRT Fossick Areas** — Castray (with the
Brassy North gold working inside it), Magnet Range, and Melba Flat.

## 6. Negative results

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
