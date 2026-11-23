"""Gauss-Seidel NaN filling (replicates DataPreprocessing_listv2.fill_nan,
including the nadir-gap column masking and the fully-NaN column restoration).

API note: production ran pyinterp 2025.11.0, whose ``fill.gauss_seidel`` took a
``Grid2D`` and returned ``(converged, filled)``. pyinterp >= 2026 fills the plain
ndarray in place and returns ``(iterations, residual)``; the relaxation algorithm
is unchanged. This module uses the >= 2026 API and returns per-dataset
``(iterations, residual)`` tuples. The JSON ``packages_versions`` field records
the pyinterp version used for each spectrum.
"""

from __future__ import annotations

import logging
from typing import List, Tuple

import numpy as np

logger = logging.getLogger(__name__)


def fill_nan(
    datasets: dict, varname: str = "ssh", num_threads: int = 16
) -> Tuple[List[Tuple[int, float]], dict]:
    """Fill NaNs in each dataset with pyinterp's Gauss-Seidel solver (in place)."""
    import pyinterp.fill as fill

    info: List[Tuple[int, float]] = []
    filled_datasets = {}
    new_key = 0
    for key in range(len(datasets)):
        data = datasets[key][[varname]]

        values = np.asarray(data[varname].values, dtype="float64", order="C")
        if values.shape[1] >= 34:
            values[:, 33:35] = np.nan

        nan_columns = np.all(np.isnan(values), axis=0)

        iterations, residual = fill.gauss_seidel(values, num_threads=num_threads)
        info.append((int(iterations), float(residual)))

        values[:, nan_columns] = np.nan

        datasets[key][varname] = (("num_lines", "num_pixels"), values)
        filled_datasets[new_key] = datasets[key]
        new_key += 1

    return info, filled_datasets
