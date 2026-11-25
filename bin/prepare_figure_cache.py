#!/usr/bin/env python3
"""Materialize the local figure cache (`figure_cache/GLOBALv2/`) for the figure notebooks.

The region notebooks (AG / GS) read stored spectra JSONs from a relative
`GLOBALv2/` folder: `GLOBALv2/{KEY}/Global_box_{box}_{season}_{KEY}.json`.
Public keys are fetched anonymously from the legacy DIVE store (anonymous GET
is open there; anonymous *listing* is denied, so keys are constructed), and the
GEOMAR (eINALT100) spectra are copied from the local workspace mirror.

Idempotent: existing files are kept, only missing ones are fetched.
Run from anywhere; paths resolve relative to the repo root.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

DIVE_ENDPOINT = "https://minio.dive.edito.eu"
SPECTRA_PREFIX = "project-meom-ige/OMIP/Global"
GEOJSON = REPO_ROOT / "data" / "mostly_ocean_boxes_filtered.geojson"
DEFAULT_GEOMAR_ROOT = REPO_ROOT.parent / "data" / "GEOMAR_SSHspectrum"

# Cache recipe per region: box centers (lon_min, lon_max, lat_min, lat_max),
# keys and seasons actually read by the committed region notebooks.
REGIONS = {
    "agulhas": dict(
        regcoord=[0, 50, -50, -20],
        keys=["GLO12V4", "GLO36V1", "GLO36V1NOTIDE", "NOC12", "NOC025", "LLC4320", "SWOT"],
        seasons=["JFM", "JAS", "AMJ", "OND"],
    ),
    "natl": dict(
        regcoord=[-80, -20, -10, 50],
        keys=["GLO36V1", "GLO36V1NOTIDE", "SWOT"],
        seasons=["JFM", "JAS"],
    ),
    # Every box (0-based indices 0..N-1 in geojson order) — the "global" sets
    # used by the global figure notebooks (which call position_boxes bare).
    "global": dict(
        regcoord=None,
        keys=["GLO12V4", "GLO36V1", "GLO36V1NOTIDE", "NOC12", "NOC025", "LLC4320", "SWOT"],
        seasons=["JFM", "JAS"],
    ),
}


def region_boxes(regcoord: list | None) -> list:
    if regcoord is None:
        all_features = json.loads(GEOJSON.read_text())["features"]
        return list(range(len(all_features)))

    import position_function as pf

    # position_boxes must see the geojson; cwd to its folder for the bare open().
    import os

    prev = Path.cwd()
    os.chdir(GEOJSON.parent)
    try:
        _, boxes = pf.position_boxes(GEOJSON.name, regcoord=regcoord)
    finally:
        os.chdir(prev)
    return boxes


def fetch_public(dest: Path, keys, boxes, seasons, dry_run: bool) -> dict:
    import s3fs

    fs = s3fs.S3FileSystem(anon=True, endpoint_url=DIVE_ENDPOINT)
    fetched, kept, missing, bytes_dl = 0, 0, [], 0
    for key in keys:
        folder = dest / key
        folder.mkdir(parents=True, exist_ok=True)
        for season in seasons:
            for box in boxes:
                name = f"Global_box_{box}_{season}_{key}.json"
                out = folder / name
                if out.exists():
                    kept += 1
                    continue
                if dry_run:
                    fetched += 1
                    continue
                s3key = f"{SPECTRA_PREFIX}/{key}/{name}"
                for attempt in (1, 2):
                    try:
                        data = fs.cat(s3key) if hasattr(fs, "cat") else fs.open(s3key, "rb").read()
                        out.write_bytes(data)
                        fetched += 1
                        bytes_dl += len(data)
                        break
                    except Exception as exc:
                        if attempt == 2:
                            missing.append(f"{key}/{name} ({type(exc).__name__})")
                            break
                        time.sleep(0.5)
    return dict(fetched=fetched, kept=kept, missing=missing, bytes=bytes_dl)


def copy_geomar(dest: Path, geomar_root: Path) -> dict:
    copied = 0
    for year_dir in sorted(p for p in geomar_root.iterdir() if p.is_dir()):
        target = dest / "GEOMAR" / year_dir.name
        target.mkdir(parents=True, exist_ok=True)
        for src in sorted(year_dir.glob("Global_box_*_GEOMAR.json")):
            out = target / src.name
            if not out.exists():
                out.write_bytes(src.read_bytes())
                copied += 1
    return dict(copied=copied)


def make_geomar_yearless(dest: Path) -> dict:
    """Disclosed stand-in for the undocumented year-less GEOMAR files.

    The committed AG notebook reads JAS (and season-2 generally) via
    `GLOBALv2/GEOMAR/Global_box_{b}_{season}_GEOMAR.json` — no year
    subfolder — for files that were never committed or documented anywhere.
    To keep the audit reproducible we write year-less files as the mean of
    the available per-year spectra (same frequency grid), fully recorded in
    `_yearless_provenance.md`. Drop-in replaceable by the true files.
    """
    import numpy as np

    geomar_root = dest / "GEOMAR"
    per_year = sorted(p for p in geomar_root.iterdir() if p.is_dir() and p.name.isdigit())
    by_key: dict = {}
    for year_dir in per_year:
        for f in year_dir.glob("Global_box_*_GEOMAR.json"):
            by_key.setdefault(f.name, []).append(f)
    created, kept, skipped, no_data = 0, 0, [], []
    for name, files in sorted(by_key.items()):
        out = geomar_root / name
        if out.exists():
            kept += 1
            continue
        datas = []
        for p in sorted(files):
            d = json.loads(p.read_text())
            spec, freq = d.get("Spectra"), d.get("Frequency")
            if (
                isinstance(spec, list) and len(spec) > 0
                and isinstance(freq, list) and len(freq) == len(spec)
            ):
                datas.append(d)
        if not datas:
            no_data.append(name)
            continue
        spectra = [np.asarray(d["Spectra"], dtype=float) for d in datas]
        freqs = [np.asarray(d["Frequency"], dtype=float) for d in datas]
        if not all(len(f) == len(freqs[0]) and np.allclose(f, freqs[0]) for f in freqs[1:]):
            skipped.append(name)
            continue
        merged = dict(datas[0])
        merged["Spectra"] = np.mean(spectra, axis=0).tolist()
        merged["date_creation"] = time.strftime("%Y-%m-%d")
        merged["login_creator"] = "figure-cache-aux (mean of per-year spectra)"
        out.write_text(json.dumps(merged))
        created += 1
    note = geomar_root / "_yearless_provenance.md"
    note.write_text(
        "# Year-less GEOMAR stand-in files\n\n"
        "The committed AG notebook (region_plot_spectr_noonl_AG-Copy1-IMPR) reads\n"
        "GEOMAR season-2 spectra from a year-less path\n"
        "(`GLOBALv2/GEOMAR/Global_box_{b}_{season}_GEOMAR.json`). The corresponding\n"
        "files were never committed or documented; their origin content is an open\n"
        "question to the notebook author (contreras-m).\n\n"
        f"These {created} stand-in files (created {time.strftime('%Y-%m-%d')}) are the\n"
        "per-position mean of the per-year spectra (2021-2023) at identical frequency\n"
        "grids. If the true year-less files surface, replace these drop-in.\n\n"
        f"Skipped (mismatched frequency grids): {skipped}\n\n"
        f"Not written (no valid per-year spectra — the annotated empty boxes): {no_data}\n"
    )
    return dict(created=created, kept=kept, skipped=skipped, no_data=no_data)


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--regions", default="agulhas,natl", help="comma list from: agulhas,natl,global")
    ap.add_argument("--geomar-root", type=Path, default=DEFAULT_GEOMAR_ROOT)
    ap.add_argument("--dest", type=Path, default=REPO_ROOT / "figure_cache" / "GLOBALv2")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument(
        "--no-yearless-mean",
        action="store_true",
        help="do not write the year-less GEOMAR stand-in files (see make_geomar_yearless)",
    )
    args = ap.parse_args()

    dest: Path = args.dest
    if not GEOJSON.exists():
        print(f"ERROR: box file not found: {GEOJSON}")
        return 1
    if not args.geomar_root.exists():
        print(f"ERROR: GEOMAR spectra mirror not found: {args.geomar_root}")
        print("       (expected data/GEOMAR_SSHspectrum/{2021,2022,2023} in the workspace)")
        return 1

    summary = {"dest": str(dest), "dry_run": args.dry_run, "regions": {}}
    for region in args.regions.split(","):
        region = region.strip()
        if region not in REGIONS:
            print(f"ERROR: unknown region {region!r}")
            return 1
        recipe = REGIONS[region]
        boxes = region_boxes(recipe["regcoord"])
        print(f"[{region}] boxes ({len(boxes)}): {boxes}")
        if args.dry_run:
            continue
        info = fetch_public(dest, recipe["keys"], boxes, recipe["seasons"], args.dry_run)
        info["boxes"] = len(boxes)
        summary["regions"][region] = info
        print(
            f"[{region}] fetched={info['fetched']} kept={info['kept']} "
            f"missing={len(info['missing'])} ({info['bytes'] / 1e6:.1f} MB)"
        )
        for miss in info["missing"][:12]:
            print(f"    MISSING {miss}")

    if not args.dry_run:
        gm = copy_geomar(dest, args.geomar_root)
        summary["geomar"] = gm
        print(f"[GEOMAR] copied={gm['copied']}")
        if not args.no_yearless_mean:
            yl = make_geomar_yearless(dest)
            summary["geomar_yearless_mean"] = yl
            print(
                f"[GEOMAR] year-less stand-ins created={yl['created']} "
                f"kept={yl['kept']} skipped={len(yl['skipped'])} (provenance: "
                "GLOBALv2/GEOMAR/_yearless_provenance.md)"
            )
        (dest / "_cache_manifest.json").write_text(json.dumps(summary, indent=2))
        total = sum(
            r["fetched"] + r["kept"] for r in summary["regions"].values()
        ) if summary.get("regions") else 0
        print(f"cache ready at {dest} ({total} public files + GEOMAR years)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
