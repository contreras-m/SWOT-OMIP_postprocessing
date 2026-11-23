from pathlib import Path

import pandas as pd
import pytest

from swotomip_spectra.calendar import (
    load_cycle_calendar,
    matching_cycles,
    season_months,
    season_window,
    zfill3,
)

ROOT = Path(__file__).resolve().parents[1]

CLEAN_CSV = "cycle,start_date,end_date\n8,2024-01-01 00:07:06,2024-01-04 03:34:26\n9,2024-01-04 03:34:27,2024-01-25 00:19:31\n10,2024-01-25 00:19:32,2024-02-14 21:04:36\n"

PREAMBLE_CSV = "# cycles_periods\nsome header junk\ncycle_number,start_time,end_time\n8,2024-01-01,2024-01-04\n9,2024-01-04,2024-01-25\n"


def _tmp_csv(tmp_path, text):
    p = tmp_path / "cal.csv"
    p.write_text(text)
    return p


def test_clean_header_csv(tmp_path):
    cal = load_cycle_calendar(_tmp_csv(tmp_path, CLEAN_CSV))
    assert list(cal["cycle"]) == [8, 9, 10]


def test_preamble_csv(tmp_path):
    cal = load_cycle_calendar(_tmp_csv(tmp_path, PREAMBLE_CSV))
    assert list(cal["cycle"]) == [8, 9]


def test_overlap_semantics(tmp_path):
    cal = load_cycle_calendar(_tmp_csv(tmp_path, CLEAN_CSV))
    start, end = season_window("JFM")
    assert matching_cycles(cal, start, end) == [8, 9, 10]
    assert matching_cycles(cal, "2024-01-20", "2024-01-22") == [9]
    assert matching_cycles(cal, "2024-06-01", "2024-06-15") == []


def test_repo_calendar_includes_early_cycles_for_jfm():
    cal = load_cycle_calendar(ROOT / "data" / "time_ranges.csv")
    assert list(cal["cycle"]) == list(range(8, 27))
    start, end = season_window("JFM")
    cycles = matching_cycles(cal, start, end)
    assert 8 in cycles and 9 in cycles
    assert cycles == [8, 9, 10, 11, 12, 13]


def test_zfill3_and_months():
    assert zfill3([8, 26]) == ["008", "026"]
    start, end = season_window("JFM")
    assert season_months(start, end) == [1, 2, 3]
    start, end = season_window("ASO")
    assert season_months(start, end) == [8, 9, 10]
