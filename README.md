# SWOT-OMIP_postprocessing

This repo contains the code for post-processing the contribution from SWOT-OMIP project (GH). 

Data directory contains the dataset used in this repo. Additional dataset is the first barolcinic gravity wave  and rossy wave speed which was obtain from "http://passage.phys.ocean.dal.ca/~olivere/

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

