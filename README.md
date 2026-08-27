# Corinna Goldfield — Combined Prospecting Workflow

Screening tool for the Corinna–Pieman goldfield (western Tasmania): takes 19
history-derived target creeks and tests each against three **live** government
layers to find unworked, lead-fed ground on open country.

| Layer | Source | What it answers |
|---|---|---|
| Current Mineral Tenements | MRT statewide shapefile (daily) | is the creek inside a lease / EL / unavailable area? |
| Geological Polygons 25K | LIST ArcGIS REST (bbox-clipped) | does it sit on mapped Tertiary lead gravel (`Tsgs`/`Tss`/`Tsgra`)? |
| Tasmanian Reserve Estate | LIST ArcGIS REST (bbox-clipped) | which reserve is it in, and is mining *available under the MRDA* there? |

The **sweet spot** the tool surfaces: tier-3 (upstream) target + on/near
Tertiary lead + clear of tenements + not in a mining-unavailable reserve.

## Contents

- **`corinna_workflow.py`** — the map tool (above). Writes
  `corinna_result.geojson` with all computed columns, ready to style in QGIS.
- **`corinna_targets.geojson`** — 19 target creeks in 3 tiers
  (high-yield / documented / upstream-exploratory), with lead status, yield,
  and history notes.
- **`HISTORY_SOURCEPACK.md`** — verified links to the 1880s inspectors' reports
  and modern mining histories, annotated with the upstream detail to mine and
  how to cross-reference it against the map.
- **`corinna_gold_tenure.py`** — the simpler earlier script (tenement check
  only); superseded by `corinna_workflow.py` but kept as a lightweight fallback.
- **`tests/`** — offline tests (synthetic geometry + target-file validation).

## Run

```
pip install -r requirements.txt
python3 corinna_workflow.py            # caches downloads under work/
python3 corinna_workflow.py --refresh  # tenements update daily — refresh
                                       # before relying on a tenure answer
```

Tests: `pip install pytest && pytest` (no network needed).

## Reading the output

Each target gets:
- `tenure` / `tenure_dist_m` — ON TENEMENT, or clear + metres to the nearest
  tenement edge (near-boundary results deserve suspicion: see accuracy note)
- `on_lead` / `lead_dist_m` — on mapped Tertiary lead, or metres to it
- `reserve` / `reserve_mining` — reserve name and its MRDA mining status
  (e.g. Pieman River State Reserve is **Not available under the MRDA**)

## Known data issues

- **Main Rivulet** — the field's richest target (600–900 kg est.) — has an
  ambiguous grid reference in the source and currently plots ~87 km south of
  the field. The script flags it loudly and excludes it from the download
  bounding box. It needs re-locating on LISTmap; until then its row is noise.

## The one rule

Every result is "the right creek, roughly" — coordinates are ~100–200 m (old
AMG conversions). This narrows a whole goldfield to a handful of lead-fed
candidates; **LISTmap and the MRT tenement viewer are what you navigate and
verify by.** "Mining available under the MRDA" still requires a Prospecting
Licence and any reserve-specific conditions — confirm with MRT
(info@mrt.tas.gov.au) before going anywhere.

## Safety

Remote, wet, trackless, no phone coverage, hidden 1880s shafts. Not a solo
trip. Tell someone your route and return time. The Fatman barge at Corinna has
operating hours — your exit is time-gated.
