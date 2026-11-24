#!/usr/bin/env python3
"""Faithful ports of the region notebooks' local cells (AG + GS variants).

Sources:
- notebook/region_plot_spectr_noonl_AG-Copy1-IMPR.ipynb cells 4-6
- notebook/region_plot_spectr_noonl_GS-Copy1-IMPR.ipynb cells 4-6

Recorded deviations from the notebook code (only these):
- the notebook's `read_json_local(folder, filename)` reads are replaced by
  the injected `read(key, box, season, year=None)` (from _common.read_spectrum
  via a small closure); offline cache by default, anonymous DIVE with
  --online. GEOMAR keeps its per-year and year-less read pattern.
- plot_psd(..., savefig=False): the notebooks pass savefig=True, which only
  re-saves globa_JFM.png to the cwd per inset plot (no layout effect) --
  the scripts keep the working tree clean.

Everything else -- iteration order, the 50-600 km log-log clipping, the
hemisphere-dependent ratio (north: JFM/JAS, south: JAS/JFM), the GEOMAR
per-year accumulation quirks (including the year-less JAS read inside the
per-year loop), region-mean interpolation and the (i != 14, 15) skip in
load_spectrum -- is kept EXACTLY as in the committed notebooks, so script
output reproduces the notebook figures.
"""

from __future__ import annotations

import numpy as np

import plot_psd1Xglobal1 as pp2X


def reader_from(cfg):
    """The read(key, box, season, year=None) used by the ported functions."""
    from _common import read_spectrum

    return lambda key, box, season, year=None: read_spectrum(cfg, key, box, season, year)


# ---------------------------------------------------------------- AG variant


def plot_boxspectrum(fig, region_boxes, models, modellabel, cds, selected,
                     region_name, north_boxes, south_boxes, colors, lsts,
                     read, box_legend=0):
    import cartopy.crs as ccrs
    import cartopy.feature as cfeature
    import matplotlib.pyplot as plt

    ax = fig.add_axes([0.15, 0.53, 0.7, 0.45], projection=ccrs.PlateCarree())
    ax.set_extent([cds[0] - 2, cds[1] + 2, cds[2] - 2, cds[3] + 2], crs=ccrs.PlateCarree())
    gl = ax.gridlines(
        crs=ccrs.PlateCarree(),
        draw_labels=True,
        linewidth=2,
        color='gray',
        alpha=0.5,
        linestyle='--'
    )
    gl.top_labels = False
    gl.right_labels = False
    gl.xlabel_style = {'size': 10}
    gl.ylabel_style = {'size': 10}
    gl.xlines = False
    gl.ylines = False
    ax.set_title(region_name, fontsize=15, fontweight="bold", color="black")
    ax.add_feature(cfeature.LAND, zorder=10, facecolor="lightgray")
    ax.add_feature(cfeature.COASTLINE)

    ibox = 0
    for ir in region_boxes:
        box = region_boxes[ibox]
        poly = selected[ir]

        lon_min, lat_min, lon_max, lat_max = poly.bounds
        lon_c = 0.5 * (lon_min + lon_max) - 2
        lat_c = 0.5 * (lat_min + lat_max) - 2

        x_fig, y_fig = ax.transData.transform(
            ccrs.PlateCarree().transform_point(lon_c, lat_c, ccrs.PlateCarree())
        )
        x_fig, y_fig = fig.transFigure.inverted().transform((x_fig, y_fig))
        w, h = 0.08, 0.08

        wlmin = 50
        wlmax = 600
        inset_ax = fig.add_axes([x_fig, y_fig, w, h])
        season1 = "JFM"
        Ra = []
        freqJFM = []
        season2 = "JAS"
        freqJAS = []
        for imod in models:
            if imod != "GEOMAR":
                data = read(imod, box, season1)
                freqJFM0 = np.array(data["Frequency"])
                spectrumJFM0 = np.array(data["Spectra"])
                wavelength = 1 / np.array(freqJFM0)
                poswl = np.where((wavelength > wlmin) & (wavelength < wlmax))
                freqJFM.append(freqJFM0[poswl[0]])

                data = read(imod, box, season2)
                freqJAS0 = np.array(data["Frequency"])
                spectrumJAS0 = np.array(data["Spectra"])
                wavelength = 1 / np.array(freqJAS0)
                poswl = np.where((wavelength > wlmin) & (wavelength < wlmax))
                freqJAS.append(freqJAS0[poswl[0]])

                if box in north_boxes:
                    Ra.append(spectrumJFM0[poswl[0]] / spectrumJAS0[poswl[0]])
                elif box in south_boxes:
                    Ra.append(spectrumJAS0[poswl[0]] / spectrumJFM0[poswl[0]])
            elif imod == "GEOMAR":
                kyr = 0
                for yr in range(2021, 2024):
                    data = read(imod, box, season1, year=yr)
                    freqJFM0 = np.array(data["Frequency"])
                    spectrumJFM0 = np.array(data["Spectra"])
                    wavelength = 1 / np.array(freqJFM0)
                    poswl = np.where((wavelength > wlmin) & (wavelength < wlmax))
                    # NOTE (faithful port): season 2 reads the YEAR-LESS file
                    # inside the per-year loop, exactly like the notebook
                    # (stand-ins are the disclosed 3-yr means -- see the
                    # cache provenance note).
                    data = read(imod, box, season2)
                    freqJAS0 = np.array(data["Frequency"])
                    poswl = np.where((wavelength > wlmin) & (wavelength < wlmax))
                    spectrumJAS0 = np.array(data["Spectra"])
                    if yr == 2021:
                        spectrumJFM1 = np.zeros((len(spectrumJFM0)))
                        spectrumJAS1 = np.zeros((len(spectrumJAS0)))
                    spectrumJFM1 = spectrumJFM1 + spectrumJFM0
                    spectrumJAS1 = spectrumJAS1 + spectrumJAS0
                    kyr = kyr + 1
                freqJFM.append(freqJFM0[poswl[0]])
                freqJAS.append(freqJAS0[poswl[0]])
                if box in north_boxes:
                    Ra.append((spectrumJFM0[poswl[0]] / kyr) / (spectrumJAS0[poswl[0]] / kyr))
                elif box in south_boxes:
                    Ra.append((spectrumJAS0[poswl[0]] / kyr) / (spectrumJFM0[poswl[0]] / kyr))

        if ibox == box_legend:
            pp2X.plot_psd(inset_ax, np.squeeze(np.array(freqJAS)).T, psds=Ra, unit="m2",
                          psd_labels=modellabel,
                          legend=True, bba_leg=(4.5, 2), colors=colors, lsts=lsts,
                          xtick_show=True, ytick_show=True, xlabel_upper=False,
                          xlabel_lower=False,
                          wavelength_ticks=np.array([50, 250, 100, 500]),
                          ylabel=False, savefig=False,
                          plot_transparent=False, slope=False,
                          scaleX='log', scaleY='log')
        else:
            pp2X.plot_psd(inset_ax, np.squeeze(np.array(freqJAS)).T, psds=Ra, unit="m2",
                          psd_labels=modellabel,
                          legend=False, colors=colors, lsts=lsts,
                          xtick_show=True, ytick_show=True, xlabel_upper=False,
                          xlabel_lower=False,
                          wavelength_ticks=np.array([50, 250, 100, 500]),
                          ylabel=False, savefig=False,
                          plot_transparent=False, slope=False,
                          scaleX='log', scaleY='log')
        ibox = ibox + 1
        plt.axhline(y=1, color='gray', linestyle='--')
        inset_ax.set_ylim([1e-1, 1e1])
    ax.set_extent([cds[0] - 2, cds[1] + 2, cds[2] - 2, cds[3] + 2], crs=ccrs.PlateCarree())
    return


def load_spectrum(read, region_boxes, models, season1, season2, Wl):
    box = 0
    psdsW = np.zeros((len(region_boxes), len(models)))
    psdsS = np.zeros((len(region_boxes), len(models)))

    FbS = np.zeros((len(Wl), len(models)))  # Mean spectrum over the region in summer
    FbW = np.zeros((len(Wl), len(models)))  # Mean spectrum over the region in winter
    aFbS = np.zeros((3, len(Wl)))
    aFbW = np.zeros((3, len(Wl)))

    km = 0
    for imod in models:
        ki = 0
        for i in (region_boxes):

            if (i != 14) and (i != 15):
                season = season1
                spectrumJFM = []
                freqJFM = []
                # Plot spectrum JFM
                if imod != "GEOMAR":
                    data = read(imod, i, season)
                    spectrumJFM.append(data["Spectra"])
                    freqJFM.append(data["Frequency"])
                    FbW[:, km] = FbW[:, km] + np.interp(1 / Wl, np.array(data["Frequency"]),
                                                        np.array(data["Spectra"]))
                elif imod == "GEOMAR":
                    kyr = 0
                    for yr in range(2021, 2024):
                        spectrumJFM = []
                        freqJFM = []
                        data = read(imod, i, season, year=yr)
                        spectrumJFM.append(data["Spectra"])
                        freqJFM.append(data["Frequency"])
                        aFbW[kyr, :] = aFbW[kyr, :] + np.interp(1 / Wl, np.array(data["Frequency"]),
                                                                np.array(data["Spectra"]))
                        kyr = kyr + 1
                    FbW[:, km] = np.nanmean(aFbW, axis=0)
                    FbWy = np.nanstd(aFbW, axis=0)

                season = season2
                spectrumJAS = []
                freqJAS = []
                # Plot spectrum JAS
                if imod != "GEOMAR":
                    data = read(imod, i, season)
                    spectrumJAS.append(data["Spectra"])
                    freqJAS.append(data["Frequency"])
                    FbS[:, km] = FbS[:, km] + np.interp(1 / Wl, np.array(data["Frequency"]),
                                                        np.array(data["Spectra"]))
                elif imod == "GEOMAR":
                    kyr = 0
                    for yr in range(2021, 2024):
                        spectrumJAS = []
                        freqJAS = []
                        data = read(imod, i, season, year=yr)
                        spectrumJAS.append(data["Spectra"])
                        freqJAS.append(data["Frequency"])
                        aFbS[kyr, :] = aFbS[kyr, :] + np.interp(1 / Wl, np.array(data["Frequency"]),
                                                                np.array(data["Spectra"]))
                        kyr = kyr + 1
                    FbS[:, km] = np.nanmean(aFbS, axis=0)
                ki = ki + 1
        km = km + 1

    FbS = FbS / len(region_boxes)
    FbW = FbW / len(region_boxes)
    aFbW = aFbW / len(region_boxes)
    aFbS = aFbS / len(region_boxes)
    return FbS, FbW, aFbS, aFbW


# ---------------------------------------------------------------- GS variant


def plot_boxspectrum_gs(fig, region_boxes, models, modellabel, cds, selected,
                        region_name, north_boxes, south_boxes, colors, lsts,
                        read, box_legend=0):
    """The GS notebook's map variant: map axes [0.1, 0.1, 0.7, 0.7], inset 0.065."""
    import cartopy.crs as ccrs
    import cartopy.feature as cfeature
    import matplotlib.pyplot as plt

    ax = fig.add_axes([0.1, 0.1, 0.7, 0.7], projection=ccrs.PlateCarree())
    ax.set_extent([cds[0] - 2, cds[1] + 2, cds[2] - 2, cds[3] + 2], crs=ccrs.PlateCarree())
    gl = ax.gridlines(
        crs=ccrs.PlateCarree(),
        draw_labels=True,
        linewidth=2,
        color='gray',
        alpha=0.5,
        linestyle='--'
    )
    gl.top_labels = False
    gl.right_labels = False
    gl.xlabel_style = {'size': 10}
    gl.ylabel_style = {'size': 10}
    gl.xlines = False
    gl.ylines = False
    ax.set_title(region_name, fontsize=15, fontweight="bold", color="black")
    ax.add_feature(cfeature.LAND, zorder=10, facecolor="lightgray")
    ax.add_feature(cfeature.COASTLINE)

    ibox = 0
    for ir in region_boxes:
        box = region_boxes[ibox]
        poly = selected[ir]

        lon_min, lat_min, lon_max, lat_max = poly.bounds
        lon_c = 0.5 * (lon_min + lon_max) - 2
        lat_c = 0.5 * (lat_min + lat_max) - 2

        x_fig, y_fig = ax.transData.transform(
            ccrs.PlateCarree().transform_point(lon_c, lat_c, ccrs.PlateCarree())
        )
        x_fig, y_fig = fig.transFigure.inverted().transform((x_fig, y_fig))
        w, h = 0.065, 0.065

        wlmin = 50
        wlmax = 600
        inset_ax = fig.add_axes([x_fig, y_fig, w, h])
        season1 = "JFM"
        Ra = []
        freqJFM = []
        season2 = "JAS"
        freqJAS = []
        for imod in models:
            if imod != "GEOMAR":
                data = read(imod, box, season1)
                freqJFM0 = np.array(data["Frequency"])
                spectrumJFM0 = np.array(data["Spectra"])
                wavelength = 1 / np.array(freqJFM0)
                poswl = np.where((wavelength > wlmin) & (wavelength < wlmax))
                freqJFM.append(freqJFM0[poswl[0]])

                data = read(imod, box, season2)
                freqJAS0 = np.array(data["Frequency"])
                spectrumJAS0 = np.array(data["Spectra"])
                wavelength = 1 / np.array(freqJAS0)
                poswl = np.where((wavelength > wlmin) & (wavelength < wlmax))
                freqJAS.append(freqJAS0[poswl[0]])

                if box in north_boxes:
                    Ra.append(spectrumJFM0[poswl[0]] / spectrumJAS0[poswl[0]])
                elif box in south_boxes:
                    Ra.append(spectrumJAS0[poswl[0]] / spectrumJFM0[poswl[0]])
            elif imod == "GEOMAR":
                kyr = 0
                for yr in range(2021, 2024):
                    data = read(imod, box, season1, year=yr)
                    freqJFM0 = np.array(data["Frequency"])
                    spectrumJFM0 = np.array(data["Spectra"])
                    wavelength = 1 / np.array(freqJFM0)
                    poswl = np.where((wavelength > wlmin) & (wavelength < wlmax))
                    data = read(imod, box, season2)
                    freqJAS0 = np.array(data["Frequency"])
                    poswl = np.where((wavelength > wlmin) & (wavelength < wlmax))
                    spectrumJAS0 = np.array(data["Spectra"])
                    if yr == 2021:
                        spectrumJFM1 = np.zeros((len(spectrumJFM0)))
                        spectrumJAS1 = np.zeros((len(spectrumJAS0)))
                    spectrumJFM1 = spectrumJFM1 + spectrumJFM0
                    spectrumJAS1 = spectrumJAS1 + spectrumJAS0
                    kyr = kyr + 1
                freqJFM.append(freqJFM0[poswl[0]])
                freqJAS.append(freqJAS0[poswl[0]])
                if box in north_boxes:
                    Ra.append((spectrumJFM0[poswl[0]] / kyr) / (spectrumJAS0[poswl[0]] / kyr))
                elif box in south_boxes:
                    Ra.append((spectrumJAS0[poswl[0]] / kyr) / (spectrumJFM0[poswl[0]] / kyr))

        if ibox == box_legend:
            pp2X.plot_psd(inset_ax, np.squeeze(np.array(freqJAS)).T, psds=Ra, unit="m2",
                          psd_labels=modellabel,
                          legend=True, bba_leg=(4.5, 2), colors=colors, lsts=lsts,
                          xtick_show=True, ytick_show=True, xlabel_upper=False,
                          xlabel_lower=False,
                          wavelength_ticks=np.array([50, 250, 100, 500]),
                          ylabel=False, savefig=False,
                          plot_transparent=False, slope=False,
                          scaleX='log', scaleY='log')
        else:
            pp2X.plot_psd(inset_ax, np.squeeze(np.array(freqJAS)).T, psds=Ra, unit="m2",
                          psd_labels=modellabel,
                          legend=False, colors=colors, lsts=lsts,
                          xtick_show=True, ytick_show=True, xlabel_upper=False,
                          xlabel_lower=False,
                          wavelength_ticks=np.array([50, 250, 100, 500]),
                          ylabel=False, savefig=False,
                          plot_transparent=False, slope=False,
                          scaleX='log', scaleY='log')
        ibox = ibox + 1
        plt.axhline(y=1, color='gray', linestyle='--')
        inset_ax.set_ylim([1e-1, 1e1])
    ax.set_extent([cds[0] - 2, cds[1] + 2, cds[2] - 2, cds[3] + 2], crs=ccrs.PlateCarree())
    return
