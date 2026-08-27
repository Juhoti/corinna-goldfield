#!/usr/bin/env python3
"""
Trove newspaper searches for each target creek.
===============================================
The 1870s-1900s Tasmanian papers (Mercury, Launceston Examiner, Zeehan &
Dundas Herald...) covered the Pieman rushes in week-by-week detail — claim
locations, yields, which creeks were being rushed. Trove (National Library of
Australia) has them digitised and searchable.

Default mode needs no API key: it prints a ready-made Trove search URL for
every target in corinna_targets.geojson (Tasmanian papers, 1870-1949),
plus general field-level searches. Open them in a browser.

With a free API key (https://trove.nla.gov.au/about/create-something/using-api)
in the TROVE_API_KEY environment variable, --api queries Trove directly and
prints the article count and first hits per target.

USAGE
    python3 trove_links.py            # print search URLs (no key needed)
    TROVE_API_KEY=xxx python3 trove_links.py --api
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import urlencode

HERE = Path(__file__).parent
TARGETS = HERE / "corinna_targets.geojson"

# Field-level searches worth running regardless of target
GENERAL_QUERIES = [
    '"Pieman River" gold',
    '"Corinna" gold',
    '"Long Plains" gold Pieman',
    '"Savage River" osmiridium',
]

DECADES = ["187", "188", "189", "190", "191", "192", "193", "194"]


def variants(name):
    """Search-term variants for a target name.
    'Timbs/Longback (The Badger)' -> ['Timbs Creek'... no — split & alias]"""
    out = []
    # alias in parentheses becomes its own variant
    paren = re.findall(r"\(([^)]+)\)", name)
    base = re.sub(r"\([^)]*\)", "", name).strip()
    for part in re.split(r"[/,]", base):
        part = part.strip()
        if part:
            out.append(part)
    out.extend(p.strip() for p in paren if p.strip() and not p.strip().isupper())
    # drop pure annotations like 'N/S/Dredge' fragments of one letter
    return [v for v in out if len(v) > 2]


def search_url(query):
    """Trove web-UI newspaper search: Tasmanian papers, 1870-1949.
    `query` is the full search string, e.g. '"Rocky River" gold'."""
    params = [("keyword", query)] + [("l-decade", d) for d in DECADES]
    params.append(("l-state", "Tasmania"))
    return "https://trove.nla.gov.au/search/category/newspapers?" + urlencode(params)


def api_search(query, key, n=3):
    import requests
    r = requests.get(
        "https://api.trove.nla.gov.au/v3/result",
        params={"q": query, "category": "newspaper",
                "l-state": "Tasmania", "n": n, "encoding": "json",
                "sortby": "dateasc"},
        headers={"X-API-KEY": key}, timeout=60)
    r.raise_for_status()
    cat = r.json()["category"][0]
    total = cat["records"].get("total", 0)
    arts = cat["records"].get("article", [])
    return total, arts


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--api", action="store_true",
                    help="query the Trove API (needs TROVE_API_KEY env var)")
    args = ap.parse_args(argv)

    terms = list(GENERAL_QUERIES)
    if TARGETS.exists():
        data = json.loads(TARGETS.read_text())
        for f in data["features"]:
            for v in variants(f["properties"]["name"]):
                q = f'"{v}" gold'
                if q not in terms:
                    terms.append(q)

    if not args.api:
        print("Trove newspaper searches (Tasmanian papers, 1870-1949) — open in browser:\n")
        for t in terms:
            print(f"  {t}")
            print(f"    {search_url(t)}")
        print("\nTip: add a free API key (TROVE_API_KEY) and rerun with --api for counts.")
        return 0

    key = os.environ.get("TROVE_API_KEY")
    if not key:
        sys.exit("--api needs the TROVE_API_KEY environment variable "
                 "(free: https://trove.nla.gov.au/about/create-something/using-api)")
    for t in terms:
        try:
            total, arts = api_search(t, key)
        except Exception as e:
            print(f"{t:30s} !! {e}")
            continue
        print(f"\n{t}  —  {total} articles")
        for a in arts:
            date = a.get("date", "????")
            title = (a.get("heading") or "").strip()[:70]
            url = a.get("troveUrl", "")
            print(f"    {date}  {title}\n      {url}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
