"""Dataset registry loading and path/naming authority."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import yaml

SEASON_WINDOWS = {
    "JFM": ("2024-01-01", "2024-03-31"),
    "FMA": ("2024-02-01", "2024-04-30"),
    "AMJ": ("2024-04-01", "2024-06-30"),
    "JAS": ("2024-07-01", "2024-09-30"),
    "ASO": ("2024-08-01", "2024-10-31"),
    "OND": ("2024-10-01", "2024-12-31"),
}

DEFAULT_FILENAME_REGEX = (
    r"_(?P<cycle>\d{3})_(?P<pass>\d{3})_(?P<start>\d{8}T\d{6})_(?P<end>\d{8}T\d{6})[_.]"
)


@dataclass(frozen=True)
class S3Source:
    endpoint_url: str
    base: str
    anon: bool = True

    def base_for_year(self, year: Optional[str]) -> str:
        if year is None:
            return self.base
        return self.base.format(year=year)


@dataclass(frozen=True)
class LocalSource:
    root: str

    def root_for_year(self, year: Optional[str]) -> str:
        if year is None:
            return self.root
        return self.root.format(year=year)


@dataclass(frozen=True)
class Store:
    name: str
    uri: Optional[str]
    endpoint_url: str
    anon: bool = True
    spectra_prefix: Optional[str] = None


@dataclass(frozen=True)
class DatasetSpec:
    name: str
    spectra_key: str
    privacy: str
    status: str
    ssh_varname: str
    lon_convention: str
    years: Tuple[str, ...]
    s3: Optional[S3Source]
    local: Optional[LocalSource]
    note: str

    @property
    def is_multiyear(self) -> bool:
        return bool(self.years)

    def resolve_years(self, requested: Optional[Sequence[str]]) -> List[str]:
        if not self.years:
            return [""]
        if requested is None:
            return list(self.years)
        missing = [y for y in requested if y not in self.years]
        if missing:
            raise ValueError(f"years {missing} not in dataset years {list(self.years)}")
        return list(requested)


class Registry:
    def __init__(self, cfg: Dict, path: Path):
        self._cfg = cfg
        self.path = Path(path).resolve()

        self.defaults = dict(cfg.get("defaults", {}))
        self.region = dict(cfg.get("regions", {}).get("global", {}))

        self.season_windows = dict(SEASON_WINDOWS)
        for name, window in (cfg.get("season_windows") or {}).items():
            self.season_windows[name] = (str(window[0]), str(window[1]))

        self.seasons = list(self.season_windows)

        self.stores: Dict[str, Store] = {}
        for name, s in (cfg.get("stores") or {}).items():
            if s.get("uri") is None and s.get("spectra_prefix") is None:
                raise ValueError(f"store {name} needs uri or spectra_prefix")
            self.stores[name] = Store(
                name=name,
                uri=s.get("uri"),
                endpoint_url=s["endpoint_url"],
                anon=bool(s.get("anon", True)),
                spectra_prefix=s.get("spectra_prefix"),
            )

        self.datasets: Dict[str, DatasetSpec] = {}
        for name, d in (cfg.get("datasets") or {}).items():
            s3 = d.get("s3")
            local = d.get("local")
            self.datasets[name] = DatasetSpec(
                name=name,
                spectra_key=d["spectra_key"],
                privacy=d.get("privacy", "public"),
                status=d.get("status", "unverified"),
                ssh_varname=d.get("ssh_varname", "ssh"),
                lon_convention=d.get("lon_convention", "0_360"),
                years=tuple(d.get("years") or ()),
                s3=S3Source(**s3) if s3 else None,
                local=LocalSource(**local) if local else None,
                note=d.get("note", ""),
            )

    @classmethod
    def load(cls, path) -> "Registry":
        path = Path(path)
        cfg = yaml.safe_load(path.read_text())
        return cls(cfg, path)

    def get(self, name: str) -> DatasetSpec:
        if name not in self.datasets:
            raise KeyError(
                f"unknown dataset {name!r}; registered: {sorted(self.datasets)}"
            )
        return self.datasets[name]

    def default_seasons(self) -> List[str]:
        return list(self.defaults.get("seasons", ["JFM", "JAS"]))

    def store_for(self, spec: DatasetSpec) -> Store:
        name = "ige_private" if spec.privacy == "private" else "ige_public"
        if name not in self.stores:
            raise KeyError(f"store {name} missing from registry")
        return self.stores[name]

    def dive_store(self) -> Optional[Store]:
        return self.stores.get("dive")

    def default_spectra_key_dir(self, spec: DatasetSpec, year: Optional[str]) -> str:
        base = f"Global/{spec.spectra_key}"
        if spec.is_multiyear and year:
            base = f"{base}/{year}"
        return base

    def target_uri(self, spec: DatasetSpec, year: Optional[str], box_id: int, season: str) -> str:
        store = self.store_for(spec)
        return "/".join(
            [
                store.uri.rstrip("/"),
                self.default_spectra_key_dir(spec, year),
                self.spectra_filename(spec, box_id, season),
            ]
        )

    def region_label(self, spec: DatasetSpec, year: Optional[str], box_id: int) -> str:
        return f"{self.default_spectra_key_dir(spec, year)}/Global_box_{box_id}"

    def spectra_filename(self, spec: DatasetSpec, box_id: int, season: str) -> str:
        return f"Global_box_{box_id}_{season}_{spec.spectra_key}.json"

    def dive_spectra_key(self, spec: DatasetSpec, year: Optional[str], box_id: int, season: str) -> Optional[str]:
        store = self.dive_store()
        if store is None or store.spectra_prefix is None:
            return None
        return (
            f"{store.spectra_prefix.rstrip('/')}/{spec.spectra_key}/"
            f"{self.spectra_filename(spec, box_id, season)}"
        )

    def cycles_base_s3(self, spec: DatasetSpec, year: Optional[str]) -> Optional[str]:
        if spec.s3 is None:
            return None
        return spec.s3.base_for_year(year if spec.is_multiyear else None)

    def cycles_root_local(self, spec: DatasetSpec, year: Optional[str]) -> Optional[str]:
        if spec.local is None:
            return None
        return spec.local.root_for_year(year if spec.is_multiyear else None)
