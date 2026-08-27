#!/usr/bin/env python3
"""
CORINNA GOLDFIELD — combined geology + tenement + history workflow
===================================================================
Answers the question: where does Tertiary deep-lead gravel sit in UNWORKED
upper catchments, on OPEN ground?  Combines three real layers plus a
history-derived target list.

It downloads (on YOUR machine — these hosts are firewalled off Anthropic's
sandbox, so this must run locally):
  1. MRT Current Mineral Tenements  (leases / ELs / unavailable areas)
  2. MRT 1:25 000 Geology           (Tertiary gravel polygons = the lead)
and tests the target points (corinna_targets.geojson) against both.

WHAT IT TELLS YOU
  - tenement: is the point inside a current mineral tenement?
  - geology:  does the point sit on / near mapped Tertiary gravel (lead)?
  - the intersection of "Tertiary gravel" + "upstream/tier-3" + "no tenement"
    is the exploratory sweet spot you were asking about.

WHAT IT DOESN'T
  - Reserve / national-park / conservation land is a SEPARATE layer (the LIST,
    'Tasmania Reserves'). A point clear of mineral tenements can still be inside
    the Savage River Regional Reserve / Tarkine. The script fetches that layer
    too IF you give it the LIST WFS URL (see RESERVES_WFS below); otherwise it
    prints a reminder to check LISTmap by hand.
  - Coordinates are ~100-200 m (old AMG conversion). Treat every result as
    "the right creek, roughly" — verify on LISTmap before travelling.

REQUIREMENTS
    pip install geopandas requests
RUN
    python3 corinna_workflow.py
"""
import io, sys, zipfile, json
from pathlib import Path
import requests
import geopandas as gpd

HERE = Path(__file__).parent
WORK = HERE / "work"; WORK.mkdir(exist_ok=True)
TARGETS = HERE / "corinna_targets.geojson"
MGA55 = "EPSG:28355"

TENEMENT_ZIP = ("https://www.mrt.tas.gov.au/mrtdoc/public_files/"
                "Current_Mineral_Tenements_Shapefile.zip")

# MRT 1:25k geology is served as a zipped shapefile from the digital-data page.
# The exact filename changes occasionally; if this 404s, grab the current link
# from https://www.mrt.tas.gov.au/products/digital_data and paste it here.
GEOLOGY_ZIP = ("https://www.mrt.tas.gov.au/mrtdoc/public_files/"
               "Geology_25k_Shapefile.zip")   # <-- verify/replace if needed

# OPTIONAL: LIST reserves as WFS (GeoJSON). Find the current layer URL in
# LISTdata (https://listdata.thelist.tas.gov.au) -> "Tasmania Reserves".
# Leave as None to skip (script will remind you to check LISTmap manually).
RESERVES_WFS = None  # e.g. "https://services.thelist.tas.gov.au/.../query?...f=geojson"

# Which geology attribute values indicate Tertiary gravels / deep-lead material.
# Printed field names on first run so you can tune this to the actual schema.
TERTIARY_HINTS = ["tertiary", "gravel", "browns plains", "cainozoic", "cenozoic"]


def dl_shapefile(url, cache_name):
    cache = WORK / f"{cache_name}.gpkg"
    if cache.exists():
        print(f"[cache] {cache.name}")
        return gpd.read_file(cache)
    print(f"[download] {url}")
    try:
        r = requests.get(url, timeout=600); r.raise_for_status()
    except Exception as e:
        print(f"  !! download failed: {e}")
        return None
    try:
        zf = zipfile.ZipFile(io.BytesIO(r.content))
    except zipfile.BadZipFile:
        print("  !! not a zip — the URL may have changed. Check the digital-data page.")
        return None
    shps = [n for n in zf.namelist() if n.lower().endswith(".shp")]
    if not shps:
        print("  !! no .shp inside"); return None
    # Multi-layer zips (25k geology ships polygons + lines + points): prefer the
    # polygon layer, else fall back to the biggest file in the archive.
    shp = next((n for n in shps if "poly" in n.lower()), None) \
          or max(shps, key=lambda n: zf.getinfo(n).file_size)
    if len(shps) > 1:
        print(f"  {len(shps)} shapefiles in zip; using {shp}")
    zf.extractall(WORK / cache_name)
    gdf = gpd.read_file(WORK / cache_name / shp)
    if gdf.crs is None: gdf = gdf.set_crs(MGA55)
    gdf.to_file(cache, driver="GPKG")
    print(f"  ok: {len(gdf)} features -> {cache.name}")
    return gdf


def flag_tertiary(geol):
    """Return subset of geology polygons that look like Tertiary gravel / lead."""
    if geol is None: return None
    cols = [c for c in geol.columns if geol[c].dtype == object]
    print(f"[geology] attribute columns: {list(geol.columns)}")
    mask = None
    for c in cols:
        s = geol[c].astype(str).str.lower()
        m = s.apply(lambda v: any(h in v for h in TERTIARY_HINTS))
        mask = m if mask is None else (mask | m)
    if mask is None: return geol.iloc[0:0]
    sub = geol[mask]
    print(f"[geology] {len(sub)} polygons match Tertiary/gravel hints "
          f"(of {len(geol)}). Tune TERTIARY_HINTS if this looks off.")
    return sub


def main():
    if not TARGETS.exists():
        sys.exit(f"missing {TARGETS}")
    tgt = gpd.read_file(TARGETS).to_crs(MGA55)

    ten = dl_shapefile(TENEMENT_ZIP, "tenements")
    geol = dl_shapefile(GEOLOGY_ZIP, "geology25k")
    tert = flag_tertiary(geol) if geol is not None else None
    if tert is not None: tert = tert.to_crs(MGA55)
    if ten is not None: ten = ten.to_crs(MGA55)

    reserves = None
    if RESERVES_WFS:
        try:
            reserves = gpd.read_file(RESERVES_WFS).to_crs(MGA55)
            print(f"[reserves] {len(reserves)} polygons")
        except Exception as e:
            print(f"[reserves] WFS fetch failed ({e}); check LISTmap by hand")

    print("\n" + "="*84)
    print("CORINNA TARGETS — geology (lead) x tenement x reserve")
    print("="*84)
    order = {1:"1-HIGH-YIELD", 2:"2-DOCUMENTED", 3:"3-UPSTREAM/EXPLORATORY"}
    for _, r in sorted(tgt.iterrows(), key=lambda kv: kv[1]["tier"]):
        p = r
        g = r.geometry
        line = f"\n[{order[p['tier']]}] {p['name']}"
        if p.get("approx"): line += "  (POSITION APPROX)"
        print(line)
        print(f"    yield : {p['yield']}")
        print(f"    hist  : {p['history']}")
        if g is None:
            print("    geo   : no coordinate (archival-only) — locate via history + LISTmap")
            continue
        # tenement test
        if ten is not None:
            within = ten[ten.contains(g)]
            dmin = ten.distance(g).min()
            if len(within): ten_flag = "ON TENEMENT (permission/❌)"
            elif dmin < 500: ten_flag = f"clear, ~{int(dmin)}m from tenement edge"
            else: ten_flag = f"clear of tenements (~{int(dmin/1000)}km)"
        else: ten_flag = "tenement layer unavailable"
        # geology test
        if tert is not None and len(tert):
            on = tert.contains(g).any()
            dg = tert.distance(g).min()
            geo_flag = ("ON Tertiary gravel (LEAD)" if on
                        else f"~{int(dg)}m from mapped Tertiary gravel")
        else:
            geo_flag = "geology layer unavailable — use stated lead field: " + str(p['lead'])
        # reserve test
        if reserves is not None:
            inres = reserves.contains(g).any()
            res_flag = "  ⚠ INSIDE RESERVE" if inres else ""
        else:
            res_flag = ""
        print(f"    tenure: {ten_flag}{res_flag}")
        print(f"    lead  : {geo_flag}")

    print("\n" + "-"*84)
    print("SWEET SPOT = tier-3 (upstream) + ON/near Tertiary gravel + clear of tenement + not in reserve.")
    print("Those are unworked lead-fed creeks on open ground. VERIFY each on LISTmap +")
    print("MRT viewer before travelling; confirm a Prospecting Licence is held.")
    if reserves is None:
        print("NOTE: reserve layer not loaded — you MUST still check the Savage River")
        print("Regional Reserve / Tarkine boundary on LISTmap for every point.")
    print("-"*84)

    out = HERE / "corinna_result.geojson"
    tgt.to_crs("EPSG:4326").to_file(out, driver="GeoJSON")
    print(f"\n[ok] {out.name} written — load in QGIS over a topo/satellite basemap.")


if __name__ == "__main__":
    main()
