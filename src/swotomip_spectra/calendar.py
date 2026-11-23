"""Cycle calendar: robust replacement for the production get_matching_cycles
(now upstreamed to widetrax.DataPreprocessing, widetrax >= 1.2).

Semantics replicate the production notebook: a cycle matches a season window when
its [start, end] time range overlaps the window. Unlike the production helper, the
parser accepts both the clean repository calendar (data/time_ranges.csv, one header
line) and calendars with preamble lines, without silently dropping the first rows.
"""

from __future__ import annotations

import io
import re
from datetime import date, datetime
from pathlib import Path
from typing import List, Sequence, Tuple

import pandas as pd


def load_cycle_calendar(path) -> pd.DataFrame:
    """Load a cycle calendar CSV into a DataFrame with columns cycle/start/end."""
    text = Path(path).read_text()
    first_data = None
    for i, line in enumerate(text.splitlines()):
        if re.match(r"^\s*\d+,", line):
            first_data = i
            break
    if first_data is None:
        raise ValueError(f"no cycle rows found in {path}")
    df = pd.read_csv(
        io.StringIO("\n".join(text.splitlines()[first_data:])),
        header=None,
        names=["cycle", "start_date", "end_date"],
    )
    df["cycle"] = df["cycle"].astype(int)
    df["start_date"] = pd.to_datetime(df["start_date"])
    df["end_date"] = pd.to_datetime(df["end_date"])
    return df.drop_duplicates(subset="cycle").reset_index(drop=True)


def matching_cycles(calendar: pd.DataFrame, start_date, end_date) -> List[int]:
    """Cycles whose [start,end] range overlaps [start_date,end_date] (inclusive)."""
    start = pd.Timestamp(start_date)
    end = pd.Timestamp(end_date)
    mask = (calendar["start_date"] <= end) & (calendar["end_date"] >= start)
    return sorted(int(c) for c in calendar.loc[mask, "cycle"])


def zfill3(cycles: Sequence[int]) -> List[str]:
    return [str(c).zfill(3) for c in cycles]


def season_window(season: str) -> Tuple[date, date]:
    from .registry import SEASON_WINDOWS

    if season not in SEASON_WINDOWS:
        raise ValueError(f"unknown season {season!r}")
    s, e = SEASON_WINDOWS[season]
    return datetime.strptime(s, "%Y-%m-%d").date(), datetime.strptime(e, "%Y-%m-%d").date()


def format_ddmmyyyy(d: date) -> str:
    return d.strftime("%d%m%Y")


def format_iso(d: date) -> str:
    return d.strftime("%Y-%m-%d")


def season_months(start_date: date, end_date: date) -> List[int]:
    """Calendar months spanned by the window, replicating the production filter
    (production compares only the month token of the file start date)."""
    return list(range(start_date.month, end_date.month + 1))
