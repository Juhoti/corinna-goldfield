# corinna-goldfield

GIS screening toolkit for the Corinna–Pieman goldfield in western Tasmania.
It cross-references the 19th-century mining record against current Tasmanian
government spatial data to classify historical gold workings by present-day
accessibility: mineral tenure, mapped Tertiary lead geology, and reserve
status.

Analysis results are summarised in [FINDINGS.md](FINDINGS.md). Dated copies
of the generated datasets are committed under [`data/`](data/), so the
results can be used without running anything.

## Data sources

| Dataset | Provider | Used for |
|---|---|---|
| Current Mineral Tenements (leases, licences, unavailable areas) | Mineral Resources Tasmania, updated daily | tenure classification |
| Mineral Occurrences | Mineral Resources Tasmania | recorded workings, surveyed positions |
| Geological Polygons 1:25 000 | LIST (ArcGIS REST) | Tertiary lead sediment mapping |
| Tasmanian Reserve Estate | LIST (ArcGIS REST) | reserve boundaries and MRDA mining availability |
| Rivers, Streams and Creeks | LIST (ArcGIS REST) | creek centrelines, historical name recovery |

Historical inputs (target creeks, yields, rush chronology) are drawn from the
1880s–1930s reports and modern histories listed in
[HISTORY_SOURCEPACK.md](HISTORY_SOURCEPACK.md).

## Installation

```
pip install -r requirements.txt
```

Requires Python 3.10+ and network access to `mrt.tas.gov.au` and
`services.thelist.tas.gov.au`. Downloads are cached under `work/`.

## Usage

```
python3 corinna_workflow.py              # per-target tenure/geology/reserve report
python3 corinna_workflow.py --refresh    # force re-download (tenements change daily)
python3 corinna_workflow.py --margin 0.3 # widen the analysis window to the
                                         # surrounding districts
python3 reach_analysis.py                # classify creek centrelines into reaches
python3 tenure_watch.py                  # diff current tenure against committed state
python3 locate_creeks.py "Hangmans Creek"  # find a creek name in the hydrography layer
python3 trove_links.py                   # Trove newspaper search links per target
```

Tests (no network required): `pip install pytest && pytest`

## Outputs

| File | Contents |
|---|---|
| `corinna_result.geojson` | the 19 historical targets with computed columns: tenure and containing tenements, distance to mapped lead, reserve and its mining status, nearby recorded workings |
| `corinna_workings.geojson` | all recorded gold/osmiridium occurrences in the analysis window, with the same assessment columns |
| `corinna_reaches.geojson` | creek centrelines segmented into reaches classified by tenure and lead proximity; the `prime` flag marks reaches that are both accessible and lead-fed |

All outputs are WGS84 GeoJSON and load directly in QGIS. The LIST ArcGIS
REST endpoint (`https://services.thelist.tas.gov.au/arcgis/rest/services`)
serves topographic, hillshade and orthophoto basemaps that can be added as
ArcGIS REST layers underneath them.

## Tenure monitoring

Mineral tenure over the field changes; two exploration licences covering
target creeks are due to expire in December 2026. `tenure_watch.py` snapshots
the tenure state of every target plus a watchlist of tenements into
`tenure_state.json`. A GitHub Action
(`.github/workflows/tenure-watch.yml`) runs it weekly, commits the updated
state, and opens an issue describing any change: ground opening or closing,
a tenement lapsing from the layer, an expiry date moving, or a holder change.

## Accuracy and limitations

- Historical target positions are converted 1880s–1930s grid references,
  accurate to roughly 100–200 m. MRT occurrence positions are surveyed,
  typically ±50–200 m. Boundary-adjacent results should be verified on
  LISTmap and the MRT tenement viewer.
- Tenure classification reflects a daily snapshot and is a screening result,
  not legal advice. Prospecting in Tasmania requires a Prospecting Licence
  outside declared fossicking areas, and land access rules apply
  independently of mineral tenure. Access questions should be confirmed with
  Mineral Resources Tasmania (info@mrt.tas.gov.au).
- The lead-geology filter selects Tertiary sediment units (`Ts*`, plus other
  Tertiary units whose description records gravel). Quaternary stream
  alluvium is deliberately excluded.
- Several historically named creeks (Sabbath, Frenchmans, Whyte, Nonesuch)
  have no named centreline in the current hydrography layer within the field,
  so reach analysis cannot cover them.
- No public LiDAR coverage exists over the field. Historic aerial photography
  (1946 onwards) exists but is only accessible through the LIST Aerial Photo
  Viewer after login.

## Field safety

The area is remote temperate rainforest with no mobile coverage and
unmarked 19th-century shafts. The Fatman Barge at Corinna operates limited
hours. Travel with company, leave route details, and treat all workings as
unstable.

## License

MIT. Government datasets remain subject to their providers' terms
(Mineral Resources Tasmania; Land Information System Tasmania).
