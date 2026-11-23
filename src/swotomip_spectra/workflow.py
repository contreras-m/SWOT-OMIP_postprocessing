"""Chunk planning and execution: the compute unit is dataset x year x box x season."""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .boxes import Box, load_boxes, load_swath_geometries, passes_for_box
from .calendar import load_cycle_calendar, matching_cycles, season_months, season_window, zfill3, format_iso
from .discovery import filter_matches, list_cycle_files_local, list_cycle_files_s3, match_filename
from .output import build_document, exists as target_exists, write_json
from .registry import DatasetSpec, Registry

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Chunk:
    dataset: str
    year: Optional[str]
    season: str
    box_id: int
    target_uri: str
    region_label: str
    dive_key: Optional[str]


class RunContext:
    def __init__(
        self,
        registry: Registry,
        *,
        calendar_path,
        boxes_path,
        swath_path,
        source: str = "auto",
        data_root: Optional[str] = None,
        out_uri: str = "spectra_out",
        push: bool = False,
        dry_run: bool = False,
        force: bool = False,
        no_dive_skip: bool = False,
        allow_unverified: bool = False,
        fill_threads: int = 16,
    ):
        self.registry = registry
        self.calendar = load_cycle_calendar(calendar_path)
        self.boxes: List[Box] = load_boxes(boxes_path)
        self.swath = load_swath_geometries(swath_path)
        self.source = source
        self.data_root = data_root
        self.out_uri = out_uri
        self.push = push
        self.dry_run = dry_run
        self.force = force
        self.no_dive_skip = no_dive_skip
        self.allow_unverified = allow_unverified
        self.fill_threads = fill_threads
        self._fs_cache: Dict[Tuple[str, bool], object] = {}

    def s3fs(self, endpoint_url: str, anon: bool):
        key = (endpoint_url, anon)
        if key not in self._fs_cache:
            import s3fs

            self._fs_cache[key] = s3fs.S3FileSystem(anon=anon, endpoint_url=endpoint_url)
        return self._fs_cache[key]

    def box(self, box_id: int) -> Box:
        return self.boxes[box_id]

    def source_fs(self, spec: DatasetSpec, year: Optional[str]):
        if self.push:
            store = self.registry.store_for(spec)
            return self.s3fs(store.endpoint_url, store.anon)
        return None

    def resolve_source(self, spec: DatasetSpec, year: Optional[str]) -> Tuple[str, object, str]:
        """Returns (mode, fs or None, base_path)."""
        mode = self.source
        local_root = None
        if spec.local is not None and self.data_root is not None:
            candidate = Path(self.data_root) / self.registry.cycles_root_local(spec, year)
            if candidate.is_dir():
                local_root = str(candidate)
        if mode == "auto":
            mode = "local" if local_root is not None else "s3"
        if mode == "local":
            if local_root is None:
                raise FileNotFoundError(
                    f"no local mirror for {spec.name} under {self.data_root!r}; use --source s3"
                )
            return "local", None, local_root
        if spec.s3 is None:
            raise ValueError(f"dataset {spec.name} has no s3 source")
        return (
            "s3",
            self.s3fs(spec.s3.endpoint_url, spec.s3.anon),
            self.registry.cycles_base_s3(spec, year),
        )


def plan_chunks(
    registry: Registry,
    spec: DatasetSpec,
    *,
    years: List[str],
    seasons: List[str],
    box_ids: List[int],
    out_uri: Optional[str] = None,
    push: bool = False,
) -> List[Chunk]:
    chunks = []
    for year in years:
        for season in seasons:
            for box_id in box_ids:
                if push:
                    target = registry.target_uri(spec, year or None, box_id, season)
                else:
                    key_dir = registry.default_spectra_key_dir(spec, year or None)
                    target = f"{(out_uri or 'spectra_out').rstrip('/')}/{key_dir}/{registry.spectra_filename(spec, box_id, season)}"
                chunks.append(
                    Chunk(
                        dataset=spec.name,
                        year=year or None,
                        season=season,
                        box_id=box_id,
                        target_uri=target,
                        region_label=registry.region_label(spec, year or None, box_id),
                        dive_key=registry.dive_spectra_key(spec, year, box_id, season),
                    )
                )
    return chunks


def dive_key_exists(ctx: RunContext, dive_key: Optional[str]) -> bool:
    if not dive_key:
        return False
    store = ctx.registry.dive_store()
    if store is None:
        return False
    fs = ctx.s3fs(store.endpoint_url, True)
    try:
        return bool(fs.exists(dive_key))
    except Exception as exc:
        logger.debug("dive probe failed for %s: %s", dive_key, exc)
        return False


def chunk_status(ctx: RunContext, spec: DatasetSpec, chunk: Chunk) -> Tuple[str, Optional[str]]:
    """Status of a chunk against the output store; ('pending', None) or ('exists', where)."""
    if ctx.push:
        store = ctx.registry.store_for(spec)
        out_fs = ctx.s3fs(store.endpoint_url, store.anon)
        if target_exists(out_fs, chunk.target_uri):
            return "exists", "target"
    elif not chunk.target_uri.startswith("s3://"):
        from fsspec.implementations.local import LocalFileSystem

        if target_exists(LocalFileSystem(), chunk.target_uri):
            return "exists", "target"
    if not ctx.no_dive_skip and dive_key_exists(ctx, chunk.dive_key):
        return "exists", "dive"
    return "pending", None


def list_chunk_files(ctx: RunContext, spec: DatasetSpec, year: Optional[str], chunk: Chunk):
    start, end = season_window(chunk.season)
    cycles = matching_cycles(ctx.calendar, start, end)
    box = ctx.box(chunk.box_id)
    passes = passes_for_box(ctx.swath, box)
    months = season_months(start, end)
    mode, src_fs, base = ctx.resolve_source(spec, year)
    cycles_str = zfill3(cycles)
    if mode == "s3":
        files = list_cycle_files_s3(src_fs, base, cycles_str)
    else:
        files = list_cycle_files_local(base, cycles_str)
    matches = [match_filename(f) for f in files]
    kept = filter_matches(matches, passes, months)
    return {
        "cycles": cycles,
        "passes": passes,
        "months": months,
        "mode": mode,
        "n_cycle_files": len(files),
        "n_filtered_files": len(kept),
        "files": [m.path for m in kept],
    }


def run_chunk(ctx: RunContext, spec: DatasetSpec, chunk: Chunk) -> dict:
    summary = {
        "dataset": chunk.dataset,
        "year": chunk.year,
        "season": chunk.season,
        "box_id": chunk.box_id,
        "target": chunk.target_uri,
    }
    status, where = chunk_status(ctx, spec, chunk)
    summary["status_before"] = f"exists@{where}" if where else "new"
    if where == "target" and not ctx.force:
        summary["result"] = "skipped"
        return summary
    if where == "dive" and not ctx.no_dive_skip:
        summary["result"] = "skipped"
        return summary

    t0 = time.time()
    plan = list_chunk_files(ctx, spec, chunk.year, chunk)
    summary.update({k: v for k, v in plan.items() if k != "files"})
    if ctx.dry_run:
        summary["result"] = "planned"
        return summary

    from .interpolate import fill_nan
    from .readers import load_pass_datasets
    from .spectra import calculate_psd, psd_mean_and_freq, retrieve_segments

    mode, src_fs, _ = ctx.resolve_source(spec, chunk.year)
    datasets = load_pass_datasets(
        plan["files"],
        ctx.box(chunk.box_id).area0360,
        lon_convention=spec.lon_convention,
        fs=src_fs,
    )
    summary["n_datasets"] = len(datasets)
    has_converged, filled = fill_nan(datasets, varname=spec.ssh_varname, num_threads=ctx.fill_threads)
    summary["fill_converged"] = has_converged
    segments = retrieve_segments(filled, file_type="NetCDF", namevar=spec.ssh_varname)
    summary["n_segments"] = len(segments)
    psd_dict, freqs_dict = calculate_psd(segments)
    psd_mean, freqs_mean = psd_mean_and_freq(psd_dict, freqs_dict)

    start, end = season_window(chunk.season)
    try:
        document = build_document(
            region=chunk.region_label,
            model=spec.spectra_key,
            lon_min=ctx.box(chunk.box_id).lon_min360,
            lon_max=ctx.box(chunk.box_id).lon_max360,
            lat_min=ctx.box(chunk.box_id).lat_min,
            lat_max=ctx.box(chunk.box_id).lat_max,
            start_date=format_iso(start),
            end_date=format_iso(end),
            freqs=freqs_mean,
            psd=psd_mean,
        )
    except ValueError:
        summary["result"] = "empty"
        summary["elapsed_s"] = round(time.time() - t0, 1)
        return summary

    store_fs = ctx.source_fs(spec, chunk.year)
    write_json(store_fs, chunk.target_uri, document)
    summary["result"] = "written"
    summary["elapsed_s"] = round(time.time() - t0, 1)
    summary["psd_len"] = len(psd_mean)
    return summary


def append_run_log(out_uri: str, summary: dict) -> None:
    log_path = Path(out_uri) / "spectra_runs.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a") as fh:
        fh.write(json.dumps(summary) + "\n")
