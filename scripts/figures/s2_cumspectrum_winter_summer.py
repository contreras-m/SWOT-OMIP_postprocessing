#!/usr/bin/env python3
"""Figure S2 -- combined winter/summer scatterplots of the models-vs-SWOT
cumulative spectra.

Paper reference: Figures_SI/scatter_global_cumspectrum_modelSWOT2_winter-summer_150-350.png
(caption: scatterplots of the cumulative spectra (winter and summer) of the
models versus SWOT for (a-b) 50-150 km and (c-d) 150-350 km, with the
corresponding R2 values; colors = box indices per Fig. 2m).

Ported from notebook/plot_cumpsd_scatterplt_SI.ipynb cells 13 (winter figure)
and 14 (summer figure) plus the shared cells they depend on: cell 5
(plot_spectral_scatter, 7-arg cumulative-spectra version), cell 7 (box
positions), cells 9/10 (season_cum 50-150 km and 150-350 km). The compute
ports live in scripts/figures/_cumsd_helpers.py (see its docstring for the
recorded deviations shared with fig2_cumsd_ratio_scatter.py and
s3_cumsd_ratio_tides.py).

USER-DECISION arrangement (the only new part): the notebook saves the WINTER
and SUMMER figures as separate files (each: box-map panel (a) + 10 scatter
panels); the paper reference is ONE COMBINED figure, so this script renders
the combined 2x2 grid of season/band groups matching the caption:
row "50-150 km": (a) winter 50-150, (b) summer 50-150;
row "150-350 km": (c) winter 150-350, (d) summer 150-350;
winter = left five-model group, summer = right five-model group of each pair.
Each group holds the notebook's model-row panels (LLC4320, GLO36, GLO12,
NOC12, NOC025 order, i.e. notebook imodel 4,1,0,2,3) with per-panel content
identical to the notebook's per-panel plotting code (nipy_spectral
box-index colors, R2 annotation, 1e-7..1e-1 log-log axes, "k--" 1:1 line,
" "/model-name and "SWOT" x/y labels, " " title).

Recorded deviations from the notebook (only these):
- combined arrangement above (single figure; the notebook's two separate
  figures and their duplicate model/letters/valmin/valmax/lon_edges/
  lat_edges definitions are merged; each notebook figure's band fig.text is
  kept once per band row).
- the notebook's box-index map panel "(a) 10x10 Boxes with Index Numbers"
  and its cartopy stack are NOT ported: the combined caption locates the box
  indices via Fig. 2m instead, and the four panel groups are the content.
- one shared "Boxes Index" colorbar (notebook: fig.add_axes([0.12, 0.6, .8,
  0.01]) per figure) placed between the two band rows; its add_axes y-position
  is adapted to the two-row layout.
- the notebooks' per-panel letter titles ("(b)".."(k)", reused by both
  seasons) become blank panel titles; the season/band groups carry the
  caption letters as fig.text labels ("(a) Winter", "(b) Summer",
  "(c) Winter", "(d) Summer"; notebook has no group-letter analog).
- online reads replaced by read(key, box, season) from _common (offline
  cache default, --online for anonymous DIVE); no GEOMAR in the model list;
  remap's geojson -> _common.GEOJSON; ZW/ZS/ZWL/ZSL (remap outputs) are
  computed but unused by the scatter cells, kept because the notebook
  computes them.
- the commented-out notebook savefigs ..._winter_{min}-{max}.png /
  ..._summer_{min}-{max}.png are replaced by the single save(fig, cfg,
  "<paper-reference stem>") writing PNG (300 dpi) + PDF, tight bbox;
  plt.show() is not ported; comment lines are not ported.
"""

import argparse

import _common
from _common import add_arguments, resolve, save

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import position_function as pf
from _region_helpers import reader_from
from _cumsd_helpers import plot_spectral_scatter_cumspectrum, remap, season_cum


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

    psdsW, psdsS, freqJAS = season_cum(read, models, selected, min_wavelength, max_wavelength,
                                       north_boxes, south_boxes, 'JFM', 'JAS')

    ZW, ZS = remap(psdsW, psdsS, models, _common.GEOJSON)

    min_wavelength = 150
    max_wavelength = 350
    models = ["GLO12V4", "GLO36V1", "NOC12", "NOC025", "LLC4320", "SWOT"]

    psdsWL, psdsSL, freqJASL = season_cum(read, models, selected, min_wavelength, max_wavelength,
                                          north_boxes, south_boxes, 'JFM', 'JAS')

    ZWL, ZSL = remap(psdsWL, psdsSL, models, _common.GEOJSON)

    model = ["GLO12", "GLO36", "NOC12", "NOC025", "LLC4320", "SWOT"]
    lon_edges = np.arange(-180, 181, 10)
    lat_edges = np.arange(-90, 91, 10)

    valmin = 0
    valmax = 2

    fig = plt.figure(figsize=(28, 6.4))

    outer = fig.add_gridspec(
        2, 1,
        left=0.055,
        right=0.99,
        top=0.90,
        bottom=0.14,
        hspace=0.9
    )

    gs_top = outer[0].subgridspec(1, 10, wspace=0.4)
    gs_bottom = outer[1].subgridspec(1, 10, wspace=0.4)

    ax = np.empty((2, 10), dtype=object)

    for j in range(10):
        ax[0, j] = fig.add_subplot(gs_top[j])
        ax[1, j] = fig.add_subplot(gs_bottom[j])

    fig.text(0.015, 0.77, '50-150 km', ha='center', fontsize=14, rotation=90)
    fig.text(0.282, 0.935, '(a) Winter', ha='center', fontsize=14)
    fig.text(0.763, 0.935, '(b) Summer', ha='center', fontsize=14)

    imodel = 4
    sc0 = plot_spectral_scatter_cumspectrum(ax[0, 0], np.arange(0, 282), np.squeeze(psdsW[:, imodel]), np.squeeze(psdsW[:, 5]), " ", model[imodel], " ")
    imodel = 1
    sc1 = plot_spectral_scatter_cumspectrum(ax[0, 1], np.arange(0, 282), np.squeeze(psdsW[:, imodel]), np.squeeze(psdsW[:, 5]), " ", model[imodel], " ")
    imodel = 0
    sc2 = plot_spectral_scatter_cumspectrum(ax[0, 2], np.arange(0, 282), np.squeeze(psdsW[:, imodel]), np.squeeze(psdsW[:, 5]), " ", model[imodel], " ")
    imodel = 2
    sc3 = plot_spectral_scatter_cumspectrum(ax[0, 3], np.arange(0, 282), np.squeeze(psdsW[:, imodel]), np.squeeze(psdsW[:, 5]), " ", model[imodel], " ")
    imodel = 3
    sc4 = plot_spectral_scatter_cumspectrum(ax[0, 4], np.arange(0, 282), np.squeeze(psdsW[:, imodel]), np.squeeze(psdsW[:, 5]), " ", model[imodel], " ")

    imodel = 4
    sc0 = plot_spectral_scatter_cumspectrum(ax[0, 5], np.arange(0, 282), np.squeeze(psdsS[:, imodel]), np.squeeze(psdsS[:, 5]), " ", model[imodel], " ")
    imodel = 1
    sc1 = plot_spectral_scatter_cumspectrum(ax[0, 6], np.arange(0, 282), np.squeeze(psdsS[:, imodel]), np.squeeze(psdsS[:, 5]), " ", model[imodel], " ")
    imodel = 0
    sc2 = plot_spectral_scatter_cumspectrum(ax[0, 7], np.arange(0, 282), np.squeeze(psdsS[:, imodel]), np.squeeze(psdsS[:, 5]), " ", model[imodel], " ")
    imodel = 2
    sc3 = plot_spectral_scatter_cumspectrum(ax[0, 8], np.arange(0, 282), np.squeeze(psdsS[:, imodel]), np.squeeze(psdsS[:, 5]), " ", model[imodel], " ")
    imodel = 3
    sc4 = plot_spectral_scatter_cumspectrum(ax[0, 9], np.arange(0, 282), np.squeeze(psdsS[:, imodel]), np.squeeze(psdsS[:, 5]), " ", model[imodel], " ")

    fig.text(0.015, 0.27, '150-350 km', ha='center', fontsize=14, rotation=90)
    fig.text(0.282, 0.44, '(c) Winter', ha='center', fontsize=14)
    fig.text(0.763, 0.44, '(d) Summer', ha='center', fontsize=14)

    imodel = 4
    sc0L = plot_spectral_scatter_cumspectrum(ax[1, 0], np.arange(0, 282), np.squeeze(psdsWL[:, imodel]), np.squeeze(psdsWL[:, 5]), "SWOT", model[imodel], " ")
    imodel = 1
    sc1L = plot_spectral_scatter_cumspectrum(ax[1, 1], np.arange(0, 282), np.squeeze(psdsWL[:, imodel]), np.squeeze(psdsWL[:, 5]), "SWOT", model[imodel], " ")
    imodel = 0
    sc2L = plot_spectral_scatter_cumspectrum(ax[1, 2], np.arange(0, 282), np.squeeze(psdsWL[:, imodel]), np.squeeze(psdsWL[:, 5]), "SWOT", model[imodel], " ")
    imodel = 2
    sc3L = plot_spectral_scatter_cumspectrum(ax[1, 3], np.arange(0, 282), np.squeeze(psdsWL[:, imodel]), np.squeeze(psdsWL[:, 5]), "SWOT", model[imodel], " ")
    imodel = 3
    sc4L = plot_spectral_scatter_cumspectrum(ax[1, 4], np.arange(0, 282), np.squeeze(psdsWL[:, imodel]), np.squeeze(psdsWL[:, 5]), "SWOT", model[imodel], " ")

    imodel = 4
    sc0L = plot_spectral_scatter_cumspectrum(ax[1, 5], np.arange(0, 282), np.squeeze(psdsSL[:, imodel]), np.squeeze(psdsSL[:, 5]), "SWOT", model[imodel], " ")
    imodel = 1
    sc1L = plot_spectral_scatter_cumspectrum(ax[1, 6], np.arange(0, 282), np.squeeze(psdsSL[:, imodel]), np.squeeze(psdsSL[:, 5]), "SWOT", model[imodel], " ")
    imodel = 0
    sc2L = plot_spectral_scatter_cumspectrum(ax[1, 7], np.arange(0, 282), np.squeeze(psdsSL[:, imodel]), np.squeeze(psdsSL[:, 5]), "SWOT", model[imodel], " ")
    imodel = 2
    sc3L = plot_spectral_scatter_cumspectrum(ax[1, 8], np.arange(0, 282), np.squeeze(psdsSL[:, imodel]), np.squeeze(psdsSL[:, 5]), "SWOT", model[imodel], " ")
    imodel = 3
    sc4L = plot_spectral_scatter_cumspectrum(ax[1, 9], np.arange(0, 282), np.squeeze(psdsSL[:, imodel]), np.squeeze(psdsSL[:, 5]), "SWOT", model[imodel], " ")

    cbar_ax = fig.add_axes([0.12, 0.52, .8, 0.01])
    cbar = fig.colorbar(sc3, cax=cbar_ax, orientation='horizontal', fraction=0.02, extend='both')
    cbar.set_label("Boxes Index")

    save(fig, cfg, "scatter_global_cumspectrum_modelSWOT2_winter-summer_150-350")
    print(f"done ({cfg.reads} spectra reads)")


if __name__ == "__main__":
    main()
