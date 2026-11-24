#!/usr/bin/env python3
"""Figure S1 -- GEOMAR Agulhas spectra per year (winter/summer/spring/fall).

Paper reference: Figures_SI/agulhas_spectrum_geomarperyear.png.

Ported 1:1 from notebook/region_plot_spectr_noonl_AG-Copy1-IMPR.ipynb
cell 11: GEOMAR-only panels -- the column-mean (3-year) spectrum against
each single year, per season pair (JFM, JAS, AMJ, OND; panel titles follow
the notebook's austral-season naming: Winter=JAS, Summer=JFM). GEOMAR reads
the local cache per-year files (private data, offline always).
"""

import argparse

import _common
from _common import add_arguments, resolve, save

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import position_function as pf
import plot_psd1Xglobal1 as pp2X
from _region_helpers import load_spectrum, reader_from


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    add_arguments(ap)
    args = ap.parse_args()
    cfg = resolve(args)
    read = reader_from(cfg)

    # note: cell 11 reuses cell 10's models list -- only GEOMAR is plotted
    models = ["GLO12V4", "GLO36V1", "NOC12", "NOC025", "LLC4320", "GEOMAR", "SWOT"]
    regcoordA = [0, 50, -50, -20]

    Wl = np.array([50, 85, 100, 150, 200, 300, 400, 500])
    selected, region_boxes = pf.position_boxes(_common.GEOJSON, regcoord=regcoordA)

    FbS_A, FbW_A, FbS_Ayr, FbW_Ayr = load_spectrum(read, region_boxes, models, 'JFM', 'JAS', Wl)
    FbF_A, FbSp_A, FbF_Ayr, FbSp_Ayr = load_spectrum(read, region_boxes, models, 'AMJ', 'OND', Wl)

    fig = plt.figure(figsize=(10, 8))
    yr_colors = ['saddlebrown', 'sandybrown', 'goldenrod', 'gold']
    yr_labels = ["Mean", "2021", "2022", "2023"]

    ax1 = fig.add_axes([0.1, 0.6, 0.3, 0.2])
    pp2X.plot_psd(ax1, 1 / Wl, [FbS_A[:, 0], FbS_Ayr[0, :], FbS_Ayr[1, :], FbS_Ayr[2, :]],
                  unit="m2", psd_labels=yr_labels, title="(a) Winter",
                  savefig=False, plot_transparent=False, legend=False,
                  colors=yr_colors, wavelength_ticks=Wl)
    ax1.set_ylim([1e-5, 1e1])
    ax2 = fig.add_axes([0.55, 0.6, 0.3, 0.2])
    pp2X.plot_psd(ax2, 1 / Wl, [FbW_A[:, 0], FbW_Ayr[0, :], FbW_Ayr[1, :], FbW_Ayr[2, :]],
                  unit="m2", psd_labels=yr_labels, title="(b) Summer",
                  savefig=False, plot_transparent=False, legend=True,
                  colors=yr_colors, wavelength_ticks=Wl)
    ax2.set_ylim([1e-5, 1e1])
    ax3 = fig.add_axes([0.1, 0.2, 0.3, 0.2])
    pp2X.plot_psd(ax3, 1 / Wl, [FbF_A[:, 0], FbF_Ayr[0, :], FbF_Ayr[1, :], FbF_Ayr[2, :]],
                  unit="m2", psd_labels=yr_labels, title="(c) Spring",
                  savefig=False, plot_transparent=False, legend=False,
                  colors=yr_colors, wavelength_ticks=Wl)
    ax3.set_ylim([1e-5, 1e1])
    ax4 = fig.add_axes([0.55, 0.2, 0.3, 0.2])
    pp2X.plot_psd(ax4, 1 / Wl, [FbSp_A[:, 0], FbSp_Ayr[0, :], FbSp_Ayr[1, :], FbSp_Ayr[2, :]],
                  unit="m2", psd_labels=yr_labels, title="(d) Fall",
                  savefig=False, plot_transparent=False, legend=False,
                  colors=yr_colors, wavelength_ticks=Wl)
    ax4.set_ylim([1e-5, 1e1])

    save(fig, cfg, "agulhas_spectrum_geomarperyear")
    print(f"done ({cfg.reads} spectra reads)")


if __name__ == "__main__":
    main()
