# Corinna Goldfield — Combined Prospecting Workflow

Two halves that work together:
- **`corinna_workflow.py`** — the map tool. Downloads live MRT tenement + 1:25k
  geology data, tests target creeks for (a) deep-lead gravel and (b) tenement
  status, and flags the upstream lead-fed ground on open country.
- **`HISTORY_SOURCEPACK.md`** — the archive. Verified links to the 1880s reports
  and modern histories, annotated with the upstream detail to mine and how to
  cross-reference it against the map.
- **`corinna_targets.geojson`** — 19 target creeks in 3 tiers (high-yield /
  documented / upstream-exploratory), with lead status, yield, and history notes.
- **`corinna_gold_tenure.py`** — the simpler earlier script (tenement check only);
  superseded by `corinna_workflow.py` but kept as a lightweight fallback.

## Run
```
pip install geopandas requests
python3 corinna_workflow.py
```
Must run on your own machine — the MRT/LIST hosts are firewalled off the
environment this was built in, so the downloads only work locally.

## The one rule
Every result is "the right creek, roughly." The script narrows the search from
a whole goldfield to a handful of lead-fed candidates; **LISTmap and the MRT
viewer are what you navigate and check tenure by.** Confirm a Prospecting
Licence is held, and check the Savage River Regional Reserve / Tarkine boundary
for every point before going anywhere.

## Safety
Remote, wet, trackless, no phone coverage, hidden 1880s shafts. Not a solo trip.
Tell someone your route and return time. The Fatman barge has operating hours —
your exit is time-gated.
