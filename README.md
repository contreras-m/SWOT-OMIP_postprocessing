# SWOT-OMIP_postprocessing

Spectra pipeline and figure scripts for the SWOT-OMIP ocean-model
intercomparison paper on the seasonal variability of sea-surface height
(the *2026 seasonality paper*, manuscript in preparation: how the seasonal
cycle of SSH spectral variance compares across ocean simulations and SWOT
L3 observations). This README is written for a reader who wants to **(a)
reproduce a paper figure**, **(b) understand where its data come from**, or
**(c) recompute the spectra from the model outputs** — in that order.

The paper's figures (4 main + 10 supplementary) are **produced by scripts**
in [`scripts/figures/`](scripts/figures) — one parameterized script per
figure — and synced into the paper repository from there. The Jupyter
notebooks those scripts were ported from stay in [`notebook/`](notebook)
as interactive exploration. The figure ↔ script ↔ notebook map, workflow
and known quirks: [FIGURES.md](FIGURES.md).

## Reproduce a figure

Python 3.12 on macOS or Linux. The public data is read anonymously from S3
(no account needed); the one input that is not yet public (GEOMAR / eINALT100
spectra) is covered in its own step below. Only steps 2 and 3 use the
network; once the cache exists, every figure runs offline in minutes.

### 1. Environment

```bash
# with uv (https://docs.astral.sh/uv/):
uv venv .venv --python 3.12
uv pip install --python .venv -r requirements-pipeline.txt

# stdlib alternative:
python3 -m venv .venv
.venv/bin/pip install -r requirements-pipeline.txt
```

### 2. Spectra cache (one-time, ~50 MB)

The figure scripts read precomputed along-track SSH spectra (small JSONs
per ocean box × season × dataset). Fetching them once makes the figures
reproducible offline:

```bash
.venv/bin/python3 bin/prepare_figure_cache.py --regions agulhas,natl,global
```

Public keys are fetched from the legacy DIVE store (anonymous HTTPS), and
GEOMAR spectra are copied from a local mirror when one is configured (see
the GEOMAR step). The cache lands in `figure_cache/GLOBALv2/` (gitignored);
the command is idempotent — re-run to continue after an interruption.

### 3. Rossby radius file (needed by Fig 3 and S5 only)

```bash
bash bin/download_rossby_radius.sh
```

Downloads Erik Oliver's first-baroclinic gravity-wave speed dataset
(computed from the CARS2009 climatology following Chelton et al., JPO,
1998; 0.5° grid — data page:
https://ecjoliver.weebly.com/rossby-radius.html) into
`data/Rossby_radius.nc` (gitignored), verifying the pinned sha256.

### 4. Produce a figure

```bash
.venv/bin/python3 scripts/figures/fig1_agulhas.py
```

writes `figures_out/agulhas_modelsswot.png` (300 dpi) and `.pdf`, both with
a tight crop — this is exactly what the paper carries. Every producer
script supports `--online` (read the public store live instead of the
cache; GEOMAR always comes from the cache), `--cache DIR` and `--out DIR`.

To produce them all (a few minutes each from the cache):

```bash
for s in scripts/figures/[fs]*.py; do .venv/bin/python3 "$s" || break; done
```

### 5. Compare against the published figures

```bash
.venv/bin/python3 bin/compare_figures.py --out /tmp/check
```

scores each script output (`figures_out/`) against the paper repository's
committed figures and writes side-by-side contact sheets (1500 px). The
scores are crop-tolerant structural triage, **not** acceptance — the
contact sheets are; see *Scoring notes* in [FIGURES.md](FIGURES.md).

### GEOMAR (eINALT100) spectra — the private input

Fig 1 and S1 include the GEOMAR contribution (InAlt1K / eINALT100), whose
computed spectra are **not yet public** — they will open with the paper's
submission. Until then they live in the project's private S3 store, and the
cache builder copies them from a local mirror you point it at:

```bash
.venv/bin/python3 bin/prepare_figure_cache.py --geomar-root /path/to/GEOMAR_SSHspectrum
```

(any mirror of `Global_box_*_GEOMAR.json` under year directories 2021–2023;
the default looks at `../data/GEOMAR_SSHspectrum` relative to this repo).
Without a GEOMAR mirror the other figures still run; Fig 1 / S1 fail with
an explicit read error since their GEOMAR spectra are absent.

When the paper is submitted, all precomputed spectra will additionally be
gathered in a Zenodo record — the archival source of truth — with the S3
endpoints remaining a working convenience for collaborators.

### Numbers

The paper's quantitative statements are carried by its figures (the
values quoted in the text are the ones the plots show). Standalone
number-producing scripts do not exist yet; when they are added they will
live under [`scripts/`](scripts), their outputs checked in CI, and this
paragraph will point at them.

### Notebooks = interactive exploration

The notebooks are runnable but no longer the producers of record — fixes
land in the scripts first. To execute them headless with per-cell capture,
use `bin/run_figure_notebooks.py`.

| Notebook | Makes |
|---|---|
| `region_plot_spectr_noonl_AG-Copy1-IMPR.ipynb` | Fig 1, S1 |
| `plot_cumpsd_ratio-scatter.ipynb` | Fig 2, S3 |
| `plot_cumpsd_scatterplt_SI.ipynb` | S2 |
| `plot_cumratio_map.ipynb` | S4 |
| `plotscale_ratioSWOT_meanlat_V3.ipynb` | Fig 3, S5 |
| `plot_slope_onl_v3+tides.ipynb` | Fig 4, S6–S9 (+ one extra figure the paper does not use) |
| `region_plot_spectr_noonl_GS-Copy1-IMPR.ipynb` | S10 |
| `Wavenumber_Spectra_Computation_GlobalBoxes.ipynb` | computes the SSH spectra (the parameterized counterpart is `bin/compute_spectra.py`) |
| `save_geojson_boxes_v3.ipynb` | draws and saves the box definitions (`data/mostly_ocean_boxes_filtered.geojson`) |

## Where the data come from

Three layers:

1. **Input datasets — not read by the figure scripts.** The
   intercomparison compares ocean models through pseudo-SWOT datasets:
   model sea-surface height sampled onto SWOT's swath geometry, plus the
   SWOT L3 observations. Conventions, per-dataset metadata and contribution
   status live in the protocol repository
   [IGE-OPERA/swot-omip](https://github.com/IGE-OPERA/swot-omip).
2. **Precomputed spectra — what the figures read.** Along-track SSH
   wavenumber spectra per ocean box × season × dataset, stored as ~19 KB
   JSONs on the legacy DIVE store (`project-meom-ige/OMIP/Global/...` at
   `https://minio.dive.edito.eu`, anonymous read), plus the GEOMAR set
   (above). The cache builder fetches these; the recompute path below
   regenerates them.
3. **Small reference files — kept in this repo.**
   `data/mostly_ocean_boxes_filtered.geojson` (the 282 mostly-ocean boxes
   covering the globe; box ids in the spectra stores are 0-based feature
   indices), `data/KaRIn_2kms_science_geometries.geojson` (SWOT KaRIn 2 km
   science-mode geometries), `data/time_ranges.csv` (the SWOT repeat-cycle
   calendar), and the downloaded Rossby file (step 3).

## Recompute the spectra (advanced)

[`bin/compute_spectra.py`](bin/compute_spectra.py) computes along-track SSH
wavenumber spectra per chunk = (dataset × year × global box × season),
replicating the production chain (Gauss-Seidel `fill_nan` with the
nadir-gap column mask, segments per cross-track pixel column, Welch
`fs=0.5`, min segment length 120 pts), and writes JSONs
schema-compatible with the existing store. Internals:
[`src/swotomip_spectra/`](src/swotomip_spectra).

Datasets, endpoints and output stores are declared in
[`config/datasets.yaml`](config/datasets.yaml). Sources are read from S3
(`--source s3`) or from local mirrors (`--source local --data-root DIR`).
Output goes to a local tree by default (`--out-dir spectra_out`); `--push`
writes to the ige spectra store (public tier for public datasets, private
tier for eINALT100). Chunks whose spectrum already exists at the target
store — or in the legacy DIVE store — are skipped (`--force` /
`--no-dive-skip` to override). `--dry-run` plans without computing.

```bash
.venv/bin/python bin/compute_spectra.py --dataset LLC4320 --dry-run
.venv/bin/python bin/compute_spectra.py --dataset LLC4320 --seasons JFM --boxes 109 --source s3
.venv/bin/python bin/verify_manifest.py --init
```

`bin/verify_manifest.py` refreshes [`spectra_manifest.yaml`](spectra_manifest.yaml)
by read-only probing of the stores.

## Repository map

| Path | What it is |
|---|---|
| [`scripts/figures/`](scripts/figures) | **the producer scripts** (one per paper figure) + the ported helper modules (`_*.py`) |
| [FIGURES.md](FIGURES.md) | figure manifest: script ↔ notebook ↔ paper file ↔ status ↔ known quirks |
| [`notebook/`](notebook) | the exploration notebooks (table above) |
| [`bin/`](bin) | command-line tools — each documented at the top of the file |
| [`src/swotomip_spectra/`](src/swotomip_spectra) | the spectra pipeline package |
| [`src/`](src) | helper functions the notebooks import (`position_function.py`, `plot_psd1Xglobal1.py`, `cum_sp_onl_season_v3.py`) |
| [`data/`](data) | box definitions, cycle calendar, (downloaded) Rossby file |
| [`config/datasets.yaml`](config/datasets.yaml) | datasets, endpoints, output stores |
| [`tests/`](tests) | unit tests, including the one that keeps this README in phase |
| `figure_cache/`, `figures_out/`, `figure_runs/`, `spectra_out/` | gitignored working dirs (cache, figure outputs, notebook audit runs, pipeline output) |
| [`spectra_manifest.yaml`](spectra_manifest.yaml) | live spectra-store coverage record (refreshed by `bin/verify_manifest.py`) |

## This repo in the SWOT-OMIP ecosystem

- [IGE-OPERA/swot-omip](https://github.com/IGE-OPERA/swot-omip): the public
  **protocol** repo — data conventions, dataset metadata, contribution
  status, and the one-box demo notebook (`_processing/`). Nothing
  paper-specific.
- **This repo** (`contreras-m/SWOT-OMIP_postprocessing`): the paper's
  **production** — the parameterized spectra pipeline
  ([`src/swotomip_spectra/`](src/swotomip_spectra) +
  [`bin/compute_spectra.py`](bin/compute_spectra.py)), the figure producer
  scripts ([`scripts/figures/`](scripts/figures) + [FIGURES.md](FIGURES.md)),
  the plot notebooks, the box definitions and cycle calendar
  ([`data/`](data)), and `spectra_manifest.yaml`.
- [IGE-OPERA/widetrax](https://github.com/IGE-OPERA/widetrax) (>= 1.2, on
  PyPI): the PSD/interpolation library this pipeline pins; the SWOT-OMIP
  production deltas (pass preselection + list readers, pyinterp>=2026
  `fill_nan`, `plot_psd` styling) were upstreamed there.
- `contreras-m/SWOT_OMIP-processing`: the earlier notebook-only generation,
  **superseded by this repo**.

## Keeping this README true

Documentation drifts; this repo guards against it:

- On every push and pull request,
  [`.github/workflows/ci.yml`](.github/workflows/ci.yml) installs the
  environment exactly as step 1 above and runs `pytest` — including
  [`tests/test_readme.py`](tests/test_readme.py), which fails if this README
  mentions a path that does not exist, forgets a notebook or a `bin/` tool,
  if the FIGURES.md manifest drifts from `scripts/figures/`, or if stale
  names come back.
- Weekly (and on demand),
  [`.github/workflows/figure-smoke.yml`](.github/workflows/figure-smoke.yml)
  runs the fully-public part of the walkthrough end-to-end on a clean
  machine: environment → NATL spectra cache → Figure S10 → assert the PNG
  and PDF landed in `figures_out/`.
- **Contributor rule:** if you add or rename a producer script, a notebook
  or a `bin/` tool, update README and FIGURES.md in the same PR — CI will
  point at whatever you missed.

## For coauthors (transitory)

*This section records project state that is not part of the reader-facing
story — stores, coverage, the paper-sync workflow, open items. It is
expected to shrink as the paper nears submission and to disappear with the
Zenodo publication.*

### Spectra stores & coverage (probed 2026-11-23)

| Store | Layout | Access |
|---|---|---|
| DIVE (legacy, read-only) | `project-meom-ige/OMIP/Global/.../Global_box_{box}_{season}_{KEY}.json` @ `https://minio.dive.edito.eu` | anonymous read |
| ige (two tiers) | `s3://ige/public/swot-omip/spectra/Global/{KEY}/...` and `s3://ige/private/swot-omip/spectra/Global/GEOMAR/{year}/...` @ `https://s3-ige-ping.osug.fr` | public tier anonymous; private tier restricted |

Coverage: LLC4320, GLO12V4, GLO36V1, NOC025 (`NOC_eORCA025`), NOC12
(`NOC_eORCA12`) and SWOT are complete on DIVE (282/282 boxes × JFM+JAS —
nothing to recompute). eINALT100 (key `GEOMAR`) lives on the ige private
tier: 492 files = 41 boxes × 4 seasons (JFM/AMJ/JAS/OND) × 2021–2023; 228
carry spectra (19 boxes), 264 are empty-spectra results (22 boxes — pending
confirmation whether expected or to be regenerated), and the JFM+JAS
remainder for 241 boxes × 3 years (**1446 chunks**) is run on request.

**Where global-spectra computation lives** (meeting decision, 2026-11-23):
in this repo for the moment; it moves to the protocol repository once all
data providers agree to open the computed spectra with the paper — consent
tracked in
[IGE-OPERA/swot-omip#45](https://github.com/IGE-OPERA/swot-omip/issues/45).

### Paper-figure sync

```bash
.venv/bin/python3 bin/sync_figure_to_paper.py Fig1   # copies the tex-referenced file into the paper repo
```

then commit in the paper repo (the helper prints the provenance message).
Acceptance = contact sheets + eyeball; the score matrix and per-figure
quirks live in [FIGURES.md](FIGURES.md) (*Scoring notes* + *NOTES*). Status
(2026-11-25): 11 of the 14 figures are synced from the scripts; Fig 2 and
S3 follow after PR merge; S2 awaits the merged Fig 2 + S2 redesign.

### Open items

- S2 redesign (merge S2's scatter rows into Fig 2) — design answer pending.
- `ratio_model` season handling (Fig 3 / S5) and the S8/S9 "winter"
  colorbar labels — on the fix list (see FIGURES.md *NOTES*).
- GEOMAR year-less cache stand-ins become removable once the AG notebook
  is patched
  (`figure_cache/GLOBALv2/GEOMAR/_yearless_provenance.md`).
- Zenodo record of all precomputed spectra at submission (source of
  truth; see the GEOMAR step).

## License & citation

- Code: MIT — [LICENSE](LICENSE).
- Citation record: [CITATION.cff](CITATION.cff) — placeholder until the
  paper's author list is final; cite the paper once published.
- Contact: open an issue here, or reach the maintainers
  ([@contreras-m](https://github.com/contreras-m),
  [@lesommer](https://github.com/lesommer)).
