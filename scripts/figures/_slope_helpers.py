#!/usr/bin/env python3
"""Faithful ports of notebook/plot_slope_onl_v3+tides.ipynb local cells for the
five slope scripts (fig4_winterslope_zonal, s6_ratioslope, s7_std_slope_winter,
s8_slope_summer, s9_std_slope_summer).

Sources:
- notebook/plot_slope_onl_v3+tides.ipynb cells 4 (plot_fig) and 5 (plot_fig2v):
  verbatim.
- cell 9 (sole data load of the notebook): src.cum_sp_onl_season_v3.season_slope
  body ported below with the data reads substituted, followed by the two
  cs.remap calls (see load_slope_maps).
- cell 7 (boxesjson / north_boxes / south_boxes / selected): stays in the
  scripts, with the bare geojson filename replaced by _common.GEOJSON.

Recorded deviations from the notebook code (only these):
- the notebooks' online reads (cum_sp_onl_season_v3.read_season over anonymous
  S3 at https://minio.dive.edito.eu/, prefix project-meom-ige/OMIP/Global/) are
  replaced by the injected read(key, box, season, year=None) (from
  _common.read_spectrum via _region_helpers.reader_from): offline cache
  figure_cache/GLOBALv2/ by default, anonymous DIVE reads with --online. The
  read_season online body (append data["Spectra"] / data["Frequency"] per
  model, in model order) is preserved exactly in _read_season; everything else
  in season_slope is kept verbatim (JFM wavelength grid for the band
  selection, JAS frequency grid for the slope x-axis, hemisphere-dependent
  winter/summer assignment, np.nanmean/np.nanstd stats).
- cs.remap is called with boxesjson=_common.GEOJSON: the notebook calls
  cs.remap(...) relying on its default relative path
  "mostly_ocean_boxes_filtered.geojson", which only resolves from the
  notebook's CWD -- the absolute path is the same file, no computation change.

Everything else is kept EXACTLY as in the committed notebook, so script output
reproduces the notebook figures.
"""

from __future__ import annotations

import numpy as np

import cartopy.crs as ccrs
import cartopy.feature as cfeature

import cum_sp_onl_season_v3 as cs
from _common import GEOJSON


def _read_season(read, season1, box, models):
    """Notebook read_season(season1, box, endpoint_url, models) with the online
    read_json_s3 body substituted by read(key, box, season)."""
    spectrumJFM = []
    freqJFM = []
    for imod in models:
        data = read(imod, box, season1)
        spectrumJFM.append(data["Spectra"])
        freqJFM.append(data["Frequency"])
    return spectrumJFM, freqJFM


def season_slope(read, models, selected, wlmin, wlmax, north_boxes, south_boxes,
                 season1, season2):
    """Port of src.cum_sp_onl_season_v3.season_slope with the reads substituted.

    Signature change only: endpoint_url/modeload/folder existed solely to feed
    read_season and are dropped; all computation is verbatim."""
    box = 0
    m_slopeW = np.zeros((len(selected), len(models)))
    m_slopeS = np.zeros((len(selected), len(models)))
    s_slopeW = np.zeros((len(selected), len(models)))
    s_slopeS = np.zeros((len(selected), len(models)))
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
                psdsW = ((spectrumJFMM[poswl[0]]))
                psdsS = ((spectrumJASM[poswl[0]]))
                x_slope = np.log10(freqJASM[poswl[0]])
                y_slope = np.log10(psdsW)
                slopeW = -np.gradient(y_slope, x_slope)
                y_slope = np.log10(psdsS)
                slopeS = -np.gradient(y_slope, x_slope)
                m_slopeW[box, imodel] = np.nanmean(slopeW)
                s_slopeW[box, imodel] = np.nanstd(slopeW)
                m_slopeS[box, imodel] = np.nanmean(slopeS)
                s_slopeS[box, imodel] = np.nanstd(slopeS)
            elif box in south_boxes:
                psdsW = ((spectrumJASM[poswl[0]]))
                psdsS = ((spectrumJFMM[poswl[0]]))
                x_slope = np.log10(freqJASM[poswl[0]])
                y_slope = np.log10(psdsW)
                slopeW = -np.gradient(y_slope, x_slope)
                y_slope = np.log10(psdsS)
                slopeS = -np.gradient(y_slope, x_slope)
                m_slopeW[box, imodel] = np.nanmean(slopeW)
                s_slopeW[box, imodel] = np.nanstd(slopeW)
                m_slopeS[box, imodel] = np.nanmean(slopeS)
                s_slopeS[box, imodel] = np.nanstd(slopeS)

        box = box + 1

    return m_slopeW, m_slopeS, s_slopeW, s_slopeS


def load_slope_maps(read, selected, north_boxes, south_boxes):
    """Notebook cell 9 verbatim (reads substituted): per-box/model/season slope
    statistics on the 50-150 km band for the 7-key model list, then the two
    cs.remap calls reorganizing the (282, 7) arrays into (7, 18, 36) maps.

    Returns (m_slopeW2, m_slopeS2, s_slopeW2, s_slopeS2)."""
    min_wavelength = 50
    max_wavelength = 150
    models = ["GLO12V4", "GLO36V1", "GLO36V1NOTIDE", "NOC12", "NOC025", 'LLC4320', "SWOT"]

    m_slopeW, m_slopeS, s_slopeW, s_slopeS = season_slope(
        read, models, selected, min_wavelength, max_wavelength,
        north_boxes, south_boxes, "JFM", "JAS")

    m_slopeW2, m_slopeS2 = cs.remap(m_slopeW, m_slopeS, models, boxesjson=GEOJSON)
    s_slopeW2, s_slopeS2 = cs.remap(s_slopeW, s_slopeS, models, boxesjson=GEOJSON)
    return m_slopeW2, m_slopeS2, s_slopeW2, s_slopeS2


def plot_fig(ax, imodel, lon_edges, lat_edges, ZW, valmin, valmax, model, posx, posy, abc):
    """Notebook cell 4 verbatim (contourf slope map helper)."""
    ax[posx, posy].add_feature(cfeature.COASTLINE)
    ax[posx, posy].add_feature(cfeature.LAND, facecolor="lightgray")
    mesh = ax[posx, posy].contourf(
        lon_edges,
        lat_edges,
        np.squeeze((ZW[imodel, :, :])),
        np.arange(valmin, valmax, 0.25),
        cmap='hsv',
        transform=ccrs.PlateCarree()
    )
    ax[posx, posy].set_title(abc + model[imodel])
    ax[posx, posy] = ax[posx, posy].gridlines(draw_labels=True, linewidth=0.2)
    ax[posx, posy].bottom_labels = True
    ax[posx, posy].top_labels = False
    ax[posx, posy].right_labels = False
    ax[posx, posy].left_labels = True
    ax[posx, posy].xlines = False
    ax[posx, posy].ylines = False
    return ax, mesh


def plot_fig2v(ax, imodel, lon_edges, lat_edges, ZW, ZS, valmin, valmax, model,
               posx, posy, abc, box_pos, box_neg):
    """Notebook cell 5 verbatim (pcolormesh winter/summer slope-ratio map helper
    with the Boxes >1 / Boxes <1 annotations)."""
    ax[posx, posy].add_feature(cfeature.COASTLINE)
    ax[posx, posy].add_feature(cfeature.LAND, facecolor="lightgray")
    mesh = ax[posx, posy].pcolormesh(
        lon_edges,
        lat_edges,
        np.squeeze((ZW[imodel, :, :]) / (ZS[imodel, :, :])),
        vmin=valmin, vmax=valmax,
        cmap='seismic',
        transform=ccrs.PlateCarree()
    )
    ax[posx, posy].text(30, 60, f"Boxes >1: {box_pos[imodel]}", transform=ccrs.PlateCarree(),
                       fontsize=8, fontweight='bold',
                       bbox=dict(facecolor='white', alpha=0.6, edgecolor='none'))
    ax[posx, posy].text(30, 40, f"Boxes <1: {box_neg[imodel]}", transform=ccrs.PlateCarree(),
                       fontsize=8, fontweight='bold',
                       bbox=dict(facecolor='white', alpha=0.6, edgecolor='none'))
    ax[posx, posy].set_title(abc + model[imodel])
    ax[posx, posy] = ax[posx, posy].gridlines(draw_labels=True, linewidth=0.2)
    ax[posx, posy].bottom_labels = True
    ax[posx, posy].top_labels = False
    ax[posx, posy].right_labels = False
    ax[posx, posy].left_labels = True
    ax[posx, posy].xlines = False
    ax[posx, posy].ylines = False
    return ax, mesh
