"""Spectra backend smoke: resolves to widetrax >= 1.2 and computes end-to-end.

Guards the swap that removed the vendored src/Spectra.py copy: the PSD chain
must come from the installed widetrax and behave like the production chain.
"""
import numpy as np
import pytest

pytest.importorskip("widetrax")

import xarray as xr

from swotomip_spectra import spectra


def _dataset(n_lines=200, n_pixels=5):
    ssh = np.sin(np.arange(n_lines, dtype="f8")[:, None] / 10.0) + np.tile(
        np.arange(n_pixels, dtype="f8")[None, :] * 0.1, (n_lines, 1)
    )
    ssh[:, 0] = np.nan  # fully-NaN column -> NO segment (historical behavior)
    ssh[10:20, 1] = np.nan  # interior NaNs -> trimmed (concatenated) segment
    lat = np.linspace(-30, -20, n_lines)[:, None] * np.ones((1, n_pixels))
    lon = np.ones((n_lines, 1)) * np.linspace(300, 310, n_pixels)[None, :]
    return xr.Dataset(
        {"ssh": (("num_lines", "num_pixels"), ssh)},
        coords={
            "latitude": (("num_lines", "num_pixels"), lat),
            "longitude": (("num_lines", "num_pixels"), lon),
        },
    )


def test_backend_is_widetrax():
    import widetrax

    assert spectra.load_spectra_module() is widetrax.Spectra


def test_retrieve_segments_skips_and_trims():
    segments = spectra.retrieve_segments({0: _dataset()}, "NetCDF", "ssh")
    # column 0 (all NaN) yields no segment; columns 1-4 do
    assert len(segments) == 4
    # column 1 lost its 10 interior NaNs to the historic NaN-squeeze
    assert sorted(len(v) for v in segments.values()) == [190, 200, 200, 200]


def test_calculate_psd_and_mean():
    segments = spectra.retrieve_segments({0: _dataset()}, "NetCDF", "ssh")
    psd_dict, freqs_dict = spectra.calculate_psd(segments)
    assert len(psd_dict) == len(freqs_dict) == 4  # all segments > 120 points

    mean, freqs = spectra.psd_mean_and_freq(psd_dict, freqs_dict)
    assert mean.size > 0
    assert mean.size == freqs.size
    assert np.isfinite(mean).all()
    assert (mean > 0).all()


def test_empty_inputs_return_empty_arrays():
    mean, freqs = spectra.psd_mean_and_freq({}, {})
    assert mean.size == 0 and freqs.size == 0
