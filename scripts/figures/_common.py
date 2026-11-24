#!/usr/bin/env python3
"""Shared plumbing for the canonical paper-figure scripts (scripts/figures/).

Each figure script is the producer-of-record for one paper figure (see
FIGURES.md): it reads stored spectra, renders the figure exactly as the
producing notebook cell does, and saves it under the PAPER-REFERENCE file
stem as both PNG (300 dpi default) and PDF with a tight bounding box -- the
in-code replacement of the manual finishing the committed paper figures
carry.

Data access:
- offline (default): the local spectra cache `figure_cache/GLOBALv2/`,
  materialized by bin/prepare_figure_cache.py (anonymous DIVE GETs for the
  public keys; GEOMAR per-year files copied from the local private mirror).
- --online: anonymous S3 reads from the legacy DIVE store
  (project-meom-ige/OMIP/Global). Anonymous GET is open there; the legacy
  bogus s3fs credentials (key="xxx") were removed from the src helpers.
- GEOMAR is ALWAYS read from the local cache (private per-year files) in
  both modes. The year-less GEOMAR files that the AG notebook reads are the
  disclosed 3-year-mean stand-ins recorded in
  figure_cache/GLOBALv2/GEOMAR/_yearless_provenance.md.

Box indices are the 0-based feature indices produced by
src.position_function.position_boxes (0..281), not the geojson `id`.

The src modules are importable after `import _common` (this file prepends
the src dir to sys.path).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC = REPO_ROOT / "src"
DATA = REPO_ROOT / "data"
GEOJSON = DATA / "mostly_ocean_boxes_filtered.geojson"
DEFAULT_CACHE = REPO_ROOT / "figure_cache" / "GLOBALv2"
DEFAULT_OUT = REPO_ROOT / "figures_out"

DIVE_ENDPOINT = "https://minio.dive.edito.eu"
SPECTRA_PREFIX = "project-meom-ige/OMIP/Global"
GEOMAR_YEARS = (2021, 2022, 2023)

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def add_arguments(ap: argparse.ArgumentParser) -> None:
    g = ap.add_argument_group("figure-script plumbing")
    g.add_argument("--online", action="store_true",
                   help="read public spectra over anonymous S3 from DIVE instead of the local cache")
    g.add_argument("--cache", type=Path, default=DEFAULT_CACHE,
                   help="offline spectra cache (default figure_cache/GLOBALv2)")
    g.add_argument("--out", type=Path, default=DEFAULT_OUT,
                   help="output dir (default figures_out/)")
    g.add_argument("--dpi", type=int, default=300,
                   help="PNG dpi (default 300)")


def resolve(args) -> SimpleNamespace:
    """Validate the mode/paths; returns the config the script passes around."""
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    cache = Path(args.cache)
    if not args.online and not cache.exists():
        sys.exit(
            f"spectra cache not found: {cache}\n"
            "run: python3 bin/prepare_figure_cache.py --regions agulhas,natl,global"
        )
    return SimpleNamespace(online=bool(args.online), cache=cache, out=out,
                           dpi=int(args.dpi), reads=0)


def spectra_path(cfg, key: str, box: int, season: str, year=None) -> Path:
    """Cache layout matches the notebooks' relative GLOBALv2/ tree."""
    if year is None:
        return Path(cfg.cache) / key / f"Global_box_{box}_{season}_{key}.json"
    return Path(cfg.cache) / key / str(year) / f"Global_box_{box}_{season}_{key}.json"


_FS = None


def _fs():
    global _FS
    if _FS is None:
        import s3fs

        _FS = s3fs.S3FileSystem(anon=True, endpoint_url=DIVE_ENDPOINT)
    return _FS


def read_spectrum(cfg, key: str, box: int, season: str, year=None) -> dict:
    """One stored spectrum. Public keys: cache or --online DIVE; GEOMAR: cache."""
    cfg.reads += 1
    if key == "GEOMAR":
        p = spectra_path(cfg, key, box, season, year)
        if not p.exists():
            sys.exit(
                f"missing GEOMAR spectra file in the local cache: {p}\n"
                "(GEOMAR is private, per-year data -- always served from the cache;"
                " run bin/prepare_figure_cache.py, or check the year-less "
                "stand-ins in GLOBALv2/GEOMAR/_yearless_provenance.md)"
            )
        with open(p, "rb") as f:
            return json.load(f)
    if cfg.online:
        name = f"Global_box_{box}_{season}_{key}.json"
        s3key = f"{SPECTRA_PREFIX}/{key}/{name}"
        data = _fs().cat(s3key) if hasattr(_fs(), "cat") else _fs().open(s3key, "rb").read()
        return json.loads(data)
    p = spectra_path(cfg, key, box, season)
    if not p.exists():
        sys.exit(
            f"missing cache file: {p}\n"
            "(run: python3 bin/prepare_figure_cache.py --regions agulhas,natl,global,"
            " or use --online)"
        )
    with open(p, "rb") as f:
        return json.load(f)


def save(fig, cfg, stem: str):
    """Write the figure as <stem>.png + <stem>.pdf under cfg.out.

    Tight bounding box: replaces the old manual crop/patching step.
    The stem is the paper-reference filename without extension, so
    bin/compare_figures.py picks both up as script-output candidates."""
    stem = Path(stem).with_suffix("")
    png, pdf = cfg.out / f"{stem}.png", cfg.out / f"{stem}.pdf"
    fig.savefig(png, dpi=cfg.dpi, transparent=False, bbox_inches="tight")
    fig.savefig(pdf, transparent=False, bbox_inches="tight")
    print(f"saved: {png}")
    print(f"saved: {pdf}")
    return png, pdf


def rossby_file() -> Path:
    """Internal Rossby radius file for the meanlat figures (Fig 3 / S5)."""
    for p in [Path(os.environ["SWOTOMIP_ROSSBY_RADIUS_FILE"])
              if "SWOTOMIP_ROSSBY_RADIUS_FILE" in os.environ else None,
              DATA / "Rossby_radius.nc"]:
        if p is not None and p.exists():
            return p
    sys.exit(
        "Rossby_radius.nc not found -- run: bin/download_rossby_radius.sh\n"
        "(or set SWOTOMIP_ROSSBY_RADIUS_FILE)"
    )
