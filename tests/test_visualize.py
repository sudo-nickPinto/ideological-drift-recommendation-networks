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

import networkx as nx
import pytest

from src.graph_builder import build_graph, load_edges, load_nodes
from src.ideology import SCORE_ATTRIBUTE, assign_ideology_scores
from src.simulator import SCORE_FIELD, STEP_FIELD
from src.visualize import (
	generate_all_figures,
	plot_drift_distribution,
	plot_extremity_distribution,
	plot_ideology_distribution,
	plot_null_model_comparison,
	plot_recommendation_vs_random,
	plot_steps_to_extreme,
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

def test_save_metrics_table_creates_file(tmp_path):
	"""
	WHAT: Call save_metrics_table() with sample rows.
	EXPECT: A CSV file appears at the specified output path.
	"""
	rows = [
		("Simulated user journeys", "3", "Number of random walks"),
		("Average drift", "+0.67", "Users drifted rightward"),
	]
	output_path = str(tmp_path / "summary_metrics.csv")
	save_metrics_table(rows, output_path)
	assert os.path.isfile(output_path), "CSV file was not created."


def test_save_metrics_table_content(tmp_path):
	"""
	WHAT: Write a metrics table, read it back, and verify the values.
	EXPECT: The CSV has a 3-column header (Metric, Value, What It Means)
	        and each data row matches the input.
	WHY: This is the one visualization output where we CAN verify content
	     precisely — it's just text, not pixels.
	"""
	rows = [
		("Simulated user journeys", "3", "Number of random walks"),
		("Average drift", "+0.67", "Users drifted rightward"),
	]
	output_path = str(tmp_path / "summary_metrics.csv")
	save_metrics_table(rows, output_path)

	# Read the CSV back.
	with open(output_path, "r") as csvfile:
		reader = csv.reader(csvfile)
		read_rows = list(reader)

	# Row 0 = header, Rows 1+ = data.
	assert len(read_rows) == 3, "CSV should have 1 header + 2 data rows."

	# Verify header.
	assert read_rows[0] == ["Metric", "Value", "What It Means"]

	# Verify first data row.
	assert read_rows[1][0] == "Simulated user journeys"
	assert read_rows[1][1] == "3"
	assert read_rows[1][2] == "Number of random walks"


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


# ==============================================================================
# TESTS — NEW CHART FUNCTIONS (Enhancement Phase)
# ==============================================================================
#
# These tests verify the three new charts that strengthen the experiment.
# As with the original chart tests, we use SMOKE TESTS: does the function
# run without crashing and produce a PNG file?
#
# ==============================================================================


def test_plot_null_model_comparison_creates_file(tmp_path):
	"""
	WHAT: Call plot_null_model_comparison() with synthetic data.
	EXPECT: A PNG file appears at the specified output path.

	WHY: This chart shows whether the real extremity change is
	     statistically significant compared to shuffled-label trials.
	"""
	output_path = str(tmp_path / "null_model_comparison.png")
	plot_null_model_comparison(
		real_extremity=0.19,
		null_extremities=[0.02, 0.03, 0.01, 0.04, 0.02, 0.05, 0.03, 0.01, 0.04, 0.02],
		p_value=0.02,
		output_path=output_path,
	)
	assert os.path.isfile(output_path), "PNG file was not created."


def test_plot_recommendation_vs_random_creates_file(tmp_path):
	"""
	WHAT: Call plot_recommendation_vs_random() with two summary dicts.
	EXPECT: A PNG file appears at the specified output path.

	WHY: This chart compares recommendation-following to random browsing.
	"""
	from src.metrics import MEAN_ABSOLUTE_DRIFT_FIELD, MEAN_EXTREMITY_CHANGE_FIELD, EXTREME_HIT_RATE_FIELD

	rec_summary = {
		MEAN_ABSOLUTE_DRIFT_FIELD: 0.96,
		MEAN_EXTREMITY_CHANGE_FIELD: 0.19,
		EXTREME_HIT_RATE_FIELD: 0.85,
	}
	random_summary = {
		MEAN_ABSOLUTE_DRIFT_FIELD: 0.45,
		MEAN_EXTREMITY_CHANGE_FIELD: 0.05,
		EXTREME_HIT_RATE_FIELD: 0.40,
	}

	output_path = str(tmp_path / "recommendation_vs_random.png")
	plot_recommendation_vs_random(rec_summary, random_summary, output_path)
	assert os.path.isfile(output_path), "PNG file was not created."


def test_plot_steps_to_extreme_creates_file(tmp_path):
	"""
	WHAT: Call plot_steps_to_extreme() with a list of step counts.
	EXPECT: A PNG file appears at the specified output path.

	WHY: This chart shows how quickly users reach extreme content.
	"""
	output_path = str(tmp_path / "steps_to_extreme.png")
	plot_steps_to_extreme(
		steps_list=[1, 2, 3, 2, 1, 4, 3, 2, 5, 1],
		median_val=2.0,
		pct_reaching=0.85,
		output_path=output_path,
	)
	assert os.path.isfile(output_path), "PNG file was not created."


def test_plot_steps_to_extreme_handles_empty_list(tmp_path):
	"""
	WHAT: Call plot_steps_to_extreme() with an empty list.
	EXPECT: A PNG file is still created (with a "no data" message).

	WHY: Edge case — if no walks reached extreme content, the function
	     should not crash.
	"""
	output_path = str(tmp_path / "steps_empty.png")
	plot_steps_to_extreme(
		steps_list=[],
		median_val=None,
		pct_reaching=0.0,
		output_path=output_path,
	)
	assert os.path.isfile(output_path), "PNG file was not created for empty input."


def test_generate_all_figures_creates_new_files_when_data_provided(
	scored_graph, sample_trajectories, sample_metrics, tmp_path
):
	"""
	WHAT: Call generate_all_figures() with all new optional parameters.
	EXPECT: The three new PNGs appear alongside the original four.

	WHY: This is the integration test for backward-compatible enhancement.
	     The original four figures should still be created, AND the three
	     new figures should also appear when their data is provided.
	"""
	from src.metrics import MEAN_ABSOLUTE_DRIFT_FIELD, MEAN_EXTREMITY_CHANGE_FIELD, EXTREME_HIT_RATE_FIELD

	output_dir = str(tmp_path / "results")

	rec_summary = {
		MEAN_ABSOLUTE_DRIFT_FIELD: 0.96,
		MEAN_EXTREMITY_CHANGE_FIELD: 0.19,
		EXTREME_HIT_RATE_FIELD: 0.85,
	}
	random_summary = {
		MEAN_ABSOLUTE_DRIFT_FIELD: 0.45,
		MEAN_EXTREMITY_CHANGE_FIELD: 0.05,
		EXTREME_HIT_RATE_FIELD: 0.40,
	}

	generate_all_figures(
		scored_graph,
		sample_trajectories,
		sample_metrics,
		output_dir=output_dir,
		null_extremities=[0.02, 0.03, 0.01, 0.04, 0.05],
		null_p_value=0.02,
		real_extremity=0.19,
		rec_summary=rec_summary,
		random_summary=random_summary,
		steps_to_extreme_data={
			"steps_list": [1, 2, 3, 2, 1],
			"median": 2.0,
			"pct_reaching": 0.80,
		},
	)

	# Original figures should still exist.
	for filename in ["ideology_distribution.png", "drift_distribution.png",
					 "trajectory_sample.png", "extremity_distribution.png"]:
		filepath = os.path.join(output_dir, "figures", filename)
		assert os.path.isfile(filepath), f"Missing original figure: {filename}"

	# New figures should also exist.
	for filename in ["null_model_comparison.png", "recommendation_vs_random.png",
					 "steps_to_extreme.png"]:
		filepath = os.path.join(output_dir, "figures", filename)
		assert os.path.isfile(filepath), f"Missing new figure: {filename}"
