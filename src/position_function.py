from shapely.geometry import shape, box
import numpy as np
import json
from watermark import watermark

def position_boxes(regcoord):
    # Reading boxes positioxn over the entire global ocean
    roi = {
        "lon_min": -180,
        "lon_max": 180,
        "lat_min": -90,
        "lat_max": 90
    }
    pos_reg=[-180, -90, 180, 90]

    with open("mostly_ocean_boxes_filtered.geojson") as f:
        data = json.load(f)

    roi_poly = box(roi["lon_min"], roi["lat_min"],
               roi["lon_max"], roi["lat_max"])

    selected = [] 

    for feature in data["features"]:
        poly = shape(feature["geometry"])
        if poly.intersects(roi_poly):
            selected.append(poly)

    region_boxes = []

    for i, feature in enumerate(data["features"]):

        coords = feature["geometry"]["coordinates"][0]

        lats = [c[1] for c in coords]
        lons = [c[0] for c in coords]
        lat_center = sum(lats) / len(lats)
        lon_center = sum(lons) / len(lons)
        if (lat_center >=regcoord[2]) & (lat_center <=regcoord[3]) & (lon_center >=regcoord[0]) & (lon_center <=regcoord[1]) :
            region_boxes.append(i)


    return selected, region_boxes


def position_boxes_northsouth(boxesjson):
    
    # Reading boxes position over the entire global ocean

    with open(boxesjson) as f:
        data = json.load(f)


    north_boxes = []
    south_boxes = []

    for i, feature in enumerate(data["features"]):
        coords = feature["geometry"]["coordinates"][0]
        lats = [c[1] for c in coords]
        lat_center = sum(lats) / len(lats)
        if lat_center >= 0:
            north_boxes.append(i)
        else:
            south_boxes.append(i)

    print("North boxes:", len(north_boxes))
    print("South boxes:", len(south_boxes))

    return north_boxes, south_boxes
