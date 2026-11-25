#!/usr/bin/env python3
"""Faithful ports of the cumulative-spectra notebooks' shared cells and of the
src/cum_sp_onl_season_v3.py compute functions their data-load cells call.

Sources (verbatim computation):
- notebook/plot_cumpsd_ratio-scatter.ipynb cell 5: plot_spectral_scatter
  (the 9-arg model-vs-SWOT ratio-of-ratio scatter) -- used by
  fig2_cumsd_ratio_scatter.py and s3_cumsd_ratio_tides.py.
- notebook/plot_cumpsd_scatterplt_SI.ipynb cell 5: the 7-arg
  plot_spectral_scatter_cumspectrum (same name in that notebook; different
  signature and axis limits 1e-7..1e-1) -- used by
  s2_cumspectrum_winter_summer.py.
- both notebooks' cell 12: the latitude-bin index (latindex over 14 skipped
  features 14/15, latpos, and the geojson dict).
- src/cum_sp_onl_season_v3.py season_spec / season_cum / remap: the compute
  bodies of the notebooks' data-load cells (cells 9/10 and 15/16 call them
  with modeload="online").

Recorded deviations from the notebook/src code (only these):
- cs.read_season / cs.read_json_s3 (anonymous S3 GETs of
  project-meom-ige/OMIP/Global/<KEY>/Global_box_{box}_{season}_{KEY}.json)
  are replaced by the injected read(key, box, season) from _common (offline
  figure_cache/GLOBALv2 by default, anonymous DIVE with --online); the
  surrounding computation is verbatim, so the endpoint_url / modeload /
  folder arguments drop out of the signatures. None of these figures'
  model lists include GEOMAR, so no per-year read pattern is involved.
- remap's boxesjson default (bare "mostly_ocean_boxes_filtered.geojson",
  cwd-relative in the notebooks) becomes an explicit argument; callers pass
  _common.GEOJSON. Likewise load_latindex takes the geojson path.
- cell 12's trailing print(latindex[0]) is dropped (scripts print nothing
  beyond the save/done lines).
- author-approved change (contreras-m, 2026-11-25): the latindex block no
  longer skips geojson features 14/15 -- the skip was a leftover bug guard
  (confirmed by the notebook author), and carrying it left the latitude-bin
  positions indexing a 280-long list against 282-long per-box lists. latindex
  now covers all 282 features. The 60-degree latitude bin remains empty
  (nan zonal means + RuntimeWarning), as in the notebooks.
"""

import json

import numpy as np


def _read_season(read, season, box, models):
    spectrum = []
    freq = []
    for imod in models:
        data = read(imod, box, season)
        spectrum.append(data["Spectra"])
        freq.append(data["Frequency"])
    return spectrum, freq


def season_spec(read, models, selected, wlmin, wlmax, north_boxes, south_boxes,
                season1, season2):
    R = {imod: [] for imod in models}
    F = {imod: [] for imod in models}

    for i, poly in enumerate(selected):
        box = i

        spectrum_s1, freq_s1 = _read_season(read, season1, box, models)
        spectrum_s2, freq_s2 = _read_season(read, season2, box, models)

        for imodel, imod in enumerate(models):
            freq = np.array(freq_s1[imodel])
            wavelength = 1.0 / freq

            poswl = np.where((wavelength > wlmin) & (wavelength < wlmax))[0]

            spec_s1 = np.array(spectrum_s1[imodel])[poswl]
            spec_s2 = np.array(spectrum_s2[imodel])[poswl]
            freq_filtered = freq[poswl]

            if box in north_boxes:
                psdsW = spec_s1
                psdsS = spec_s2
            elif box in south_boxes:
                psdsW = spec_s2
                psdsS = spec_s1
            else:
                continue

            Z = psdsW / psdsS

            R[imod].append(Z)
            F[imod].append(freq_filtered)

    return R, F


def season_cum(read, models, selected, wlmin, wlmax, north_boxes, south_boxes,
               season1, season2):
    box = 0
    psdsW = np.zeros((len(selected), len(models)))
    psdsS = np.zeros((len(selected), len(models)))

    for i, poly in enumerate(selected):
        spectrumJFM, freqJFM = _read_season(read, season1, box, models)
        spectrumJAS, freqJAS = _read_season(read, season2, box, models)

        wavelength = 1 / np.array(freqJFM)

        for imodel in range(len(models)):
            poswl = np.where((wavelength[imodel] > wlmin) & (wavelength[imodel] < wlmax))
            spectrumJFMM = np.array(spectrumJFM[imodel])
            spectrumJASM = np.array(spectrumJAS[imodel])
            freqJASM = np.array(freqJAS[imodel])
            dk = np.gradient(freqJASM[poswl[0]])
            if box in north_boxes:
                psdsW[box, imodel] = np.cumsum(spectrumJFMM[poswl[0]] * dk)[-1]
                psdsS[box, imodel] = np.cumsum(spectrumJASM[poswl[0]] * dk)[-1]
            elif box in south_boxes:
                psdsW[box, imodel] = np.cumsum(spectrumJASM[poswl[0]] * dk)[-1]
                psdsS[box, imodel] = np.cumsum(spectrumJFMM[poswl[0]] * dk)[-1]
        box = box + 1

    return psdsW, psdsS, freqJAS


def remap(psdsW, psdsS, models, boxesjson):
    with open(boxesjson) as f:
        data = json.load(f)

    nboxes = len(data["features"])

    lon_min_list = []
    lat_min_list = []

    for feature in data["features"]:
        coords = feature["geometry"]["coordinates"][0]
        lons = [pt[0] for pt in coords]
        lats = [pt[1] for pt in coords]

        lon_min_list.append(min(lons))
        lat_min_list.append(min(lats))

    lon_min_list = np.array(lon_min_list)
    lat_min_list = np.array(lat_min_list)

    lon_edges = np.arange(-180, 181, 10)
    lat_edges = np.arange(-90, 91, 10)

    nlon = len(lon_edges) - 1
    nlat = len(lat_edges) - 1

    ZW = np.full((len(models), nlat, nlon), np.nan)
    values = np.array(psdsW)
    for i in range(nboxes):
        lon_idx = np.where(lon_edges[:-1] == lon_min_list[i])[0][0]
        lat_idx = np.where(lat_edges[:-1] == lat_min_list[i])[0][0]
        for imodel in range(len(models)):
            ZW[imodel, lat_idx, lon_idx] = np.array(values[i, imodel])

    ZS = np.full((len(models), nlat, nlon), np.nan)
    values = np.array(psdsS)
    for i in range(nboxes):
        lon_idx = np.where(lon_edges[:-1] == lon_min_list[i])[0][0]
        lat_idx = np.where(lat_edges[:-1] == lat_min_list[i])[0][0]
        for imodel in range(len(models)):
            ZS[imodel, lat_idx, lon_idx] = np.array(values[i, imodel])

    return ZW, ZS


def load_latindex(geojson):
    with open(geojson) as f:
        data = json.load(f)

    latboxes = []
    latpos = np.arange(-70, 61, 10)

    for i, feature in enumerate(data["features"]):
        coords = feature["geometry"]["coordinates"][0]
        first_lat = coords[0][1]
        latboxes.append(first_lat)

    latindex = []
    for i in latpos:
        latindex.append(np.where(latboxes == i))

    return latindex, latpos, data


def plot_spectral_scatter(ax, k_list, specAW_list, specAS_list, specBW_list,
                          specBS_list, labelA, labelB, abc):
    from scipy.stats import linregress

    vmin = 0
    vmax = 282
    vmin1 = 1e-1
    vmax1 = 1e1

    xW_all = np.array(specAW_list)
    yW_all = np.array(specBW_list)
    xS_all = np.array(specAS_list)
    yS_all = np.array(specBS_list)
    k_all = np.array(k_list)

    mask_valid1 = (xW_all > 0) & (yW_all > 0)
    mask_valid2 = (xS_all > 0) & (yS_all > 0)

    xS_all = xS_all[mask_valid2]
    yS_all = yS_all[mask_valid2]
    xW_all = xW_all[mask_valid1]
    yW_all = yW_all[mask_valid1]
    k_all = k_all[mask_valid1]

    x_all = xW_all / xS_all
    y_all = yW_all / yS_all
    slope, intercept, r_value, p_value, std_err = linregress(x_all, y_all)
    sc = ax.scatter(
        x_all,
        y_all,
        c=k_all,
        vmin=vmin,
        vmax=vmax,
        cmap="nipy_spectral",
        s=10,
        alpha=0.7
    )

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_title(abc)

    vmin = min(x_all.min(), y_all.min())
    vmax = max(x_all.max(), y_all.max())

    ax.plot([vmin, vmax], [vmin, vmax], "k--")

    ax.set_xlim(vmin1, vmax1)
    ax.set_ylim(vmin1, vmax1)
    ax.text(x=1.2e-1, y=0.7e1, s=f"R2 = {r_value:.3f}", weight="bold")
    ax.grid(True, which="both", ls="--", alpha=0.3)
    ax.set_xlabel(labelA)
    ax.set_ylabel(labelB)

    return sc


def plot_spectral_scatter_cumspectrum(ax, k_list, specAW_list, specBW_list,
                                      labelA, labelB, abc):
    from scipy.stats import linregress

    vmin = 0
    vmax = 282
    vmin1 = 1e-7
    vmax1 = 1e-1

    xW_all = np.array(specAW_list)
    yW_all = np.array(specBW_list)
    k_all = np.array(k_list)

    mask_valid = (xW_all > 0) & (yW_all > 0)

    mask = mask_valid
    xW_all = xW_all[mask]
    yW_all = yW_all[mask]
    k_all = k_all[mask]

    x_all = xW_all
    y_all = yW_all
    slope, intercept, r_value, p_value, std_err = linregress(x_all, y_all)
    sc = ax.scatter(
        x_all,
        y_all,
        c=k_all,
        vmin=vmin,
        vmax=vmax,
        cmap="nipy_spectral",
        s=10,
        alpha=0.7
    )

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_title(abc)

    vmin = min(x_all.min(), y_all.min())
    vmax = max(x_all.max(), y_all.max())

    ax.plot([vmin, vmax], [vmin, vmax], "k--")

    ax.set_xlim(vmin1, vmax1)
    ax.set_ylim(vmin1, vmax1)
    ax.text(x=1e-6, y=1e-2, s=f"R2 = {r_value:.3f}", weight="bold")
    ax.grid(True, which="both", ls="--", alpha=0.3)
    ax.set_xlabel(labelA)
    ax.set_ylabel(labelB)

    return sc
