#!/usr/bin/env python3
"""
Corinna / Savage River goldfield — tenure check, terminal-only.

Downloads the LIVE MRT mineral tenement dataset (updated daily) and tests each
historical gold working against it: is the site inside a current lease /
exploration licence / unavailable area, or on apparently open ground?

WHAT THIS DOES AND DOESN'T TELL YOU
  - DOES: flags whether a point falls inside a current MRT *mineral tenement*.
  - DOES NOT: confirm a site is legal to prospect. Reserves / national parks /
    conservation areas / private land are a SEPARATE layer (the LIST), not in
    this dataset. A "CLEAR" result here means "no mineral tenement" — you still
    MUST check the LIST reserve/tenure layer and ideally email info@mrt.tas.gov.au
    before going. Gold-point coords are approximate (drainage-derived), so treat
    a hit/miss near a boundary as "investigate", not gospel.

REQUIREMENTS
    pip install geopandas requests
    (GDAL comes bundled with geopandas wheels; nothing else needed.)

USAGE
    python3 corinna_gold_tenure.py
"""

import io
import sys
import zipfile
from pathlib import Path

import requests
import geopandas as gpd
from shapely.geometry import Point

WORK = Path("./corinna_tenure")
WORK.mkdir(exist_ok=True)

TENEMENT_ZIP = (
    "https://www.mrt.tas.gov.au/mrtdoc/public_files/"
    "Current_Mineral_Tenements_Shapefile.zip"
)

# Historical workings, Corinna–Savage River field (Bottrill 2010, MRT 11).
# (lat, lon) are APPROXIMATE — derived from drainage names, not survey.
GOLD = [
    ("Main Rivulet (+tribs)",     -41.63, 145.12, "600-900 kg est — richest drainage on record"),
    ("Long Plains / Golden Ridge",-41.55, 145.30, "~190 kg; crystalline 'arboriform' gold"),
    ("Rocky River (McGinty)",     -41.58, 145.18, "Tas's two largest nuggets 7.6 + 4.4 kg, 1883"),
    ("Whyte River",               -41.60, 145.16, "5.8 kg RECORDED 1901-1938"),
    ("Middleton Creek",           -41.52, 145.24, "7.9 kg 1935-41; 1.2 kg ~1990 (most recent)"),
    ("Paradise River",            -41.72, 145.18, "nuggets 1-7.5 oz; 1879 rush"),
    ("Nancy/Lucy Creek",          -41.70, 145.15, "1879 Pieman rush cluster"),
    ("Mount Donaldson",           -41.68, 145.20, "named principal working"),
]

TENEMENT_CRS = "EPSG:28355"  # GDA94 / MGA Zone 55 — the dataset's native CRS


def fetch_tenements() -> gpd.GeoDataFrame:
    cache = WORK / "tenements.gpkg"
    if cache.exists():
        print(f"[cache] using {cache}")
        return gpd.read_file(cache)

    print(f"[download] {TENEMENT_ZIP}  (~72 MB, this is the slow bit)")
    r = requests.get(TENEMENT_ZIP, timeout=300)
    r.raise_for_status()

    zf = zipfile.ZipFile(io.BytesIO(r.content))
    shp = next((n for n in zf.namelist() if n.lower().endswith(".shp")), None)
    if not shp:
        sys.exit("No .shp found in the zip — MRT may have changed the layout.")
    zf.extractall(WORK / "raw")
    gdf = gpd.read_file(WORK / "raw" / shp)

    if gdf.crs is None:
        gdf = gdf.set_crs(TENEMENT_CRS)
    gdf.to_file(cache, driver="GPKG")
    print(f"[ok] {len(gdf)} tenement polygons; cached to {cache}")
    return gdf


def main():
    ten = fetch_tenements()
    ten = ten.to_crs(TENEMENT_CRS)

    gold = gpd.GeoDataFrame(
        {"name": [g[0] for g in GOLD], "note": [g[3] for g in GOLD]},
        geometry=[Point(g[2], g[1]) for g in GOLD],
        crs="EPSG:4326",
    ).to_crs(TENEMENT_CRS)

    # Point-in-polygon. Also compute distance to nearest tenement so near-misses
    # (where the approx coord matters) are obvious rather than hidden.
    hit = gpd.sjoin(gold, ten, how="left", predicate="within")

    # try to surface a human-readable tenement label if the columns exist
    label_cols = [c for c in ten.columns
                  if c.lower() in ("tenementi", "tenement", "name", "title",
                                   "status", "type", "holder", "lease_no",
                                   "tenement_n", "tenementno")]

    print("\n" + "=" * 78)
    print("CORINNA–SAVAGE RIVER GOLDFIELD — current mineral-tenement check")
    print("=" * 78)
    for _, row in gold.iterrows():
        within = ten[ten.contains(row.geometry)]
        dist = ten.distance(row.geometry).min()
        if len(within):
            cols = [c for c in label_cols if c in within.columns]
            desc = " | ".join(str(within.iloc[0][c]) for c in cols) if cols else "tenement"
            flag = f"ON TENEMENT  ->  {desc}"
        elif dist < 500:
            flag = f"CLEAR but ~{int(dist)} m from a tenement edge (coord is approx — verify)"
        else:
            flag = f"CLEAR of mineral tenements (nearest ~{int(dist/1000)} km)"
        print(f"\n• {row['name']}")
        print(f"    {row['note']}")
        print(f"    {flag}")

    print("\n" + "-" * 78)
    print("REMINDER: 'CLEAR' = no MINERAL tenement only. You still must check the")
    print("LIST reserve/tenure layer (reserves, parks, conservation, private land)")
    print("and confirm with MRT (info@mrt.tas.gov.au) before prospecting. A")
    print("Prospecting Licence is required outside declared fossicking areas.")
    print("-" * 78)

    out = WORK / "corinna_gold_tenure_result.geojson"
    hit.to_crs("EPSG:4326").to_file(out, driver="GeoJSON")
    print(f"\n[ok] full result written to {out}")
    print("     (load in QGIS, or feed to folium/kepler for a basemap overlay)")


if __name__ == "__main__":
    main()
