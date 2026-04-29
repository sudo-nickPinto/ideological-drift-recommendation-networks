# System Design — Ideological Drift in Recommendation Networks

This document describes the architecture that is actually implemented in the repository today. Its job is not to describe a future wishlist. Its job is to explain how the current code is structured, why the modules are separated the way they are, how data moves through the pipeline, and how the test suite validates that behavior.

## Design Goals

The implemented system is intentionally small and modular because the research problem is conceptually sequential:

1. Load recommendation data.
2. Turn that data into a graph.
3. Attach ideology scores to nodes.
4. Simulate recommendation-following behavior.
5. Compute interpretable drift and network metrics.
6. Generate figures and a summary table.

That order matters. Each stage produces the exact structure the next stage needs, which keeps the code easy to test and easy to explain.

## Implemented Architecture

The repository currently uses a five-module pipeline.

```text
graph_builder.py -> ideology.py -> simulator.py -> metrics.py -> visualize.py
```

An orchestration layer now sits on top of that pipeline so the whole project can
be executed from one obvious script:

```text
run.py
```

### 1. Graph Builder

`src/graph_builder.py` is responsible for turning CSV files into a directed NetworkX graph.

Implemented public functions:

- `load_nodes(filepath)`
- `load_edges(filepath)`
- `build_graph(nodes_df, edges_df)`

Why this module exists separately:

- CSV loading and graph construction are foundational. If they are wrong, every downstream result is wrong.
- By isolating them, the tests can verify the graph schema before simulation or metrics are even involved.

What it adds to the graph:

- Nodes keyed by `CHANNEL_ID`
- Node attributes such as `CHANNEL_TITLE`, `LR`, `RELEVANCE`, `SUBS`, `MEDIA`, `TAGS`, and `IDEOLOGY`
- Directed edges from `FROM_CHANNEL_ID` to `TO_CHANNEL_ID`
- Edge attributes including `RELEVANT_IMPRESSIONS_DAILY` and `PERCENT_OF_CHANNEL_RECS`
- Self-loop filtering so channels recommending themselves do not distort walk behavior

### 2. Ideology Scoring

`src/ideology.py` converts the categorical `LR` field into a numeric `IDEOLOGY_SCORE`.

Implemented public function:

- `assign_ideology_scores(G)`

Why this is its own module:

- The graph builder should focus on preserving raw source data.
- The ideology scorer is the translation step from human-readable labels to numbers that later modules can calculate with.
- Keeping the mapping in one place avoids hidden scoring logic scattered across the codebase.

Implemented mapping:

- `L -> -1.0`
- `C -> 0.0`
- `R -> 1.0`
- Missing or unknown labels become `None`

### 3. Simulation

`src/simulator.py` models user navigation as weighted random walks.

Implemented public functions:

- `choose_next_node(G, current_node, rng=None, weight_attr="RELEVANT_IMPRESSIONS_DAILY")`
- `simulate_walk(...)`
- `simulate_walks(...)`

Why simulation is separated from metrics:

- The simulator should only produce trajectories.
- The metrics layer should only interpret trajectories.
- This split lets tests verify selection logic, stopping behavior, and trajectory shape independently from the math in the metrics module.

Key implementation choices:

- Uses `RELEVANT_IMPRESSIONS_DAILY` as the default edge weight.
- Falls back to uniform choice when all outgoing weights are zero or unusable.
- Stops cleanly at dead ends instead of fabricating extra steps.
- Accepts a seeded `random.Random` instance for deterministic tests.

Trajectory format:

Each walk is a list of step dictionaries with at least these fields:

- `step`
- `node_id`
- `ideology_score`

### 4. Metrics

`src/metrics.py` turns trajectories and graph structure into interpretable numbers.

Implemented public functions:

- `compute_walk_drift(...)`
- `compute_walk_extremity_change(...)`
- `compute_mean_drift(...)`
- `compute_mean_absolute_drift(...)`
- `compute_mean_extremity_change(...)`
- `compute_ideology_assortativity(...)`
- `compute_average_clustering(...)`
- `compute_all_metrics(...)`

Why this module exists:

- The research question is expressed in numbers, not raw trajectories.
- Grouping the formulas in one file makes the analytical contract explicit and testable.

Implemented metric behavior:

- Drift is `final_score - initial_score`.
- Extremity change is `|final_score| - |initial_score|`.
- Summary functions skip invalid trajectories instead of inventing fallback values.
- Assortativity filters out nodes with missing ideology scores before calling NetworkX.
- Clustering is computed on an undirected copy of the graph for a simpler and more teachable interpretation.

`compute_all_metrics()` packages results under the field names that downstream CSV output expects:

- `num_trajectories`
- `num_valid_drifts`
- `mean_drift`
- `mean_absolute_drift`
- `mean_extremity_change`
- `ideology_assortativity`
- `average_clustering`

### 5. Visualization and Reporting

`src/visualize.py` is the output stage of the pipeline.

Implemented public functions:

- `plot_ideology_distribution(G, output_path)`
- `plot_drift_distribution(trajectories, output_path)`
- `plot_trajectory_sample(trajectories, output_path, max_lines=20)`
- `plot_extremity_distribution(trajectories, output_path)`
- `save_metrics_table(metrics_dict, output_path)`
- `generate_all_figures(G, trajectories, metrics_dict, output_dir="results")`

Why this module also covers reporting:

- There is no separate `reporter.py` in the implemented repository.
- In the current design, writing the CSV summary and saving figures are part of the same final output layer.
- This is simpler and matches the actual code.

Key implementation choices:

- Uses the Matplotlib `Agg` backend so plots can be generated without a display.
- Uses seaborn styling for readable defaults.
- Writes local artifacts into `results/figures/` and `results/tables/`.
- Closes figures after saving to avoid memory buildup.

### 6. Orchestration and Runnable Script

`run.py` is the beginner-facing script.
`src/run_pipeline.py` contains the real orchestration logic that `run.py` calls.

Implemented public functions in `src/run_pipeline.py`:

- `prepare_graph(nodes_path, edges_path)`
- `choose_start_nodes(G, score_attr="IDEOLOGY_SCORE")`
- `run_pipeline(...)`
- `build_argument_parser()`
- `main(argv=None)`

Why this layer exists:

- The core modules were already implemented, but there was no single command that moved from raw data to output artifacts.
- The orchestration layer keeps the domain logic inside the existing modules and only handles sequencing, defaults, and command-line input.
- The root-level `run.py` keeps the user-facing entrypoint obvious for someone who is new to Python and wants one file to click.

Default orchestration behavior:

- Reads `data/vis_channel_stats.csv` and `data/vis_channel_recs2.csv`
- Selects default start nodes with known ideology scores and at least one outgoing edge
- Runs deterministic walks with a fixed random seed
- Writes outputs to `results/`

## Data Flow

The implemented data flow is:

```text
CSV files
  -> pandas DataFrames
  -> networkx.DiGraph with node/edge attributes
  -> scored graph with IDEOLOGY_SCORE on nodes
  -> simulated trajectories
  -> drift and structural metrics
  -> PNG figures + one-row CSV summary
```

The design stays local and in-memory. There is no database, API server, message queue, or front-end application because the current project does not need them. The workload is a research pipeline over a static dataset, so keeping everything in Python objects is the most direct and least fragile option.

## Actual Project Layout

The repository layout that exists today is:

| Path | Role in the architecture |
|------|--------------------------|
| `src/graph_builder.py` | Input loading and graph construction |
| `src/ideology.py` | Ideology label to score translation |
| `src/simulator.py` | Weighted random-walk generation |
| `src/metrics.py` | Walk-level and graph-level measurements |
| `src/visualize.py` | Figure and CSV generation |
| `run.py` | The one obvious runnable script for the full project |
| `src/run_pipeline.py` | End-to-end orchestration logic used by `run.py` |
| `tests/test_graph_builder.py` | Validates CSV loading, graph shape, and self-loop removal |
| `tests/test_ideology.py` | Validates ideology-score assignment and edge cases |
| `tests/test_simulator.py` | Validates weighted selection, dead ends, trajectory shape, and input checks |
| `tests/test_metrics.py` | Validates formulas, graph metrics, and packaged summaries |
| `tests/test_visualize.py` | Smoke-tests file generation and CSV content |
| `tests/test_run_pipeline.py` | Smoke-tests the one-command orchestration layer |
| `tests/fixtures/` | Synthetic test CSVs used across the suite |
| `data/README.md` | Dataset provenance and schema notes |
| `results/` | Local output destination for generated artifacts |

## Validation Strategy

The test suite is organized around the same pipeline order as the code.

### Module-level validation

- `test_graph_builder.py` checks row counts, required columns, directed graph creation, node and edge counts, and self-loop removal.
- `test_ideology.py` checks the `L/C/R` mapping, missing-label behavior, and score attribute coverage across all nodes.
- `test_simulator.py` checks dead-end handling, forced-choice paths, bad inputs, weight overrides, and multi-walk output structure.
- `test_metrics.py` checks exact hand-computed drift formulas, summary math, assortativity edge cases, clustering, and summary-field contracts.
- `test_visualize.py` checks that figures and CSV outputs are created successfully, and that the summary CSV content matches expected keys and values.
- `test_run_pipeline.py` checks the scored-graph preparation step, default start-node selection, full output generation, and the failure mode when no valid start nodes exist.

### Why the tests use synthetic fixtures

The repository uses small synthetic CSVs in `tests/fixtures/` because deterministic tests are more valuable than tests that depend on a large real dataset.

That gives three benefits:

1. The expected answer is human-checkable.
2. Random behavior can be controlled with fixed seeds or forced graph structures.
3. A failing test points to a logic bug rather than a data acquisition problem.

### Focused validation commands

The narrow current validation commands are:

```bash
python3 -m pytest tests/test_run_pipeline.py -v
python3 -m pytest tests/test_graph_builder.py -v
python3 -m pytest tests/test_ideology.py -v
python3 -m pytest tests/test_simulator.py -v
python3 -m pytest tests/test_metrics.py tests/test_visualize.py -v
```

For a full project pass:

```bash
python3 -m pytest -v
```

## Stack Choices

The implemented stack is intentionally conservative and research-friendly.

| Tool | Why it is used here |
|------|---------------------|
| Python | Keeps the pipeline readable and beginner-friendly |
| pandas | Loads and manipulates CSV data cleanly |
| NetworkX | Represents the recommendation graph and computes graph metrics |
| NumPy / SciPy | Available for numerical and scientific work in the environment |
| Matplotlib / seaborn | Generates static figures for reports and presentations |
| pytest | Provides focused, readable automated validation |
| venv + pip + requirements.txt | Keeps the environment simple and reproducible |

## Explicit Non-Goals in the Current Repository

To avoid stale expectations, these are not implemented right now:

- No web application, dashboard, or API.
- No live scraping or streaming ingestion.
- No committed generated output artifacts from the real dataset.
- No separate reporting module beyond the figure and CSV helpers in `visualize.py`.

## Source-of-Truth Rule

This document should stay aligned with the real repository.

- `README.md` is the source of truth for setup, status, and workflow summary.
- This file is the source of truth for architecture and validation strategy.
- `data/README.md` is the source of truth for dataset provenance and schema.
- `tests/` define the currently enforced behavior.

If the implementation changes materially, update this document in the same workstream rather than leaving future readers to reconcile stale architecture by hand.