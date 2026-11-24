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
- [IGE-OPERA/widetrax](https://github.com/IGE-OPERA/widetrax): reusable PSD/interpolation library. This repo vendors the Spectra compute chain (`src/Spectra.py`, compute functions identical to widetrax v1.1.1) and hosts un-merged production deltas (`src/DataPreprocessing_listv2.py`, patched `fill_nan`/`plot_psd`) pending upstreaming.
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

