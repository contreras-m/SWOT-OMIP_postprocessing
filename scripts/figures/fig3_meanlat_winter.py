#!/usr/bin/env python3
"""Fig 3 -- zonal-mean model/SWOT SSH spectral ratio, WINTER.

Paper reference: Figures/meanlatratio_modelsswot_winter_v2 (PNG + PDF on sync).

Ported 1:1 from notebook/plotscale_ratioSWOT_meanlat_V3.ipynb: figure cell 12
(the WINTER variant; cell 13 is the SUMMER variant, ported as
s5_meanlat_summer.py) on its compute chain: cells 4 (boxes), 6 (per-box
model/SWOT ratios via cs.ratio_model -> ported in _meanlat_helpers.ratio_model),
8 (internal Rossby radius) and 10 (latitude-bin index over all 282 boxes --
this notebook does NOT skip features 14/15, unlike the scatter notebooks).

Recorded deviations from the notebook (only these):
- cell 6's online reads (cs.ratio_model / cs.read_season over anonymous
  s3://project-meom-ige/OMIP/Global/, or their relative-cwd offline mode)
  are replaced by read(key, box, season) from _common: offline cache by
  default, anonymous DIVE with --online. The committed quirks of the chain
  are kept (see _meanlat_helpers docstring), notably: the SWOT reference
  picks the same per-hemisphere season for the summer variant too.
- cell 6 computes both the winter and the summer ratio pair; this script
  computes only the winter pair (RW, FW) that cell 12 plots.
- Rossby_radius.nc is located via _common.rossby_file() (repo data/, or
  $SWOTOMIP_ROSSBY_RADIUS_FILE; fail-fast if absent) instead of the
  notebook's cwd-relative default; the resolved path is printed for run
  verification (stdout only). The computation itself is the notebook's own.
- the notebook's commented savefig (FigV2/meanlatratio_modelsswot_winter_v2.png,
  dpi=300) is replaced by _common.save under the paper-reference stem, PNG
  + PDF, tight bounding box; the notebook's trailing plt.show() is dropped.
"""

import argparse
import json

import _common
from _common import add_arguments, resolve, save, rossby_file

import matplotlib
matplotlib.use("Agg")
import matplotlib.cm as cm
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import numpy as np
import xarray as xr

import position_function as pf
from _meanlat_helpers import ratio_model
from _region_helpers import reader_from


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    add_arguments(ap)
    args = ap.parse_args()
    cfg = resolve(args)
    read = reader_from(cfg)

    # --------------------- notebook cell 4 ---------------------
    north_boxes, south_boxes = pf.position_boxes_northsouth(_common.GEOJSON)
    selected = pf.position_boxes(_common.GEOJSON)

    # --------------------- notebook cell 6 ---------------------
    models = ["GLO12V4", "GLO36V1", "GLO36V1NOTIDE", "NOC12", "NOC025", "LLC4320", "SWOT"]
    wmin = 50
    wmax = 500
    RW, FW = ratio_model(read, models, selected, wmin, wmax, north_boxes,
                         south_boxes, "JFM", "JAS", "winter", "SWOT")

    # --------------------- notebook cell 8 ---------------------
    rf = rossby_file()
    print(f"Rossby radius file: {rf}")
    dng = xr.open_dataset(rf)
    c1 = dng['c1'][:].data
    latR = dng['lat'][:].data
    dng.close()

    omega = 7.292e-5
    f = 2 * omega * np.sin(np.deg2rad(latR))

    RoR = np.nanmean(c1 / f, axis=0) / 1000

    poslatR = np.where((latR >= -3) & (latR <= 3))
    RoR[poslatR] = np.nan

    # --------------------- notebook cell 10 ---------------------
    with open(_common.GEOJSON) as fj:
        data = json.load(fj)

    latboxes = []
    latpos = np.arange(-70, 61, 10)

    for i, feature in enumerate(data["features"]):
        coords = feature["geometry"]["coordinates"][0]
        first_lat = coords[0][1]
        latboxes.append(first_lat)

    latindex = []
    for i in latpos:
        latindex.append(np.where(latboxes == i))

    print(latindex[0])

    # --------------------- notebook cell 12 (WINTER) ---------------------
    modelslabel = ["GLO12", "GLO36", "GLO36-DETIDED", "NOC12", "NOC025", "LLC4320"]
    models = ["GLO12V4", "GLO36V1", "GLO36V1NOTIDE", "NOC12", "NOC025", "LLC4320"]

    F2 = FW[models[0]]
    Wl = np.squeeze(F2[0])

    Fmean = np.zeros((len(Wl), len(latindex), len(models)))
    Fstd = np.zeros((len(Wl), len(latindex), len(models)))

    kmod = 0
    for imodel in models:
        RM = RW[imodel]
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

    mymin = 1e2
    mymax = 1e-2
    norm = mcolors.LogNorm(vmin=mymin, vmax=mymax)

    imodel = 5
    fig, ax = plt.subplots(3, 2, figsize=(12, 12))
    pc = ax[0, 0].pcolormesh(1 / Wl, latpos, np.squeeze(Fmean[:, :, imodel]).T, norm=norm, shading='nearest', cmap='seismic')
    ax[0, 0].plot(np.abs(RoR), latR, color='y')
    ax[0, 0].set_ylabel("Latitude")
    ax[0, 0].set_ylim([-60, 60])
    ax[0, 0].set_xlim([50, np.nanmax(1 / Wl)])
    ax[0, 0].set_title("(a) " + modelslabel[imodel])
    fig.colorbar(pc, ax=ax[0, 0])

    imodel = 2
    pc = ax[0, 1].pcolormesh(1 / Wl, latpos, np.squeeze(Fmean[:, :, imodel]).T, norm=norm, shading='nearest', cmap='seismic')
    ax[0, 1].plot(np.abs(RoR), latR, color='y')
    ax[0, 1].set_ylabel("Latitude")
    ax[0, 1].set_ylim([-60, 60])
    ax[0, 1].set_xlim([50, np.nanmax(1 / Wl)])
    ax[0, 1].set_title("(b) " + modelslabel[imodel])
    fig.colorbar(pc, ax=ax[0, 1])

    imodel = 1
    pc = ax[1, 0].pcolormesh(1 / Wl, latpos, np.squeeze(Fmean[:, :, imodel]).T, norm=norm, shading='nearest', cmap='seismic')
    ax[1, 0].plot(np.abs(RoR), latR, color='y')
    ax[1, 0].set_ylabel("Latitude")
    ax[1, 0].set_ylim([-60, 60])
    ax[1, 0].set_xlim([50, np.nanmax(1 / Wl)])
    ax[1, 0].set_title("(c) " + modelslabel[imodel])
    fig.colorbar(pc, ax=ax[1, 0])

    imodel = 0
    pc = ax[1, 1].pcolormesh(1 / Wl, latpos, np.squeeze(Fmean[:, :, imodel]).T, norm=norm, shading='nearest', cmap='seismic')
    ax[1, 1].plot(np.abs(RoR), latR, color='y')
    ax[1, 1].set_ylabel("Latitude")
    ax[1, 1].set_ylim([-60, 60])
    ax[1, 1].set_xlim([50, np.nanmax(1 / Wl)])
    ax[1, 1].set_title("(d) " + modelslabel[imodel])
    fig.colorbar(pc, ax=ax[1, 1])

    imodel = 3
    pc = ax[2, 0].pcolormesh(1 / Wl, latpos, np.squeeze(Fmean[:, :, imodel]).T, norm=norm, shading='nearest', cmap='seismic')
    ax[2, 0].set_xlabel("Wavelength")
    ax[2, 0].plot(np.abs(RoR), latR, color='y')
    ax[2, 0].set_ylabel("Latitude")
    ax[2, 0].set_ylim([-60, 60])
    ax[2, 0].set_xlim([50, np.nanmax(1 / Wl)])
    ax[2, 0].set_title("(e) " + modelslabel[imodel])
    fig.colorbar(pc, ax=ax[2, 0])

    imodel = 4
    pc = ax[2, 1].pcolormesh(1 / Wl, latpos, np.squeeze(Fmean[:, :, imodel]).T, norm=norm, shading='nearest', cmap='seismic')
    ax[2, 1].set_xlabel("Wavelength")
    ax[2, 1].plot(np.abs(RoR), latR, color='y')
    ax[2, 1].set_ylabel("Latitude")
    ax[2, 1].set_ylim([-60, 60])
    ax[2, 1].set_xlim([50, np.nanmax(1 / Wl)])
    ax[2, 1].set_title("(f) " + modelslabel[imodel])
    fig.colorbar(pc, ax=ax[2, 1])

    save(fig, cfg, "meanlatratio_modelsswot_winter_v2")
    print(f"done ({cfg.reads} spectra reads)")


if __name__ == "__main__":
    main()
