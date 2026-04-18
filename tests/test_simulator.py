# ==============================================================================
# TEST MODULE: test_simulator.py
# PURPOSE: Verify that simulator.py correctly performs weighted random walks
#          through the scored recommendation graph.
# ==============================================================================
#
# WHAT WE ARE TESTING:
#   1. choose_next_node() correctly handles:
#        - deterministic cases (only one outgoing edge)
#        - dead ends (no outgoing edges)
#        - invalid start nodes
#        - zero-weight fallback behavior
#   2. simulate_walk() correctly:
#        - includes the start node as step 0
#        - records node IDs and ideology scores
#        - stops early at dead ends
#        - validates bad input
#   3. simulate_walks() correctly:
#        - runs multiple trajectories
#        - returns the right number of walks
#        - validates bad input
#
# TESTING PHILOSOPHY:
#   Random code is harder to test than deterministic code because the result
#   can vary from run to run. We solve that in two ways:
#
#   1. Use graph situations where the answer is forced.
#      Example: if a node has exactly one outgoing edge, the simulator has
#      no real choice to make — it must choose that edge.
#
#   2. Pass a random.Random object with a fixed seed.
#      A seed is the starting state of the random generator.
#      Same seed + same code + same inputs = same sequence of "random" choices.
#      That makes stochastic behavior reproducible for tests.
#
# ==============================================================================


import os
import random

import pytest
import networkx as nx

from src.graph_builder import build_graph, load_edges, load_nodes
from src.ideology import SCORE_ATTRIBUTE, assign_ideology_scores
from src.simulator import (
	DEFAULT_WEIGHT_ATTRIBUTE,
	NODE_FIELD,
	SCORE_FIELD,
	STEP_FIELD,
	choose_next_node,
	simulate_walk,
	simulate_walks,
	simulate_walk_uniform,
	simulate_walks_uniform,
)


# --- CONSTANTS ---------------------------------------------------------------

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")
NODES_CSV = os.path.join(FIXTURES_DIR, "test_nodes.csv")
EDGES_CSV = os.path.join(FIXTURES_DIR, "test_edges.csv")


# --- FIXTURES ----------------------------------------------------------------

@pytest.fixture
def scored_graph():
	"""
	Build the synthetic test graph and attach ideology scores.

	This reproduces the real pipeline so far:
		load CSVs → build graph → assign ideology scores
	"""
	nodes_df = load_nodes(NODES_CSV)
	edges_df = load_edges(EDGES_CSV)
	G = build_graph(nodes_df, edges_df)
	assign_ideology_scores(G)
	return G


# ==============================================================================
# TESTS — choose_next_node()
# ==============================================================================


def test_choose_next_node_returns_none_at_dead_end(scored_graph):
	"""
	WHAT: ch_island has no outgoing edges, so choose_next_node() returns None.

	WHY: The simulator must stop cleanly at dead ends instead of crashing.
	"""
	result = choose_next_node(scored_graph, "ch_island", rng=random.Random(1))
	assert result is None, (
		"Expected None for dead-end node ch_island, but simulator tried "
		f"to move to {result!r}."
	)


def test_choose_next_node_returns_only_outgoing_neighbor_when_forced(scored_graph):
	"""
	WHAT: ch_C3 has exactly one outgoing edge: ch_C3 → ch_L3.

	WHY: This gives us a deterministic test of the selection logic.
		 Weighted randomness is irrelevant when only one option exists.
	"""
	result = choose_next_node(scored_graph, "ch_C3", rng=random.Random(1))
	assert result == "ch_L3", (
		f"Expected ch_C3 to move to its only neighbor ch_L3, got {result}."
	)


def test_choose_next_node_raises_for_unknown_node(scored_graph):
	"""
	WHAT: Passing a node ID that is not in the graph should raise ValueError.

	WHY: A typo in a node ID is a caller bug. Silent failure would make
		 debugging much harder.
	"""
	with pytest.raises(ValueError, match="not in the graph"):
		choose_next_node(scored_graph, "not_a_real_node")


def test_choose_next_node_falls_back_to_uniform_when_all_weights_zero():
	"""
	WHAT: If all outgoing weights are zero, the function should still choose
		  among the neighbors uniformly rather than getting stuck.

	WHY: The graph structure says movement is possible. Zero or missing
		 weights should not freeze the walk.
	"""
	G = nx.DiGraph()
	G.add_edge("A", "B", RELEVANT_IMPRESSIONS_DAILY=0.0)
	G.add_edge("A", "C", RELEVANT_IMPRESSIONS_DAILY=0.0)

	rng = random.Random(7)
	result = choose_next_node(G, "A", rng=rng)

	assert result in {"B", "C"}, (
		f"Expected uniform fallback to choose 'B' or 'C', got {result!r}."
	)


# ==============================================================================
# TESTS — simulate_walk()
# ==============================================================================


def test_simulate_walk_includes_start_node_as_step_zero(scored_graph):
	"""
	WHAT: Even a zero-step walk should return the starting node as step 0.

	WHY: The starting position is analytically important. Drift is measured
		 relative to where the user started.
	"""
	trajectory = simulate_walk(scored_graph, "ch_L1", num_steps=0, rng=random.Random(1))

	assert len(trajectory) == 1, f"Expected exactly 1 record, got {len(trajectory)}."
	assert trajectory[0][STEP_FIELD] == 0
	assert trajectory[0][NODE_FIELD] == "ch_L1"
	assert trajectory[0][SCORE_FIELD] == -1.0


def test_simulate_walk_stops_early_at_dead_end(scored_graph):
	"""
	WHAT: Starting from ch_C3 with num_steps=5 should produce only 2 records:
		  ch_C3 at step 0, then ch_L3 at step 1, then stop because ch_L3
		  has no outgoing edges.

	WHY: This verifies early stopping instead of fabricating fake extra steps.
	"""
	trajectory = simulate_walk(scored_graph, "ch_C3", num_steps=5, rng=random.Random(1))

	expected_nodes = ["ch_C3", "ch_L3"]
	actual_nodes = [record[NODE_FIELD] for record in trajectory]

	assert actual_nodes == expected_nodes, (
		f"Expected path {expected_nodes}, got {actual_nodes}."
	)
	assert len(trajectory) == 2, (
		f"Expected walk to stop at dead end with 2 records, got {len(trajectory)}."
	)


def test_simulate_walk_records_scores_for_each_step(scored_graph):
	"""
	WHAT: The trajectory should store ideology scores alongside node IDs.

	WHY: metrics.py should not have to re-look-up every score from the graph
		 later if the trajectory already knows them.
	"""
	trajectory = simulate_walk(scored_graph, "ch_C3", num_steps=2, rng=random.Random(1))
	actual_scores = [record[SCORE_FIELD] for record in trajectory]

	assert actual_scores == [0.0, -1.0], (
		f"Expected scores [0.0, -1.0], got {actual_scores}."
	)


def test_simulate_walk_raises_for_unknown_start_node(scored_graph):
	"""An invalid start node should raise ValueError."""
	with pytest.raises(ValueError, match="not in the graph"):
		simulate_walk(scored_graph, "ghost_node", num_steps=3)


def test_simulate_walk_raises_for_negative_steps(scored_graph):
	"""Negative walk length is invalid and should raise ValueError."""
	with pytest.raises(ValueError, match="num_steps"):
		simulate_walk(scored_graph, "ch_L1", num_steps=-1)


def test_simulate_walk_uses_requested_weight_attribute():
	"""
	WHAT: The caller should be able to override which edge attribute counts
		  as the weight.

	WHY: This keeps the simulator flexible for future experiments.
	"""
	G = nx.DiGraph()
	G.add_node("A", **{SCORE_ATTRIBUTE: 0.0})
	G.add_node("B", **{SCORE_ATTRIBUTE: 1.0})
	G.add_node("C", **{SCORE_ATTRIBUTE: -1.0})
	G.add_edge("A", "B", custom_weight=1.0)
	G.add_edge("A", "C", custom_weight=0.0)

	trajectory = simulate_walk(
		G,
		"A",
		num_steps=1,
		rng=random.Random(1),
		weight_attr="custom_weight",
	)

	assert trajectory[1][NODE_FIELD] == "B", (
		"Expected custom_weight to force the walk from A to B."
	)


# ==============================================================================
# TESTS — simulate_walks()
# ==============================================================================


def test_simulate_walks_returns_requested_number_of_trajectories(scored_graph):
	"""
	WHAT: Two start nodes with 2 walks each should return 4 trajectories.

	WHY: This verifies the outer loop logic that repeats walks across starts.
	"""
	trajectories = simulate_walks(
		scored_graph,
		start_nodes=["ch_C3", "ch_island"],
		num_steps=2,
		walks_per_start=2,
		rng=random.Random(1),
	)

	assert len(trajectories) == 4, (
		f"Expected 4 trajectories, got {len(trajectories)}."
	)


def test_simulate_walks_returns_trajectory_lists(scored_graph):
	"""
	WHAT: The return value should be a list of trajectories, where each
		  trajectory is itself a list of step dictionaries.
	"""
	trajectories = simulate_walks(
		scored_graph,
		start_nodes=["ch_C3"],
		num_steps=1,
		walks_per_start=1,
		rng=random.Random(1),
	)

	assert isinstance(trajectories, list)
	assert isinstance(trajectories[0], list)
	assert isinstance(trajectories[0][0], dict)


def test_simulate_walks_raises_for_invalid_walk_count(scored_graph):
	"""walks_per_start must be at least 1."""
	with pytest.raises(ValueError, match="walks_per_start"):
		simulate_walks(scored_graph, start_nodes=["ch_L1"], num_steps=2, walks_per_start=0)


def test_default_weight_attribute_constant_matches_graph_builder_schema():
	"""
	WHAT: The simulator's default weight attribute name should match the
		  schema used by graph_builder.py.

	WHY: If these names drift apart, the simulator would silently ignore
		 the real edge weights and produce wrong random-walk behavior.
	"""
	assert DEFAULT_WEIGHT_ATTRIBUTE == "RELEVANT_IMPRESSIONS_DAILY"


# ==============================================================================
# TESTS — simulate_walk_uniform()
# ==============================================================================
#
# The "uniform" walk is a CONTROL EXPERIMENT. Instead of following
# recommendation edges (which the real YouTube algorithm would produce),
# the walker teleports to a RANDOM scored node at every step.
#
# If following recommendations causes more drift than random browsing,
# that proves the recommendation structure is responsible for the drift.
#
# ==============================================================================


def test_simulate_walk_uniform_picks_any_node(scored_graph):
	"""
	WHAT: A uniform walk should produce a trajectory with the correct format:
	      each step has STEP_FIELD, NODE_FIELD, and SCORE_FIELD.

	WHY: Even though the walk ignores edges, the trajectory format must
	     match the recommendation walk format so metrics.py can process
	     both types identically.
	"""
	trajectory = simulate_walk_uniform(
		scored_graph,
		start_node="ch_L1",
		num_steps=5,
		rng=random.Random(42),
	)

	# Walk should have num_steps + 1 records (start node + 5 steps).
	assert len(trajectory) == 6, f"Expected 6 records, got {len(trajectory)}."

	# Every record should contain the three required fields.
	for record in trajectory:
		assert STEP_FIELD in record, "Missing step field."
		assert NODE_FIELD in record, "Missing node_id field."
		assert SCORE_FIELD in record, "Missing ideology_score field."

	# Step numbers should be sequential: 0, 1, 2, 3, 4, 5.
	steps = [record[STEP_FIELD] for record in trajectory]
	assert steps == list(range(6)), f"Steps should be 0..5, got {steps}."

	# The start node should be the one we passed in.
	assert trajectory[0][NODE_FIELD] == "ch_L1"


def test_simulate_walk_uniform_ignores_edges(scored_graph):
	"""
	WHAT: An isolated node (ch_island has no outgoing edges) should still
	      complete a full uniform walk — because uniform walk picks from
	      ALL scored nodes, not from neighbors.

	WHY: This is the key difference between the recommendation walk and
	     the random baseline. The recommendation walk stops at dead ends;
	     the uniform walk cannot get stuck.
	"""
	trajectory = simulate_walk_uniform(
		scored_graph,
		start_node="ch_island",
		num_steps=5,
		rng=random.Random(42),
	)

	# Should NOT stop early. Full length = 6 records.
	assert len(trajectory) == 6, (
		f"Uniform walk should never stop early. Expected 6 records, got {len(trajectory)}."
	)


def test_simulate_walks_uniform_returns_correct_count(scored_graph):
	"""
	WHAT: 2 start nodes × 2 walks each = 4 trajectories total.

	WHY: This verifies the outer loop logic of the batch wrapper,
	     matching the same interface as simulate_walks().
	"""
	trajectories = simulate_walks_uniform(
		scored_graph,
		start_nodes=["ch_L1", "ch_R1"],
		num_steps=3,
		walks_per_start=2,
		rng=random.Random(42),
	)

	assert len(trajectories) == 4, f"Expected 4 trajectories, got {len(trajectories)}."
