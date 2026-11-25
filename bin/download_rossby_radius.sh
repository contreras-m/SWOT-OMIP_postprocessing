#!/usr/bin/env bash
# Fetch the first-baroclinic gravity/Rossby wave-speed dataset used by
# notebook/plotscale_ratioSWOT_meanlat_V3.ipynb (paper figures 3 and S5).
#
# Source: Erik Oliver's "Rossby radius" data page
#   https://ecjoliver.weebly.com/rossby-radius.html
# direct file (NetCDF, linked from that page):
#   http://passage.phys.ocean.dal.ca/~olivere/data/Rossby_radius.nc
# The dataset gives first-baroclinic gravity-wave speeds from CARS2009
# temperature/salinity following Chelton et al. (JPO, 1998), 0.5° grid.
#
# The file is NOT committed (binary). This script is idempotent: an existing
# file with the pinned checksum is left untouched.
set -euo pipefail

URL="http://passage.phys.ocean.dal.ca/~olivere/data/Rossby_radius.nc"
SHA256="18da15b074b14e87bad24930146be7660c3ba3ac0745b87767cb850c9231ab96"
OUT="$(cd "$(dirname "$0")/.." && pwd)/data/Rossby_radius.nc"
TMP="${OUT}.part"

mkdir -p "$(dirname "$OUT")"

if [ -f "$OUT" ] && echo "$SHA256  $OUT" | shasum -a 256 --check --quiet; then
    echo "Rossby_radius.nc already present with pinned checksum: $OUT"
    exit 0
fi

echo "downloading $URL"
curl -L --fail --retry 3 -o "$TMP" "$URL"
if echo "$SHA256  $TMP" | shasum -a 256 --check --quiet; then
    mv "$TMP" "$OUT"
    echo "ok: $OUT (sha256 $SHA256)"
else
    echo "checksum mismatch for $TMP — removing partial download" >&2
    rm -f "$TMP"
    echo "expected sha256: $SHA256" >&2
    exit 1
fi
