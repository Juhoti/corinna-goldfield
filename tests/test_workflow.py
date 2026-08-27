"""Offline tests: analysis logic on synthetic geometry + target-file schema.

No network — the MRT/LIST downloads are exercised only by a real local run.
    pip install pytest && pytest
"""
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


def test_assess_without_layers(targets):
    out = cw.assess(targets, None, None, None)
    assert out.iloc[0]["tenure"] == "unknown"
    assert out.iloc[0]["on_lead"] is None


def test_flag_lead_matches_real_schema():
    """Unit symbols/descriptions as they actually appear in the live 25K layer
    near Corinna — the word 'Tertiary' appears nowhere in the attributes."""
    geol = gpd.GeoDataFrame(
        {"SYMBOL": ["Tsgs", "Tsgra", "Tb", "Lsdh", "Qha"],
         "DESCRIPT": [
             "Interbedded siliceous gravel, quartz sand and clay.",
             "Rounded and angular gravel, mainly vein quartz.",
             "Basalt.",
             "Pale grey and cream, massive, fine-grained dolomite (Corinna Dolomite).",
             "Stream alluvium, swamp and marsh deposits.",
         ]},
        geometry=[square(i * 9000, 0) for i in range(5)],
        crs=MGA55,
    )
    sub = cw.flag_lead(geol)
    assert sorted(sub["SYMBOL"]) == ["Tsgra", "Tsgs"]


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


def test_known_outlier_is_flagged():
    """Main Rivulet's grid ref is ambiguous in the source and currently plots
    ~87 km south of the field. Until it's re-located on LISTmap, the sanity
    check must keep flagging it. When the coordinate is fixed, flip this test
    to assert `bad == []`."""
    tgt = gpd.read_file(TARGET_FILE).to_crs(MGA55)
    bad = cw.flag_outliers(tgt)
    assert [n for n, _ in bad] == ["Main Rivulet"]
