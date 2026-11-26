#!/usr/bin/env python3
"""Copy approved figure outputs into the paper repo (tex-referenced file only).

Usage:
    python3 bin/sync_figure_to_paper.py Fig1 [S3 ...] [--dry-run]

For each label the script copies figures_out/<stem>.<ext> into the paper repo
at the paper-relative reference path (the exact file \\includegraphics loads).
The sibling format stays in figures_out/ (both PNG+PDF are always produced;
the paper repo keeps only the referenced file to avoid re-creating orphans).
Prints a ready-to-use provenance commit message citing the producer script
and the current postprocessing commit.

The paper-repo commit itself is left to the operator (git add + commit + push
inside 2026_swot-omip-paper-seasonality).
"""

from __future__ import annotations

import argparse
import subprocess
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FIGURES_OUT = REPO_ROOT / "figures_out"
PAPER_ROOT_DEFAULT = REPO_ROOT.parent / "2026_swot-omip-paper-seasonality"

FIGURE_LABEL = {
    "Fig1": "Figures/agulhas_modelsswot.png",
    "Fig2": "Figures/scatter_global_cumration_modelSWOT2_V3_150-350.png",
    "Fig3": "Figures/meanlatratio_modelsswot_winter_v2.pdf",
    "Fig4": "Figures/winterslope_season_zonalaverage_V2_50-150.png",
    "S1": "Figures_SI/agulhas_spectrum_geomarperyear.png",
    "S2": "Figures_SI/scatter_global_cumspectrum_modelSWOT2_winter-summer_150-350.png",
    "S3": "Figures_SI/scatter_global_cumration_modelSWOT2_V2_tidesv2_150-350.png",
    "S4": "Figures_SI/cumspectrumratio_model_50-150.png",
    "S5": "Figures_SI/meanlatratio_modelsswot_summer_v2.pdf",
    "S6": "Figures_SI/ratioslope_season_model_50-150.pdf",
    "S7": "Figures_SI/std_slope_season_model_winter_50-150.pdf",
    "S8": "Figures_SI/slope_season_model_summer_50-150.pdf",
    "S9": "Figures_SI/std_slope_season_model_summer_50-150.pdf",
    "S10": "Figures_SI/NATL_modelsswot_detided.png",
}

SCRIPT_OF = {
    "Fig1": "fig1_agulhas.py", "Fig2": "fig2_cumsd_ratio_scatter.py",
    "Fig3": "fig3_meanlat_winter.py", "Fig4": "fig4_winterslope_zonal.py",
    "S1": "s1_agulhas_geomar_peryear.py", "S2": "s2_cumspectrum_winter_summer.py",
    "S3": "s3_cumsd_ratio_tides.py", "S4": "s4_cumratio_map.py", "S5": "s5_meanlat_summer.py",
    "S6": "s6_ratioslope.py", "S7": "s7_std_slope_winter.py",
    "S8": "s8_slope_summer.py", "S9": "s9_std_slope_summer.py",
    "S10": "s10_natl_detided.py",
}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("labels", nargs="+", help=f"one of: {', '.join(FIGURE_LABEL)}")
    ap.add_argument("--paper-root", type=Path, default=PAPER_ROOT_DEFAULT)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    sha = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=REPO_ROOT,
                         capture_output=True, text=True).stdout.strip()
    synced = []
    for label in args.labels:
        if label not in FIGURE_LABEL:
            print(f"ERROR: unknown label {label!r}")
            return 1
        dest = args.paper_root / FIGURE_LABEL[label]
        src = FIGURES_OUT / dest.name
        if not src.exists():
            print(f"ERROR: no script output for {label}: {src} "
                  "(run the producer script first)")
            return 1
        if not args.dry_run:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(src.read_bytes())
        synced.append((label, src, dest))
        print(f"{'(dryrun) ' if args.dry_run else ''}{label}: {src.name} -> {dest}")

    print("\nprovenance commit message for the paper repo:")
    names = ", ".join(f"{lbl} ({SCRIPT_OF[lbl]})" for lbl, _, _ in synced)
    print(f"Figures {', '.join(lbl for lbl, _, _ in synced)}: regenerated from "
          f"SWOT-OMIP_postprocessing scripts ({names}), "
          f"contreras-m/SWOT-OMIP_postprocessing@{sha}, approved {time.strftime('%Y-%m-%d')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
