#!/usr/bin/env python3
"""Figure S4 -- maps of the winter-to-summer cumulative-spectrum ratio.

Paper reference: Figures_SI/cumspectrumratio_model_50-150.pdf (PNG+PDF on sync).

Ported 1:1 from notebook/plot_cumratio_map.ipynb (uploaded by contreras-m on
2026-11-25, commit 9886daf): cell 8 (cs.season_cum/cs.remap compute over all
boxes, JFM/JAS, 50-150 km, GLO12V4/GLO36V1/NOC12/NOC025/LLC4320/SWOT),
cell 4 (plot_fig map), cell 10 (3x2 panel figure, (a) SWOT -> (f) NOC025,
vmin/vmax 0-2, box-count annotations, colorbar).

Recorded deviations (only these):
- the notebook's online reads (cum_sp_onl_season_v3.season_cum /
  cs.remap with modeload='online', DIVE endpoint) are replaced by the
  ported _cumsd_helpers.season_cum / remap with the injected reader
  (offline cache default, --online for anonymous DIVE);
- geojson via the absolute _common.GEOJSON path (remap takes it explicitly);
- save() writes PNG+PDF with a tight crop under the paper-reference stem
  instead of the notebook's FigV2/cumspectrumratio_model_50-150.png;
- plt.show() not ported.
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

import position_function as pf
from _cumsd_helpers import remap, season_cum
from _region_helpers import reader_from


def plot_fig(ax, imodel, lon_edges, lat_edges, ZW, ZS, valmin, valmax, model,
             posx, posy, abc, box_pos, box_neg):
    ax[posx, posy].add_feature(cfeature.COASTLINE)
    ax[posx, posy].add_feature(cfeature.LAND, facecolor="lightgray")
    mesh = ax[posx, posy].pcolormesh(
        lon_edges,
        lat_edges,
        np.squeeze(ZW[imodel, :, :] / ZS[imodel, :, :]),
        vmin=valmin,
        vmax=valmax,
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


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    add_arguments(ap)
    args = ap.parse_args()
    cfg = resolve(args)
    read = reader_from(cfg)

    # ----------------------------- notebook cell 6 -----------------------
    north_boxes, south_boxes = pf.position_boxes_northsouth(_common.GEOJSON)
    selected = pf.position_boxes(_common.GEOJSON)

    # ----------------------------- notebook cell 8 -----------------------
    min_wavelength = 50
    max_wavelength = 150
    models = ["GLO12V4", "GLO36V1", "NOC12", "NOC025", "LLC4320", "SWOT"]

    psdsW, psdsS, freqJAS = season_cum(read, models, selected,
                                       min_wavelength, max_wavelength,
                                       north_boxes, south_boxes, 'JFM', 'JAS')

    ZW, ZS = remap(psdsW, psdsS, models, _common.GEOJSON)

    # ----------------------------- notebook cell 10 ----------------------
    model = ["GLO12", "GLO36", "NOC12", "NOC025", "LLC4320", "SWOT"]
    box_pos = np.zeros((6))
    box_neg = np.zeros((6))

    for imodel in range(6):
        box_neg[imodel] = len(np.where(ZW[imodel, :, :] / ZS[imodel, :, :] < 1)[0])
        box_pos[imodel] = len(np.where(ZW[imodel, :, :] / ZS[imodel, :, :] > 1)[0])

    lon_edges = np.arange(-180, 181, 10)
    lat_edges = np.arange(-90, 91, 10)

    valmin = 0
    valmax = 2
    fig, ax = plt.subplots(3, 2, figsize=(10, 8),
                           subplot_kw={'projection': ccrs.PlateCarree()})
    fig.subplots_adjust(wspace=0.2, hspace=0.2)
    imodel = 5
    ax, mesh = plot_fig(ax, imodel, lon_edges, lat_edges, ZW, ZS, valmin, valmax, model, 0, 0, '(a) ', box_pos, box_neg)
    imodel = 4
    ax, mesh = plot_fig(ax, imodel, lon_edges, lat_edges, ZW, ZS, valmin, valmax, model, 0, 1, '(b) ', box_pos, box_neg)
    imodel = 1
    ax, mesh = plot_fig(ax, imodel, lon_edges, lat_edges, ZW, ZS, valmin, valmax, model, 1, 0, '(c) ', box_pos, box_neg)
    imodel = 0
    ax, mesh = plot_fig(ax, imodel, lon_edges, lat_edges, ZW, ZS, valmin, valmax, model, 1, 1, '(d) ', box_pos, box_neg)
    imodel = 2
    ax, mesh = plot_fig(ax, imodel, lon_edges, lat_edges, ZW, ZS, valmin, valmax, model, 2, 0, '(e) ', box_pos, box_neg)
    imodel = 3
    ax, mesh = plot_fig(ax, imodel, lon_edges, lat_edges, ZW, ZS, valmin, valmax, model, 2, 1, '(f) ', box_pos, box_neg)

    cbar_ax = fig.add_axes([0.92, 0.1, 0.01, .8])
    cbar = fig.colorbar(mesh, cax=cbar_ax, orientation='vertical',
                        fraction=0.02, extend='both')
    cbar.set_label("Cum. spectral ratio  Winter/Summer")

    save(fig, cfg, f"cumspectrumratio_model_{min_wavelength}-{max_wavelength}")
    print(f"done ({cfg.reads} spectra reads)")


if __name__ == "__main__":
    main()
