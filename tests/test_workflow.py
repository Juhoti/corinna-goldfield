"""Offline tests: analysis logic on synthetic geometry + target-file schema.

No network — the MRT/LIST downloads are exercised only by a real local run.
    pip install pytest && pytest
"""
import json
import sys
from pathlib import Path

import geopandas as gpd
import pytest
from shapely.geometry import Point, box

sys.path.insert(0, str(Path(__file__).parent.parent))
import corinna_workflow as cw

MGA55 = cw.MGA55


def square(x, y, half=1000):
    return box(x - half, y - half, x + half, y + half)


@pytest.fixture
def targets():
    return gpd.GeoDataFrame(
        {"name": ["on-everything", "clear-near", "archival"],
         "tier": [1, 3, 3],
         "yield": ["a", "b", "c"],
         "history": ["h", "h", "h"],
         "lead": [None, None, None],
         "approx": [False, False, True]},
        geometry=[Point(0, 0), Point(5000, 0), None],
        crs=MGA55,
    )


def test_assess_flags(targets):
    ten = gpd.GeoDataFrame(
        {"NAME": ["EL1/2020"], "TENEMENTTY": ["Exploration Licence"],
         "OWNER": ["Acme Pty Ltd"]},
        geometry=[square(0, 0)], crs=MGA55)
    lead = gpd.GeoDataFrame(geometry=[square(0, 0)], crs=MGA55)
    res = gpd.GeoDataFrame(
        {"RES_NAME": ["Test State Reserve"],
         "MINING": ["Not available under the MRDA"]},
        geometry=[square(0, 0)], crs=MGA55)
    out = cw.assess(targets, ten, lead, res)

    r0 = out.iloc[0]
    assert r0["tenure"] == "ON TENEMENT"
    assert r0["tenements"] == "EL1/2020 — Exploration Licence — Acme Pty Ltd"
    assert r0["on_lead"] is True
    assert r0["reserve"] == "Test State Reserve"
    assert "Not available" in r0["reserve_mining"]

    r1 = out.iloc[1]  # 5 km away: clear of the 1 km square, 4 km to its edge
    assert r1["tenure"] == "clear"
    assert r1["tenure_dist_m"] == 4000
    assert r1["on_lead"] is False
    assert r1["lead_dist_m"] == 4000
    assert r1["reserve"] is None

    r2 = out.iloc[2]  # no coordinate
    assert "archival" in r2["tenure"]
    assert r2["on_lead"] is None


def occ_frame():
    return gpd.GeoDataFrame(
        {"NAME": ["Old Adit", "Unnamed", "Far Working"],
         "COMMODITYS": ["Gold", "Gold", "Gold"],
         "STATUS": ["Abandoned", "Mineralised", "Mineralised"],
         "LOC_ACC": [100.0, 100.0, 100.0],
         "lon": [145.1, 145.1, 145.2], "lat": [-41.6, -41.6, -41.7]},
        geometry=[Point(200, 0), Point(600, 0), Point(20000, 0)],
        crs=MGA55)


def test_assess_workings(targets):
    out = cw.assess(targets, None, None, None, occ_frame())
    r0 = out.iloc[0]  # at origin: two workings within 750m
    assert r0["workings_near"] == 2
    assert r0["nearest_working"] == "Old Adit"
    assert r0["nearest_working_m"] == 200


def test_new_candidates(targets):
    named, unnamed = cw.new_candidates(occ_frame(), targets)
    # only Far Working is >750m from every target (clear-near target is at x=5000)
    assert [o["NAME"] for o, _ in named] == ["Far Working"]
    assert unnamed == 0
    assert named[0][1] == 15000  # 20000 - 5000 from the nearest target


def test_tenure_short():
    assert cw._tenure_short({"tenure": "clear", "tenements": None}) == "OPEN"
    assert cw._tenure_short({"tenure": "ON TENEMENT",
                             "tenements": "ERA9999 — Exploration Release Area"}) == "released"
    assert cw._tenure_short(
        {"tenure": "ON TENEMENT",
         "tenements": "EL2/2018 — Exploration Licence — Georgina"}) == "EL2/2018"


def test_assess_occurrences_reused(targets):
    """assess() must work on the occurrences frame (no target columns)."""
    ten = gpd.GeoDataFrame(
        {"NAME": ["EL1/2020"], "TENEMENTTY": ["Exploration Licence"],
         "OWNER": ["Acme Pty Ltd"]},
        geometry=[square(0, 0)], crs=MGA55)
    out = cw.assess(occ_frame(), ten, None, None)
    assert out.iloc[0]["tenure"] == "ON TENEMENT"      # working at x=200
    assert out.iloc[2]["tenure"] == "clear"            # working at x=20000


def test_assess_without_layers(targets):
    out = cw.assess(targets, None, None, None)
    assert out.iloc[0]["tenure"] == "unknown"
    assert out.iloc[0]["on_lead"] is None


def test_flag_lead_matches_real_schema():
    """Unit symbols/descriptions as they actually appear in the live 25K layer
    near Corinna — the word 'Tertiary' appears nowhere in the attributes."""
    geol = gpd.GeoDataFrame(
        {"SYMBOL": ["Tsgs", "Tsgra", "Tb", "Lsdh", "Qha", "Qhag", "Tcbc"],
         "DESCRIPT": [
             "Interbedded siliceous gravel, quartz sand and clay.",
             "Rounded and angular gravel, mainly vein quartz.",
             "Basalt.",
             "Pale grey and cream, massive, fine-grained dolomite (Corinna Dolomite).",
             "Stream alluvium, swamp and marsh deposits.",
             "Alluvial gravel of modern streams.",   # Quaternary — must NOT match
             "Basal conglomerate and gravel.",       # Tertiary + gravel — matches
         ]},
        geometry=[square(i * 9000, 0) for i in range(7)],
        crs=MGA55,
    )
    sub = cw.flag_lead(geol)
    assert sorted(sub["SYMBOL"]) == ["Tcbc", "Tsgra", "Tsgs"]


def test_flag_lead_missing_columns():
    geol = gpd.GeoDataFrame({"code": [1, 2]},
                            geometry=[square(0, 0), square(9000, 0)], crs=MGA55)
    assert len(cw.flag_lead(geol)) == 0


def test_flag_outliers_catches_distant_point():
    pts = gpd.GeoDataFrame(
        {"name": ["a", "b", "c", "far"]},
        geometry=[Point(0, 0), Point(1000, 0), Point(0, 1000), Point(0, 90_000)],
        crs=MGA55,
    )
    bad = cw.flag_outliers(pts)
    assert [n for n, _ in bad] == ["far"]


def test_field_bbox_excludes_outliers():
    pts = gpd.GeoDataFrame(
        {"name": ["a", "b", "far"]},
        geometry=[Point(145.1, -41.6), Point(145.2, -41.7), Point(145.16, -42.4)],
        crs="EPSG:4326",
    )
    minx, miny, maxx, maxy = cw.field_bbox(pts, {"far"})
    assert miny > -41.8  # the -42.4 outlier must not drag the box south


# ---- placenames resolver ----------------------------------------------------

def test_name_variants():
    import placenames as pn
    assert pn.name_variants("Frenchmans Creek") == ["Frenchmans Creek",
                                                    "Frenchman Creek"]
    assert pn.name_variants("Middleton Creek") == ["Middleton Creek"]
    # generic words (plains, creek...) keep their s
    assert pn.name_variants("Brown Plains Creek") == ["Brown Plains Creek"]


def test_distinctive_token():
    import placenames as pn
    assert pn.distinctive_token("Frenchmans Creek") == "Frenchman"
    assert pn.distinctive_token("The Badger") == "Badger"
    assert pn.distinctive_token("Main Rivulet") == "Main"


def test_alias_file_resolution():
    import placenames as pn
    aliases = pn.load_aliases()
    assert aliases["Sabbath Creek"] == "Sunday Creek"
    assert aliases["Whyte Creek"] == "White Creek"
    assert aliases["Nonesuch Creek"] == "None Such Creek"
    resolved, note, _ = pn.resolve("Sabbath Creek", aliases=aliases)
    assert resolved == "Sunday Creek"
    assert "alias" in note


# ---- reach analysis ---------------------------------------------------------

def test_classify_matches():
    import reach_analysis as ra
    assert ra.classify_matches([]) == "OPEN"
    assert ra.classify_matches([("LICENCES", "ERA9999")]) == "released"
    assert ra.classify_matches([("LICENCES", "EL25/2020")]) == "dec:EL25/2020"
    assert ra.classify_matches([("LICENCES", "EL2/2018")]) == "held:EL2/2018"
    assert ra.classify_matches([("LEASES", "25M/2003")]) == "held:25M/2003"
    assert ra.classify_matches(
        [("UNAVAILABLE_AREAS", "State Reserve")]) == "unavailable"
    assert ra.classify_matches(
        [("UNAVAILABLE_AREAS", "MRT Defined Areas - Fossick Areas")]) == "fossick"
    # worst-wins stacking: EL over released ground is held
    assert ra.classify_matches(
        [("LICENCES", "ERA9999"), ("LICENCES", "EL2/2018")]) == "held:EL2/2018"
    # a dec licence over ERA ground is still the December window
    assert ra.classify_matches(
        [("LICENCES", "ERA9999"), ("LICENCES", "EL25/2020")]) == "dec:EL25/2020"


def test_runs():
    import reach_analysis as ra
    assert ra.runs(["a", "a", "b", "a"]) == [(0, 1, "a"), (2, 2, "b"), (3, 3, "a")]
    assert ra.runs(["x"]) == [(0, 0, "x")]


def test_classify_line_and_reaches():
    import reach_analysis as ra
    from shapely.geometry import LineString
    line = LineString([(0, 0), (10000, 0)])   # 10 km west-east creek
    # a tenement over the middle 2 km; lead polygon under the first 3 km
    ten = gpd.GeoDataFrame({"layer": ["LICENCES"], "NAME": ["EL2/2018"]},
                           geometry=[box(4000, -500, 6000, 500)], crs=MGA55)
    lead = gpd.GeoDataFrame(geometry=[box(0, -500, 3000, 500)], crs=MGA55)
    ds, labels = ra.classify_line(line, ten, lead, None)
    recs = ra.reaches_for_line("Test Creek", 0, line, labels, ds)
    prime = [r for r in recs if r["prime"]]
    assert len(prime) == 1
    # open + lead-fed = first ~3 km (plus the 150 m lead-near margin)
    assert 2900 <= prime[0]["length_m"] <= 3400
    held = [r for r in recs if r["access"] == "held:EL2/2018"]
    assert held and 1800 <= held[0]["length_m"] <= 2200
    assert sum(r["length_m"] for r in recs) >= 9500  # covers ~whole line


# ---- tenure watcher ---------------------------------------------------------

def test_diff_states():
    import tenure_watch as tw
    old = {"targets": {"Frenchmans Creek": {"tenure": "ON TENEMENT",
                                            "tenements": ["EL25/2020"]}},
           "tenements": {"EL25/2020": {"type": "Exploration Licence",
                                       "owner": "Georgina Resources Pty Ltd",
                                       "status": "Granted",
                                       "expires": "2026-12-02"}}}
    # no change
    assert tw.diff_states(old, json.loads(json.dumps(old))) == []
    # the December event: licence gone, target now clear
    new = {"targets": {"Frenchmans Creek": {"tenure": "clear", "tenements": []}},
           "tenements": {"EL25/2020": None}}
    lines = tw.diff_states(old, new)
    assert any("GROUND OPENED" in l and "Frenchmans" in l for l in lines)
    assert any("GONE from the tenement layer" in l for l in lines)
    # renewal: expiry moves
    renewed = json.loads(json.dumps(old))
    renewed["tenements"]["EL25/2020"]["expires"] = "2031-12-02"
    lines = tw.diff_states(old, renewed)
    assert any("expires" in l and "RENEWED" in l for l in lines)
    # new tenement over a target
    grabbed = json.loads(json.dumps(old))
    grabbed["targets"]["Frenchmans Creek"]["tenements"] = ["EL25/2020", "EL9/2026"]
    assert any("tenements changed" in l for l in tw.diff_states(old, grabbed))


def test_watch_state_matches_targets():
    """Committed baseline must track every target with a coordinate."""
    import tenure_watch as tw
    if not tw.STATE_FILE.exists():
        pytest.skip("no baseline committed yet")
    state = json.loads(tw.STATE_FILE.read_text())
    tgt = gpd.read_file(TARGET_FILE)
    assert set(state["targets"]) == set(tgt[tgt.geometry.notna()]["name"])
    for nm in tw.WATCHLIST:
        assert nm in state["tenements"]


# ---- the real target file ---------------------------------------------------

TARGET_FILE = Path(__file__).parent.parent / "corinna_targets.geojson"


def test_targets_schema():
    tgt = gpd.read_file(TARGET_FILE)
    assert len(tgt) > 0
    for col in ["name", "tier", "yield", "history", "lead", "approx"]:
        assert col in tgt.columns, f"missing property: {col}"
    assert tgt["name"].notna().all()
    assert set(tgt["tier"]) <= {1, 2, 3}
    assert not tgt["name"].duplicated().any()


def test_targets_within_tasmania():
    tgt = gpd.read_file(TARGET_FILE)
    pts = tgt[tgt.geometry.notna()]
    assert pts.geometry.x.between(143.5, 149).all()
    assert pts.geometry.y.between(-44, -40).all()


def test_no_outliers_in_targets():
    """Main Rivulet's ambiguous source grid ref used to plot ~87 km south of
    the field; its position (and Hangmans/Longback's) is now derived from the
    LIST hydrography centrelines, so no target should trip the sanity check."""
    tgt = gpd.read_file(TARGET_FILE).to_crs(MGA55)
    assert cw.flag_outliers(tgt) == []


def test_all_targets_have_coordinates():
    """The formerly archival-only creeks were located via LIST hydrography."""
    tgt = gpd.read_file(TARGET_FILE)
    assert tgt.geometry.notna().all()


def test_trove_variants():
    import trove_links as tl
    assert tl.variants("Rocky River") == ["Rocky River"]
    assert tl.variants("Timbs/Longback (The Badger)") == \
        ["Timbs", "Longback", "The Badger"]
    assert "Nancy Creek" in tl.variants("Nancy Creek")


def test_trove_search_url_shape():
    import trove_links as tl
    url = tl.search_url('"Rocky River" gold')
    assert url.startswith("https://trove.nla.gov.au/search/category/newspapers?")
    assert "l-state=Tasmania" in url
    assert "keyword=%22Rocky+River%22+gold&" in url


def test_locate_creeks_summarise():
    import locate_creeks as lc
    feats = [
        {"geometry": {"type": "LineString",
                      "coordinates": [[145.0, -41.5], [145.2, -41.7]]}},
        {"geometry": {"type": "MultiLineString",
                      "coordinates": [[[145.1, -41.6], [145.3, -41.8]]]}},
    ]
    cx, cy, ext = lc.summarise(feats)
    assert abs(cx - 145.15) < 1e-9
    assert ext == (145.0, -41.8, 145.3, -41.5)
