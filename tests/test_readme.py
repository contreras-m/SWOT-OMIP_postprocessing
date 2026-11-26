"""Keep README.md in phase with the repository.

The reader-facing promise (see README, "Keeping this README true"):
every path this README mentions exists; every notebook in notebook/ is
mentioned (and no ghost notebook is); every producer script appears in
the FIGURES.md manifest; every bin/ tool is mentioned; no stale lingo
comes back; and code blocks go through the repo venv rather than a bare
interpreter. CI runs this on every push/PR; the scheduled figure-smoke
workflow exercises the README walkthrough end-to-end on a clean machine.
"""
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
README = (REPO / "README.md").read_text()
FIGURES_MD = (REPO / "FIGURES.md").read_text()
REQUIREMENTS = (REPO / "requirements-pipeline.txt").read_text()

NOTEBOOKS = {p.name for p in (REPO / "notebook").glob("*.ipynb")}
PRODUCERS = {p.name for p in (REPO / "scripts" / "figures").glob("[fs]*.py")}
BIN_TOOLS = {p.name for p in (REPO / "bin").glob("*.py")}

# Dirs a fresh checkout does not have (gitignored working dirs) and files
# the walkthrough downloads on purpose: mentioning them is fine.
GENERATED_DIR_PREFIXES = {"figure_cache", "figures_out", "figure_runs", "spectra_out", ".venv"}
ALLOW_MISSING = {"data/Rossby_radius.nc"}

STALE_LINGO = (".ipynb.ipynb", "S1O", "pending upstreaming")

PATH_TOKEN = re.compile(
    r"(?<![\w./])(?:\.github|bin|scripts|notebook|data|config|src|tests)/[\w.+\-]+"
)


def _code_blocks(text: str):
    parts = text.split("```")
    return [parts[i] for i in range(1, len(parts), 2)]


def test_mentioned_paths_exist():
    tokens = set(PATH_TOKEN.findall(README))
    missing = [
        t
        for t in tokens
        if t.split("/")[0] not in GENERATED_DIR_PREFIXES
        and t not in ALLOW_MISSING
        and not (REPO / t).exists()
    ]
    assert not missing, f"README mentions paths that do not exist: {sorted(missing)}"


def test_notebooks_mentioned_both_ways():
    mentioned = set(re.findall(r"[\w.+\-]+\.ipynb", README))
    ghost = mentioned - NOTEBOOKS
    unmentioned = NOTEBOOKS - mentioned
    assert not ghost, f"README mentions notebooks that do not exist: {sorted(ghost)}"
    assert not unmentioned, f"notebooks never mentioned in README: {sorted(unmentioned)}"


def test_bin_tools_mentioned():
    unmentioned = sorted(t for t in BIN_TOOLS if t not in README)
    assert not unmentioned, f"bin/ tools never mentioned in README: {unmentioned}"


def test_figures_manifest_matches_producer_scripts():
    rows = [
        ln
        for ln in FIGURES_MD.splitlines()
        if re.match(r"^\|\s*(?:Fig \d+|S\d+)\s*\|", ln)
    ]
    assert rows, "FIGURES.md manifest table not found"
    listed = {m for ln in rows for m in re.findall(r"[\w.+\-]+\.py", ln)}
    assert listed == PRODUCERS, (
        "FIGURES.md manifest and scripts/figures/ drifted: "
        f"manifest-only={sorted(listed - PRODUCERS)} "
        f"dir-only={sorted(PRODUCERS - listed)}"
    )


def test_no_stale_lingo():
    for word in STALE_LINGO:
        assert word not in README, f"stale lingo back in README: {word!r}"


def test_code_blocks_use_the_venv():
    offenders = []
    for block in _code_blocks(README) + _code_blocks(FIGURES_MD):
        for line in block.splitlines():
            bare = re.match(r"\s*(?:python3?|pip)\s", line)
            venv_creation = re.match(r"\s*python3?\s+-m\b", line)
            if bare and not venv_creation:
                offenders.append(line.strip())
    assert not offenders, (
        "bare-interpreter invocation outside the venv "
        "(use .venv/bin/python3): " + repr(offenders)
    )


def test_requirements_cover_the_figure_stack():
    for package in (
        "cartopy",
        "matplotlib",
        "numpy",
        "scipy",
        "xarray",
        "s3fs",
        "shapely",
        "geopandas",
        "widetrax",
    ):
        assert re.search(
            rf"(?m)^{package}\b", REQUIREMENTS
        ), f"{package} missing from requirements-pipeline.txt"
