import numpy as np
import pytest

from swotomip_spectra.output import DOCUMENT_KEYS, build_document

STORED_TEMPLATE_KEYS = [
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


def test_document_schema_matches_stored_template():
    doc = build_document(
        region="Global/LLC4320/Global_box_109",
        model="LLC4320",
        lon_min=30.0,
        lon_max=40.0,
        lat_min=-40.0,
        lat_max=-30.0,
        start_date="2024-01-01",
        end_date="2024-03-31",
        freqs=np.linspace(0, 0.25, 295),
        psd=np.linspace(1e-2, 1e-8, 295),
        packages_versions_str="numpy : x\n",
        date_creation="2026-11-23T00:00:00",
        creator="test-node",
    )
    assert list(doc.keys()) == STORED_TEMPLATE_KEYS == DOCUMENT_KEYS
    assert doc["lon_min"] == 30.0 and doc["lat_min"] == -40.0
    assert len(doc["Frequency"]) == len(doc["Spectra"]) == 295
    assert isinstance(doc["machine_info"], dict)


def test_empty_spectra_refused():
    with pytest.raises(ValueError):
        build_document(
            "r", "m", 0, 1, 0, 1, "2024-01-01", "2024-03-31",
            np.array([]), np.array([]),
        )
