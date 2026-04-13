# ==============================================================================
# TEST MODULE: test_ideology.py
# PURPOSE: Verify that ideology.py correctly maps LR labels to numeric
#          scores and attaches them to every node in the graph.
# ==============================================================================
#
# WHAT WE ARE TESTING:
#   The single function assign_ideology_scores(G) which:
#     - reads the "LR" node attribute added by graph_builder
#     - maps "L" → -1.0, "C" → 0.0, "R" → 1.0
#     - writes the result as "IDEOLOGY_SCORE" on each node
#     - handles missing or unknown labels gracefully (returns None)
#     - modifies the graph in-place and returns it
#
# TEST DESIGN STRATEGY:
#   We use two kinds of test setups:
#
#   1. FIXTURE-BASED TESTS (using our test_nodes.csv + test_edges.csv data)
#      These test the module as it will be called in the real pipeline:
#      build a graph from CSV files, then call assign_ideology_scores on it.
#      This is called an "integration-style" test — it exercises the
#      boundary between graph_builder and ideology together.
#
#   2. MANUAL MINI-GRAPH TESTS (constructing a tiny graph in the test itself)
#      For edge cases (missing LR, unknown LR), it's cleaner to build a
#      controlled 1-node graph than to rely on the CSV fixture having that
#      exact scenario. This is called a "unit test" — it isolates one
#      specific behaviour.
#
# WHAT "IN-PLACE" MEANS FOR TESTING:
#   assign_ideology_scores modifies the graph object G directly.
#   This means: after calling the function, the SAME graph we passed in
#   has new attributes on its nodes. We don't need to capture a return value
#   to see the changes, though we do to verify the return value too.
#
# TEST STRUCTURE — ARRANGE, ACT, ASSERT:
#   Every test follows the same three steps:
#     1. ARRANGE: set up inputs (load fixture graph, or build mini-graph)
#     2. ACT:     call assign_ideology_scores()
#     3. ASSERT:  check the IDEOLOGY_SCORE attribute on specific nodes
#
# ==============================================================================


# --- IMPORTS ------------------------------------------------------------------

import os               # os.path.join builds cross-platform file paths

import pytest           # pytest: test runner. We use @pytest.fixture.

import networkx as nx   # We build mini-graphs for edge-case tests

# Import the full graph building pipeline so we can test end-to-end.
from src.graph_builder import load_nodes, load_edges, build_graph

# Import the function and constant we are testing.
# Importing SCORE_ATTRIBUTE from the module is better than hardcoding the
# string "IDEOLOGY_SCORE" in every test. If the name changes, the test
# automatically breaks and tells you where to update — rather than silently
# looking at a nonexistent attribute.
from src.ideology import assign_ideology_scores, SCORE_ATTRIBUTE


# --- CONSTANTS ---------------------------------------------------------------

# Same fixture paths as test_graph_builder.py.
# Each test file is independent — we do not import fixtures from other
# test files. This keeps test files isolated: a change in one module's
# tests can't break another module's tests.
FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")
NODES_CSV = os.path.join(FIXTURES_DIR, "test_nodes.csv")
EDGES_CSV = os.path.join(FIXTURES_DIR, "test_edges.csv")


# --- FIXTURES -----------------------------------------------------------------

@pytest.fixture
def scored_graph():
    """
    Build the full test graph AND assign ideology scores to it.

    This fixture chains three steps together:
      load_nodes → load_edges → build_graph → assign_ideology_scores

    Any test that includes "scored_graph" in its parameters automatically
    receives a fully-built, fully-scored graph. pytest handles the wiring.

    WHY COMBINE BUILD AND SCORE INTO ONE FIXTURE?
    Because every test in this file needs a scored graph — none of them
    care about the "before scoring" state. Having one fixture that delivers
    the final state keeps each test shorter and more readable.
    """
    nodes_df = load_nodes(NODES_CSV)
    edges_df  = load_edges(EDGES_CSV)
    G = build_graph(nodes_df, edges_df)
    assign_ideology_scores(G)   # Modifies G in-place
    return G


# ==============================================================================
# TESTS — Correct score values for each ideology label
# ==============================================================================
# This group of tests checks the core mapping: does each label produce
# the right number? We test each label in isolation using a known node.


def test_left_node_gets_negative_one(scored_graph):
    """
    WHAT: ch_L1 is labeled LR="L". After scoring, its IDEOLOGY_SCORE
          must be -1.0.

    WHY: The entire drift analysis depends on "Left" being -1. If this
         mapping is wrong, all statistical results (average drift, direction
         of change) will be wrong. This is the most critical test.

    ARRANGE: scored_graph fixture builds and scores the graph.
    ACT:     We access the node attribute (scoring already happened).
    ASSERT:  The score is exactly -1.0.
    """
    score = scored_graph.nodes["ch_L1"][SCORE_ATTRIBUTE]
    assert score == -1.0, (
        f"Expected ch_L1 IDEOLOGY_SCORE=-1.0, got {score}. "
        "Check the LR_TO_SCORE mapping for 'L'."
    )


def test_center_node_gets_zero(scored_graph):
    """
    WHAT: ch_C1 is labeled LR="C". After scoring, its IDEOLOGY_SCORE
          must be 0.0.

    WHY: Center nodes are the reference point. If they're off-center in
         the numeric scale, all comparisons between left, center, and right
         will be skewed.
    """
    score = scored_graph.nodes["ch_C1"][SCORE_ATTRIBUTE]
    assert score == 0.0, (
        f"Expected ch_C1 IDEOLOGY_SCORE=0.0, got {score}. "
        "Check the LR_TO_SCORE mapping for 'C'."
    )


def test_right_node_gets_positive_one(scored_graph):
    """
    WHAT: ch_R1 is labeled LR="R". After scoring, its IDEOLOGY_SCORE
          must be +1.0.

    WHY: Same rationale as the Left test — fundamental mapping correctness.
    """
    score = scored_graph.nodes["ch_R1"][SCORE_ATTRIBUTE]
    assert score == 1.0, (
        f"Expected ch_R1 IDEOLOGY_SCORE=1.0, got {score}. "
        "Check the LR_TO_SCORE mapping for 'R'."
    )


# ==============================================================================
# TESTS — Coverage: every node receives a score
# ==============================================================================


def test_all_nodes_have_score_attribute(scored_graph):
    """
    WHAT: After calling assign_ideology_scores, EVERY node in the graph
          must have the IDEOLOGY_SCORE attribute — even if its value is None.

    WHY: If even one node is missing the attribute, the simulator will
         crash with a KeyError the moment it tries to read the score for
         that node. We need 100% coverage.

    HOW: We iterate over all nodes and check that SCORE_ATTRIBUTE is present
         in each node's attribute dictionary. "Present" means the key exists,
         even if its value is None.
    """
    for node_id in scored_graph.nodes:
        attrs = scored_graph.nodes[node_id]
        assert SCORE_ATTRIBUTE in attrs, (
            f"Node '{node_id}' is missing the '{SCORE_ATTRIBUTE}' attribute. "
            "assign_ideology_scores() must process every node, even isolated ones."
        )


def test_isolated_node_is_scored(scored_graph):
    """
    WHAT: ch_island is an isolated node (no edges). It is labeled LR="C"
          in our test fixture, so it should get IDEOLOGY_SCORE=0.0.

    WHY: A common bug is to only process nodes that have edges, ignoring
         isolated nodes. This test catches that. Isolated nodes still need
         scores because the metrics module might include them in averages.
    """
    score = scored_graph.nodes["ch_island"][SCORE_ATTRIBUTE]
    assert score == 0.0, (
        f"Expected ch_island IDEOLOGY_SCORE=0.0, got {score}. "
        "Isolated nodes must be scored just like connected ones."
    )


def test_score_attribute_is_float_or_none(scored_graph):
    """
    WHAT: Every IDEOLOGY_SCORE value must be a float or None.
          It must NOT be a string (e.g., "L" or "-1.0").

    WHY: If the code accidentally stores the original string label instead
         of looking up the numeric score, downstream math will crash with a
         TypeError when it tries to average strings. This catches that bug.

    HOW: Python's isinstance(value, float) returns True for floats.
         We accept None explicitly because that is the valid "unknown" value.
    """
    for node_id in scored_graph.nodes:
        score = scored_graph.nodes[node_id][SCORE_ATTRIBUTE]
        is_valid = (score is None) or isinstance(score, float)
        assert is_valid, (
            f"Node '{node_id}' IDEOLOGY_SCORE is type {type(score).__name__} "
            f"with value {score!r}. Expected float or None."
        )


# ==============================================================================
# TESTS — Spot-check all three labels on separate nodes
# ==============================================================================
# These tests complement the first group by checking the other L, C, R
# nodes. Having multiple representatives of each class catches a bug where
# only the FIRST node of a label works and something breaks for the rest.


def test_second_left_node_scored(scored_graph):
    """ch_L2 is the second Left node. It should also get -1.0."""
    assert scored_graph.nodes["ch_L2"][SCORE_ATTRIBUTE] == -1.0


def test_second_center_node_scored(scored_graph):
    """ch_C2 is the second Center node. It should also get 0.0."""
    assert scored_graph.nodes["ch_C2"][SCORE_ATTRIBUTE] == 0.0


def test_second_right_node_scored(scored_graph):
    """ch_R2 is the second Right node. It should also get 1.0."""
    assert scored_graph.nodes["ch_R2"][SCORE_ATTRIBUTE] == 1.0


# ==============================================================================
# TESTS — Edge cases: missing and unknown labels
# ==============================================================================
# These tests use hand-built mini-graphs, not the CSV fixture.
# Why? Because we want precise control over the node attributes.
# The fixture data is clean (all LR values are L, C, or R). But the
# real dataset might have messy values, and we need to verify our
# code handles them gracefully rather than crashing.


def test_missing_lr_attribute_gets_none():
    """
    WHAT: A node with NO "LR" attribute at all should get IDEOLOGY_SCORE=None.

    WHY: If a node's LR attribute is missing (not just empty — completely
         absent), the code must not crash. It must silently assign None.
         This can happen if the CSV had a blank cell or the column wasn't
         present in the data file.

    HOW: We build a 1-node graph manually and add a node WITHOUT attaching
         any "LR" attribute. Then we call assign_ideology_scores and check.
    """
    # ARRANGE: Create a minimal directed graph with one node, no LR attribute.
    G = nx.DiGraph()
    G.add_node("orphan")   # No attributes — not even LR.

    # ACT: Run the scoring function.
    assign_ideology_scores(G)

    # ASSERT: The node should have IDEOLOGY_SCORE=None (not raise an error).
    score = G.nodes["orphan"][SCORE_ATTRIBUTE]
    assert score is None, (
        f"Expected None for a node with no LR attribute, got {score!r}. "
        "Missing LR should not crash — it should produce None."
    )


def test_unknown_lr_label_gets_none():
    """
    WHAT: A node with LR="X" (an unrecognised label) gets IDEOLOGY_SCORE=None.

    WHY: The real dataset might contain unexpected values (typos, new
         categories, blank strings). We must not silently assign the wrong
         score — we must signal "we don't know" by returning None.

    HOW: Build a 1-node graph with LR="X" and verify the output is None.
    """
    # ARRANGE: A node with an unexpected LR value.
    G = nx.DiGraph()
    G.add_node("mystery", LR="X")   # "X" is not a valid label.

    # ACT
    assign_ideology_scores(G)

    # ASSERT
    score = G.nodes["mystery"][SCORE_ATTRIBUTE]
    assert score is None, (
        f"Expected None for unknown LR label 'X', got {score!r}. "
        "Unknown labels should not be silently mapped to 0 — use None."
    )


# ==============================================================================
# TESTS — Return value
# ==============================================================================


def test_function_returns_same_graph_object():
    """
    WHAT: assign_ideology_scores() must return the exact same graph object
          it received as input (not a copy).

    WHY: The function modifies the graph in-place. Returning the same
         object lets callers chain calls. If the function accidentally
         returned a different object, callers who relied on the return
         value would have an un-scored graph and never know it.

    HOW: Python's "is" operator checks identity (same object in memory),
         not just equality. Two objects can be "equal" but not the same.
         "is" guarantees we got the exact same graph back.
    """
    G = nx.DiGraph()
    G.add_node("test_node", LR="L")

    returned = assign_ideology_scores(G)

    assert returned is G, (
        "assign_ideology_scores() should return the same graph object "
        "it received, not a copy. Use 'return G' at the end of the function."
    )
