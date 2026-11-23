"""swotomip_spectra: parameterized wavenumber-spectra pipeline for SWOT-OMIP."""

__version__ = "0.1.0"

from .registry import Registry, DatasetSpec, Store, SEASON_WINDOWS
from .calendar import load_cycle_calendar, matching_cycles

__all__ = [
    "Registry",
    "DatasetSpec",
    "Store",
    "SEASON_WINDOWS",
    "load_cycle_calendar",
    "matching_cycles",
]
