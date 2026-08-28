#!/usr/bin/env python3
"""
Locate named creeks from the LIST hydrography layer.
====================================================
The 1880s reports name creeks that appear in no modern mining appendix
(Hangmans, Longback, ...). Many of those names SURVIVE in the LIST
'Rivers Streams and Creeks' layer — this queries it by name, clipped to the
Corinna field, and reports where each creek actually runs.

This is how the Main Rivulet position was fixed (the source grid ref plotted
~87 km south of the field; the real creek runs NE of Corinna) and how the
formerly archival-only Hangmans and Longback targets got coordinates.

USAGE
    python3 locate_creeks.py                      # the default archival names
    python3 locate_creeks.py "Sabbath Creek" "Specimen Creek"
    python3 locate_creeks.py --geojson creeks.geojson "Hangmans Creek"

Names are exact matches against the layer's NAME field (case-insensitive);
add --like for substring search. A name found OUTSIDE the bbox is reported
too, flagged, since Tasmanian creek names repeat across the state.
"""
import argparse
import json
import sys

import requests

HYDRO_LAYER = ("https://services.thelist.tas.gov.au/arcgis/rest/services/"
               "Public/TopographyAndRelief/MapServer/15")

# lon/lat box around the Corinna-Pieman field, with generous margin
FIELD_BBOX = (144.85, -41.90, 145.45, -41.40)

DEFAULT_NAMES = ["Hangmans Creek", "Longback Creek", "Sunday Creek",
                 "Main Rivulet", "Frenchman Creek", "None Such Creek",
                 "White Creek", "Lucy Creek"]


def query(names, bbox=None, like=False):
    """Return {name: [feature, ...]} from the hydrography layer."""
    if like:
        clauses = [f"UPPER(NAME) LIKE '%{n.upper()}%'" for n in names]
        where = " OR ".join(clauses)
    else:
        quoted = ",".join("'" + n.replace("'", "''") + "'" for n in names)
        where = f"NAME IN ({quoted})"
    params = {"where": where, "outFields": "NAME", "outSR": "4326",
              "returnGeometry": "true", "f": "geojson"}
    if bbox:
        params.update({"geometry": ",".join(f"{v:.5f}" for v in bbox),
                       "geometryType": "esriGeometryEnvelope", "inSR": "4326"})
    r = requests.get(f"{HYDRO_LAYER}/query", params=params, timeout=120)
    r.raise_for_status()
    out = {}
    for f in r.json().get("features", []):
        out.setdefault(f["properties"]["NAME"], []).append(f)
    return out


def summarise(features):
    """(centre_lon, centre_lat, extent) of a list of line features."""
    coords = []
    for f in features:
        geom = f["geometry"]
        parts = [geom["coordinates"]] if geom["type"] == "LineString" \
            else geom["coordinates"]
        for part in parts:
            coords.extend(part)
    xs = [c[0] for c in coords]
    ys = [c[1] for c in coords]
    return (sum(xs) / len(xs), sum(ys) / len(ys),
            (min(xs), min(ys), max(xs), max(ys)))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("names", nargs="*", default=DEFAULT_NAMES,
                    help="creek names to look up (default: the archival set)")
    ap.add_argument("--like", action="store_true",
                    help="substring match instead of exact name")
    ap.add_argument("--geojson", metavar="FILE",
                    help="also write the matched creek lines to FILE")
    ap.add_argument("--statewide", action="store_true",
                    help="search all of Tasmania, not just the field bbox")
    args = ap.parse_args(argv)
    names = args.names or DEFAULT_NAMES

    bbox = None if args.statewide else FIELD_BBOX
    found = query(names, bbox=bbox, like=args.like)

    all_feats = []
    for nm in names:
        matches = ([v for k, v in found.items() if nm.lower() in k.lower()]
                   if args.like else [found.get(nm)] if nm in found else [])
        matches = [m for m in matches if m]
        if not matches and not args.like:
            # not in hydrography under that name: try the placenames register
            # (curated aliases + spelling variants), then re-query
            try:
                from placenames import resolve
                registered, note, _ = resolve(nm, bbox=bbox)
            except Exception:
                registered, note = None, "register lookup failed"
            if registered and registered != nm:
                refound = query([registered], bbox=bbox)
                if registered in refound:
                    print(f"{nm:22s} -> {registered}  ({note})")
                    matches = [refound[registered]]
            if not matches:
                print(f"{nm:22s} NOT FOUND — {note}")
                continue
        elif not matches:
            where = "Tasmania" if args.statewide else "the field bbox"
            print(f"{nm:22s} NOT FOUND in {where}"
                  + ("" if args.statewide else "  (try --statewide)"))
            continue
        for feats in matches:
            cx, cy, ext = summarise(feats)
            label = feats[0]["properties"]["NAME"]
            print(f"{label:22s} centre ~ {cx:.4f}, {cy:.4f}   "
                  f"runs {ext[0]:.3f}..{ext[2]:.3f} E, {ext[1]:.3f}..{ext[3]:.3f} S "
                  f"({len(feats)} segments)")
            all_feats.extend(feats)

    if args.geojson and all_feats:
        with open(args.geojson, "w") as fh:
            json.dump({"type": "FeatureCollection", "features": all_feats}, fh)
        print(f"\n[ok] {args.geojson} written — load in QGIS over a topo basemap")
    return 0


if __name__ == "__main__":
    sys.exit(main())
