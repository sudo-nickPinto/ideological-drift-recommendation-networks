# ==============================================================================
# TEST MODULE: test_visualize.py
# PURPOSE: Verify that visualize.py correctly generates all output figures
#          and the summary metrics table.
# ==============================================================================
#
# WHAT WE ARE TESTING:
#   1. plot_ideology_distribution()  — bar chart of L/C/R counts
#   2. plot_drift_distribution()     — histogram of per-walk drift
#   3. plot_trajectory_sample()      — line plot of sample trajectories
#   4. plot_extremity_distribution() — histogram of extremity change
#   5. save_metrics_table()          — CSV summary table
#   6. generate_all_figures()        — wrapper that calls all of the above
#
# TEST STRATEGY:
#   Visualization functions are inherently hard to unit test. You cannot
#   easily assert that a bar chart "looks correct" without comparing pixel
#   data (fragile and platform-dependent).
#
#   Instead, we test:
#     - SMOKE TESTS: does the function run without crashing?
#     - FILE CREATION: does a PNG or CSV file appear at the expected path?
#     - CONTENT TESTS (for the CSV): do the written values match the input?
#     - EDGE CASES: empty trajectories, max_lines capping
#
#   All file outputs use pytest's tmp_path fixture, which creates a unique
#   temporary directory for each test. This avoids polluting the real
#   results/ folder and ensures tests don't interfere with each other.
#
# MATPLOTLIB BACKEND NOTE:
#   visualize.py sets matplotlib.use("Agg") at import time. The Agg backend
#   renders to files without needing a display. This is why these tests work
#   in headless environments (CI servers, SSH sessions, etc.).
#
# ==============================================================================


import csv
import os

import matplotlib.pyplot as plt
import networkx as nx
import pytest

from src.graph_builder import build_graph, load_edges, load_nodes
from src.ideology import SCORE_ATTRIBUTE, assign_ideology_scores
from src.simulator import SCORE_FIELD, STEP_FIELD
from src.visualize import (
	generate_all_figures,
	plot_drift_distribution,
	plot_experiment_step_trend_summary,
	plot_extremity_distribution,
	plot_ideology_distribution,
	plot_trajectory_sample,
	save_metrics_table,
)
from src.metrics import (
	TRAJECTORY_COUNT_FIELD,
	VALID_DRIFT_COUNT_FIELD,
	MEAN_DRIFT_FIELD,
	MEAN_ABSOLUTE_DRIFT_FIELD,
	MEAN_EXTREMITY_CHANGE_FIELD,
	ASSORTATIVITY_FIELD,
	CLUSTERING_FIELD,
)


# --- FIXTURES -----------------------------------------------------------------

# Locate the synthetic test data CSVs relative to this test file.
# os.path.dirname(__file__) gives the directory containing this .py file,
# which is tests/. From there, fixtures/ is one level down.
FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")
NODES_CSV = os.path.join(FIXTURES_DIR, "test_nodes.csv")
EDGES_CSV = os.path.join(FIXTURES_DIR, "test_edges.csv")


@pytest.fixture
def scored_graph():
	"""
	Build the small synthetic graph and attach ideology scores.

	This graph has 8 nodes (2 Left, 2 Center, 2 Right, 1 isolated, 1 no-LR)
	and a known set of directed edges. It is the same fixture used across
	all test modules in this project.
	"""
	nodes_df = load_nodes(NODES_CSV)
	edges_df = load_edges(EDGES_CSV)
	G = build_graph(nodes_df, edges_df)
	G = assign_ideology_scores(G)
	return G


@pytest.fixture
def sample_trajectories():
	"""
	Hand-built trajectories that mimic the output of simulate_walk().

	These trajectories have KNOWN drift and extremity-change values so
	we can verify that the plotting functions handle them correctly.

	Trajectory A: starts at L (−1.0), ends at R (+1.0)
		drift = +1.0 − (−1.0) = +2.0
		extremity change = |+1.0| − |−1.0| = 0.0

	Trajectory B: starts at C (0.0), ends at R (+1.0)
		drift = +1.0 − 0.0 = +1.0
		extremity change = |+1.0| − |0.0| = +1.0

	Trajectory C: starts at R (+1.0), ends at C (0.0)
		drift = 0.0 − 1.0 = −1.0
		extremity change = |0.0| − |+1.0| = −1.0
	"""
	trajectory_a = [
		{STEP_FIELD: 0, "node_id": "ch_L1", SCORE_FIELD: -1.0},
		{STEP_FIELD: 1, "node_id": "ch_C1", SCORE_FIELD: 0.0},
		{STEP_FIELD: 2, "node_id": "ch_R1", SCORE_FIELD: 1.0},
	]
	trajectory_b = [
		{STEP_FIELD: 0, "node_id": "ch_C1", SCORE_FIELD: 0.0},
		{STEP_FIELD: 1, "node_id": "ch_R1", SCORE_FIELD: 1.0},
	]
	trajectory_c = [
		{STEP_FIELD: 0, "node_id": "ch_R1", SCORE_FIELD: 1.0},
		{STEP_FIELD: 1, "node_id": "ch_C1", SCORE_FIELD: 0.0},
	]
	return [trajectory_a, trajectory_b, trajectory_c]


@pytest.fixture
def sample_metrics():
	"""
	A metrics dictionary matching the structure returned by
	compute_all_metrics(). Uses realistic-looking values.
	"""
	return {
		TRAJECTORY_COUNT_FIELD: 3,
		VALID_DRIFT_COUNT_FIELD: 3,
		MEAN_DRIFT_FIELD: 0.6667,
		MEAN_ABSOLUTE_DRIFT_FIELD: 1.3333,
		MEAN_EXTREMITY_CHANGE_FIELD: 0.0,
		ASSORTATIVITY_FIELD: 0.45,
		CLUSTERING_FIELD: 0.12,
	}


# --- TESTS: plot_ideology_distribution() -------------------------------------

def test_plot_ideology_distribution_creates_file(scored_graph, tmp_path):
	"""
	WHAT: Call plot_ideology_distribution() on the synthetic scored graph.
	EXPECT: A PNG file appears at the specified output path.
	WHY: If the file exists, the function ran to completion without crashing
	     and matplotlib successfully rendered and saved the figure.
	"""
	output_path = str(tmp_path / "ideology_distribution.png")
	plot_ideology_distribution(scored_graph, output_path)
	assert os.path.isfile(output_path), "PNG file was not created."


# --- TESTS: plot_drift_distribution() ----------------------------------------

def test_plot_drift_distribution_creates_file(sample_trajectories, tmp_path):
	"""
	WHAT: Call plot_drift_distribution() with hand-built trajectories.
	EXPECT: A PNG file appears at the specified output path.
	WHY: Verifies that the function computes drifts, draws the histogram,
	     and saves without error.
	"""
	output_path = str(tmp_path / "drift_distribution.png")
	plot_drift_distribution(sample_trajectories, output_path)
	assert os.path.isfile(output_path), "PNG file was not created."


def test_plot_drift_distribution_empty_trajectories(tmp_path):
	"""
	WHAT: Call plot_drift_distribution() with an empty list.
	EXPECT: The function still creates a PNG (with a "no data" message).
	WHY: The function should handle the edge case of no valid drifts
	     gracefully instead of crashing.
	"""
	output_path = str(tmp_path / "drift_empty.png")
	plot_drift_distribution([], output_path)
	assert os.path.isfile(output_path), "PNG file was not created for empty input."


def test_plot_experiment_step_trend_summary_creates_file(tmp_path):
	"""
	WHAT: Call plot_experiment_step_trend_summary() with small hand-built rows.
	EXPECT: A PNG file appears at the specified output path.
	WHY: This verifies the new repeated-experiment trend figure can render its
		mean lines plus uncertainty bands without crashing.
	"""
	summary_rows = [
		{
			"start_policy": "all_valid",
			"start_policy_label": "Current valid starts",
			"step_count": 5,
			"step_index": 0,
			"runs_aggregated": 2,
			"mean_valid_observation_count": 10,
			"signed_drift_mean": 0.0,
			"signed_drift_std": 0.0,
			"extremity_change_mean": 0.0,
			"extremity_change_std": 0.0,
		},
		{
			"start_policy": "all_valid",
			"start_policy_label": "Current valid starts",
			"step_count": 5,
			"step_index": 1,
			"runs_aggregated": 2,
			"mean_valid_observation_count": 10,
			"signed_drift_mean": -0.1,
			"signed_drift_std": 0.02,
			"extremity_change_mean": 0.05,
			"extremity_change_std": 0.01,
		},
		{
			"start_policy": "center_only",
			"start_policy_label": "Center-only starts",
			"step_count": 5,
			"step_index": 0,
			"runs_aggregated": 2,
			"mean_valid_observation_count": 8,
			"signed_drift_mean": 0.0,
			"signed_drift_std": 0.0,
			"extremity_change_mean": 0.0,
			"extremity_change_std": 0.0,
		},
		{
			"start_policy": "center_only",
			"start_policy_label": "Center-only starts",
			"step_count": 5,
			"step_index": 1,
			"runs_aggregated": 2,
			"mean_valid_observation_count": 8,
			"signed_drift_mean": -0.05,
			"signed_drift_std": 0.01,
			"extremity_change_mean": 0.15,
			"extremity_change_std": 0.02,
		},
	]

	output_path = str(tmp_path / "experiment_step_trend.png")
	plot_experiment_step_trend_summary(
		summary_rows,
		output_path,
		metric_field="signed_drift_mean",
		std_field="signed_drift_std",
		title="Step-by-Step Mean Signed Drift Across Repeated Simulations",
		y_label="Mean signed drift from start",
	)
	assert os.path.isfile(output_path), "PNG file was not created."


# --- TESTS: plot_trajectory_sample() ------------------------------------------

def test_plot_trajectory_sample_creates_file(sample_trajectories, tmp_path):
	"""
	WHAT: Call plot_trajectory_sample() with the sample trajectories.
	EXPECT: A PNG file appears at the specified output path.
	"""
	output_path = str(tmp_path / "trajectory_sample.png")
	plot_trajectory_sample(sample_trajectories, output_path)
	assert os.path.isfile(output_path), "PNG file was not created."


def test_plot_trajectory_sample_limits_lines(tmp_path):
	"""
	WHAT: Create 50 trajectories but set max_lines=5.
	EXPECT: The function runs successfully and produces a file.
	WHY: This verifies that the sampling logic does not crash and
	     correctly limits the number of lines plotted.
	"""
	# Build 50 identical single-step trajectories.
	many_trajectories = [
		[{STEP_FIELD: 0, "node_id": f"ch_{i}", SCORE_FIELD: 0.0}]
		for i in range(50)
	]
	output_path = str(tmp_path / "trajectory_limited.png")
	plot_trajectory_sample(many_trajectories, output_path, max_lines=5)
	assert os.path.isfile(output_path), "PNG file was not created."


def test_plot_trajectory_sample_default_uses_three_walks_and_two_legends(tmp_path, monkeypatch):
	"""
	WHAT: Call plot_trajectory_sample() without overriding max_lines.
	EXPECT: The default figure title reflects 3 sampled walks and the chart
		contains separate legends for the walk labels and ideology reference lines.
	WHY: The presentation version of this figure should stay visually simple
		and clearly labeled by default.
	"""
	many_trajectories = [
		[
			{STEP_FIELD: 0, "node_id": f"start_{index}", SCORE_FIELD: -1.0},
			{STEP_FIELD: 1, "node_id": f"mid_{index}", SCORE_FIELD: 0.0},
			{STEP_FIELD: 2, "node_id": f"end_{index}", SCORE_FIELD: 1.0},
		]
		for index in range(12)
	]

	captured = {}
	original_close = plt.close

	def fake_savefig(self, *args, **kwargs):
		captured["figure"] = self

	def fake_close(fig=None):
		return None

	monkeypatch.setattr("matplotlib.figure.Figure.savefig", fake_savefig)
	monkeypatch.setattr(plt, "close", fake_close)

	try:
		plot_trajectory_sample(many_trajectories, str(tmp_path / "ignored.png"))
		fig = captured["figure"]
		ax = fig.axes[0]

		assert ax.get_title() == "Sample of 3 Walk Trajectories"
		assert len(ax.get_lines()) == 6
		assert len(ax.artists) == 1
		assert ax.artists[0].get_title().get_text() == "Walk Key"
		assert ax.get_legend() is not None
		assert ax.get_legend().get_title().get_text() == "Ideology Key"
	finally:
		original_close("all")


# --- TESTS: plot_extremity_distribution() ------------------------------------

def test_plot_extremity_distribution_creates_file(sample_trajectories, tmp_path):
	"""
	WHAT: Call plot_extremity_distribution() with hand-built trajectories.
	EXPECT: A PNG file appears at the specified output path.
	"""
	output_path = str(tmp_path / "extremity_distribution.png")
	plot_extremity_distribution(sample_trajectories, output_path)
	assert os.path.isfile(output_path), "PNG file was not created."


# --- TESTS: save_metrics_table() ---------------------------------------------

def test_save_metrics_table_creates_file(sample_metrics, tmp_path):
	"""
	WHAT: Call save_metrics_table() with a sample metrics dictionary.
	EXPECT: A CSV file appears at the specified output path.
	"""
	output_path = str(tmp_path / "summary_metrics.csv")
	save_metrics_table(sample_metrics, output_path)
	assert os.path.isfile(output_path), "CSV file was not created."


def test_save_metrics_table_content(sample_metrics, tmp_path):
	"""
	WHAT: Write a metrics table, read it back, and verify the values.
	EXPECT: The CSV header matches the expected column names and the
	        data row contains the correct values.
	WHY: This is the one visualization output where we CAN verify content
	     precisely — it's just text, not pixels.
	"""
	output_path = str(tmp_path / "summary_metrics.csv")
	save_metrics_table(sample_metrics, output_path)

	# Read the CSV back.
	with open(output_path, "r") as csvfile:
		reader = csv.reader(csvfile)
		rows = list(reader)

	# Row 0 = header, Row 1 = data.
	assert len(rows) == 2, "CSV should have exactly 2 rows (header + data)."

	header = rows[0]
	data = rows[1]

	# Verify header matches expected column order.
	expected_header = [
		TRAJECTORY_COUNT_FIELD,
		VALID_DRIFT_COUNT_FIELD,
		MEAN_DRIFT_FIELD,
		MEAN_ABSOLUTE_DRIFT_FIELD,
		MEAN_EXTREMITY_CHANGE_FIELD,
		ASSORTATIVITY_FIELD,
		CLUSTERING_FIELD,
	]
	assert header == expected_header, f"Header mismatch: {header}"

	# Verify data values.
	# CSV stores everything as strings, so we compare string representations.
	assert data[0] == str(sample_metrics[TRAJECTORY_COUNT_FIELD])
	assert data[1] == str(sample_metrics[VALID_DRIFT_COUNT_FIELD])
	assert data[2] == str(sample_metrics[MEAN_DRIFT_FIELD])


# --- TESTS: generate_all_figures() -------------------------------------------

def test_generate_all_figures_creates_all_files(
	scored_graph, sample_trajectories, sample_metrics, tmp_path
):
	"""
	WHAT: Call generate_all_figures() and verify every expected output exists.
	EXPECT: Four PNGs in figures/ and one CSV in tables/.
	WHY: This is the integration smoke test. If this passes, the full
	     visualization pipeline works end-to-end.
	"""
	output_dir = str(tmp_path / "results")
	generate_all_figures(
		scored_graph,
		sample_trajectories,
		sample_metrics,
		output_dir=output_dir,
	)

	# Check that all expected files were created.
	expected_figures = [
		"ideology_distribution.png",
		"drift_distribution.png",
		"trajectory_sample.png",
		"extremity_distribution.png",
	]
	for filename in expected_figures:
		filepath = os.path.join(output_dir, "figures", filename)
		assert os.path.isfile(filepath), f"Missing figure: {filename}"

	# Check the metrics table.
	table_path = os.path.join(output_dir, "tables", "summary_metrics.csv")
	assert os.path.isfile(table_path), "Missing metrics table CSV."
