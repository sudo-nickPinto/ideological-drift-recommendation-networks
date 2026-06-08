from __future__ import annotations

import argparse
import csv
import random
import sys
from pathlib import Path

if __package__ in {None, ""}:
    PROJECT_ROOT_FOR_IMPORTS = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(PROJECT_ROOT_FOR_IMPORTS))

from src.graph_builder import build_graph, load_edges, load_nodes
from src.ideology import SCORE_ATTRIBUTE, assign_ideology_scores
from src.metrics import (
    ASSORTATIVITY_FIELD,
    CLUSTERING_FIELD,
    MEAN_ABSOLUTE_DRIFT_FIELD,
    MEAN_DRIFT_FIELD,
    MEAN_EXTREMITY_CHANGE_FIELD,
    TRAJECTORY_COUNT_FIELD,
    VALID_DRIFT_COUNT_FIELD,
    compute_all_metrics,
    compute_graph_metrics,
)
from src.simulator import simulate_walks
from src.visualize import generate_all_figures


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_NODES_PATH = PROJECT_ROOT / "data" / "vis_channel_stats.csv"
DEFAULT_EDGES_PATH = PROJECT_ROOT / "data" / "vis_channel_recs2.csv"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "results"

DEFAULT_NUM_STEPS = 10
DEFAULT_WALKS_PER_START = 1
DEFAULT_RANDOM_SEED = 42
DEFAULT_REPEAT_COUNT = 5

REPEATED_RUNS_SUMMARY_FILENAME = "repeated_runs_summary.csv"
REPEATED_RUNS_FIELDNAMES = [
    "row_type",
    "repeat_index",
    "seed",
    TRAJECTORY_COUNT_FIELD,
    VALID_DRIFT_COUNT_FIELD,
    MEAN_DRIFT_FIELD,
    MEAN_ABSOLUTE_DRIFT_FIELD,
    MEAN_EXTREMITY_CHANGE_FIELD,
    ASSORTATIVITY_FIELD,
    CLUSTERING_FIELD,
]


def prepare_graph(nodes_path, edges_path):
    nodes_df = load_nodes(nodes_path)
    edges_df = load_edges(edges_path)
    graph = build_graph(nodes_df, edges_df)
    assign_ideology_scores(graph)
    return graph


def choose_start_nodes(G, score_attr=SCORE_ATTRIBUTE):
    start_nodes = []
    for node_id, attrs in G.nodes(data=True):
        has_score = attrs.get(score_attr) is not None
        has_outgoing_edge = G.out_degree(node_id) > 0
        if has_score and has_outgoing_edge:
            start_nodes.append(node_id)
    return start_nodes


def _aggregate_repeated_metrics(per_run_rows):
    total_trajectories = sum(row[TRAJECTORY_COUNT_FIELD] for row in per_run_rows)
    total_valid_drifts = sum(row[VALID_DRIFT_COUNT_FIELD] for row in per_run_rows)

    weighted_mean_drift = None
    weighted_mean_absolute_drift = None
    weighted_mean_extremity_change = None

    if total_valid_drifts:
        weighted_mean_drift = (
            sum(
                row[MEAN_DRIFT_FIELD] * row[VALID_DRIFT_COUNT_FIELD]
                for row in per_run_rows
                if row[MEAN_DRIFT_FIELD] is not None
            )
            / total_valid_drifts
        )
        weighted_mean_absolute_drift = (
            sum(
                row[MEAN_ABSOLUTE_DRIFT_FIELD] * row[VALID_DRIFT_COUNT_FIELD]
                for row in per_run_rows
                if row[MEAN_ABSOLUTE_DRIFT_FIELD] is not None
            )
            / total_valid_drifts
        )

    if total_trajectories:
        weighted_mean_extremity_change = (
            sum(
                row[MEAN_EXTREMITY_CHANGE_FIELD] * row[TRAJECTORY_COUNT_FIELD]
                for row in per_run_rows
                if row[MEAN_EXTREMITY_CHANGE_FIELD] is not None
            )
            / total_trajectories
        )

    first_row = per_run_rows[0] if per_run_rows else {}

    return {
        TRAJECTORY_COUNT_FIELD: total_trajectories,
        VALID_DRIFT_COUNT_FIELD: total_valid_drifts,
        MEAN_DRIFT_FIELD: weighted_mean_drift,
        MEAN_ABSOLUTE_DRIFT_FIELD: weighted_mean_absolute_drift,
        MEAN_EXTREMITY_CHANGE_FIELD: weighted_mean_extremity_change,
        ASSORTATIVITY_FIELD: first_row.get(ASSORTATIVITY_FIELD),
        CLUSTERING_FIELD: first_row.get(CLUSTERING_FIELD),
    }


def _write_repeated_runs_summary(per_run_rows, aggregate_metrics, tables_dir):
    output_path = tables_dir / REPEATED_RUNS_SUMMARY_FILENAME
    with output_path.open("w", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=REPEATED_RUNS_FIELDNAMES)
        writer.writeheader()

        for row in per_run_rows:
            writer.writerow({
                "row_type": "run",
                "repeat_index": row["repeat_index"],
                "seed": row["seed"],
                TRAJECTORY_COUNT_FIELD: row[TRAJECTORY_COUNT_FIELD],
                VALID_DRIFT_COUNT_FIELD: row[VALID_DRIFT_COUNT_FIELD],
                MEAN_DRIFT_FIELD: row[MEAN_DRIFT_FIELD],
                MEAN_ABSOLUTE_DRIFT_FIELD: row[MEAN_ABSOLUTE_DRIFT_FIELD],
                MEAN_EXTREMITY_CHANGE_FIELD: row[MEAN_EXTREMITY_CHANGE_FIELD],
                ASSORTATIVITY_FIELD: row[ASSORTATIVITY_FIELD],
                CLUSTERING_FIELD: row[CLUSTERING_FIELD],
            })

        writer.writerow({
            "row_type": "aggregate",
            "repeat_index": "",
            "seed": "",
            TRAJECTORY_COUNT_FIELD: aggregate_metrics[TRAJECTORY_COUNT_FIELD],
            VALID_DRIFT_COUNT_FIELD: aggregate_metrics[VALID_DRIFT_COUNT_FIELD],
            MEAN_DRIFT_FIELD: aggregate_metrics[MEAN_DRIFT_FIELD],
            MEAN_ABSOLUTE_DRIFT_FIELD: aggregate_metrics[MEAN_ABSOLUTE_DRIFT_FIELD],
            MEAN_EXTREMITY_CHANGE_FIELD: aggregate_metrics[MEAN_EXTREMITY_CHANGE_FIELD],
            ASSORTATIVITY_FIELD: aggregate_metrics[ASSORTATIVITY_FIELD],
            CLUSTERING_FIELD: aggregate_metrics[CLUSTERING_FIELD],
        })

    return output_path


def run_pipeline(
    nodes_path=DEFAULT_NODES_PATH,
    edges_path=DEFAULT_EDGES_PATH,
    output_dir=DEFAULT_OUTPUT_DIR,
    num_steps=DEFAULT_NUM_STEPS,
    walks_per_start=DEFAULT_WALKS_PER_START,
    seed=DEFAULT_RANDOM_SEED,
    repeat_count=DEFAULT_REPEAT_COUNT,
    show_progress=None,
):
    if repeat_count < 1:
        raise ValueError("repeat_count must be at least 1.")

    graph = prepare_graph(nodes_path, edges_path)
    start_nodes = choose_start_nodes(graph)

    if not start_nodes:
        raise ValueError(
            "No valid start nodes were found. "
            "The graph needs scored nodes with outgoing edges."
        )

    graph_metrics = compute_graph_metrics(graph)

    all_trajectories = []
    per_run_rows = []

    for repeat_index in range(repeat_count):
        run_seed = seed + repeat_index
        rng = random.Random(run_seed)
        trajectories = simulate_walks(
            graph,
            start_nodes=start_nodes,
            num_steps=num_steps,
            walks_per_start=walks_per_start,
            rng=rng,
        )
        all_trajectories.extend(trajectories)

        run_metrics = compute_all_metrics(
            graph,
            trajectories,
            graph_metrics=graph_metrics,
        )
        per_run_rows.append(
            {
                "repeat_index": repeat_index + 1,
                "seed": run_seed,
                TRAJECTORY_COUNT_FIELD: run_metrics[TRAJECTORY_COUNT_FIELD],
                VALID_DRIFT_COUNT_FIELD: run_metrics[VALID_DRIFT_COUNT_FIELD],
                MEAN_DRIFT_FIELD: run_metrics[MEAN_DRIFT_FIELD],
                MEAN_ABSOLUTE_DRIFT_FIELD: run_metrics[MEAN_ABSOLUTE_DRIFT_FIELD],
                MEAN_EXTREMITY_CHANGE_FIELD: run_metrics[MEAN_EXTREMITY_CHANGE_FIELD],
                ASSORTATIVITY_FIELD: run_metrics[ASSORTATIVITY_FIELD],
                CLUSTERING_FIELD: run_metrics[CLUSTERING_FIELD],
            }
        )

        if show_progress:
            print(
                f"Completed repeat {repeat_index + 1}/{repeat_count} "
                f"(seed={run_seed})"
            )

    aggregate_metrics = _aggregate_repeated_metrics(per_run_rows)

    generate_all_figures(
        graph,
        all_trajectories,
        aggregate_metrics,
        output_dir=str(output_dir),
    )

    output_dir_path = Path(output_dir)
    tables_dir = output_dir_path / "tables"
    tables_dir.mkdir(parents=True, exist_ok=True)
    repeated_runs_summary_path = _write_repeated_runs_summary(
        per_run_rows,
        aggregate_metrics,
        tables_dir,
    )

    return {
        "graph": graph,
        "trajectories": all_trajectories,
        "metrics": aggregate_metrics,
        "num_start_nodes": len(start_nodes),
        "num_walks": len(all_trajectories),
        "repeat_count": repeat_count,
        "output_dir": output_dir_path,
        "per_run_rows": per_run_rows,
        "repeated_runs_summary_path": repeated_runs_summary_path,
    }


def build_argument_parser():
    parser = argparse.ArgumentParser(
        description=(
            "Run the ideological-drift pipeline from CSV inputs to output "
            "figures and summary tables."
        )
    )

    parser.add_argument(
        "--nodes-path",
        default=str(DEFAULT_NODES_PATH),
        help="Path to the node CSV (default: %(default)s)",
    )
    parser.add_argument(
        "--edges-path",
        default=str(DEFAULT_EDGES_PATH),
        help="Path to the edge CSV (default: %(default)s)",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Directory where figures and summary tables are written (default: %(default)s)",
    )
    parser.add_argument(
        "--num-steps",
        type=int,
        default=DEFAULT_NUM_STEPS,
        help="Maximum number of recommendation moves after the starting node (default: %(default)s)",
    )
    parser.add_argument(
        "--walks-per-start",
        type=int,
        default=DEFAULT_WALKS_PER_START,
        help="How many walks to run from each valid starting node (default: %(default)s)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=DEFAULT_RANDOM_SEED,
        help="Base random seed; repeat k uses seed + k for reproducible repeated runs (default: %(default)s)",
    )
    parser.add_argument(
        "--repeat-count",
        type=int,
        default=DEFAULT_REPEAT_COUNT,
        help="How many repeated runs to execute using seed offsets (default: %(default)s)",
    )

    return parser


def main(argv=None):
    parser = build_argument_parser()
    args = parser.parse_args(argv)

    try:
        summary = run_pipeline(
            nodes_path=args.nodes_path,
            edges_path=args.edges_path,
            output_dir=args.output_dir,
            num_steps=args.num_steps,
            walks_per_start=args.walks_per_start,
            seed=args.seed,
            repeat_count=args.repeat_count,
            show_progress=True,
        )
    except (FileNotFoundError, ValueError) as exc:
        print(f"Pipeline failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    metrics_dict = summary["metrics"]
    print("Pipeline completed successfully.")
    print(f"Start nodes used: {summary['num_start_nodes']}")
    print(f"Total walks generated: {summary['num_walks']}")
    print(f"Repeated runs: {summary['repeat_count']}")
    print(f"Output directory: {summary['output_dir']}")
    print(f"Mean drift: {metrics_dict[MEAN_DRIFT_FIELD]}")
    print(f"Mean extremity change: {metrics_dict[MEAN_EXTREMITY_CHANGE_FIELD]}")
    print(f"Ideology assortativity: {metrics_dict[ASSORTATIVITY_FIELD]}")
    print(f"Average clustering: {metrics_dict[CLUSTERING_FIELD]}")
    print(f"Repeated-runs summary table: {summary['repeated_runs_summary_path']}")


if __name__ == "__main__":
    main()
