# ==============================================================================
# MODULE: run_pipeline.py
# PURPOSE: Hold the real step-by-step logic for running the entire project.
# ==============================================================================
#
# HIGH-LEVEL EXPLANATION:
#   Think of this file as the "engine room" of the project.
#   The other files each do one smaller job:
#
#       graph_builder.py  ->  ideology.py  ->  simulator.py  ->  metrics.py  ->  visualize.py
#
#   This file ties those smaller jobs together in the correct order.
#
#   MOST USERS SHOULD NOT START HERE.
#   The beginner-friendly file to run is the root-level file named:
#
#       run.py
#
#   You can open run.py and press the VS Code Play button on THAT file.
#   That file is just a very small front door. This file is the room behind
#   the door where the real work happens.
#
#   When the full project runs, these steps happen in order:
#     1. Read the real CSV files from data/
#     2. Build the recommendation graph
#     3. Add ideology scores to the graph nodes
#     4. Choose reasonable starting channels for the simulated user walks
#     5. Run the weighted random walks
#     6. Compute the summary metrics
#     7. Save the figures and CSV table into results/
#
# WHY THIS FILE IS IMPORTANT:
#   Without this file, the project is just a set of separate parts.
#   This file is the checklist that says what order those parts must run in.
#
# WHY THE IMPORT SETUP LOOKS A LITTLE STRANGE:
#   Python treats code differently depending on HOW you run it.
#
#   - If you run a file directly, Python starts from that file.
#   - If you run a package/module, Python starts from the package.
#
#   The earlier version of this file only worked in the second case.
#   That was confusing for a beginner because the Play button usually runs a
#   FILE directly, not a package. So this file now supports the direct-file
#   workflow on purpose.
#
# DESIGN DECISIONS:
#   - The logic is split into small functions so each step is easier to read
#     and test.
#   - The default run uses a fixed random seed so results are reproducible.
#   - Default starting nodes must have both a known ideology score and at
#     least one outgoing recommendation.
#
# ==============================================================================


from __future__ import annotations

import argparse
import random
from pathlib import Path


# When you run this file directly with "python3 src/run_pipeline.py",
# Python starts inside the src/ folder. That means "from src..." imports would
# normally fail, because Python is looking from the wrong starting location.
#
# To fix that, we manually add the PROJECT ROOT folder to Python's import path
# when this file is run directly.
#
# In plain English: we tell Python where the rest of the project lives.
if __package__ in {None, ""}:
    import sys

    PROJECT_ROOT_FOR_IMPORTS = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(PROJECT_ROOT_FOR_IMPORTS))

from src.graph_builder import build_graph, load_edges, load_nodes
from src.ideology import SCORE_ATTRIBUTE, assign_ideology_scores
from src.metrics import compute_all_metrics
from src.simulator import simulate_walks
from src.visualize import generate_all_figures


# --- DEFAULT PATHS ------------------------------------------------------------
#
# Path = the location of a file or folder on your computer.
#
# We define the important paths once here so the rest of the file can reuse
# them without hardcoding long folder names over and over.

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_NODES_PATH = PROJECT_ROOT / "data" / "vis_channel_stats.csv"
DEFAULT_EDGES_PATH = PROJECT_ROOT / "data" / "vis_channel_recs2.csv"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "results"


# --- DEFAULT RUN PARAMETERS ---------------------------------------------------

# A "constant" is a value we define once and reuse.
# These are the default settings used if the user does not pass custom values.

# Ten steps is long enough to observe movement while still keeping the default
# run fast and easy to interpret.
DEFAULT_NUM_STEPS = 10

# One walk per starting node keeps the default run lightweight while still
# sampling the whole network structure.
DEFAULT_WALKS_PER_START = 1

# Fixed seed = reproducible outputs.
DEFAULT_RANDOM_SEED = 42


# --- FUNCTIONS ----------------------------------------------------------------

def prepare_graph(nodes_path, edges_path):
    """
    Build the scored recommendation graph from the two real dataset CSV files.

    PARAMETERS:
        nodes_path (str or Path): Path to vis_channel_stats.csv
        edges_path (str or Path): Path to vis_channel_recs2.csv

    RETURNS:
        networkx.DiGraph: A graph with IDEOLOGY_SCORE attached to each node.
    """
    # STEP 1: Read the channel table.
    # This gives us one row per YouTube channel.
    nodes_df = load_nodes(nodes_path)

    # STEP 2: Read the recommendation-edge table.
    # This gives us one row per recommendation link.
    edges_df = load_edges(edges_path)

    # STEP 3: Turn those tables into a directed graph.
    graph = build_graph(nodes_df, edges_df)

    # STEP 4: Add numeric ideology scores to every node.
    # Example: L -> -1.0, C -> 0.0, R -> +1.0
    assign_ideology_scores(graph)

    # Return the finished graph so later steps can use it.
    return graph


def choose_start_nodes(G, score_attr=SCORE_ATTRIBUTE):
    """
    Select the default starting nodes for simulation.

    RULES:
        A node is a valid default start node only if:
        1. It has a numeric ideology score (not None)
        2. It has at least one outgoing edge

    WHY THESE RULES:
        - Drift cannot be interpreted if the starting ideology is unknown.
        - A node with zero outgoing edges immediately dead-ends, which makes it
          unhelpful as the default starting point for a recommendation walk.

    RETURNS:
        list: Node IDs that satisfy both rules.
    """
    # We build a list step by step.
    # A list is just an ordered collection of values.
    start_nodes = []

    # G.nodes(data=True) gives us:
    #   - node_id: the unique name/ID of a node
    #   - attrs: a dictionary of extra information attached to that node
    for node_id, attrs in G.nodes(data=True):
        # attrs.get(score_attr) reads the ideology score from the node.
        # "is not None" means: the score exists and is not missing.
        has_score = attrs.get(score_attr) is not None

        # out_degree tells us how many outgoing edges leave this node.
        # If that number is 0, a walk starting here cannot go anywhere.
        has_outgoing_edge = G.out_degree(node_id) > 0

        # Only keep nodes that satisfy BOTH rules.
        if has_score and has_outgoing_edge:
            start_nodes.append(node_id)

    return start_nodes


def run_pipeline(
    nodes_path=DEFAULT_NODES_PATH,
    edges_path=DEFAULT_EDGES_PATH,
    output_dir=DEFAULT_OUTPUT_DIR,
    num_steps=DEFAULT_NUM_STEPS,
    walks_per_start=DEFAULT_WALKS_PER_START,
    seed=DEFAULT_RANDOM_SEED,
):
    """
    Execute the full project pipeline end to end.

    RETURNS:
        dict: A small run summary useful for CLI output and testing.
    """
    # Build the graph and attach ideology scores.
    graph = prepare_graph(nodes_path, edges_path)

    # Decide where our simulated walks are allowed to begin.
    start_nodes = choose_start_nodes(graph)

    # If the list is empty, we stop early with a clear error message.
    # Raising an error means: stop the program here and explain why.
    if not start_nodes:
        raise ValueError(
            "No valid start nodes were found. "
            "The graph needs scored nodes with outgoing edges."
        )

    # random.Random(seed) creates a random-number generator.
    # The seed makes the results reproducible.
    rng = random.Random(seed)

    # Simulate the recommendation-following behavior.
    trajectories = simulate_walks(
        graph,
        start_nodes=start_nodes,
        num_steps=num_steps,
        walks_per_start=walks_per_start,
        rng=rng,
    )

    # Convert the graph + walks into summary numbers.
    metrics_dict = compute_all_metrics(graph, trajectories)

    # Write the figures and CSV output files to disk.
    generate_all_figures(graph, trajectories, metrics_dict, output_dir=str(output_dir))

    # Return a summary dictionary so tests and future code can inspect the run.
    return {
        "graph": graph,
        "trajectories": trajectories,
        "metrics": metrics_dict,
        "num_start_nodes": len(start_nodes),
        "num_walks": len(trajectories),
        "output_dir": Path(output_dir),
    }


def build_argument_parser():
    """
    Create the command-line parser.

    "Command-line arguments" are the extra options you can type after a
    command in the terminal.

    Example:
        python3 src/run_pipeline.py --num-steps 15 --seed 123

    In that example:
        --num-steps 15
    and
        --seed 123
    are command-line arguments.
    """
    parser = argparse.ArgumentParser(
        description=(
            "Run the full ideological-drift pipeline from CSV inputs to "
            "generated figures and summary metrics."
        )
    )

    parser.add_argument(
        "--nodes-path",
        default=str(DEFAULT_NODES_PATH),
        help="Path to vis_channel_stats.csv",
    )
    parser.add_argument(
        "--edges-path",
        default=str(DEFAULT_EDGES_PATH),
        help="Path to vis_channel_recs2.csv",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Directory where results/figures and results/tables are written",
    )
    parser.add_argument(
        "--num-steps",
        type=int,
        default=DEFAULT_NUM_STEPS,
        help="Maximum number of moves per walk",
    )
    parser.add_argument(
        "--walks-per-start",
        type=int,
        default=DEFAULT_WALKS_PER_START,
        help="How many walks to run from each starting node",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=DEFAULT_RANDOM_SEED,
        help="Random seed used for reproducible walks",
    )

    return parser


def main(argv=None):
    """
    Main entrypoint for this script.

    In plain English, this function is the "start the engine" function.
    Another file can call this function so the user does not need to know how
    the rest of the pipeline is wired together.
    """
    # Build the parser object that knows which arguments are allowed.
    parser = build_argument_parser()

    # Parse the actual values the user typed in the terminal.
    # If the user typed nothing extra, the defaults are used.
    args = parser.parse_args(argv)

    # Run the real project using either the defaults or the user's overrides.
    summary = run_pipeline(
        nodes_path=args.nodes_path,
        edges_path=args.edges_path,
        output_dir=args.output_dir,
        num_steps=args.num_steps,
        walks_per_start=args.walks_per_start,
        seed=args.seed,
    )

    # Pull the metrics dictionary out of the returned summary so the code below
    # is shorter and easier to read.
    metrics_dict = summary["metrics"]

    # Print a simple human-readable summary in the terminal.
    print("Pipeline completed successfully.")
    print(f"Start nodes used: {summary['num_start_nodes']}")
    print(f"Walks generated: {summary['num_walks']}")
    print(f"Output directory: {summary['output_dir']}")
    print(f"Mean drift: {metrics_dict['mean_drift']}")
    print(f"Mean extremity change: {metrics_dict['mean_extremity_change']}")
    print(f"Ideology assortativity: {metrics_dict['ideology_assortativity']}")
    print(f"Average clustering: {metrics_dict['average_clustering']}")


if __name__ == "__main__":
    # This still lets advanced users run this file directly if they want to,
    # but the simpler beginner-facing entrypoint is the root-level run.py file.
    main()