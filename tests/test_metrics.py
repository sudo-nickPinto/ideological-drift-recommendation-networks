# ==============================================================================
# TEST MODULE: test_metrics.py
# PURPOSE: Verify that metrics.py correctly computes drift summaries and
#          structural graph statistics.
# ==============================================================================
#
# WHAT WE ARE TESTING:
#   1. Path-based metrics:
#        - compute_walk_drift()
#        - compute_walk_extremity_change()
#        - summarize_trajectories()
#
#   2. Graph-based metrics:
#        - compute_ideology_assortativity()
#        - compute_average_clustering()
#
#   3. Wrapper function:
#        - compute_all_metrics()
#
# WHY THESE TESTS MATTER:
#   The simulator creates raw trajectories, but research conclusions are based
#   on the summaries computed here. If these formulas are wrong, the project
#   could report ideological drift when there is none, or miss drift that is
#   really present. This module is where raw behavior becomes evidence.
#
# TEST STRATEGY:
#   - Use tiny hand-built trajectories for drift formulas, because we can
#     calculate the correct answers by hand.
#   - Use the synthetic fixture graph for structural metrics, because that
#     graph is stable and already tested by earlier modules.
#   - Compare NetworkX-based results against NetworkX itself when appropriate.
#     This verifies our wrapper logic without forcing us to hand-compute
#     complicated graph statistics.
#
# ==============================================================================


import os
import random

import networkx as nx
import pytest

from src.graph_builder import build_graph, load_edges, load_nodes
from src.ideology import SCORE_ATTRIBUTE, assign_ideology_scores
from src.metrics import (
	ASSORTATIVITY_FIELD,
	CLUSTERING_FIELD,
	CENTER_ENDPOINT_RATE_FIELD,
	CENTER_START_GROUP,
	EXTREME_HIT_RATE_FIELD,
	LEFT_ENDPOINT_RATE_FIELD,
	LEFT_START_GROUP,
	MEAN_CENTER_SHARE_FIELD,
	MEAN_ABSOLUTE_DRIFT_FIELD,
	MEAN_DRIFT_FIELD,
	MEAN_EXTREME_SHARE_FIELD,
	MEAN_EXTREMITY_CHANGE_FIELD,
	MEAN_LEFT_SHARE_FIELD,
	MEAN_RIGHT_SHARE_FIELD,
	NULL_MODEL_P_VALUE_FIELD,
	PCT_REACHING_EXTREME_FIELD,
	RIGHT_ENDPOINT_RATE_FIELD,
	RIGHT_START_GROUP,
	STEPS_TO_EXTREME_FIELD,
	MEDIAN_STEPS_TO_EXTREME_FIELD,
	TRAJECTORY_COUNT_FIELD,
	UNKNOWN_START_GROUP,
	VALID_DRIFT_COUNT_FIELD,
	classify_start_group,
	compute_all_metrics,
	compute_average_clustering,
	compute_ideology_assortativity,
	compute_null_model_p_value,
	compute_steps_to_extreme,
	compute_walk_drift,
	compute_walk_extremity_change,
	compute_walk_hits_extreme,
	compute_walk_score_shares,
	shuffle_ideology_scores,
	summarize_steps_to_extreme,
	summarize_trajectories,
	summarize_trajectories_by_start,
)
from src.simulator import SCORE_FIELD


# --- CONSTANTS ---------------------------------------------------------------

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")
NODES_CSV = os.path.join(FIXTURES_DIR, "test_nodes.csv")
EDGES_CSV = os.path.join(FIXTURES_DIR, "test_edges.csv")


# --- FIXTURES ----------------------------------------------------------------

@pytest.fixture
def scored_graph():
	"""
	Build the same scored graph used by the earlier modules.

	This ensures metrics.py is tested against the real pipeline objects,
	not a separate invented graph format.
	"""
	nodes_df = load_nodes(NODES_CSV)
	edges_df = load_edges(EDGES_CSV)
	G = build_graph(nodes_df, edges_df)
	assign_ideology_scores(G)
	return G


# ==============================================================================
# TESTS — compute_walk_drift()
# ==============================================================================


def test_compute_walk_drift_for_left_to_right_path():
	"""
	WHAT: A path from -1.0 to +1.0 has drift +2.0.

	WHY: This is the clearest possible hand-checkable drift example.
	"""
	trajectory = [
		{SCORE_FIELD: -1.0},
		{SCORE_FIELD: 0.0},
		{SCORE_FIELD: 1.0},
	]

	drift = compute_walk_drift(trajectory)
	assert drift == 2.0, f"Expected drift 2.0, got {drift}."


def test_compute_walk_drift_returns_none_when_endpoint_score_missing():
	"""
	WHAT: If either endpoint score is missing, the drift result should be None.

	WHY: Missing data must stay visible. Silent substitution would create
		 fake certainty.
	"""
	trajectory = [
		{SCORE_FIELD: -1.0},
		{SCORE_FIELD: None},
	]

	assert compute_walk_drift(trajectory) is None


def test_compute_walk_drift_raises_for_empty_trajectory():
	"""An empty trajectory is invalid input and should raise ValueError."""
	with pytest.raises(ValueError, match="trajectory"):
		compute_walk_drift([])


# ==============================================================================
# TESTS — compute_walk_extremity_change()
# ==============================================================================


def test_compute_walk_extremity_change_from_center_to_extreme():
	"""
	WHAT: A path from 0.0 to +1.0 increases extremity by +1.0.

	WHY: This tests the absolute-value logic directly.
	"""
	trajectory = [
		{SCORE_FIELD: 0.0},
		{SCORE_FIELD: 1.0},
	]

	change = compute_walk_extremity_change(trajectory)
	assert change == 1.0, f"Expected extremity change 1.0, got {change}."


def test_compute_walk_extremity_change_is_zero_for_left_to_right_flip():
	"""
	WHAT: A path from -1.0 to +1.0 changes direction but not extremity.

	WHY: Both endpoints are equally far from the center.
	"""
	trajectory = [
		{SCORE_FIELD: -1.0},
		{SCORE_FIELD: 1.0},
	]

	change = compute_walk_extremity_change(trajectory)
	assert change == 0.0, f"Expected extremity change 0.0, got {change}."


def test_compute_walk_score_shares_returns_expected_fractions():
	"""
	WHAT: A trajectory with one Left, one Center, and two Right steps should
	      produce the corresponding time-share fractions.

	WHY: This verifies the new occupancy-style metrics that track where the
	     user spends time, not just where they start and end.
	"""
	trajectory = [
		{SCORE_FIELD: -1.0},
		{SCORE_FIELD: 0.0},
		{SCORE_FIELD: 1.0},
		{SCORE_FIELD: 1.0},
	]

	shares = compute_walk_score_shares(trajectory)

	assert shares[MEAN_LEFT_SHARE_FIELD] == pytest.approx(0.25)
	assert shares[MEAN_CENTER_SHARE_FIELD] == pytest.approx(0.25)
	assert shares[MEAN_RIGHT_SHARE_FIELD] == pytest.approx(0.5)
	assert shares[MEAN_EXTREME_SHARE_FIELD] == pytest.approx(0.75)


def test_compute_walk_hits_extreme_detects_extreme_visit():
	"""
	WHAT: Any walk that reaches -1.0 or +1.0 should be marked as hitting an
	      extreme state.
	"""
	trajectory = [
		{SCORE_FIELD: 0.0},
		{SCORE_FIELD: 1.0},
	]

	assert compute_walk_hits_extreme(trajectory) is True


def test_compute_walk_hits_extreme_returns_false_when_no_extreme_reached():
	"""
	WHAT: A walk that stays entirely at the center should not count as having
	      visited an extreme.
	"""
	trajectory = [
		{SCORE_FIELD: 0.0},
		{SCORE_FIELD: 0.0},
	]

	assert compute_walk_hits_extreme(trajectory) is False


# ==============================================================================
# TESTS — summarize_trajectories()
# ==============================================================================


def test_summarize_trajectories_computes_expected_means():
	"""
	WHAT: Summary means should match hand-computed values.

	TEST DATA:
		Walk 1: -1.0 -> +1.0   drift = +2.0, extremity change =  0.0
		Walk 2:  0.0 ->  0.0   drift =  0.0, extremity change =  0.0
		Walk 3: +1.0 ->  0.0   drift = -1.0, extremity change = -1.0

		Mean drift            = (2 + 0 - 1) / 3 = 1/3
		Mean absolute drift   = (2 + 0 + 1) / 3 = 1
		Mean extremity change = (0 + 0 - 1) / 3 = -1/3
	"""
	trajectories = [
		[{SCORE_FIELD: -1.0}, {SCORE_FIELD: 1.0}],
		[{SCORE_FIELD: 0.0}, {SCORE_FIELD: 0.0}],
		[{SCORE_FIELD: 1.0}, {SCORE_FIELD: 0.0}],
	]

	summary = summarize_trajectories(trajectories)

	assert summary[TRAJECTORY_COUNT_FIELD] == 3
	assert summary[VALID_DRIFT_COUNT_FIELD] == 3
	assert summary[MEAN_DRIFT_FIELD] == pytest.approx(1 / 3)
	assert summary[MEAN_ABSOLUTE_DRIFT_FIELD] == pytest.approx(1.0)
	assert summary[MEAN_EXTREMITY_CHANGE_FIELD] == pytest.approx(-1 / 3)
	assert summary[MEAN_LEFT_SHARE_FIELD] == pytest.approx(1 / 6)
	assert summary[MEAN_CENTER_SHARE_FIELD] == pytest.approx(1 / 2)
	assert summary[MEAN_RIGHT_SHARE_FIELD] == pytest.approx(1 / 3)
	assert summary[MEAN_EXTREME_SHARE_FIELD] == pytest.approx(1 / 2)
	assert summary[EXTREME_HIT_RATE_FIELD] == pytest.approx(2 / 3)
	assert summary[LEFT_ENDPOINT_RATE_FIELD] == pytest.approx(0.0)
	assert summary[CENTER_ENDPOINT_RATE_FIELD] == pytest.approx(2 / 3)
	assert summary[RIGHT_ENDPOINT_RATE_FIELD] == pytest.approx(1 / 3)


def test_summarize_trajectories_handles_missing_scores():
	"""
	WHAT: Walks with unusable endpoint scores should not count as valid drifts.
	"""
	trajectories = [
		[{SCORE_FIELD: -1.0}, {SCORE_FIELD: 1.0}],
		[{SCORE_FIELD: None}, {SCORE_FIELD: 1.0}],
	]

	summary = summarize_trajectories(trajectories)

	assert summary[TRAJECTORY_COUNT_FIELD] == 2
	assert summary[VALID_DRIFT_COUNT_FIELD] == 1
	assert summary[MEAN_DRIFT_FIELD] == 2.0


def test_classify_start_group_uses_initial_score():
	"""
	WHAT: The grouping helper should classify trajectories by their first
	      recorded ideology score.
	"""
	assert classify_start_group([{SCORE_FIELD: -1.0}, {SCORE_FIELD: 0.0}]) == LEFT_START_GROUP
	assert classify_start_group([{SCORE_FIELD: 0.0}, {SCORE_FIELD: 1.0}]) == CENTER_START_GROUP
	assert classify_start_group([{SCORE_FIELD: 1.0}, {SCORE_FIELD: 0.0}]) == RIGHT_START_GROUP
	assert classify_start_group([{SCORE_FIELD: None}, {SCORE_FIELD: 0.0}]) == UNKNOWN_START_GROUP


def test_summarize_trajectories_by_start_splits_walks_into_groups():
	"""
	WHAT: Group summaries should preserve how many trajectories came from each
	      starting ideology bucket.

	WHY: This is the first safeguard against pooled averages hiding asymmetry.
	"""
	trajectories = [
		[{SCORE_FIELD: -1.0}, {SCORE_FIELD: 1.0}],
		[{SCORE_FIELD: 0.0}, {SCORE_FIELD: 1.0}],
		[{SCORE_FIELD: 1.0}, {SCORE_FIELD: 0.0}],
		[{SCORE_FIELD: None}, {SCORE_FIELD: 0.0}],
	]

	grouped = summarize_trajectories_by_start(trajectories)

	assert grouped[LEFT_START_GROUP][TRAJECTORY_COUNT_FIELD] == 1
	assert grouped[CENTER_START_GROUP][TRAJECTORY_COUNT_FIELD] == 1
	assert grouped[RIGHT_START_GROUP][TRAJECTORY_COUNT_FIELD] == 1
	assert grouped[UNKNOWN_START_GROUP][TRAJECTORY_COUNT_FIELD] == 1
	assert grouped[LEFT_START_GROUP][MEAN_DRIFT_FIELD] == pytest.approx(2.0)
	assert grouped[CENTER_START_GROUP][MEAN_DRIFT_FIELD] == pytest.approx(1.0)
	assert grouped[RIGHT_START_GROUP][MEAN_DRIFT_FIELD] == pytest.approx(-1.0)


# ==============================================================================
# TESTS — graph structure metrics
# ==============================================================================


def test_compute_ideology_assortativity_matches_networkx(scored_graph):
	"""
	WHAT: Our wrapper should match the direct NetworkX calculation when the
		  graph already has valid ideology scores everywhere.
	"""
	expected = nx.numeric_assortativity_coefficient(scored_graph, SCORE_ATTRIBUTE)
	actual = compute_ideology_assortativity(scored_graph)

	assert actual == pytest.approx(expected)


def test_compute_ideology_assortativity_returns_none_when_no_edges():
	"""
	WHAT: A graph with nodes but no edges has no relationship structure,
		  so assortativity should be None.
	"""
	G = nx.DiGraph()
	G.add_node("A", **{SCORE_ATTRIBUTE: -1.0})
	G.add_node("B", **{SCORE_ATTRIBUTE: 1.0})

	assert compute_ideology_assortativity(G) is None


def test_compute_average_clustering_matches_networkx_undirected_version(scored_graph):
	"""
	WHAT: Our clustering wrapper should match NetworkX average clustering on
		  the undirected version of the graph.
	"""
	expected = nx.average_clustering(scored_graph.to_undirected())
	actual = compute_average_clustering(scored_graph)

	assert actual == pytest.approx(expected)


def test_compute_average_clustering_returns_none_for_empty_graph():
	"""An empty graph should return None instead of crashing."""
	G = nx.DiGraph()
	assert compute_average_clustering(G) is None


# ==============================================================================
# TESTS — compute_all_metrics()
# ==============================================================================


def test_compute_all_metrics_returns_combined_summary(scored_graph):
	"""
	WHAT: compute_all_metrics() should merge path and graph metrics into one
		  dictionary.
	"""
	trajectories = [
		[{SCORE_FIELD: -1.0}, {SCORE_FIELD: 0.0}],
		[{SCORE_FIELD: 0.0}, {SCORE_FIELD: 1.0}],
	]

	summary = compute_all_metrics(scored_graph, trajectories)

	assert TRAJECTORY_COUNT_FIELD in summary
	assert VALID_DRIFT_COUNT_FIELD in summary
	assert MEAN_DRIFT_FIELD in summary
	assert MEAN_ABSOLUTE_DRIFT_FIELD in summary
	assert MEAN_EXTREMITY_CHANGE_FIELD in summary
	assert ASSORTATIVITY_FIELD in summary
	assert CLUSTERING_FIELD in summary

	assert summary[TRAJECTORY_COUNT_FIELD] == 2
	assert summary[VALID_DRIFT_COUNT_FIELD] == 2


# ==============================================================================
# TESTS — compute_steps_to_extreme()
# ==============================================================================
#
# This metric answers: "How many clicks does it take for a walker to first
# reach extreme content?" Extreme means |ideology_score| >= threshold (1.0).
#
# ==============================================================================


def test_compute_steps_to_extreme_finds_first_extreme():
	"""
	WHAT: A trajectory that reaches extreme at step 2 should return 2.

	HAND CALCULATION:
		Step 0: score = 0.0 → |0.0| = 0.0 < 1.0 → not extreme
		Step 1: score = 0.0 → |0.0| = 0.0 < 1.0 → not extreme
		Step 2: score = 1.0 → |1.0| = 1.0 >= 1.0 → EXTREME → return 2
		Step 3: score = 0.0 → never checked — we already returned

	WHY FIRST OCCURRENCE?
		We care about the minimum exposure time — the fastest path from
		moderate content to extreme content.
	"""
	trajectory = [
		{"step": 0, SCORE_FIELD: 0.0},
		{"step": 1, SCORE_FIELD: 0.0},
		{"step": 2, SCORE_FIELD: 1.0},
		{"step": 3, SCORE_FIELD: 0.0},
	]

	result = compute_steps_to_extreme(trajectory)
	assert result == 2, f"Expected 2, got {result}."


def test_compute_steps_to_extreme_returns_none_when_no_extreme():
	"""
	WHAT: A trajectory that never reaches extreme should return None.

	WHY: None signals "never happened" — it is different from 0
	     (which would mean "started at extreme"). We must distinguish
	     these two cases so that summaries only count walks that
	     actually reached extreme content.
	"""
	trajectory = [
		{"step": 0, SCORE_FIELD: 0.0},
		{"step": 1, SCORE_FIELD: 0.0},
		{"step": 2, SCORE_FIELD: 0.0},
	]

	result = compute_steps_to_extreme(trajectory)
	assert result is None, f"Expected None, got {result}."


def test_compute_steps_to_extreme_returns_zero_when_starting_extreme():
	"""
	WHAT: A trajectory starting at score = 1.0 should return step 0.

	WHY: If a user starts at extreme content, the distance to extreme
	     is zero clicks.
	"""
	trajectory = [
		{"step": 0, SCORE_FIELD: 1.0},
		{"step": 1, SCORE_FIELD: 0.0},
	]

	result = compute_steps_to_extreme(trajectory)
	assert result == 0, f"Expected 0, got {result}."


def test_compute_steps_to_extreme_detects_negative_extreme():
	"""
	WHAT: A trajectory reaching -1.0 (Left extreme) should also count.

	WHY: Extreme means the absolute value meets the threshold. Both
	     Left (-1.0) and Right (+1.0) are extreme.
	"""
	trajectory = [
		{"step": 0, SCORE_FIELD: 0.0},
		{"step": 1, SCORE_FIELD: -1.0},
	]

	result = compute_steps_to_extreme(trajectory)
	assert result == 1, f"Expected 1, got {result}."


def test_compute_steps_to_extreme_raises_for_empty():
	"""
	WHAT: An empty trajectory should raise ValueError.

	WHY: An empty trajectory has no data to analyze. This catches
	     caller bugs early.
	"""
	with pytest.raises(ValueError, match="trajectory"):
		compute_steps_to_extreme([])


# ==============================================================================
# TESTS — summarize_steps_to_extreme()
# ==============================================================================


def test_summarize_steps_to_extreme_computes_correct_stats():
	"""
	WHAT: Given 4 trajectories with known steps-to-extreme values,
	      verify that the summary statistics are correct.

	HAND CALCULATION:
		Walk 1: extreme at step 2
		Walk 2: extreme at step 4
		Walk 3: never reaches extreme → excluded from mean/median
		Walk 4: extreme at step 0 (started at extreme)

		Values that reached extreme: [2, 4, 0]
		Mean   = (2 + 4 + 0) / 3 = 2.0
		Median = 2.0 (middle value when sorted: [0, 2, 4])
		Pct reaching = 3 / 4 = 0.75

	WHY TEST THIS?
		These three numbers are the core of the "speed of radicalization"
		story. If the summary is wrong, the presentation gives wrong numbers.
	"""
	trajectories = [
		# Walk 1: reaches extreme at step 2
		[{"step": 0, SCORE_FIELD: 0.0}, {"step": 1, SCORE_FIELD: 0.0},
		 {"step": 2, SCORE_FIELD: 1.0}, {"step": 3, SCORE_FIELD: 0.0}],
		# Walk 2: reaches extreme at step 4
		[{"step": 0, SCORE_FIELD: 0.0}, {"step": 1, SCORE_FIELD: 0.0},
		 {"step": 2, SCORE_FIELD: 0.0}, {"step": 3, SCORE_FIELD: 0.0},
		 {"step": 4, SCORE_FIELD: -1.0}],
		# Walk 3: never reaches extreme
		[{"step": 0, SCORE_FIELD: 0.0}, {"step": 1, SCORE_FIELD: 0.0}],
		# Walk 4: starts at extreme
		[{"step": 0, SCORE_FIELD: 1.0}, {"step": 1, SCORE_FIELD: 0.0}],
	]

	summary = summarize_steps_to_extreme(trajectories)

	assert summary[STEPS_TO_EXTREME_FIELD] == pytest.approx(2.0)
	assert summary[MEDIAN_STEPS_TO_EXTREME_FIELD] == pytest.approx(2.0)
	assert summary[PCT_REACHING_EXTREME_FIELD] == pytest.approx(0.75)


# ==============================================================================
# TESTS — shuffle_ideology_scores()
# ==============================================================================


def test_shuffle_ideology_scores_preserves_graph_structure(scored_graph):
	"""
	WHAT: After shuffling, the graph should have the same nodes and edges.

	WHY: Shuffling is supposed to change ONLY the ideology labels —
	     the network structure (who recommends whom) must remain
	     identical. Otherwise, the comparison is not "same structure,
	     different labels" and the null model is invalid.
	"""
	rng = random.Random(42)
	shuffled = shuffle_ideology_scores(scored_graph, rng)

	# Same set of nodes.
	assert set(shuffled.nodes()) == set(scored_graph.nodes())

	# Same set of edges.
	assert set(shuffled.edges()) == set(scored_graph.edges())


def test_shuffle_ideology_scores_does_not_modify_original(scored_graph):
	"""
	WHAT: The original graph's scores should be unchanged after shuffling.

	WHY: If shuffle modified the original in place, the main experiment's
	     data would be corrupted and all subsequent analysis would be wrong.
	"""
	# Record the original scores.
	original_scores = {
		node: scored_graph.nodes[node].get(SCORE_ATTRIBUTE)
		for node in scored_graph.nodes()
	}

	rng = random.Random(42)
	shuffle_ideology_scores(scored_graph, rng)

	# Verify original is unchanged.
	for node in scored_graph.nodes():
		assert scored_graph.nodes[node].get(SCORE_ATTRIBUTE) == original_scores[node], (
			f"Original graph was modified for node {node}!"
		)


def test_shuffle_ideology_scores_permutes_scores(scored_graph):
	"""
	WHAT: The shuffled scores should be a permutation of the original scores
	      (same values, different assignment).

	WHY: We are redistributing existing labels, not creating new ones.
	     The total count of Left/Center/Right/None should stay the same.
	"""
	rng = random.Random(42)
	shuffled = shuffle_ideology_scores(scored_graph, rng)

	original_scores = sorted([
		scored_graph.nodes[n].get(SCORE_ATTRIBUTE)
		for n in scored_graph.nodes()
	], key=lambda x: (x is None, x))
	shuffled_scores = sorted([
		shuffled.nodes[n].get(SCORE_ATTRIBUTE)
		for n in shuffled.nodes()
	], key=lambda x: (x is None, x))

	assert original_scores == shuffled_scores, (
		"Shuffled scores should be a permutation of the originals."
	)


# ==============================================================================
# TESTS — compute_null_model_p_value()
# ==============================================================================


def test_compute_null_model_p_value_correct():
	"""
	WHAT: Given real = 5.0 and null = [1, 2, 3, 4, 6, 7],
	      two null values (6 and 7) are >= 5.0.
	      p-value = 2 / 6 ≈ 0.3333.

	WHY: This is a simple hand-checkable case. p ≈ 0.33 means the real
	     result is NOT unusual — a third of the random trials produced
	     comparable values.
	"""
	p = compute_null_model_p_value(5.0, [1, 2, 3, 4, 6, 7])
	assert p == pytest.approx(2 / 6), f"Expected 2/6, got {p}."


def test_compute_null_model_p_value_returns_zero_when_real_is_best():
	"""
	WHAT: If no null value reaches the real value, p-value = 0.

	WHY: p = 0 means the real result is more extreme than EVERY random
	     trial — very strong evidence that the result is real.
	"""
	p = compute_null_model_p_value(10.0, [1, 2, 3])
	assert p == 0.0, f"Expected 0.0, got {p}."


def test_compute_null_model_p_value_returns_one_for_empty_null():
	"""
	WHAT: With no null data, we cannot reject the null hypothesis.
	      p-value defaults to 1.0 (no evidence).

	WHY: 1.0 is the safest default — it means "we don't know."
	"""
	p = compute_null_model_p_value(5.0, [])
	assert p == 1.0, f"Expected 1.0, got {p}."
