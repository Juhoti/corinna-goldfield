#!/usr/bin/env python3
"""
Placenames Tasmania register access and historical-name resolution.
===================================================================
The LIST "Named Features" layer carries the registered nomenclature,
including superseded and unofficial names. Several creeks in the 1880s
mining record appear on the modern map under different spellings or under a
different name entirely (Sabbath Creek's registered hydrography name is its
1879 name, Sunday Creek). This module resolves historical names to
registered ones, so the other tools can query the hydrography layer with
names that actually match.

Resolution order:
  1. curated aliases (creek_aliases.json) — renames that cannot be guessed
  2. the name as given
  3. possessive-s variants (Frenchmans -> Frenchman)
  4. a LIKE search on the distinctive token against the register

USAGE (as a tool)
    python3 placenames.py "Sabbath Creek" "Whyte Creek"
    python3 placenames.py --search "%MCGINTY%"     # raw register search
"""
import argparse
import json
import re
import sys
from pathlib import Path

import requests

HERE = Path(__file__).parent
ALIASES_FILE = HERE / "creek_aliases.json"
REGISTER_LAYER = ("https://services.thelist.tas.gov.au/arcgis/rest/services/"
                  "Public/SearchService/MapServer/0")
FIELD_BBOX = (144.98, -41.92, 145.56, -41.34)

GENERIC = {"creek", "river", "rivulet", "hill", "ridge", "plains", "plain",
           "the", "spur", "mount", "mt"}


def load_aliases():
    if ALIASES_FILE.exists():
        return json.loads(ALIASES_FILE.read_text())
    return {}


def name_variants(name):
    """Spelling variants worth trying, most specific first."""
    out = [name]
    words = name.split()
    for i, w in enumerate(words):
        if w.lower() not in GENERIC and w.endswith("s") and len(w) > 3:
            out.append(" ".join(words[:i] + [w[:-1]] + words[i + 1:]))
    return out


def distinctive_token(name):
    for w in name.split():
        if w.lower() not in GENERIC:
            return re.sub(r"s$", "", w)
    return name.split()[0]


def search_register(where, bbox=FIELD_BBOX, timeout=120):
    """Raw query against the Named Features layer. Returns
    [{name, type, reg_no, lat, lon}] (lat/lon = feature extent centre)."""
    params = {"where": where, "outFields": "NAME,TYPE,NOM_REG_NO",
              "outSR": "4326", "returnGeometry": "true", "f": "geojson"}
    if bbox:
        params.update({"geometry": ",".join(f"{v:.4f}" for v in bbox),
                       "geometryType": "esriGeometryEnvelope", "inSR": "4326"})
    r = requests.get(f"{REGISTER_LAYER}/query", params=params, timeout=timeout)
    r.raise_for_status()
    out = []
    for f in r.json().get("features", []):
        coords = []
        geom = f.get("geometry") or {}
        rings = geom.get("coordinates", [])
        if geom.get("type") == "Polygon":
            coords = rings[0]
        elif geom.get("type") == "MultiPolygon":
            coords = [c for poly in rings for c in poly[0]]
        lat = lon = None
        if coords:
            lon = sum(c[0] for c in coords) / len(coords)
            lat = sum(c[1] for c in coords) / len(coords)
        p = f["properties"]
        out.append({"name": p.get("NAME"), "type": p.get("TYPE"),
                    "reg_no": p.get("NOM_REG_NO"),
                    "lat": round(lat, 4) if lat else None,
                    "lon": round(lon, 4) if lon else None})
    return out


def _quote(n):
    return "'" + n.replace("'", "''").upper() + "'"


def resolve(name, bbox=FIELD_BBOX, aliases=None):
    """Resolve a (possibly historical) name to registered candidates.
    Returns (resolved_name_or_None, note, candidates)."""
    aliases = load_aliases() if aliases is None else aliases
    if name in aliases:
        return aliases[name], f"curated alias -> {aliases[name]}", []
    variants = name_variants(name)
    hits = search_register(
        "UPPER(NAME) IN (" + ",".join(_quote(v) for v in variants) + ")", bbox)
    if hits:
        exact = next((h for h in hits if h["name"].upper() == name.upper()), None)
        chosen = exact or hits[0]
        note = ("registered as given" if exact
                else f"registered spelling -> {chosen['name']}")
        return chosen["name"].title(), note, hits
    token = distinctive_token(name).upper()
    like = search_register(f"UPPER(NAME) LIKE '%{token}%'", bbox)
    if like:
        return None, f"no registration; register has similar: " + \
            ", ".join(sorted({h["name"] for h in like})[:5]), like
    return None, "no match in the register for this area", []


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("names", nargs="*", help="names to resolve")
    ap.add_argument("--search", metavar="LIKE",
                    help="raw LIKE pattern against the register (e.g. '%%MCGINTY%%')")
    ap.add_argument("--statewide", action="store_true")
    args = ap.parse_args(argv)
    bbox = None if args.statewide else FIELD_BBOX

    if args.search:
        for h in search_register(f"UPPER(NAME) LIKE '{args.search.upper()}'", bbox):
            print(f"  {h['name']:40s} {h['type'] or '':18s} "
                  f"{h['lat']},{h['lon']}  reg {h['reg_no']}")
        return 0
    if not args.names:
        ap.error("give names to resolve, or --search")
    for nm in args.names:
        resolved, note, _ = resolve(nm, bbox)
        print(f"{nm:26s} -> {resolved or '(unresolved)':26s} {note}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
