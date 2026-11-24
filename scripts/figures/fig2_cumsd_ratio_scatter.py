#!/usr/bin/env python3
"""Fig 2 -- global winter/summer spectral-ratio zonal sections, box map, and
model-vs-SWOT ratio scatters.

Paper reference: Figures/scatter_global_cumration_modelSWOT2_V3_150-350.png.

Ported from notebook/plot_cumpsd_ratio-scatter.ipynb cell 13 (the "V3"
figure; its savefig line is commented out in the notebook) plus every earlier
cell it depends on: cell 5 (plot_spectral_scatter, 9-arg ratio version),
cell 7 (box positions), cell 9 (season_spec ratios R,F over 50-500 km and
season_cum 50-150 km), cell 10 (season_cum 150-350 km), cell 12 (latitude-bin
index + geojson dict). cs.season_spec / cs.season_cum / cs.remap and
plot_spectral_scatter live in scripts/figures/_cumsd_helpers.py (see its
docstring for the recorded deviations shared with s3_cumsd_ratio_tides.py).

Recorded deviations from the notebook (only these):
- online reads replaced by read(key, box, season) from _common (offline cache
  default, --online for anonymous DIVE); cs.remapping arguments
  endpoint_url/modeload/folder drop out (see _cumsd_helpers docstring).
- cs.remap's bare "mostly_ocean_boxes_filtered.geojson" and cell 12's bare
  geojson open become _common.GEOJSON; cell 12's print(latindex[0]) dropped.
- the commented-out notebook savefig ..._V3_{min}-{max}.png (min/max = 150/350
  from cell 10) is replaced by save(fig, cfg, "<paper-reference stem>") which
  writes PNG (300 dpi) + PDF with a tight bbox; plt.show() is not ported
  (Agg scripts).
- ZW/ZS/ZWL/ZSL (remap outputs of cells 9/10) are computed but unused by
  cell 13; kept because the notebook computes them.
- cell 13's comment lines are not ported (scripts carry no comments).

Everything else -- model lists, the (a)-(f) mean and (g)-(l) std zonal
sections (LogNorm 1e1..1e-1 seismic, latpos x 1/Wl, +/-60 lat, 50-420 km
wavelength), the add_axes colorbar positions and labels, the (m) box map with
red 0-based index numbers, the 2x5 (n)-(w) scatters with fig.text band
labels, tight_layout calls, the "(f) "+models[imodel] key-label quirk, and
the latindex 280-vs-282 alignment offset -- is exactly as in the committed
notebook, so the script reproduces the notebook figure.
"""

import argparse

import _common
from _common import add_arguments, resolve, save

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import cartopy.crs as ccrs
import cartopy.feature as cfeature
import matplotlib.colors as mcolors
from shapely.geometry import shape

import position_function as pf
from _region_helpers import reader_from
from _cumsd_helpers import load_latindex, plot_spectral_scatter, remap, season_cum, season_spec


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    add_arguments(ap)
    args = ap.parse_args()
    cfg = resolve(args)
    read = reader_from(cfg)

    boxesjson = _common.GEOJSON
    north_boxes, south_boxes = pf.position_boxes_northsouth(boxesjson)
    selected = pf.position_boxes(boxesjson)

    min_wavelength = 50
    max_wavelength = 150
    models = ["GLO12V4", "GLO36V1", "NOC12", "NOC025", "LLC4320", "SWOT"]

    R, F = season_spec(read, models, selected, 50, 500, north_boxes, south_boxes, 'JFM', 'JAS')

    psdsW, psdsS, freqJAS = season_cum(read, models, selected, min_wavelength, max_wavelength,
                                       north_boxes, south_boxes, 'JFM', 'JAS')

    ZW, ZS = remap(psdsW, psdsS, models, _common.GEOJSON)

    min_wavelength = 150
    max_wavelength = 350
    models = ["GLO12V4", "GLO36V1", "NOC12", "NOC025", "LLC4320", "SWOT"]

    psdsWL, psdsSL, freqJASL = season_cum(read, models, selected, min_wavelength, max_wavelength,
                                         north_boxes, south_boxes, 'JFM', 'JAS')

    ZWL, ZSL = remap(psdsWL, psdsSL, models, _common.GEOJSON)

    latindex, latpos, data = load_latindex(_common.GEOJSON)

    model = ["GLO12", "GLO36", "NOC12", "NOC025", "LLC4320", "SWOT"]
    letters = ["(n)", "(o)", "(p)", "(q)", "(r)", "(s)", "(t)", "(u)", "(v)", "(w)"]
    lon_edges = np.arange(-180, 181, 10)
    lat_edges = np.arange(-90, 91, 10)

    valmin = 0
    valmax = 2

    fig = plt.figure(figsize=(14, 18))

    outer = fig.add_gridspec(
        3, 1,
        height_ratios=[2, 1.5, 1.5],
        hspace=0.28
    )

    gs_bottom = outer[0].subgridspec(
        2, 6,
        hspace=0.5,
        wspace=0.5
    )
    ax_new = np.empty((2, 6), dtype=object)

    for i in range(2):
        for j in range(6):
            ax_new[i, j] = fig.add_subplot(gs_bottom[i, j])

    F2 = F[models[0]]
    Wl = np.squeeze(F2[0])

    Fmean = np.zeros((len(Wl), len(latindex), len(models)))
    Fstd = np.zeros((len(Wl), len(latindex), len(models)))

    kmod = 0
    for imodel in models:
        RM = R[imodel]
        for i in range(len(latindex)):
            k = 0
            pos = latindex[i][0]

            F_interp = []

            for ilat in pos:
                F_interp.append(
                    np.interp(Wl, np.squeeze(F2[ilat]), np.squeeze(RM[ilat]))
                )
                k += 1
            F_interp = np.array(F_interp)
            Fmean[:, i, kmod] = np.mean(F_interp, axis=0)
            Fstd[:, i, kmod] = np.std(F_interp, axis=0)

        kmod = kmod + 1

    mymin = 1e1
    mymax = 1e-1
    norm = mcolors.LogNorm(vmin=mymin, vmax=mymax)
    imodel = 5
    pc = ax_new[0, 0].pcolormesh(latpos, (1 / Wl), np.squeeze(Fmean[:, :, imodel]), norm=norm, shading='nearest', cmap='seismic')
    ax_new[0, 0].set_ylabel("Wavelength")
    ax_new[0, 0].set_xlim([-60, 60])
    ax_new[0, 0].set_ylim([50, 420])
    ax_new[0, 0].set_title("(a) " + model[imodel])

    imodel = 4
    pc = ax_new[0, 1].pcolormesh(latpos, (1 / Wl), np.squeeze(Fmean[:, :, imodel]), norm=norm, shading='nearest', cmap='seismic')
    ax_new[0, 1].set_xlim([-60, 60])
    ax_new[0, 1].set_ylim([50, 420])
    ax_new[0, 1].set_title("(b) " + model[imodel])

    imodel = 1
    pc = ax_new[0, 2].pcolormesh(latpos, (1 / Wl), np.squeeze(Fmean[:, :, imodel]), norm=norm, shading='nearest', cmap='seismic')
    ax_new[0, 2].set_ylim([50, 420])
    ax_new[0, 2].set_xlim([-60, 60])
    ax_new[0, 2].set_title("(c) " + model[imodel])

    imodel = 0
    pc = ax_new[0, 3].pcolormesh(latpos, (1 / Wl), np.squeeze(Fmean[:, :, imodel]), norm=norm, shading='nearest', cmap='seismic')
    ax_new[0, 3].set_xlim([-60, 60])
    ax_new[0, 3].set_ylim([50, 420])
    ax_new[0, 3].set_title("(d) " + model[imodel])

    imodel = 2
    pc = ax_new[0, 4].pcolormesh(latpos, (1 / Wl), np.squeeze(Fmean[:, :, imodel]), norm=norm, shading='nearest', cmap='seismic')
    ax_new[0, 4].set_xlim([-60, 60])
    ax_new[0, 4].set_ylim([50, 420])
    ax_new[0, 4].set_title("(e) " + model[imodel])

    imodel = 3
    pc = ax_new[0, 5].pcolormesh(latpos, (1 / Wl), np.squeeze(Fmean[:, :, imodel]), norm=norm, shading='nearest', cmap='seismic')
    ax_new[0, 5].set_xlim([-60, 60])
    ax_new[0, 5].set_ylim([50, 420])
    ax_new[0, 5].set_title("(f) " + models[imodel])
    cbar_ax = fig.add_axes([0.92, 0.78, .01, 0.1])
    cbar = fig.colorbar(pc, cax=cbar_ax, orientation='vertical', fraction=0.02, extend='both')
    cbar.set_label("Winter/Summer ratio")
    plt.tight_layout()

    mymin = 0
    mymax = 2
    imodel = 5
    pc = ax_new[1, 0].pcolormesh(latpos, (1 / Wl), np.squeeze(Fstd[:, :, imodel]), vmin=mymin, vmax=mymax, shading='nearest', cmap='seismic')
    ax_new[1, 0].set_ylabel("Wavelength")
    ax_new[1, 0].set_xlabel("Latitude")
    ax_new[1, 0].set_xlim([-60, 60])
    ax_new[1, 0].set_ylim([50, 420])
    ax_new[1, 0].set_title("(g) " + model[imodel])

    imodel = 4
    pc = ax_new[1, 1].pcolormesh(latpos, (1 / Wl), np.squeeze(Fstd[:, :, imodel]), vmin=mymin, vmax=mymax, shading='nearest', cmap='seismic')
    ax_new[1, 1].set_xlabel("Latitude")
    ax_new[1, 1].set_xlim([-60, 60])
    ax_new[1, 1].set_ylim([50, 420])
    ax_new[1, 1].set_title("(h) " + model[imodel])

    imodel = 1
    pc = ax_new[1, 2].pcolormesh(latpos, (1 / Wl), np.squeeze(Fstd[:, :, imodel]), vmin=mymin, vmax=mymax, shading='nearest', cmap='seismic')
    ax_new[1, 2].set_xlabel("Latitude")
    ax_new[1, 2].set_ylim([50, 420])
    ax_new[1, 2].set_xlim([-60, 60])
    ax_new[1, 2].set_title("(i) " + model[imodel])

    imodel = 0
    pc = ax_new[1, 3].pcolormesh(latpos, (1 / Wl), np.squeeze(Fstd[:, :, imodel]), vmin=mymin, vmax=mymax, shading='nearest', cmap='seismic')
    ax_new[1, 3].set_xlabel("Latitude")
    ax_new[1, 3].set_xlim([-60, 60])
    ax_new[1, 3].set_ylim([50, 420])
    ax_new[1, 3].set_title("(j) " + model[imodel])

    imodel = 2
    pc = ax_new[1, 4].pcolormesh(latpos, (1 / Wl), np.squeeze(Fstd[:, :, imodel]), vmin=mymin, vmax=mymax, shading='nearest', cmap='seismic')
    ax_new[1, 4].set_xlim([-60, 60])
    ax_new[1, 4].set_ylim([50, 420])
    ax_new[1, 4].set_xlabel("Latitude")
    ax_new[1, 4].set_title("(k) " + model[imodel])

    imodel = 3
    pc = ax_new[1, 5].pcolormesh(latpos, (1 / Wl), np.squeeze(Fstd[:, :, imodel]), vmin=mymin, vmax=mymax, shading='nearest', cmap='seismic')
    ax_new[1, 5].set_xlabel("Latitude")
    ax_new[1, 5].set_xlim([-60, 60])
    ax_new[1, 5].set_ylim([50, 420])
    ax_new[1, 5].set_title("(l) " + model[imodel])
    cbar_ax = fig.add_axes([0.92, 0.62, .01, 0.1])
    cbar = fig.colorbar(pc, cax=cbar_ax, orientation='vertical', fraction=0.02, extend='both')
    cbar.set_label("Winter/Summer ratio ")
    plt.tight_layout()

    ax_big = fig.add_subplot(
        outer[1].subgridspec(1, 1)[0],
        projection=ccrs.PlateCarree()
    )

    ax_big.set_global()
    ax_big.add_feature(cfeature.LAND, facecolor="lightgray")
    ax_big.add_feature(cfeature.COASTLINE)

    for i, feature in enumerate(data["features"]):

        poly = shape(feature["geometry"])

        ax_big.add_geometries(
            [poly],
            ccrs.PlateCarree(),
            edgecolor="black",
            facecolor="none",
            linewidth=0.8
        )

        lon_min, lat_min, lon_max, lat_max = poly.bounds
        lon_c = 0.5 * (lon_min + lon_max)
        lat_c = 0.5 * (lat_min + lat_max)

        ax_big.text(
            lon_c, lat_c,
            str(i),
            transform=ccrs.PlateCarree(),
            ha="center",
            va="center",
            fontsize=6,
            color="red"
        )

    ax_big.set_title("(m) 10°×10° Boxes with Index Numbers")

    gs_middle = outer[2].subgridspec(
        2, 5,
        hspace=0.4,
        wspace=0.4
    )

    ax = np.empty((2, 5), dtype=object)

    for i in range(2):
        for j in range(5):
            ax[i, j] = fig.add_subplot(gs_middle[i, j])

    fig.text(0.05, 0.25, '50-150 km', ha='center', fontsize=14, rotation=90)
    imodel = 4
    sc0 = plot_spectral_scatter(ax[0, 0], np.arange(0, 282), np.squeeze(psdsW[:, imodel]), np.squeeze(psdsS[:, imodel]),
                                np.squeeze(psdsW[:, 5]), np.squeeze(psdsS[:, 5]), " ", model[imodel], letters[0])
    imodel = 1
    sc1 = plot_spectral_scatter(ax[0, 1], np.arange(0, 282), np.squeeze(psdsW[:, imodel]), np.squeeze(psdsS[:, imodel]),
                                np.squeeze(psdsW[:, 5]), np.squeeze(psdsS[:, 5]), " ", model[imodel], letters[1])
    imodel = 0
    sc2 = plot_spectral_scatter(ax[0, 2], np.arange(0, 282), np.squeeze(psdsW[:, imodel]), np.squeeze(psdsS[:, imodel]),
                                np.squeeze(psdsW[:, 5]), np.squeeze(psdsS[:, 5]), " ", model[imodel], letters[2])
    imodel = 2
    sc3 = plot_spectral_scatter(ax[0, 3], np.arange(0, 282), np.squeeze(psdsW[:, imodel]), np.squeeze(psdsS[:, imodel]),
                                np.squeeze(psdsW[:, 5]), np.squeeze(psdsS[:, 5]), " ", model[imodel], letters[3])
    imodel = 3
    sc4 = plot_spectral_scatter(ax[0, 4], np.arange(0, 282), np.squeeze(psdsW[:, imodel]), np.squeeze(psdsS[:, imodel]),
                                np.squeeze(psdsW[:, 5]), np.squeeze(psdsS[:, 5]), " ", model[imodel], letters[4])

    fig.text(0.05, 0.15, '150-350 km', ha='center', fontsize=14, rotation=90)
    imodel = 4
    sc0L = plot_spectral_scatter(ax[1, 0], np.arange(0, 282), np.squeeze(psdsWL[:, imodel]), np.squeeze(psdsSL[:, imodel]),
                                 np.squeeze(psdsWL[:, 5]), np.squeeze(psdsSL[:, 5]), "SWOT", model[imodel], letters[5])
    imodel = 1
    sc1L = plot_spectral_scatter(ax[1, 1], np.arange(0, 282), np.squeeze(psdsWL[:, imodel]), np.squeeze(psdsSL[:, imodel]),
                                 np.squeeze(psdsWL[:, 5]), np.squeeze(psdsSL[:, 5]), "SWOT", model[imodel], letters[6])
    imodel = 0
    sc2L = plot_spectral_scatter(ax[1, 2], np.arange(0, 282), np.squeeze(psdsWL[:, imodel]), np.squeeze(psdsSL[:, imodel]),
                                 np.squeeze(psdsWL[:, 5]), np.squeeze(psdsSL[:, 5]), "SWOT", model[imodel], letters[7])
    imodel = 2
    sc3L = plot_spectral_scatter(ax[1, 3], np.arange(0, 282), np.squeeze(psdsWL[:, imodel]), np.squeeze(psdsSL[:, imodel]),
                                 np.squeeze(psdsWL[:, 5]), np.squeeze(psdsSL[:, 5]), "SWOT", model[imodel], letters[8])
    imodel = 3
    sc4L = plot_spectral_scatter(ax[1, 4], np.arange(0, 282), np.squeeze(psdsWL[:, imodel]), np.squeeze(psdsSL[:, imodel]),
                                 np.squeeze(psdsWL[:, 5]), np.squeeze(psdsSL[:, 5]), "SWOT", model[imodel], letters[9])

    cbar_ax = fig.add_axes([0.12, 0.35, .8, 0.01])
    cbar = fig.colorbar(sc3, cax=cbar_ax, orientation='horizontal', fraction=0.02, extend='both')
    cbar.set_label("Boxes Index")
    plt.tight_layout()

    save(fig, cfg, "scatter_global_cumration_modelSWOT2_V3_150-350")
    print(f"done ({cfg.reads} spectra reads)")


if __name__ == "__main__":
    main()
