# ==============================================================================
# MODULE: simulator.py
# PURPOSE: Simulate user movement through the recommendation graph by
#          performing weighted random walks.
# ==============================================================================
#
# This is the THIRD module in the analysis pipeline:
#
#     graph_builder.py  →  ideology.py  →  simulator.py  →  metrics.py  →  visualize.py
#                                           ^^^^^^^^^^^^
#
# WHAT THIS MODULE DOES:
#   Once graph_builder.py has created the recommendation graph and
#   ideology.py has attached a numeric ideology score to every node,
#   we can start asking the core research question:
#
#       "If a user keeps clicking recommended content, where do they go?"
#
#   We model that behavior with a random walk.
#
# WHAT IS A RANDOM WALK?
#   A random walk is a process where you stand on one node in a graph,
#   choose one outgoing edge, move to the next node, and repeat.
#   In this project, one "step" represents a user following one more
#   recommendation.
#
#   Example:
#       User starts on ch_L1
#       YouTube recommends ch_L2, ch_L3, and ch_C1
#       The simulator chooses one of those three targets
#       Then repeats from the newly chosen node
#
# WHY WEIGHT THE WALK?
#   Not every recommendation edge is equally strong.
#   The dataset gives us RELEVANT_IMPRESSIONS_DAILY for each edge.
#   That number estimates how often that recommendation appears.
#   A recommendation shown 200 times per day should be chosen more often
#   than one shown 30 times per day.
#
#   So our walk is not a uniform random walk (all edges equally likely).
#   It is a weighted random walk (stronger edges more likely).
#
# WHAT THIS MODULE RETURNS:
#   Each walk returns a trajectory — a list of dictionaries.
#   Every dictionary represents one step in the walk and stores:
#       - the step number
#       - the node ID at that step
#       - the ideology score at that step
#
#   Example trajectory:
#       [
#           {"step": 0, "node_id": "ch_L1", "ideology_score": -1.0},
#           {"step": 1, "node_id": "ch_C1", "ideology_score":  0.0},
#           {"step": 2, "node_id": "ch_R1", "ideology_score":  1.0},
#       ]
#
#   This format is intentionally simple and explicit. It is easy to:
#       - print and inspect by eye
#       - convert into a pandas DataFrame later
#       - feed into metrics.py to compute drift statistics
#
# DESIGN DECISIONS:
#   - choose_next_node() is separated from simulate_walk() so we can test
#     "edge selection" logic independently from full walk logic.
#   - Dead ends return None instead of crashing. A dead end is a node with
#     no outgoing edges. In real user terms, that means "there is nowhere
#     left to go in this graph." The walk should stop cleanly.
#   - If every outgoing edge has a missing or non-positive weight, we fall
#     back to uniform random choice among those neighbors. That keeps the
#     walker moving when the graph structure exists but the weights are bad.
#   - The caller can pass in a random.Random object. This is important for
#     testing: fixed random seeds make stochastic behavior reproducible.
#
# ==============================================================================


import random

from src.ideology import SCORE_ATTRIBUTE


# --- CONSTANTS ----------------------------------------------------------------

# This is the edge attribute used by graph_builder.py to store recommendation
# strength. The simulator reads this to make stronger edges more likely.
DEFAULT_WEIGHT_ATTRIBUTE = "RELEVANT_IMPRESSIONS_DAILY"

# These are the field names used in each trajectory record.
# Defining them once avoids typos and makes later modules more consistent.
STEP_FIELD = "step"
NODE_FIELD = "node_id"
SCORE_FIELD = "ideology_score"


# --- FUNCTIONS ----------------------------------------------------------------

def choose_next_node(G, current_node, rng=None, weight_attr=DEFAULT_WEIGHT_ATTRIBUTE):
	"""
	Choose one outgoing neighbor from current_node using weighted randomness.

	PARAMETERS:
		G (networkx.DiGraph): The recommendation graph.
		current_node: The node where the walker currently stands.
		rng (random.Random or None): Random number generator to use.
									 If None, a fresh generator is created.
		weight_attr (str): Name of the edge attribute holding the weight.

	RETURNS:
		node ID or None:
			- Returns the chosen next node if at least one outgoing edge exists
			- Returns None if current_node has zero outgoing edges

	RAISES:
		ValueError: If current_node does not exist in the graph.

	WHY A SEPARATE FUNCTION?
		Choosing the next edge is the "random" part of the simulator.
		By isolating it here, we can test edge-selection behavior without
		having to inspect a whole trajectory at the same time.
	"""
	if current_node not in G:
		raise ValueError(f"Start/current node '{current_node}' is not in the graph.")

	if rng is None:
		rng = random.Random()

	# G.successors(node) returns all nodes reachable by one outgoing edge.
	# We convert it to a list because we need to iterate multiple times.
	neighbors = list(G.successors(current_node))

	# No outgoing edges means the walker is at a dead end.
	if not neighbors:
		return None

	weights = []
	for neighbor in neighbors:
		raw_weight = G.edges[current_node, neighbor].get(weight_attr, 0.0)

		# Edge weights should be numeric, but robust code assumes real data
		# can be messy. If conversion fails, treat the edge as zero-weight.
		try:
			numeric_weight = float(raw_weight)
		except (TypeError, ValueError):
			numeric_weight = 0.0

		# Negative weights do not make sense as probabilities.
		# Clamp them to zero.
		weights.append(max(numeric_weight, 0.0))

	# If all weights are zero, weighted choice is impossible because there is
	# no probability mass to work with. In that case we fall back to a plain
	# uniform random choice across existing outgoing neighbors.
	if sum(weights) == 0:
		return rng.choice(neighbors)

	# random.choices returns a list even when k=1, so we take [0].
	return rng.choices(neighbors, weights=weights, k=1)[0]


def simulate_walk(
	G,
	start_node,
	num_steps,
	rng=None,
	weight_attr=DEFAULT_WEIGHT_ATTRIBUTE,
	score_attr=SCORE_ATTRIBUTE,
):
	"""
	Run one weighted random walk through the graph.

	PARAMETERS:
		G (networkx.DiGraph): The scored recommendation graph.
		start_node: Node where the walk begins.
		num_steps (int): Maximum number of moves to take.
						 IMPORTANT: step 0 is the starting node, so a walk
						 with num_steps=3 can return up to 4 records.
		rng (random.Random or None): Random number generator.
		weight_attr (str): Edge attribute used for weighted choice.
		score_attr (str): Node attribute holding ideology score.

	RETURNS:
		list[dict]: Trajectory records, one dictionary per visited node.

	RAISES:
		ValueError: If start_node is not in the graph or num_steps is negative.

	WALK LENGTH RULE:
		- The trajectory ALWAYS includes the starting node as step 0.
		- Then the walker attempts up to num_steps moves.
		- If it reaches a dead end early, the walk stops immediately.
	"""
	if start_node not in G:
		raise ValueError(f"Start node '{start_node}' is not in the graph.")

	if num_steps < 0:
		raise ValueError("num_steps must be 0 or greater.")

	if rng is None:
		rng = random.Random()

	# Record the starting state before any movement happens.
	current_node = start_node
	trajectory = [
		{
			STEP_FIELD: 0,
			NODE_FIELD: current_node,
			SCORE_FIELD: G.nodes[current_node].get(score_attr),
		}
	]

	# range(1, num_steps + 1) means:
	#   if num_steps = 3, loop over 1, 2, 3
	# Each loop iteration attempts one move.
	for step_number in range(1, num_steps + 1):
		next_node = choose_next_node(
			G,
			current_node,
			rng=rng,
			weight_attr=weight_attr,
		)

		# None means the walker hit a dead end (no outgoing edges).
		# We stop early instead of padding the path with fake data.
		if next_node is None:
			break

		current_node = next_node
		trajectory.append(
			{
				STEP_FIELD: step_number,
				NODE_FIELD: current_node,
				SCORE_FIELD: G.nodes[current_node].get(score_attr),
			}
		)

	return trajectory


def simulate_walks(
	G,
	start_nodes,
	num_steps,
	walks_per_start=1,
	rng=None,
	weight_attr=DEFAULT_WEIGHT_ATTRIBUTE,
	score_attr=SCORE_ATTRIBUTE,
):
	"""
	Run multiple weighted random walks from one or more starting nodes.

	PARAMETERS:
		G (networkx.DiGraph): The scored recommendation graph.
		start_nodes (iterable): Collection of starting node IDs.
		num_steps (int): Maximum number of moves per walk.
		walks_per_start (int): How many walks to run from each start node.
		rng (random.Random or None): Random number generator shared across runs.
		weight_attr (str): Edge attribute used for weighted choice.
		score_attr (str): Node attribute holding ideology score.

	RETURNS:
		list[list[dict]]: A list of trajectories.

	WHY THIS FUNCTION EXISTS:
		Research usually needs many paths, not one. A single walk can be
		misleading because randomness can take one unusual route. Running
		many walks lets metrics.py summarize typical behavior.
	"""
	if walks_per_start <= 0:
		raise ValueError("walks_per_start must be at least 1.")

	if rng is None:
		rng = random.Random()

	all_trajectories = []

	for start_node in start_nodes:
		for _ in range(walks_per_start):
			trajectory = simulate_walk(
				G,
				start_node,
				num_steps,
				rng=rng,
				weight_attr=weight_attr,
				score_attr=score_attr,
			)
			all_trajectories.append(trajectory)

	return all_trajectories
