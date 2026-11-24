#!/usr/bin/env python3
"""Figure S6 -- Winter/summer ratio of the spectral-slope maps, with box counts.

Paper reference: Figures_SI/ratioslope_season_model_50-150.pdf.

Ported 1:1 from notebook/plot_slope_onl_v3+tides.ipynb cell 13 (figure) and
cell 11 (Boxes >1 / Boxes <1 counts, printed as in the notebook). Data chain =
cell 9 (slope statistics on the 50-150 km band for the 7-key model list,
remapped to global maps), shared with the other slope scripts and factored
into scripts/figures/_slope_helpers.py (load_slope_maps; plot_fig2v = cell 5).

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
  300 dpi PNG only (FigV2/ratioslope_season_model_50-150.png).
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
from _slope_helpers import load_slope_maps, plot_fig2v


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

    box_pos = np.zeros((7))
    box_neg = np.zeros((7))

    for imodel in range(7):
        box_neg[imodel] = len(np.where(m_slopeW2[imodel, :, :] / m_slopeS2[imodel, :, :] < 1)[0])
        box_pos[imodel] = len(np.where(m_slopeW2[imodel, :, :] / m_slopeS2[imodel, :, :] > 1)[0])

    print(box_pos)
    print(box_neg)

    model = ["GLO12", "GLO36", "GLO36-DETIDED", "NOC12", "NOC025", "LLC4320", "SWOT"]

    lon_edges = np.arange(-180, 181, 10)
    lat_edges = np.arange(-90, 91, 10)
    lon_edges2, lat_edges2 = np.meshgrid(lon_edges[:-1], lat_edges[:-1])

    valmin = 0
    valmax = 2
    fig, ax = plt.subplots(3, 2, figsize=(10, 8), subplot_kw={'projection': ccrs.PlateCarree()})
    fig.subplots_adjust(wspace=0.2, hspace=0.2)
    imodel = 6
    ax, mesh = plot_fig2v(ax, imodel, lon_edges2, lat_edges2, m_slopeW2, m_slopeS2, valmin, valmax, model, 0, 0, '(a) ', box_pos, box_neg)
    imodel = 5
    ax, mesh = plot_fig2v(ax, imodel, lon_edges2, lat_edges2, m_slopeW2, m_slopeS2, valmin, valmax, model, 0, 1, '(b) ', box_pos, box_neg)
    imodel = 1
    ax, mesh = plot_fig2v(ax, imodel, lon_edges2, lat_edges2, m_slopeW2, m_slopeS2, valmin, valmax, model, 1, 0, '(c) ', box_pos, box_neg)
    imodel = 0
    ax, mesh = plot_fig2v(ax, imodel, lon_edges2, lat_edges2, m_slopeW2, m_slopeS2, valmin, valmax, model, 1, 1, '(d) ', box_pos, box_neg)
    imodel = 3
    ax, mesh = plot_fig2v(ax, imodel, lon_edges2, lat_edges2, m_slopeW2, m_slopeS2, valmin, valmax, model, 2, 0, '(e) ', box_pos, box_neg)
    imodel = 4
    ax, mesh = plot_fig2v(ax, imodel, lon_edges2, lat_edges2, m_slopeW2, m_slopeS2, valmin, valmax, model, 2, 1, '(f) ', box_pos, box_neg)

    cbar_ax = fig.add_axes([0.92, 0.1, 0.01, .8])
    cbar = fig.colorbar(mesh, cax=cbar_ax, orientation='vertical', fraction=0.03, extend='both')
    cbar.set_label("Ratio slope spectra winter")

    save(fig, cfg, "ratioslope_season_model_50-150")
    print(f"done ({cfg.reads} spectra reads)")


if __name__ == "__main__":
    main()
