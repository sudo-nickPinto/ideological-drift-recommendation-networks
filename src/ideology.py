# ==============================================================================
# MODULE: ideology.py
# PURPOSE: Convert each channel's LR label into a numeric ideology score
#          and attach that score to every node in the graph.
# ==============================================================================
#
# This is the SECOND module in the analysis pipeline:
#
#     graph_builder.py  →  ideology.py  →  simulator.py  →  metrics.py  →  visualize.py
#                          ^^^^^^^^^^^
#
# WHAT THIS MODULE DOES:
#   The graph produced by graph_builder.py has a string label on every node:
#   "L", "C", or "R". Strings are for humans to read, but math can't operate
#   on a string. You can't compute the average of ("L", "R", "L", "C") —
#   you get a TypeError. You CAN compute the average of (-1, 1, -1, 0) = -0.25.
#
#   This module bridges that gap. It translates the categorical (text)
#   ideology label into a quantitative (numeric) ideology score:
#
#       "L"  →  -1.0    (Left)
#       "C"  →   0.0    (Center)
#       "R"  →  +1.0    (Right)
#
#   This −1 to +1 scale is called a "continuous ideological spectrum."
#   It is the standard encoding used in political science computational
#   research. The sign convention (Left = negative, Right = positive)
#   follows the standard Western political science convention.
#
#   After this module runs, every node in the graph has an "IDEOLOGY_SCORE"
#   attribute (a float), which is what the simulator and metrics modules read.
#
# WHAT HAPPENS STEP BY STEP:
#   1. Define a lookup dictionary: label → score
#   2. Iterate over every node in the graph
#   3. Read each node's LR attribute (attached by graph_builder)
#   4. Look up the numeric score for that label
#   5. Attach the numeric score as a new node attribute ("IDEOLOGY_SCORE")
#   6. Return the modified graph
#
# DESIGN DECISIONS:
#   - assign_ideology_scores() modifies the graph IN-PLACE and also returns it.
#     "In-place" means we change the object G itself, not a copy.
#     Returning G too allows you to chain calls:
#       G = assign_ideology_scores(build_graph(nodes_df, edges_df))
#   - Missing or unknown labels get None (Python's "no value").
#     This prevents silent wrong answers — if a node gets treated as 0.0
#     when its label is actually unknown, downstream averages would be wrong
#     in a hard-to-detect way. None makes the gap visible and explicit.
#   - The score constant is named SCORE_ATTRIBUTE so the name is defined
#     in one place. If we ever rename "IDEOLOGY_SCORE" to "SCORE", we
#     change one line instead of searching the whole codebase.
#
# ==============================================================================


import networkx as nx    # We import nx to use its type in the docstring.
                         # In this module we don't CREATE a graph — we receive
                         # one and modify it. But the type annotation in the
                         # docstring still needs nx.DiGraph.


# --- CONSTANTS ----------------------------------------------------------------

# The mapping from text label to numeric score.
# A dictionary in Python is a set of key → value pairs.
# You look up a value by its key: LR_TO_SCORE["L"] returns -1.0
#
# Why floats (-1.0, 0.0, 1.0) instead of integers (-1, 0, 1)?
# Because downstream computations (averages, standard deviations) produce
# floats. Starting with floats avoids implicit integer→float conversions
# and potential rounding surprises. It also signals to readers that these
# are measurements on a continuous scale, not category codes.
LR_TO_SCORE = {
    "L": -1.0,    # Left
    "C":  0.0,    # Center
    "R": +1.0,    # Right
}

# The name of the attribute we will attach to every node.
# Defining it as a constant means:
#   - ideology.py defines it here
#   - simulator.py and metrics.py import this name: from src.ideology import SCORE_ATTRIBUTE
#   - If the name ever changes, we change it in one place instead of many
SCORE_ATTRIBUTE = "IDEOLOGY_SCORE"


# --- FUNCTIONS ----------------------------------------------------------------

def assign_ideology_scores(G):
    """
    Translate each node's LR string label into a numeric ideology score
    and attach it as a new node attribute.

    WHAT THIS FUNCTION DOES:
        Reads the "LR" attribute already on each node (attached by
        graph_builder's build_graph), maps it through LR_TO_SCORE, and
        writes the resulting float back onto the node as "IDEOLOGY_SCORE".

        Nodes with a missing or unrecognised LR label receive None.

    PARAMETERS:
        G (networkx.DiGraph): The recommendation graph produced by
                              build_graph(). Every node is expected to
                              have an "LR" attribute, but the function
                              handles nodes that are missing it.

    RETURNS:
        networkx.DiGraph: The SAME graph object, now with "IDEOLOGY_SCORE"
                          on every node. The graph is modified IN-PLACE
                          (we change G itself, not a copy), and is also
                          returned so callers can chain this call.

    WHY IN-PLACE?
        The graph can be large (~7,000 nodes, ~400,000 edges). Making a
        deep copy would double memory usage for no benefit, since no part
        of the pipeline needs to keep the "before scoring" version of the
        graph. Modifying in-place is both safer (no accidental duplicate
        objects) and more efficient.

    EXAMPLE:
        >>> G = build_graph(nodes_df, edges_df)
        >>> G = assign_ideology_scores(G)
        >>> G.nodes["ch_L1"]["IDEOLOGY_SCORE"]
        -1.0
        >>> G.nodes["ch_C1"]["IDEOLOGY_SCORE"]
        0.0
        >>> G.nodes["ch_R1"]["IDEOLOGY_SCORE"]
        1.0
    """

    # Iterate over every node identifier in the graph.
    # G.nodes returns a NodeView — a collection of all node IDs
    # (e.g., "ch_L1", "ch_C1", "ch_R1", ...).
    # We don't need the attribute dictionary on this loop — we access
    # it below via G.nodes[node_id].
    for node_id in G.nodes:

        # Read the LR label from the node's attribute dictionary.
        # G.nodes[node_id] returns a dictionary of attributes for that node,
        # e.g.: {"CHANNEL_TITLE": "Left News 1", "LR": "L", "SUBS": 10000}
        #
        # We use .get("LR") instead of ["LR"] on purpose.
        # Dictionary access with ["LR"] raises a KeyError if the key is
        # absent. .get("LR") returns None if the key is missing — safe.
        # In rare cases a node might have been loaded without an LR column;
        # we should not crash on those.
        lr_label = G.nodes[node_id].get("LR")

        # Look up the numeric score for this label.
        # LR_TO_SCORE.get(lr_label) does the same safe lookup:
        #   - "L" → -1.0
        #   - "C" →  0.0
        #   - "R" → +1.0
        #   - None (missing LR) → None
        #   - Any other string like "Unknown" → None
        #
        # Returning None for unknown labels is a deliberate choice.
        # An alternative would be to raise an error (strict) or assign 0.0
        # (forgiving). We choose None because:
        #   - Raises an error: too harsh — the real dataset may have noise.
        #   - Assign 0.0: dangerous — treats unknown as "Center," which
        #     could make averages look more centrist than they are.
        #   - None: forces downstream code to handle the gap explicitly
        #     (e.g., skip it in calculations or flag it in output).
        score = LR_TO_SCORE.get(lr_label)

        # Write the score back onto the node.
        # This is the same syntax as adding a key to any Python dictionary.
        # After this line: G.nodes["ch_L1"]["IDEOLOGY_SCORE"] == -1.0
        G.nodes[node_id][SCORE_ATTRIBUTE] = score

    # Return the graph.
    # Because we modified G in-place, the caller's variable already points
    # at the updated graph. Returning it anyway lets you write:
    #   scored_graph = assign_ideology_scores(G)
    # or even:
    #   G = assign_ideology_scores(build_graph(...))
    # Both patterns work cleanly.
    return G
