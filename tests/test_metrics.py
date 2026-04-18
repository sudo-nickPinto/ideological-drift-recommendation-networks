# ==============================================================================
# TEST MODULE: test_metrics.py
# PURPOSE: Verify that metrics.py correctly computes walk-level and graph-level
#          metrics for ideological drift analysis.
# ==============================================================================
#
# WHAT WE ARE TESTING:
#   1. Per-walk metrics
#      - compute_walk_drift()
#      - compute_walk_extremity_change()
#
#   2. Cross-walk summary metrics
#      - compute_mean_drift()
#      - compute_mean_absolute_drift()
#      - compute_mean_extremity_change()
#
#   3. Graph-level structural metrics
#      - compute_ideology_assortativity()
#      - compute_average_clustering()
#
#   4. Full summary packaging
#      - compute_all_metrics()
#
# WHY THESE TESTS MATTER:
#   metrics.py is where the project stops being "just graph traversal" and
#   starts producing interpretable research results. If the formulas are wrong,
#   the entire written analysis will be wrong even if graph_builder.py and
#   simulator.py are perfect. So this test file pins down the math carefully.
#
# TESTING STRATEGY:
#   - Use hand-built trajectories when we want exact, human-checkable math.
#   - Use small manual graphs when we want a graph property with an obvious
#     expected answer (for example, a triangle should have clustering = 1.0).
#   - Use the shared synthetic CSV fixture graph for one integration-style test
#     of compute_all_metrics() because that mimics the real pipeline.
#
# ==============================================================================


import os

import networkx as nx
import pytest

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
	compute_average_clustering,
	compute_ideology_assortativity,
	compute_mean_absolute_drift,
	compute_mean_drift,
	compute_mean_extremity_change,
	compute_walk_drift,
	compute_walk_extremity_change,
)
from src.simulator import SCORE_FIELD, STEP_FIELD


# --- CONSTANTS ----------------------------------------------------------------

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")
NODES_CSV = os.path.join(FIXTURES_DIR, "test_nodes.csv")
EDGES_CSV = os.path.join(FIXTURES_DIR, "test_edges.csv")


# --- FIXTURES -----------------------------------------------------------------

@pytest.fixture
def scored_graph():
	"""
	Build the synthetic fixture graph and attach ideology scores.

	This reproduces the real pipeline up to the metrics stage:
		load CSVs → build graph → assign ideology scores
	"""
	nodes_df = load_nodes(NODES_CSV)
	edges_df = load_edges(EDGES_CSV)
	G = build_graph(nodes_df, edges_df)
	assign_ideology_scores(G)
	return G


@pytest.fixture
def sample_trajectories():
	"""
	Three hand-built trajectories with easy-to-check expected values.

	Trajectory A: Left → Center → Right
		drift = 1.0 - (-1.0) = 2.0
		extremity change = |1.0| - |-1.0| = 0.0

	Trajectory B: Center → Right
		drift = 1.0 - 0.0 = 1.0
		extremity change = |1.0| - |0.0| = 1.0

	Trajectory C: Right → Center
		drift = 0.0 - 1.0 = -1.0
		extremity change = |0.0| - |1.0| = -1.0
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


# ==============================================================================
# TESTS — Per-walk metrics
# ==============================================================================


def test_compute_walk_drift_returns_final_minus_initial(sample_trajectories):
	"""
	WHAT: Verify the basic drift formula on a known trajectory.

	WHY: This is the most important math in the project. If drift is wrong,
	the main research conclusion will be wrong.
	"""
	drift = compute_walk_drift(sample_trajectories[0])
	assert drift == 2.0, f"Expected drift 2.0, got {drift}."


def test_compute_walk_extremity_change_uses_absolute_values(sample_trajectories):
	"""
	WHAT: Verify that extremity change measures distance from center,
	not simple left-right direction.
	"""
	change = compute_walk_extremity_change(sample_trajectories[1])
	assert change == 1.0, f"Expected extremity change 1.0, got {change}."


def test_compute_walk_drift_returns_none_for_empty_trajectory():
	"""
	WHAT: An empty trajectory has no start and no end, so drift is undefined.

	WHY: Returning None is safer than inventing a fake numeric answer.
	"""
	assert compute_walk_drift([]) is None


def test_compute_walk_extremity_change_returns_none_when_score_missing():
	"""
	WHAT: If either endpoint score is missing, extremity change is undefined.
	"""
	trajectory = [
		{STEP_FIELD: 0, "node_id": "start", SCORE_FIELD: None},
		{STEP_FIELD: 1, "node_id": "end", SCORE_FIELD: 1.0},
	]
	assert compute_walk_extremity_change(trajectory) is None


# ==============================================================================
# TESTS — Multi-walk summaries
# ==============================================================================


def test_compute_mean_drift_matches_hand_calculation(sample_trajectories):
	"""
	The sample drifts are [2.0, 1.0, -1.0].
	Mean = (2 + 1 - 1) / 3 = 2/3.
	"""
	result = compute_mean_drift(sample_trajectories)
	assert result == pytest.approx(2.0 / 3.0)


def test_compute_mean_absolute_drift_ignores_direction(sample_trajectories):
	"""
	Absolute drifts are [2.0, 1.0, 1.0].
	Mean absolute drift = 4/3.
	"""
	result = compute_mean_absolute_drift(sample_trajectories)
	assert result == pytest.approx(4.0 / 3.0)


def test_compute_mean_extremity_change_matches_hand_calculation(sample_trajectories):
	"""
	Extremity changes are [0.0, 1.0, -1.0].
	Mean = 0.0.
	"""
	result = compute_mean_extremity_change(sample_trajectories)
	assert result == pytest.approx(0.0)


def test_summary_functions_return_none_when_no_valid_values():
	"""
	WHAT: If every trajectory is invalid, the mean should be None.

	WHY: That tells the caller the metric was undefined, rather than zero.
	"""
	invalid_trajectories = [
		[{STEP_FIELD: 0, "node_id": "x", SCORE_FIELD: None}],
		[],
	]

	assert compute_mean_drift(invalid_trajectories) is None
	assert compute_mean_absolute_drift(invalid_trajectories) is None
	assert compute_mean_extremity_change(invalid_trajectories) is None


# ==============================================================================
# TESTS — Graph-level metrics
# ==============================================================================


def test_compute_average_clustering_is_one_for_triangle():
	"""
	WHAT: A 3-node triangle has perfect clustering.

	WHY: Every node's two neighbors are connected to each other, so the
	local clustering coefficient for every node is 1.0, making the average 1.0.
	"""
	G = nx.DiGraph()
	G.add_edges_from(
		[
			("A", "B"),
			("B", "A"),
			("A", "C"),
			("C", "A"),
			("B", "C"),
			("C", "B"),
		]
	)

	result = compute_average_clustering(G)
	assert result == pytest.approx(1.0)


def test_compute_average_clustering_returns_none_for_empty_graph():
	"""
	WHAT: The empty graph has no nodes, so average clustering is undefined.
	"""
	G = nx.DiGraph()
	assert compute_average_clustering(G) is None


def test_compute_ideology_assortativity_is_high_for_within_group_edges():
	"""
	WHAT: Build a graph where Left connects only to Left and Right only to Right.

	EXPECTATION: Assortativity should be very close to +1.0 because the graph
	is perfectly like-to-like.
	"""
	G = nx.DiGraph()
	G.add_node("L1", **{SCORE_ATTRIBUTE: -1.0})
	G.add_node("L2", **{SCORE_ATTRIBUTE: -1.0})
	G.add_node("R1", **{SCORE_ATTRIBUTE: 1.0})
	G.add_node("R2", **{SCORE_ATTRIBUTE: 1.0})
	G.add_edges_from(
		[
			("L1", "L2"),
			("L2", "L1"),
			("R1", "R2"),
			("R2", "R1"),
		]
	)

	result = compute_ideology_assortativity(G)
	assert result == pytest.approx(1.0)


def test_compute_ideology_assortativity_returns_none_when_no_valid_edges():
	"""
	WHAT: If no edge connects two nodes with known ideology scores, the metric
	should be undefined.
	"""
	G = nx.DiGraph()
	G.add_node("unknown_a", **{SCORE_ATTRIBUTE: None})
	G.add_node("unknown_b", **{SCORE_ATTRIBUTE: None})
	G.add_edge("unknown_a", "unknown_b")

	assert compute_ideology_assortativity(G) is None


# ==============================================================================
# TESTS — Full summary dictionary
# ==============================================================================


def test_compute_all_metrics_returns_expected_fields(scored_graph, sample_trajectories):
	"""
	WHAT: compute_all_metrics() should package all summary values under the
	agreed field names used by visualize.py.
	"""
	metrics_dict = compute_all_metrics(scored_graph, sample_trajectories)

	expected_keys = {
		TRAJECTORY_COUNT_FIELD,
		VALID_DRIFT_COUNT_FIELD,
		MEAN_DRIFT_FIELD,
		MEAN_ABSOLUTE_DRIFT_FIELD,
		MEAN_EXTREMITY_CHANGE_FIELD,
		ASSORTATIVITY_FIELD,
		CLUSTERING_FIELD,
	}

	assert set(metrics_dict.keys()) == expected_keys


def test_compute_all_metrics_matches_known_walk_summary(scored_graph, sample_trajectories):
	"""
	WHAT: Verify the trajectory-based values in the summary dictionary.

	WHY: This is the contract visualize.py depends on when it writes the CSV.
	"""
	metrics_dict = compute_all_metrics(scored_graph, sample_trajectories)

	assert metrics_dict[TRAJECTORY_COUNT_FIELD] == 3
	assert metrics_dict[VALID_DRIFT_COUNT_FIELD] == 3
	assert metrics_dict[MEAN_DRIFT_FIELD] == pytest.approx(2.0 / 3.0)
	assert metrics_dict[MEAN_ABSOLUTE_DRIFT_FIELD] == pytest.approx(4.0 / 3.0)
	assert metrics_dict[MEAN_EXTREMITY_CHANGE_FIELD] == pytest.approx(0.0)


def test_compute_all_metrics_includes_graph_metrics(scored_graph, sample_trajectories):
	"""
	WHAT: The summary dictionary should include finite graph-level metrics
	for the synthetic scored graph.
	"""
	metrics_dict = compute_all_metrics(scored_graph, sample_trajectories)

	assert metrics_dict[ASSORTATIVITY_FIELD] is not None
	assert metrics_dict[CLUSTERING_FIELD] is not None
