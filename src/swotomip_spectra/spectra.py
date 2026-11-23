"""PSD chain: segments -> Welch -> mean, delegating to widetrax.Spectra.

widetrax >= 1.2 ships the production compute chain (retrieve_segments /
calculate_psd / psd_mean_and_freq) upstreamed from this repo via
IGE-OPERA/widetrax#20 (PRs #22-#24); the formerly vendored src/Spectra.py
and its spectra_impl symlink have been removed.
"""

from __future__ import annotations

from typing import Tuple


def load_spectra_module():
    """Return the widetrax Spectra module (import deferred to first use)."""
    from widetrax import Spectra

    return Spectra


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
