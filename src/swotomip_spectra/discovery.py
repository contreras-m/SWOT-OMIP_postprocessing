"""File discovery: cycle folders, robust filename parsing, pass/month filtering."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Set

logger = logging.getLogger(__name__)

DEFAULT_FILENAME_REGEX = re.compile(
    r"_(?P<cycle>\d{3})_(?P<pass>\d{3})_(?P<start>\d{8}T\d{6})_(?P<end>\d{8}T\d{6})[_.]"
)


@dataclass(frozen=True)
class FileMatch:
    path: str
    cycle: int
    pass_number: int
    start: datetime
    end: datetime


def match_filename(path: str, pattern: re.Pattern = DEFAULT_FILENAME_REGEX) -> Optional[FileMatch]:
    """Parse cycle/pass/start/end from a protocol-style filename.

    Replaces the production parts.index('SSH') parser, which crashes on names
    without an SSH token; accepts both protocol (…_SSH_c_p_dates_v1.0.2.nc) and
    GEOMAR contributor (…_SSH_c_p_dates_eINALT100.nc) formats.
    """
    name = Path(path).name
    m = pattern.search(name)
    if m is None:
        return None
    return FileMatch(
        path=path,
        cycle=int(m.group("cycle")),
        pass_number=int(m.group("pass")),
        start=datetime.strptime(m.group("start"), "%Y%m%dT%H%M%S"),
        end=datetime.strptime(m.group("end"), "%Y%m%dT%H%M%S"),
    )


def list_cycle_files_s3(fs, base: str, cycles: Sequence[str]) -> List[str]:
    files: List[str] = []
    for cycle in cycles:
        pattern = f"{base.rstrip('/')}/cycle_{cycle}/**/*.nc"
        found = fs.glob(pattern)
        for f in found:
            if Path(f).name.endswith(".nc"):
                files.append(f)
    return files


def list_cycle_files_local(root, cycles: Sequence[str]) -> List[str]:
    files: List[str] = []
    for cycle in cycles:
        cdir = Path(root) / f"cycle_{cycle}"
        if not cdir.is_dir():
            logger.debug("missing cycle dir %s", cdir)
            continue
        files.extend(str(p) for p in sorted(cdir.rglob("*.nc")))
    return files


def filter_matches(
    matches: Iterable[Optional[FileMatch]],
    pass_numbers: Sequence[int],
    months: Sequence[int],
) -> List[FileMatch]:
    passes: Set[int] = set(int(p) for p in pass_numbers)
    months_: Set[int] = set(int(m) for m in months)
    kept = []
    for m in matches:
        if m is None:
            continue
        if m.pass_number in passes and m.start.month in months_:
            kept.append(m)
    return kept
