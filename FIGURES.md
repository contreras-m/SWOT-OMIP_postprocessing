# FIGURES.md — the paper figures, their scripts, and the workflow

Every paper figure of `2026_swot-omip-paper-seasonality` (4 main + 10 SI) is
produced by a **parameterized script** in `scripts/figures/` — the
producer-of-record. The notebooks stay as reader-facing exploration; the
scripts are the canonical, minimal, reproducible path (offline spectra cache
by default, `--online` for anonymous DIVE reads).

Conventions (locked 2026-11-24): scripts save **PNG (300 dpi) + PDF** with
`bbox_inches="tight"` — the in-code replacement of the manual finishing the
committed paper figures carried (`*_patched.pdf` / `*_labeled.pdf`). No
manual finishing anywhere; acceptance is visual (contact sheets) plus this
manifest.

## Manifest

| Figure | Paper repo file (tex-referenced) | Producer script | Notebook source (cells) | Status |
|---|---|---|---|---|
| Fig 1 | `Figures/agulhas_modelsswot.png` | `fig1_agulhas.py` | `region_plot_spectr_noonl_AG-Copy1-IMPR` (10) | ready |
| Fig 2 | `Figures/scatter_global_cumration_modelSWOT2_V3_150-350.png` | `fig2_cumsd_ratio_scatter.py` | `plot_cumpsd_ratio-scatter` (5,7,9,10,12,13) | ready |
| Fig 3 | `Figures/meanlatratio_modelsswot_winter_v2.pdf` | `fig3_meanlat_winter.py` | `plotscale_ratioSWOT_meanlat_V3` (4,6,8,10,12) | ready (needs `data/Rossby_radius.nc`) |
| Fig 4 | `Figures/winterslope_season_zonalaverage_V2_50-150.png` | `fig4_winterslope_zonal.py` | `plot_slope_onl_v3+tides` (4,5,7,9,12) | ready |
| S1 | `Figures_SI/agulhas_spectrum_geomarperyear.png` | `s1_agulhas_geomar_peryear.py` | AG notebook (11) | ready |
| S2 | `Figures_SI/scatter_global_cumspectrum_modelSWOT2_winter-summer_150-350.png` | `s2_cumspectrum_winter_summer.py` | `plot_cumpsd_scatterplt_SI` (5,7,9,10,13,14) | **superseded**: the committed file came from the wrong notebook (contreras-m, 2026-11-25) — the figure is being redesigned as a merged Fig2+S2 (Takaya's suggestion); this script gets retired when the merged producer lands |
| S3 | `Figures_SI/scatter_global_cumration_modelSWOT2_V2_tidesv2_150-350.png` | `s3_cumsd_ratio_tides.py` | `plot_cumpsd_ratio-scatter` (5,7,12,15,16,17) | ready |
| S4 | `Figures_SI/cumspectrumratio_model_50-150.pdf` | `s4_cumratio_map.py` | `plot_cumratio_map` (contreras-m upload 9886daf: cells 4,6,8,10) | ready — **caption touch needed**: committed caption says "(a-e)", producer makes 6 panels (a-f) |
| S5 | `Figures_SI/meanlatratio_modelsswot_summer_v2.pdf` | `s5_meanlat_summer.py` | plotscale (4,6,8,10,13) | ready (Rossby) |
| S6 | `Figures_SI/ratioslope_season_model_50-150.pdf` | `s6_ratioslope.py` | slope notebook (4,5,7,9,11,13) | ready |
| S7 | `Figures_SI/std_slope_season_model_winter_50-150.pdf` | `s7_std_slope_winter.py` | slope notebook (4,5,7,9,15) | ready |
| S8 | `Figures_SI/slope_season_model_summer_50-150.pdf` | `s8_slope_summer.py` | slope notebook (4,5,7,9,16) | ready |
| S9 | `Figures_SI/std_slope_season_model_summer_50-150.pdf` | `s9_std_slope_summer.py` | slope notebook (4,5,7,9,17) | ready |
| S10 | `Figures_SI/NATL_modelsswot_detided.png` | `s10_natl_detided.py` | `region_plot_spectr_noonl_GS-Copy1-IMPR` (8, helpers 4-6) | ready |

Also produced by the slope notebook but not referenced by the paper (removed
from the paper repo in the 2026-11-24 tidy): `slope_season_model_winter_50-150`
(slope notebook cell 14). Easy to revive as a script if ever wanted.

## Workflow

```bash
# 1. one-time: materialize the offline cache (~50 MB, idempotent)
python3 bin/prepare_figure_cache.py --regions agulhas,natl,global

# 2. produce a figure (offline cache; --online reads DIVE anonymously)
.venv/bin/python3 scripts/figures/fig1_agulhas.py

# 3. score + contact sheets against the paper repo + audit runs
.venv/bin/python3 bin/compare_figures.py figure_runs/<ts> --out <any-dir>
#    (script outputs from figures_out/ are picked up automatically)

# 4. after visual approval: copy into the paper repo + commit there
.venv/bin/python3 bin/sync_figure_to_paper.py Fig1
cd ../2026_swot-omip-paper-seasonality && git add -A && git commit  # message is printed by the sync helper
```

Scripts write both `<stem>.png` and `<stem>.pdf` under `figures_out/`
(gitignored). `sync_figure_to_paper.py` copies **only the tex-referenced
file** into the paper repo (the sibling format stays here) so the paper repo
does not accumulate unreferenced files again.

## Scoring notes

`bin/compare_figures.py` scores are crop-tolerant structural triage, NOT
acceptance: the committed paper figures carry undocumented manual finishing,
so even a faithful reproduction lands in the "drifts" band. The contact
sheets (1500 px, `pdftoppm -r 200`) are the acceptance artifact.

Script-output scores vs the committed references
(`figure_runs/scriptmatrix-20261125-fixes/`, post the 2026-11-25 fixes --
explicit GEOMAR 3-yr means + latindex unskip): Fig1 0.821, Fig2 0.968
("similar"), Fig3 0.852, Fig4 0.872, S1 0.847, S3 0.879, **S4 0.829**,
S5 0.844, S6 0.826, S7 0.806, S8 0.711, S9 0.838, S10 0.726 — every script
matches or exceeds what the committed notebooks' own renders score against
the same references, which is the fidelity check that matters pre-approval.
Notably the latindex fix *improved* Fig2 (0.965->0.968) and S3 (0.875->0.879):
the committed figures were evidently generated with the skip already fixed,
which matches contreras-m's recollection ("I thought I had fixed it") --
the fix just never made it back into the committed notebook cells.
(S2's script score is meaningless pending the merged Fig2+S2 redesign --
the committed reference came from the wrong notebook.)

## NOTES — quirks resolved / kept (paper-impacting items for contreras-m)

- **S2 layout — RESOLVED (contreras-m, 2026-11-25)**: the committed SI file
  (map + colorbar + a single 2x5 scatter block) was produced from the wrong
  notebook; its layout is an accident, not a design. The figure will be
  redesigned as a merged Fig2+S2 (Takaya's suggestion; contreras-m proposes
  appending the S2 scatterplots to the bottom of Fig 2); the
  caption-literal combined script (`s2_cumspectrum_winter_summer.py`) is a
  stopgap to retire once the merged producer lands.
- **S4 caption**: the committed caption says "(a-e)"; the producer
  (`plot_cumratio_map.ipynb`, contreras-m upload 9886daf, ported to
  `s4_cumratio_map.py`) makes 6 panels, (a) SWOT -> (f) NOC025 — the SI
  caption needs a touch during the sync round.
- **GEOMAR year-less reads — RESOLVED (contreras-m, 2026-11-25)**: the
  intended design is the **3-year average**; the scripts now read per-year
  files and average explicitly (season 2 numerically unchanged -- the
  cache stand-ins were 3-yr means; season 1 in the map insets moves from
  the last-year-only quirk to the 3-yr mean, matching the paper text).
  The year-less stand-ins remain in the cache only so the still-unpatched
  notebooks keep running; they become removable once contreras-m's notebook
  fix lands (`figure_cache/GLOBALv2/GEOMAR/_yearless_provenance.md`).
- **latindex 14/15 skip — FIXED in the scripts (contreras-m confirmed the
  bug, 2026-11-25)**: the guard is removed from the ported helpers (and the
  no-op guard from load_spectrum); notebook patches follow on her schedule.
  The fix *improved* Fig2/S3 scores vs the committed figures (see above).
- **S8/S9 colorbars say "winter"** on summer figures (notebook verbatim) —
  contreras-m offered to correct; awaiting her fix (scripts or notebooks).
- **`ratio_model` season bug (Fig3/S5)**: the SWOT reference branch ignores
  its `season` argument, so the "summer" ratio divides model-summer by
  SWOT-winter per hemisphere. Kept faithfully (the committed figures carry
  it); contreras-m may fix (scripts or notebooks — re-port is small).
- **`plot_psd(savefig=True)` in the region notebooks is
  layout-carrying** — the mid-loop `globa_JFM.png` re-save settles the
  cartopy map state; removing it displaces every inset after the first
  (found while porting S10; both ported variants keep the render pass, the
  litter goes to a process scratch dir).
