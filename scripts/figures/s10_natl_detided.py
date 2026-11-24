#!/usr/bin/env python3
"""Figure S10 -- NATL: GLO36 de-tided vs GLO36 vs SWOT, spectra-ratio map.

Paper reference: Figures_SI/NATL_modelsswot_detided (PNG + PDF).

Ported 1:1 from notebook/region_plot_spectr_noonl_GS-Copy1-IMPR.ipynb
cell 8, which calls the notebook's own plot_boxspectrum (cells 4-6). That
GS map variant is the shared port _region_helpers.plot_boxspectrum_gs;
cell 8's call matches it after TWO corrections recorded in
_region_helpers.py: (1) the legend inset's bba_leg is (-3, 1) as in the GS
notebook cell 5 -- the shared port had initially carried the AG variant's
(4.5, 2); (2) the per-inset plot_psd savefig=True /
filename="globa_JFM.png" of the notebook is KEPT (it is not
layout-neutral: the mid-loop renders settle the cartopy map's aspect
state, so without them every inset plot after the first lands displaced --
s10 reproduces the committed notebook render only with them). Cell 8's
models list has no GEOMAR, so the helper's GEOMAR branch never triggers.

Recorded deviations from the notebook (only these):
- the notebook's reads (folder="GLOBALv2/" + read_json_local, i.e.
  relative-cwd paths) are replaced by read(key, box, season) from
  _common (--online: anonymous DIVE): recorded in _region_helpers.
- the globa_JFM.png side-product that plot_psd re-saves to the cwd after
  every inset plot is removed at the end of the run (the render effects
  it caused are baked into the figure; only the junk file goes).
- the notebook's commented savefig (FigV2/NATL_modelsswot_detided.png,
  dpi=300) is replaced by _common.save under the paper-reference stem,
  PNG + PDF, tight bounding box.
- the importlib.reload(pp2X) ritual of cells 2/5/8 is not carried
  (module hygiene; no plotting effect).
"""

from pathlib import Path

import argparse

import _common
from _common import add_arguments, resolve, save

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import position_function as pf
from _region_helpers import plot_boxspectrum_gs, reader_from


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    add_arguments(ap)
    args = ap.parse_args()
    cfg = resolve(args)
    read = reader_from(cfg)

    # --------------------- notebook cell 8 ---------------------
    models = ["GLO36V1NOTIDE", "GLO36V1", "SWOT"]
    modellabel = ["GLO36-DETIDED", "GLO36", "SWOT"]

    lst = ['solid', 'dotted', 'solid']

    colors = ['lime',
              "darkgreen",
              "k"]

    regcoordA = [-80, -20, -10, 50]
    north_boxes, south_boxes = pf.position_boxes_northsouth(_common.GEOJSON)
    selected, region_boxes = pf.position_boxes(_common.GEOJSON, regcoordA)
    cds = regcoordA
    fig = plt.figure(figsize=(12, 13))
    plot_boxspectrum_gs(fig, region_boxes, models, modellabel, cds, selected,
                        '', north_boxes, south_boxes, colors, lst, read,
                        box_legend=0)

    save(fig, cfg, "NATL_modelsswot_detided")
    print(f"done ({cfg.reads} spectra reads)")
    Path("globa_JFM.png").unlink(missing_ok=True)


if __name__ == "__main__":
    main()
