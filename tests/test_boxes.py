from pathlib import Path

import pytest

from swotomip_spectra.boxes import (
    load_boxes,
    load_swath_geometries,
    normalize_lon_polygon,
    passes_for_box,
)
from shapely.geometry import Polygon

ROOT = Path(__file__).resolve().parents[1]
BOXES = ROOT / "data" / "mostly_ocean_boxes_filtered.geojson"
SWATH = ROOT / "data" / "KaRIn_2kms_science_geometries.geojson"


def test_normalize_polygon_dateline():
    poly = Polygon([(170, -10), (190, -10), (190, 10), (170, 10)])
    norm = normalize_lon_polygon(poly)
    lons = [c[0] for c in norm.exterior.coords]
    assert all(-180 <= x <= 180 for x in lons)
    assert min(lons) < 0


def test_boxes_load_and_dateline_box0():
    boxes = load_boxes(BOXES)
    assert len(boxes) == 282
    box0 = boxes[0]
    assert box0.polygon.bounds[0] == -180
    assert box0.lon_min360 == 180 and box0.lon_max360 == 190
    assert box0.area0360 == (180, -70, 190, -60)


def test_passes_for_box_agulhas_nonempty():
    boxes = load_boxes(BOXES)
    swath = load_swath_geometries(SWATH)
    passes = passes_for_box(swath, boxes[109])
    assert passes
    assert passes == sorted(set(passes))
    assert all(isinstance(p, int) for p in passes)
