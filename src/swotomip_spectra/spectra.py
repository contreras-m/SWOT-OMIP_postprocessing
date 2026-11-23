"""PSD chain: segments -> Welch -> mean, delegating to the repo-vendored
Spectra implementation (src/Spectra.py, byte-identical compute functions to
widetrax v1.1.1 Spectra; only plot_psd cosmetics differ).

The vendored module is exposed as the real package submodule
swotomip_spectra.spectra_impl (symlink to ../Spectra.py) so that
multiprocessing pickling works under macOS spawn. Set
SWOTOMIP_SPECTRA_BACKEND=widetrax to import widetrax.Spectra instead
(requires the full widetrax dependency set).
"""

from __future__ import annotations

import os
from typing import Dict, Tuple

from . import spectra_impl


def load_spectra_module():
    backend = os.environ.get("SWOTOMIP_SPECTRA_BACKEND", "vendored")
    if backend == "widetrax":
        from widetrax import Spectra

        return Spectra
    return spectra_impl


def retrieve_segments(datasets: dict, file_type: str = "NetCDF", namevar: str = "ssh") -> dict:
    return load_spectra_module().retrieve_segments(datasets, file_type, namevar)


def calculate_psd(segments_dict: dict, fs: float = 0.5) -> Tuple[dict, dict]:
    return load_spectra_module().calculate_psd(segments_dict, fs)


def psd_mean_and_freq(psd_dict: dict, freqs_dict: dict) -> Tuple["np.ndarray", "np.ndarray"]:
    import numpy as np

    mean = None
    freqs = None
    if psd_dict and freqs_dict:
        mean, freqs = load_spectra_module().psd_mean_and_freq(psd_dict, freqs_dict)
    if mean is None:
        mean = np.array([])
    if freqs is None:
        freqs = np.array([])
    return mean, freqs
