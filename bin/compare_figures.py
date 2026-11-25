#!/usr/bin/env python3
"""Compare regenerated figure candidates against the paper-repo figures.

Inputs: zero or more audit run directories (as produced by
bin/run_figure_notebooks.py) plus the paper repository, plus (optionally) the
output tree of the canonical figure scripts (``figures_out/``). For each paper
figure this tool gathers every candidate — the runner-captured inline cell
outputs (``cells/*.png``), the explicit ``FigV2/`` saves of the mapped producer
notebook, and the script outputs (``figures_out/<reference-stem>.{png,pdf}``,
kind ``script-output``) — scores each pair structurally, builds a labeled
stacked contact sheet (1500 px columns, high-res PDF rasterization), and
writes a verdict matrix plus a per-producer cross matrix.

Honesty notes:
* The committed paper figures went through undocumented manual finishing (the
  paper repo carries files like ``*_patched.pdf`` / ``*_labeled.pdf``; e.g.
  paper Fig 1 is 2661x3776 px while today's notebook layout emits 3600x3900),
  so scoring is crop-tolerant: both sides are autocropped to their ink
  bounding box before comparison.
* The scores triage "near-identical / similar / drifts / different / not
  produced"; final acceptance is visual, via the contact sheets this tool
  writes.
* Scoring rasters at <=900 px; the sheets reload the reference and the top
  candidates at 1500 px (PDFs via pdftoppm -r 200) for eyeballing.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
import time
from pathlib import Path

from PIL import Image

REPO_ROOT = Path(__file__).resolve().parent.parent
PAPER_ROOT = REPO_ROOT.parent / "2026_swot-omip-paper-seasonality"

# paper reference (relative to the paper repo) -> producer slug
FIGURE_MAP = {
    "Figures/agulhas_modelsswot.png": "AG",
    "Figures/scatter_global_cumration_modelSWOT2_V3_150-350.png": "cumpsd_ratio_scatter",
    "Figures/meanlatratio_modelsswot_winter_v2.pdf": "plotscale_meanlat",
    "Figures/winterslope_season_zonalaverage_V2_50-150.png": "slope_onl",
    "Figures_SI/agulhas_spectrum_geomarperyear.png": "AG",
    "Figures_SI/scatter_global_cumspectrum_modelSWOT2_winter-summer_150-350.png": "cumpsd_scatterplt_SI",
    "Figures_SI/scatter_global_cumration_modelSWOT2_V2_tidesv2_150-350.png": "cumpsd_ratio_scatter",
    "Figures_SI/cumspectrumratio_model_50-150.pdf": "plot_cumratio_map",  # producer: contreras-m's uploaded notebook (9886daf)
    "Figures_SI/meanlatratio_modelsswot_summer_v2.pdf": "plotscale_meanlat",
    "Figures_SI/ratioslope_season_model_50-150.pdf": "slope_onl",
    "Figures_SI/std_slope_season_model_winter_50-150.pdf": "slope_onl",
    "Figures_SI/slope_season_model_summer_50-150.pdf": "slope_onl",
    "Figures_SI/std_slope_season_model_summer_50-150.pdf": "slope_onl",
    "Figures_SI/NATL_modelsswot_detided.png": "GS",
}
FIGURE_LABEL = {p: lbl for lbl, p in {
    "Fig1": "Figures/agulhas_modelsswot.png",
    "Fig2": "Figures/scatter_global_cumration_modelSWOT2_V3_150-350.png",
    "Fig3": "Figures/meanlatratio_modelsswot_winter_v2.pdf",
    "Fig4": "Figures/winterslope_season_zonalaverage_V2_50-150.png",
    "S1": "Figures_SI/agulhas_spectrum_geomarperyear.png",
    "S2": "Figures_SI/scatter_global_cumspectrum_modelSWOT2_winter-summer_150-350.png",
    "S3": "Figures_SI/scatter_global_cumration_modelSWOT2_V2_tidesv2_150-350.png",
    "S4": "Figures_SI/cumspectrumratio_model_50-150.pdf",
    "S5": "Figures_SI/meanlatratio_modelsswot_summer_v2.pdf",
    "S6": "Figures_SI/ratioslope_season_model_50-150.pdf",
    "S7": "Figures_SI/std_slope_season_model_winter_50-150.pdf",
    "S8": "Figures_SI/slope_season_model_summer_50-150.pdf",
    "S9": "Figures_SI/std_slope_season_model_summer_50-150.pdf",
    "S10": "Figures_SI/NATL_modelsswot_detided.png",
}.items()}
FIGURE_MAP_LABEL = {path: FIGURE_LABEL[path] for path in FIGURE_MAP}

# canonical producer script per paper reference ("scripts/figures/<name>")
SCRIPT_OF = {
    "Figures/agulhas_modelsswot.png": "fig1_agulhas.py",
    "Figures/scatter_global_cumration_modelSWOT2_V3_150-350.png": "fig2_cumsd_ratio_scatter.py",
    "Figures/meanlatratio_modelsswot_winter_v2.pdf": "fig3_meanlat_winter.py",
    "Figures/winterslope_season_zonalaverage_V2_50-150.png": "fig4_winterslope_zonal.py",
    "Figures_SI/agulhas_spectrum_geomarperyear.png": "s1_agulhas_geomar_peryear.py",
    "Figures_SI/scatter_global_cumspectrum_modelSWOT2_winter-summer_150-350.png": "s2_cumspectrum_winter_summer.py",
    "Figures_SI/scatter_global_cumration_modelSWOT2_V2_tidesv2_150-350.png": "s3_cumsd_ratio_tides.py",
    "Figures_SI/cumspectrumratio_model_50-150.pdf": "s4_cumratio_map.py",
    "Figures_SI/meanlatratio_modelsswot_summer_v2.pdf": "s5_meanlat_summer.py",
    "Figures_SI/ratioslope_season_model_50-150.pdf": "s6_ratioslope.py",
    "Figures_SI/std_slope_season_model_winter_50-150.pdf": "s7_std_slope_winter.py",
    "Figures_SI/slope_season_model_summer_50-150.pdf": "s8_slope_summer.py",
    "Figures_SI/std_slope_season_model_summer_50-150.pdf": "s9_std_slope_summer.py",
    "Figures_SI/NATL_modelsswot_detided.png": "s10_natl_detided.py",
}


def _rasterize_pdf(path: Path, width: int = 900, dpi: int = 100):
    """Rasterize a PDF with a white background. pdftoppm renders matplotlib's
    transparent PDF background correctly white; sips renders it dark, so its
    RGBA output is composited over white as a fallback."""
    with tempfile.TemporaryDirectory() as td:
        try:
            subprocess.run(
                ["pdftoppm", "-png", "-r", str(dpi), "-singlefile", str(path), str(Path(td) / "ref")],
                check=True, capture_output=True,
            )
            return Image.open(Path(td) / "ref.png").convert("RGB")
        except Exception:
            pass
        try:
            subprocess.run(
                ["sips", "-s", "format", "png", str(path), "--out", str(Path(td) / "ref.png")],
                check=True, capture_output=True,
            )
            img = Image.open(Path(td) / "ref.png")
            if img.mode in ("RGBA", "LA"):
                bg = Image.new("RGB", img.size, (255, 255, 255))
                bg.paste(img, mask=img.split()[-1])
                return bg
            return img.convert("RGB")
        except Exception:
            return None


def load_image(path: Path, width: int = 900, dpi: int = 100):
    """Load a PNG or PDF; scale to <=`width` px wide. None on failure."""
    if path.suffix.lower() == ".pdf":
        img = _rasterize_pdf(path, width, dpi)
        if img is None:
            return None
    else:
        img = Image.open(path).convert("RGB")
    w, h = img.size
    if w > width:
        img = img.resize((width, max(1, round(h * width / w))), Image.LANCZOS)
    return img


def autocrop(img, ink_threshold: float = 0.97):
    """Crop to the bounding box of non-white ink; None if the page is blank."""
    import numpy as np

    a = np.asarray(img.convert("L"), dtype=float) / 255.0
    rows = np.where((a < ink_threshold).any(axis=1))[0]
    cols = np.where((a < ink_threshold).any(axis=0))[0]
    if len(rows) == 0 or len(cols) == 0:
        return None
    box = (int(cols[0]), int(rows[0]), int(cols[-1]) + 1, int(rows[-1]) + 1)
    return img.crop(box)


def ink_fraction(img):
    import numpy as np

    a = np.asarray(img.convert("L"), dtype=float) / 255.0
    return float((a < 0.95).mean())


def _scale_to(img, width: int):
    w, h = img.size
    if w == width:
        return img
    return img.resize((width, max(1, round(h * width / w))), Image.LANCZOS)


def score_pair(ref_img, cand_img):
    """Crop-tolerant structural triage: autocrop both, common canvas, NCC/MAD."""
    import numpy as np

    ref, cand = autocrop(ref_img), autocrop(cand_img)
    info = {"ref_ink": ink_fraction(ref_img), "cand_ink": ink_fraction(cand_img)}
    if ref is None or cand is None:
        return None, info
    w = min(ref.size[0], cand.size[0])
    ref, cand = _scale_to(ref, w), _scale_to(cand, w)
    H = max(ref.size[1], cand.size[1])
    g_ref = np.asarray(ref.convert("L"), dtype=float) / 255.0
    g_cand = np.asarray(cand.convert("L"), dtype=float) / 255.0
    canvas_r = np.ones((H, w))
    canvas_c = np.ones((H, w))
    canvas_r[: g_ref.shape[0], :] = g_ref
    canvas_c[: g_cand.shape[0], :] = g_cand
    g1 = canvas_r - canvas_r.mean()
    g2 = canvas_c - canvas_c.mean()
    denom = (np.linalg.norm(g1) * np.linalg.norm(g2)) or 1e-12
    info["corr"] = float((g1 * g2).sum() / denom)
    info["mad"] = float(np.abs(g1 - g2).mean())
    info["diff_frac"] = float((np.abs(g1 - g2) > 0.1).mean())
    ar = ref_img.size[0] / ref_img.size[1]
    ac = cand_img.size[0] / cand_img.size[1]
    info["aspect_ratio_diff"] = abs(ar - ac) / max(ar, ac)
    info["cropped_sizes"] = [list(ref.size), list(cand.size)]
    return info, info


def verdict(scores):
    if scores is None:
        return "not-produced"
    if scores["corr"] > 0.995 and scores["mad"] < 0.02:
        return "near-identical"
    if scores["corr"] > 0.9 and scores["aspect_ratio_diff"] < 0.08:
        return "similar"
    if scores["corr"] > 0.6:
        return "drifts"
    return "different"


def candidates_for(slug: str, run_dirs: list) -> list:
    out = []
    for rd in run_dirs:
        wd = rd / slug
        if not wd.exists():
            continue
        for p in sorted((wd / "cells").glob("cell*.png")):
            out.append((p, "inline-capture"))
        for p in sorted((wd / "FigV2").glob("*.png")):
            out.append((p, "explicit-save"))
    return out


def script_candidates(ref_rel: str, figures_out: Path) -> list:
    """Canonical script outputs for a reference: figures_out/<stem>.{png,pdf}."""
    out = []
    if not figures_out.exists():
        return out
    stem = Path(ref_rel).stem
    for ext in (".png", ".pdf"):
        p = figures_out / f"{stem}{ext}"
        if p.exists():
            out.append((p, "script-output"))
    return out


def sheet(ref_img, pairs, out_path: Path, title: str, img_w: int = 1500):
    """Stacked contact sheet: reference first, then up to four scored candidates.

    `ref_img` / `pairs` carry the HIGH-RES loads (caller reloads at img_w);
    images are autocropped and capped at (img_w, 2400)."""
    from PIL import Image, ImageDraw, ImageFont

    try:
        font = ImageFont.load_default(size=28)
    except TypeError:  # older Pillow: fixed-size default font
        font = ImageFont.load_default()
    W = img_w + 40
    entries = []
    if ref_img is not None:
        r = autocrop(ref_img) or ref_img
        r.thumbnail((img_w, 2400))
        entries.append(("REFERENCE", r))
    for (path, kind), cand_img, scores in pairs[:4]:
        if cand_img is None:
            continue
        c = autocrop(cand_img) or cand_img
        c.thumbnail((img_w, 2400))
        tag = f"{path.name} [{kind}]"
        if scores:
            tag += f" corr={scores['corr']:.3f} mad={scores['mad']:.3f}"
        entries.append((tag, c))
    H = sum(e[1].size[1] + 64 for e in entries) + 60
    sheet_img = Image.new("RGB", (W, H), (252, 252, 252))
    draw = ImageDraw.Draw(sheet_img)
    y = 14
    draw.text((20, y), title[:120], fill=(10, 10, 10), font=font)
    y += 44
    for tag, img in entries:
        draw.text((20, y), tag[:140], fill=(40, 40, 40), font=font)
        y += 36
        sheet_img.paste(img, (20, y))
        y += img.size[1] + 28
    sheet_img.save(out_path)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("run_dirs", nargs="*", type=Path, help="figure_runs/<ts> dir(s)")
    ap.add_argument("--paper-root", type=Path, default=PAPER_ROOT)
    ap.add_argument("--figures-out", type=Path, default=REPO_ROOT / "figures_out",
                    help="canonical script output dir (default <repo>/figures_out)")
    ap.add_argument("--sheet-width", type=int, default=1500)
    ap.add_argument("--ref-dpi", type=int, default=200)
    ap.add_argument("--out", type=Path, default=None,
                    help="output dir (default <last-run-dir>/comparison, else <figures-out>/comparison)")
    args = ap.parse_args()

    out_dir = args.out or (
        (args.run_dirs[-1] / "comparison") if args.run_dirs else (args.figures_out / "comparison")
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    run_dirs = [rd for rd in args.run_dirs if rd.exists()]

    # load all references and candidates per producer once
    refs, cands = {}, {}
    for ref_rel, slug in FIGURE_MAP.items():
        if slug is None:
            continue
        refs.setdefault(slug, []).append((ref_rel, FIGURE_MAP_LABEL[ref_rel],
                                          load_image(args.paper_root / ref_rel)))
    for slug in refs:
        cands[slug] = [
            ((p, kind), load_image(p)) for p, kind in candidates_for(slug, run_dirs)
        ]

    # per-producer cross matrix: every reference vs every candidate
    xmatrix = {}
    for slug in refs:
        xmatrix[slug] = {}
        for ref_rel, label, ref_img in refs[slug]:
            if ref_img is None:
                continue
            row = {}
            for (path, kind), cand_img in cands[slug]:
                if cand_img is None:
                    continue
                scores, _ = score_pair(ref_img, cand_img)
                if scores:
                    row[f"{path.name}"] = round(scores["corr"], 3)
            xmatrix[slug][label] = row

    results = []
    for ref_rel, slug in FIGURE_MAP.items():
        label = FIGURE_MAP_LABEL[ref_rel]
        ref_img = next((r[2] for r in refs.get(slug, []) if r[0] == ref_rel), None)
        if ref_img is None and (args.paper_root / ref_rel).exists():
            # orphaned references are not preloaded per producer — load on demand
            ref_img = load_image(args.paper_root / ref_rel)
        entry = {
            "figure": label, "reference": ref_rel,
            "producer": slug or "ORPHANED (ask)",
            "script": SCRIPT_OF.get(ref_rel) or "—",
            "ref_exists": (args.paper_root / ref_rel).exists(),
            "n_candidates": 0, "best": None, "candidates": [], "verdict": None,
        }
        if ref_img is None:
            entry["verdict"] = "ref-pdf-unavailable"
            results.append(entry)
            continue
        pairs = []
        if slug is not None:
            for (path, kind), cand_img in cands.get(slug, []):
                if cand_img is None:
                    continue
                scores, extra = score_pair(ref_img, cand_img)
                pairs.append(((path, kind), cand_img, scores))
        for path, kind in script_candidates(ref_rel, args.figures_out):
            cand_img = load_image(path)
            if cand_img is None:
                continue
            scores, _ = score_pair(ref_img, cand_img)
            pairs.append(((path, kind), cand_img, scores))
        pairs.sort(key=lambda p: -(p[2]["corr"] if p[2] else -1))
        entry["n_candidates"] = len(pairs)
        for (p, kind), _, s in pairs[:4]:
            entry["candidates"].append({"file": str(p), "kind": kind, **(s or {})})
        if pairs and pairs[0][2]:
            best = pairs[0]
            entry["best"] = {"file": str(best[0][0]), "kind": best[0][1], **best[2]}
            entry["verdict"] = verdict(best[2])
        elif slug is None:
            entry["verdict"] = "orphaned-no-producer"
        else:
            entry["verdict"] = "not-produced"
        # sheet: script outputs always shown first (canonical), then the best
        # notebook candidates; rebuilt at high resolution for eyeballing
        script_pairs = [p for p in pairs if p[0][1] == "script-output"][:4]
        nb_pairs = [p for p in pairs if p[0][1] != "script-output"][:4]
        shown = script_pairs + nb_pairs
        ref_hi = load_image(args.paper_root / ref_rel, args.sheet_width, args.ref_dpi)
        sheet_pairs = [
            ((p, k), load_image(p, args.sheet_width, args.ref_dpi), s)
            for (p, k), _, s in shown
        ]
        sheet(
            ref_hi, sheet_pairs,
            out_dir / f"{label}_{Path(ref_rel).name}.sheet.png",
            f"{label}: {Path(ref_rel).name} — producer: {slug or 'ask'} | script: {entry['script']}",
            img_w=args.sheet_width,
        )
        results.append(entry)

    lines = [
        "# Figure comparison matrix", "",
        f"- paper repo: {args.paper_root}",
        f"- run dirs: {[str(r) for r in run_dirs]}",
        f"- generated: {time.strftime('%Y-%m-%d %H:%M')}",
        "- scoring is crop-tolerant (autocropped, grayscale NCC/MAD).",
        "- NOTE: committed paper figures carry manual finishing (patched/labeled",
        "  files exist in the paper repo), so 'similar' bands are heuristics;",        "  the contact sheets are the acceptance artifact.", "",
        "| figure | reference | producer | script | verdict | best corr | best mad | best cand |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in results:
        best = r.get("best")
        corr = f"{best['corr']:.3f}" if best else "—"
        mad = f"{best['mad']:.3f}" if best else "—"
        name = Path(best["file"]).name if best else "—"
        lines.append(
            f"| {r['figure']} | {Path(r['reference']).name} | {r['producer']} "
            f"| {r['script']} | {r['verdict']} | {corr} | {mad} | {name} |"
        )
    lines += ["", "## Cross matrices (reference x candidate corr per producer)", ""]
    for slug, rows in xmatrix.items():
        lines.append(f"### {slug}")
        if not rows:
            lines.append("- (no rasterizable references)")
            continue
        cols = sorted({c for row in rows.values() for c in row})
        head = "| ref \\ cand | " + " | ".join(c[:22] for c in cols) + " |"
        lines += [head, "|---|" + "---|" * len(cols)]
        for label, row in rows.items():
            cells = " | ".join(str(row.get(c, "—")) for c in cols)
            lines.append(f"| {label} | {cells} |")
        lines.append("")
    (out_dir / "matrix.md").write_text("\n".join(lines))
    (out_dir / "comparison.json").write_text(json.dumps(
        {"figures": results, "xmatrix": xmatrix}, indent=2))
    print(f"wrote {out_dir}/matrix.md, {len(results)} figures, {len(xmatrix)} producers")
    for r in results:
        print(f"  {r['figure']:5s} {str(r['verdict']):20s} "
              f"{Path(r['reference']).name[:50]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
