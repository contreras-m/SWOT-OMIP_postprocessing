# SWOT-OMIP_postprocessing

This repo contains the code for post-processing the contribution from SWOT-OMIP project (GH). 

Data directory contains the dataset used in this repo. An additional dataset is
the first-baroclinic gravity- and Rossby-wave speed dataset of Erik Oliver
(first baroclinic gravity wave speeds computed from CARS2009 temperature and
salinity following Chelton et al., JPO, 1998; 0.5° grid). Data page:
https://ecjoliver.weebly.com/rossby-radius.html — direct NetCDF:
http://passage.phys.ocean.dal.ca/~olivere/data/Rossby_radius.nc.
The binary is not committed; fetch and verify it with
`bash bin/download_rossby_radius.sh` (pins
sha256 `18da15b074b14e87bad24930146be7660c3ba3ac0745b87767cb850c9231ab96`).

Notebook directory include the follow code:
* Wavenumber_Spectra_Computation_GlobalBoxes: Estimate the SSH spectra (online)
* plot_cumpsd_ratio-scatter.ipynb.ipynb: plot figure 2 from article
* plot_slope_onl_v3+tides.ipynb : plot figure 4 from article
* region_plot_spectr_noonl_AG-Copy1-IMPR.ipynb plot figure 1 from article
* region_plot_spectr_noonl_AG-Copy1-IMPR.ipynb plot figure S1O from  SI article
* plot_cumpsd_scatterplt_SI.ipynb plot figure S2  from  SI article
* save_geojson_boxes_v3.ipynb : define and save boxes position

The functions needed for the notebook are located in the src directory.

## Repo articulation (SWOT-OMIP ecosystem)

- [IGE-OPERA/swot-omip](https://github.com/IGE-OPERA/swot-omip): public protocol repo — data conventions, dataset metadata, contribution status, and the one-box demo notebook (`_processing/`).
- **This repo** (`contreras-m/SWOT-OMIP_postprocessing`): paper-specific production — the parameterized spectra pipeline (`src/swotomip_spectra/` + `bin/compute_spectra.py`), the plot notebooks behind the paper figures, box definitions (`data/`), the cycle calendar, and `spectra_manifest.yaml`.
- [IGE-OPERA/widetrax](https://github.com/IGE-OPERA/widetrax) (>= 1.2, on PyPI): the PSD/interpolation library. The SWOT-OMIP production deltas (pass preselection + list readers, pyinterp>=2026 `fill_nan`, `plot_psd` styling) were upstreamed via IGE-OPERA/widetrax#20; the vendored copies (`src/DataPreprocessing_listv2.py`, `src/Spectra.py`) are removed and notebooks import `widetrax` directly.
- `contreras-m/SWOT_OMIP-processing`: earlier notebook generation, **superseded by this repo**.

## Spectra pipeline (`bin/compute_spectra.py`)

Computes along-track SSH wavenumber spectra per chunk = (dataset x year x global box x season), replicating the production chain (Gauss-Seidel `fill_nan` with the nadir-gap column mask, segments per cross-track pixel column, Welch `fs=0.5`, min segment length 120 pts), and writes JSONs schema-compatible with the existing DIVE store (`project-meom-ige/OMIP/Global/…/Global_box_{box}_{season}_{KEY}.json`).

Datasets, endpoints and output stores are declared in `config/datasets.yaml`. Sources are read from S3 (`--source s3`) or from local mirrors (`--source local --data-root DIR`). Output goes to a local tree by default (`--out-dir spectra_out`); `--push` writes to the ige spectra store (public tier for public datasets, private tier for eINALT100). Chunks whose spectrum already exists at the target store — or in the legacy DIVE store — are skipped (`--force` / `--no-dive-skip` to override). `--dry-run` plans without computing.

```bash
uv venv .venv --python 3.12
uv pip install --python .venv -r requirements-pipeline.txt

.venv/bin/python bin/compute_spectra.py --dataset LLC4320 --dry-run
.venv/bin/python bin/compute_spectra.py --dataset LLC4320 --seasons JFM --boxes 109 --source s3
.venv/bin/python bin/verify_manifest.py --init
```

`bin/verify_manifest.py` refreshes `spectra_manifest.yaml` by probing the stores (read-only).

## Spectra stores & status

**Decision (SWOT-OMIP meeting, 2026-11-23):** the systematic computation of spectra in all the boxes covering the globe lives in **this repo for the moment**. It will move to the [swot-omip protocol repo](https://github.com/IGE-OPERA/swot-omip) once all data providers have agreed to open the computed spectra with the paper — tracked in [IGE-OPERA/swot-omip#45](https://github.com/IGE-OPERA/swot-omip/issues/45). Until then the protocol repo does not track spectra status; this section is the record.

### Stores

| Store | Layout | Access |
|---|---|---|
| DIVE (legacy, read-only) | `s3://project-meom-ige/OMIP/Global/…/Global_box_{box}_{season}_{KEY}.json` @ `https://minio.dive.edito.eu` | anonymous read |
| ige (new canonical, two tiers) | `s3://ige/public/swot-omip/spectra/Global/{KEY}/…` and `s3://ige/private/swot-omip/spectra/Global/GEOMAR/{year}/…` @ `https://s3-ige-ping.osug.fr` | public tier anonymous; private tier restricted |

### Coverage (probed 2026-11-23 with `bin/verify_manifest.py`)

| Dataset (store key) | Coverage |
|---|---|
| LLC4320, GLO12V4, GLO36V1, NOC_eORCA025 (`NOC025`), NOC_eORCA12 (`NOC12`), SWOT_L3 (`SWOT`) | complete on DIVE: **282/282 boxes × JFM+JAS** — nothing to recompute |
| eINALT100 (`GEOMAR`) | ige private tier: **41 boxes × 4 seasons (JFM/AMJ/JAS/OND) × 2021–2023** = 492 files provided by contreras-m. 228 carry spectra (19 boxes); 264 are empty-spectra results (22 boxes: 14–20, 39, 46, 154–155, 177–181, 202, 257, 269–270, 279–280) — pending confirmation whether expected or to be regenerated |

Remaining computation gap for eINALT100: JFM+JAS for 241 boxes × 3 years (**1446 chunks**, run on request).

The live record is `spectra_manifest.yaml`, refreshed by `bin/verify_manifest.py --init` (read-only probing of the stores).

## Paper figures (`scripts/figures/`)

Every paper figure is produced by a parameterized script — the
producer-of-record — png (300 dpi) + pdf with a tight crop; the notebooks
remain as exploration. Full manifest, workflow and known quirks:
[FIGURES.md](FIGURES.md). Quickstart:

```bash
python3 bin/prepare_figure_cache.py --regions agulhas,natl,global   # once, ~50 MB
.venv/bin/python3 scripts/figures/fig1_agulhas.py                   # offline cache (add --online for anon DIVE)
.venv/bin/python3 bin/compare_figures.py --out /tmp/check           # scores + 1500 px contact sheets
.venv/bin/python3 bin/sync_figure_to_paper.py Fig1                   # copy the tex-referenced file into the paper repo
```

The audit tooling behind this lives in `bin/run_figure_notebooks.py`
(nbclient runner with disclosed s3fs shim) and `bin/compare_figures.py`
(crop-tolerant structural scoring, cross matrices, contact sheets).

