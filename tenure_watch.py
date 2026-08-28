#!/usr/bin/env python3
"""
Tenure watcher — notices when ground opens (or closes).
=======================================================
Snapshots the tenure state of every target plus a watchlist of licences into
`tenure_state.json` (committed to the repo). On each run it re-downloads the
daily MRT tenement layer, compares against the committed state, and if
anything changed writes a human-readable `tenure_diff.md` and updates the
state file.

The GitHub Action in .github/workflows/tenure-watch.yml runs this weekly,
commits the state, and opens an issue with the diff — so the December 2026
lapses (EL25/2020 on the 2nd, EL7/2021 on the 21st) announce themselves.

What counts as a change:
  - a target's tenure flips (ON TENEMENT <-> clear) — the headline event
  - the set of tenements over a target changes
  - a watched tenement disappears from the layer (lapsed / surrendered)
  - a watched tenement's expiry date moves (renewal), or owner/status change

USAGE
    python3 tenure_watch.py               # fresh download (what CI does)
    python3 tenure_watch.py --no-refresh  # reuse work/tenements.gpkg cache
First run writes the baseline state and no diff.
"""
import argparse
import json
import sys
from pathlib import Path

import pandas as pd
import geopandas as gpd

from corinna_workflow import fetch_tenements, MGA55, _text

HERE = Path(__file__).parent
TARGETS = HERE / "corinna_targets.geojson"
STATE_FILE = HERE / "tenure_state.json"
DIFF_FILE = HERE / "tenure_diff.md"

# Licences we care about even before/after they cover a target.
WATCHLIST = ["EL25/2020", "EL7/2021", "EL2/2018", "EL30/2003",
             "25M/2003", "2M/2001", "ERA9999"]


def snapshot(refresh=True):
    """Current tenure state: per-target coverage + watched tenement records."""
    ten = fetch_tenements(refresh)
    if ten is None:
        sys.exit("tenement download failed — no diff produced")
    ten = ten.to_crs(MGA55)
    tgt = gpd.read_file(TARGETS).to_crs(MGA55)

    state = {"targets": {}, "tenements": {}}
    interest = set(WATCHLIST)
    for _, r in tgt.iterrows():
        if r.geometry is None:
            continue
        within = ten[ten.contains(r.geometry)]
        names = sorted({str(w["NAME"]) for _, w in within.iterrows()})
        state["targets"][r["name"]] = {
            "tenure": "ON TENEMENT" if len(within) else "clear",
            "tenements": names,
        }
        interest.update(names)

    for nm in sorted(interest):
        rows = ten[ten["NAME"].astype(str) == nm]
        if not len(rows):
            state["tenements"][nm] = None      # gone from the layer
            continue
        r0 = rows.iloc[0]
        exp = r0.get("EXPIREDATE")
        state["tenements"][nm] = {
            "type": _text(r0, "TENEMENTTY"),
            "owner": _text(r0, "OWNER"),
            "status": _text(r0, "STATUS"),
            "expires": str(exp)[:10] if pd.notna(exp) else None,
        }
    return state


def diff_states(old, new):
    """Human-readable change lines between two snapshots. [] = no change."""
    lines = []
    for name, cur in new["targets"].items():
        prev = old.get("targets", {}).get(name)
        if prev is None:
            lines.append(f"- NEW TARGET tracked: **{name}** — {cur['tenure']}")
            continue
        if prev["tenure"] != cur["tenure"]:
            if cur["tenure"] == "clear":
                lines.append(f"- 🎉 **GROUND OPENED: {name}** is now CLEAR of "
                             f"tenements (was on {', '.join(prev['tenements'])})")
            else:
                lines.append(f"- ⚠ **{name}** is now ON TENEMENT "
                             f"({', '.join(cur['tenements'])}) — was clear")
        elif prev["tenements"] != cur["tenements"]:
            lines.append(f"- **{name}**: tenements changed "
                         f"{prev['tenements']} → {cur['tenements']}")
    for name in old.get("targets", {}):
        if name not in new["targets"]:
            lines.append(f"- target no longer tracked: {name}")

    for nm, cur in new["tenements"].items():
        prev = old.get("tenements", {}).get(nm, "ABSENT")
        if prev == "ABSENT":
            lines.append(f"- new tenement tracked: **{nm}** ({fmt_ten(cur)})")
        elif prev is None and cur is not None:
            lines.append(f"- **{nm}** has REAPPEARED in the layer ({fmt_ten(cur)})")
        elif cur is None and prev is not None:
            lines.append(f"- 🎉 **{nm} is GONE from the tenement layer** — "
                         f"lapsed or surrendered (was {fmt_ten(prev)}). "
                         f"Verify on the MRT register, then re-run the workflow.")
        elif prev != cur:
            for k in ("expires", "owner", "status", "type"):
                if (prev or {}).get(k) != (cur or {}).get(k):
                    lines.append(f"- **{nm}** {k}: {(prev or {}).get(k)} → "
                                 f"{(cur or {}).get(k)}"
                                 + (" (RENEWED?)" if k == "expires" else ""))
    return lines


def fmt_ten(t):
    if not t:
        return "?"
    return " · ".join(str(v) for v in (t.get("type"), t.get("owner"),
                                       f"expires {t.get('expires')}") if v)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--no-refresh", action="store_true",
                    help="reuse the cached tenement layer instead of downloading")
    args = ap.parse_args(argv)

    DIFF_FILE.unlink(missing_ok=True)
    new = snapshot(refresh=not args.no_refresh)

    if not STATE_FILE.exists():
        STATE_FILE.write_text(json.dumps(new, indent=1, sort_keys=True) + "\n")
        print(f"[baseline] {STATE_FILE.name} written — no diff on first run")
        return 0

    old = json.loads(STATE_FILE.read_text())
    lines = diff_states(old, new)
    if not lines:
        print("[ok] no tenure changes")
        return 0

    body = ("## Corinna tenure change detected\n\n" + "\n".join(lines)
            + "\n\nNext step: `python3 corinna_workflow.py --refresh` for the "
              "full picture, and verify on the MRT tenement register before "
              "acting on it.\n")
    DIFF_FILE.write_text(body)
    STATE_FILE.write_text(json.dumps(new, indent=1, sort_keys=True) + "\n")
    print(body)
    print(f"[!] changes -> {DIFF_FILE.name}; state updated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
