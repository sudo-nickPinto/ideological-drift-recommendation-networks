# ==============================================================================
# TEST MODULE: test_run_pipeline.py
# PURPOSE: Verify that the new orchestration layer can run the whole project
#          pipeline from CSV inputs to generated output files.
# ==============================================================================


import csv
import os
import random

import pytest

import src.run_pipeline as run_pipeline_module
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

    assert summary["mode"] == "baseline"
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


def test_run_pipeline_experiment_mode_writes_tables_and_keeps_baseline_bundle(
    tmp_path,
    monkeypatch,
):
    """
    WHAT: Experiment mode should keep the baseline artifact bundle while also
    writing the repeated-experiment CSV tables.

    WHY: The user wants one entrypoint, one pipeline, and one stronger mode
    that adds rigor without replacing the simpler baseline outputs.
    """
    monkeypatch.setattr(
        run_pipeline_module,
        "EXPERIMENT_STEP_COUNTS",
        [1, 3],
    )
    monkeypatch.setattr(
        run_pipeline_module,
        "EXPERIMENT_WALKS_PER_START",
        2,
    )
    monkeypatch.setattr(
        run_pipeline_module,
        "EXPERIMENT_SEED_COUNT",
        2,
    )

    summary = run_pipeline(
        nodes_path=NODES_CSV,
        edges_path=EDGES_CSV,
        output_dir=tmp_path,
        num_steps=4,
        walks_per_start=1,
        seed=11,
        mode="experiment",
    )

    assert summary["mode"] == "experiment"
    assert summary["baseline_summary"]["mode"] == "baseline"
    assert len(summary["per_run_rows"]) == 12
    assert len(summary["grouped_summary_rows"]) == 6
    assert len(summary["presentation_rows"]) == 6
    assert len(summary["step_trend_summary_rows"]) > 0
    assert summary["experiment_configuration_count"] == 12
    assert summary["num_walks"] == summary["experiment_total_walks"]
    assert summary["experiment_total_walks"] == sum(
        row[run_pipeline_module.TRAJECTORY_COUNT_FIELD]
        for row in summary["per_run_rows"]
    )
    assert summary["metrics"][run_pipeline_module.MEAN_DRIFT_FIELD] != summary[
        "baseline_summary"
    ]["metrics"][run_pipeline_module.MEAN_DRIFT_FIELD]
    assert summary["metrics"][run_pipeline_module.MEAN_EXTREMITY_CHANGE_FIELD] != summary[
        "baseline_summary"
    ]["metrics"][run_pipeline_module.MEAN_EXTREMITY_CHANGE_FIELD]

    expected_files = [
        tmp_path / "figures" / "ideology_distribution.png",
        tmp_path / "figures" / "drift_distribution.png",
        tmp_path / "figures" / "trajectory_sample.png",
        tmp_path / "figures" / "extremity_distribution.png",
        tmp_path / "figures" / "experiment_signed_drift_summary.png",
        tmp_path / "figures" / "experiment_extremity_change_summary.png",
        tmp_path / "figures" / "experiment_stepwise_signed_drift.png",
        tmp_path / "figures" / "experiment_stepwise_extremity_change.png",
        tmp_path / "tables" / "summary_metrics.csv",
        tmp_path / "tables" / "experiment_per_run.csv",
        tmp_path / "tables" / "experiment_grouped_summary.csv",
        tmp_path / "tables" / "experiment_step_trend_summary.csv",
        tmp_path / "tables" / "presentation_headline_metrics.csv",
    ]

    for filepath in expected_files:
        assert filepath.is_file(), f"Expected output file was not created: {filepath}"

    with open(tmp_path / "tables" / "presentation_headline_metrics.csv", newline="") as csvfile:
        reader = csv.reader(csvfile)
        rows = list(reader)

    assert rows[0] == [
        "start group",
        "steps per walk",
        "signed ideological drift",
        "extremity change",
        "how to read signed ideological drift",
        "how to read extremity change",
    ]


def test_run_pipeline_can_print_cli_progress_for_long_runs(
    tmp_path,
    monkeypatch,
    capsys,
):
    """
    WHAT: When progress reporting is enabled, the pipeline should emit the
    baseline and experiment progress labels to the terminal.

    WHY: Long-running experiment mode needs a visible "still working" signal
    so users can tell the simulation is active.
    """
    monkeypatch.setattr(
        run_pipeline_module,
        "EXPERIMENT_STEP_COUNTS",
        [1],
    )
    monkeypatch.setattr(
        run_pipeline_module,
        "EXPERIMENT_WALKS_PER_START",
        1,
    )
    monkeypatch.setattr(
        run_pipeline_module,
        "EXPERIMENT_SEED_COUNT",
        1,
    )

    run_pipeline(
        nodes_path=NODES_CSV,
        edges_path=EDGES_CSV,
        output_dir=tmp_path,
        num_steps=2,
        walks_per_start=1,
        seed=3,
        mode="experiment",
        show_progress=True,
    )

    captured = capsys.readouterr()
    assert "Baseline simulation:" in captured.out
    assert "Experiment simulation:" in captured.out
    assert "Config 1/1" in captured.out
    assert "Config 1/3" in captured.out
    assert "walks/start 1" in captured.out
    assert "completed" in captured.out


def test_experiment_start_selection_can_cap_large_policy_samples(monkeypatch):
    """
    WHAT: The repeated experiment should be able to cap oversized start-node
    pools so the real-data run stays practical.

    WHY: Without a cap, the full experiment matrix grows into millions of
    walks and becomes too slow for an interactive CLI workflow.
    """
    graph = prepare_graph(NODES_CSV, EDGES_CSV)
    valid_start_nodes = choose_start_nodes(graph)

    monkeypatch.setattr(
        run_pipeline_module,
        "EXPERIMENT_MAX_START_NODES_PER_POLICY",
        3,
    )

    all_valid_selected, available_all_valid = run_pipeline_module._select_experiment_start_nodes(
        graph,
        valid_start_nodes,
        "all_valid",
        random.Random(5),
    )
    balanced_selected, _ = run_pipeline_module._select_experiment_start_nodes(
        graph,
        valid_start_nodes,
        "ideology_balanced",
        random.Random(5),
    )

    assert available_all_valid == len(valid_start_nodes)
    assert len(all_valid_selected) == 3
    assert len(balanced_selected) == 3
    assert sorted(
        graph.nodes[node_id]["IDEOLOGY_SCORE"] for node_id in balanced_selected
    ) == [-1.0, 0.0, 1.0]


def test_run_pipeline_deletes_stale_images_but_keeps_existing_csv_tables(tmp_path):
    """
    WHAT: Repeated runs should remove stale image files before writing the new
    figure bundle, but they should not wipe unrelated CSV tables.

    WHY: This matches the safer cleanup rule requested for Play-button runs.
    """
    figures_dir = tmp_path / "figures"
    tables_dir = tmp_path / "tables"
    figures_dir.mkdir(parents=True)
    tables_dir.mkdir(parents=True)

    stale_root_image = tmp_path / "stale_root_image.png"
    stale_figure_image = figures_dir / "stale_figure.png"
    preserved_table = tables_dir / "keep_me.csv"

    stale_root_image.write_text("old image")
    stale_figure_image.write_text("old image")
    preserved_table.write_text("note,keep\n1,yes\n")

    run_pipeline(
        nodes_path=NODES_CSV,
        edges_path=EDGES_CSV,
        output_dir=tmp_path,
        num_steps=2,
        walks_per_start=1,
        seed=5,
    )

    assert not stale_root_image.exists()
    assert not stale_figure_image.exists()
    assert preserved_table.is_file()
    assert (tables_dir / "summary_metrics.csv").is_file()


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
