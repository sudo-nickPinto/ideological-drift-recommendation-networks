import csv
import os

import pytest

from src.run_pipeline import choose_start_nodes, prepare_graph, run_pipeline


FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")
NODES_CSV = os.path.join(FIXTURES_DIR, "test_nodes.csv")
EDGES_CSV = os.path.join(FIXTURES_DIR, "test_edges.csv")


def test_prepare_graph_returns_scored_graph():
    graph = prepare_graph(NODES_CSV, EDGES_CSV)
    assert graph.number_of_nodes() == 10
    assert graph.nodes["ch_L1"]["IDEOLOGY_SCORE"] == -1.0


def test_choose_start_nodes_skips_dead_ends_and_missing_scores():
    graph = prepare_graph(NODES_CSV, EDGES_CSV)
    start_nodes = choose_start_nodes(graph)

    assert "ch_island" not in start_nodes
    assert "ch_no_lr" not in start_nodes
    assert "ch_L1" in start_nodes


def test_run_pipeline_creates_expected_outputs(tmp_path):
    summary = run_pipeline(
        nodes_path=NODES_CSV,
        edges_path=EDGES_CSV,
        output_dir=tmp_path,
        num_steps=3,
        walks_per_start=1,
        seed=7,
        repeat_count=2,
    )

    assert summary["num_start_nodes"] > 0
    assert summary["repeat_count"] == 2
    assert summary["num_walks"] == summary["num_start_nodes"] * 2
    assert len(summary["per_run_rows"]) == 2

    expected_files = [
        tmp_path / "figures" / "ideology_distribution.png",
        tmp_path / "figures" / "drift_distribution.png",
        tmp_path / "figures" / "trajectory_sample.png",
        tmp_path / "figures" / "extremity_distribution.png",
        tmp_path / "tables" / "summary_metrics.csv",
        tmp_path / "tables" / "repeated_runs_summary.csv",
    ]

    for filepath in expected_files:
        assert filepath.is_file(), f"Expected output file was not created: {filepath}"


def test_run_pipeline_writes_repeated_runs_summary_with_aggregate_row(tmp_path):
    run_pipeline(
        nodes_path=NODES_CSV,
        edges_path=EDGES_CSV,
        output_dir=tmp_path,
        num_steps=2,
        walks_per_start=1,
        seed=11,
        repeat_count=3,
    )

    repeated_summary_path = tmp_path / "tables" / "repeated_runs_summary.csv"
    with repeated_summary_path.open("r", newline="") as csvfile:
        rows = list(csv.DictReader(csvfile))

    assert len(rows) == 4
    assert [row["row_type"] for row in rows[:-1]] == ["run", "run", "run"]
    assert rows[-1]["row_type"] == "aggregate"


def test_run_pipeline_raises_when_no_valid_start_nodes(tmp_path):
    empty_nodes_path = tmp_path / "nodes.csv"
    empty_edges_path = tmp_path / "edges.csv"

    empty_nodes_path.write_text(
        "CHANNEL_ID,CHANNEL_TITLE,LR\n"
        "dead_end,Dead End,C\n"
        "unknown,Unknown,\n"
    )
    empty_edges_path.write_text("FROM_CHANNEL_ID,TO_CHANNEL_ID,RELEVANT_IMPRESSIONS_DAILY\n")

    with pytest.raises(ValueError, match="No valid start nodes"):
        run_pipeline(
            nodes_path=empty_nodes_path,
            edges_path=empty_edges_path,
            output_dir=tmp_path / "out",
        )


def test_run_pipeline_rejects_repeat_count_below_one(tmp_path):
    with pytest.raises(ValueError, match="repeat_count"):
        run_pipeline(
            nodes_path=NODES_CSV,
            edges_path=EDGES_CSV,
            output_dir=tmp_path,
            repeat_count=0,
        )
