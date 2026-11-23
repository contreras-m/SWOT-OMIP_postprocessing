import numpy as np
import pytest
import xarray as xr

from swotomip_spectra.readers import _box_mask, normalize_longitude_values


def _dataset(lon_values, lat_value=15.0):
    n = len(lon_values)
    lon = xr.DataArray(np.array(lon_values, dtype=float).reshape(1, n), dims=("num_lines", "num_pixels"))
    lat = xr.DataArray(np.full((1, n), lat_value), dims=("num_lines", "num_pixels"))
    return xr.Dataset(
        {"ssh": (("num_lines", "num_pixels"), np.ones((1, n)))},
        coords={"longitude": lon, "latitude": lat},
    )


def test_normalize_minus180_to_0360():
    lon = xr.DataArray(np.array([-10.0, 5.0, 170.0, 180.0, -180.0]), dims="x")
    norm = normalize_longitude_values(lon, "-180_180")
    assert list(norm.values) == [350.0, 5.0, 170.0, 180.0, 180.0]


def test_mask_normal_box():
    ds = _dataset([5.0, 15.0, 30.0])
    mask = _box_mask(ds, (10.0, 0.0, 20.0, 30.0))
    assert list(mask.values.ravel()) == [False, True, False]


def test_mask_dateline_box_wrap():
    ds = _dataset([355.0, 5.0, 100.0])
    area = (350.0, 0.0, 10.0, 30.0)
    mask = _box_mask(ds, area)
    assert list(mask.values.ravel()) == [True, True, False]


def test_mask_uses_360_convention():
    ds = _dataset([350.0, 5.0])
    ds360 = ds.assign_coords(longitude=normalize_longitude_values(ds["longitude"], "-180_180"))
    area = (350.0, 0.0, 10.0, 30.0)
    mask = _box_mask(ds360, area)
    assert list(mask.values.ravel()) == [True, True]
