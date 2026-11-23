"""Global boxes and KaRIn swath pass preselection."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import List

import geopandas as gpd
from shapely.geometry import Polygon, shape


@dataclass(frozen=True)
class Box:
    id: int
    polygon: object
    lon_min360: float
    lat_min: float
    lon_max360: float
    lat_max: float

    @property
    def area0360(self):
        return (self.lon_min360, self.lat_min, self.lon_max360, self.lat_max)


def load_boxes(geojson_path) -> List[Box]:
    """Load mostly_ocean_boxes_filtered.geojson; feature order defines the box id."""
    features = json.loads(Path(geojson_path).read_text())["features"]
    boxes = []
    for i, feature in enumerate(features):
        poly = shape(feature["geometry"])
        lon_min, lat_min, lon_max, lat_max = poly.bounds
        boxes.append(
            Box(
                id=i,
                polygon=poly,
                lon_min360=(lon_min + 360) % 360,
                lat_min=lat_min,
                lon_max360=(lon_max + 360) % 360,
                lat_max=lat_max,
            )
        )
    return boxes


def normalize_lon_polygon(geometry):
    """Longitude-normalize a polygon to [-180, 180] (corrected port of
    DataPreprocessing_listv2.normalize_longitude for Polygon geometries)."""
    if isinstance(geometry, Polygon):
        def shift(coords):
            return [((lon + 180) % 360 - 180, lat) for lon, lat in coords]

        exterior = shift(geometry.exterior.coords)
        interiors = [shift(interior.coords) for interior in geometry.interiors]
        return Polygon(exterior, interiors)
    return geometry


def load_swath_geometries(path) -> gpd.GeoDataFrame:
    gdf = gpd.read_file(path)
    gdf["geometry"] = gdf["geometry"].apply(normalize_lon_polygon)
    gdf.crs = "EPSG:4326"
    return gdf


def passes_for_box(swath: gpd.GeoDataFrame, box: Box) -> List[int]:
    """Pass numbers whose KaRIn swath polygon intersects the box polygon."""
    sel = swath[swath.intersects(box.polygon)]
    return sorted({int(v) for v in sel["pass_number"]})
