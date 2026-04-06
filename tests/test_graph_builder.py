# ==============================================================================
# TEST MODULE: test_graph_builder.py
# PURPOSE: Verify that graph_builder.py correctly loads data and builds graphs.
# ==============================================================================
#
# HOW TESTING WORKS:
#   pytest (our test runner) automatically discovers functions whose names
#   start with "test_". When you run "pytest" from the terminal, it:
#     1. Finds all files named test_*.py
#     2. Finds all functions named test_*() inside them
#     3. Runs each one
#     4. Reports PASS if no assertion fails, FAIL if one does
#
# WHAT IS AN ASSERTION?
#   An assertion is a statement that says "this MUST be true."
#   Example: assert 2 + 2 == 4  → passes (it is true)
#            assert 2 + 2 == 5  → FAILS (it is false) and the test stops
#
#   When a test fails, pytest shows you:
#     - Which assertion failed
#     - What the expected value was
#     - What the actual value was
#   This makes it easy to find and fix the bug.
#
# TEST STRUCTURE — ARRANGE, ACT, ASSERT:
#   Every well-written test follows three steps:
#     1. ARRANGE: Set up the inputs (load the test fixture CSVs)
#     2. ACT:     Call the function being tested (build the graph)
#     3. ASSERT:  Check that the result is correct (node count, etc.)
#
# WHAT IS A FIXTURE (in pytest)?
#   pytest has a feature called "fixtures" — functions decorated with
#   @pytest.fixture that run BEFORE each test to set up shared resources.
#   We use one fixture (sample_graph) to build the test graph once and
#   share it across all tests, avoiding redundant file loading.
#
# WHY TEST IN ISOLATION?
#   These tests verify ONLY graph_builder.py. They don't test ideology
#   scoring, simulation, or metrics. If a test here fails, you know the
#   bug is in graph_builder.py — not somewhere else. This is the whole
#   point of modular testing.
#
# ==============================================================================


# --- IMPORTS ------------------------------------------------------------------

import os               # os: provides operating system utilities. We use
                         # os.path.join() to build file paths that work on
                         # both macOS ("/") and Windows ("\"). Hardcoding
                         # "/" would break on Windows.

import pytest            # pytest: the test runner framework. We import it
                         # to use the @pytest.fixture decorator.

import networkx as nx    # networkx: we need this to check properties of
                         # the graph object returned by build_graph().

# Import the functions we're testing from our own src/ package.
# "from src.graph_builder import ..." means:
#   "Go into the src/ folder, open graph_builder.py, and bring in
#    these three functions so we can call them in our tests."
from src.graph_builder import load_nodes, load_edges, build_graph


# --- CONSTANTS ---------------------------------------------------------------

# Path to the directory containing our synthetic test CSV files.
# os.path.dirname(__file__) gives us the directory where THIS test file
# lives (tests/). We then join "fixtures" to get "tests/fixtures/".
#
# __file__ is a special Python variable that holds the path to the
# current file. It's set automatically by Python when the file is loaded.
FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")

# Full paths to each fixture CSV, built by joining the directory path
# with the filename. This produces paths like:
#   "tests/fixtures/test_nodes.csv"
#   "tests/fixtures/test_edges.csv"
NODES_CSV = os.path.join(FIXTURES_DIR, "test_nodes.csv")
EDGES_CSV = os.path.join(FIXTURES_DIR, "test_edges.csv")


# --- FIXTURES -----------------------------------------------------------------
# A pytest fixture is a function that produces something tests need.
# By marking it with @pytest.fixture, pytest will:
#   1. Run this function before any test that asks for it
#   2. Pass the return value into that test as an argument
#
# The benefit: if 10 tests all need a graph, we write the setup code
# once here instead of repeating it in every test function.


@pytest.fixture
def nodes_df():
    """
    Load the synthetic node CSV and return it as a DataFrame.

    Any test that includes "nodes_df" as a parameter will automatically
    receive this DataFrame — pytest handles the wiring.
    """
    return load_nodes(NODES_CSV)


@pytest.fixture
def edges_df():
    """
    Load the synthetic edge CSV and return it as a DataFrame.
    """
    return load_edges(EDGES_CSV)


@pytest.fixture
def sample_graph(nodes_df, edges_df):
    """
    Build the full test graph from synthetic data.

    NOTE: This fixture depends on the nodes_df and edges_df fixtures
    above. pytest sees that sample_graph needs nodes_df and edges_df,
    so it runs those fixtures first and passes their results in.
    This is called "fixture chaining" — fixtures can depend on other
    fixtures.
    """
    return build_graph(nodes_df, edges_df)


# ==============================================================================
# TESTS — Loading Data
# ==============================================================================
# These tests verify that load_nodes() and load_edges() correctly read
# the CSV files and produce DataFrames with the right shape and content.
# If these fail, the problem is in file reading, not graph construction.


def test_load_nodes_row_count(nodes_df):
    """
    WHAT: Verify that load_nodes() reads exactly 10 rows.

    WHY: Our test_nodes.csv has exactly 10 channels. If the count is
         wrong, either:
         - Rows are being skipped (maybe a parsing error on a line)
         - The comment="#" setting is eating data rows
         - The file is malformed

    ARRANGE: nodes_df fixture loads the CSV (done automatically by pytest).
    ACT:     We just check the length — loading already happened.
    ASSERT:  Must be exactly 10.
    """
    assert len(nodes_df) == 10, (
        f"Expected 10 node rows, got {len(nodes_df)}. "
        "Check test_nodes.csv for formatting issues."
    )


def test_load_nodes_has_required_columns(nodes_df):
    """
    WHAT: Verify that the critical columns exist in the loaded DataFrame.

    WHY: If a column is misspelled or missing in the CSV, the loader
         won't crash — it'll just produce a DataFrame without that column.
         The crash would happen LATER when build_graph tries to read it,
         making the bug harder to trace. This test catches it early.

    We check for the columns that graph_builder actually uses:
    CHANNEL_ID (node identifier) and LR (ideology label).
    """
    # "columns" is a list of all column names in the DataFrame.
    required = ["CHANNEL_ID", "LR", "CHANNEL_TITLE"]
    for col in required:
        assert col in nodes_df.columns, (
            f"Required column '{col}' not found in node data. "
            f"Available columns: {list(nodes_df.columns)}"
        )


def test_load_edges_row_count(edges_df):
    """
    WHAT: Verify that load_edges() reads exactly 16 rows (including
          the self-loop).

    WHY: Same logic as the node count test. 16 rows is what we designed
         into test_edges.csv.
    """
    assert len(edges_df) == 16, (
        f"Expected 16 edge rows, got {len(edges_df)}."
    )


def test_load_edges_has_required_columns(edges_df):
    """
    WHAT: Verify that edge data has the columns needed for graph construction.
    """
    required = [
        "FROM_CHANNEL_ID",
        "TO_CHANNEL_ID",
        "RELEVANT_IMPRESSIONS_DAILY",
    ]
    for col in required:
        assert col in edges_df.columns, (
            f"Required column '{col}' not found in edge data."
        )


# ==============================================================================
# TESTS — Graph Construction
# ==============================================================================
# These tests verify that build_graph() correctly assembles the DiGraph
# from the DataFrames. They use the sample_graph fixture, which chains
# through load_nodes → load_edges → build_graph automatically.


def test_graph_is_directed(sample_graph):
    """
    WHAT: Verify the graph is a DiGraph (directed), not a regular Graph.

    WHY: Recommendations are one-way: "YouTube recommends B when you
         watch A" does NOT mean "YouTube recommends A when you watch B."
         If we accidentally created an undirected Graph, every edge
         would go both ways, completely distorting the analysis.
         A→B would also create B→A, doubling edges and breaking
         path simulation.
    """
    assert isinstance(sample_graph, nx.DiGraph), (
        f"Expected a DiGraph, got {type(sample_graph).__name__}. "
        "Recommendations are directional — use nx.DiGraph()."
    )


def test_graph_node_count(sample_graph):
    """
    WHAT: Verify the graph has exactly 10 nodes.

    WHY: This is the most fundamental correctness check. Our test data
         has 10 channels. If the graph has fewer, a node was skipped.
         If it has more, duplicate or phantom nodes were created.
         The isolated node (ch_island) should be present even though
         it has no edges — it was added during the node-adding step,
         which is independent from edge-adding.
    """
    assert sample_graph.number_of_nodes() == 10, (
        f"Expected 10 nodes, got {sample_graph.number_of_nodes()}."
    )


def test_graph_edge_count_after_self_loop_removal(sample_graph):
    """
    WHAT: Verify the graph has exactly 15 edges (16 minus 1 self-loop).

    WHY: This is the critical test for self-loop filtering.
         Our test data has 16 edges, one of which is ch_R1 → ch_R1.
         build_graph() must remove it, leaving 15.
         If this returns 16, the self-loop filter is broken.
         If this returns less than 15, real edges were accidentally removed.
    """
    assert sample_graph.number_of_edges() == 15, (
        f"Expected 15 edges (16 raw - 1 self-loop), "
        f"got {sample_graph.number_of_edges()}."
    )


def test_no_self_loops_remain(sample_graph):
    """
    WHAT: Verify that zero self-loops exist in the finished graph.

    WHY: The previous test checks the count is 15, but what if a
         different edge was removed by mistake and the self-loop is
         still there? This test checks directly: are there any edges
         where source == target? There should be zero.
    """
    self_loops = list(nx.selfloop_edges(sample_graph))
    assert len(self_loops) == 0, (
        f"Found {len(self_loops)} self-loop(s) in graph: {self_loops}. "
        "Self-loops should have been removed by build_graph()."
    )


def test_specific_nodes_exist(sample_graph):
    """
    WHAT: Verify that specific expected nodes are present in the graph.

    WHY: Checking the count is 10 doesn't guarantee the RIGHT 10 nodes
         are present. This spot-checks critical nodes:
         - ch_L1 (Left, used as start of drift chain)
         - ch_R1 (Right, has the self-loop we filtered)
         - ch_island (isolated node with no edges)
    """
    for node_id in ["ch_L1", "ch_R1", "ch_island"]:
        assert sample_graph.has_node(node_id), (
            f"Node '{node_id}' not found in graph."
        )


def test_specific_edges_exist(sample_graph):
    """
    WHAT: Verify that specific expected edges are present.

    WHY: Spot-checks that the edge-adding logic works correctly.
         We test a within-cluster edge and a cross-ideology edge.
    """
    # Within-cluster: ch_L1 → ch_L2 (Left to Left)
    assert sample_graph.has_edge("ch_L1", "ch_L2"), (
        "Edge ch_L1 → ch_L2 not found."
    )

    # Cross-ideology: ch_L1 → ch_C1 (Left to Center)
    assert sample_graph.has_edge("ch_L1", "ch_C1"), (
        "Edge ch_L1 → ch_C1 not found."
    )


def test_self_loop_edge_was_removed(sample_graph):
    """
    WHAT: Verify that the specific self-loop ch_R1 → ch_R1 is gone.

    WHY: Our test data has exactly one self-loop: ch_R1 recommending
         itself. This test confirms that SPECIFIC edge was removed,
         not just that the count is correct.
    """
    assert not sample_graph.has_edge("ch_R1", "ch_R1"), (
        "Self-loop ch_R1 → ch_R1 should have been removed."
    )


def test_node_attributes_attached(sample_graph):
    """
    WHAT: Verify that node attributes (metadata) are attached correctly.

    WHY: build_graph() is supposed to attach channel metadata (LR label,
         title, subscriber count, etc.) as node attributes. If this
         doesn't work, ideology.py won't be able to read the LR label
         to assign numeric scores, and the entire pipeline breaks.

         We check ch_L1 because we know its exact values from the
         test fixture:
           - CHANNEL_TITLE = "Left News 1"
           - LR = "L"
    """
    attrs = sample_graph.nodes["ch_L1"]

    assert "LR" in attrs, (
        "Node 'ch_L1' is missing the 'LR' attribute. "
        "build_graph() should attach metadata from the CSV."
    )
    assert attrs["LR"] == "L", (
        f"Expected ch_L1 LR='L', got '{attrs['LR']}'."
    )
    assert attrs["CHANNEL_TITLE"] == "Left News 1", (
        f"Expected ch_L1 title='Left News 1', got '{attrs['CHANNEL_TITLE']}'."
    )


def test_edge_attributes_attached(sample_graph):
    """
    WHAT: Verify that edge attributes (weights) are attached correctly.

    WHY: The simulator will use RELEVANT_IMPRESSIONS_DAILY as the edge
         weight for weighted random walks. If this attribute is missing,
         the simulator can't do weighted selection and will either crash
         or fall back to uniform random walks (giving wrong results).

         We check the ch_L1 → ch_L2 edge, which has weight 200.0
         in our test fixture.
    """
    edge_data = sample_graph.edges["ch_L1", "ch_L2"]

    assert "RELEVANT_IMPRESSIONS_DAILY" in edge_data, (
        "Edge ch_L1→ch_L2 is missing 'RELEVANT_IMPRESSIONS_DAILY'. "
        "build_graph() should attach edge weights from the CSV."
    )
    assert edge_data["RELEVANT_IMPRESSIONS_DAILY"] == 200.0, (
        f"Expected weight 200.0, got {edge_data['RELEVANT_IMPRESSIONS_DAILY']}."
    )


def test_isolated_node_has_no_edges(sample_graph):
    """
    WHAT: Verify that ch_island exists but has zero edges.

    WHY: ch_island is our isolated node — it's in the node CSV but
         has no rows in the edge CSV. This test verifies:
         1. The node exists (it was added during node-adding)
         2. It has no outgoing edges (out-degree = 0)
         3. It has no incoming edges (in-degree = 0)

         If this test breaks, build_graph() might be creating phantom
         edges or skipping nodes that aren't in the edge data.

    TERMINOLOGY:
         "degree" = number of edges connected to a node.
         "out-degree" = number of outgoing edges (recs FROM this node).
         "in-degree" = number of incoming edges (recs TO this node).
    """
    assert sample_graph.has_node("ch_island"), (
        "Isolated node 'ch_island' should exist in the graph."
    )
    assert sample_graph.out_degree("ch_island") == 0, (
        f"ch_island should have 0 outgoing edges, "
        f"got {sample_graph.out_degree('ch_island')}."
    )
    assert sample_graph.in_degree("ch_island") == 0, (
        f"ch_island should have 0 incoming edges, "
        f"got {sample_graph.in_degree('ch_island')}."
    )


def test_all_lr_values_present(sample_graph):
    """
    WHAT: Verify that nodes with L, C, and R labels all exist.

    WHY: If one ideology label is missing, it could mean:
         - Rows with that label were skipped during loading
         - The LR attribute wasn't attached correctly
         Either way, the ideology scoring and analysis would be
         incomplete. We need all three to test the full L→C→R spectrum.
    """
    # Collect all unique LR values across all nodes in the graph.
    # G.nodes[node_id] returns the attribute dictionary for that node.
    # We extract the "LR" value from each node and put them in a set.
    # A set automatically removes duplicates.
    lr_values = {
        sample_graph.nodes[n].get("LR")  # .get() returns None if missing
        for n in sample_graph.nodes                 # instead of crashing
    }

    assert "L" in lr_values, "No Left-labeled nodes found."
    assert "C" in lr_values, "No Center-labeled nodes found."
    assert "R" in lr_values, "No Right-labeled nodes found."
