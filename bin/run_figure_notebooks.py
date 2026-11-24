#!/usr/bin/env python3
"""Run the paper figure notebooks headlessly and audit their outputs.

Two modes:

* queue mode (default): create `figure_runs/<ts>/` and execute the audited
  notebooks one at a time, each in its own subprocess with a wall-clock cap,
  then write `REPORT.md`.
* single mode (`--single SLUG --run-dir DIR`): execute one notebook inside an
  existing run dir (used internally by the queue).

Per notebook the runner:
  1. creates a working dir with the box geojson, a `GLOBALv2` symlink to the
     shared cache (`bin/prepare_figure_cache.py`), and a `FigV2/` folder;
  2. optionally injects a disclosed shim cell (visible in the executed
     notebook and quoted in REPORT.md) that fixes the notebooks' bogus s3
     credentials (`key="xxx"` is rejected by minio.dive.edito.eu) by swapping to
     a cached anonymous filesystem — identical bytes, anonymous GET is open;
  3. executes with `allow_errors=True` so an early cell failure cannot kill
     the cells that produce the figures; every cell error is recorded;
  4. extracts the rendered figures (inline `image/png` outputs) to
     `cells/cell<N>_f<j>.png`, lists explicit `FigV2/` saves, and writes
     `manifest.json`.

Zero notebook-file edits: notebooks are read, executed in memory, and the
executed copies land in the run dir only.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
NOTEBOOK_DIR = REPO_ROOT / "notebook"
CACHE_GLOBALV2 = REPO_ROOT / "figure_cache" / "GLOBALv2"
DATA_DIR = REPO_ROOT / "data"
RUNS_ROOT = REPO_ROOT / "figure_runs"
DEFAULT_KERNEL = "swotomip-figs"

# (notebook filename stem, slug) — audit order: cheap local first, the
# Rossby-blocked notebook last.
AUDIT_NOTEBOOKS = [
    ("region_plot_spectr_noonl_AG-Copy1-IMPR", "AG"),
    ("region_plot_spectr_noonl_GS-Copy1-IMPR", "GS"),
    ("plot_cumpsd_scatterplt_SI", "cumpsd_scatterplt_SI"),
    ("plot_slope_onl_v3+tides", "slope_onl"),
    ("plot_cumpsd_ratio-scatter", "cumpsd_ratio_scatter"),
    ("plotscale_ratioSWOT_meanlat_V3", "plotscale_meanlat"),
]

SHIM_SRC = """\
# --- _audit_shim (injected by bin/run_figure_notebooks.py; see REPORT.md) ---
# The notebooks read spectra via s3fs with placeholder credentials
# (key="xxx"...), which minio.dive.edito.eu rejects. The DIVE spectra store
# allows anonymous GET, so swap those constructions to a cached anonymous
# filesystem — the objects read are identical.
import s3fs as _s3fs
_RealS3FS = _s3fs.S3FileSystem
_fs_pool = {}
def _anon_factory(*args, **kwargs):
    if kwargs.get("key") in (None, "xxx") and kwargs.get("secret") in (None, "xxx"):
        endpoint = (kwargs.get("endpoint_url") or "").rstrip("/")
        if endpoint:
            fs = _fs_pool.get(endpoint)
            if fs is None:
                kw = dict(kwargs)
                kw.pop("key", None)
                kw.pop("secret", None)
                kw.setdefault("anon", True)
                fs = _RealS3FS(*args, **kw)
                _fs_pool[endpoint] = fs
            return fs
    return _RealS3FS(*args, **kwargs)
_anon_factory._real = _RealS3FS
_s3fs.S3FileSystem = _anon_factory
"""


def slugify(name: str) -> str:
    import re

    return re.sub(r"[^A-Za-z0-9_.-]+", "-", name)


def kernel_env() -> dict:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO_ROOT / "src") + (
        os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else ""
    )
    env.setdefault("OMP_NUM_THREADS", "4")
    return env


def package_versions() -> dict:
    from importlib.metadata import PackageNotFoundError, version

    out = {}
    for pkg in [
        "ipykernel", "nbclient", "nbconvert", "matplotlib", "cartopy",
        "xarray", "numpy", "scipy", "s3fs", "pyinterp", "widetrax", "shapely",
    ]:
        try:
            out[pkg] = version(pkg)
        except PackageNotFoundError:
            out[pkg] = "not installed"
    return out


def prepare_workdir(workdir: Path) -> None:
    workdir.mkdir(parents=True, exist_ok=True)
    for name in ("mostly_ocean_boxes_filtered.geojson", "KaRIn_2kms_science_geometries.geojson"):
        src = DATA_DIR / name
        if src.exists():
            shutil.copy2(src, workdir / name)
        else:
            raise FileNotFoundError(f"missing box file: {src}")
    if not CACHE_GLOBALV2.exists():
        raise FileNotFoundError(
            f"figure cache not found at {CACHE_GLOBALV2}; run bin/prepare_figure_cache.py first"
        )
    link = workdir / "GLOBALv2"
    if link.is_symlink() or link.exists():
        link.unlink() if link.is_symlink() else shutil.rmtree(link)
    link.symlink_to(CACHE_GLOBALV2, target_is_directory=True)
    (workdir / "FigV2").mkdir(exist_ok=True)
    (workdir / "cells").mkdir(exist_ok=True)


def run_single(slug: str, nb_stem: str, run_dir: Path, args) -> int:
    import nbformat
    from nbclient import NotebookClient
    from nbclient.exceptions import CellTimeoutError, DeadKernelError

    workdir = run_dir / slug
    prepare_workdir(workdir)
    src_nb = NOTEBOOK_DIR / f"{nb_stem}.ipynb"
    nb = nbformat.read(src_nb, as_version=4)

    if not args.no_shim:
        shim_cell = nbformat.v4.new_code_cell(SHIM_SRC)
        nb.cells.insert(0, shim_cell)

    os.environ.update(kernel_env())
    t0 = time.time()
    client = NotebookClient(
        nb,
        timeout=args.timeout_cell,
        kernel_name=args.kernel_name,
        allow_errors=True,
        resources={"metadata": {"path": str(workdir)}},
    )
    kernel_error = None
    try:
        client.execute()
    except (CellTimeoutError, DeadKernelError) as exc:
        kernel_error = f"{type(exc).__name__}: {exc}"
    wall = time.time() - t0

    executed_nb_path = workdir / f"{slug}.executed.ipynb"
    nbformat.write(nb, executed_nb_path)

    # extract rendered figures + per-cell statuses (index counts code cells in
    # the ORIGINAL notebook when the shim is off, or includes the shim cell
    # when on — the manifest records the offset).
    cell_records = []
    n_images = 0
    for idx, cell in enumerate(nb.cells):
        if cell.cell_type != "code":
            continue
        rec = {"cell": idx, "exec": cell.get("execution_count"), "status": "ok", "images": 0, "error": None}
        for out in cell.get("outputs", []):
            if out.get("output_type") == "error":
                rec["status"] = "error"
                rec["error"] = f"{out.get('ename')}: {out.get('evalue', '')[:220]}"
            if out.get("output_type") in ("display_data", "execute_result"):
                png = (out.get("data") or {}).get("image/png")
                if png:
                    import base64

                    rec["images"] += 1
                    n_images += 1
                    out_path = workdir / "cells" / f"cell{idx}_f{rec['images']}.png"
                    out_path.write_bytes(base64.b64decode(png))
        cell_records.append(rec)

    figv2 = sorted(p.name for p in (workdir / "FigV2").glob("*.png")) + sorted(
        p.name for p in (workdir / "FigV2").glob("*.pdf")
    )
    manifest = {
        "notebook": nb_stem,
        "slug": slug,
        "shim_injected": not args.no_shim,
        "kernel_error": kernel_error,
        "wall_s": round(wall, 1),
        "n_code_cells": len(cell_records),
        "n_error_cells": sum(1 for r in cell_records if r["status"] == "error"),
        "n_images": n_images,
        "figv2_files": figv2,
        "cells": cell_records,
        "versions": package_versions(),
        "python": sys.version.split()[0],
    }
    (workdir / "manifest.json").write_text(json.dumps(manifest, indent=2))

    status = "ok" if (kernel_error is None and manifest["n_error_cells"] == 0) else "issues"
    print(
        f"[{slug}] {status}: wall={wall:.0f}s cells={manifest['n_code_cells']} "
        f"errors={manifest['n_error_cells']} images={n_images} figv2={len(figv2)}"
        + (f" KERNEL_ERROR={kernel_error}" if kernel_error else "")
    )
    for rec in cell_records:
        if rec["status"] == "error":
            print(f"    cell{rec['cell']} ERROR: {rec['error']}")
    return 0 if kernel_error is None else 3


def run_queue(args) -> int:
    wanted = [s.strip() for s in args.notebooks.split(",")] if args.notebooks != "all" else None
    selection = []
    for nb_stem, slug in AUDIT_NOTEBOOKS:
        if wanted is None or slug in wanted or nb_stem in wanted:
            selection.append((nb_stem, slug))
    if not selection:
        print(f"ERROR: no notebook matches --notebooks {args.notebooks!r}")
        print("known slugs:", ", ".join(s for _, s in AUDIT_NOTEBOOKS))
        return 1

    ts = time.strftime("%Y%m%d-%H%M%S")
    run_dir = RUNS_ROOT / ts
    run_dir.mkdir(parents=True)
    print(f"run dir: {run_dir}")
    print(f"notebooks: {[s for _, s in selection]}")

    env = kernel_env()
    results = []
    for nb_stem, slug in selection:
        cmd = [
            sys.executable, __file__,
            "--single", slug,
            "--run-dir", str(run_dir),
            "--nb-stem", nb_stem,
            "--timeout-cell", str(args.timeout_cell),
            "--kernel-name", args.kernel_name,
        ]
        if args.no_shim:
            cmd.append("--no-shim")
        t0 = time.time()
        try:
            proc = subprocess.run(
                cmd, env=env, timeout=args.timeout_nb, capture_output=True, text=True
            )
            outcome = dict(
                slug=slug, nb=nb_stem, returncode=proc.returncode,
                wall_s=round(time.time() - t0, 1), timeout=False,
                stdout_tail=proc.stdout.strip().splitlines()[-12:],
                stderr_tail=proc.stderr.strip().splitlines()[-6:],
                manifest=None,
            )
        except subprocess.TimeoutExpired as exc:
            outcome = dict(
                slug=slug, nb=nb_stem, returncode=None,
                wall_s=round(time.time() - t0, 1), timeout=True,
                stdout_tail=(exc.stdout or b"").decode(errors="replace").splitlines()[-12:] if isinstance(exc.stdout, bytes) else (exc.stdout or "").splitlines()[-12:],
                stderr_tail=[],
                manifest=None,
            )
        mpath = run_dir / slug / "manifest.json"
        if mpath.exists():
            outcome["manifest"] = json.loads(mpath.read_text())
        results.append(outcome)
        print(f"queue: {slug} done in {outcome['wall_s']}s rc={outcome['returncode']} timeout={outcome['timeout']}")

    lines = []
    lines.append(f"# Figure-notebook audit run {ts}")
    lines.append("")
    lines.append(f"- repo: {REPO_ROOT}")
    lines.append(f"- kernel: {args.kernel_name}, cell timeout {args.timeout_cell}s, wall cap {args.timeout_nb}s/nb")
    lines.append(f"- shim: {'OFF' if args.no_shim else 'ON (anon s3fs swap; source quoted below)'}")
    lines.append("")
    lines.append("| notebook | wall s | cells | errors | images | FigV2 saves | outcome |")
    lines.append("|---|---|---|---|---|---|---|")
    for r in results:
        m = r["manifest"]
        if m:
            lines.append(
                f"| {r['slug']} | {m['wall_s']} | {m['n_code_cells']} | {m['n_error_cells']} "
                f"| {m['n_images']} | {len(m['figv2_files'])} "
                f"| {'timeout' if r['timeout'] else ('kernel-dead' if r['returncode'] else 'completed')} |"
            )
        else:
            lines.append(f"| {r['slug']} | {r['wall_s']} | ? | ? | ? | ? | TIMEOUT |")
    lines.append("")
    for r in results:
        if r["manifest"]:
            for rec in r["manifest"]["cells"]:
                if rec["status"] == "error":
                    lines.append(f"## {r['slug']} cell{rec['cell']} error")
                    lines.append("```")
                    lines.append(rec["error"] or "")
                    lines.append("```")
        if r["stdout_tail"]:
            lines.append(f"## {r['slug']} runner output (tail)")
            lines.append("```")
            lines.extend(r["stdout_tail"])
            lines.append("```")
    lines.append("## Injected shim (verbatim)")
    lines.append("```python")
    lines.append(SHIM_SRC)
    lines.append("```")
    (run_dir / "REPORT.md").write_text("\n".join(lines))
    print(f"REPORT: {run_dir / 'REPORT.md'}")
    return 0


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--notebooks", default="all", help="'all' or comma-separated slugs/notebook stems")
    ap.add_argument("--single", metavar="SLUG", help="internal: run one notebook (requires --run-dir)")
    ap.add_argument("--run-dir", type=Path, help="run directory for --single")
    ap.add_argument("--nb-stem", help="internal: notebook filename stem for --single")
    ap.add_argument("--timeout-cell", type=int, default=1800, help="per-cell kernel timeout (s)")
    ap.add_argument("--timeout-nb", type=int, default=2700, help="per-notebook wall cap in queue mode (s)")
    ap.add_argument("--kernel-name", default=DEFAULT_KERNEL)
    ap.add_argument("--no-shim", action="store_true", help="do not inject the anon s3fs shim")
    args = ap.parse_args()

    if args.single:
        if not (args.run_dir and args.nb_stem):
            print("ERROR: --single requires --run-dir and --nb-stem")
            return 2
        return run_single(args.single, args.nb_stem, args.run_dir, args)
    return run_queue(args)


if __name__ == "__main__":
    raise SystemExit(main())
