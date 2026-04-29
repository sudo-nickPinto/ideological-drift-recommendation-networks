# ==============================================================================
# TEST MODULE: test_run_pipeline.py
# PURPOSE: Verify that the new orchestration layer can run the whole project
#          pipeline from CSV inputs to generated output files.
# ==============================================================================


import os

import pytest

from src.run_pipeline import choose_start_nodes, prepare_graph, run_pipeline


# --- CONSTANTS ----------------------------------------------------------------

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")
NODES_CSV = os.path.join(FIXTURES_DIR, "test_nodes.csv")
EDGES_CSV = os.path.join(FIXTURES_DIR, "test_edges.csv")


def test_prepare_graph_returns_scored_graph():
    """
    WHAT: prepare_graph() should reproduce the existing core pipeline:
    load CSVs -> build graph -> assign ideology scores.

    WHY: This is the central contract of the orchestration layer. If the graph
    is not already scored here, the simulator and metrics stages will work on
    incomplete data.
    """
    graph = prepare_graph(NODES_CSV, EDGES_CSV)

    assert graph.number_of_nodes() == 10
    assert graph.nodes["ch_L1"]["IDEOLOGY_SCORE"] == -1.0


def test_choose_start_nodes_skips_dead_ends_and_missing_scores():
    """
    WHAT: choose_start_nodes() should exclude nodes that cannot contribute to
    meaningful default walks.

    EXPECTATION:
    - ch_island is excluded because it has no outgoing edges
    - ch_no_lr is excluded because its score becomes None
    - ch_L1 is included because it has a score and outgoing edges
    """
    graph = prepare_graph(NODES_CSV, EDGES_CSV)
    start_nodes = choose_start_nodes(graph)

    assert "ch_island" not in start_nodes
    assert "ch_no_lr" not in start_nodes
    assert "ch_L1" in start_nodes


def test_run_pipeline_creates_expected_outputs(tmp_path):
    """
    WHAT: run_pipeline() should generate the same figure/table bundle that the
    visualization layer promises.

    WHY: This is the end-to-end smoke test for the new one-command workflow.
    """
    summary = run_pipeline(
        nodes_path=NODES_CSV,
        edges_path=EDGES_CSV,
        output_dir=tmp_path,
        num_steps=3,
        walks_per_start=1,
        seed=7,
    )

    assert summary["num_start_nodes"] > 0
    assert summary["num_walks"] == summary["num_start_nodes"]

    expected_files = [
        tmp_path / "figures" / "ideology_distribution.png",
        tmp_path / "figures" / "drift_distribution.png",
        tmp_path / "figures" / "trajectory_sample.png",
        tmp_path / "figures" / "extremity_distribution.png",
        tmp_path / "tables" / "summary_metrics.csv",
    ]

    for filepath in expected_files:
        assert filepath.is_file(), f"Expected output file was not created: {filepath}"


def test_run_pipeline_raises_when_no_valid_start_nodes(tmp_path):
    """
    WHAT: If the graph has no valid default start nodes, the orchestration
    layer should fail clearly instead of silently producing empty output.
    """
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