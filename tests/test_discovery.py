from datetime import date

from swotomip_spectra.calendar import season_window
from swotomip_spectra.discovery import (
    FileMatch,
    filter_matches,
    match_filename,
)

LLC = "LLC4320_GRID_L3_LR_SSH_008_497_20240101T000706_20240101T005832_v1.0.2.nc"
GEOMAR = "SWOT_GRID_L3_LR_SSH_008_499_20240101T015000_20240101T024126_eINALT100.nc"


def _match(name):
    return match_filename(f"some/prefix/cycle_008/{name}")


def test_parse_protocol_filename():
    m = _match(LLC)
    assert m is not None
    assert m.cycle == 8
    assert m.pass_number == 497
    assert m.start.month == 1


def test_parse_geomar_filename():
    m = _match(GEOMAR)
    assert m is not None
    assert m.cycle == 8
    assert m.pass_number == 499
    assert m.start.year == 2024


def test_parse_rejects_malformed():
    assert _match("file_without_ssh_token.nc") is None
    assert _match("MODEL_20240101.nc") is None


def test_filter_by_pass_and_month():
    m1 = _match(LLC)
    m2 = _match(GEOMAR)
    kept = filter_matches([m1, m2], pass_numbers=[497], months=[1])
    assert [k.pass_number for k in kept] == [497]
    kept = filter_matches([m1, m2], pass_numbers=[497, 499], months=[7])
    assert kept == []
    kept = filter_matches([m1, None, m2], pass_numbers=[497, 499], months=[1, 2, 3])
    assert len(kept) == 2
