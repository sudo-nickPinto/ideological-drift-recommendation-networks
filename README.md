# Ideological Drift in Recommendation Networks

Graph-based analysis code for studying whether a recommendation network can move users toward more extreme political content even when the user is modeled only as a walker following recommendations.

## What This Repository Does

The project uses the Recfluence YouTube recommendation dataset to model channels as nodes, recommendations as directed edges, and channel ideology as a numeric score. The implemented pipeline then simulates weighted recommendation-following behavior, computes drift and structural metrics, and generates figures plus summary tables.

The current presentation-facing questions are simple:

1. Do recommendation paths tend to change ideology direction overall?
2. Do recommendation paths tend to increase ideological extremity?

## Current Status

The core analysis pipeline is implemented and covered by pytest.

- Graph ingestion is implemented in `src/graph_builder.py`.
- Ideology scoring is implemented in `src/ideology.py`.
- Weighted random-walk simulation is implemented in `src/simulator.py`.
- Drift and network metrics are implemented in `src/metrics.py`.
- Figure and CSV generation are implemented in `src/visualize.py`.
- Synthetic fixture-driven tests exist for every module in `tests/`.

What is not in the repository yet:

- Committed generated figures or metrics tables from the real dataset. The `results/` directories exist for local outputs, but generated artifacts remain untracked.

## Implemented Pipeline

The analysis flow in the codebase is:

1. `graph_builder.py`
   Reads the node and edge CSV files with pandas, builds a `networkx.DiGraph`, attaches node and edge attributes, and removes self-loops.
2. `ideology.py`
   Converts `LR` labels into `IDEOLOGY_SCORE` values using `L -> -1.0`, `C -> 0.0`, and `R -> 1.0`.
3. `simulator.py`
   Runs weighted random walks using `RELEVANT_IMPRESSIONS_DAILY` as the default edge weight.
4. `metrics.py`
   Computes per-walk drift, extremity change, mean summaries, ideology assortativity, average clustering, and a packaged metrics dictionary.
5. `visualize.py`
   Writes the baseline figure bundle and CSV tables from the graph, trajectories, and metrics.

This modular order matters because each stage assumes the previous one has already prepared the required inputs. For example, the simulator expects ideology scores to already be attached to nodes, and the metrics module expects walk trajectories in the simulator's step-record format.

## Repository Layout

| Path | Purpose |
|------|---------|
| `src/graph_builder.py` | Load CSV data and build the directed recommendation graph |
| `src/ideology.py` | Attach numeric ideology scores to graph nodes |
| `src/simulator.py` | Run weighted random walks through the graph |
| `src/metrics.py` | Compute drift summaries and graph-level polarization metrics |
| `src/visualize.py` | Generate PNG figures and a summary CSV |
| `run.py` | The one obvious file to run with the Play button |
| `src/run_pipeline.py` | The internal step-by-step orchestration logic used by `run.py` |
| `tests/` | Pytest coverage for each module |
| `tests/fixtures/` | Synthetic CSV fixtures used to test the pipeline deterministically |
| `data/README.md` | Dataset provenance, acquisition steps, and schema notes |
| `docs/SYSTEM_DESIGN.md` | Architecture, data flow, and validation strategy |
| `results/figures/` | Local output directory for generated figures |
| `results/tables/` | Local output directory for generated tables |

## Dataset

This repository is built around the Recfluence dataset by Mark Ledwich and Anna Zaitsev.

- Source repository: <https://github.com/markledwich2/Recfluence>
- License: MIT
- Core files used here: `vis_channel_stats.csv` and `vis_channel_recs2.csv`

For download steps, provenance, schema details, and data quality notes, use [data/README.md](data/README.md). That file is the source of truth for data acquisition and field-level meaning.

## Setup

1. Create and activate a virtual environment.
2. Install dependencies from `requirements.txt`.
3. Download the Recfluence CSVs described in [data/README.md](data/README.md) into `data/`.

Example:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run The Full Pipeline

The beginner-friendly way to run the whole project is:

1. Open `run.py`
2. Press the VS Code Play button

If you prefer the terminal, use:

```bash
python3 run.py
```

That script loads the real dataset from `data/`, builds and scores the graph,
runs deterministic weighted random walks, computes metrics, and writes figures
plus `summary_metrics.csv` into `results/`.

Optional flags:

```bash
python3 run.py --num-steps 15 --walks-per-start 2 --seed 123
```

## Two Run Modes

The same entrypoint supports two workflows:

1. Baseline mode
   This is the default. It runs one deterministic simulation using the current
   start-node rule and writes the familiar four PNG figures plus
   `results/tables/summary_metrics.csv`.
2. Experiment mode
   This first refreshes the baseline bundle, then runs a repeated experiment
   across three start policies, four step counts, and multiple seeds to make
   the two headline questions more defensible. It also writes two
   experiment-specific summary PNGs and prints experiment-level headline
   numbers in the terminal so the repeated run does not look identical to the
   baseline pass.

Use experiment mode like this:

```bash
python3 run.py --mode experiment
```

The repeated experiment keeps the ideology metric formulas unchanged. It varies:

- Start policy: current valid starts, center-only starts, ideology-balanced starts
- Steps per walk: `1`, `5`, `10`, `20`
- Walks per start: `5`
- Seeds: `5`
- Start-node cap per policy: `900`

In experiment mode, the baseline CLI flags `--num-steps`, `--walks-per-start`,
and `--seed` still control the baseline refresh pass. The repeated experiment
uses its fixed matrix inside `src/run_pipeline.py`.

When you launch experiment mode from a real terminal, the CLI now shows a live
simulation dashboard with a progress bar, current configuration number, start
group, seed, steps per walk, and selected-start counts.

## Validation

The commands below assume the project virtual environment is already active
with `source .venv/bin/activate`.

The narrowest routine checks in this repository are the module-level pytest files.

```bash
python3 -m pytest tests/test_graph_builder.py -v
python3 -m pytest tests/test_ideology.py -v
python3 -m pytest tests/test_simulator.py -v
python3 -m pytest tests/test_metrics.py tests/test_visualize.py -v
```

To run the full current test suite:

```bash
python3 -m pytest -v
```

## Outputs

`src/visualize.py` generates the following local artifacts:

- `results/figures/ideology_distribution.png`
- `results/figures/drift_distribution.png`
- `results/figures/trajectory_sample.png`
- `results/figures/extremity_distribution.png`
- `results/figures/experiment_signed_drift_summary.png`
- `results/figures/experiment_extremity_change_summary.png`
- `results/tables/summary_metrics.csv`
- `results/tables/experiment_per_run.csv`
- `results/tables/experiment_grouped_summary.csv`
- `results/tables/presentation_headline_metrics.csv`

Repeated runs automatically delete stale image files from `results/` and
`results/figures/` before writing the current PNG bundle. Existing CSV tables
in `results/tables/` are preserved unless a run overwrites a specific file.

The presentation table is intentionally plain English. It focuses only on:

- signed ideological drift: whether the network tends to push users left or right overall
- extremity change: whether walks tend to end farther from or closer to the center

Those outputs are intentionally untracked because they are regenerable from code plus data.

## Source-of-Truth Guidance

Use the repository documents in this order when you need to understand or update the project:

1. [README.md](README.md) for the current workflow, setup, and project status.
2. [docs/SYSTEM_DESIGN.md](docs/SYSTEM_DESIGN.md) for architecture and module boundaries.
3. [data/README.md](data/README.md) for data provenance and schema.
4. `tests/` for the currently implemented behavior and expected interfaces.

When these disagree, trust the implemented code and tests first, then update the docs.
