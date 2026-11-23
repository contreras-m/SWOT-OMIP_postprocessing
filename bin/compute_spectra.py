#!/usr/bin/env python
"""Parameterized wavenumber-spectra computation for SWOT-OMIP datasets.

Compute unit (chunk) = dataset x year x box x season. Already-computed spectra
(existing at the target store, or at the legacy DIVE store) are skipped unless
--force / --no-dive-skip are given.

Examples:
  # plan only (no compute, no file listing)
  python bin/compute_spectra.py --dataset LLC4320 --dry-run

  # demo chunk: one box, one season, read from the public ige mirror anonymously
  python bin/compute_spectra.py --dataset LLC4320 --seasons JFM --boxes 109 --source s3 --out-dir spectra_out

  # full pass (later, on request)
  python bin/compute_spectra.py --dataset eINALT100 --year 2021,2022,2023 --boxes all --push
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from swotomip_spectra.manifest import load as load_manifest, new_manifest, save as save_manifest
from swotomip_spectra.workflow import RunContext, append_run_log, chunk_status, plan_chunks, run_chunk


def parse_boxes(value: str, n_boxes: int):
    value = (value or "all").strip().lower()
    if value == "all":
        return list(range(n_boxes))
    ids = [int(v) for v in value.split(",") if v.strip()]
    for i in ids:
        if not 0 <= i < n_boxes:
            raise SystemExit(f"box id {i} out of range [0, {n_boxes})")
    return sorted(set(ids))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--year", default=None, help="comma-separated years for multi-year datasets (default: all)")
    parser.add_argument("--seasons", default=None, help="comma-separated, e.g. JFM,JAS (default from registry: JFM,JAS)")
    parser.add_argument("--boxes", default="all", help="'all' or comma-separated box ids")
    parser.add_argument("--source", default="auto", choices=["auto", "local", "s3"])
    parser.add_argument("--data-root", default=None, help="local data root containing the dataset mirrors")
    parser.add_argument("--out-dir", default="spectra_out", help="local output tree when not --push (default ./spectra_out)")
    parser.add_argument("--push", action="store_true", help="write spectra to the ige store from the registry")
    parser.add_argument("--dry-run", action="store_true", help="list chunks and statuses; no compute")
    parser.add_argument("--force", action="store_true", help="recompute even if the target already exists")
    parser.add_argument("--no-dive-skip", action="store_true", help="compute even if the legacy DIVE store has the spectrum")
    parser.add_argument("--allow-unverified", action="store_true", help="permit datasets whose registry status is unverified")
    parser.add_argument("--calendar", default=str(ROOT / "data" / "time_ranges.csv"))
    parser.add_argument("--boxes-file", default=str(ROOT / "data" / "mostly_ocean_boxes_filtered.geojson"))
    parser.add_argument("--swath-file", default=str(ROOT / "data" / "KaRIn_2kms_science_geometries.geojson"))
    parser.add_argument("--manifest", default=str(ROOT / "spectra_manifest.yaml"))
    parser.add_argument("--fill-threads", type=int, default=16)
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    from swotomip_spectra.registry import Registry

    registry = Registry.load(ROOT / "config" / "datasets.yaml")
    spec = registry.get(args.dataset)
    if spec.status != "verified" and not args.allow_unverified:
        raise SystemExit(
            f"dataset {args.dataset!r} is '{spec.status}' in the registry; "
            "verify its endpoints/naming or pass --allow-unverified"
        )

    years = spec.resolve_years(args.year.split(",") if args.year else None)
    seasons = [s.strip().upper() for s in (args.seasons or ",".join(registry.default_seasons())).split(",") if s.strip()]
    for s in seasons:
        if s not in registry.season_windows:
            raise SystemExit(f"unknown season {s!r}; available: {registry.seasons}")

    ctx = RunContext(
        registry,
        calendar_path=args.calendar,
        boxes_path=args.boxes_file,
        swath_path=args.swath_file,
        source=args.source,
        data_root=args.data_root,
        out_uri=args.out_dir,
        push=args.push,
        dry_run=args.dry_run,
        force=args.force,
        no_dive_skip=args.no_dive_skip,
        allow_unverified=args.allow_unverified,
        fill_threads=args.fill_threads,
    )

    box_ids = parse_boxes(args.boxes, len(ctx.boxes))
    chunks = plan_chunks(
        registry,
        spec,
        years=years,
        seasons=seasons,
        box_ids=box_ids,
        out_uri=args.out_dir,
        push=args.push,
    )

    print(f"dataset={spec.name} spectra_key={spec.spectra_key} privacy={spec.privacy}")
    print(f"years={years} seasons={seasons} boxes={len(box_ids)} -> {len(chunks)} chunks")
    print(f"output: {'ige store (push)' if args.push else args.out_dir}   source: {args.source}")

    n = {"written": 0, "skipped": 0, "planned": 0, "empty": 0, "failed": 0}
    for i, chunk in enumerate(chunks, 1):
        try:
            summary = run_chunk(ctx, spec, chunk)
        except Exception as exc:
            logging.exception("chunk %s failed", chunk)
            summary = {"dataset": chunk.dataset, "season": chunk.season, "box_id": chunk.box_id, "result": "failed", "error": str(exc)}
        result = summary.get("result", "failed")
        n[result] = n.get(result, 0) + 1
        line = f"[{i}/{len(chunks)}] {chunk.dataset}" + (f"/{chunk.year}" if chunk.year else "")
        line += f" {chunk.season} box_{chunk.box_id}: {result}"
        if summary.get("status_before", "new") != "new":
            line += f" ({summary['status_before']})"
        if result in ("written", "planned"):
            line += (
                f" files={summary.get('n_filtered_files')} datasets={summary.get('n_datasets', '-')}"
                f" segments={summary.get('n_segments', '-')}"
            )
        if "elapsed_s" in summary:
            line += f" [{summary['elapsed_s']}s]"
        print(line, flush=True)
        if not args.dry_run:
            append_run_log(args.out_dir, summary)

    print(f"summary: {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
