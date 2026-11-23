"""Spectra JSON output: schema-compatible writer for the SWOT-OMIP spectra store.

Document schema matches the production save_spect_json2 files stored on DIVE
(e.g. project-meom-ige/OMIP/Global/GLO12V4/Global_box_0_JFM_GLO12V4.json):
region, model, lon_min, lon_max, lat_min, lat_max, start_date, end_date,
packages_versions, date_creation, login_creator, Frequency, Spectra, machine_info.
"""

from __future__ import annotations

import getpass
import json
import platform
from datetime import datetime
from pathlib import Path
from typing import Optional, Sequence

import numpy as np

DOCUMENT_KEYS = [
    "region",
    "model",
    "lon_min",
    "lon_max",
    "lat_min",
    "lat_max",
    "start_date",
    "end_date",
    "packages_versions",
    "date_creation",
    "login_creator",
    "Frequency",
    "Spectra",
    "machine_info",
]

WATERMARK_PACKAGES = "numpy,xarray,s3fs,pyinterp"


def packages_versions() -> str:
    try:
        from watermark import watermark

        return watermark(packages=WATERMARK_PACKAGES)
    except Exception:
        import s3fs
        import xarray

        lines = [f"numpy   : {np.__version__}", f"xarray  : {xarray.__version__}", f"s3fs    : {s3fs.__version__}"]
        try:
            import pyinterp

            lines.append(f"pyinterp: {pyinterp.__version__}")
        except Exception:
            pass
        return "\n".join(lines) + "\n"


def build_document(
    region: str,
    model: str,
    lon_min: float,
    lon_max: float,
    lat_min: float,
    lat_max: float,
    start_date: str,
    end_date: str,
    freqs: np.ndarray,
    psd: np.ndarray,
    packages_versions_str: Optional[str] = None,
    date_creation: Optional[str] = None,
    creator: Optional[str] = None,
) -> dict:
    if freqs is None or psd is None or len(freqs) == 0 or len(psd) == 0:
        raise ValueError("empty spectra; refusing to write JSON")
    return {
        "region": region,
        "model": model,
        "lon_min": lon_min,
        "lon_max": lon_max,
        "lat_min": lat_min,
        "lat_max": lat_max,
        "start_date": start_date,
        "end_date": end_date,
        "packages_versions": packages_versions_str or packages_versions(),
        "date_creation": date_creation or datetime.now().isoformat(),
        "login_creator": creator or platform.node(),
        "Frequency": [float(v) for v in np.asarray(freqs).ravel()],
        "Spectra": [float(v) for v in np.asarray(psd).ravel()],
        "machine_info": dict(platform.uname()._asdict()),
    }


def open_fs_for(target: str, endpoint_url: Optional[str] = None, anon: bool = True):
    """Filesystem for a target URI (local path or s3://)."""
    if target.startswith("s3://"):
        import s3fs

        return s3fs.S3FileSystem(anon=anon, endpoint_url=endpoint_url)
    from fsspec import get_filesystem_class

    return get_filesystem_class("file")()


def exists(fs, target: str) -> bool:
    return bool(fs.exists(target))


def write_json(fs, target: str, document: dict) -> str:
    payload = json.dumps(document, indent=4)
    if target.startswith("s3://"):
        with fs.open(target, mode="w") as fh:
            fh.write(payload)
    else:
        path = Path(target)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(payload)
    return target


def read_json(fs, target: str) -> dict:
    with fs.open(target, mode="r") as fh:
        return json.load(fh)
