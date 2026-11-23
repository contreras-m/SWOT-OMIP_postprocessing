"""Pass-file loading with spatial subsetting (replicates DataPreprocessing_listv2
read_swot_ncfiles_S3folder_list / read_swot_ncfiles_local_list, with an explicit
longitude-convention normalization step)."""

from __future__ import annotations

import logging
from typing import Dict, Optional, Sequence, Tuple

import xarray as xr

logger = logging.getLogger(__name__)

DROP_VARS = ["i_num_line", "i_num_pixel"]


def normalize_longitude_values(longitude: xr.DataArray, convention: str) -> xr.DataArray:
    if convention == "0_360":
        return longitude
    if convention == "-180_180":
        return xr.where(longitude < 0, longitude + 360, longitude)
    raise ValueError(f"unknown lon_convention {convention!r}")


def _box_mask(ds: xr.Dataset, area0360: Tuple[float, float, float, float]) -> xr.DataArray:
    lon_min, lat_min, lon_max, lat_max = area0360
    longitude = ds["longitude"]
    latitude = ds["latitude"]
    if lon_min < lon_max:
        lon_selection = (longitude >= lon_min) & (longitude <= lon_max)
    else:
        lon_selection = ((longitude >= lon_min) & (longitude <= 360)) | (longitude <= lon_max)
    lat_selection = (latitude >= lat_min) & (latitude <= lat_max)
    return lat_selection & lon_selection


def load_pass_datasets(
    files: Sequence[str],
    area0360: Tuple[float, float, float, float],
    lon_convention: str = "0_360",
    fs=None,
    engine: str = "h5netcdf",
) -> Dict[int, xr.Dataset]:
    """Open each file, normalize longitudes to the box convention, keep only
    in-box data. Mirrors the production reader, including its wrap-around
    handling for dateline boxes (lon_min > lon_max pre-shift)."""
    datasets = {}
    opener = (lambda f: fs.open(f, mode="rb")) if fs is not None else open
    for path in files:
        try:
            with opener(path) as fileobj:
                ds = xr.open_dataset(fileobj, engine=engine)
                ds = ds.drop_vars(DROP_VARS, errors="ignore")
                if "latitude" not in ds or "longitude" not in ds:
                    logger.warning("no lat/lon in %s", path)
                    ds.close()
                    continue
                ds["longitude"] = normalize_longitude_values(ds["longitude"], lon_convention)
                mask = _box_mask(ds, area0360)
                if not mask.any():
                    logger.debug("out of box %s: %s", area0360, path)
                    ds.close()
                    continue
                ds = ds.where(mask, drop=True)
                if ds["latitude"].size == 0 or ds["longitude"].size == 0:
                    logger.debug("empty after region filtering: %s", path)
                    ds.close()
                    continue
                datasets[len(datasets)] = ds
        except Exception as exc:
            logger.warning("failed to process %s: %s", path, exc)
            continue
    return datasets
