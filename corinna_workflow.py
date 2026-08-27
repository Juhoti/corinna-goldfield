#!/usr/bin/env python3
"""
CORINNA GOLDFIELD — combined geology + tenement + reserve + history workflow
=============================================================================
Answers the question: where does Tertiary deep-lead gravel sit in UNWORKED
upper catchments, on OPEN ground?  Tests the history-derived target points
(corinna_targets.geojson) against three live layers:

  1. MRT Current Mineral Tenements   — leases + licences + unavailable areas
     (statewide zipped shapefile, updated daily)
  2. LIST 'Geological Polygons 25K'  — the Tertiary lead gravels
  3. LIST 'Tasmanian Reserve Estate' — reserves, incl. whether mining is
     available under the MRDA in each one

Layers 2 and 3 are fetched from the LIST ArcGIS REST API clipped to the
field's bounding box, so the download is a few MB, not statewide.

WHAT IT TELLS YOU, per target
  - tenure : inside a current mineral tenement? (distance to nearest edge)
  - lead   : on / near mapped Tertiary sediment (Tsgs, Tss, Tsgra — the
             "interbedded siliceous gravel, quartz sand and clay" units)
  - reserve: which reserve it falls in, and that reserve's MRDA mining status

The sweet spot = tier-3 (upstream) + ON/near Tertiary gravel + clear of
tenement + not in a mining-unavailable reserve.

CAVEATS
  - Target coordinates are ~100-200 m (old AMG conversion). Every result is
    "the right creek, roughly" — verify on LISTmap before travelling.
  - "Mining available under the MRDA" still requires a Prospecting Licence
    and any reserve-specific conditions. This script is a screening tool,
    not legal advice; confirm with MRT (info@mrt.tas.gov.au).

USAGE
    pip install -r requirements.txt
    python3 corinna_workflow.py             # normal run (caches downloads)
    python3 corinna_workflow.py --refresh   # re-download (tenements change daily)

Output: corinna_result.geojson — the targets with all computed columns,
ready to style in QGIS over a topo basemap.
"""
import argparse
import io
import json
import sys
import zipfile
from pathlib import Path

import requests
import pandas as pd
import geopandas as gpd

HERE = Path(__file__).parent
WORK = HERE / "work"
TARGETS = HERE / "corinna_targets.geojson"
MGA55 = "EPSG:28355"   # GDA94 / MGA zone 55 — metres, so distances are metres

TENEMENT_ZIP = ("https://www.mrt.tas.gov.au/mrtdoc/public_files/"
                "Current_Mineral_Tenements_Shapefile.zip")

LIST_REST = "https://services.thelist.tas.gov.au/arcgis/rest/services"
GEOLOGY_LAYER = f"{LIST_REST}/Public/GeologicalAndSoils/MapServer/14"      # Geological Polygons 25K
RESERVES_LAYER = f"{LIST_REST}/Public/CadastreAndAdministrative/MapServer/29"  # Tasmanian Reserve Estate

# What counts as deep-lead material in the 25K schema. Verified against the
# live layer (2026-08): the lead units around Corinna are Tsgs / Tss / Tsgra
# ("interbedded siliceous gravel, quartz sand and clay", "rounded and angular
# gravel, mainly vein quartz") — the word "Tertiary" appears NOWHERE in their
# attributes (PERIOD is "Cretaceous - Quaternary"), so we match the Ts* symbol
# prefix (Tertiary sediments) plus 'gravel' in the description.
LEAD_SYMBOL_PREFIXES = ("Ts",)
LEAD_DESCRIPT_HINTS = ("gravel",)

# Degrees of margin around the targets when clipping the LIST layers.
BBOX_MARGIN = 0.05

# A target further than this from the median of the field is almost certainly
# a bad grid-ref conversion, not a real location. Flagged loudly, not dropped,
# and excluded from the download bounding box.
OUTLIER_M = 25_000

TIER_LABEL = {1: "1-HIGH-YIELD", 2: "2-DOCUMENTED", 3: "3-UPSTREAM/EXPLORATORY"}


def fetch_tenements(refresh=False):
    """MRT statewide tenement zip: merge ALL shapefiles inside (leases,
    licences, unavailable areas) — a point can be caught by any of them."""
    WORK.mkdir(exist_ok=True)
    cache = WORK / "tenements.gpkg"
    if cache.exists() and not refresh:
        print(f"[cache] {cache.name}  (use --refresh for today's data)")
        return gpd.read_file(cache)
    print(f"[download] {TENEMENT_ZIP}  (~36 MB, the slow bit)")
    try:
        r = requests.get(TENEMENT_ZIP, timeout=600)
        r.raise_for_status()
        zf = zipfile.ZipFile(io.BytesIO(r.content))
    except Exception as e:
        print(f"  !! tenement download failed: {e}")
        return None
    shps = [n for n in zf.namelist() if n.lower().endswith(".shp")]
    if not shps:
        print("  !! no .shp inside — MRT may have changed the layout")
        return None
    zf.extractall(WORK / "tenements_raw")
    parts = []
    for shp in shps:
        gdf = gpd.read_file(WORK / "tenements_raw" / shp)
        gdf["layer"] = Path(shp).stem   # LEASES / LICENCES / UNAVAILABLE_AREAS
        parts.append(gdf)
        print(f"  {Path(shp).stem}: {len(gdf)} features")
    ten = gpd.GeoDataFrame(pd.concat(parts, ignore_index=True), crs=parts[0].crs)
    if ten.crs is None:
        ten = ten.set_crs(MGA55)
    ten.to_file(cache, driver="GPKG")
    print(f"  ok: {len(ten)} tenement features total -> {cache.name}")
    return ten


def fetch_list_layer(layer_url, bbox, cache_name, refresh=False):
    """Query a LIST ArcGIS REST layer clipped to bbox (lon/lat), paginated."""
    WORK.mkdir(exist_ok=True)
    cache = WORK / f"{cache_name}.gpkg"
    if cache.exists() and not refresh:
        print(f"[cache] {cache.name}")
        return gpd.read_file(cache)
    print(f"[query] {layer_url}")
    feats, offset = [], 0
    while True:
        params = {
            "where": "1=1",
            "geometry": ",".join(f"{v:.5f}" for v in bbox),
            "geometryType": "esriGeometryEnvelope",
            "inSR": "4326", "outSR": "4326",
            "outFields": "*", "returnGeometry": "true",
            "resultOffset": offset, "f": "geojson",
        }
        try:
            r = requests.get(f"{layer_url}/query", params=params, timeout=300)
            r.raise_for_status()
            page = r.json()
        except Exception as e:
            print(f"  !! LIST query failed: {e}")
            return None
        got = page.get("features", [])
        feats.extend(got)
        if page.get("exceededTransferLimit") or (page.get("properties") or {}).get(
                "exceededTransferLimit"):
            offset += len(got)
            continue
        break
    if not feats:
        print("  !! 0 features returned")
        return None
    gdf = gpd.GeoDataFrame.from_features(feats, crs="EPSG:4326")
    gdf.to_file(cache, driver="GPKG")
    print(f"  ok: {len(gdf)} features -> {cache.name}")
    return gdf


def flag_lead(geol):
    """Subset of 25K geology polygons that are Tertiary lead material."""
    if geol is None:
        return None
    sym = geol.get("SYMBOL", pd.Series("", index=geol.index)).astype(str)
    desc = geol.get("DESCRIPT", pd.Series("", index=geol.index)).astype(str).str.lower()
    mask = sym.str.startswith(LEAD_SYMBOL_PREFIXES) | desc.apply(
        lambda v: any(h in v for h in LEAD_DESCRIPT_HINTS))
    sub = geol[mask]
    units = sorted(sub["SYMBOL"].unique()) if "SYMBOL" in sub else []
    print(f"[geology] {len(sub)} lead polygons of {len(geol)} (units: {', '.join(units)})")
    return sub


def flag_outliers(tgt):
    """Warn about targets implausibly far from the field — bad conversions.
    Returns [(name, distance_m)]; callers also use it to exclude these from
    the download bounding box."""
    pts = tgt[tgt.geometry.notna()]
    if len(pts) < 3:
        return []
    med_x = pts.geometry.x.median()
    med_y = pts.geometry.y.median()
    bad = []
    for _, r in pts.iterrows():
        d = ((r.geometry.x - med_x) ** 2 + (r.geometry.y - med_y) ** 2) ** 0.5
        if d > OUTLIER_M:
            bad.append((r["name"], d))
            print(f"[!!] '{r['name']}' plots {d/1000:.0f} km from the rest of the "
                  f"field — grid-ref conversion is suspect. Fix it on LISTmap "
                  f"before trusting any result for this point.")
    return bad


def field_bbox(tgt_4326, outlier_names):
    """Lon/lat bounding box of the plausible targets, with margin."""
    pts = tgt_4326[tgt_4326.geometry.notna() & ~tgt_4326["name"].isin(outlier_names)]
    minx, miny, maxx, maxy = pts.total_bounds
    return (minx - BBOX_MARGIN, miny - BBOX_MARGIN,
            maxx + BBOX_MARGIN, maxy + BBOX_MARGIN)


def _text(row, *cols):
    """First non-empty string value among cols (pandas NaN-safe)."""
    for c in cols:
        v = row.get(c)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return None


def _tenement_label(row):
    bits = [_text(row, "NAME") or "unnamed",
            _text(row, "TENEMENTTY"), _text(row, "OWNER")]
    return " — ".join(b for b in bits if b)


def assess(tgt, ten, lead, reserves):
    """Attach tenure / lead / reserve columns to the target GeoDataFrame."""
    tgt = tgt.copy()
    tgt["tenure"] = "unknown"
    tgt["tenure_dist_m"] = None
    tgt["tenements"] = None      # which tenement(s) the point is inside, if any
    tgt["on_lead"] = None
    tgt["lead_dist_m"] = None
    tgt["reserve"] = None
    tgt["reserve_mining"] = None
    for i, r in tgt.iterrows():
        g = r.geometry
        if g is None:
            tgt.at[i, "tenure"] = "no coordinate (archival-only)"
            continue
        if ten is not None and len(ten):
            d = ten.distance(g).min()
            tgt.at[i, "tenure_dist_m"] = round(float(d))
            within = ten[ten.contains(g)]
            if len(within):
                tgt.at[i, "tenure"] = "ON TENEMENT"
                tgt.at[i, "tenements"] = "; ".join(
                    _tenement_label(row) for _, row in within.iterrows())
            else:
                tgt.at[i, "tenure"] = "clear"
        if lead is not None and len(lead):
            dg = lead.distance(g).min()
            tgt.at[i, "lead_dist_m"] = round(float(dg))
            tgt.at[i, "on_lead"] = bool(lead.contains(g).any())
        if reserves is not None and len(reserves):
            inres = reserves[reserves.contains(g)]
            if len(inres):
                row = inres.iloc[0]
                tgt.at[i, "reserve"] = _text(row, "RES_NAME", "RES_CLASS") or "reserve"
                tgt.at[i, "reserve_mining"] = _text(row, "MINING") or "unknown"
    return tgt


def print_report(tgt, have_lead, have_reserves):
    print("\n" + "=" * 84)
    print("CORINNA TARGETS — geology (lead) x tenement x reserve")
    print("=" * 84)
    for _, r in tgt.sort_values("tier").iterrows():
        line = f"\n[{TIER_LABEL.get(r['tier'], r['tier'])}] {r['name']}"
        if r.get("approx"):
            line += "  (POSITION APPROX)"
        print(line)
        print(f"    yield : {r['yield']}")
        print(f"    hist  : {r['history']}")
        if r.geometry is None:
            print("    geo   : no coordinate (archival-only) — locate via history + LISTmap")
            continue
        # tenure
        if r["tenure"] == "ON TENEMENT":
            ten_flag = f"ON TENEMENT: {r['tenements']}"
        elif r["tenure"] == "clear":
            d = r["tenure_dist_m"]
            ten_flag = (f"clear, ~{d}m from tenement edge" if d < 500
                        else f"clear of tenements (~{d // 1000}km)")
        else:
            ten_flag = "tenement layer unavailable"
        print(f"    tenure: {ten_flag}")
        # lead
        if r["on_lead"] is not None:
            geo_flag = ("ON Tertiary lead gravel" if r["on_lead"]
                        else f"~{r['lead_dist_m']}m from mapped Tertiary lead")
        else:
            geo_flag = f"geology layer unavailable — use stated lead field: {r['lead']}"
        print(f"    lead  : {geo_flag}")
        # reserve
        if not have_reserves:
            res_flag = "reserve layer unavailable — CHECK LISTmap"
        elif r["reserve"]:
            res_flag = f"{r['reserve']} — mining {r['reserve_mining']}"
            if "not available" in str(r["reserve_mining"]).lower():
                res_flag = "⚠ " + res_flag + "  ❌"
        else:
            res_flag = "not in any mapped reserve"
        print(f"    resrv : {res_flag}")

    print("\n" + "-" * 84)
    print("SWEET SPOT = tier-3 (upstream) + ON/near Tertiary lead + clear of tenement +")
    print("not in a mining-unavailable reserve. VERIFY each on LISTmap + the MRT tenement")
    print("viewer before travelling. 'Mining available under the MRDA' still requires a")
    print("Prospecting Licence and reserve conditions — confirm with info@mrt.tas.gov.au.")
    print("-" * 84)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--refresh", action="store_true",
                    help="re-download layers instead of using the cache "
                         "(tenements update daily)")
    ap.add_argument("--targets", type=Path, default=TARGETS,
                    help="target points GeoJSON (default: corinna_targets.geojson)")
    args = ap.parse_args(argv)

    if not args.targets.exists():
        sys.exit(f"missing {args.targets}")
    tgt_4326 = gpd.read_file(args.targets)
    tgt = tgt_4326.to_crs(MGA55)
    outliers = flag_outliers(tgt)
    bbox = field_bbox(tgt_4326, {n for n, _ in outliers})

    ten = fetch_tenements(args.refresh)
    geol = fetch_list_layer(GEOLOGY_LAYER, bbox, "geology25k", args.refresh)
    reserves = fetch_list_layer(RESERVES_LAYER, bbox, "reserves", args.refresh)
    lead = flag_lead(geol)

    if ten is not None:
        ten = ten.to_crs(MGA55)
    if lead is not None:
        lead = lead.to_crs(MGA55)
    if reserves is not None:
        reserves = reserves.to_crs(MGA55)

    result = assess(tgt, ten, lead, reserves)
    print_report(result, have_lead=lead is not None, have_reserves=reserves is not None)

    out = HERE / "corinna_result.geojson"
    result.to_crs("EPSG:4326").to_file(out, driver="GeoJSON")
    print(f"\n[ok] {out.name} written — targets WITH the computed tenure/lead/reserve")
    print("     columns. Load in QGIS over a topo/satellite basemap and style by them.")


if __name__ == "__main__":
    main()
