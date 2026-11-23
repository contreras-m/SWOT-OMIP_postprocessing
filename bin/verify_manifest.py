#!/usr/bin/env python
"""Refresh spectra_manifest.yaml by probing spectra stores (read-only, never computes).

Probes the legacy DIVE store and the ige two-tier store for every (dataset x year x
season x box) key and records what exists. Anonymous exact-key access works on both
stores; listing is not required.

Examples:
  python bin/verify_manifest.py --datasets LLC4320,eINALT100
  python bin/verify_manifest.py --datasets GLO12V4 --sample 20
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def key_exists(endpoint_url: str, key: str, anon: bool = True) -> bool:
    import s3fs

    fs = s3fs.S3FileSystem(anon=anon, endpoint_url=endpoint_url)
    try:
        return bool(fs.exists(key))
    except Exception as exc:
        logging.getLogger(__name__).debug("probe failed for %s: %s", key, exc)
        return _http_exists(endpoint_url, key)


def _http_exists(endpoint_url: str, key: str) -> bool:
    import urllib.request
    import urllib.error

    url = f"{endpoint_url.rstrip('/')}/{key}"
    try:
        with urllib.request.urlopen(url) as resp:
            return 200 <= resp.status < 300
    except urllib.error.HTTPError as err:
        return err.code == 200
    except Exception:
        return False


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--datasets", default=None, help="comma-separated dataset names (default: all registered)")
    parser.add_argument("--seasons", default="JFM,JAS")
    parser.add_argument("--sample", type=int, default=0, help="probe only the first N boxes per (dataset, season)")
    parser.add_argument("--manifest", default=str(ROOT / "spectra_manifest.yaml"))
    parser.add_argument("--init", action="store_true", help="create the manifest if it does not exist")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.WARNING)

    from swotomip_spectra.manifest import dataset_section, load, new_manifest, record_probe, save
    from swotomip_spectra.registry import Registry

    registry = Registry.load(ROOT / "config" / "datasets.yaml")
    manifest = load(args.manifest)
    if manifest is None:
        if not args.init:
            raise SystemExit(f"no manifest at {args.manifest}; pass --init to create it")
        manifest = new_manifest(registry)

    names = [d.strip() for d in args.datasets.split(",")] if args.datasets else list(registry.datasets)
    seasons = [s.strip().upper() for s in args.seasons.split(",") if s.strip()]
    n_boxes = len(__import__("json").loads(Path(registry.region["boxes_file"]).read_text())["features"])

    dive = registry.dive_store()
    box_ids = list(range(n_boxes if args.sample <= 0 else min(args.sample, n_boxes)))

    for name in names:
        spec = registry.get(name)
        years = spec.resolve_years(None)
        section = dataset_section(manifest, name)
        section["spectra_key"] = spec.spectra_key
        section["privacy"] = spec.privacy
        section["years"] = list(spec.years) or None

        for year in years:
            yl = year if year else None
            for season in seasons:
                dive_hits = []
                if dive is not None:
                    for bx in box_ids:
                        key = registry.dive_spectra_key(spec, yl, bx, season)
                        if key and key_exists(dive.endpoint_url, key, dive.anon):
                            dive_hits.append(bx)
                    record_probe(manifest, name, yl, season, "dive", len(dive_hits), len(box_ids), dive_hits or None)

                store = registry.store_for(spec)
                ige_hits = []
                for bx in box_ids:
                    uri = registry.target_uri(spec, yl, bx, season)
                    ige_key = uri.replace("s3://", "", 1)
                    if key_exists(store.endpoint_url, ige_key, store.anon):
                        ige_hits.append(bx)
                record_probe(manifest, name, yl, season, store.name, len(ige_hits), len(box_ids), ige_hits or None)

                print(
                    f"{name}" + (f"/{yl}" if yl else "") + f" {season}: dive {len(dive_hits)}/{len(box_ids)}"
                    f" | {store.name} {len(ige_hits)}/{len(box_ids)}"
                )

    save(args.manifest, manifest)
    print(f"manifest updated: {args.manifest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
