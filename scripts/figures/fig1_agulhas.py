#!/usr/bin/env python3
"""Fig 1 -- Agulhas region spectra and seasonal ratio.

Paper reference: Figures/agulhas_modelsswot.png (PNG + PDF on sync).

Ported 1:1 from notebook/region_plot_spectr_noonl_AG-Copy1-IMPR.ipynb
cell 10. Season semantics preserved as committed: for the southern-hemisphere
Agulhas boxes, JFM = austral summer and JAS = austral winter -- the notebook
variable names (FbW = JFM, FbS = JAS) follow northern conventions; panel
(b) "Winter" plots FbS (JAS), panel (c) "Summer" plots FbW (JFM), and the
(d) ratio is JAS/JFM (aural winter/summer). GEOMAR reads the local cache
per-year files; the year-less JAS reads are the disclosed stand-ins
(figure_cache/GLOBALv2/GEOMAR/_yearless_provenance.md).
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
from _region_helpers import load_spectrum, plot_boxspectrum, reader_from


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    add_arguments(ap)
    args = ap.parse_args()
    cfg = resolve(args)
    read = reader_from(cfg)

    # --------------------- notebook cell 10 variables ---------------------
    models = ["GLO12V4", "GLO36V1", "NOC12", "NOC025", "LLC4320", "GEOMAR", "SWOT"]
    modellabel = ["GLO12", "GLO36", "NOC12", "NOC025", "LLC4320", "GEOMAR", "SWOT"]
    lst = ['dashdot', 'dashed', 'solid', 'solid', 'dashed', 'solid', 'solid']
    colors = [
        "#E6194B",   # red
        "#3CB44B",   # green
        "#FFE119",   # yellow
        "#4363D8",   # blue
        "pink",      # purple
        "#F58231",
        "k",
    ]
    regcoordA = [0, 50, -50, -20]  # lon_min, lon_max, lat_min, lat_max

    selected, region_boxes = pf.position_boxes(_common.GEOJSON, regcoord=regcoordA)
    north_boxes, south_boxes = pf.position_boxes_northsouth(_common.GEOJSON)

    fig = plt.figure(figsize=(12, 13))
    plot_boxspectrum(fig, region_boxes, models, modellabel, regcoordA, selected,
                     '(a) Agulhas Region', north_boxes, south_boxes, colors, lst,
                     read, box_legend=5)

    Wl = np.array([50, 100, 200, 300, 500])
    FbS_A, FbW_A, FbS_Ay, FbW_Ay = load_spectrum(read, region_boxes, models,
                                                 'JFM', 'JAS', Wl)

    ax1 = fig.add_axes([0.2, 0.3, 0.25, 0.16])
    pp2X.plot_psd(ax1, 1 / Wl, FbS_A.T, unit="m2", psd_labels=modellabel, title="(b) Winter",
                  savefig=False, plot_transparent=False, legend=False, colors=colors, lsts=lst,
                  wavelength_ticks=Wl, xlabel_upper=True, xlabel_lower=True)
    ax1.set_ylim([1e-5, 1e1])
    ax2 = fig.add_axes([0.55, 0.3, 0.25, 0.16])
    pp2X.plot_psd(ax2, 1 / Wl, FbW_A.T, unit="m2", psd_labels=modellabel, title="(c) Summer",
                  savefig=False, plot_transparent=False, legend=False, colors=colors, lsts=lst,
                  wavelength_ticks=Wl, xlabel_upper=True, xlabel_lower=True)
    ax2.set_ylim([1e-5, 1e1])

    Ra_A = FbS_A / FbW_A
    ax3 = fig.add_axes([0.3, 0.04, 0.4, 0.17])
    pp2X.plot_psd(ax3, 1 / Wl, Ra_A.T, unit="m2", psd_labels=modellabel,
                  title="(d) Winter/Summer", wavelength_ticks=np.array(Wl), savefig=False,
                  plot_transparent=False, slope=False, legend=None, colors=colors,
                  ylabelname="Ratio", lsts=lst, xlabel_upper=True, xlabel_lower=True)
    ax3.set_ylim([1e-1 * 2, 1e1 / 2])
    ax3.set_yticks([0.2, 0.5, 1, 2, 5])
    ax3.set_yticklabels([
        r'$2\times10^{-1}$',
        r'$5\times10^{-1}$',
        r'$10^{0}$',
        r'$2\times10^{0}$',
        r'$5\times10^{0}$'
    ])
    ax3.axhline(y=1, linestyle='dotted', linewidth=2, color="slategrey")

    save(fig, cfg, "agulhas_modelsswot")
    print(f"done ({cfg.reads} spectra reads)")


if __name__ == "__main__":
    main()
