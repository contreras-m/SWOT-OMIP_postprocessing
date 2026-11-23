"""Gauss-Seidel NaN filling (replicates DataPreprocessing_listv2.fill_nan,
including the nadir-gap column masking and the fully-NaN column restoration)."""

from __future__ import annotations

import logging
from typing import Dict, Tuple

import numpy as np

logger = logging.getLogger(__name__)


def _make_circular_axis(lon_array: np.ndarray) -> np.ndarray:
    lon = np.mod(lon_array, 360)
    return np.sort(lon)


def fill_nan(datasets: dict, varname: str = "ssh", num_threads: int = 16) -> Tuple[bool, dict]:
    """Fill NaNs in each dataset with pyinterp's Gauss-Seidel solver."""
    import pyinterp
    import pyinterp.fill as fill

    has_converged = True
    filled_datasets = {}
    new_key = 0
    for key in range(len(datasets)):
        data = datasets[key][[varname]]
        latitudes = data["latitude"].values
        longitudes = data["longitude"].values
        values = data[varname].values

        if longitudes.size > 0 and latitudes.size > 0:
            if values.shape[1] >= 34:
                values[:, 33:35] = np.nan

            nan_columns = np.all(np.isnan(values), axis=0)

            lon_sorted = _make_circular_axis(longitudes[0, :])
            x_axis = pyinterp.core.Axis(lon_sorted, is_circle=False)
            y_axis = pyinterp.core.Axis(latitudes[:, 0], is_circle=False)
            grid = pyinterp.Grid2D(y_axis, x_axis, values)
            _has_converged, filled_values = fill.gauss_seidel(grid, num_threads=num_threads)
            has_converged &= _has_converged

            filled_values[:, nan_columns] = np.nan

            datasets[key][varname] = (("num_lines", "num_pixels"), filled_values)
            filled_datasets[new_key] = datasets[key]
            new_key += 1
        else:
            logger.warning("empty lon/lat for dataset number %s", key)

    return has_converged, filled_datasets
