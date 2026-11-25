#!/usr/bin/env python3
"""Fig 4 -- Winter spectral-slope maps + zonal-average slope panels.

Paper reference: Figures/winterslope_season_zonalaverage_V2_50-150.png.

Ported 1:1 from notebook/plot_slope_onl_v3+tides.ipynb cell 12. Data chain =
cell 9 (slope statistics on the 50-150 km band for the 7-key model list,
remapped to global maps), shared with the other slope scripts and factored
into scripts/figures/_slope_helpers.py (load_slope_maps; plot_fig = cell 4).

Recorded deviations from the notebook (only these):
- data reads: the notebook's cs.season_slope -> read_season online S3 reads
  (DIVE MinIO, project-meom-ige/OMIP/Global/) are substituted by
  read(key, box, season, year=None) from _common -- offline cache
  figure_cache/GLOBALv2/ by default, anonymous DIVE with --online
  (see _slope_helpers docstring).
- cell 7's position_boxes calls take _common.GEOJSON (absolute) instead of the
  bare "mostly_ocean_boxes_filtered.geojson"; cs.remap likewise
  (via _slope_helpers).
- the in-cell importlib.reload of cell 2 and in-cell matplotlib/cartopy
  imports are covered by the script's top-level imports; commented-out
  notebook lines (incl. the commented savefig) are not ported.
- plt.show() is replaced by save() writing <stem>.png + <stem>.pdf (300 dpi,
  tight bbox) under figures_out/ -- the notebook's commented savefig wrote a
  300 dpi PNG only (FigV2/winterslope_season_zonalaverage_V2_50-150.png).
"""

import argparse

import _common
from _common import add_arguments, resolve, save

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import cartopy.crs as ccrs

import position_function as pf
from _region_helpers import reader_from
from _slope_helpers import load_slope_maps, plot_fig


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    add_arguments(ap)
    args = ap.parse_args()
    cfg = resolve(args)
    read = reader_from(cfg)

    north_boxes, south_boxes = pf.position_boxes_northsouth(_common.GEOJSON)
    selected = pf.position_boxes(_common.GEOJSON)
    m_slopeW2, m_slopeS2, s_slopeW2, s_slopeS2 = load_slope_maps(read, selected,
                                                                north_boxes, south_boxes)

    model = ["GLO12", "GLO36", "GLO36-DETIDED", "NOC12", "NOC025", "LLC4320", "SWOT"]
    lsty = ['dashdot', 'dotted', 'solid', 'solid', 'solid', 'dotted', 'solid', 'solid']

    colors = ["#E6194B", "#3CB44B", "#3CB44B", "#FFE119", "#4363D8", "pink", "k"]

    lon_edges = np.arange(-180, 181, 10)
    lat_edges = np.arange(-90, 91, 10)

    valmin = 1
    valmax = 9

    lon_edges = np.arange(-180, 181, 10)
    lat_edges = np.arange(-90, 91, 10)
    lon_edges2, lat_edges2 = np.meshgrid(lon_edges[:-1], lat_edges[:-1])

    fig = plt.figure(figsize=(10, 10))
    fig.subplots_adjust(wspace=0.1, hspace=0.3)

    ax = np.empty((4, 2), dtype=object)

    for r in range(4):
        for c in range(2):
            idx = r * 2 + c + 1

            if r < 3:
                ax[r, c] = fig.add_subplot(
                    4, 2, idx,
                    projection=ccrs.PlateCarree()
                )
            else:
                ax[r, c] = fig.add_subplot(4, 2, idx)

    imodel = 6
    ax, mesh = plot_fig(ax, imodel, lon_edges2, lat_edges2, m_slopeW2, valmin, valmax, model, 0, 0, '(a) ')
    imodel = 5
    ax, mesh = plot_fig(ax, imodel, lon_edges2, lat_edges2, m_slopeW2, valmin, valmax, model, 0, 1, '(b) ')
    imodel = 1
    ax, mesh = plot_fig(ax, imodel, lon_edges2, lat_edges2, m_slopeW2, valmin, valmax, model, 1, 0, '(c) ')
    imodel = 0
    ax, mesh = plot_fig(ax, imodel, lon_edges2, lat_edges2, m_slopeW2, valmin, valmax, model, 1, 1, '(d) ')
    imodel = 3
    ax, mesh = plot_fig(ax, imodel, lon_edges2, lat_edges2, m_slopeW2, valmin, valmax, model, 2, 0, '(e) ')
    imodel = 4
    ax, mesh = plot_fig(ax, imodel, lon_edges2, lat_edges2, m_slopeW2, valmin, valmax, model, 2, 1, '(f) ')

    cbar_ax = fig.add_axes([0.92, 0.1, 0.01, .8])
    cbar = fig.colorbar(mesh, cax=cbar_ax, orientation='vertical', fraction=0.02, extend='both')
    cbar.set_label("Ratio Slope spectra Winter/Summer")

    for i in range(len(colors)):
        ax[3, 0].plot(lat_edges[:-1], np.nanmean(m_slopeW2[i, :, :], axis=1).T, label=model[i],
                      color=colors[i], linestyle=lsty[i])
    ax[3, 0].set_xlabel("Latitude")
    ax[3, 0].set_ylabel("Slope spectra")
    ax[3, 0].set_title('(g) Zonal average slope spectra winter')
    ax[3, 0].set_ylim([1, 8])
    ax[3, 0].set_xlim([-70, 60])
    ax[3, 0].axhline(y=2, linestyle=':', linewidth=1)
    ax[3, 0].axhline(y=4, linestyle=':', linewidth=1)
    ax[3, 0].axhline(y=6, linestyle=':', linewidth=1)

    for i in range(len(colors)):
        ax[3, 1].plot(lat_edges[:-1], np.nanmean(m_slopeS2[i, :, :], axis=1).T, label=model[i],
                      color=colors[i], linestyle=lsty[i])
    ax[3, 1].set_title('(h) Zonal average slope spectra summer')
    ax[3, 1].set_xlabel("Latitude")
    ax[3, 1].legend(loc='upper right', handlelength=3, fontsize=5)
    ax[3, 1].set_ylim([1, 8])
    ax[3, 1].set_xlim([-70, 60])
    ax[3, 1].axhline(y=2, linestyle=':', linewidth=1)
    ax[3, 1].axhline(y=4, linestyle=':', linewidth=1)
    ax[3, 1].axhline(y=6, linestyle=':', linewidth=1)

    save(fig, cfg, "winterslope_season_zonalaverage_V2_50-150")
    print(f"done ({cfg.reads} spectra reads)")


if __name__ == "__main__":
    main()
