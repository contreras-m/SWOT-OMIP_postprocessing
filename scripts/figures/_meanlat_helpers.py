#!/usr/bin/env python3
"""Faithful port of the meanlat notebook's model/SWOT ratio chain
(notebook/plotscale_ratioSWOT_meanlat_V3.ipynb cell 6), used by
fig3_meanlat_winter.py and s5_meanlat_summer.py.

Source chain inside src/cum_sp_onl_season_v3.py: cell 6 calls ratio_model,
whose per-box reads go through read_season(month, box, ...) in models order
for both seasons. That structure is kept; only the reads move to the
figure-script plumbing (deviations recorded here and in the two scripts).

Committed quirks of the chain that are kept EXACTLY (they shape the paper
figures; flagged for the record, not fixed):
- the SWOT reference branch ignores the season argument: psdsS is spec_s1
  in north boxes and spec_s2 in south boxes for BOTH winter and summer,
  so the "summer" ratio is model-summer / SWOT-winter;
- F[imod] stores the month1 (JFM) filtered frequency grid for every box,
  including southern boxes whose ratio value comes from month2 spectra
  (the stored spectra share one wavenumber grid, so the notebook's later
  np.interp against these JFM grids is consistent);
- imodelref is hard-coded models.index("SWOT") regardless of modelref.
"""

from __future__ import annotations

import numpy as np


def ratio_model(read, models, selected, wlmin, wlmax, north_boxes, south_boxes,
                month1, month2, season, modelref):
    R = {imod: [] for imod in models if imod != modelref}
    F = {imod: [] for imod in models if imod != modelref}
    for i, poly in enumerate(selected):

        box = i

        spectrum_s1, freq_s1 = [], []
        spectrum_s2, freq_s2 = [], []

        for imod in models:
            data = read(imod, box, month1)
            spectrum_s1.append(data["Spectra"])
            freq_s1.append(data["Frequency"])
        for imod in models:
            data = read(imod, box, month2)
            spectrum_s2.append(data["Spectra"])
            freq_s2.append(data["Frequency"])

        imodelref = models.index("SWOT")
        freq = np.array(freq_s1[imodelref])
        wavelength = 1.0 / freq

        poswl = np.where((wavelength > wlmin) & (wavelength < wlmax))[0]

        spec_s1 = np.array(spectrum_s1[imodelref])[poswl]
        spec_s2 = np.array(spectrum_s2[imodelref])[poswl]
        freq_filtered = freq[poswl]

        if season == "winter":
            if box in north_boxes:
                psdsS = spec_s1
            elif box in south_boxes:
                psdsS = spec_s2
            else:
                continue
        elif season == "summer":
            if box in north_boxes:
                psdsS = spec_s1
            elif box in south_boxes:
                psdsS = spec_s2
            else:
                continue

        for imodel, imod in enumerate(models):
            if imod == modelref:
                continue
            freq = np.array(freq_s1[imodel])
            wavelength = 1.0 / freq

            poswl = np.where((wavelength > wlmin) & (wavelength < wlmax))[0]

            spec_s1 = np.array(spectrum_s1[imodel])[poswl]
            spec_s2 = np.array(spectrum_s2[imodel])[poswl]
            freq_filtered = freq[poswl]

            if season == "winter":
                if box in north_boxes:
                    psds = spec_s1
                elif box in south_boxes:
                    psds = spec_s2
                else:
                    continue
            elif season == "summer":
                if box in north_boxes:
                    psds = spec_s2
                elif box in south_boxes:
                    psds = spec_s1
                else:
                    continue

            Z = psds / psdsS

            R[imod].append(Z)
            F[imod].append(freq_filtered)

    return R, F
