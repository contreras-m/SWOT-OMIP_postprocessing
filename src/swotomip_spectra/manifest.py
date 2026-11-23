"""Spectra manifest: discovery status of computed spectra across stores.

The manifest records, per dataset (x year) and season, the probe status of every
global box against the legacy DIVE store and the new ige two-tier store. It is
refreshed read-only by bin/verify_manifest.py; compute_spectra.py consults it
(and live HEAD probes) to skip already-computed chunks.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

import yaml

SCHEMA_VERSION = 1


def new_manifest(registry) -> dict:
    from .registry import SEASON_WINDOWS

    return {
        "schema_version": SCHEMA_VERSION,
        "updated": None,
        "boxes_file": registry.region.get("boxes_file"),
        "seasons": sorted(SEASON_WINDOWS),
        "datasets": {},
    }


def load(path) -> Optional[dict]:
    p = Path(path)
    if not p.is_file():
        return None
    return yaml.safe_load(p.read_text()) or {}


def save(path, manifest: dict) -> None:
    manifest["updated"] = datetime.now().isoformat(timespec="seconds")
    Path(path).write_text(yaml.safe_dump(manifest, sort_keys=False))


def dataset_section(manifest: dict, dataset: str) -> dict:
    return manifest.setdefault("datasets", {}).setdefault(dataset, {})


def record_probe(
    manifest: dict,
    dataset: str,
    year: Optional[str],
    season: str,
    store: str,
    n_exist: int,
    n_probed: int,
    existing_boxes: Optional[list] = None,
) -> dict:
    key = f"{year}/{season}" if year else season
    section = dataset_section(manifest, dataset)
    probes = section.setdefault("probes", {})
    record = {
        "probe_date": datetime.now().isoformat(timespec="seconds"),
        "n_probed": n_probed,
        "n_exist": n_exist,
    }
    if existing_boxes is not None:
        record["existing_boxes"] = existing_boxes
    probes.setdefault(key, {})[store] = record
    return record
