#!/usr/bin/env python3
"""Figure S3 -- GLO36 with/without tides vs SWOT: seasonal-ratio scatters and
zonal-mean ratio sections.

Paper reference: Figures_SI/scatter_global_cumration_modelSWOT2_V2_tidesv2_150-350.png.

Ported from notebook/plot_cumpsd_ratio-scatter.ipynb cells 15-17 (the
"COMPARISION WITH DE-TIDED" section: the tides trio
GLO36V1/GLO36V1NOTIDE/SWOT data loads and the tidesv2 figure; its savefig
line is commented out in the notebook) plus the shared cells they depend on:
cell 5 (plot_spectral_scatter, 9-arg ratio version), cell 7 (box positions),
cell 12 (latitude-bin index). The compute ports live in
scripts/figures/_cumsd_helpers.py (see its docstring for the recorded
deviations shared with fig2_cumsd_ratio_scatter.py).

Recorded deviations from the notebook (only these):
- online reads replaced by read(key, box, season) from _common (offline cache
  default, --online for anonymous DIVE); endpoint_url/modeload/folder drop out
  (see _cumsd_helpers docstring). No GEOMAR in the tides model list.
- same read-substitution note for cells 15/16 re-loading R,F/psdsW/psdsS/
  psdsWL/psdsSL over the 3-key model list (overwriting cell-9/10-style
  variables, as the notebook does) and remap's geojson -> _common.GEOJSON.
- the commented-out notebook savefig ..._V2_tidesv2_{min}-{max}.png
  (min/max = 150/350 from cell 16) is replaced by save(fig, cfg,
  "<paper-reference stem>") writing PNG (300 dpi) + PDF, tight bbox;
  plt.show() is not ported.
- cell 17's comment lines are not ported (scripts carry no comments).

Everything else is exactly as in the committed notebook, including its
quirks: the scatter panels use letters[1..4] ("(b)".."(e)") although the paper
caption letters them (a)-(d); "(e)" then also titles the first zonal-mean
panel, so the letter (e) appears twice; the zonal-mean titles use the model
KEYS ("(f) GLO36V1", "(g)GLO36V1NOTIDE") and panel (f) carries
set_ylabel("Latitude"); the in-cell redefinition model=["GLO36","GLO36
DE-TIDED","SWOT"] is kept although unused; the empty 60-degree latitude bin
yields nan zonal means; the latindex 280-vs-282 alignment offset described
in the _cumsd_helpers docstring applies to the Fb1 computation.
"""

import argparse

import _common
from _common import add_arguments, resolve, save

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import matplotlib.colors as mcolors

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

    models = ["GLO36V1", "GLO36V1NOTIDE", "SWOT"]

    R, F = season_spec(read, models, selected, 50, 500, north_boxes, south_boxes, 'JFM', 'JAS')

    min_wavelength = 50
    max_wavelength = 150
    psdsW, psdsS, freqJAS = season_cum(read, models, selected, min_wavelength, max_wavelength,
                                       north_boxes, south_boxes, 'JFM', 'JAS')

    ZW, ZS = remap(psdsW, psdsS, models, _common.GEOJSON)

    min_wavelength = 150
    max_wavelength = 350
    models = ["GLO36V1", "GLO36V1NOTIDE", "SWOT"]

    psdsWL, psdsSL, freqJASL = season_cum(read, models, selected, min_wavelength, max_wavelength,
                                          north_boxes, south_boxes, 'JFM', 'JAS')

    ZWL, ZSL = remap(psdsWL, psdsSL, models, _common.GEOJSON)

    latindex, latpos, data = load_latindex(_common.GEOJSON)

    model = ["GLO36", "GLO36-DETIDED", "SWOT"]
    letters = ["(a)", "(b)", "(c)", "(d)", "(e)", "(f)", "(g)", "(h)", "(i)", "(j)", "(k)"]
    lon_edges = np.arange(-180, 181, 10)
    lat_edges = np.arange(-90, 91, 10)

    valmin = 0
    valmax = 2

    fig = plt.figure(figsize=(12, 8))

    outer = fig.add_gridspec(
        2, 1,
        height_ratios=[2, 1.5],
        hspace=0.28
    )

    gs_middle = outer[0].subgridspec(
        2, 2,
        hspace=0.3,
        wspace=0.3
    )

    ax = np.empty((2, 2), dtype=object)

    for i in range(2):
        for j in range(2):
            ax[i, j] = fig.add_subplot(gs_middle[i, j])

    fig.text(0.05, 0.75, '50-150 km', ha='center', fontsize=12, rotation=90)
    sc0 = plot_spectral_scatter(ax[0, 0], np.arange(0, 282), np.squeeze(psdsW[:, 0]), np.squeeze(psdsS[:, 0]),
                                np.squeeze(psdsW[:, 2]), np.squeeze(psdsS[:, 2]), " ", model[0], letters[1])
    sc1 = plot_spectral_scatter(ax[0, 1], np.arange(0, 282), np.squeeze(psdsW[:, 1]), np.squeeze(psdsS[:, 1]),
                                np.squeeze(psdsW[:, 2]), np.squeeze(psdsS[:, 2]), " ", model[1], letters[2])

    fig.text(0.05, 0.5, '150-350 km', ha='center', fontsize=12, rotation=90)
    sc0L = plot_spectral_scatter(ax[1, 0], np.arange(0, 282), np.squeeze(psdsWL[:, 0]), np.squeeze(psdsSL[:, 0]),
                                 np.squeeze(psdsWL[:, 2]), np.squeeze(psdsSL[:, 2]), "SWOT", model[0], letters[3])
    sc1L = plot_spectral_scatter(ax[1, 1], np.arange(0, 282), np.squeeze(psdsWL[:, 1]), np.squeeze(psdsSL[:, 1]),
                                 np.squeeze(psdsWL[:, 2]), np.squeeze(psdsSL[:, 2]), "SWOT", model[1], letters[4])

    gs_bottom = outer[1].subgridspec(
        1, 3,
        hspace=0.5,
        wspace=0.5
    )
    ax_new = np.empty((1, 3), dtype=object)

    for i in range(1):
        for j in range(3):
            ax_new[i, j] = fig.add_subplot(gs_bottom[i, j])

    F2 = F[models[0]]
    Wl = np.squeeze(F2[0])

    Fb1 = np.zeros((len(Wl), len(latindex), len(models)))

    kmod = 0
    for imodel in models:
        RM = R[imodel]
        for i in range(len(latindex)):
            k = 0
            pos = latindex[i][0]
            Fb0 = np.zeros((len(Wl)))
            for ilat in pos:
                Fb0 = Fb0 + np.interp(Wl, np.squeeze(F2[ilat]), np.squeeze(RM[ilat]))
                k = k + 1
            Fb1[:, i, kmod] = np.array(Fb0 / k)
        kmod = kmod + 1

    model = ["GLO36", "GLO36 DE-TIDED", "SWOT"]

    mymin = 1e1
    mymax = 1e-1
    norm = mcolors.LogNorm(vmin=mymin, vmax=mymax)
    imodel = 2
    pc = ax_new[0, 0].pcolormesh(latpos, (1 / Wl), np.squeeze(Fb1[:, :, imodel]), norm=norm, shading='nearest', cmap='seismic')
    ax_new[0, 0].set_ylabel("Wavelength")
    ax_new[0, 0].set_xlim([-60, 60])
    ax_new[0, 0].set_ylim([50, 420])
    ax_new[0, 0].set_title("(e)" + models[imodel])
    fig.colorbar(pc, ax=ax_new[0, 0])

    imodel = 0
    pc = ax_new[0, 1].pcolormesh(latpos, (1 / Wl), np.squeeze(Fb1[:, :, imodel]), norm=norm, shading='nearest', cmap='seismic')
    ax_new[0, 1].set_ylabel("Latitude")
    ax_new[0, 1].set_xlim([-60, 60])
    ax_new[0, 1].set_ylim([50, 420])
    ax_new[0, 1].set_title("(f) " + models[imodel])
    fig.colorbar(pc, ax=ax_new[0, 1])

    imodel = 1
    pc = ax_new[0, 2].pcolormesh(latpos, (1 / Wl), np.squeeze(Fb1[:, :, imodel]), norm=norm, shading='nearest', cmap='seismic')
    ax_new[0, 2].set_xlim([-60, 60])
    ax_new[0, 2].set_ylim([50, 420])
    ax_new[0, 2].set_title("(g)" + models[imodel])
    fig.colorbar(pc, ax=ax_new[0, 2])

    save(fig, cfg, "scatter_global_cumration_modelSWOT2_V2_tidesv2_150-350")
    print(f"done ({cfg.reads} spectra reads)")


if __name__ == "__main__":
    main()
