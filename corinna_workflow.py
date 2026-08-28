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
TRACKS_LAYER = f"{LIST_REST}/Public/TopographyAndRelief/MapServer/24"          # Tracks-Ferry Routes

# MRT Mineral Occurrences: every recorded working/deposit in the state, with
# surveyed positions (LOC_ACC in metres — mostly 50-200 m, better than our
# converted 1880s grid refs).
OCCURRENCES_ZIP = ("https://www.mrt.tas.gov.au/mrtdoc/public_files/"
                   "Mineral_Occurrences_Shapefile.zip")
GOLD_PATTERN = "Gold|Osmium|Osmiridium|Platinoids"
# A recorded working within this distance of a target counts as "at" it; an
# occurrence further than this from EVERY target is reported as a candidate
# the history pack missed.
NEAR_WORKINGS_M = 750

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


def fetch_occurrences(bbox, refresh=False):
    """MRT Mineral Occurrences (statewide zip, cached), clipped to bbox and
    filtered to gold / osmiridium. Keeps lon/lat columns for reporting."""
    WORK.mkdir(exist_ok=True)
    cache = WORK / "occurrences.gpkg"
    if cache.exists() and not refresh:
        print(f"[cache] {cache.name}")
        occ = gpd.read_file(cache)
    else:
        print(f"[download] {OCCURRENCES_ZIP}")
        try:
            r = requests.get(OCCURRENCES_ZIP, timeout=300)
            r.raise_for_status()
            zf = zipfile.ZipFile(io.BytesIO(r.content))
        except Exception as e:
            print(f"  !! occurrences download failed: {e}")
            return None
        shp = next((n for n in zf.namelist() if n.lower().endswith(".shp")), None)
        if not shp:
            print("  !! no .shp inside")
            return None
        zf.extractall(WORK / "occurrences_raw")
        occ = gpd.read_file(WORK / "occurrences_raw" / shp)
        occ.to_file(cache, driver="GPKG")
        print(f"  ok: {len(occ)} occurrences statewide -> {cache.name}")
    occ = occ.to_crs("EPSG:4326")
    occ = occ.cx[bbox[0]:bbox[2], bbox[1]:bbox[3]]
    au = occ[occ["COMMODITYS"].astype(str).str.contains(
        GOLD_PATTERN, case=False, na=False)].copy()
    au["lon"] = au.geometry.x.round(4)
    au["lat"] = au.geometry.y.round(4)
    print(f"[workings] {len(au)} recorded gold/Os-Ir workings in the field "
          f"(of {len(occ)} occurrences in bbox)")
    return au


def flag_lead(geol):
    """Subset of 25K geology polygons that are Tertiary lead material."""
    if geol is None:
        return None
    sym = geol.get("SYMBOL", pd.Series("", index=geol.index)).astype(str)
    desc = geol.get("DESCRIPT", pd.Series("", index=geol.index)).astype(str).str.lower()
    # Tertiary only: Ts* is the lead-sediment family; other T* units count when
    # their description says gravel. Quaternary (Q*) stream gravels are modern
    # alluvium, not deep lead — deliberately excluded.
    mask = sym.str.startswith(LEAD_SYMBOL_PREFIXES) | (
        sym.str.startswith("T") & desc.apply(
            lambda v: any(h in v for h in LEAD_DESCRIPT_HINTS)))
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


def field_bbox(tgt_4326, outlier_names, margin=BBOX_MARGIN):
    """Lon/lat bounding box of the plausible targets, with margin."""
    pts = tgt_4326[tgt_4326.geometry.notna() & ~tgt_4326["name"].isin(outlier_names)]
    minx, miny, maxx, maxy = pts.total_bounds
    return (minx - margin, miny - margin, maxx + margin, maxy + margin)


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


def assess(tgt, ten, lead, reserves, occ=None):
    """Attach tenure / lead / reserve / workings columns to the targets."""
    tgt = tgt.copy()
    tgt["tenure"] = "unknown"
    tgt["tenure_dist_m"] = None
    tgt["tenements"] = None      # which tenement(s) the point is inside, if any
    tgt["on_lead"] = None
    tgt["lead_dist_m"] = None
    tgt["reserve"] = None
    tgt["reserve_mining"] = None
    tgt["workings_near"] = None      # recorded workings within NEAR_WORKINGS_M
    tgt["nearest_working"] = None
    tgt["nearest_working_m"] = None
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
        if occ is not None and len(occ):
            d = occ.distance(g)
            j = d.idxmin()
            tgt.at[i, "nearest_working"] = _text(occ.loc[j], "NAME") or "unnamed"
            tgt.at[i, "nearest_working_m"] = round(float(d.min()))
            tgt.at[i, "workings_near"] = int((d <= NEAR_WORKINGS_M).sum())
    return tgt


def new_candidates(occ, tgt):
    """Recorded workings further than NEAR_WORKINGS_M from every target —
    ground the history pack never surfaced. Returns (named, n_unnamed)."""
    if occ is None or not len(occ):
        return [], 0
    pts = tgt[tgt.geometry.notna()]
    named, unnamed = [], 0
    for _, o in occ.iterrows():
        d = pts.distance(o.geometry).min()
        if d <= NEAR_WORKINGS_M:
            continue
        if _text(o, "NAME") and o["NAME"] != "Unnamed":
            named.append((o, d))
        else:
            unnamed += 1
    named.sort(key=lambda t: -t[1])
    return named, unnamed


def _tenure_short(o):
    """One-word access flag for a working: OPEN / released / tenement id."""
    if o.get("tenure") == "clear":
        return "OPEN"
    tens = str(o.get("tenements") or "")
    if "Release Area" in tens:
        return "released"
    return tens.split(" — ")[0] if tens else "?"


def print_candidates(named, unnamed):
    if not named and not unnamed:
        return
    print("\n" + "=" * 84)
    print(f"RECORDED WORKINGS >{NEAR_WORKINGS_M}m FROM EVERY TARGET — "
          "ground the history pack missed")
    print("(MRT Mineral Occurrences, surveyed; tenure/lead tested like the targets)")
    print("=" * 84)
    rank = {"OPEN": 0, "released": 1}
    named = sorted(named, key=lambda t: (rank.get(_tenure_short(t[0]), 2),
                                         str(t[0]["NAME"])))
    for o, d in named:
        acc = f"±{int(o['LOC_ACC'])}m" if pd.notna(o.get("LOC_ACC")) else ""
        lead = (f"lead ~{o['lead_dist_m']}m" if o.get("lead_dist_m") is not None
                else "")
        res = ""
        if "not available" in str(o.get("reserve_mining") or "").lower():
            res = "  ⚠ NO-MINING RESERVE"
        print(f"  {str(o['NAME'])[:32]:32s} {_tenure_short(o):10s} "
              f"{o['lat']:.4f},{o['lon']:.4f} {acc:>7s}  {lead:>12s}{res}")
    if unnamed:
        print(f"  ... plus {unnamed} unnamed occurrences — see corinna_workings.geojson")


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
        # recorded workings
        if r["workings_near"] is not None:
            print(f"    works : {r['workings_near']} recorded within {NEAR_WORKINGS_M}m"
                  f" — nearest: {r['nearest_working']} ({r['nearest_working_m']}m)")
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
    ap.add_argument("--margin", type=float, default=BBOX_MARGIN,
                    help="degrees of margin around the targets when clipping "
                         "layers (default %(default)s; try 0.3 to sweep the "
                         "surrounding districts - Bald Hill, Wilson River)")
    args = ap.parse_args(argv)

    if not args.targets.exists():
        sys.exit(f"missing {args.targets}")
    tgt_4326 = gpd.read_file(args.targets)
    tgt = tgt_4326.to_crs(MGA55)
    outliers = flag_outliers(tgt)
    bbox = field_bbox(tgt_4326, {n for n, _ in outliers}, args.margin)

    ten = fetch_tenements(args.refresh)
    geol = fetch_list_layer(GEOLOGY_LAYER, bbox, "geology25k", args.refresh)
    reserves = fetch_list_layer(RESERVES_LAYER, bbox, "reserves", args.refresh)
    tracks = fetch_list_layer(TRACKS_LAYER, bbox, "tracks", args.refresh)
    occ = fetch_occurrences(bbox, args.refresh)
    lead = flag_lead(geol)

    if ten is not None:
        ten = ten.to_crs(MGA55)
    if lead is not None:
        lead = lead.to_crs(MGA55)
    if reserves is not None:
        reserves = reserves.to_crs(MGA55)
    if occ is not None:
        occ = occ.to_crs(MGA55)

    result = assess(tgt, ten, lead, reserves, occ)
    print_report(result, have_lead=lead is not None, have_reserves=reserves is not None)
    occ_assessed = None
    if occ is not None and len(occ):
        # run the same tenure/lead/reserve tests over the recorded workings,
        # so missed ground is reported WITH its access status
        occ_assessed = assess(occ, ten, lead, reserves)
    named, unnamed = new_candidates(occ_assessed, tgt)
    print_candidates(named, unnamed)

    out = HERE / "corinna_result.geojson"
    result.to_crs("EPSG:4326").to_file(out, driver="GeoJSON")
    print(f"\n[ok] {out.name} written — targets WITH the computed tenure/lead/reserve")
    print("     columns. Load in QGIS over a topo/satellite basemap and style by them.")
    if lead is not None and len(lead):
        lout = HERE / "corinna_lead.geojson"
        lcols = [c for c in ("SYMBOL", "DESCRIPT", "PERIOD", "geometry")
                 if c in lead.columns]
        lead[lcols].to_crs("EPSG:4326").to_file(lout, driver="GeoJSON")
        print(f"[ok] {lout.name} written — {len(lead)} mapped Tertiary lead polygons.")
    if tracks is not None and len(tracks):
        tout = HERE / "corinna_tracks.geojson"
        tcols = [c for c in ("PRI_NAME", "STATUS", "USER_TYPE", "TRANS_TYPE",
                             "SURFACE_TY", "geometry") if c in tracks.columns]
        tracks[tcols].to_file(tout, driver="GeoJSON")
        closed = int((tracks.get("STATUS") == "Closed").sum())
        print(f"[ok] {tout.name} written — {len(tracks)} track segments "
              f"({closed} closed).")
    if occ_assessed is not None:
        wout = HERE / "corinna_workings.geojson"
        cols = [c for c in ("NAME", "COMMODITYS", "TYPE", "STATUS", "DEP_SIZE",
                            "LOC_ACC", "GENETIC", "REF", "tenure", "tenements",
                            "on_lead", "lead_dist_m", "reserve", "reserve_mining",
                            "geometry") if c in occ_assessed.columns]
        occ_assessed[cols].to_crs("EPSG:4326").to_file(wout, driver="GeoJSON")
        print(f"[ok] {wout.name} written — all {len(occ_assessed)} recorded "
              "gold/Os-Ir workings WITH tenure/lead/reserve columns.")


if __name__ == "__main__":
    main()
