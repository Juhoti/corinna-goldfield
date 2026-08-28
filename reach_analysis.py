#!/usr/bin/env python3
"""
Reach-level analysis — from "the right creek" to "walk this stretch".
=====================================================================
The workflow tests one point per creek. This goes further: it pulls each
creek's centreline from the LIST hydrography layer, samples it every 25 m,
classifies every step by

  - tenure  : OPEN / fossick / released (ERA) / dec (licence lapsing Dec 2026)
              / held (live lease or licence) / unavailable (MRDA-excluded)
  - lead    : within LEAD_NEAR_M of a mapped Tertiary lead polygon?
  - reserve : inside a mining-unavailable reserve? (forces blocked)

then merges consecutive same-class steps into REACHES. A **prime reach** is
accessible tenure (OPEN / fossick / released / dec) AND lead-fed. That's the
stretch you actually walk with the detector.

Needs the workflow's cached layers (run `corinna_workflow.py` first, or the
caches download on demand).

USAGE
    python3 reach_analysis.py                  # default creek set
    python3 reach_analysis.py "Sabbath Creek" "Nonesuch Creek"
    python3 reach_analysis.py --lead-near 250  # widen the lead corridor

Output: corinna_reaches.geojson — every classified reach as a line, ready to
style in QGIS or the dossier map.
"""
import argparse
import sys
from pathlib import Path

import pandas as pd
import geopandas as gpd
import requests
from shapely.geometry import shape
from shapely.ops import linemerge, substring

from corinna_workflow import (fetch_tenements, fetch_list_layer, flag_lead,
                              MGA55, GEOLOGY_LAYER, RESERVES_LAYER, _text)

HERE = Path(__file__).parent
HYDRO_LAYER = ("https://services.thelist.tas.gov.au/arcgis/rest/services/"
               "Public/TopographyAndRelief/MapServer/15")
FIELD_BBOX = (144.98, -41.92, 145.56, -41.34)   # wide frame, lon/lat

STEP_M = 25          # sampling interval along each creek
LEAD_NEAR_M = 150    # "lead-fed" = within this of a mapped lead polygon
MIN_REACH_M = 100    # don't report slivers shorter than this

DEFAULT_CREEKS = [
    "Middleton Creek", "Sabbath Creek", "Longback Creek", "Hangmans Creek",
    "Frenchmans Creek", "Nancy Creek", "Lucy Creek", "Donnelly Creek",
    "Timbs Creek", "Eight Mile Creek", "Sailor Creek", "Sailor Jack Creek",
    "Main Rivulet", "Whyte Creek", "Nonesuch Creek", "Brown Plain Creek",
    "Browns Creek", "Doodie Creek", "Jansen Creek", "Jarman Creek",
]

ACCESS_GOOD = {"OPEN", "fossick", "released", "dec"}
DEC_LICENCES = ("EL25/2020", "EL7/2021")


def fetch_creeks(names):
    """{name: [LineString, ...]} from the LIST hydrography layer (MGA55)."""
    quoted = ",".join("'" + n.replace("'", "''") + "'" for n in names)
    r = requests.get(f"{HYDRO_LAYER}/query", params={
        "where": f"NAME IN ({quoted})",
        "geometry": ",".join(f"{v:.4f}" for v in FIELD_BBOX),
        "geometryType": "esriGeometryEnvelope", "inSR": "4326",
        "outSR": "4326", "outFields": "NAME", "f": "geojson"}, timeout=180)
    r.raise_for_status()
    grouped = {}
    for f in r.json().get("features", []):
        grouped.setdefault(f["properties"]["NAME"], []).append(shape(f["geometry"]))
    out = {}
    src = gpd.GeoSeries([], crs="EPSG:4326")
    for nm, gs in grouped.items():
        flat = [l for g in gs
                for l in (g.geoms if g.geom_type == "MultiLineString" else [g])]
        merged = linemerge(flat)
        parts = list(merged.geoms) if merged.geom_type == "MultiLineString" else [merged]
        proj = gpd.GeoSeries(parts, crs="EPSG:4326").to_crs(MGA55)
        out[nm] = list(proj)
    return out


def classify_matches(rows):
    """Access class from the tenement rows containing a point.
    rows: iterable of (layer, name) tuples. Priority: worst wins, except the
    fossick carve-out which is good by definition."""
    names = [str(n) for _, n in rows]
    layers = [str(l) for l, _ in rows]
    if any("Fossick" in n for n in names):
        return "fossick"
    unavailable = [n for l, n in zip(layers, names)
                   if l == "UNAVAILABLE_AREAS"]
    if unavailable:
        return "unavailable"
    held = [n for l, n in zip(layers, names)
            if l == "LEASES" or (l == "LICENCES" and n != "ERA9999"
                                 and n not in DEC_LICENCES)]
    if held:
        return "held:" + held[0]
    dec = [n for n in names if n in DEC_LICENCES]
    if dec:
        return "dec:" + dec[0]
    if "ERA9999" in names:
        return "released"
    return "OPEN"


def runs(labels):
    """[(start_idx, end_idx_inclusive, label)] for consecutive equal labels."""
    out = []
    start = 0
    for i in range(1, len(labels) + 1):
        if i == len(labels) or labels[i] != labels[start]:
            out.append((start, i - 1, labels[start]))
            start = i
    return out


def classify_line(line, ten, lead, reserves, step=STEP_M, lead_near=LEAD_NEAR_M):
    """Sample a line and return a list of per-step labels (access, lead_ok)."""
    n = max(2, int(line.length // step) + 2)
    ds = [i * line.length / (n - 1) for i in range(n)]
    pts = gpd.GeoDataFrame(geometry=[line.interpolate(d) for d in ds], crs=MGA55)

    access = ["OPEN"] * len(pts)
    if ten is not None and len(ten):
        j = gpd.sjoin(pts, ten[["layer", "NAME", "geometry"]], predicate="within")
        by_pt = {}
        for idx, row in j.iterrows():
            by_pt.setdefault(idx, []).append((row["layer"], row["NAME"]))
        for idx, rows_ in by_pt.items():
            access[idx] = classify_matches(rows_)

    lead_ok = [False] * len(pts)
    if lead is not None and len(lead):
        near = gpd.sjoin_nearest(pts, lead[["geometry"]], distance_col="d")
        d = near.groupby(near.index)["d"].min()
        for idx, dist in d.items():
            lead_ok[idx] = bool(dist <= lead_near)

    if reserves is not None and len(reserves):
        nomine = reserves[reserves["MINING"].astype(str)
                          .str.contains("not available", case=False, na=False)]
        if len(nomine):
            j = gpd.sjoin(pts, nomine[["geometry"]], predicate="within")
            for idx in set(j.index):
                access[idx] = "unavailable"

    return ds, list(zip(access, lead_ok))


def reaches_for_line(creek, part_i, line, labels, ds, min_len=MIN_REACH_M):
    """Merge label runs into reach records with substring geometry."""
    out = []
    for a, b, (access, lead_ok) in runs(labels):
        d0 = ds[a] if a > 0 else 0.0
        d1 = ds[b] if b < len(ds) - 1 else line.length
        length = d1 - d0
        if length < min_len:
            continue
        geom = substring(line, d0, d1)
        out.append({"creek": creek, "part": part_i,
                    "access": access, "lead": lead_ok,
                    "prime": access.split(":")[0] in {a.split(":")[0] for a in ACCESS_GOOD} and lead_ok,
                    "length_m": round(length), "geometry": geom})
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("creeks", nargs="*", default=None,
                    help="creek names (default: the target + open-cluster set)")
    ap.add_argument("--lead-near", type=float, default=LEAD_NEAR_M,
                    help="metres from mapped lead that counts as lead-fed "
                         "(default %(default)s)")
    ap.add_argument("--refresh", action="store_true",
                    help="re-download the tenement/geology/reserve layers")
    args = ap.parse_args(argv)
    names = args.creeks or DEFAULT_CREEKS

    ten = fetch_tenements(args.refresh)
    geol = fetch_list_layer(GEOLOGY_LAYER, FIELD_BBOX, "geology25k", args.refresh)
    reserves = fetch_list_layer(RESERVES_LAYER, FIELD_BBOX, "reserves", args.refresh)
    lead = flag_lead(geol)
    if ten is not None:
        ten = ten.to_crs(MGA55)
    if lead is not None:
        lead = lead.to_crs(MGA55)
    if reserves is not None:
        reserves = reserves.to_crs(MGA55)

    creeks = fetch_creeks(names)
    missing = [n for n in names if n not in creeks]
    for n in missing:
        print(f"[--] {n}: not in the hydrography layer inside the field bbox")

    all_reaches = []
    print("\n" + "=" * 84)
    print(f"PRIME REACHES — accessible tenure AND within {args.lead_near:.0f}m "
          "of mapped Tertiary lead")
    print("=" * 84)
    for nm in names:
        if nm not in creeks:
            continue
        recs = []
        for i, line in enumerate(creeks[nm]):
            ds, labels = classify_line(line, ten, lead, reserves,
                                       lead_near=args.lead_near)
            recs.extend(reaches_for_line(nm, i, line, labels, ds))
        all_reaches.extend(recs)
        prime = [r for r in recs if r["prime"]]
        total = sum(r["length_m"] for r in recs)
        if not prime:
            best = max(recs, key=lambda r: r["length_m"], default=None)
            note = (f"best is {best['access']}, lead={'yes' if best['lead'] else 'no'}"
                    if best else "no reaches")
            print(f"\n{nm}  ({total/1000:.1f} km mapped) — no prime reach ({note})")
            continue
        print(f"\n{nm}  ({total/1000:.1f} km mapped) — "
              f"{sum(r['length_m'] for r in prime)} m prime:")
        wgs = gpd.GeoSeries([r["geometry"] for r in prime], crs=MGA55).to_crs("EPSG:4326")
        for r, g in zip(prime, wgs):
            p0, p1 = g.coords[0], g.coords[-1]
            print(f"    {r['length_m']:>5} m  [{r['access']}]  "
                  f"{p0[1]:.4f},{p0[0]:.4f}  ->  {p1[1]:.4f},{p1[0]:.4f}")

    if all_reaches:
        gdf = gpd.GeoDataFrame(all_reaches, crs=MGA55).to_crs("EPSG:4326")
        out = HERE / "corinna_reaches.geojson"
        gdf.to_file(out, driver="GeoJSON")
        n_prime = int(gdf["prime"].sum())
        print("\n" + "-" * 84)
        print(f"[ok] {out.name} written — {len(gdf)} reaches, {n_prime} prime. "
              "Style by 'access'/'prime' in QGIS.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
