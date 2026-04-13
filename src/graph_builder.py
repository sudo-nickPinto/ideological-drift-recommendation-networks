# ==============================================================================
# MODULE: graph_builder.py
# PURPOSE: Load CSV data and construct the recommendation network graph.
# ==============================================================================
#
# This is the FIRST module in the analysis pipeline:
#
#     graph_builder.py  →  ideology.py  →  simulator.py  →  metrics.py  →  visualize.py
#     ^^^^^^^^^^^^^^^^
#
# WHAT THIS MODULE SHOULD DO:
#   1. Reads the node CSV (channel metadata) into a pandas DataFrame
#   2. Reads the edge CSV (recommendation links) into a pandas DataFrame
#   3. Constructs a NetworkX "DiGraph" (directed graph) where:
#        - Each CHANNEL_ID becomes a node
#        - Each FROM_CHANNEL_ID → TO_CHANNEL_ID becomes a directed edge
#   4. Attaches channel metadata (title, LR label, subscriber count, etc.)
#      as "node attributes" — data that rides along with each node
#   5. Attaches edge metadata (impression count, recommendation percentage)
#      as "edge attributes" — data that rides along with each edge
#   6. Filters out self-loops (a channel recommending itself)
#
#
# DESIGN DECISIONS:
#   - Functions take file paths as arguments rather than hardcoding paths.
#     This means the same code works with test fixtures AND real data.
#   - Each function does ONE thing (load nodes, load edges, build graph).
#     This is the "Single Responsibility Principle" — each function has
#     one reason to change.
#   - The build_graph function returns a plain NetworkX DiGraph object.
#     Downstream modules don't need to know that the data came from CSV
#     files — they just receive a graph object and work with it.
#
# ==============================================================================


import pandas as pd      
import networkx as nx     # networkx: provides the DiGraph data structure and
                          # graph algorithms


# Used as the node ID in the graph.
NODE_ID_COLUMN = "CHANNEL_ID"

EDGE_SOURCE_COLUMN = "FROM_CHANNEL_ID"
EDGE_TARGET_COLUMN = "TO_CHANNEL_ID"

NODE_ATTRIBUTE_COLUMNS = [
    "CHANNEL_TITLE",                   # Human-readable channel name
    "LR",                              # Ideology label: L, C, or R
    "RELEVANCE",                       # Fraction of content about US politics
    "SUBS",                            # Subscriber count
    "CHANNEL_VIEWS",                   # Total lifetime views
    "CHANNEL_VIDEO_VIEWS",             # Total video views
    "RELEVANT_IMPRESSIONS_DAILY",      # Daily outgoing recommendation impressions
    "RELEVANT_IMPRESSIONS_IN_DAILY",   # Daily incoming recommendation impressions
    "MEDIA",                           # Media type (YouTube, Mainstream Media)
    "TAGS",                            # Category tags (JSON array as string)
    "IDEOLOGY",                        # Granular ideology label
]

# Which columns from the edge CSV to attach as edge attributes.
EDGE_ATTRIBUTE_COLUMNS = [
    "RELEVANT_IMPRESSIONS_DAILY",      # Daily impressions for this rec link
    "PERCENT_OF_CHANNEL_RECS",         # Fraction of source's total recs
]

# --- FUNCTIONS ----------------------------------------------------------------

def load_nodes(filepath):
    """
    Read the node (channel) CSV file and return it as a pandas DataFrame.

    PARAMETERS:
        filepath (str): Path to the CSV file containing channel data.
                        Example: "data/vis_channel_stats.csv" for real data
                                 "tests/fixtures/test_nodes.csv" for tests

    RETURNS:
        pandas.DataFrame: A table where each row is one channel.

    """

    # pd.read_csv() does all the heavy lifting:
    #   - Opens the file
    #   - Parses the header row to get column names
    #   - Reads each subsequent row as a data record
    #   - Infers data types (strings, numbers, dates)
    #   - Returns a DataFrame
    #
    # The comment="#" argument tells pandas to skip any line that starts
    # with "#". Our test fixture CSVs have comment headers that explain
    # the data — this ensures pandas ignores those explanatory lines
    # and only reads actual data rows.
    nodes_df = pd.read_csv(filepath, comment="#")

    return nodes_df


def load_edges(filepath):
    """
    Read the edge (recommendation) CSV file and return it as a DataFrame.

    Each row represents one directed recommendation: the platform
    recommended TO_CHANNEL_ID when a user was watching FROM_CHANNEL_ID.

    PARAMETERS:
        filepath (str): Path to the CSV file containing recommendation data.

    RETURNS:
        pandas.DataFrame: A table where each row is one recommendation edge.
    """

    edges_df = pd.read_csv(filepath, comment="#")

    return edges_df


def build_graph(nodes_df, edges_df):
    """
    Construct a directed graph from node and edge DataFrames.

    This is the core function of the module. It takes the raw tabular data
    and transforms it into a NetworkX DiGraph — a data structure purpose-
    built for the kind of analysis we need to do (path finding, centrality,
    clustering, random walks, etc.).

    WHAT HAPPENS STEP BY STEP:
        1. Create an empty directed graph
        2. Add every channel as a node, with its metadata attached
        3. Add every recommendation as a directed edge, with weights attached
        4. Remove self-loops (channels recommending themselves)
        5. Return the finished graph

    PARAMETERS:
        nodes_df (DataFrame): Channel data, as returned by load_nodes().
        edges_df (DataFrame): Recommendation data, as returned by load_edges().

    RETURNS:
        networkx.DiGraph: The completed recommendation network.

    WHAT IS RETURNED?
        A DiGraph object where:
        - G.nodes["ch_L1"] gives you the node for channel "ch_L1"
        - G.nodes["ch_L1"]["LR"] gives you its ideology label ("L")
        - G.nodes["ch_L1"]["CHANNEL_TITLE"] gives you "Left News 1"
        - G.edges["ch_L1", "ch_C1"] gives you the edge from L1 to C1
        - G.edges["ch_L1", "ch_C1"]["RELEVANT_IMPRESSIONS_DAILY"] = 30.0
        - G.number_of_nodes() returns the total node count
        - G.number_of_edges() returns the total edge count (after filtering)
    """

    # STEP 1: Create an empty directed graph.
    # ----------------------------------------
    # nx.DiGraph() creates a new graph object with no nodes and no edges.
    # Think of it as creating an empty canvas that we'll add to.
    # "Di" = Directed. Edges have a FROM and a TO (like one-way streets).
    G = nx.DiGraph()

    # STEP 2: Add nodes with their attributes.
    # -----------------------------------------
    # We iterate over every row in the nodes DataFrame. For each channel,
    # we add it as a node in the graph and attach its metadata.
    #
    # iterrows() gives us two things on each loop iteration:
    #   - index: the row number (0, 1, 2, ...) — we don't need this,
    #            so we use "_" (Python convention for "I'm ignoring this")
    #   - row: a pandas Series containing all column values for that row.
    #          We can access values like row["CHANNEL_ID"], row["LR"], etc.
    for _, row in nodes_df.iterrows():

        # Extract the channel ID — this becomes the node's unique identifier
        # in the graph. Every node in a NetworkX graph needs a unique ID.
        node_id = row[NODE_ID_COLUMN]

        # Build a dictionary of attributes to attach to this node.
        # A dictionary is a collection of key-value pairs:
        #   {"CHANNEL_TITLE": "Left News 1", "LR": "L", "SUBS": 10000, ...}
        #
        # We only include columns listed in NODE_ATTRIBUTE_COLUMNS.
        # The dictionary comprehension below reads as:
        #   "For each column name in our list, create a key-value pair
        #    where the key is the column name and the value is whatever
        #    is in that column for this row."
        attributes = {
            col: row[col]
            for col in NODE_ATTRIBUTE_COLUMNS
            if col in row.index   # Safety check: only include columns that
                                  # actually exist in the data. This prevents
                                  # a crash if a column is missing (e.g., the
                                  # test data might not have every column).
        }

        # Add the node to the graph with its attributes.
        # After this call, G.nodes["ch_L1"]["LR"] will return "L".
        G.add_node(node_id, **attributes)
        # The **attributes syntax "unpacks" the dictionary into keyword
        # arguments. It's equivalent to writing:
        #   G.add_node("ch_L1", CHANNEL_TITLE="Left News 1", LR="L", ...)

    # STEP 3: Add edges with their attributes.
    # -----------------------------------------
    # Same pattern: iterate over every row in the edges DataFrame,
    # add each recommendation as a directed edge.
    for _, row in edges_df.iterrows():

        source = row[EDGE_SOURCE_COLUMN]   # Channel the rec comes FROM
        target = row[EDGE_TARGET_COLUMN]   # Channel the rec goes TO

        # Build edge attributes dictionary, same approach as nodes.
        edge_attrs = {
            col: row[col]
            for col in EDGE_ATTRIBUTE_COLUMNS
            if col in row.index
        }

        # Add the directed edge: source → target.
        # After this call, G.has_edge("ch_L1", "ch_C1") returns True.
        G.add_edge(source, target, **edge_attrs)

    # STEP 4: Remove self-loops.
    # --------------------------
    # A self-loop is an edge where source == target (a channel recommending
    # itself). The real dataset has 6,942 of these. They are meaningless
    # for our analysis because:
    #   - A user is already on that channel, so "recommending" it doesn't
    #     represent navigation to new content.
    #   - In a random walk, a self-loop would mean the walker stays in
    #     place for a step, adding noise without information.
    #
    # nx.selfloop_edges(G) returns a list of all self-loop edges.
    # We convert it to a list first because you can't modify a graph
    # while iterating over it (Python raises an error if you try).
    self_loops = list(nx.selfloop_edges(G))

    # Remove all self-loops from the graph in one call.
    G.remove_edges_from(self_loops)

    # STEP 5: Return the completed graph.
    # ------------------------------------
    # At this point the graph contains:
    #   - All channels as nodes (with metadata attributes)
    #   - All recommendation edges (minus self-loops, with weights)
    # Downstream modules (ideology.py, simulator.py) receive this graph
    # object and work with it directly.
    return G
